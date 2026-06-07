from sqlalchemy import Column, Integer, ForeignKey, Text, TIMESTAMP, CheckConstraint, String, ARRAY
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import enum
from sqlalchemy import Enum as SQLEnum
from datetime import datetime


class EstadoQuoteRequest(str, enum.Enum):
    pendiente = "pendiente"
    con_respuesta = "con_respuesta"
    aceptada = "aceptada"
    rechazada = "rechazada"
    expirada = "expirada"


class QuoteRequest(Base):
    __tablename__ = "quote_request"

    id = Column(Integer, primary_key=True, index=True)
    ubicacion = Column(String, nullable=True)
    fecha_creacion = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    fecha_expiracion = Column(TIMESTAMP, nullable=True)
    comentario = Column(Text, nullable=True)
    estado = Column(SQLEnum(EstadoQuoteRequest), nullable=False, default=EstadoQuoteRequest.pendiente)
    fecha_aceptada = Column(TIMESTAMP, nullable=True)
    id_vehiculo = Column(Integer, ForeignKey("vehiculo.id", ondelete="RESTRICT"), nullable=False)
    id_servicio = Column(Integer, ForeignKey("tipo_servicio.id", ondelete="RESTRICT"), nullable=False)
    id_cliente = Column(Integer, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False)
    fotos = Column(ARRAY(String), nullable=True)

    # Relaciones
    vehiculo = relationship("Vehiculo", backref="quote_requests")
    tipo_servicio = relationship("TipoServicio")  # Sin back_populates para evitar error de inicialización circular
    cliente = relationship("Usuario", backref="quote_requests")
    responses = relationship("QuoteResponse", back_populates="quote_request", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('fecha_expiracion > fecha_creacion', name='check_fecha_expiracion_valida'),
    )
