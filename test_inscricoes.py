import pytest


def novo_participante(client, n):
    return client.post(
        "/participantes",
        json={"nome": f"Pessoa {n}", "email": f"pessoa{n}@email.com", "curso": "ADS"},
    ).json()


# ---------- testes de endpoint ----------

def test_inscrever_participante(client, evento, participante):
    resposta = client.post(f"/eventos/{evento['id']}/inscricoes/{participante['id']}")
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["evento_id"] == evento["id"]
    assert corpo["participante_id"] == participante["id"]
    assert "data_inscricao" in corpo


def test_listar_inscritos(client, evento, participante):
    client.post(f"/eventos/{evento['id']}/inscricoes/{participante['id']}")
    resposta = client.get(f"/eventos/{evento['id']}/inscricoes")
    assert resposta.status_code == 200
    assert [p["id"] for p in resposta.json()] == [participante["id"]]
    assert "data_inscricao" in resposta.json()[0]


def test_listar_inscritos_evento_sem_inscricoes(client, evento):
    assert client.get(f"/eventos/{evento['id']}/inscricoes").json() == []


def test_listar_inscritos_evento_inexistente(client):
    resposta = client.get("/eventos/99/inscricoes")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Evento não encontrado."}


def test_inscrever_evento_inexistente(client, participante):
    resposta = client.post(f"/eventos/99/inscricoes/{participante['id']}")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Evento não encontrado."}


def test_inscrever_participante_inexistente(client, evento):
    resposta = client.post(f"/eventos/{evento['id']}/inscricoes/99")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Participante não encontrado."}


def test_inscricao_duplicada(client, evento, participante):
    url = f"/eventos/{evento['id']}/inscricoes/{participante['id']}"
    client.post(url)
    resposta = client.post(url)
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "Participante já está inscrito neste evento."}


def test_evento_sem_vagas(client, evento):
    # a capacidade do evento da fixture é 2
    for n in (1, 2):
        p = novo_participante(client, n)
        assert client.post(f"/eventos/{evento['id']}/inscricoes/{p['id']}").status_code == 201
    terceiro = novo_participante(client, 3)
    resposta = client.post(f"/eventos/{evento['id']}/inscricoes/{terceiro['id']}")
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "Não existem vagas disponíveis para este evento."}


def test_excluir_evento_remove_inscricoes(client, evento, participante):
    client.post(f"/eventos/{evento['id']}/inscricoes/{participante['id']}")
    client.delete(f"/eventos/{evento['id']}")
    novo = client.post(
        "/eventos",
        json={
            "titulo": "Outro", "descricao": "d", "data": "2026-12-10", "horario": "10:00",
            "local": "Sala 1", "capacidade": 5, "categoria": "Workshop",
        },
    ).json()
    assert client.get(f"/eventos/{novo['id']}/inscricoes").json() == []


def test_mesmo_participante_em_eventos_diferentes(client, evento, participante, evento_payload):
    segundo = client.post("/eventos", json=evento_payload).json()
    assert client.post(f"/eventos/{evento['id']}/inscricoes/{participante['id']}").status_code == 201
    assert client.post(f"/eventos/{segundo['id']}/inscricoes/{participante['id']}").status_code == 201


def test_id_invalido_na_rota(client):
    assert client.post("/eventos/abc/inscricoes/1").status_code == 422
