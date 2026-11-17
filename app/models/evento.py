from sqlalchemy import CheckConstraint, Column, Date, Integer, String, Text, Time
from sqlalchemy.orm import relationship

from app.database import Base


class Evento(Base):
    __tablename__ = "eventos"
    __table_args__ = (CheckConstraint("capacidade > 0", name="ck_evento_capacidade"),)

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(150), nullable=False)
    descricao = Column(Text, nullable=False)
    data = Column(Date, nullable=False)
    horario = Column(Time, nullable=False)
    local = Column(String(150), nullable=False)
    capacidade = Column(Integer, nullable=False)
    categoria = Column(String(50), nullable=False)

    # Excluir o evento exclui as inscrições dele junto (não sobra registro órfão)
    inscricoes = relationship(
        "Inscricao",
        back_populates="evento",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def inscritos_atuais(self) -> int:
        return len(self.inscricoes)
