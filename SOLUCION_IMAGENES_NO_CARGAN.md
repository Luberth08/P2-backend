# 🔧 Solución: Imágenes no cargan en Frontend

## ❌ PROBLEMA

Error en consola:
```
Error loading image:
Image URL: https://backend-repo-2ncr.onrender.com/static/uploads/diagnosticos/38db1a1….jpg
```

## 🔍 CAUSA

Las imágenes se guardaron **localmente** en tu máquina:
```
C:\..\BACKEND-repo\static\uploads\diagnosticos\38db1a1....jpg
```

Pero el `BASE_URL` en tu `.env` apunta a **Render** (producción):
```
BASE_URL="https://backend-repo-2ncr.onrender.com"
```

Cuando el frontend intenta cargar la imagen, hace una petición a:
```
https://backend-repo-2ncr.onrender.com/static/uploads/diagnosticos/...
```

Pero ese archivo **NO existe en Render**, solo existe en tu máquina local.

---

## ✅ SOLUCIÓN 1: Trabajar en Local (DESARROLLO)

### Cambiar BASE_URL a localhost

Edita tu `.env`:

```env
# Desarrollo (DESCOMENTAR)
DATABASE_URL="postgresql+asyncpg://postgres:106347@localhost:5432/ASISTENCIA_VEHICULAR"
SYNC_DATABASE_URL="postgresql://postgres:106347@localhost:5432/ASISTENCIA_VEHICULAR"
BASE_URL="http://localhost:8000"

# Producción (COMENTAR mientras desarrollas)
# DATABASE_URL="postgresql+asyncpg://asistencia_vehicular_db...@dpg-..."
# SYNC_DATABASE_URL="postgresql://asistencia_vehicular_db...@dpg-..."
# BASE_URL="https://backend-repo-2ncr.onrender.com"
```

### Reiniciar el backend

```bash
# Detener el servidor si está corriendo (Ctrl+C)
# Reiniciar
uvicorn app.main:app --reload
```

### Ahora las URLs serán:

```
http://localhost:8000/static/uploads/diagnosticos/38db1a1....jpg
```

Y funcionarán porque los archivos están en tu máquina local.

---

## ✅ SOLUCIÓN 2: Usar Almacenamiento en la Nube (PRODUCCIÓN)

Para que las imágenes funcionen en Render, necesitas guardarlas en un servicio de almacenamiento cloud:

### Opciones de almacenamiento:

#### A. AWS S3 (Más popular)
- Crear bucket S3
- Configurar credenciales AWS
- Usar `boto3` para subir archivos

#### B. Cloudinary (Más fácil)
- Crear cuenta gratis en https://cloudinary.com/
- Subir imágenes vía API
- Obtener URLs públicas

#### C. Render Disk (Limitado)
- Render tiene almacenamiento efímero
- Los archivos se borran en cada deploy
- NO recomendado para archivos persistentes

#### D. Google Cloud Storage
- Similar a S3
- Usar librería `google-cloud-storage`

### Ejemplo con Cloudinary:

```python
# pip install cloudinary
import cloudinary
import cloudinary.uploader

# Configurar
cloudinary.config( 
  cloud_name = "tu_cloud_name", 
  api_key = "tu_api_key", 
  api_secret = "tu_api_secret" 
)

# Subir imagen
result = cloudinary.uploader.upload(file)
url_publica = result['secure_url']
```

---

## ✅ SOLUCIÓN 3: Variables de entorno por ambiente

Crear dos archivos `.env`:

### `.env.local` (desarrollo)
```env
DATABASE_URL="postgresql+asyncpg://postgres:106347@localhost:5432/ASISTENCIA_VEHICULAR"
BASE_URL="http://localhost:8000"
```

### `.env.production` (producción)
```env
DATABASE_URL="postgresql+asyncpg://asistencia_vehicular_db...@dpg-..."
BASE_URL="https://backend-repo-2ncr.onrender.com"
USE_CLOUD_STORAGE=true
CLOUDINARY_CLOUD_NAME="..."
CLOUDINARY_API_KEY="..."
CLOUDINARY_API_SECRET="..."
```

