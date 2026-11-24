"""Configuração do banco de dados (SQLite + SQLAlchemy).

Responsabilidades deste módulo:
  - configurar a conexão com o SQLite;
  - criar e gerenciar as sessões de acesso;
  - disponibilizar uma sessão para as rotas/serviços (`get_db`);
  - criar as tabelas a partir dos models;
  - encerrar a sessão após o uso.

O arquivo do banco (`eventos.db`) é criado na raiz do projeto. Para usar outro
local, defina a variável de ambiente `EVENTOS_DATABASE_URL`
(ex.: `sqlite:///./outro.db`).
"""

import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("EVENTOS_DATABASE_URL", f"sqlite:///{BASE_DIR / 'eventos.db'}")


class Base(DeclarativeBase):
    """Classe base de todos os models SQLAlchemy."""


def criar_engine(url: str = DATABASE_URL) -> Engine:
    """Cria o engine e ativa as chaves estrangeiras do SQLite.

    O SQLite não valida chaves estrangeiras por padrão; o PRAGMA abaixo garante
    a integridade referencial (inscrição sempre aponta para evento e participante
    existentes) e o funcionamento do ON DELETE CASCADE.
    """
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _ativar_chaves_estrangeiras(conexao, _registro):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = criar_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def criar_tabelas(bind: Engine | None = None) -> None:
    """Cria as tabelas que ainda não existem (não apaga dados existentes)."""
    # Importa os models para que sejam registrados em Base.metadata.
    from model import evento, inscricao, participante  # noqa: F401

    Base.metadata.create_all(bind=bind or engine)


def get_db():
    """Dependência do FastAPI: abre uma sessão por requisição e a fecha ao final."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
