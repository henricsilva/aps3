from fastapi import APIRouter, Depends

from dependencies import get_relatorio_service
from schema.relatorio_schema import (
    EventosPorCategoriaResponse,
    OcupacaoEventoResponse,
    ParticipacaoPorCursoResponse,
)
from service.relatorio_service import RelatorioService

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])


@router.get(
    "/eventos/ocupacao",
    response_model=list[OcupacaoEventoResponse],
    summary="Relatório de ocupação dos eventos",
)
def ocupacao_dos_eventos(service: RelatorioService = Depends(get_relatorio_service)):
    return service.ocupacao_eventos()


@router.get(
    "/eventos/categorias",
    response_model=list[EventosPorCategoriaResponse],
    summary="Relatório de eventos por categoria",
)
def eventos_por_categoria(service: RelatorioService = Depends(get_relatorio_service)):
    return service.eventos_por_categoria()


@router.get(
    "/participantes/cursos",
    response_model=list[ParticipacaoPorCursoResponse],
    summary="Relatório de participação por curso",
)
def participacao_por_curso(service: RelatorioService = Depends(get_relatorio_service)):
    return service.participacao_por_curso()
