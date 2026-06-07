import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, text
from datetime import datetime, timedelta
import random

from app.db.session import AsyncSessionLocal


async def seed_kpi_data():
    """Genera datos de prueba para el dashboard de KPIs usando SQL directo"""
    
    async with AsyncSessionLocal() as db:
        # Verificar si hay talleres
        result = await db.execute(text("SELECT COUNT(*) FROM taller"))
        count_talleres = result.scalar()
        
        if count_talleres == 0:
            print("No hay talleres en la base de datos. Primero crea talleres.")
            return
        
        # Verificar si hay tipos de incidente
        result = await db.execute(text("SELECT COUNT(*) FROM tipo_incidente"))
        count_tipos = result.scalar()
        
        if count_tipos == 0:
            print("Creando tipos de incidente básicos...")
            await db.execute(text("""
                INSERT INTO tipo_incidente (concepto, prioridad, requiere_remolque) VALUES
                ('Batería', 3, true),
                ('Llanta', 2, false),
                ('Motor', 4, true),
                ('Choque', 5, true),
                ('Otros', 1, false)
            """))
            await db.commit()
        
        # Obtener IDs de talleres
        result = await db.execute(text("SELECT id FROM taller LIMIT 5"))
        taller_ids = [row[0] for row in result.fetchall()]
        
        # Obtener IDs de tipos de incidente
        result = await db.execute(text("SELECT id FROM tipo_incidente"))
        tipo_ids = [row[0] for row in result.fetchall()]
        
        # Obtener IDs de diagnósticos
        result = await db.execute(text("SELECT id FROM diagnostico"))
        diagnostico_ids = [row[0] for row in result.fetchall()]
        
        if not diagnostico_ids:
            print("No hay diagnósticos. Creando diagnósticos básicos...")
            # Crear solicitud_diagnostico primero
            await db.execute(text("""
                INSERT INTO solicitud_diagnostico (descripcion, fecha, id_vehiculo, estado)
                VALUES ('Solicitud de prueba', NOW(), 1, 'completado')
                RETURNING id
            """))
            result = await db.execute(text("SELECT lastval()"))
            sol_diag_id = result.scalar()
            
            # Crear más diagnósticos para evitar conflictos de unicidad
            for i in range(50):
                await db.execute(text("""
                    INSERT INTO diagnostico (descripcion, nivel_confianza, fecha, id_solicitud_diagnostico)
                    VALUES (:desc, :conf, NOW(), :sol_id)
                """), {"desc": f"Diagnóstico {i}", "conf": random.uniform(0.7, 0.99), "sol_id": sol_diag_id})
            await db.commit()
            
            result = await db.execute(text("SELECT id FROM diagnostico"))
            diagnostico_ids = [row[0] for row in result.fetchall()]
        
        print(f"Talleres: {len(taller_ids)}")
        print(f"Tipos de incidente: {len(tipo_ids)}")
        print(f"Diagnósticos: {len(diagnostico_ids)}")
        
        # Generar datos para los últimos 30 días
        fecha_fin = datetime.utcnow()
        fecha_inicio = fecha_fin - timedelta(days=30)
        
        # Para cada taller, generar solicitudes y servicios
        for taller_id in taller_ids:
            print(f"\nGenerando datos para taller ID: {taller_id}")
            
            # Generar entre 20-30 solicitudes por taller
            num_solicitudes = random.randint(20, 30)
            
            for i in range(num_solicitudes):
                # Fecha aleatoria en los últimos 30 días
                fecha_solicitud = fecha_inicio + timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                # Ubicación aleatoria (Lima, Perú)
                lat = -12.0464 + random.uniform(-0.1, 0.1)
                lon = -77.0428 + random.uniform(-0.1, 0.1)
                ubicacion = f"POINT({lon} {lat})"
                
                # Estado aleatorio (mayoría aceptadas)
                estado = random.choice(['aceptada', 'aceptada', 'aceptada', 'cancelada', 'rechazada'])
                
                # Seleccionar diagnóstico aleatorio
                diagnostico_id = random.choice(diagnostico_ids)
                
                # Crear solicitud de servicio
                fecha_aceptada = None
                if estado == 'aceptada':
                    fecha_aceptada = fecha_solicitud + timedelta(minutes=random.randint(5, 30))
                
                result = await db.execute(text("""
                    INSERT INTO solicitud_servicio 
                    (ubicacion, fecha, comentario, estado, fecha_aceptada, costo_estimado, distancia_km, sugerido_por, id_taller, id_diagnostico)
                    VALUES 
                    (ST_GeomFromText(:ubicacion, 4326), :fecha, :comentario, :estado, :fecha_aceptada, :costo, :distancia, :sugerido, :taller_id, :diag_id)
                    ON CONFLICT (id_taller, id_diagnostico) DO NOTHING
                    RETURNING id
                """), {
                    "ubicacion": ubicacion,
                    "fecha": fecha_solicitud,
                    "comentario": f"Solicitud de prueba {i+1}",
                    "estado": estado,
                    "fecha_aceptada": fecha_aceptada,
                    "costo": random.uniform(50, 500),
                    "distancia": random.uniform(1, 50),
                    "sugerido": random.choice(['ia', 'conductor']),
                    "taller_id": taller_id,
                    "diag_id": diagnostico_id
                })
                
                solicitud_row = result.fetchone()
                solicitud_id = solicitud_row[0] if solicitud_row else None
                
                await db.flush()
                
                # Si la solicitud fue aceptada y se insertó correctamente, crear servicio
                if estado == 'aceptada' and solicitud_id:
                    
                    # Estado del servicio
                    estado_servicio = random.choice(['finalizado', 'finalizado', 'finalizado', 'cancelado'])
                    
                    await db.execute(text("""
                        INSERT INTO servicio (fecha, estado, id_taller, id_solicitud_servicio)
                        VALUES (:fecha, :estado, :taller_id, :solicitud_id)
                        RETURNING id
                    """), {
                        "fecha": fecha_solicitud,
                        "estado": estado_servicio,
                        "taller_id": taller_id,
                        "solicitud_id": solicitud_id
                    })
                    
                    result = await db.execute(text("SELECT lastval()"))
                    servicio_id = result.scalar()
                    
                    # Crear historial de estados
                    estados = ['creado', 'tecnico_asignado', 'en_camino', 'en_lugar', 'en_atencion']
                    if estado_servicio == 'finalizado':
                        estados.append('finalizado')
                    else:
                        estados.append('cancelado')
                    
                    tiempo_actual = fecha_solicitud
                    for est in estados:
                        tiempo_actual += timedelta(minutes=random.randint(5, 20))
                        await db.execute(text("""
                            INSERT INTO historial_estados_servicio (estado, tiempo, id_servicio)
                            VALUES (:estado, :tiempo, :servicio_id)
                        """), {"estado": est, "tiempo": tiempo_actual, "servicio_id": servicio_id})
                    
                    # Crear incidentes
                    num_incidentes = random.randint(1, 2)
                    for _ in range(num_incidentes):
                        tipo_id = random.choice(tipo_ids)
                        await db.execute(text("""
                            INSERT INTO incidente (id_diagnostico, id_tipo_incidente, sugerido_por, nivel_confianza)
                            VALUES (:diag_id, :tipo_id, :sugerido, :conf)
                            ON CONFLICT (id_diagnostico, id_tipo_incidente) DO NOTHING
                        """), {
                            "diag_id": diagnostico_id,
                            "tipo_id": tipo_id,
                            "sugerido": random.choice(['ia', 'conductor']),
                            "conf": random.uniform(0.6, 0.99)
                        })
        
        await db.commit()
        print("\n✅ Datos de prueba generados exitosamente")
        print("Ahora puedes probar el dashboard de KPIs")


if __name__ == "__main__":
    asyncio.run(seed_kpi_data())
