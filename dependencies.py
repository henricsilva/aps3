"""Injeção de dependência (Depends do FastAPI).

Cada requisição recebe uma sessão do banco (`get_db`, que a fecha ao final) e
a repassa ao Service correspondente. Nos testes, `get_db` é substituída por uma
sessão de um banco temporário via `app.dependency_overrides`.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_db
from service.evento_service import EventoService
from service.inscricao_service import InscricaoService
from service.participante_service import ParticipanteService
from service.relatorio_service import RelatorioService


def get_evento_service(db: Session = Depends(get_db)) -> EventoService:
    return EventoService(db)


def get_participante_service(db: Session = Depends(get_db)) -> ParticipanteService:
    return ParticipanteService(db)


def get_inscricao_service(db: Session = Depends(get_db)) -> InscricaoService:
    return InscricaoService(db)


def get_relatorio_service(db: Session = Depends(get_db)) -> RelatorioService:
    return RelatorioService(db)
