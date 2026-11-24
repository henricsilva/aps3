from sqlalchemy import select
from sqlalchemy.orm import Session

from model.participante import Participante
from schema.participante_schema import ParticipanteCreate
from service.exceptions import ConflitoError, NaoEncontradoError, confirmar

MENSAGEM_EMAIL_DUPLICADO = "Já existe um participante cadastrado com este e-mail."


class ParticipanteService:
    """Regras de negócio e persistência de participantes."""

    def __init__(self, db: Session):
        self.db = db

    def _validar_email_unico(self, email: str, ignorar_id: int | None = None) -> None:
        existente = self.db.scalar(select(Participante).where(Participante.email == email))
        if existente is not None and existente.id != ignorar_id:
            raise ConflitoError(MENSAGEM_EMAIL_DUPLICADO)

    def criar(self, dados: ParticipanteCreate) -> Participante:
        self._validar_email_unico(dados.email)
        participante = Participante(**dados.model_dump())
        self.db.add(participante)
        # A restrição UNIQUE do banco é a garantia final (ex.: duas requisições simultâneas).
        confirmar(self.db, MENSAGEM_EMAIL_DUPLICADO)
        return participante

    def listar(self) -> list[Participante]:
        return list(self.db.scalars(select(Participante).order_by(Participante.id)))

    def obter(self, participante_id: int) -> Participante:
        participante = self.db.get(Participante, participante_id)
        if participante is None:
            raise NaoEncontradoError("Participante não encontrado.")
        return participante

    def atualizar(self, participante_id: int, dados: ParticipanteCreate) -> Participante:
        participante = self.obter(participante_id)
        self._validar_email_unico(dados.email, ignorar_id=participante_id)
        for campo, valor in dados.model_dump().items():
            setattr(participante, campo, valor)
        confirmar(self.db, MENSAGEM_EMAIL_DUPLICADO)
        return participante

    def remover(self, participante_id: int) -> None:
        participante = self.obter(participante_id)
        # As inscrições do participante são removidas junto (cascade).
        self.db.delete(participante)
        confirmar(self.db)
