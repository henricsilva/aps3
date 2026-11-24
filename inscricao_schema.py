from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InscricaoResponse(BaseModel):
    """Inscrição retornada pela API."""

    id: int = Field(description="Identificador da inscrição")
    evento_id: int = Field(description="Identificador do evento")
    participante_id: int = Field(description="Identificador do participante")
    data_inscricao: datetime = Field(description="Data e hora em que a inscrição foi realizada")

    model_config = ConfigDict(from_attributes=True)
