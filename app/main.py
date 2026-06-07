from fastapi import FastAPI
import os
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api_v1.routers import api_router
from app.api.api_v1.endpoints.websocket import router as websocket_router
from fastapi.staticfiles import StaticFiles

app = FastAPI(title=settings.PROJECT_NAME)

# Configurar CORS (si no lo has hecho)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
app.mount("/static", StaticFiles(directory="static"), name="static")
# Montar directorio de uploads para servir archivos de fotos
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.include_router(api_router, prefix="/api/v1")
# Incluir router de WebSocket (sin prefix porque ya tiene /ws)
app.include_router(websocket_router)

@app.get("/")
@app.head("/")  # Permitir HEAD para health checks de Render
async def root():
    return {"status": "Backend running", "project": settings.PROJECT_NAME}