# 🔍 Diagnóstico: "No se encontraron talleres cercanos"

## 🚨 Problema

Al solicitar servicio desde el móvil, aparece el mensaje:
> "No se encontraron talleres cercanos con las especialidades requeridas"

---

## 🔬 Ejecutar Script de Diagnóstico

```bash
cd BACKEND-repo
python debug_talleres_no_encontrados.py
```

Cuando te pregunte, ingresa el **ID del diagnóstico** (puedes obtenerlo de la base de datos o desde los logs).

---

## 🎯 Causas Posibles

### 1. **No hay talleres ACTIVOS** ❌

**Síntoma**: `Talleres activos: 0`

**Solución**:
```sql
-- Ver talleres y sus estados
SELECT id, nombre, estado FROM taller;

-- Activar un taller
UPDATE taller SET estado = 'activo' WHERE id = [ID_TALLER];
```

---

### 2. **Talleres no tienen UBICACIÓN** 📍

**Síntoma**: Al listar talleres muestra `Ubicación: NO`

**Solución**:
```sql
-- Ver talleres sin ubicación
SELECT id, nombre, ubicacion FROM taller WHERE ubicacion IS NULL;

-- Agregar ubicación a un taller (ejemplo: Cochabamba, Bolivia)
UPDATE taller 
SET ubicacion = ST_GeogFromText('POINT(-66.1568 -17.3935)')
WHERE id = [ID_TALLER];

-- Coordenadas de ejemplo para Bolivia:
-- Cochabamba: POINT(-66.1568 -17.3935)
-- La Paz: POINT(-68.1193 -16.4897)
-- Santa Cruz: POINT(-63.1812 -17.7833)
```

---

### 3. **Distancia máxima muy PEQUEÑA** 📏

**Síntoma**: `Talleres dentro del rango: 0` pero hay talleres activos con ubicación

**Solución**:
```sql
-- Ver configuración actual
SELECT * FROM configuracion_sistema WHERE clave = 'distancia_maxima_km';

-- Aumentar distancia máxima (ejemplo: 100 km)
UPDATE configuracion_sistema 
SET valor = '100' 
WHERE clave = 'distancia_maxima_km';

-- Si no existe, crear:
INSERT INTO configuracion_sistema (clave, valor, descripcion)
VALUES ('distancia_maxima_km', '100', 'Distancia máxima en km para buscar talleres');
```

---

### 4. **Talleres no tienen TÉCNICOS** 👷

**Síntoma**: `Técnicos totales: 0`

**Solución**:
- Ir al panel web de administración
- Sección "Gestión de Empleados" o "Gestión de Técnicos"
- Crear técnicos para el taller
- Asignar rol "tecnico" al usuario

---

### 5. **Técnicos no tienen ESPECIALIDADES asignadas** 🔧

**Síntoma**: `NO tiene técnicos con las especialidades requeridas`

**Solución**:
- Ir al panel web de administración
- Sección "Gestión de Técnicos"
- Editar técnico
- Asignar especialidades requeridas (ej: Mecánica, Electricidad, etc.)

**Verificar especialidades en BD**:
```sql
-- Ver especialidades del sistema
SELECT * FROM especialidad;

-- Ver qué especialidades tiene cada técnico
SELECT 
    e.id as empleado_id,
    e.nombre || ' ' || e.apellido as tecnico,
    es.nombre as especialidad,
    t.nombre as taller
FROM empleado e
JOIN tecnico_especialidad te ON e.id = te.id_empleado
JOIN especialidad es ON te.id_especialidad = es.id
JOIN taller t ON e.id_taller = t.id;

-- Asignar especialidad a un técnico (manual)
INSERT INTO tecnico_especialidad (id_empleado, id_especialidad)
VALUES ([ID_EMPLEADO], [ID_ESPECIALIDAD]);
```

---

### 6. **Diagnóstico no tiene especialidades REQUERIDAS** ⚠️

**Síntoma**: `NO se encontraron especialidades requeridas`

**Explicación**: El diagnóstico de IA no asignó especialidades automáticamente.

