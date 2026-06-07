from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class TipoServicio(Base):
    __tablename__ = "tipo_servicio"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False, unique=True)
    descripcion = Column(String(500), nullable=True)

    # Relaciones
    quote_requests = relationship("QuoteRequest", back_populates="servicio")
