from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import obter_sessao
from app.models import Usuario
from app.regras import auth as regras_auth
from app.schemas.auth import LoginEntrada, TokenSaida
from app.schemas.usuario import UsuarioSaida
from app.security.dependencias import obter_usuario_atual

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/login",
    response_model=TokenSaida,
    summary="Login (e-mail e senha) e geração do token JWT",
    responses={401: {"description": "E-mail ou senha inválidos."}},
)
def login(dados: LoginEntrada, db: Session = Depends(obter_sessao)):
    token = regras_auth.autenticar(db, dados.email, dados.senha)
    return TokenSaida(access_token=token)


@router.get(
    "/me",
    response_model=UsuarioSaida,
    summary="Dados do usuário dono do token",
    responses={401: {"description": "Token ausente, inválido ou expirado."}},
)
def meus_dados(usuario: Usuario = Depends(obter_usuario_atual)):
    # o usuário vem do TOKEN; o cliente não informa id nenhum
    return usuario
