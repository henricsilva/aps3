import pytest


def test_criar_participante(client, participante_payload):
    resposta = client.post("/participantes", json=participante_payload)
    assert resposta.status_code == 201
    assert resposta.json() == {"id": 1, **participante_payload}


def test_listar_participantes(client, participante):
    resposta = client.get("/participantes")
    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


def test_consultar_participante(client, participante):
    resposta = client.get(f"/participantes/{participante['id']}")
    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Maria Silva"


def test_consultar_participante_inexistente(client):
    resposta = client.get("/participantes/99")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Participante não encontrado."}


def test_atualizar_participante(client, participante, participante_payload):
    participante_payload["curso"] = "Ciência da Computação"
    resposta = client.put(f"/participantes/{participante['id']}", json=participante_payload)
    assert resposta.status_code == 200
    assert resposta.json()["curso"] == "Ciência da Computação"


def test_atualizar_mantendo_o_mesmo_email(client, participante, participante_payload):
    resposta = client.put(f"/participantes/{participante['id']}", json=participante_payload)
    assert resposta.status_code == 200


def test_atualizar_participante_inexistente(client, participante_payload):
    assert client.put("/participantes/99", json=participante_payload).status_code == 404


def test_excluir_participante(client, participante):
    assert client.delete(f"/participantes/{participante['id']}").status_code == 204
    assert client.get(f"/participantes/{participante['id']}").status_code == 404


def test_excluir_participante_inexistente(client):
    assert client.delete("/participantes/99").status_code == 404


def test_excluir_participante_libera_vaga(client, evento, participante):
    client.post(f"/eventos/{evento['id']}/inscricoes/{participante['id']}")
    client.delete(f"/participantes/{participante['id']}")
    assert client.get(f"/eventos/{evento['id']}/inscricoes").json() == []


def test_email_duplicado(client, participante, participante_payload):
    resposta = client.post("/participantes", json=participante_payload)
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "Já existe um participante cadastrado com este e-mail."}


def test_atualizar_para_email_de_outro(client, participante):
    outro = client.post(
        "/participantes", json={"nome": "João", "email": "joao@email.com", "curso": "ADS"}
    ).json()
    resposta = client.put(
        f"/participantes/{outro['id']}",
        json={"nome": "João", "email": "maria@email.com", "curso": "ADS"},
    )
    assert resposta.status_code == 409


# ---------- validações ----------

def test_participante_sem_campos(client):
    assert client.post("/participantes", json={}).status_code == 422


@pytest.mark.parametrize("nome", ["", "   "])
def test_nome_vazio(client, participante_payload, nome):
    participante_payload["nome"] = nome
    assert client.post("/participantes", json=participante_payload).status_code == 422


@pytest.mark.parametrize("email", ["semarroba", "a@", "@dominio.com", "texto qualquer"])
def test_email_invalido(client, participante_payload, email):
    participante_payload["email"] = email
    assert client.post("/participantes", json=participante_payload).status_code == 422


def test_curso_vazio(client, participante_payload):
    participante_payload["curso"] = ""
    assert client.post("/participantes", json=participante_payload).status_code == 422
