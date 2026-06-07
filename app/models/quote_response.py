from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, DECIMAL, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import enum
from sqlalchemy import Enum as SQLEnum
from datetime import datetime


class EstadoQuoteResponse(str, enum.Enum):
    pendiente = "pendiente"
    respondida = "respondida"
    rechazada = "rechazada"
    expirada = "expirada"


class QuoteResponse(Base):
    __tablename__ = "quote_response"

    id = Column(Integer, primary_key=True, index=True)
    fecha_creacion = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    fecha_respuesta = Column(TIMESTAMP, nullable=True)
    estado = Column(SQLEnum(EstadoQuoteResponse), nullable=False, default=EstadoQuoteResponse.pendiente)
    total = Column(DECIMAL(10, 2), nullable=True)
    id_quote_request = Column(Integer, ForeignKey("quote_request.id", ondelete="CASCADE"), nullable=False)
    id_taller = Column(Integer, ForeignKey("taller.id", ondelete="RESTRICT"), nullable=False)

    # Relaciones
    quote_request = relationship("QuoteRequest", back_populates="responses")
    taller = relationship("Taller", backref="quote_responses")
    items = relationship("QuoteItem", back_populates="quote_response", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint('total >= 0', name='check_total_positivo'),
    )
