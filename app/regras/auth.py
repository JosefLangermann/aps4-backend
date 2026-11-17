from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.regras import usuarios as regras_usuarios
from app.security.security import HASH_FALSO, criar_token_acesso, verificar_senha

MSG_CREDENCIAIS_INVALIDAS = "E-mail ou senha inválidos."


def autenticar(db: Session, email: str, senha: str) -> str:
    """Confere e-mail e senha e devolve um token JWT.

    A mesma resposta (401) vale para e-mail inexistente e para senha errada, e a verificação
    do hash roda nos dois casos, para não revelar qual dos dois deu errado.
    """
    usuario = regras_usuarios.obter_por_email(db, email)
    senha_confere = verificar_senha(senha, usuario.senha_hash if usuario else HASH_FALSO)

    if usuario is None or not senha_confere:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            MSG_CREDENCIAIS_INVALIDAS,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return criar_token_acesso(usuario.id)
