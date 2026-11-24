from fastapi import APIRouter, Depends, Response, status

from dependencies import get_evento_service
from schema.evento_schema import EventoCreate, EventoResponse
from service.evento_service import EventoService

router = APIRouter(prefix="/eventos", tags=["Eventos"])

NAO_ENCONTRADO = {404: {"description": "Evento não encontrado."}}


@router.post(
    "",
    response_model=EventoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um evento",
)
def criar_evento(evento: EventoCreate, service: EventoService = Depends(get_evento_service)):
    return service.criar(evento)


@router.get("", response_model=list[EventoResponse], summary="Lista todos os eventos")
def listar_eventos(service: EventoService = Depends(get_evento_service)):
    return service.listar()


@router.get(
    "/{evento_id}",
    response_model=EventoResponse,
    summary="Consulta um evento pelo id",
    responses=NAO_ENCONTRADO,
)
def obter_evento(evento_id: int, service: EventoService = Depends(get_evento_service)):
    return service.obter(evento_id)


@router.put(
    "/{evento_id}",
    response_model=EventoResponse,
    summary="Atualiza os dados de um evento",
    responses={
        **NAO_ENCONTRADO,
        409: {"description": "Capacidade menor que o número de inscritos."},
    },
)
def atualizar_evento(
    evento_id: int,
    evento: EventoCreate,
    service: EventoService = Depends(get_evento_service),
):
    return service.atualizar(evento_id, evento)


@router.delete(
    "/{evento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui um evento (e suas inscrições)",
    responses=NAO_ENCONTRADO,
)
def remover_evento(evento_id: int, service: EventoService = Depends(get_evento_service)):
    service.remover(evento_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
