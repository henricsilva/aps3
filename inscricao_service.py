from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from model.evento import Evento
from model.inscricao import Inscricao
from model.participante import Participante
from service.exceptions import ConflitoError, NaoEncontradoError, confirmar

MENSAGEM_JA_INSCRITO = "Participante já está inscrito neste evento."
MENSAGEM_SEM_VAGAS = "Não existem vagas disponíveis para este evento."


class InscricaoService:
    """Regras de negócio e persistência das inscrições em eventos."""

    def __init__(self, db: Session):
        self.db = db

    def _exigir_evento(self, evento_id: int) -> Evento:
        evento = self.db.get(Evento, evento_id)
        if evento is None:
            raise NaoEncontradoError("Evento não encontrado.")
        return evento

    def inscrever(self, evento_id: int, participante_id: int) -> Inscricao:
        # 1. O evento existe?
        evento = self._exigir_evento(evento_id)

        # 2. O participante existe?
        if self.db.get(Participante, participante_id) is None:
            raise NaoEncontradoError("Participante não encontrado.")

        # 3. O participante já está inscrito?
        ja_inscrito = self.db.scalar(
            select(Inscricao.id).where(
                Inscricao.evento_id == evento_id,
                Inscricao.participante_id == participante_id,
            )
        )
        if ja_inscrito is not None:
            raise ConflitoError(MENSAGEM_JA_INSCRITO)

        # 4. Existem vagas disponíveis?
        total = self.db.scalar(
            select(func.count(Inscricao.id)).where(Inscricao.evento_id == evento_id)
        )
        if total >= evento.capacidade:
            raise ConflitoError(MENSAGEM_SEM_VAGAS)

        inscricao = Inscricao(evento_id=evento_id, participante_id=participante_id)
        self.db.add(inscricao)
        # A restrição UNIQUE(evento_id, participante_id) impede duplicidade mesmo
        # com requisições simultâneas.
        confirmar(self.db, MENSAGEM_JA_INSCRITO)
        return inscricao

    def listar_inscritos(self, evento_id: int) -> list[tuple[Participante, Inscricao]]:
        """Participantes inscritos no evento (usa o relacionamento Inscricao -> Participante)."""
        self._exigir_evento(evento_id)
        inscricoes = self.db.scalars(
            select(Inscricao)
            .where(Inscricao.evento_id == evento_id)
            .options(joinedload(Inscricao.participante))
            .order_by(Inscricao.id)
        ).all()
        return [(i.participante, i) for i in inscricoes]
