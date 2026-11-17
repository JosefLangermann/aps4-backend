from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Participante(Base):
    __tablename__ = "participantes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    curso = Column(String(100), nullable=False)

    # Excluir o participante exclui as inscrições dele junto
    inscricoes = relationship(
        "Inscricao",
        back_populates="participante",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
