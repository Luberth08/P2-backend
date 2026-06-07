# 🔧 Solución: Fechas/Horas Incorrectas (Timezone)

## ❌ PROBLEMA

Las fechas se muestran incorrectamente:
- **En BD:** `2026-06-05 00:53:02.785572+00` (UTC)
- **Hora real:** `2026-06-04 21:00` (tu zona horaria local)
- **Diferencia:** ~3-4 horas

## 🔍 CAUSA

PostgreSQL guarda las fechas en **UTC (Coordinated Universal Time)** cuando usas `TIMESTAMP WITH TIMEZONE`.

El `+00` significa UTC (hora de Greenwich).

Tu zona horaria parece ser:
- **Bolivia/La Paz:** UTC-4
- **Paraguay:** UTC-4 (verano) o UTC-3 (invierno)
- **Argentina (algunas zonas):** UTC-3

**Diferencia de 3-4 horas** = UTC-4 o UTC-3

---

## ✅ SOLUCIÓN 1: Configurar Timezone en PostgreSQL (Recomendado para Display)

### Opción A: Cambiar timezone de la sesión

En tus queries, puedes convertir a tu timezone:

```sql
-- Ver en tu timezone (Bolivia/La Paz = UTC-4)
SELECT 
    id,
    estado,
    fecha AT TIME ZONE 'America/La_Paz' as fecha_local,
    fecha as fecha_utc
FROM servicio
ORDER BY fecha DESC
LIMIT 5;
```

### Opción B: Configurar timezone por defecto en PostgreSQL

```sql
-- Ver timezone actual
SHOW timezone;

-- Cambiar timezone (temporal, solo para la sesión)
SET timezone = 'America/La_Paz';

-- Ahora las fechas se mostrarán en hora local
SELECT fecha FROM servicio LIMIT 1;
```

### Opción C: Cambiar timezone permanente en postgresql.conf

Esto requiere acceso al servidor (difícil en Render).

---

## ✅ SOLUCIÓN 2: Convertir en el Backend (Mejor práctica)

### En Python (FastAPI)

Modificar cómo se devuelven las fechas en las respuestas:

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Tu zona horaria
LOCAL_TZ = ZoneInfo("America/La_Paz")  # Bolivia

def convert_to_local(dt_utc: datetime) -> datetime:
    """
    Convierte UTC a timezone local
    """
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(LOCAL_TZ)

# En los modelos de respuesta
class ServicioResponse(BaseModel):
    id: int
    fecha: datetime
    
    @validator('fecha')
    def convert_fecha(cls, v):
        return convert_to_local(v)
```

### O configurar FastAPI globalmente

En `app/core/config.py`:

```python
import pytz

# Configuración de timezone
TIMEZONE = pytz.timezone('America/La_Paz')  # O tu timezone
```

---

## ✅ SOLUCIÓN 3: Convertir en el Frontend (Más flexible)

### En Angular

```typescript
// En el servicio
import { formatDate } from '@angular/common';

formatearFecha(fecha: string): string {
  // Angular automáticamente convierte a la timezone del navegador
  return formatDate(fecha, 'dd/MM/yyyy HH:mm', 'es-BO');
}
```

### En Flutter (Móvil)

```dart
import 'package:intl/intl.dart';

String formatearFecha(DateTime fechaUtc) {
  // Convertir a hora local del dispositivo
  final fechaLocal = fechaUtc.toLocal();
  
  // Formatear
  final formatter = DateFormat('dd/MM/yyyy HH:mm');
  return formatter.format(fechaLocal);
}
```

---

## 🎯 RECOMENDACIÓN

### Para tu caso:

**Usa SOLUCIÓN 3 (Convertir en Frontend/Móvil)**

**Ventajas:**
- ✅ Cada usuario ve la fecha en SU timezone
- ✅ No necesitas cambiar el backend
- ✅ Funciona automáticamente
- ✅ Si un usuario está en Bolivia y otro en España, cada uno ve su hora local

**Cómo:**

#### Angular (Frontend Web):

```typescript
// En el HTML
{{ servicio.fecha | date:'dd/MM/yyyy HH:mm':'es-BO' }}

// O en el TypeScript
import { DatePipe } from '@angular/common';

constructor(private datePipe: DatePipe) {}

formatFecha(fecha: string): string {
  return this.datePipe.transform(fecha, 'dd/MM/yyyy HH:mm', 'es-BO') || '';
}
```

#### Flutter (Móvil):

```dart
// Ya debería estar convirtiéndose automáticamente
// Verifica que uses .toLocal()

DateTime fechaLocal = servicio.fecha.toLocal();
print('Hora local: ${DateFormat('dd/MM/yyyy HH:mm').format(fechaLocal)}');
```

---

## 📋 DIAGNÓSTICO: Script de Debug

He creado un script para diagnosticar por qué el servicio no aparece:

### Ejecutar:

```bash
cd "BACKEND-repo"
.venv\Scripts\activate
python debug_servicio_cliente.py
```

Ingresa el `id_persona` del cliente y te mostrará:
1. Todas las solicitudes de diagnóstico
2. Diagnósticos generados
3. Solicitudes de servicio
4. Servicios creados
5. Resultado de la consulta exacta del endpoint
6. Info de timezones

---

## 🔍 VERIFICAR QUE EL SERVICIO SE ENCUENTRA

### SQL para verificar:

```sql
-- Ver todos los servicios con estado activo
SELECT 
    s.id,
    s.estado,
    s.fecha,
    s.id_solicitud_servicio,
    sol.id_diagnostico,
    d.id_solicitud_diagnostico,
    sd.id_persona
FROM servicio s
JOIN solicitud_servicio sol ON s.id_solicitud_servicio = sol.id
JOIN diagnostico d ON sol.id_diagnostico = d.id
JOIN solicitud_diagnostico sd ON d.id_solicitud_diagnostico = sd.id
WHERE s.estado IN ('creado', 'tecnico_asignado', 'en_camino', 'en_lugar', 'en_atencion')
ORDER BY s.fecha DESC;
```

Busca el `id_persona` de tu cliente en los resultados.

---

## ⚠️ NOTAS IMPORTANTES

### ¿Por qué guardar en UTC?

- ✅ Estándar internacional
- ✅ Evita problemas con horario de verano
- ✅ Facilita comparaciones
- ✅ Cada usuario ve su hora local

### ¿Es un problema?

**NO es un error**, es el comportamiento correcto de PostgreSQL.

**Solución:** Convertir a hora local al **mostrar**, no al guardar.

---

## 🎯 ZONAS HORARIAS DE BOLIVIA/PARAGUAY/ARGENTINA

```
Bolivia: America/La_Paz (UTC-4)
Paraguay: America/Asuncion (UTC-4 en verano, UTC-3 en invierno)
Argentina (Buenos Aires): America/Argentina/Buenos_Aires (UTC-3)
Argentina (Salta): America/Argentina/Salta (UTC-3)
```

---

## ✅ RESUMEN DE ACCIONES

### Para el problema de timezone:

1. **Frontend Web:** Usa pipe `| date` de Angular
2. **Móvil:** Usa `.toLocal()` en Dart
3. **BD:** Deja como está (UTC es correcto)

### Para diagnosticar por qué no aparece el servicio:

1. Ejecuta: `python debug_servicio_cliente.py`
2. Ingresa el `id_persona` del cliente
3. Revisa los resultados
4. Si el servicio existe pero no aparece, puede ser:
   - Problema de token/autenticación
   - Usuario equivocado
   - Cache del móvil
   - URL incorrecta del backend en el móvil

---

**¡Ejecuta el script de debug y comparte los resultados!** 🔍
