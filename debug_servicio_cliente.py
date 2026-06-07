"""
Script de diagnóstico para verificar por qué el servicio no aparece en el móvil
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from app.core.config import settings
from app.models.servicio import Servicio, EstadoServicio
from app.models.solicitud_servicio import SolicitudServicio
from app.models.diagnostico import Diagnostico
from app.models.solicitud_diagnostico import SolicitudDiagnostico


async def debug_servicio_cliente(id_persona: int):
    """
    Verifica qué servicios tiene un cliente y por qué no aparecen.
    
    Uso: python debug_servicio_cliente.py
    Luego ingresa el id_persona del cliente
    """
    
    # Crear engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        print(f"\n{'='*70}")
        print(f"🔍 DIAGNÓSTICO: Servicios del cliente (id_persona={id_persona})")
        print(f"{'='*70}\n")
        
        # 1. Ver todas las solicitudes de diagnóstico del cliente
        print("📋 PASO 1: Solicitudes de diagnóstico del cliente")
        print("-" * 70)
        result_solicitudes_diag = await db.execute(
            select(SolicitudDiagnostico).where(
                SolicitudDiagnostico.id_persona == id_persona
            ).order_by(SolicitudDiagnostico.fecha.desc())
        )
        solicitudes_diag = result_solicitudes_diag.scalars().all()
        
        if not solicitudes_diag:
            print("❌ No hay solicitudes de diagnóstico para este cliente")
            return
        
        print(f"✅ Encontradas {len(solicitudes_diag)} solicitudes de diagnóstico:\n")
        for sol in solicitudes_diag:
            print(f"  - ID: {sol.id}")
            print(f"    Fecha: {sol.fecha}")
            print(f"    Descripción: {sol.descripcion[:50]}...")
            print()
        
        # 2. Ver diagnósticos asociados
        print("\n📋 PASO 2: Diagnósticos generados")
        print("-" * 70)
        solicitud_diag_ids = [s.id for s in solicitudes_diag]
        result_diagnosticos = await db.execute(
            select(Diagnostico).where(
                Diagnostico.id_solicitud_diagnostico.in_(solicitud_diag_ids)
            )
        )
        diagnosticos = result_diagnosticos.scalars().all()
        
        if not diagnosticos:
            print("❌ No hay diagnósticos para estas solicitudes")
            return
        
        print(f"✅ Encontrados {len(diagnosticos)} diagnósticos:\n")
        for diag in diagnosticos:
            print(f"  - ID: {diag.id}")
            print(f"    Descripción: {diag.descripcion[:50]}...")
            print(f"    Fecha: {diag.fecha}")
            print()
        
        # 3. Ver solicitudes de servicio
        print("\n📋 PASO 3: Solicitudes de servicio")
        print("-" * 70)
        diagnostico_ids = [d.id for d in diagnosticos]
        result_solicitudes_serv = await db.execute(
            select(SolicitudServicio).where(
                SolicitudServicio.id_diagnostico.in_(diagnostico_ids)
            )
        )
        solicitudes_serv = result_solicitudes_serv.scalars().all()
        
        if not solicitudes_serv:
            print("❌ No hay solicitudes de servicio")
            return
        
        print(f"✅ Encontradas {len(solicitudes_serv)} solicitudes de servicio:\n")
        for sol_serv in solicitudes_serv:
            print(f"  - ID: {sol_serv.id}")
            print(f"    Estado: {sol_serv.estado.value}")
            print(f"    Fecha: {sol_serv.fecha}")
            print(f"    Taller ID: {sol_serv.id_taller}")
            print()
        
        # 4. Ver servicios creados
        print("\n📋 PASO 4: Servicios creados")
        print("-" * 70)
        solicitud_serv_ids = [s.id for s in solicitudes_serv]
        result_servicios = await db.execute(
            select(Servicio).where(
                Servicio.id_solicitud_servicio.in_(solicitud_serv_ids)
            ).order_by(Servicio.fecha.desc())
        )
        servicios = result_servicios.scalars().all()
        
        if not servicios:
            print("❌ No hay servicios creados")
            return
        
        print(f"✅ Encontrados {len(servicios)} servicios:\n")
        for serv in servicios:
            print(f"  - ID: {serv.id}")
            print(f"    Estado: {serv.estado.value}")
            print(f"    Fecha: {serv.fecha}")
            print(f"    Solicitud Servicio ID: {serv.id_solicitud_servicio}")
            print()
        
        # 5. Verificar la consulta exacta del endpoint
        print("\n📋 PASO 5: Consulta exacta del endpoint /servicio-actual")
        print("-" * 70)
        result = await db.execute(
            select(Servicio).join(
                SolicitudServicio, Servicio.id_solicitud_servicio == SolicitudServicio.id
            ).join(
                Diagnostico, SolicitudServicio.id_diagnostico == Diagnostico.id
            ).join(
                SolicitudDiagnostico, Diagnostico.id_solicitud_diagnostico == SolicitudDiagnostico.id
            ).where(
                and_(
                    SolicitudDiagnostico.id_persona == id_persona,
                    Servicio.estado.in_([
                        EstadoServicio.creado,
                        EstadoServicio.tecnico_asignado,
                        EstadoServicio.en_camino,
                        EstadoServicio.en_lugar,
                        EstadoServicio.en_atencion
                    ])
                )
            ).order_by(Servicio.fecha.desc())
        )
        
        servicio_actual = result.scalar_one_or_none()
        
        if servicio_actual:
            print(f"✅ SERVICIO ACTIVO ENCONTRADO:")
            print(f"   ID: {servicio_actual.id}")
            print(f"   Estado: {servicio_actual.estado.value}")
            print(f"   Fecha: {servicio_actual.fecha}")
            print(f"   Taller ID: {servicio_actual.id_taller}")
        else:
            print("❌ NO SE ENCONTRÓ SERVICIO ACTIVO")
            print("\n🔍 Posibles razones:")
            print("   1. El estado del servicio no está en la lista de activos")
            print("   2. Hay un problema con los JOINs")
            print("   3. El id_persona no coincide")
        
        # 6. Verificar zonas horarias
        print(f"\n📋 PASO 6: Verificación de fechas/horas")
        print("-" * 70)
        from datetime import datetime, timezone
        print(f"Hora UTC actual: {datetime.now(timezone.utc)}")
        print(f"Hora local del servidor: {datetime.now()}")
        if servicios:
            serv = servicios[0]
            print(f"\nFecha del último servicio en BD: {serv.fecha}")
            print(f"Tipo: {type(serv.fecha)}")
            print(f"Tiene timezone: {serv.fecha.tzinfo}")
    
    await engine.dispose()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  DEBUG: ¿Por qué el servicio no aparece en el móvil del cliente?")
    print("="*70)
    
    # Pedir ID de persona
    try:
        id_persona = int(input("\nIngresa el id_persona del cliente: "))
        asyncio.run(debug_servicio_cliente(id_persona))
    except ValueError:
        print("❌ Error: Debes ingresar un número válido")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("  Diagnóstico completado")
    print("="*70 + "\n")
