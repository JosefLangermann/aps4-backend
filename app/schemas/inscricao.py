from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InscricaoSaida(BaseModel):
    """Registro de vínculo entre um participante e um evento."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    evento_id: int
    participante_id: int
    data_inscricao: datetime
