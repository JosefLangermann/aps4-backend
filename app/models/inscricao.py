from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Inscricao(Base):
    __tablename__ = "inscricoes"
    # O banco também garante que o participante não se inscreve 2x no mesmo evento
    __table_args__ = (
        UniqueConstraint("evento_id", "participante_id", name="uq_inscricao_evento_participante"),
    )

    id = Column(Integer, primary_key=True, index=True)
    evento_id = Column(Integer, ForeignKey("eventos.id", ondelete="CASCADE"), nullable=False)
    participante_id = Column(Integer, ForeignKey("participantes.id", ondelete="CASCADE"), nullable=False)
    data_inscricao = Column(DateTime, nullable=False, default=datetime.now)

    evento = relationship("Evento", back_populates="inscricoes")
    participante = relationship("Participante", back_populates="inscricoes")
