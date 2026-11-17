from datetime import date, time
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TipoEvento(str, Enum):
    PALESTRA = "Palestra"
    WORKSHOP = "Workshop"
    MINICURSO = "Minicurso"
    SEMINARIO = "Seminário"
    COMPETICAO = "Competição"


class EventoEntrada(BaseModel):
    """Payload aceito tanto na criação quanto na edição de um evento."""

    titulo: str = Field(..., min_length=1)
    descricao: str = Field(..., min_length=1)
    data: date
    horario: time
    local: str = Field(..., min_length=1)
    capacidade: int = Field(..., gt=0)
    categoria: TipoEvento

    @field_validator("titulo", "descricao", "local")
    @classmethod
    def sem_campos_em_branco(cls, valor: str) -> str:
        valor_limpo = valor.strip()
        if not valor_limpo:
            raise ValueError("Este campo não pode ficar em branco.")
        return valor_limpo


class EventoSaida(EventoEntrada):
    """Representação de um evento salvo no banco, devolvida pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    inscritos_atuais: int = 0

    @property
    def vagas_restantes(self) -> int:
        return self.capacidade - self.inscritos_atuais
