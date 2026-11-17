import os
import sqlite3

EVENTO = {
    "titulo": "Workshop de Python", "descricao": "Introdução à linguagem", "data": "2026-12-10",
    "horario": "19:30", "local": "Lab 3", "capacidade": 2, "categoria": "Workshop",
}


def novo_evento(client, **extra):
    r = client.post("/eventos", json={**EVENTO, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def novo_participante(client, nome="Ana", email="ana@exemplo.com", curso="Engenharia de Software"):
    r = client.post("/participantes", json={"nome": nome, "email": email, "curso": curso})
    assert r.status_code == 201, r.text
    return r.json()


def test_status_da_api(client):
    assert client.get("/").json()["status"] == "online"


# 1 - cadastro e consulta de eventos
def test_cadastro_e_consulta_de_eventos(client):
    ev = novo_evento(client)
    assert ev["inscritos_atuais"] == 0
    assert client.get(f"/eventos/{ev['id']}").json()["titulo"] == "Workshop de Python"
    assert len(client.get("/eventos").json()) == 1


# 2 - cadastro e consulta de participantes
def test_cadastro_e_consulta_de_participantes(client):
    p = novo_participante(client)
    assert client.get(f"/participantes/{p['id']}").json()["email"] == "ana@exemplo.com"
    assert len(client.get("/participantes").json()) == 1


# 3 - atualização e exclusão
def test_atualizar_e_excluir(client):
    ev = novo_evento(client)
    r = client.put(f"/eventos/{ev['id']}", json={**EVENTO, "titulo": "Novo título"})
    assert r.json()["titulo"] == "Novo título"
    assert client.delete(f"/eventos/{ev['id']}").status_code == 204
    assert client.get(f"/eventos/{ev['id']}").status_code == 404

    p = novo_participante(client)
    r = client.put(f"/participantes/{p['id']}", json={"nome": "Ana Maria", "email": "ana@exemplo.com", "curso": "ADS"})
    assert r.json()["nome"] == "Ana Maria"
    assert client.delete(f"/participantes/{p['id']}").status_code == 204
    assert client.get(f"/participantes/{p['id']}").status_code == 404


# 4 - inscrição
def test_inscricao(client):
    ev, p = novo_evento(client), novo_participante(client)
    r = client.post(f"/eventos/{ev['id']}/inscricoes/{p['id']}")
    assert r.status_code == 201
    assert r.json()["evento_id"] == ev["id"] and "data_inscricao" in r.json()
    inscritos = client.get(f"/eventos/{ev['id']}/inscricoes").json()
    assert len(inscritos) == 1 and inscritos[0]["nome"] == "Ana"
    assert client.get(f"/eventos/{ev['id']}").json()["inscritos_atuais"] == 1


# 5 - inscrição duplicada
def test_inscricao_duplicada(client):
    ev, p = novo_evento(client), novo_participante(client)
    client.post(f"/eventos/{ev['id']}/inscricoes/{p['id']}")
    r = client.post(f"/eventos/{ev['id']}/inscricoes/{p['id']}")
    assert r.status_code == 409
    assert r.json()["detail"] == "Participante já está inscrito neste evento."


# 6 - evento / participante inexistente
def test_inscricao_inexistentes(client):
    p = novo_participante(client)
    r = client.post(f"/eventos/999/inscricoes/{p['id']}")
    assert r.status_code == 404 and r.json()["detail"] == "Evento não encontrado."
    ev = novo_evento(client)
    r = client.post(f"/eventos/{ev['id']}/inscricoes/999")
    assert r.status_code == 404 and r.json()["detail"] == "Participante não encontrado."


# 7 - sem vagas
def test_inscricao_sem_vagas(client):
    ev = novo_evento(client, capacidade=1)
    p1 = novo_participante(client, email="a@x.com")
    p2 = novo_participante(client, nome="Bia", email="b@x.com")
    assert client.post(f"/eventos/{ev['id']}/inscricoes/{p1['id']}").status_code == 201
    r = client.post(f"/eventos/{ev['id']}/inscricoes/{p2['id']}")
    assert r.status_code == 409
    assert r.json()["detail"] == "Não existem vagas disponíveis para este evento."


# e-mail duplicado e validações
def test_email_duplicado_e_validacoes(client):
    novo_participante(client)
    r = client.post("/participantes", json={"nome": "Outra", "email": "ANA@exemplo.com", "curso": "ADS"})
    assert r.status_code == 409
    assert r.json()["detail"] == "Já existe um participante cadastrado com este e-mail."

    assert client.post("/participantes", json={"nome": "X", "email": "invalido", "curso": "ADS"}).status_code == 422
    assert client.post("/participantes", json={"nome": "  ", "email": "x@x.com", "curso": "ADS"}).status_code == 422
    assert client.post("/eventos", json={**EVENTO, "titulo": " "}).status_code == 422
    assert client.post("/eventos", json={**EVENTO, "capacidade": 0}).status_code == 422
    assert client.post("/eventos", json={**EVENTO, "categoria": "Festa"}).status_code == 422
    assert client.post("/eventos", json={**EVENTO, "data": "2026-13-45"}).status_code == 422
    assert client.post("/eventos", json={**EVENTO, "horario": "25:99"}).status_code == 422
    sem_local = {k: v for k, v in EVENTO.items() if k != "local"}
    assert client.post("/eventos", json=sem_local).status_code == 422


# 8 - persistência (lê direto do arquivo SQLite, fora da API)
def test_persistencia_no_arquivo(client):
    novo_evento(client)
    novo_participante(client)
    caminho = os.environ["DATABASE_URL"].replace("sqlite:///", "")
    con = sqlite3.connect(caminho)
    assert con.execute("select count(*) from eventos").fetchone()[0] == 1
    assert con.execute("select count(*) from participantes").fetchone()[0] == 1
    con.close()


# 9, 10, 11, 12 - relatórios e atualização conforme os dados mudam
def test_relatorios(client):
    assert client.get("/relatorios/eventos/ocupacao").json() == []
    assert client.get("/relatorios/eventos/categorias").json() == []
    assert client.get("/relatorios/participantes/cursos").json() == []

    e1 = novo_evento(client, titulo="IA", capacidade=4, categoria="Palestra")
    e2 = novo_evento(client, titulo="Python", capacidade=2, categoria="Workshop")
    novo_evento(client, titulo="Sem inscritos", capacidade=10, categoria="Palestra")
    a = novo_participante(client, nome="Ana", email="a@x.com", curso="ES")
    b = novo_participante(client, nome="Bia", email="b@x.com", curso="ES")
    c = novo_participante(client, nome="Caio", email="c@x.com", curso="ADS")

    for ev, p in [(e1, a), (e1, b), (e1, c), (e2, a), (e2, b)]:
        client.post(f"/eventos/{ev['id']}/inscricoes/{p['id']}")

    ocup = {r["titulo"]: r for r in client.get("/relatorios/eventos/ocupacao").json()}
    assert ocup["IA"]["total_inscritos"] == 3 and ocup["IA"]["vagas_disponiveis"] == 1
    assert ocup["IA"]["percentual_ocupacao"] == 75.0
    assert ocup["Python"]["percentual_ocupacao"] == 100.0 and ocup["Python"]["vagas_disponiveis"] == 0
    assert ocup["Sem inscritos"]["total_inscritos"] == 0 and ocup["Sem inscritos"]["percentual_ocupacao"] == 0.0

    cats = {r["categoria"]: r for r in client.get("/relatorios/eventos/categorias").json()}
    assert cats["Palestra"] == {"categoria": "Palestra", "total_eventos": 2, "capacidade_total": 14, "total_inscricoes": 3}
    assert cats["Workshop"] == {"categoria": "Workshop", "total_eventos": 1, "capacidade_total": 2, "total_inscricoes": 2}

    cursos = {r["curso"]: r for r in client.get("/relatorios/participantes/cursos").json()}
    assert cursos["ES"] == {"curso": "ES", "total_participantes": 2, "total_inscricoes": 4}
    assert cursos["ADS"] == {"curso": "ADS", "total_participantes": 1, "total_inscricoes": 1}

    # 12 - os relatórios mudam depois de excluir/atualizar
    client.delete(f"/eventos/{e2['id']}")
    cats = {r["categoria"]: r for r in client.get("/relatorios/eventos/categorias").json()}
    assert "Workshop" not in cats
    cursos = {r["curso"]: r for r in client.get("/relatorios/participantes/cursos").json()}
    assert cursos["ES"]["total_inscricoes"] == 2

    client.delete(f"/participantes/{a['id']}")
    cursos = {r["curso"]: r for r in client.get("/relatorios/participantes/cursos").json()}
    assert cursos["ES"] == {"curso": "ES", "total_participantes": 1, "total_inscricoes": 1}

    client.put(f"/eventos/{e1['id']}", json={**EVENTO, "titulo": "IA", "capacidade": 10, "categoria": "Palestra"})
    ocup = {r["titulo"]: r for r in client.get("/relatorios/eventos/ocupacao").json()}
    assert ocup["IA"]["percentual_ocupacao"] == 20.0


# exclusão não deixa inscrições órfãs e a capacidade não pode ficar menor que os inscritos
def test_integridade(client):
    ev = novo_evento(client, capacidade=5)
    p1 = novo_participante(client)
    p2 = novo_participante(client, nome="Bia", email="b@x.com")
    client.post(f"/eventos/{ev['id']}/inscricoes/{p1['id']}")
    client.post(f"/eventos/{ev['id']}/inscricoes/{p2['id']}")

    assert client.put(f"/eventos/{ev['id']}", json={**EVENTO, "capacidade": 1}).status_code == 409
    assert client.put(f"/eventos/{ev['id']}", json={**EVENTO, "capacidade": 2}).status_code == 200

    client.delete(f"/participantes/{p1['id']}")
    inscritos = client.get(f"/eventos/{ev['id']}/inscricoes").json()
    assert [i["id"] for i in inscritos] == [p2["id"]]

    client.delete(f"/eventos/{ev['id']}")
    caminho = os.environ["DATABASE_URL"].replace("sqlite:///", "")
    con = sqlite3.connect(caminho)
    assert con.execute("select count(*) from inscricoes").fetchone()[0] == 0
    con.close()
