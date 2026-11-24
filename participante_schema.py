from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from schema.evento_schema import TextoObrigatorio


class ParticipanteCreate(BaseModel):
    """Dados enviados pelo cliente para cadastrar/atualizar um participante."""

    nome: TextoObrigatorio = Field(description="Nome completo do participante", examples=["Maria Silva"])
    email: EmailStr = Field(description="E-mail válido e único do participante", examples=["maria@email.com"])
    curso: TextoObrigatorio = Field(description="Curso do participante", examples=["Engenharia de Software"])

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def email_em_minusculas(cls, valor: str) -> str:
        # Evita duplicidade por diferença de maiúsculas/minúsculas.
        return valor.lower()


class ParticipanteResponse(ParticipanteCreate):
    """Participante retornado pela API (inclui o id gerado pelo banco)."""

    id: int = Field(description="Identificador do participante")

    model_config = ConfigDict(from_attributes=True)


class ParticipanteInscritoResponse(ParticipanteResponse):
    """Participante inscrito em um evento, com a data da inscrição."""

    data_inscricao: datetime = Field(description="Data e hora em que a inscrição foi realizada")
