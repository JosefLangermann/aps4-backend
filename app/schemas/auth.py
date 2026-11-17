from pydantic import BaseModel, Field


class LoginEntrada(BaseModel):
    # e-mail como texto simples de propósito: um formato inválido cai em 401 como
    # qualquer outra credencial errada, sem dar pista nenhuma.
    email: str = Field(..., min_length=1, max_length=150)
    senha: str = Field(..., min_length=1, max_length=128)


class TokenSaida(BaseModel):
    access_token: str
    token_type: str = "bearer"
