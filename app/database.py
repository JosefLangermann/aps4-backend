import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# O arquivo do banco (eventos.db) fica na raiz do projeto, não importa de onde o
# servidor seja iniciado. Dá pra trocar pela variável de ambiente DATABASE_URL
# (é o que os testes fazem para não mexer no banco de verdade).
RAIZ_DO_PROJETO = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{RAIZ_DO_PROJETO / 'eventos.db'}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


# O SQLite não confere chave estrangeira por padrão, então ligamos aqui.
@event.listens_for(engine, "connect")
def ativar_chaves_estrangeiras(conexao, _):
    cursor = conexao.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def obter_sessao():
    """Abre uma sessão para a requisição e garante que ela é fechada no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas() -> None:
    from app import models  # noqa: F401  (importa os modelos para o SQLAlchemy conhecê-los)

    Base.metadata.create_all(bind=engine)