### Modificar el código para usar cloud storage en producción

En `diagnostico_service.py`:

```python
import os
from app.core.config import settings

def _save_file(filename: str, content: bytes) -> str:
    """
    Guarda archivo localmente o en cloud según configuración
    """
    if os.getenv('USE_CLOUD_STORAGE', 'false').lower() == 'true':
        # Subir a Cloudinary
        import cloudinary.uploader
        result = cloudinary.uploader.upload(
            content,
            folder="diagnosticos",
            public_id=filename.split('.')[0]
        )
        return result['secure_url']
    else:
        # Guardar localmente
        dest_path = os.path.join(UPLOAD_DIR, filename)
        with open(dest_path, "wb") as f:
            f.write(content)
        return f"/static/uploads/diagnosticos/{filename}"
```

---

## 🎯 RECOMENDACIÓN PARA TU CASO

### Para DESARROLLO (ahora):

**Usa SOLUCIÓN 1:**
1. Cambia `BASE_URL` a `http://localhost:8000`
2. Reinicia el backend
3. Las imágenes funcionarán localmente

### Para PRODUCCIÓN (después):

**Usa SOLUCIÓN 2:**
1. Configura Cloudinary (es gratis hasta 25GB)
2. Modifica el servicio de diagnóstico para subir a cloud
3. Sube las imágenes existentes a Cloudinary
4. Actualiza los registros en la BD con las nuevas URLs

---

## 📋 COMANDOS PARA SOLUCIÓN 1 (RÁPIDA)

```bash
# 1. Editar .env
# Cambia BASE_URL a http://localhost:8000

# 2. Reiniciar backend
cd "BACKEND-repo"
.venv\Scripts\activate
# Ctrl+C para detener si está corriendo
uvicorn app.main:app --reload

# 3. Reiniciar frontend (si está corriendo)
cd "../FRONTEND-repo"
ng serve

# 4. Probar
# Abre el frontend y ve el detalle de solicitud
# Las imágenes deberían cargar correctamente
```

---

## ⚠️ IMPORTANTE

### ¿Por qué Render no sirve archivos estáticos persistentes?

Render usa **almacenamiento efímero**:
- Cada deploy borra los archivos subidos
- Los archivos solo existen durante la sesión del contenedor
- Si el contenedor se reinicia, los archivos se pierden

### Para producción real necesitas:

1. **Almacenamiento cloud** (S3, Cloudinary, GCS)
2. O un **volumen persistente** (más caro)

---

## 🔍 VERIFICAR DÓNDE ESTÁN LAS IMÁGENES

### En local:

```bash
cd "BACKEND-repo"
dir static\uploads\diagnosticos
```

Deberías ver las imágenes.

### En Render:

No existen, porque Render no las tiene.

---

## 💡 MIGRACIÓN A CLOUDINARY (Opcional)

### 1. Crear cuenta en Cloudinary

https://cloudinary.com/users/register_free

### 2. Obtener credenciales

- Dashboard → Account Details
- Cloud Name
- API Key
- API Secret

### 3. Instalar librería

```bash
pip install cloudinary
```

### 4. Actualizar `.env`

```env
CLOUDINARY_CLOUD_NAME="tu_cloud_name"
CLOUDINARY_API_KEY="tu_api_key"
CLOUDINARY_API_SECRET="tu_api_secret"
USE_CLOUD_STORAGE=true
```

### 5. Modificar servicio de diagnóstico

Ver código de ejemplo arriba.

---

## ✅ RESUMEN

| Escenario | Solución | BASE_URL | Almacenamiento |
|-----------|----------|----------|----------------|
| Desarrollo local | SOLUCIÓN 1 | `http://localhost:8000` | Local (static/) |
| Producción Render | SOLUCIÓN 2 | `https://backend-repo...` | Cloud (Cloudinary/S3) |
| Ambos ambientes | SOLUCIÓN 3 | Variable por ambiente | Condicional |

---

**Para seguir desarrollando ahora: Usa SOLUCIÓN 1 (cambiar BASE_URL a localhost)** 🚀