**Solución Temporal**:
```sql
-- Ver especialidades requeridas del diagnóstico
SELECT * FROM tecnico_especialidad WHERE id_diagnostico = [ID_DIAGNOSTICO];

-- Si no hay, asignar manualmente (ejemplo: especialidad genérica)
INSERT INTO tecnico_especialidad (id_diagnostico, id_especialidad, id_empleado)
VALUES ([ID_DIAGNOSTICO], 1, NULL);
-- Nota: id_empleado puede ser NULL si es solo requerimiento
```

**Solución Permanente**: El sistema de IA debería asignar especialidades al generar el diagnóstico.

---

### 7. **Cliente no tiene UBICACIÓN en la solicitud** 📍

**Síntoma**: `ERROR CRÍTICO: La solicitud NO tiene ubicación`

**Solución**:
```sql
-- Ver solicitudes sin ubicación
SELECT id, descripcion, ubicacion 
FROM solicitud_diagnostico 
WHERE ubicacion IS NULL;

-- Asignar ubicación (ejemplo)
UPDATE solicitud_diagnostico 
SET ubicacion = ST_GeogFromText('POINT(-66.1568 -17.3935)')
WHERE id = [ID_SOLICITUD];
```

**Prevención**: Asegurar que la app móvil capture la ubicación GPS correctamente.

---

## 📊 Verificación Rápida (SQL)

Ejecuta estas consultas para ver el estado del sistema:

```sql
-- 1. Talleres activos
SELECT COUNT(*) as talleres_activos FROM taller WHERE estado = 'activo';

-- 2. Talleres con ubicación
SELECT COUNT(*) as con_ubicacion FROM taller WHERE ubicacion IS NOT NULL;

-- 3. Técnicos por taller
SELECT t.nombre, COUNT(e.id) as tecnicos
FROM taller t
LEFT JOIN empleado e ON e.id_taller = t.id
GROUP BY t.id, t.nombre;

-- 4. Técnicos con especialidades
SELECT COUNT(DISTINCT te.id_empleado) as tecnicos_con_especialidades
FROM tecnico_especialidad te;

-- 5. Distancia máxima configurada
SELECT valor FROM configuracion_sistema WHERE clave = 'distancia_maxima_km';
```

---

## 🔧 Solución Rápida (Todos los Problemas)

Si quieres arreglar todo de una vez:

```sql
-- 1. Activar todos los talleres
UPDATE taller SET estado = 'activo';

-- 2. Aumentar distancia máxima
UPDATE configuracion_sistema 
SET valor = '100' 
WHERE clave = 'distancia_maxima_km';

-- 3. Verificar que talleres tienen ubicación (manual)
-- 4. Verificar que técnicos tienen especialidades (manual, desde panel web)
```

---

## 📝 Checklist de Verificación

Después de ejecutar el script de diagnóstico, verifica:

- [ ] Hay al menos 1 taller **activo**
- [ ] Los talleres tienen **ubicación** (lat/lon)
- [ ] La **distancia_maxima_km** es razonable (ej: 50-100 km)
- [ ] Hay **técnicos** asignados a los talleres
- [ ] Los técnicos tienen **especialidades** asignadas
- [ ] El diagnóstico tiene **especialidades requeridas** (o ninguna)
- [ ] La solicitud del cliente tiene **ubicación GPS**

---

## 🎯 Resultado Esperado

Después de arreglar los problemas:

```
✅ RESULTADO: Se encontraron talleres válidos
  - Taller Mecánico Central
  - Auto Service Express
```

Y en el móvil, al solicitar servicio, deberían aparecer los talleres disponibles.

---

## 📞 Comandos Útiles

```bash
# Ejecutar diagnóstico
cd BACKEND-repo
python debug_talleres_no_encontrados.py

# Ver logs del backend
tail -f logs/app.log

# Conectar a BD (local)
psql -U postgres -d ASISTENCIA_VEHICULAR

# Conectar a BD (Render)
# Obtener el string de conexión de Render Dashboard
```

---

**EJECUTA EL SCRIPT Y COMPARTE EL RESULTADO** 🔍

Te dirá exactamente cuál es el problema y cómo solucionarlo.
