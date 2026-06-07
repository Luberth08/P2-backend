from sqlalchemy import Column, Integer, ForeignKey, String, DECIMAL, CheckConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class QuoteItem(Base):
    __tablename__ = "quote_item"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(200), nullable=False)
    precio = Column(DECIMAL(10, 2), nullable=False)
    id_quote_response = Column(Integer, ForeignKey("quote_response.id", ondelete="CASCADE"), nullable=False)

    # Relaciones
    quote_response = relationship("QuoteResponse", back_populates="items")

    # Constraints
    __table_args__ = (
        CheckConstraint('precio >= 0', name='check_precio_positivo'),
    )
