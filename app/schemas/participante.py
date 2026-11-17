from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ParticipanteEntrada(BaseModel):
    """Payload aceito na criação e edição de um participante."""

    nome: str = Field(..., min_length=1)
    email: EmailStr
    curso: str = Field(..., min_length=1)

    @field_validator("nome", "curso")
    @classmethod
    def sem_campos_em_branco(cls, valor: str) -> str:
        valor_limpo = valor.strip()
        if not valor_limpo:
            raise ValueError("Este campo não pode ficar em branco.")
        return valor_limpo


class ParticipanteSaida(ParticipanteEntrada):
    """Representação de um participante salvo no banco, devolvida pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
