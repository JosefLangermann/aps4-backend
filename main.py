from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal, criar_tabelas
from app.regras import usuarios as regras_usuarios
from app.routers import auth, eventos, inscricoes, participantes, relatorios, usuarios


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    criar_tabelas()  # cria as tabelas no SQLite caso ainda não existam
    with SessionLocal() as db:
        regras_usuarios.garantir_admin_inicial(db)  # cria o admin definido no .env (se houver)
    yield


app = FastAPI(
    title="Central de Eventos Acadêmicos",
    description=(
        "API para organizar palestras, workshops, minicursos, seminários e "
        "competições dentro da instituição, controlando participantes e vagas. "
        "Os dados são salvos em um banco SQLite. O acesso exige login (JWT): "
        "faça `POST /auth/login`, copie o `access_token` e clique em **Authorize**."
    ),
    version="4.0.0",
    lifespan=ciclo_de_vida,
)


# Falha inesperada do banco: resposta genérica, sem expor detalhes técnicos
@app.exception_handler(SQLAlchemyError)
async def erro_de_banco(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro ao processar a operação no banco de dados."},
    )


app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(eventos.router)
app.include_router(participantes.router)
app.include_router(inscricoes.router)
app.include_router(relatorios.router)


@app.get("/", tags=["Status"])
def status_da_api():
    return {"status": "online", "servico": "Central de Eventos Acadêmicos"}
