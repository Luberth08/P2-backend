import os
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from sqlalchemy import select 

from app.crud import (
    solicitud_diagnostico,
    evidencia as evidencia_crud,
    diagnostico as diagnostico_crud,
    tipo_incidente as tipo_incidente_crud,
    incidente as incidente_crud,
    vehiculo as crud_vehiculo
)
from app.models.solicitud_diagnostico import EstadoSolicitudDiagnostico
from app.services import ai_service 

logger = logging.getLogger(__name__)
UPLOAD_DIR = os.path.join("static", "uploads", "diagnosticos")

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

async def _save_upload_file(file: UploadFile, dest_folder: str) -> str:
    _ensure_dir(dest_folder)
    ext = os.path.splitext(file.filename)[1] or ""
    filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(dest_folder, filename)
    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)
    return f"/static/uploads/diagnosticos/{filename}"

# ---------- Función principal que reemplaza tu anterior crear_solicitud_diagnostico ----------
async def crear_solicitud_diagnostico(
    db: AsyncSession,
    id_persona: int,
    descripcion: str,
    ubicacion_str: str,
    matricula: Optional[str] = None,
    vehiculo_data: Optional[Dict[str, Any]] = None,
    fotos: Optional[List[UploadFile]] = None,
    audio: Optional[UploadFile] = None
):
    """
    Crea la solicitud, guarda archivos, llama a la IA, y asocia TipoIncidente existente.
    """
    import uuid
    from shapely.geometry import Point
    from geoalchemy2.shape import from_shape

    # 1. Ubicación
    try:
        lat, lon = map(float, ubicacion_str.split(","))
        point = Point(lon, lat)
        ubicacion_geog = from_shape(point, srid=4326)
    except Exception:
        raise ValueError("Ubicación inválida. Use 'lat,lon'")

    # 2. Vehículo
    veh = None
    if matricula:
        veh = await crud_vehiculo.get_by_matricula(db, matricula)
    if not veh and vehiculo_data and vehiculo_data.get("matricula"):
        vehiculo_data["id_persona"] = id_persona
        veh = await crud_vehiculo.create(db, vehiculo_data)

    # 3. Crear solicitud (estado pendiente)
    solicitud_data = {
        "descripcion": descripcion,
        "ubicacion": ubicacion_geog,
        "id_persona": id_persona,
        "id_vehiculo": veh.id if veh else None,
    }
    solicitud = await solicitud_diagnostico.create(db, solicitud_data)
    await db.flush()  # para obtener el id

    # 4. Guardar evidencias (fotos y audio)
    folder = UPLOAD_DIR
    _ensure_dir(folder)
    imagen_urls = []
    evidencias_imagenes = []
    transcripcion_text = None

    # Guardar fotos sin análisis primero (se actualizará después)
    evidencias_imagenes = []
    if fotos:
        for f in fotos[:3]:  # máximo 3 fotos
            url = await _save_upload_file(f, folder)
            imagen_urls.append(url)
            evidencia = await evidencia_crud.create(db, {
                "url": url,
                "tipo": "imagen",
                "id_solicitud_diagnostico": solicitud.id
            })
            evidencias_imagenes.append(evidencia)

    if audio:
        audio_url = await _save_upload_file(audio, folder)
        # Transcribir el audio usando nuestro ai_service
        audio_path = os.path.join(folder, os.path.basename(audio_url))
        transcripcion_text = await ai_service.transcribe_audio(audio_path)
        await evidencia_crud.create(db, {
            "url": audio_url,
            "tipo": "audio",
            "transcripcion": transcripcion_text,
            "id_solicitud_diagnostico": solicitud.id
        })

    # Commit inicial para persistir solicitud y evidencias
    await db.commit()

    # 5. Obtener todos los conceptos válidos de TipoIncidente desde la BD
    result = await db.execute(select(tipo_incidente_crud.model.concepto))
    valid_concepts = [row[0] for row in result.all()]
    if not valid_concepts:
        logger.warning("No hay Tipos de Incidente cargados en la BD. Usando lista por defecto.")
        valid_concepts = ["desconocido", "informacion_insuficiente"]

    # 6. Llamar a la IA real
    try:
        # Analizar imágenes con CLIP + nuestros conceptos válidos
        image_analysis = []
        if imagen_urls:
            # Convertir URLs a rutas locales (porque en Render se guardan en disco)
            local_paths = [("." + url) if url.startswith("/static") else url for url in imagen_urls]
            image_analysis = await ai_service.analyze_multiple_images(local_paths, valid_concepts)
            
            # Guardar análisis CLIP en evidencia.transcripcion
            for idx, (evidencia, analisis) in enumerate(zip(evidencias_imagenes, image_analysis)):
                # Obtener el concepto con mayor confianza
                best_match = max(analisis.items(), key=lambda x: x[1])
                analisis_texto = f"CLIP Analysis: {best_match[0]} (confianza: {best_match[1]:.2%})"
                # Agregar top 3 conceptos
                top_3 = sorted(analisis.items(), key=lambda x: x[1], reverse=True)[:3]
                analisis_texto += " | Top 3: " + ", ".join([f"{k}: {v:.2%}" for k, v in top_3])
                
                evidencia.transcripcion = analisis_texto
                await db.flush()

        # Generar diagnóstico con LLM
        vehiculo_info = None
        if veh:
            vehiculo_info = {
                "matricula": veh.matricula,
                "marca": veh.marca,
                "modelo": veh.modelo,
                "anio": veh.anio,
            }
        diagnosis = await ai_service.generate_diagnosis(
            description=descripcion,
            image_analysis=image_analysis,
            transcription=transcripcion_text,
            vehicle_info=vehiculo_info,
            valid_concepts=valid_concepts
        )

        # 7. Crear el registro Diagnostico
        nuevo_diagnostico = await diagnostico_crud.create(db, {
            "descripcion": diagnosis["descripcion"],
            "nivel_confianza": Decimal(str(diagnosis["nivel_confianza"])),
            "id_solicitud_diagnostico": solicitud.id
        })
        await db.flush()

        # 8. Para cada incidente devuelto por IA, buscar el TipoIncidente por concepto (exacto)
        for inc in diagnosis["incidentes"]:
            concepto = inc["concepto"]
            tipo_inc = await tipo_incidente_crud.get_by_concepto(db, concepto)
            if not tipo_inc:
                logger.error(f"No se encontró TipoIncidente con concepto '{concepto}'. Se omite este incidente.")
                continue
            await incidente_crud.create(db, {
                "id_diagnostico": nuevo_diagnostico.id,
                "id_tipo_incidente": tipo_inc.id,
                "sugerido_por": inc["sugerido_por"],
                "nivel_confianza": Decimal(str(inc["nivel_confianza"]))
            })

        # 9. Actualizar estado de la solicitud a 'diagnosticada'
        await solicitud_diagnostico.update_estado(db, solicitud.id, EstadoSolicitudDiagnostico.diagnosticada)
        await db.commit()

    except Exception as e:
        logger.exception(f"Error durante el procesamiento de IA para solicitud {solicitud.id}")
        await solicitud_diagnostico.update_estado(db, solicitud.id, EstadoSolicitudDiagnostico.error)
        await db.commit()
        # Re-lanzar o manejar según tu política
        raise

    # Recargar solicitud con relaciones (opcional)
    return await solicitud_diagnostico.get(db, solicitud.id)


