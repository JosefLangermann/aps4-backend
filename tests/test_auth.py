"""Testes da APS 4: usuários, hash de senha, login, JWT, rotas protegidas e perfis."""
import sqlite3
import os
from datetime import timedelta

import jwt

from app import config
from app.security.security import criar_token_acesso
from tests.conftest import (
    ADMIN_EMAIL, ADMIN_SENHA, USUARIO_EMAIL, USUARIO_SENHA, cliente_com_token, fazer_login,
)
from tests.test_api import EVENTO, novo_evento, novo_participante

NOVO_USUARIO = {"nome": "Aluno Exemplo", "email": USUARIO_EMAIL, "senha": USUARIO_SENHA}
MSG_401 = {"detail": "Não foi possível validar as credenciais."}
MSG_403 = {"detail": "Você não possui permissão para executar esta operação."}


def consultar_banco(sql, *params):
    caminho = os.environ["DATABASE_URL"].replace("sqlite:///", "")
    con = sqlite3.connect(caminho)
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


# ---------------------------------------------------------------- 1 e 2: cadastro e hash
def test_cadastro_de_usuario_nao_expoe_senha_nem_hash(anonimo):
    r = anonimo.post("/usuarios", json=NOVO_USUARIO)
    assert r.status_code == 201
    assert r.json() == {"id": r.json()["id"], "nome": "Aluno Exemplo", "email": USUARIO_EMAIL, "perfil": "usuario"}
    assert "senha" not in r.json() and "senha_hash" not in r.json()
    assert USUARIO_SENHA not in r.text


def test_senha_e_guardada_como_hash_argon2(anonimo):
    anonimo.post("/usuarios", json=NOVO_USUARIO)
    (senha_hash,) = consultar_banco("select senha_hash from usuarios where email = ?", USUARIO_EMAIL)[0]
    assert senha_hash != USUARIO_SENHA
    assert USUARIO_SENHA not in senha_hash
    assert senha_hash.startswith("$argon2")
    # a senha em texto puro não aparece em nenhuma coluna da tabela
    assert USUARIO_SENHA not in str(consultar_banco("select * from usuarios"))


def test_mesma_senha_gera_hashes_diferentes(anonimo):
    anonimo.post("/usuarios", json=NOVO_USUARIO)
    anonimo.post("/usuarios", json={**NOVO_USUARIO, "email": "outro@exemplo.com"})
    hashes = [h for (h,) in consultar_banco("select senha_hash from usuarios where perfil = 'usuario'")]
    assert len(hashes) == 2 and hashes[0] != hashes[1]  # salt aleatório


# ---------------------------------------------------------------- 3: e-mail duplicado
def test_email_duplicado(anonimo):
    assert anonimo.post("/usuarios", json=NOVO_USUARIO).status_code == 201
    r = anonimo.post("/usuarios", json={**NOVO_USUARIO, "email": USUARIO_EMAIL.upper()})
    assert r.status_code == 409
    assert r.json() == {"detail": "Já existe um usuário cadastrado com este e-mail."}


# ---------------------------------------------------------------- validações do cadastro
def test_validacoes_do_cadastro(anonimo):
    casos = [
        {"email": USUARIO_EMAIL, "senha": USUARIO_SENHA},                 # sem nome
        {"nome": "A", "senha": USUARIO_SENHA},                            # sem e-mail
        {**NOVO_USUARIO, "nome": "   "},                                  # nome em branco
        {**NOVO_USUARIO, "email": "invalido"},                            # e-mail inválido
        {**NOVO_USUARIO, "senha": ""},                                    # senha vazia
        {**NOVO_USUARIO, "senha": "curta"},                               # menos de 8 caracteres
        {**NOVO_USUARIO, "senha": "        "},                            # só espaços
        {"nome": "A", "email": USUARIO_EMAIL},                            # sem senha
    ]
    for corpo in casos:
        assert anonimo.post("/usuarios", json=corpo).status_code == 422, corpo
    assert consultar_banco("select count(*) from usuarios where perfil = 'usuario'")[0][0] == 0


