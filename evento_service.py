from sqlalchemy import func, select
from sqlalchemy.orm import Session

from model.evento import Evento
from model.inscricao import Inscricao
from schema.evento_schema import EventoCreate
from service.exceptions import ConflitoError, NaoEncontradoError, confirmar


class EventoService:
    """Regras de negócio e persistência de eventos."""

    def __init__(self, db: Session):
        self.db = db

    def criar(self, dados: EventoCreate) -> Evento:
        evento = Evento(**dados.model_dump(mode="python"))
        self.db.add(evento)
        confirmar(self.db)
        return evento

    def listar(self) -> list[Evento]:
        return list(self.db.scalars(select(Evento).order_by(Evento.id)))

    def obter(self, evento_id: int) -> Evento:
        evento = self.db.get(Evento, evento_id)
        if evento is None:
            raise NaoEncontradoError("Evento não encontrado.")
        return evento

    def atualizar(self, evento_id: int, dados: EventoCreate) -> Evento:
        evento = self.obter(evento_id)
        inscritos = self.db.scalar(
            select(func.count(Inscricao.id)).where(Inscricao.evento_id == evento_id)
        )
        if dados.capacidade < inscritos:
            raise ConflitoError(
                "A nova capacidade não pode ser menor que o número de inscritos."
            )
        for campo, valor in dados.model_dump(mode="python").items():
            setattr(evento, campo, valor)
        confirmar(self.db)
        return evento

    def remover(self, evento_id: int) -> None:
        evento = self.obter(evento_id)
        # As inscrições do evento são removidas junto (cascade): sem registros órfãos.
        self.db.delete(evento)
        confirmar(self.db)
