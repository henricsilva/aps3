from datetime import date, time
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Texto obrigatório: remove espaços nas pontas e não aceita vazio.
TextoObrigatorio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Categoria(str, Enum):
    PALESTRA = "Palestra"
    WORKSHOP = "Workshop"
    MINICURSO = "Minicurso"
    SEMINARIO = "Seminário"
    COMPETICAO = "Competição"


class EventoCreate(BaseModel):
    """Dados enviados pelo cliente para cadastrar/atualizar um evento."""

    titulo: TextoObrigatorio = Field(description="Título do evento", examples=["Semana de Tecnologia"])
    descricao: TextoObrigatorio = Field(
        description="Descrição do evento", examples=["Palestras sobre desenvolvimento back-end."]
    )
    data: date = Field(description="Data do evento (AAAA-MM-DD)", examples=["2026-12-05"])
    horario: time = Field(description="Horário de início (HH:MM)", examples=["19:30"])
    local: TextoObrigatorio = Field(description="Local de realização", examples=["Auditório A"])
    capacidade: int = Field(gt=0, description="Número máximo de participantes (maior que zero)", examples=[50])
    categoria: Categoria = Field(description="Categoria do evento")

    model_config = ConfigDict(extra="forbid")


class EventoResponse(EventoCreate):
    """Evento retornado pela API (inclui o id gerado pelo banco)."""

    id: int = Field(description="Identificador do evento")

    model_config = ConfigDict(from_attributes=True)