def test_cliente_nao_consegue_se_cadastrar_como_administrador(anonimo):
    for perfil in ("administrador", "usuario"):
        r = anonimo.post("/usuarios", json={**NOVO_USUARIO, "perfil": perfil})
        assert r.status_code == 422  # campo "perfil" não é aceito no cadastro público
    assert consultar_banco("select count(*) from usuarios where email = ?", USUARIO_EMAIL)[0][0] == 0


def test_admin_inicial_vem_da_configuracao(anonimo):
    assert consultar_banco("select perfil from usuarios where email = ?", ADMIN_EMAIL) == [("administrador",)]
    admin = cliente_com_token(fazer_login(anonimo, ADMIN_EMAIL, ADMIN_SENHA))
    assert admin.get("/auth/me").json()["perfil"] == "administrador"


# ---------------------------------------------------------------- 4 e 5: login
def test_login_valido_devolve_jwt(anonimo):
    anonimo.post("/usuarios", json=NOVO_USUARIO)
    r = anonimo.post("/auth/login", json={"email": USUARIO_EMAIL, "senha": USUARIO_SENHA})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["token_type"] == "bearer"

    payload = jwt.decode(corpo["access_token"], config.JWT_SECRET_KEY, algorithms=["HS256"])
    id_no_banco = consultar_banco("select id from usuarios where email = ?", USUARIO_EMAIL)[0][0]
    assert payload["sub"] == str(id_no_banco)  # o token identifica o usuário
    assert payload["exp"] - payload["iat"] == config.TOKEN_EXPIRA_MINUTOS * 60  # prazo de validade
    assert "senha" not in payload and "perfil" not in payload  # token não carrega senha nem perfil


def test_login_aceita_email_com_maiusculas(anonimo):
    anonimo.post("/usuarios", json=NOVO_USUARIO)
    r = anonimo.post("/auth/login", json={"email": "  ALUNO@Exemplo.COM ", "senha": USUARIO_SENHA})
    assert r.status_code == 200


def test_login_invalido_nao_revela_o_motivo(anonimo):
    anonimo.post("/usuarios", json=NOVO_USUARIO)
    senha_errada = anonimo.post("/auth/login", json={"email": USUARIO_EMAIL, "senha": "errada123"})
    email_inexistente = anonimo.post("/auth/login", json={"email": "ninguem@exemplo.com", "senha": USUARIO_SENHA})
    email_malformado = anonimo.post("/auth/login", json={"email": "isso-nao-e-email", "senha": USUARIO_SENHA})
    for r in (senha_errada, email_inexistente, email_malformado):
        assert r.status_code == 401
        assert r.json() == {"detail": "E-mail ou senha inválidos."}
    assert senha_errada.json() == email_inexistente.json()  # mesma resposta nos dois casos


# ---------------------------------------------------------------- 6, 7 e 8: rotas protegidas
ROTAS_PROTEGIDAS = [
    ("post", "/eventos"), ("get", "/eventos"), ("get", "/eventos/1"), ("put", "/eventos/1"),
    ("delete", "/eventos/1"), ("post", "/participantes"), ("get", "/participantes"),
    ("get", "/participantes/1"), ("put", "/participantes/1"), ("delete", "/participantes/1"),
    ("post", "/eventos/1/inscricoes/1"), ("get", "/eventos/1/inscricoes"),
    ("get", "/relatorios/eventos/ocupacao"), ("get", "/relatorios/eventos/categorias"),
    ("get", "/relatorios/participantes/cursos"), ("get", "/auth/me"), ("get", "/usuarios"),
    ("patch", "/usuarios/1/perfil"),
]


def test_todas_as_rotas_protegidas_recusam_acesso_sem_token(anonimo):
    for metodo, rota in ROTAS_PROTEGIDAS:
        # corpo inválido de propósito: a autenticação tem que ser checada ANTES da validação
        r = getattr(anonimo, metodo)(rota, **({"json": {}} if metodo in ("post", "put", "patch") else {}))
        assert r.status_code == 401, f"{metodo.upper()} {rota} -> {r.status_code}"
        assert r.json() == MSG_401
        assert r.headers["www-authenticate"] == "Bearer"


def test_rotas_publicas(anonimo):
    assert anonimo.get("/").status_code == 200
    assert anonimo.get("/docs").status_code == 200
    assert anonimo.get("/openapi.json").status_code == 200
    assert anonimo.post("/usuarios", json=NOVO_USUARIO).status_code == 201
    assert anonimo.post("/auth/login", json={"email": USUARIO_EMAIL, "senha": USUARIO_SENHA}).status_code == 200


