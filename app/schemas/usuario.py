from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.usuario import Perfil


class UsuarioCadastro(BaseModel):
    """Payload público de cadastro.

    `extra="forbid"`: se alguém tentar mandar "perfil": "administrador" no corpo, a API
    recusa (422). O perfil nunca vem do cliente: todo cadastro público nasce como "usuario".
    """

    model_config = ConfigDict(extra="forbid")

    nome: str = Field(..., min_length=1, max_length=150)
    email: EmailStr
    senha: str = Field(..., min_length=8, max_length=128)

    @field_validator("nome")
    @classmethod
    def nome_sem_branco(cls, valor: str) -> str:
        valor_limpo = valor.strip()
        if not valor_limpo:
            raise ValueError("Este campo não pode ficar em branco.")
        return valor_limpo

    @field_validator("senha")
    @classmethod
    def senha_nao_so_espacos(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("A senha não pode ser formada só por espaços.")
        return valor


class UsuarioSaida(BaseModel):
    """O que a API devolve de um usuário. Não existe campo de senha nem de hash aqui."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    perfil: Perfil


class AlterarPerfil(BaseModel):
    model_config = ConfigDict(extra="forbid")

    perfil: Perfil
