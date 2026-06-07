from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.quote import (
    QuoteRequestCreate, QuoteRequestResponse, QuoteRequestListResponse,
    QuoteResponseCreate, QuoteResponseResponse, QuoteAcceptRequest,
    TallerQuoteRequestResponse, TallerQuoteRequestListResponse
)
from app.services.quote_service import quote_service
from app.core.deps import get_current_usuario, require_permiso
from app.models.usuario import Usuario
from typing import Optional, List
from app.models.quote_request import EstadoQuoteRequest
from app.models.tipo_servicio import TipoServicio
from app.models.taller import Taller
import os
import uuid

router = APIRouter(tags=["Cotizaciones"])


# Endpoints para CLIENTE (Flutter)


@router.get("/tipos-servicio")
async def obtener_tipos_servicio(
    db: AsyncSession = Depends(get_db)
):
    """Obtiene la lista de tipos de servicios disponibles para cotizaciones"""
    try:
        from sqlalchemy import select
        result = await db.execute(select(TipoServicio))
        tipos_servicio = result.scalars().all()
        
        return [
            {
                "id": tipo.id,
                "nombre": tipo.nombre,
                "descripcion": tipo.descripcion
            }
            for tipo in tipos_servicio
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/talleres")
async def obtener_talleres(
    db: AsyncSession = Depends(get_db)
):
    """Obtiene la lista de talleres disponibles (solo activos)"""
    try:
        from sqlalchemy import select
        from app.models.taller import EstadoTaller
        result = await db.execute(
            select(Taller).where(Taller.estado == EstadoTaller.activo)
        )
        talleres = result.scalars().all()
        
        return [
            {
                "id": taller.id,
                "nombre": taller.nombre,
                "telefono": taller.telefono
            }
            for taller in talleres
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/solicitudes", response_model=QuoteRequestResponse, status_code=status.HTTP_201_CREATED)
async def crear_solicitud_cotizacion(
    req: QuoteRequestCreate,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """El cliente crea una solicitud de cotización (sin fotos)"""
    try:
        quote_req = await quote_service.create_quote_request(db, current_usuario.id, req)
        
        # Formatear ubicación para la respuesta
        from app.services.quote_service import quote_service as qs
        ubicacion_str = qs.format_ubicacion(quote_req.ubicacion)
        
        # Cargar relaciones
        await db.refresh(quote_req, ["vehiculo", "servicio", "responses"])
        
        response_dict = {
            "id": quote_req.id,
            "ubicacion": ubicacion_str,
            "fecha_creacion": quote_req.fecha_creacion,
            "fecha_expiracion": quote_req.fecha_expiracion,
            "comentario": quote_req.comentario,
            "estado": quote_req.estado.value,
            "fecha_aceptada": quote_req.fecha_aceptada,
            "id_vehiculo": quote_req.id_vehiculo,
            "id_servicio": quote_req.id_servicio,
            "id_cliente": quote_req.id_cliente,
            "vehiculo": {
                "id": quote_req.vehiculo.id,
                "placa": quote_req.vehiculo.matricula,
                "marca": quote_req.vehiculo.marca,
                "modelo": quote_req.vehiculo.modelo
            } if quote_req.vehiculo else None,
            "servicio": {
                "id": quote_req.servicio.id,
                "nombre": quote_req.servicio.nombre,
                "descripcion": quote_req.servicio.descripcion
            } if quote_req.servicio else None,
            "responses": [],
            "fotos": quote_req.fotos
        }
        
        return QuoteRequestResponse(**response_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/solicitudes-con-fotos", response_model=QuoteRequestResponse, status_code=status.HTTP_201_CREATED)
async def crear_solicitud_cotizacion_con_fotos(
    id_vehiculo: int = Form(...),
    id_servicio: int = Form(...),
    ubicacion_lat: Optional[float] = Form(None),
    ubicacion_lon: Optional[float] = Form(None),
    comentario: Optional[str] = Form(None),
    ids_talleres: str = Form(...),  # JSON string
    fotos: Optional[List[UploadFile]] = File(None),
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """El cliente crea una solicitud de cotización con fotos"""
    try:
        import json
        ids_talleres_list = json.loads(ids_talleres)
        
        # Guardar fotos si se proporcionan
        foto_urls = []
        if fotos:
            # Crear directorio de uploads si no existe
            upload_dir = "uploads/quote_requests"
            os.makedirs(upload_dir, exist_ok=True)
            
            for foto in fotos:
                # Generar nombre único para el archivo
                file_extension = foto.filename.split('.')[-1] if '.' in foto.filename else 'jpg'
                unique_filename = f"{uuid.uuid4()}.{file_extension}"
                file_path = os.path.join(upload_dir, unique_filename)
                
                # Guardar el archivo
                with open(file_path, "wb") as buffer:
                    content = await foto.read()
                    buffer.write(content)
                
                # Generar URL pública (ajustar según tu configuración)
                foto_url = f"/uploads/quote_requests/{unique_filename}"
                # Agregar URL base para que sea accesible desde el frontend
                from app.core.config import settings
                foto_url = f"{settings.BASE_URL}{foto_url}"
                foto_urls.append(foto_url)
        
        # Crear el objeto QuoteRequestCreate
        req = QuoteRequestCreate(
            id_vehiculo=id_vehiculo,
            id_servicio=id_servicio,
            ubicacion_lat=ubicacion_lat,
            ubicacion_lon=ubicacion_lon,
            comentario=comentario,
            ids_talleres=ids_talleres_list
        )
        
        quote_req = await quote_service.create_quote_request(db, current_usuario.id, req, foto_urls)
        
        # Formatear ubicación para la respuesta
        from app.services.quote_service import quote_service as qs
        ubicacion_str = qs.format_ubicacion(quote_req.ubicacion)
        
        # Cargar relaciones
        await db.refresh(quote_req, ["vehiculo", "servicio", "responses"])
        
        response_dict = {
            "id": quote_req.id,
            "ubicacion": ubicacion_str,
            "fecha_creacion": quote_req.fecha_creacion,
            "fecha_expiracion": quote_req.fecha_expiracion,
            "comentario": quote_req.comentario,
            "estado": quote_req.estado.value,
            "fecha_aceptada": quote_req.fecha_aceptada,
            "id_vehiculo": quote_req.id_vehiculo,
            "id_servicio": quote_req.id_servicio,
            "id_cliente": quote_req.id_cliente,
            "vehiculo": {
                "id": quote_req.vehiculo.id,
                "placa": quote_req.vehiculo.matricula,
                "marca": quote_req.vehiculo.marca,
                "modelo": quote_req.vehiculo.modelo
            } if quote_req.vehiculo else None,
            "servicio": {
                "id": quote_req.servicio.id,
                "nombre": quote_req.servicio.nombre,
                "descripcion": quote_req.servicio.descripcion
            } if quote_req.servicio else None,
            "responses": [],
            "fotos": quote_req.fotos
        }
        
        return QuoteRequestResponse(**response_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/solicitudes/mis-cotizaciones", response_model=QuoteRequestListResponse)
async def mis_cotizaciones(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    estado: Optional[str] = Query(None),
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """El cliente obtiene sus solicitudes de cotización"""
    estado_enum = None
    if estado:
        try:
            estado_enum = EstadoQuoteRequest(estado)
        except ValueError:
            raise HTTPException(status_code=400, detail="Estado inválido")
    
    items, total = await quote_service.get_client_quotes(db, current_usuario.id, skip, limit, estado_enum)
    
    # Formatear respuestas
    formatted_items = []
    for item in items:
        from app.services.quote_service import quote_service as qs
        ubicacion_str = qs.format_ubicacion(item.ubicacion)
        
        await db.refresh(item, ["vehiculo", "servicio", "responses"])
        
        # Formatear responses
        responses_data = []
        for resp in item.responses:
            await db.refresh(resp, ["items"])
            
            items_data = [
                {
                    "id": quote_item.id,
                    "titulo": quote_item.titulo,
                    "precio": quote_item.precio
                }
                for quote_item in resp.items
            ]
            
            responses_data.append({
                "id": resp.id,
                "fecha_creacion": resp.fecha_creacion,
                "fecha_respuesta": resp.fecha_respuesta,
                "estado": resp.estado.value,
                "total": resp.total,
                "id_quote_request": resp.id_quote_request,
                "id_taller": resp.id_taller,
                "items": items_data
            })
        
        formatted_items.append({
            "id": item.id,
            "ubicacion": ubicacion_str,
            "fecha_creacion": item.fecha_creacion,
            "fecha_expiracion": item.fecha_expiracion,
            "comentario": item.comentario,
            "estado": item.estado.value,
            "fecha_aceptada": item.fecha_aceptada,
            "id_vehiculo": item.id_vehiculo,
            "id_servicio": item.id_servicio,
            "id_cliente": item.id_cliente,
            "vehiculo": {
                "id": item.vehiculo.id,
                "placa": item.vehiculo.matricula,
                "marca": item.vehiculo.marca,
                "modelo": item.vehiculo.modelo
            } if item.vehiculo else None,
            "servicio": {
                "id": item.tipo_servicio.id,
                "nombre": item.tipo_servicio.nombre,
                "descripcion": item.tipo_servicio.descripcion
            } if item.tipo_servicio else None,
            "responses": responses_data,
            "fotos": item.fotos
        })
    
    return QuoteRequestListResponse(items=formatted_items, total=total, skip=skip, limit=limit)


@router.get("/solicitudes/{request_id}", response_model=QuoteRequestResponse)
async def obtener_detalle_cotizacion(
    request_id: int,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """El cliente obtiene el detalle de una solicitud de cotización"""
    quote_req = await quote_service.get_quote_request_detail(db, request_id, current_usuario.id)
    if not quote_req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    from app.services.quote_service import quote_service as qs
    ubicacion_str = qs.format_ubicacion(quote_req.ubicacion)
    
    await db.refresh(quote_req, ["vehiculo", "servicio", "responses"])
    
    # Formatear responses
    responses_data = []
    for resp in quote_req.responses:
        await db.refresh(resp, ["items"])
        
        items_data = [
            {
                "id": quote_item.id,
                "titulo": quote_item.titulo,
                "precio": quote_item.precio
            }
            for quote_item in resp.items
        ]
        
        responses_data.append({
            "id": resp.id,
            "fecha_creacion": resp.fecha_creacion,
            "fecha_respuesta": resp.fecha_respuesta,
            "estado": resp.estado.value,
            "total": resp.total,
            "id_quote_request": resp.id_quote_request,
            "id_taller": resp.id_taller,
            "items": items_data
        })
    
    response_dict = {
        "id": quote_req.id,
        "ubicacion": ubicacion_str,
        "fecha_creacion": quote_req.fecha_creacion,
        "fecha_expiracion": quote_req.fecha_expiracion,
        "comentario": quote_req.comentario,
        "estado": quote_req.estado.value,
        "fecha_aceptada": quote_req.fecha_aceptada,
        "id_vehiculo": quote_req.id_vehiculo,
        "id_servicio": quote_req.id_servicio,
        "id_cliente": quote_req.id_cliente,
        "vehiculo": {
            "id": quote_req.vehiculo.id,
            "placa": quote_req.vehiculo.matricula,
            "marca": quote_req.vehiculo.marca,
            "modelo": quote_req.vehiculo.modelo
        } if quote_req.vehiculo else None,
        "servicio": {
            "id": quote_req.servicio.id,
            "nombre": quote_req.servicio.nombre,
            "descripcion": quote_req.servicio.descripcion
        } if quote_req.servicio else None,
        "responses": responses_data,
        "fotos": quote_req.fotos
    }
    
    return QuoteRequestResponse(**response_dict)


@router.post("/solicitudes/{request_id}/aceptar", response_model=QuoteRequestResponse)
async def aceptar_cotizacion(
    request_id: int,
    req: QuoteAcceptRequest,
    current_usuario: Usuario = Depends(get_current_usuario),
    db: AsyncSession = Depends(get_db)
):
    """El cliente acepta una cotización específica"""
    try:
        quote_req = await quote_service.accept_quote(db, request_id, req, current_usuario.id)
        
        await db.refresh(quote_req, ["vehiculo", "servicio", "responses"])
        
        from app.services.quote_service import quote_service as qs
        ubicacion_str = qs.format_ubicacion(quote_req.ubicacion)
        
        # Formatear responses
        responses_data = []
        for resp in quote_req.responses:
            await db.refresh(resp, ["items"])
            
            items_data = [
                {
                    "id": quote_item.id,
                    "titulo": quote_item.titulo,
                    "precio": quote_item.precio
                }
                for quote_item in resp.items
            ]
            
            responses_data.append({
                "id": resp.id,
                "fecha_creacion": resp.fecha_creacion,
                "fecha_respuesta": resp.fecha_respuesta,
                "estado": resp.estado.value,
                "total": resp.total,
                "id_quote_request": resp.id_quote_request,
                "id_taller": resp.id_taller,
                "items": items_data
            })
        
        response_dict = {
            "id": quote_req.id,
            "ubicacion": ubicacion_str,
            "fecha_creacion": quote_req.fecha_creacion,
            "fecha_expiracion": quote_req.fecha_expiracion,
            "comentario": quote_req.comentario,
            "estado": quote_req.estado.value,
            "fecha_aceptada": quote_req.fecha_aceptada,
            "id_vehiculo": quote_req.id_vehiculo,
            "id_servicio": quote_req.id_servicio,
            "id_cliente": quote_req.id_cliente,
            "vehiculo": {
                "id": quote_req.vehiculo.id,
                "placa": quote_req.vehiculo.matricula,
                "marca": quote_req.vehiculo.marca,
                "modelo": quote_req.vehiculo.modelo
            } if quote_req.vehiculo else None,
            "servicio": {
                "id": quote_req.servicio.id,
                "nombre": quote_req.servicio.nombre,
                "descripcion": quote_req.servicio.descripcion
            } if quote_req.servicio else None,
            "responses": responses_data,
            "fotos": quote_req.fotos
        }
        
        return QuoteRequestResponse(**response_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoints para TALLER (Web)


@router.get("/taller/solicitudes-pendientes", response_model=TallerQuoteRequestListResponse)
async def taller_solicitudes_pendientes(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_usuario: Usuario = Depends(require_permiso("cotizacion:revisar")),
    db: AsyncSession = Depends(get_db)
):
    """El taller obtiene sus solicitudes de cotización pendientes"""
    from app.models.rol_usuario import RolUsuario
    
    # Obtener el taller del usuario desde sus roles (tomar el primero con taller)
    result = await db.execute(
        select(RolUsuario).where(RolUsuario.id_usuario == current_usuario.id, RolUsuario.id_taller.isnot(None))
    )
    roles_usuario = result.scalars().all()
    
    if not roles_usuario:
        raise HTTPException(status_code=404, detail="Taller no encontrado para el usuario")
    
    # Tomar el primer taller encontrado
    taller_id = roles_usuario[0].id_taller
    
    items, total = await quote_service.get_taller_pending_quotes(db, taller_id, skip, limit)
    
    # Formatear respuestas
    formatted_items = []
    for item in items:
        from app.services.quote_service import quote_service as qs
        ubicacion_str = qs.format_ubicacion(item.ubicacion)
        
        await db.refresh(item, ["vehiculo", "tipo_servicio", "cliente", "responses"])
        
        # Verificar si el taller ya respondió
        from app.crud.crud_quote_response import quote_response as qr_crud
        mi_respuesta = await qr_crud.get_by_taller_and_request(db, taller_id, item.id)
        
        ya_respondio = mi_respuesta and mi_respuesta.estado.value != "pendiente"
        
        # Formatear mi respuesta si existe
        mi_respuesta_data = None
        if mi_respuesta:
            await db.refresh(mi_respuesta, ["items"])
            
            items_data = [
                {
                    "id": quote_item.id,
                    "titulo": quote_item.titulo,
                    "precio": quote_item.precio
                }
                for quote_item in mi_respuesta.items
            ]
            
            mi_respuesta_data = {
                "id": mi_respuesta.id,
                "fecha_creacion": mi_respuesta.fecha_creacion,
                "fecha_respuesta": mi_respuesta.fecha_respuesta,
                "estado": mi_respuesta.estado.value,
                "total": mi_respuesta.total,
                "id_quote_request": mi_respuesta.id_quote_request,
                "id_taller": mi_respuesta.id_taller,
                "items": items_data
            }
        
        formatted_items.append({
            "id": item.id,
            "ubicacion": ubicacion_str,
            "fecha_creacion": item.fecha_creacion,
            "fecha_expiracion": item.fecha_expiracion,
            "comentario": item.comentario,
            "estado": item.estado.value,
            "vehiculo": {
                "id": item.vehiculo.id,
                "placa": item.vehiculo.matricula,
                "marca": item.vehiculo.marca,
                "modelo": item.vehiculo.modelo
            } if item.vehiculo else None,
            "servicio": {
                "id": item.tipo_servicio.id,
                "nombre": item.tipo_servicio.nombre,
                "descripcion": item.tipo_servicio.descripcion
            } if item.tipo_servicio else None,
            "cliente_nombre": item.cliente.nombre if item.cliente else None,
            "ya_respondio": ya_respondio,
            "mi_respuesta": mi_respuesta_data,
            "fotos": item.fotos
        })
    
    return TallerQuoteRequestListResponse(items=formatted_items, total=total, skip=skip, limit=limit)


@router.get("/taller/solicitudes/{request_id}", response_model=TallerQuoteRequestResponse)
async def taller_detalle_solicitud(
    request_id: int,
    current_usuario: Usuario = Depends(require_permiso("cotizacion:revisar")),
    db: AsyncSession = Depends(get_db)
):
    """El taller obtiene el detalle de una solicitud de cotización"""
    from app.models.rol_usuario import RolUsuario
    
    # Obtener el taller del usuario desde sus roles (tomar el primero con taller)
    result = await db.execute(
        select(RolUsuario).where(RolUsuario.id_usuario == current_usuario.id, RolUsuario.id_taller.isnot(None))
    )
    roles_usuario = result.scalars().all()
    
    if not roles_usuario:
        raise HTTPException(status_code=404, detail="Taller no encontrado para el usuario")
    
    # Tomar el primer taller encontrado
    taller_id = roles_usuario[0].id_taller
    
    quote_req = await quote_service.get_taller_quote_detail(db, request_id, taller_id)
    if not quote_req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    from app.services.quote_service import quote_service as qs
    ubicacion_str = qs.format_ubicacion(quote_req.ubicacion)
    
    await db.refresh(quote_req, ["vehiculo", "servicio", "cliente", "responses"])
    
    # Verificar si el taller ya respondió
    from app.crud.crud_quote_response import quote_response as qr_crud
    mi_respuesta = await qr_crud.get_by_taller_and_request(db, taller_id, quote_req.id)
    
    ya_respondio = mi_respuesta and mi_respuesta.estado.value != "pendiente"
    
    # Formatear mi respuesta si existe
    mi_respuesta_data = None
    if mi_respuesta:
        await db.refresh(mi_respuesta, ["items"])
        
        items_data = [
            {
                "id": quote_item.id,
                "titulo": quote_item.titulo,
                "precio": quote_item.precio
            }
            for quote_item in mi_respuesta.items
        ]
        
        mi_respuesta_data = {
            "id": mi_respuesta.id,
            "fecha_creacion": mi_respuesta.fecha_creacion,
            "fecha_respuesta": mi_respuesta.fecha_respuesta,
            "estado": mi_respuesta.estado.value,
            "total": mi_respuesta.total,
            "id_quote_request": mi_respuesta.id_quote_request,
            "id_taller": mi_respuesta.id_taller,
            "items": items_data
        }
    
    response_dict = {
        "id": quote_req.id,
        "ubicacion": ubicacion_str,
        "fecha_creacion": quote_req.fecha_creacion,
        "fecha_expiracion": quote_req.fecha_expiracion,
        "comentario": quote_req.comentario,
        "estado": quote_req.estado.value,
        "vehiculo": {
            "id": quote_req.vehiculo.id,
            "placa": quote_req.vehiculo.matricula,
            "marca": quote_req.vehiculo.marca,
            "modelo": quote_req.vehiculo.modelo
        } if quote_req.vehiculo else None,
        "servicio": {
            "id": quote_req.servicio.id,
            "nombre": quote_req.servicio.nombre,
            "descripcion": quote_req.servicio.descripcion
        } if quote_req.servicio else None,
        "cliente_nombre": quote_req.cliente.nombre if quote_req.cliente else None,
        "ya_respondio": ya_respondio,
        "mi_respuesta": mi_respuesta_data,
        "fotos": quote_req.fotos
    }
    
    return TallerQuoteRequestResponse(**response_dict)


@router.post("/taller/solicitudes/{request_id}/responder", response_model=QuoteResponseResponse)
async def taller_responder_cotizacion(
    request_id: int,
    req: QuoteResponseCreate,
    current_usuario: Usuario = Depends(require_permiso("cotizacion:responder")),
    db: AsyncSession = Depends(get_db)
):
    """El taller responde a una solicitud de cotización"""
    from app.models.rol_usuario import RolUsuario
    
    # Obtener el taller del usuario desde sus roles (tomar el primero con taller)
    result = await db.execute(
        select(RolUsuario).where(RolUsuario.id_usuario == current_usuario.id, RolUsuario.id_taller.isnot(None))
    )
    roles_usuario = result.scalars().all()
    
    if not roles_usuario:
        raise HTTPException(status_code=404, detail="Taller no encontrado para el usuario")
    
    # Tomar el primer taller encontrado
    taller_id = roles_usuario[0].id_taller
    
    try:
        response = await quote_service.respond_quote(db, request_id, req, taller_id)
        
        await db.refresh(response, ["items"])
        
        items_data = [
            {
                "id": quote_item.id,
                "titulo": quote_item.titulo,
                "precio": quote_item.precio
            }
            for quote_item in response.items
        ]
        
        response_dict = {
            "id": response.id,
            "fecha_creacion": response.fecha_creacion,
            "fecha_respuesta": response.fecha_respuesta,
            "estado": response.estado.value,
            "total": response.total,
            "id_quote_request": response.id_quote_request,
            "id_taller": response.id_taller,
            "items": items_data
        }
        
        return QuoteResponseResponse(**response_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint para marcar expiradas (puede ser llamado por un cron job)


@router.post("/admin/marcar-expiradas")
async def marcar_cotizaciones_expiradas(
    _: Usuario = Depends(require_permiso("admin")),
    db: AsyncSession = Depends(get_db)
):
    """Marca las cotizaciones expiradas (para cron job)"""
    expired = await quote_service.mark_expired_quotes(db)
    await db.commit()
    return {"message": f"Se marcaron {len(expired)} cotizaciones como expiradas"}