def test_acesso_com_token_valido(usuario):
    assert usuario.get("/eventos").status_code == 200


def _tokens_ruins(anonimo):
    anonimo.post("/usuarios", json=NOVO_USUARIO)
    uid = consultar_banco("select id from usuarios where email = ?", USUARIO_EMAIL)[0][0]
    bom = criar_token_acesso(uid)
    cabecalho, corpo, assinatura = bom.split(".")
    adulterado_corpo = jwt.utils.base64url_encode(b'{"sub":"1","iat":1,"exp":99999999999}').decode()
    return {
        "lixo": "isso.nao.e.jwt",
        "texto_qualquer": "abc",
        "expirado": criar_token_acesso(uid, expira_em=timedelta(seconds=-5)),
        "assinatura_adulterada": f"{cabecalho}.{corpo}.{assinatura[:-3]}AAA",
        "corpo_adulterado": f"{cabecalho}.{adulterado_corpo}.{assinatura}",
        "outra_chave": jwt.encode({"sub": str(uid), "iat": 1, "exp": 9999999999}, "outra-chave-qualquer-0123456789abcdef", algorithm="HS256"),
        "sem_assinatura_alg_none": jwt.encode({"sub": str(uid), "iat": 1, "exp": 9999999999}, None, algorithm="none"),
        "sem_exp": jwt.encode({"sub": str(uid), "iat": 1}, config.JWT_SECRET_KEY, algorithm="HS256"),
        "usuario_inexistente": criar_token_acesso(99999),
    }


def test_tokens_invalidos_adulterados_ou_expirados_sao_recusados(anonimo):
    for nome, token in _tokens_ruins(anonimo).items():
        r = anonimo.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, nome
        assert r.json() == MSG_401, nome


def test_cabecalho_authorization_mal_formado(anonimo):
    anonimo.post("/usuarios", json=NOVO_USUARIO)
    token = fazer_login(anonimo, USUARIO_EMAIL, USUARIO_SENHA)
    for valor in (token, f"Basic {token}", "Bearer", "Bearer ", ""):
        r = anonimo.get("/auth/me", headers={"Authorization": valor})
        assert r.status_code == 401, valor


# ---------------------------------------------------------------- 9 e 10: perfis
def test_usuario_comum_nao_executa_operacoes_de_administrador(usuario, client):
    ev = novo_evento(client)  # criado pelo admin
    p = novo_participante(client)
    proibidas = [
        ("post", "/eventos", {"json": EVENTO}),
        ("put", f"/eventos/{ev['id']}", {"json": EVENTO}),
        ("delete", f"/eventos/{ev['id']}", {}),
        ("put", f"/participantes/{p['id']}", {"json": {"nome": "X", "email": "x@x.com", "curso": "ADS"}}),
        ("delete", f"/participantes/{p['id']}", {}),
        ("get", f"/eventos/{ev['id']}/inscricoes", {}),
        ("get", "/relatorios/eventos/ocupacao", {}),
        ("get", "/relatorios/eventos/categorias", {}),
        ("get", "/relatorios/participantes/cursos", {}),
        ("get", "/usuarios", {}),
        ("patch", "/usuarios/1/perfil", {"json": {"perfil": "administrador"}}),
    ]
    for metodo, rota, args in proibidas:
        r = getattr(usuario, metodo)(rota, **args)
        assert r.status_code == 403, f"{metodo.upper()} {rota} -> {r.status_code}"
        assert r.json() == MSG_403

    # e nada foi alterado pelas tentativas
    assert client.get(f"/eventos/{ev['id']}").status_code == 200
    assert client.get(f"/participantes/{p['id']}").status_code == 200


def test_403_vem_antes_da_validacao_do_corpo(usuario):
    assert usuario.post("/eventos", json={}).status_code == 403


def test_administrador_executa_operacoes_administrativas(client):
    ev = novo_evento(client)
    assert client.put(f"/eventos/{ev['id']}", json={**EVENTO, "titulo": "Editado"}).status_code == 200
    assert client.get("/relatorios/eventos/ocupacao").status_code == 200
    assert client.get("/relatorios/eventos/categorias").status_code == 200
    assert client.get("/relatorios/participantes/cursos").status_code == 200
    assert client.get(f"/eventos/{ev['id']}/inscricoes").status_code == 200
    assert client.delete(f"/eventos/{ev['id']}").status_code == 204


