from sqlalchemy import Column, Integer, Text, ForeignKey, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base_class import Base

class DispositivoUsuario(Base):
    """
    Modelo para almacenar tokens FCM de dispositivos de usuarios.
    
    Permite gestionar múltiples dispositivos por usuario y rastrear
    el estado y actividad de cada token FCM.
    """
    __tablename__ = "dispositivo_usuario"

    # Atributos principales
    id = Column(Integer, primary_key=True, index=True)
    
    # Token FCM único que identifica el dispositivo en Firebase
    token_fcm = Column(Text, nullable=False, unique=True, index=True)
    
    # Referencia al usuario propietario del dispositivo
    id_persona = Column(Integer, ForeignKey("persona.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Plataforma del dispositivo: 'android', 'ios', 'web'
    plataforma = Column(String(20), nullable=True)
    
    # Indica si el token está activo (True) o fue desregistrado (False)
    activo = Column(Boolean, default=True, nullable=False, index=True)
    
    # Fecha y hora de registro inicial del token
    fecha_registro = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Fecha y hora de la última actividad del token (actualizado en cada registro)
    fecha_ultima_actividad = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relaciones
    persona = relationship("Persona", back_populates="dispositivos")