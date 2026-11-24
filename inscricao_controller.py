from fastapi import APIRouter, Depends, status

from dependencies import get_inscricao_service
from schema.inscricao_schema import InscricaoResponse
from schema.participante_schema import ParticipanteInscritoResponse
from service.inscricao_service import InscricaoService

router = APIRouter(prefix="/eventos", tags=["Inscrições"])


@router.post(
    "/{evento_id}/inscricoes/{participante_id}",
    response_model=InscricaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inscreve um participante em um evento",
    responses={
        404: {"description": "Evento ou participante não encontrado."},
        409: {"description": "Participante já inscrito ou evento sem vagas."},
    },
)
def inscrever(
    evento_id: int,
    participante_id: int,
    service: InscricaoService = Depends(get_inscricao_service),
):
    return service.inscrever(evento_id, participante_id)


@router.get(
    "/{evento_id}/inscricoes",
    response_model=list[ParticipanteInscritoResponse],
    summary="Lista os participantes inscritos em um evento",
    responses={404: {"description": "Evento não encontrado."}},
)
def listar_inscritos(
    evento_id: int,
    service: InscricaoService = Depends(get_inscricao_service),
):
    return [
        ParticipanteInscritoResponse(
            id=participante.id,
            nome=participante.nome,
            email=participante.email,
            curso=participante.curso,
            data_inscricao=inscricao.data_inscricao,
        )
        for participante, inscricao in service.listar_inscritos(evento_id)
    ]