async def reintentar_procesamiento(db: AsyncSession, solicitud_id: int):
    """
    Reintenta el procesamiento de IA para una solicitud en estado 'error'.
    """
    solicitud = await solicitud_diagnostico.get(db, solicitud_id)
    if not solicitud:
        raise ValueError("Solicitud no encontrada")
    
    if solicitud.estado != EstadoSolicitudDiagnostico.error:
        raise ValueError("Solo se puede reintentar solicitudes en estado 'error'")
    
    # Obtener evidencias existentes
    from sqlalchemy import select
    result = await db.execute(
        select(evidencia_crud.model).where(
            evidencia_crud.model.id_solicitud_diagnostico == solicitud_id
        )
    )
    evidencias = result.scalars().all()
    
    # Separar imágenes y audio
    imagen_urls = [e.url for e in evidencias if e.tipo == "imagen"]
    audio_evidencia = next((e for e in evidencias if e.tipo == "audio"), None)
    transcripcion_text = audio_evidencia.transcripcion if audio_evidencia else None
    
    # Obtener conceptos válidos
    result = await db.execute(select(tipo_incidente_crud.model.concepto))
    valid_concepts = [row[0] for row in result.all()]
    if not valid_concepts:
        valid_concepts = ["desconocido", "informacion_insuficiente"]
    
    try:
        # Analizar imágenes con CLIP
        image_analysis = []
        if imagen_urls:
            local_paths = [("." + url) if url.startswith("/static") else url for url in imagen_urls]
            image_analysis = await ai_service.analyze_multiple_images(local_paths, valid_concepts)
        
        # Obtener info del vehículo
        vehiculo_info = None
        if solicitud.id_vehiculo:
            veh = await crud_vehiculo.get(db, solicitud.id_vehiculo)
            if veh:
                vehiculo_info = {
                    "matricula": veh.matricula,
                    "marca": veh.marca,
                    "modelo": veh.modelo,
                    "anio": veh.anio,
                }
        
        # Generar diagnóstico con LLM
        diagnosis = await ai_service.generate_diagnosis(
            description=solicitud.descripcion or "",
            image_analysis=image_analysis,
            transcription=transcripcion_text,
            vehicle_info=vehiculo_info,
            valid_concepts=valid_concepts
        )
        
        # Eliminar diagnóstico anterior si existe
        diagnostico_anterior = await diagnostico_crud.get_by_solicitud(db, solicitud_id)
        if diagnostico_anterior:
            await db.delete(diagnostico_anterior)
            await db.flush()
        
        # Crear nuevo diagnóstico
        nuevo_diagnostico = await diagnostico_crud.create(db, {
            "descripcion": diagnosis["descripcion"],
            "nivel_confianza": Decimal(str(diagnosis["nivel_confianza"])),
            "id_solicitud_diagnostico": solicitud_id
        })
        await db.flush()
        
        # Crear incidentes
        for inc in diagnosis["incidentes"]:
            concepto = inc["concepto"]
            tipo_inc = await tipo_incidente_crud.get_by_concepto(db, concepto)
            if not tipo_inc:
                logger.error(f"No se encontró TipoIncidente con concepto '{concepto}'. Se omite.")
                continue
            await incidente_crud.create(db, {
                "id_diagnostico": nuevo_diagnostico.id,
                "id_tipo_incidente": tipo_inc.id,
                "sugerido_por": inc["sugerido_por"],
                "nivel_confianza": Decimal(str(inc["nivel_confianza"]))
            })
        
        # Actualizar estado a diagnosticada
        await solicitud_diagnostico.update_estado(db, solicitud_id, EstadoSolicitudDiagnostico.diagnosticada)
        await db.commit()
        
        return await solicitud_diagnostico.get(db, solicitud_id)
        
    except Exception as e:
        logger.exception(f"Error en reintento de procesamiento para solicitud {solicitud_id}")
        await solicitud_diagnostico.update_estado(db, solicitud_id, EstadoSolicitudDiagnostico.error)
        await db.commit()
        raise