import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

# Permite importar main, model, service... a partir da raiz do projeto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import criar_engine, criar_tabelas, get_db  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture
def engine(tmp_path):
    """Banco SQLite temporário (um arquivo novo por teste)."""
    eng = criar_engine(f"sqlite:///{tmp_path / 'teste.db'}")
    criar_tabelas(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory):
    sessao = session_factory()
    yield sessao
    sessao.close()


@pytest.fixture
def client(session_factory):
    def sessao_de_teste():
        sessao = session_factory()
        try:
            yield sessao
        finally:
            sessao.close()

    app.dependency_overrides[get_db] = sessao_de_teste
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def evento_payload():
    return {
        "titulo": "Semana de Tecnologia",
        "descricao": "Palestras sobre desenvolvimento back-end.",
        "data": "2026-12-05",
        "horario": "19:30",
        "local": "Auditório A",
        "capacidade": 2,
        "categoria": "Palestra",
    }


@pytest.fixture
def participante_payload():
    return {"nome": "Maria Silva", "email": "maria@email.com", "curso": "Engenharia de Software"}


@pytest.fixture
def evento(client, evento_payload):
    return client.post("/eventos", json=evento_payload).json()


@pytest.fixture
def participante(client, participante_payload):
    return client.post("/participantes", json=participante_payload).json()
