"""Exceções de negócio e de persistência.

O Service não conhece HTTP: ele apenas sinaliza o problema com estas exceções.
A tradução para status HTTP (404, 409, 500) é feita em main.py.
"""

import logging

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger("eventos")


class ErroDeNegocio(Exception):
    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class NaoEncontradoError(ErroDeNegocio):
    """Recurso inexistente (vira 404)."""


class ConflitoError(ErroDeNegocio):
    """Operação em conflito com o estado atual dos dados (vira 409)."""


class ErroPersistenciaError(Exception):
    """Falha ao acessar o banco (vira 500, sem expor detalhes técnicos)."""

    mensagem = "Erro interno ao acessar o banco de dados. Tente novamente mais tarde."


def confirmar(db: Session, mensagem_conflito: str = "A operação viola a integridade dos dados.") -> None:
    """Faz o commit; em caso de erro desfaz a transação e traduz a exceção.

    - IntegrityError (UNIQUE, FOREIGN KEY, CHECK) -> ConflitoError (409)
    - qualquer outro erro do SQLAlchemy         -> ErroPersistenciaError (500)

    O erro técnico original vai apenas para o log do servidor.
    """
    try:
        db.commit()
    except IntegrityError as erro:
        db.rollback()
        logger.warning("Violação de integridade: %s", erro)
        raise ConflitoError(mensagem_conflito) from erro
    except SQLAlchemyError as erro:
        db.rollback()
        logger.exception("Falha de persistência")
        raise ErroPersistenciaError() from erro
