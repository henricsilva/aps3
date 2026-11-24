"""Relatórios de consolidação: valores calculados a partir do banco e atualizados
conforme os dados mudam (cenários 9 a 12 do enunciado)."""

import pytest


def criar_evento(client, titulo="Evento", capacidade=10, categoria="Palestra"):
    return client.post(
        "/eventos",
        json={
            "titulo": titulo, "descricao": "d", "data": "2026-12-05", "horario": "10:00",
            "local": "Sala 1", "capacidade": capacidade, "categoria": categoria,
        },
    ).json()


def criar_participante(client, n, curso="ADS"):
    return client.post(
        "/participantes",
        json={"nome": f"Pessoa {n}", "email": f"p{n}@email.com", "curso": curso},
    ).json()


def inscrever(client, evento, participante):
    resposta = client.post(f"/eventos/{evento['id']}/inscricoes/{participante['id']}")
    assert resposta.status_code == 201
    return resposta.json()


def ocupacao(client):
    return client.get("/relatorios/eventos/ocupacao").json()


def por_categoria(client):
    return {l["categoria"]: l for l in client.get("/relatorios/eventos/categorias").json()}


def por_curso(client):
    return {l["curso"]: l for l in client.get("/relatorios/participantes/cursos").json()}


# ---------- banco vazio ----------

@pytest.mark.parametrize(
    "rota",
    ["/relatorios/eventos/ocupacao", "/relatorios/eventos/categorias", "/relatorios/participantes/cursos"],
)
def test_relatorios_sem_registros_retornam_lista_vazia(client, rota):
    resposta = client.get(rota)
    assert resposta.status_code == 200
    assert resposta.json() == []


# ---------- ocupação ----------

def test_ocupacao_evento_sem_inscricoes(client):
    e = criar_evento(client, "Sem inscritos", capacidade=40)
    assert ocupacao(client) == [
        {
            "evento_id": e["id"], "titulo": "Sem inscritos", "capacidade": 40,
            "total_inscritos": 0, "vagas_disponiveis": 40, "percentual_ocupacao": 0.0,
        }
    ]


def test_ocupacao_parcial_e_lotado(client):
    a = criar_evento(client, "Parcial", capacidade=4)
    b = criar_evento(client, "Lotado", capacidade=2)
    p = [criar_participante(client, n) for n in range(1, 4)]
    inscrever(client, a, p[0])
    inscrever(client, b, p[0])
    inscrever(client, b, p[1])
    rel = {l["evento_id"]: l for l in ocupacao(client)}
    assert rel[a["id"]]["total_inscritos"] == 1
    assert rel[a["id"]]["vagas_disponiveis"] == 3
    assert rel[a["id"]]["percentual_ocupacao"] == 25.0
    assert rel[b["id"]]["vagas_disponiveis"] == 0
    assert rel[b["id"]]["percentual_ocupacao"] == 100.0


def test_ocupacao_percentual_arredondado(client):
    e = criar_evento(client, "Terços", capacidade=3)
    inscrever(client, e, criar_participante(client, 1))
    assert ocupacao(client)[0]["percentual_ocupacao"] == 33.33


def test_ocupacao_consistente_com_lista_de_inscritos(client):
    e = criar_evento(client, capacidade=5)
    for n in range(1, 4):
        inscrever(client, e, criar_participante(client, n))
    inscritos = client.get(f"/eventos/{e['id']}/inscricoes").json()
    linha = ocupacao(client)[0]
    assert linha["total_inscritos"] == len(inscritos) == 3
    assert linha["total_inscritos"] + linha["vagas_disponiveis"] == linha["capacidade"]


# ---------- por categoria ----------

