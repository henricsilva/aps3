"""Persistência em SQLite, integridade referencial e tratamento de falhas do banco."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

import database
import main
from database import criar_engine, criar_tabelas, get_db
from main import app
from model.evento import Evento
from model.inscricao import Inscricao
from model.participante import Participante
from service.exceptions import (
    ConflitoError,
    ErroPersistenciaError,
    NaoEncontradoError,
    confirmar,
)
from service.inscricao_service import InscricaoService
from service.participante_service import ParticipanteService
from schema.participante_schema import ParticipanteCreate


def novo_evento(**extra):
    base = dict(
        titulo="Evento", descricao="d", data="2026-12-05", horario="10:00",
        local="Sala", capacidade=2, categoria="Palestra",
    )
    base.update(extra)
    from datetime import date, time
    base["data"] = date.fromisoformat(base["data"])
    base["horario"] = time.fromisoformat(base["horario"])
    return Evento(**base)


# ---------- dados sobrevivem ao reinício da aplicação ----------

def test_dados_persistem_apos_reiniciar(tmp_path, evento_payload, participante_payload):
    url = f"sqlite:///{tmp_path / 'persistente.db'}"

    def subir_aplicacao():
        eng = criar_engine(url)
        criar_tabelas(eng)  # o que o lifespan faz ao iniciar: não apaga dados
        fabrica = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)

        def sessao():
            s = fabrica()
            try:
                yield s
            finally:
                s.close()

        app.dependency_overrides[get_db] = sessao
        return eng, TestClient(app)

    # 1ª execução: grava dados
    eng, client = subir_aplicacao()
    evento = client.post("/eventos", json=evento_payload).json()
    participante = client.post("/participantes", json=participante_payload).json()
    client.post(f"/eventos/{evento['id']}/inscricoes/{participante['id']}")
    eng.dispose()  # "encerra" a aplicação

    # 2ª execução: novo engine, mesmo arquivo
    eng, client = subir_aplicacao()
    try:
        assert client.get(f"/eventos/{evento['id']}").json()["titulo"] == evento_payload["titulo"]
        assert client.get("/participantes").json()[0]["email"] == participante_payload["email"]
        inscritos = client.get(f"/eventos/{evento['id']}/inscricoes").json()
        assert [p["id"] for p in inscritos] == [participante["id"]]
        assert client.get("/relatorios/eventos/ocupacao").json()[0]["total_inscritos"] == 1
    finally:
        app.dependency_overrides.clear()
        eng.dispose()


def test_ids_nao_sao_reaproveitados_apos_reinicio(tmp_path, evento_payload):
    url = f"sqlite:///{tmp_path / 'ids.db'}"
    eng = criar_engine(url)
    criar_tabelas(eng)
    with sessionmaker(bind=eng)() as s:
        s.add(novo_evento())
        s.commit()
    eng.dispose()
    eng = criar_engine(url)
    criar_tabelas(eng)
    with sessionmaker(bind=eng)() as s:
        novo = novo_evento()
        s.add(novo)
        s.commit()
        assert novo.id == 2
    eng.dispose()


# ---------- estrutura do banco e integridade ----------

def test_tabelas_criadas_a_partir_dos_models(engine):
    with engine.connect() as con:
        tabelas = {r[0] for r in con.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
    assert {"eventos", "participantes", "inscricoes"} <= tabelas


def test_chaves_estrangeiras_ativas(engine):
    with engine.connect() as con:
        assert con.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_banco_rejeita_inscricao_duplicada(db):
    e, p = novo_evento(), Participante(nome="A", email="a@email.com", curso="X")
    db.add_all([e, p])
    db.commit()
    db.add(Inscricao(evento_id=e.id, participante_id=p.id))
    db.commit()
    db.add(Inscricao(evento_id=e.id, participante_id=p.id))
    with pytest.raises(IntegrityError):
        db.commit()


def test_banco_rejeita_inscricao_com_referencia_inexistente(db):
    db.add(Inscricao(evento_id=999, participante_id=999))
    with pytest.raises(IntegrityError):
        db.commit()


def test_banco_rejeita_email_duplicado(db):
    db.add(Participante(nome="A", email="a@email.com", curso="X"))
    db.commit()
    db.add(Participante(nome="B", email="a@email.com", curso="X"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_banco_rejeita_capacidade_nao_positiva(db):
    db.add(novo_evento(capacidade=0))
    with pytest.raises(IntegrityError):
        db.commit()


def test_relacionamentos_entre_entidades(db):
    e = novo_evento()
    p = Participante(nome="A", email="a@email.com", curso="X")
    db.add_all([e, p])
    db.commit()
    inscricao = Inscricao(evento=e, participante=p)
    db.add(inscricao)
    db.commit()
    assert e.inscricoes == [inscricao]
    assert p.inscricoes == [inscricao]
    assert inscricao.evento is e and inscricao.participante is p
    assert inscricao.data_inscricao is not None


def total(db, modelo):
    return db.scalar(select(func.count()).select_from(modelo))


def test_excluir_evento_remove_inscricoes_sem_orfaos(client, db, evento, participante):
    client.post(f"/eventos/{evento['id']}/inscricoes/{participante['id']}")
    assert total(db, Inscricao) == 1
    assert client.delete(f"/eventos/{evento['id']}").status_code == 204
    assert total(db, Inscricao) == 0
    assert total(db, Participante) == 1  # o participante continua cadastrado


def test_excluir_participante_remove_inscricoes_sem_orfaos(client, db, evento, participante):
    client.post(f"/eventos/{evento['id']}/inscricoes/{participante['id']}")
    assert client.delete(f"/participantes/{participante['id']}").status_code == 204
    assert total(db, Inscricao) == 0
    assert total(db, Evento) == 1  # o evento continua cadastrado


def test_email_unico_ignora_maiusculas(client, participante, participante_payload):
    participante_payload["email"] = "MARIA@Email.com"
    resposta = client.post("/participantes", json=participante_payload)
    assert resposta.status_code == 409


def test_email_e_salvo_em_minusculas(client, participante_payload):
    participante_payload["email"] = "Maria@EMAIL.com"
    assert client.post("/participantes", json=participante_payload).json()["email"] == "maria@email.com"


# ---------- tradução de erros do banco ----------

class SessaoComFalha:
    """Sessão que falha ao confirmar a transação."""

    def __init__(self, erro):
        self.erro = erro
        self.rollbacks = 0

    def commit(self):
        raise self.erro

    def rollback(self):
        self.rollbacks += 1


def test_confirmar_traduz_violacao_de_integridade_em_409():
    sessao = SessaoComFalha(IntegrityError("INSERT ...", {}, Exception("UNIQUE constraint failed")))
    with pytest.raises(ConflitoError) as erro:
        confirmar(sessao, "mensagem amigável")
    assert erro.value.mensagem == "mensagem amigável"
    assert sessao.rollbacks == 1


def test_confirmar_traduz_falha_generica_em_erro_de_persistencia():
    sessao = SessaoComFalha(OperationalError("INSERT ...", {}, Exception("database is locked")))
    with pytest.raises(ErroPersistenciaError):
        confirmar(sessao)
    assert sessao.rollbacks == 1


def test_email_duplicado_detectado_pelo_banco_mesmo_sem_verificacao_previa(db, monkeypatch):
    """Simula duas requisições simultâneas: a checagem prévia não vê o duplicado,
    mas a restrição UNIQUE do banco impede e o erro vira 409 (sem mensagem técnica)."""
    service = ParticipanteService(db)
    service.criar(ParticipanteCreate(nome="A", email="a@email.com", curso="X"))
    monkeypatch.setattr(ParticipanteService, "_validar_email_unico", lambda *a, **k: None)
    with pytest.raises(ConflitoError) as erro:
        service.criar(ParticipanteCreate(nome="B", email="a@email.com", curso="X"))
    assert erro.value.mensagem == "Já existe um participante cadastrado com este e-mail."
    assert "UNIQUE" not in erro.value.mensagem


def test_falha_de_persistencia_retorna_500_sem_detalhes_tecnicos(session_factory, evento_payload):
    class SessaoQueFalha:
        def __init__(self):
            self.real = session_factory()

        def __getattr__(self, nome):
            return getattr(self.real, nome)

        def commit(self):
            raise OperationalError("INSERT INTO eventos", {}, Exception("disk I/O error em /var/db"))

    def sessao():
        s = SessaoQueFalha()
        try:
            yield s
        finally:
            s.real.close()

    app.dependency_overrides[get_db] = sessao
    try:
        resposta = TestClient(app).post("/eventos", json=evento_payload)
    finally:
        app.dependency_overrides.clear()
    assert resposta.status_code == 500
    assert resposta.json() == {"detail": ErroPersistenciaError.mensagem}
    assert "disk" not in resposta.text and "INSERT" not in resposta.text


def test_falha_na_leitura_retorna_500_sem_detalhes_tecnicos(session_factory):
    class SessaoQueFalha:
        def execute(self, *a, **k):
            raise OperationalError("SELECT ... FROM eventos", {}, Exception("no such table: eventos"))

        def close(self):
            pass

    def sessao():
        yield SessaoQueFalha()

    app.dependency_overrides[get_db] = sessao
    try:
        resposta = TestClient(app).get("/relatorios/eventos/ocupacao")
    finally:
        app.dependency_overrides.clear()
    assert resposta.status_code == 500
    assert resposta.json() == {"detail": ErroPersistenciaError.mensagem}
    assert "no such table" not in resposta.text


# ---------- regras de negócio isoladas (Service + sessão, sem HTTP) ----------

@pytest.fixture
def cenario(db):
    e = novo_evento(capacidade=1)
    a = Participante(nome="A", email="a@email.com", curso="X")
    b = Participante(nome="B", email="b@email.com", curso="X")
    db.add_all([e, a, b])
    db.commit()
    return InscricaoService(db), e, a, b


def test_service_inscreve_com_sucesso(cenario):
    service, e, a, _ = cenario
    inscricao = service.inscrever(e.id, a.id)
    assert inscricao.id is not None and inscricao.participante_id == a.id


def test_service_sem_vagas(cenario):
    service, e, a, b = cenario
    service.inscrever(e.id, a.id)
    with pytest.raises(ConflitoError, match="vagas"):
        service.inscrever(e.id, b.id)


def test_service_inscricao_duplicada(cenario):
    service, e, a, _ = cenario
    service.inscrever(e.id, a.id)
    with pytest.raises(ConflitoError, match="já está inscrito"):
        service.inscrever(e.id, a.id)


def test_service_evento_inexistente(cenario):
    service, _, a, _ = cenario
    with pytest.raises(NaoEncontradoError, match="Evento"):
        service.inscrever(999, a.id)


def test_service_participante_inexistente(cenario):
    service, e, _, _ = cenario
    with pytest.raises(NaoEncontradoError, match="Participante"):
        service.inscrever(e.id, 999)


# ---------- configuração ----------

def test_get_db_abre_e_fecha_a_sessao():
    gerador = get_db()
    sessao = next(gerador)
    assert sessao.is_active
    gerador.close()


def test_lifespan_cria_as_tabelas_ao_iniciar(monkeypatch):
    chamadas = []
    monkeypatch.setattr(main, "criar_tabelas", lambda: chamadas.append(1))
    with TestClient(app):
        pass
    assert chamadas == [1]


def test_url_do_banco_aponta_para_arquivo_sqlite():
    assert database.DATABASE_URL.startswith("sqlite:///")
