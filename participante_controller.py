from fastapi import APIRouter, Depends, Response, status

from dependencies import get_participante_service
from schema.participante_schema import ParticipanteCreate, ParticipanteResponse
from service.participante_service import ParticipanteService

router = APIRouter(prefix="/participantes", tags=["Participantes"])

NAO_ENCONTRADO = {404: {"description": "Participante não encontrado."}}
EMAIL_DUPLICADO = {409: {"description": "E-mail já cadastrado."}}


@router.post(
    "",
    response_model=ParticipanteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um participante",
    responses=EMAIL_DUPLICADO,
)
def criar_participante(
    participante: ParticipanteCreate,
    service: ParticipanteService = Depends(get_participante_service),
):
    return service.criar(participante)


@router.get("", response_model=list[ParticipanteResponse], summary="Lista todos os participantes")
def listar_participantes(service: ParticipanteService = Depends(get_participante_service)):
    return service.listar()


@router.get(
    "/{participante_id}",
    response_model=ParticipanteResponse,
    summary="Consulta um participante pelo id",
    responses=NAO_ENCONTRADO,
)
def obter_participante(
    participante_id: int,
    service: ParticipanteService = Depends(get_participante_service),
):
    return service.obter(participante_id)


@router.put(
    "/{participante_id}",
    response_model=ParticipanteResponse,
    summary="Atualiza os dados de um participante",
    responses={**NAO_ENCONTRADO, **EMAIL_DUPLICADO},
)
def atualizar_participante(
    participante_id: int,
    participante: ParticipanteCreate,
    service: ParticipanteService = Depends(get_participante_service),
):
    return service.atualizar(participante_id, participante)


@router.delete(
    "/{participante_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui um participante (e suas inscrições)",
    responses=NAO_ENCONTRADO,
)
def remover_participante(
    participante_id: int,
    service: ParticipanteService = Depends(get_participante_service),
):
    service.remover(participante_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
