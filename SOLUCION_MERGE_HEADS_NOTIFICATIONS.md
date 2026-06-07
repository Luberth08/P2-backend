# 🔧 Solución a "Can't locate revision 'merge_heads_notifications'"

## ❌ PROBLEMA

Error:
```
ERROR [alembic.util.messaging] Can't locate revision identified by 'merge_heads_notifications'
FAILED: Can't locate revision identified by 'merge_heads_notifications'
```

## 🔍 CAUSA

En la tabla `alembic_version` de tu base de datos hay una referencia a una migración llamada `merge_heads_notifications` que **YA NO EXISTE** en tu carpeta de migraciones.

Esto pasa cuando:
1. Se aplicó una migración
2. Luego el archivo de esa migración fue eliminado del repositorio
3. Alembic intenta buscar esa migración y no la encuentra

## ✅ SOLUCIÓN

Necesitas **limpiar la tabla `alembic_version`** y volver a aplicar las migraciones.

---

## 📋 OPCIÓN 1: Limpiar con Python (RECOMENDADO)

### PASO 1: Ejecutar script de limpieza

```bash
cd "C:\Users\Luberth\Documentos\Avance Academico\7mo Semestre\Sistemas de Informacion II\PRIMER PARCIAL\SOFTWARE\BACKEND-repo"

# Activar entorno virtual
.venv\Scripts\activate

# Ejecutar script de limpieza
python fix_alembic_version.py
```

### PASO 2: Aplicar migraciones desde cero

```bash
# Esto aplicará todas las migraciones
alembic upgrade head
```

---

## 📋 OPCIÓN 2: Limpiar con SQL directamente

### PASO 1: Conectarte a tu base de datos

```bash
# Reemplaza con tu información de conexión
psql -h localhost -U tu_usuario -d tu_base_de_datos
```

### PASO 2: Ver el estado actual

```sql
SELECT * FROM alembic_version;
```

Verás algo como:
```
 version_num 
-------------
 merge_heads_notifications
```

### PASO 3: Limpiar la tabla

```sql
-- CUIDADO: Esto borra TODAS las versiones de alembic
DELETE FROM alembic_version;
```

### PASO 4: Verificar

```sql
SELECT * FROM alembic_version;
-- Debería estar vacía
```

### PASO 5: Salir de psql

```
\q
```

### PASO 6: Aplicar migraciones

```bash
alembic upgrade head
```

---

## 📋 OPCIÓN 3: Stampar manualmente (AVANZADO)

Si conoces la última migración que SÍ está aplicada en tu BD:

```bash
# Ver qué migraciones existen
alembic history

# Stampar a una migración conocida (ejemplo: simplify_empleado_estado)
alembic stamp simplify_empleado_estado

# Luego aplicar las migraciones pendientes
alembic upgrade head
```

---

## 🎯 COMANDOS COMPLETOS (OPCIÓN 1 - RECOMENDADA)

```bash
cd "C:\Users\Luberth\Documentos\Avance Academico\7mo Semestre\Sistemas de Informacion II\PRIMER PARCIAL\SOFTWARE\BACKEND-repo"

.venv\Scripts\activate

python fix_alembic_version.py

alembic upgrade head

alembic current
# Debería mostrar: merge_heads_final (head)
```

---

## 🎯 COMANDOS COMPLETOS (OPCIÓN 2 - SQL)

```bash
# 1. Conectar a la BD
psql -h localhost -U postgres -d nombre_de_tu_bd

# 2. Limpiar
DELETE FROM alembic_version;
\q

# 3. Aplicar migraciones
cd "BACKEND-repo"
.venv\Scripts\activate
alembic upgrade head
```

---

## ⚠️ IMPORTANTE

### ¿Es seguro borrar alembic_version?

✅ **SÍ**, es seguro SOLO SI:
- Estás trabajando en **desarrollo local**
- Tu base de datos puede ser recreada
- O estás dispuesto a rehacer el esquema

❌ **NO** lo hagas en producción sin un backup

### ¿Perderé datos?

❌ **NO** perderás datos en las tablas
✅ Solo se limpia el registro de qué migraciones están aplicadas
✅ Luego Alembic volverá a aplicar las migraciones necesarias

### ¿Qué pasa si mi BD ya tiene el esquema?

Si ya tienes todas las tablas creadas y ejecutas `alembic upgrade head`, puede fallar con errores de "tabla ya existe".

**Solución:**
```bash
# Stampar a la última migración sin ejecutar
alembic stamp head

# Verificar
alembic current
```

---

## 🔍 DIAGNÓSTICO ADICIONAL

### Ver historial de migraciones

```bash
alembic history --verbose
```

### Ver estado actual

```bash
alembic current --verbose
```

### Ver cabezas

```bash
alembic heads
```

---

## 💡 PREVENCIÓN FUTURA

1. **Nunca elimines archivos de migración** del repositorio sin hacer downgrade primero
2. **Usa `alembic downgrade`** antes de eliminar una migración
3. **Mantén sincronizado** tu código con tu base de datos
4. **Haz backup** de `alembic_version` antes de experimentos

---

## 🚨 SI NADA FUNCIONA

### OPCIÓN NUCLEAR: Recrear la base de datos desde cero

```bash
# 1. Backup de datos importantes (si los hay)

# 2. Conectar a PostgreSQL
psql -U postgres

# 3. Eliminar y recrear la base de datos
DROP DATABASE nombre_de_tu_bd;
CREATE DATABASE nombre_de_tu_bd;
\q

# 4. Aplicar todas las migraciones
cd "BACKEND-repo"
.venv\Scripts\activate
alembic upgrade head

# 5. Verificar
alembic current
```

---

## ✅ VERIFICAR QUE FUNCIONÓ

Después de aplicar la solución:

```bash
# 1. Ver migración actual
alembic current
# Debe mostrar: merge_heads_final (head)

# 2. Ver cabezas
alembic heads
# Debe mostrar solo una cabeza

# 3. Probar el backend
# Inicia el servidor y prueba aceptar una solicitud
```

---

## 📚 RESUMEN

1. El problema es una referencia huérfana en `alembic_version`
2. Limpia la tabla con Python (script) o SQL directo
3. Aplica migraciones con `alembic upgrade head`
4. Verifica con `alembic current`

**¡Elige la OPCIÓN 1 (script Python) para la forma más segura!** 🚀
