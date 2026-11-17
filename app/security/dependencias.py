"""Dependências do FastAPI que protegem as rotas.

- obter_usuario_atual: exige um token Bearer válido e devolve o usuário (401 se não houver).
- exigir_perfil / exigir_administrador: além de autenticado, exige um perfil (403 se não tiver).

O perfil é sempre lido do BANCO, nunca de algo enviado pelo cliente.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import obter_sessao
from app.models import Perfil, Usuario
from app.security.security import TokenInvalidoError, validar_token

MSG_NAO_AUTENTICADO = "Não foi possível validar as credenciais."
MSG_SEM_PERMISSAO = "Você não possui permissão para executar esta operação."

# auto_error=False: quem devolve o erro somos nós, sempre 401 com a mesma mensagem.
esquema_bearer = HTTPBearer(auto_error=False, description="Cole aqui o access_token retornado por POST /auth/login")


def _nao_autenticado() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        MSG_NAO_AUTENTICADO,
        headers={"WWW-Authenticate": "Bearer"},
    )


def obter_usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(obter_sessao),
) -> Usuario:
    if credenciais is None:
        raise _nao_autenticado()
    try:
        usuario_id = validar_token(credenciais.credentials)
    except TokenInvalidoError:
        raise _nao_autenticado()

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:  # token válido, mas o usuário não existe mais
        raise _nao_autenticado()
    return usuario


def exigir_perfil(*perfis_permitidos: Perfil):
    permitidos = {perfil.value for perfil in perfis_permitidos}

    def verificar(usuario: Usuario = Depends(obter_usuario_atual)) -> Usuario:
        if usuario.perfil not in permitidos:
            raise HTTPException(status.HTTP_403_FORBIDDEN, MSG_SEM_PERMISSAO)
        return usuario

    return verificar


exigir_administrador = exigir_perfil(Perfil.ADMINISTRADOR)
