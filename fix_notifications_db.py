"""
Script para verificar y arreglar la tabla dispositivo_usuario
Ejecutar con: python fix_notifications_db.py
"""
import asyncio
import sys
from sqlalchemy import text
from app.db.session import async_session_maker

async def verificar_y_arreglar_tabla():
    """
    Verifica la estructura de la tabla dispositivo_usuario y la arregla si es necesario
    """
    print("🔍 Verificando estructura de la tabla dispositivo_usuario...")
    
    async with async_session_maker() as db:
        try:
            # Verificar si la tabla existe y tiene todas las columnas
            result = await db.execute(
                text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'dispositivo_usuario'
                    ORDER BY ordinal_position
                """)
            )
            
            columnas_actuales = {row[0]: row[1] for row in result}
            
            print(f"\n📋 Columnas actuales en la tabla:")
            for col, tipo in columnas_actuales.items():
                print(f"  - {col}: {tipo}")
            
            # Columnas esperadas
            columnas_esperadas = {
                'id': 'integer',
                'token_fcm': 'text',
                'id_persona': 'integer',
                'plataforma': 'character varying',
                'activo': 'boolean',
                'fecha_registro': 'timestamp without time zone',
                'fecha_ultima_actividad': 'timestamp without time zone'
            }
            
            # Verificar columnas faltantes
            columnas_faltantes = []
            for col in columnas_esperadas:
                if col not in columnas_actuales:
                    columnas_faltantes.append(col)
            
            if not columnas_faltantes:
                print("\n✅ La tabla tiene todas las columnas necesarias!")
                
                # Verificar que hay datos
                result = await db.execute(text("SELECT COUNT(*) FROM dispositivo_usuario"))
                count = result.scalar()
                print(f"\n📊 Total de dispositivos registrados: {count}")
                
                return True
            else:
                print(f"\n❌ Faltan las siguientes columnas:")
                for col in columnas_faltantes:
                    print(f"  - {col}")
                
                print("\n💡 SOLUCIÓN:")
                print("   Ejecuta el siguiente comando en la terminal del backend:")
                print("   alembic upgrade head")
                
                return False
                
        except Exception as e:
            print(f"\n❌ Error al verificar la tabla: {e}")
            print("\n💡 POSIBLES SOLUCIONES:")
            print("   1. Ejecuta: alembic upgrade head")
            print("   2. Si el error persiste, verifica la conexión a la base de datos")
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 VERIFICADOR DE TABLA DISPOSITIVO_USUARIO")
    print("=" * 60)
    
    try:
        result = asyncio.run(verificar_y_arreglar_tabla())
        
        if result:
            print("\n" + "=" * 60)
            print("✅ TODO ESTÁ CORRECTO")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("⚠️  SE REQUIERE ACCIÓN")
            print("=" * 60)
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)
