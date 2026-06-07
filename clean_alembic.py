import asyncio
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://asistencia_vehicular_db_0fqi_user:wFXf1gxboekuFegZlfFsafd5NdhuwrRX@dpg-d8gs4iugvqtc738q9kdg-a.oregon-postgres.render.com/asistencia_vehicular_db_0fqi?sslmode=require')
with engine.connect() as conn:
    conn.execute(text('DELETE FROM alembic_version'))
    conn.commit()
    print('Tabla alembic_version limpiada')
