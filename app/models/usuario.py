import enum

from sqlalchemy import CheckConstraint, Column, Integer, String

from app.database import Base


class Perfil(str, enum.Enum):
    ADMINISTRADOR = "administrador"
    USUARIO = "usuario"


class Usuario(Base):
    """Quem acessa a API (diferente de Participante, que é quem se inscreve nos eventos)."""

    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("perfil IN ('administrador', 'usuario')", name="ck_usuario_perfil"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    senha_hash = Column(String(255), nullable=False)  # só o hash, nunca a senha
    perfil = Column(String(20), nullable=False, default=Perfil.USUARIO.value)
