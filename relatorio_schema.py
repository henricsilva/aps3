from pydantic import BaseModel, Field


class OcupacaoEventoResponse(BaseModel):
    evento_id: int
    titulo: str
    capacidade: int = Field(description="Capacidade total do evento")
    total_inscritos: int = Field(description="Quantidade de inscritos")
    vagas_disponiveis: int = Field(description="Vagas restantes (capacidade - inscritos)")
    percentual_ocupacao: float = Field(description="inscritos / capacidade * 100")


class EventosPorCategoriaResponse(BaseModel):
    categoria: str
    total_eventos: int = Field(description="Quantidade de eventos da categoria")
    capacidade_total: int = Field(description="Soma das capacidades dos eventos da categoria")
    total_inscricoes: int = Field(description="Inscrições nos eventos da categoria")


class ParticipacaoPorCursoResponse(BaseModel):
    curso: str
    total_participantes: int = Field(description="Participantes cadastrados no curso (sem repetição)")
    total_inscricoes: int = Field(description="Inscrições realizadas por participantes do curso")
