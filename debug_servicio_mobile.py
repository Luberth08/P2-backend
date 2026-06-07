"""
Script de diagnóstico: ¿Por qué el servicio no aparece en móvil?
Verifica cada paso del flujo y muestra información detallada.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_, func
from app.models.solicitud_diagnostico import SolicitudDiagnostico
from app.models.diagnostico import Diagnostico
from app.models.solicitud_servicio import SolicitudServicio
from app.models.servicio import Servicio, EstadoServicio
from app.models.taller import Taller
from app.core.config import settings

# Conectar a la base de datos
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def diagnosticar_servicio_mobile(id_persona_cliente: int):
    print("=" * 70)
    print("🔍 DIAGNÓSTICO: ¿Por qué el servicio NO aparece en móvil?")
    print("=" * 70)
    print(f"Cliente id_persona: {id_persona_cliente}")
    print()
    
    async with AsyncSessionLocal() as db:
        # PASO 1: Verificar solicitudes de diagnóstico
        print("📋 PASO 1: Solicitudes de diagnóstico del cliente")
        print("-" * 70)
        result = await db.execute(
            select(SolicitudDiagnostico)
            .where(SolicitudDiagnostico.id_persona == id_persona_cliente)
            .order_by(SolicitudDiagnostico.fecha_creacion.desc())
        )
        solicitudes = result.scalars().all()
        
        if not solicitudes:
            print("❌ NO hay solicitudes de diagnóstico para este cliente")
            return
        
        print(f"✅ Encontradas {len(solicitudes)} solicitudes:")
        for sol in solicitudes[:3]:  # Mostrar últimas 3
            print(f"  - ID: {sol.id}")
            print(f"    Fecha: {sol.fecha_creacion}")
            print(f"    Estado: {sol.estado}")
            print()
        
        # PASO 2: Verificar diagnósticos generados
        print("📋 PASO 2: Diagnósticos generados")
        print("-" * 70)
        result = await db.execute(
            select(Diagnostico)
            .where(Diagnostico.id_solicitud_diagnostico.in_([s.id for s in solicitudes]))
            .order_by(Diagnostico.fecha.desc())
        )
        diagnosticos = result.scalars().all()
        
        if not diagnosticos:
            print("❌ NO hay diagnósticos generados")
            return
        
        print(f"✅ Encontrados {len(diagnosticos)} diagnósticos:")
        for diag in diagnosticos[:3]:
            print(f"  - ID: {diag.id}")
            print(f"    Solicitud ID: {diag.id_solicitud_diagnostico}")
            print(f"    Fecha: {diag.fecha}")
            print()
        
        # PASO 3: Verificar solicitudes de servicio
        print("📋 PASO 3: Solicitudes de servicio")
        print("-" * 70)
        result = await db.execute(
            select(SolicitudServicio)
            .where(SolicitudServicio.id_diagnostico.in_([d.id for d in diagnosticos]))
            .order_by(SolicitudServicio.fecha.desc())
        )
        solicitudes_servicio = result.scalars().all()
        
        if not solicitudes_servicio:
            print("❌ NO hay solicitudes de servicio")
            return
        
        print(f"✅ Encontradas {len(solicitudes_servicio)} solicitudes de servicio:")
        for sol in solicitudes_servicio[:5]:
            print(f"  - ID: {sol.id}")
            print(f"    Estado: {sol.estado}")
            print(f"    Diagnóstico ID: {sol.id_diagnostico}")
            print(f"    Taller ID: {sol.id_taller}")
            print()
        
        # PASO 4: Verificar servicios creados
        print("📋 PASO 4: Servicios creados")
        print("-" * 70)
        result = await db.execute(
            select(Servicio)
            .where(Servicio.id_solicitud_servicio.in_([s.id for s in solicitudes_servicio]))
            .order_by(Servicio.fecha.desc())
        )
        servicios = result.scalars().all()
        
        if not servicios:
            print("❌ NO hay servicios creados")
            return
        
        print(f"✅ Encontrados {len(servicios)} servicios:")
        for serv in servicios:
            print(f"  - ID: {serv.id}")
            print(f"    Estado: {serv.estado}")
            print(f"    Estado (valor): {serv.estado.value if hasattr(serv.estado, 'value') else serv.estado}")
            print(f"    Fecha: {serv.fecha}")
            print(f"    Solicitud Servicio ID: {serv.id_solicitud_servicio}")
            print()
        
        # PASO 5: Verificar qué considera el endpoint como "activo"
        print("📋 PASO 5: ¿Cuáles servicios son considerados ACTIVOS?")
        print("-" * 70)
        estados_activos = [
            EstadoServicio.creado,
            EstadoServicio.tecnico_asignado,
            EstadoServicio.en_camino,
            EstadoServicio.en_lugar,
            EstadoServicio.en_atencion
        ]
        
        print("Estados considerados ACTIVOS por el endpoint:")
        for estado in estados_activos:
            print(f"  - {estado.value}")
        print()
        
        # PASO 6: Ejecutar la query exacta del endpoint
        print("📋 PASO 6: Query EXACTA del endpoint /servicio-actual")
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
                    SolicitudDiagnostico.id_persona == id_persona_cliente,
                    Servicio.estado.in_(estados_activos)
                )
            ).order_by(Servicio.fecha.desc())
        )
        
        servicio_activo = result.scalar_one_or_none()
        
        if servicio_activo:
            print("✅ SERVICIO ACTIVO ENCONTRADO:")
            print(f"  ID: {servicio_activo.id}")
            print(f"  Estado: {servicio_activo.estado}")
            print(f"  Estado (valor): {servicio_activo.estado.value if hasattr(servicio_activo.estado, 'value') else servicio_activo.estado}")
            print(f"  Fecha: {servicio_activo.fecha}")
            print()
            
            # Obtener info del taller
            result_taller = await db.execute(
                select(Taller).where(Taller.id == servicio_activo.id_taller)
            )
            taller = result_taller.scalar_one_or_none()
            if taller:
                print(f"  Taller: {taller.nombre} (ID: {taller.id})")
            print()
        else:
            print("❌ NO SE ENCONTRÓ SERVICIO ACTIVO")
            print()
            print("🔍 Análisis de por qué NO se encontró:")
            print()
            
            # Verificar cada servicio individualmente
            for serv in servicios:
                print(f"Servicio ID {serv.id}:")
                
                # Verificar estado
                estado_str = serv.estado.value if hasattr(serv.estado, 'value') else str(serv.estado)
                estado_activo = serv.estado in estados_activos
                
                print(f"  Estado actual: {estado_str}")
                print(f"  ¿Es estado activo?: {'✅ SÍ' if estado_activo else '❌ NO'}")
                
                if not estado_activo:
                    print(f"  ⚠️ PROBLEMA: Estado '{estado_str}' NO está en la lista de estados activos")
                    print(f"     Estados activos permitidos:")
                    for est in estados_activos:
                        print(f"       - {est.value}")
                
                # Verificar joins
                result_check = await db.execute(
                    select(SolicitudServicio).where(SolicitudServicio.id == serv.id_solicitud_servicio)
                )
                sol_serv = result_check.scalar_one_or_none()
                
                if sol_serv:
                    print(f"  ✅ Solicitud Servicio encontrada (ID: {sol_serv.id})")
                    
                    result_diag = await db.execute(
                        select(Diagnostico).where(Diagnostico.id == sol_serv.id_diagnostico)
                    )
                    diag = result_diag.scalar_one_or_none()
                    
                    if diag:
                        print(f"  ✅ Diagnóstico encontrado (ID: {diag.id})")
                        
                        result_sol_diag = await db.execute(
                            select(SolicitudDiagnostico).where(
                                SolicitudDiagnostico.id == diag.id_solicitud_diagnostico
                            )
                        )
                        sol_diag = result_sol_diag.scalar_one_or_none()
                        
                        if sol_diag:
                            print(f"  ✅ Solicitud Diagnóstico encontrada (ID: {sol_diag.id})")
                            print(f"  Cliente id_persona: {sol_diag.id_persona}")
                            
                            if sol_diag.id_persona == id_persona_cliente:
                                print(f"  ✅ Cliente coincide")
                            else:
                                print(f"  ❌ Cliente NO coincide (esperado: {id_persona_cliente})")
                        else:
                            print(f"  ❌ Solicitud Diagnóstico NO encontrada")
                    else:
                        print(f"  ❌ Diagnóstico NO encontrado")
                else:
                    print(f"  ❌ Solicitud Servicio NO encontrada")
                
                print()
        
        # PASO 7: Verificar estados del enum
        print("📋 PASO 7: Verificar valores del enum EstadoServicio")
        print("-" * 70)
        print("Valores del enum en el código:")
        for estado in EstadoServicio:
            print(f"  - {estado.value}")
        print()
        
        # Verificar tipos de datos en BD
        print("📋 PASO 8: Verificar tipos de datos en BD")
        print("-" * 70)
        if servicios:
            serv = servicios[0]
            print(f"Tipo de serv.estado: {type(serv.estado)}")
            print(f"Valor de serv.estado: {serv.estado}")
            if hasattr(serv.estado, 'value'):
                print(f"serv.estado.value: {serv.estado.value}")
            print()
        
        print("=" * 70)
        print("Diagnóstico completado")
        print("=" * 70)

if __name__ == "__main__":
    id_persona = int(input("Ingresa el id_persona del cliente: "))
    asyncio.run(diagnosticar_servicio_mobile(id_persona))