# ---------------------------------------------------------------- 11: /auth/me
def test_auth_me(usuario, client):
    r = usuario.get("/auth/me")
    assert r.status_code == 200
    assert r.json() == {"id": r.json()["id"], "nome": "Aluno Exemplo", "email": USUARIO_EMAIL, "perfil": "usuario"}
    assert "senha" not in r.text and "hash" not in r.text

    admin = client.get("/auth/me").json()
    assert admin["email"] == ADMIN_EMAIL and admin["perfil"] == "administrador"


def test_auth_me_ignora_id_enviado_pelo_cliente(usuario, client):
    id_admin = client.get("/auth/me").json()["id"]
    r = usuario.get("/auth/me", params={"id": id_admin, "usuario_id": id_admin})
    assert r.json()["email"] == USUARIO_EMAIL  # quem manda é o token


# ---------------------------------------------------------------- 12: APS 3 com as regras de acesso
def test_usuario_comum_usa_as_funcionalidades_permitidas(usuario, client):
    ev = novo_evento(client, capacidade=1)
    assert usuario.get("/eventos").status_code == 200
    assert usuario.get(f"/eventos/{ev['id']}").json()["titulo"] == EVENTO["titulo"]

    # usuário comum pode cadastrar e consultar participantes e inscrever
    p1 = novo_participante(usuario, email="a@x.com")
    p2 = novo_participante(usuario, nome="Bia", email="b@x.com")
    assert len(usuario.get("/participantes").json()) == 2
    assert usuario.get(f"/participantes/{p1['id']}").status_code == 200

    assert usuario.post(f"/eventos/{ev['id']}/inscricoes/{p1['id']}").status_code == 201
    # regras de negócio da APS 3 continuam valendo
    r = usuario.post(f"/eventos/{ev['id']}/inscricoes/{p1['id']}")
    assert r.status_code == 409 and r.json()["detail"] == "Participante já está inscrito neste evento."
    r = usuario.post(f"/eventos/{ev['id']}/inscricoes/{p2['id']}")
    assert r.status_code == 409 and r.json()["detail"] == "Não existem vagas disponíveis para este evento."
    assert usuario.post(f"/eventos/999/inscricoes/{p1['id']}").status_code == 404

    # o relatório (admin) enxerga a inscrição feita pelo usuário comum
    ocup = client.get("/relatorios/eventos/ocupacao").json()
    assert ocup[0]["total_inscritos"] == 1 and ocup[0]["percentual_ocupacao"] == 100.0


# ---------------------------------------------------------------- gestão de perfis
def test_admin_promove_e_a_permissao_e_checada_no_servidor(usuario, client):
    meu_id = usuario.get("/auth/me").json()["id"]
    assert usuario.post("/eventos", json=EVENTO).status_code == 403

    r = client.patch(f"/usuarios/{meu_id}/perfil", json={"perfil": "administrador"})
    assert r.status_code == 200 and r.json()["perfil"] == "administrador"
    # o MESMO token de antes passa a valer como admin: o perfil vem do banco, não do token
    assert usuario.post("/eventos", json=EVENTO).status_code == 201

    client.patch(f"/usuarios/{meu_id}/perfil", json={"perfil": "usuario"})
    assert usuario.post("/eventos", json=EVENTO).status_code == 403


def test_gestao_de_perfis_casos_de_erro(usuario, client):
    meu_id_admin = client.get("/auth/me").json()["id"]
    assert client.patch(f"/usuarios/{meu_id_admin}/perfil", json={"perfil": "usuario"}).status_code == 409
    assert client.patch("/usuarios/999/perfil", json={"perfil": "usuario"}).status_code == 404
    assert client.patch(f"/usuarios/{meu_id_admin}/perfil", json={"perfil": "superuser"}).status_code == 422

    lista = client.get("/usuarios").json()
    assert {u["email"] for u in lista} == {ADMIN_EMAIL, USUARIO_EMAIL}
    assert all("senha" not in u and "senha_hash" not in u for u in lista)
