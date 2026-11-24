import pytest


def test_raiz(client):
    resposta = client.get("/")
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "online"


def test_criar_evento(client, evento_payload):
    resposta = client.post("/eventos", json=evento_payload)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["titulo"] == "Semana de Tecnologia"
    assert corpo["categoria"] == "Palestra"


def test_listar_eventos(client, evento):
    resposta = client.get("/eventos")
    assert resposta.status_code == 200
    assert len(resposta.json()) == 1


def test_listar_eventos_vazio(client):
    assert client.get("/eventos").json() == []


def test_consultar_evento(client, evento):
    resposta = client.get(f"/eventos/{evento['id']}")
    assert resposta.status_code == 200
    assert resposta.json()["titulo"] == "Semana de Tecnologia"


def test_consultar_evento_inexistente(client):
    resposta = client.get("/eventos/99")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Evento não encontrado."}


def test_atualizar_evento(client, evento, evento_payload):
    evento_payload["titulo"] = "Semana de Tecnologia 2"
    evento_payload["capacidade"] = 100
    resposta = client.put(f"/eventos/{evento['id']}", json=evento_payload)
    assert resposta.status_code == 200
    assert resposta.json()["titulo"] == "Semana de Tecnologia 2"
    assert resposta.json()["capacidade"] == 100


def test_atualizar_evento_inexistente(client, evento_payload):
    resposta = client.put("/eventos/99", json=evento_payload)
    assert resposta.status_code == 404


def test_atualizar_capacidade_menor_que_inscritos(client, evento, participante, evento_payload):
    # inscreve 2 participantes (capacidade original = 2)
    outro = {"nome": "João", "email": "joao@email.com", "curso": "ADS"}
    p2 = client.post("/participantes", json=outro).json()
    client.post(f"/eventos/{evento['id']}/inscricoes/{participante['id']}")
    client.post(f"/eventos/{evento['id']}/inscricoes/{p2['id']}")

    # tenta reduzir a capacidade para 1, abaixo do número de inscritos
    evento_payload["capacidade"] = 1
    resposta = client.put(f"/eventos/{evento['id']}", json=evento_payload)
    assert resposta.status_code == 409
    assert "capacidade" in resposta.json()["detail"]


def test_excluir_evento(client, evento):
    resposta = client.delete(f"/eventos/{evento['id']}")
    assert resposta.status_code == 204
    assert client.get(f"/eventos/{evento['id']}").status_code == 404


def test_excluir_evento_inexistente(client):
    assert client.delete("/eventos/99").status_code == 404


# ---------- validações ----------

def test_evento_sem_campos_obrigatorios(client):
    resposta = client.post("/eventos", json={})
    assert resposta.status_code == 422


@pytest.mark.parametrize("titulo", ["", "   "])
def test_titulo_vazio(client, evento_payload, titulo):
    evento_payload["titulo"] = titulo
    assert client.post("/eventos", json=evento_payload).status_code == 422


@pytest.mark.parametrize("capacidade", [0, -5])
def test_capacidade_invalida(client, evento_payload, capacidade):
    evento_payload["capacidade"] = capacidade
    assert client.post("/eventos", json=evento_payload).status_code == 422


def test_capacidade_como_texto(client, evento_payload):
    evento_payload["capacidade"] = "muitas"
    assert client.post("/eventos", json=evento_payload).status_code == 422


def test_data_invalida(client, evento_payload):
    evento_payload["data"] = "2026-13-45"
    assert client.post("/eventos", json=evento_payload).status_code == 422


def test_horario_invalido(client, evento_payload):
    evento_payload["horario"] = "25:99"
    assert client.post("/eventos", json=evento_payload).status_code == 422


def test_categoria_invalida(client, evento_payload):
    evento_payload["categoria"] = "Festa"
    assert client.post("/eventos", json=evento_payload).status_code == 422


def test_campo_extra_rejeitado(client, evento_payload):
    evento_payload["campo_inexistente"] = "x"
    assert client.post("/eventos", json=evento_payload).status_code == 422


def test_erro_422_informa_o_campo(client, evento_payload):
    evento_payload["capacidade"] = 0
    erro = client.post("/eventos", json=evento_payload).json()["detail"][0]
    assert erro["loc"] == ["body", "capacidade"]
