# 🔧 Solución a "default cannot be cast automatically"

## ❌ ERROR

```
ERROR: default for column "estado" cannot be cast automatically to type estadoservicio_new
```

## 🔍 CAUSA

La columna `estado` tiene un `DEFAULT 'creado'::estadoservicio` (con el enum antiguo).

Cuando intentas cambiar el tipo de la columna, PostgreSQL no puede convertir automáticamente el DEFAULT del enum antiguo al nuevo.

## ✅ SOLUCIÓN

Quitar el DEFAULT temporalmente, cambiar el tipo, y luego restaurar el DEFAULT con el nuevo enum.

---

## 📋 SQL CORRECTO (COPY-PASTE COMPLETO)

He creado un archivo SQL completo que puedes ejecutar: **`SQL_FIX_ENUM_CORRECTO.sql`**

### Opción A: Ejecutar el archivo SQL

```bash
psql -h localhost -U postgres -d tu_base_datos -f SQL_FIX_ENUM_CORRECTO.sql
```

### Opción B: Copiar y pegar en psql

```bash
psql -h localhost -U postgres -d tu_base_datos
```

Luego copia y pega TODO este bloque:

```sql
-- 1. Crear nuevo ENUM
CREATE TYPE estadoservicio_new AS ENUM (
    'creado',
    'tecnico_asignado',
    'en_camino',
    'en_lugar',
    'en_atencion',
    'finalizado',
    'cancelado'
);

-- 2. Quitar DEFAULT de servicio
ALTER TABLE servicio 
ALTER COLUMN estado DROP DEFAULT;

-- 3. Actualizar tipo en servicio
ALTER TABLE servicio 
ALTER COLUMN estado TYPE estadoservicio_new 
USING (
    CASE estado::text
        WHEN 'en_proceso' THEN 'en_atencion'::estadoservicio_new
        WHEN 'completado' THEN 'finalizado'::estadoservicio_new
        ELSE estado::text::estadoservicio_new
    END
);

-- 4. Restaurar DEFAULT
ALTER TABLE servicio 
ALTER COLUMN estado SET DEFAULT 'creado'::estadoservicio_new;

-- 5. Actualizar historial_estados_servicio (si existe)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'historial_estados_servicio'
    ) THEN
        BEGIN
            ALTER TABLE historial_estados_servicio 
            ALTER COLUMN estado DROP DEFAULT;
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;
        
        ALTER TABLE historial_estados_servicio 
        ALTER COLUMN estado TYPE estadoservicio_new 
        USING (
            CASE estado::text
                WHEN 'en_proceso' THEN 'en_atencion'::estadoservicio_new
                WHEN 'completado' THEN 'finalizado'::estadoservicio_new
                ELSE estado::text::estadoservicio_new
            END
        );
    END IF;
END $$;

-- 6. Eliminar enum antiguo
DROP TYPE estadoservicio;

-- 7. Renombrar
ALTER TYPE estadoservicio_new RENAME TO estadoservicio;

-- 8. Verificar
\dT+ estadoservicio
```

---

## ✅ VERIFICAR QUE FUNCIONÓ

En psql, deberías ver:

```
                  List of enum values
      Type       |    Label
-----------------+----------------
 estadoservicio | creado
 estadoservicio | tecnico_asignado
 estadoservicio | en_camino
 estadoservicio | en_lugar
 estadoservicio | en_atencion
 estadoservicio | finalizado
 estadoservicio | cancelado
```

---

## 🎯 COMANDOS COMPLETOS

```bash
# 1. Ejecutar el SQL
cd "BACKEND-repo"
psql -h localhost -U postgres -d tu_base_datos -f SQL_FIX_ENUM_CORRECTO.sql

# O manualmente:
psql -h localhost -U postgres -d tu_base_datos
# Copiar y pegar el SQL de arriba
\q

# 2. Verificar alembic
.venv\Scripts\activate
alembic current
# Debe mostrar: merge_heads_final (head)

# 3. Iniciar backend
uvicorn app.main:app --reload

# 4. Probar en frontend
# Aceptar una solicitud - ¡debería funcionar!
```

---

## 📊 QUÉ HACE CADA PASO

| Paso | Comando | Propósito |
|------|---------|-----------|
| 1 | CREATE TYPE | Crea el nuevo enum con 7 valores |
| 2 | DROP DEFAULT | Quita el default temporal |
| 3 | ALTER TYPE | Cambia el tipo de la columna |
| 4 | SET DEFAULT | Restaura el default con nuevo enum |
| 5 | DO $$ | Actualiza historial (si existe) |
| 6 | DROP TYPE | Elimina enum antiguo |
| 7 | RENAME | Renombra nuevo enum al original |
| 8 | \dT+ | Verifica los valores |

---

## ⚠️ SI YA EJECUTASTE EL SQL INCORRECTO

Si ya creaste `estadoservicio_new` y falló, primero límpialo:

```sql
DROP TYPE IF EXISTS estadoservicio_new CASCADE;
```

Luego ejecuta el SQL correcto.

---

## 💡 EXPLICACIÓN DEL ERROR

PostgreSQL es estricto con los ENUMs. Cuando una columna tiene:
- Un tipo: `estadoservicio` (antiguo)
- Un DEFAULT: `'creado'::estadoservicio`

Y intentas cambiar el tipo a `estadoservicio_new`, PostgreSQL dice:

> "No puedo convertir automáticamente el DEFAULT del enum antiguo al nuevo"

**Solución:** Quitar el DEFAULT, cambiar tipo, restaurar DEFAULT.

---

**¡Ejecuta el SQL_FIX_ENUM_CORRECTO.sql y todo funcionará!** 🚀
