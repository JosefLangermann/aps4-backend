import os
import sys
import tempfile

# Ambiente de teste: banco temporário, chave JWT de teste e admin inicial de teste.
# (definido ANTES de importar a aplicação, que lê essas variáveis na importação)
ARQUIVO_TESTE = os.path.join(tempfile.gettempdir(), "eventos_teste.db")
if os.path.exists(ARQUIVO_TESTE):
    os.remove(ARQUIVO_TESTE)
os.environ["DATABASE_URL"] = f"sqlite:///{ARQUIVO_TESTE}"
os.environ["JWT_SECRET_KEY"] = "chave-apenas-para-testes-automatizados-0123456789"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["ADMIN_NOME"] = "Admin Teste"
os.environ["ADMIN_EMAIL"] = "admin@teste.com"
os.environ["ADMIN_SENHA"] = "Admin@12345"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from main import app

ADMIN_EMAIL = "admin@teste.com"
ADMIN_SENHA = "Admin@12345"
USUARIO_EMAIL = "aluno@exemplo.com"
USUARIO_SENHA = "senha_segura"


def fazer_login(c: TestClient, email: str, senha: str) -> str:
    r = c.post("/auth/login", json={"email": email, "senha": senha})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def cliente_com_token(token: str) -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture()
def anonimo():
    """Cliente SEM token. Sobe a aplicação (cria tabelas e o admin) e limpa o banco no fim."""
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(anonimo):
    """Cliente já autenticado como ADMINISTRADOR (usado nos testes das funcionalidades da APS 3)."""
    return cliente_com_token(fazer_login(anonimo, ADMIN_EMAIL, ADMIN_SENHA))


@pytest.fixture()
def usuario(anonimo):
    """Cliente autenticado como USUÁRIO COMUM."""
    r = anonimo.post(
        "/usuarios", json={"nome": "Aluno Exemplo", "email": USUARIO_EMAIL, "senha": USUARIO_SENHA}
    )
    assert r.status_code == 201, r.text
    return cliente_com_token(fazer_login(anonimo, USUARIO_EMAIL, USUARIO_SENHA))