def test_categorias_somam_eventos_capacidade_e_inscricoes(client):
    p1, p2 = criar_participante(client, 1), criar_participante(client, 2)
    pal1 = criar_evento(client, "Pal 1", 100, "Palestra")
    pal2 = criar_evento(client, "Pal 2", 50, "Palestra")
    work = criar_evento(client, "Work", 30, "Workshop")
    inscrever(client, pal1, p1)
    inscrever(client, pal1, p2)
    inscrever(client, pal2, p1)
    inscrever(client, work, p2)
    rel = por_categoria(client)
    # a capacidade de pal1 não pode ser somada duas vezes por ter 2 inscrições
    assert rel["Palestra"] == {
        "categoria": "Palestra", "total_eventos": 2, "capacidade_total": 150, "total_inscricoes": 3,
    }
    assert rel["Workshop"] == {
        "categoria": "Workshop", "total_eventos": 1, "capacidade_total": 30, "total_inscricoes": 1,
    }


def test_categoria_com_eventos_sem_inscricoes(client):
    criar_evento(client, "Vazio", 20, "Seminário")
    assert por_categoria(client)["Seminário"]["total_inscricoes"] == 0


# ---------- por curso ----------

def test_curso_nao_conta_participante_duas_vezes(client):
    p = criar_participante(client, 1, curso="Engenharia de Software")
    for n in range(3):
        inscrever(client, criar_evento(client, f"E{n}"), p)
    rel = por_curso(client)["Engenharia de Software"]
    assert rel["total_participantes"] == 1
    assert rel["total_inscricoes"] == 3


def test_curso_com_participante_sem_inscricao(client):
    criar_participante(client, 1, curso="Direito")
    assert por_curso(client)["Direito"] == {
        "curso": "Direito", "total_participantes": 1, "total_inscricoes": 0,
    }


def test_cursos_diferentes_sao_separados(client):
    e = criar_evento(client)
    inscrever(client, e, criar_participante(client, 1, "ADS"))
    inscrever(client, e, criar_participante(client, 2, "ADS"))
    inscrever(client, e, criar_participante(client, 3, "Direito"))
    rel = por_curso(client)
    assert rel["ADS"] == {"curso": "ADS", "total_participantes": 2, "total_inscricoes": 2}
    assert rel["Direito"]["total_inscricoes"] == 1


# ---------- relatórios acompanham as mudanças nos dados ----------

def test_relatorios_atualizam_apos_inserir_atualizar_e_excluir(client):
    evento = criar_evento(client, "Dinâmico", capacidade=10, categoria="Workshop")
    p1 = criar_participante(client, 1, "ADS")
    p2 = criar_participante(client, 2, "ADS")

    # inserir
    inscrever(client, evento, p1)
    inscrever(client, evento, p2)
    assert ocupacao(client)[0]["total_inscritos"] == 2
    assert por_categoria(client)["Workshop"]["total_inscricoes"] == 2
    assert por_curso(client)["ADS"] == {"curso": "ADS", "total_participantes": 2, "total_inscricoes": 2}

    # atualizar o evento (capacidade e categoria) e o curso de um participante
    atual = {
        "titulo": "Dinâmico", "descricao": "d", "data": "2026-12-05", "horario": "10:00",
        "local": "Sala 1", "capacidade": 4, "categoria": "Minicurso",
    }
    assert client.put(f"/eventos/{evento['id']}", json=atual).status_code == 200
    assert ocupacao(client)[0]["percentual_ocupacao"] == 50.0
    rel = por_categoria(client)
    assert "Workshop" not in rel
    assert rel["Minicurso"]["capacidade_total"] == 4

    client.put(
        f"/participantes/{p2['id']}",
        json={"nome": "Pessoa 2", "email": "p2@email.com", "curso": "Direito"},
    )
    rel = por_curso(client)
    assert rel["ADS"]["total_inscricoes"] == 1
    assert rel["Direito"]["total_inscricoes"] == 1

    # excluir participante: inscrições e contagens diminuem
    client.delete(f"/participantes/{p1['id']}")
    assert ocupacao(client)[0]["total_inscritos"] == 1
    assert "ADS" not in por_curso(client)

    # excluir evento: relatórios ficam vazios
    client.delete(f"/eventos/{evento['id']}")
    assert ocupacao(client) == []
    assert client.get("/relatorios/eventos/categorias").json() == []
    assert por_curso(client)["Direito"]["total_inscricoes"] == 0
