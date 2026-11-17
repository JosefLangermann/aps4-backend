"""Funções de segurança: hash de senhas e geração/validação de tokens JWT.

Nada aqui conhece HTTP nem banco de dados. Quem identifica o usuário a partir do token
(e devolve 401/403) são as dependências em `dependencias.py`.
"""
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app import config

# --- Senhas -------------------------------------------------------------------
# PasswordHash.recommended() usa Argon2id (com salt aleatório embutido no hash).
_hasher = PasswordHash.recommended()

# Hash "de mentira" usado no login quando o e-mail não existe, para gastar o mesmo tempo
# de uma verificação real (evita descobrir e-mails cadastrados pelo tempo da resposta).
HASH_FALSO = _hasher.hash("senha-falsa-apenas-para-igualar-o-tempo")


def gerar_hash_senha(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return _hasher.verify(senha, senha_hash)


# --- Tokens JWT ---------------------------------------------------------------
class TokenInvalidoError(Exception):
    """Token ausente de dados, adulterado, expirado ou com assinatura errada."""


def criar_token_acesso(usuario_id: int, expira_em: timedelta | None = None) -> str:
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),  # quem é o usuário
        "iat": agora,  # quando foi emitido
        "exp": agora + (expira_em if expira_em is not None else timedelta(minutes=config.TOKEN_EXPIRA_MINUTOS)),
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def validar_token(token: str) -> int:
    """Confere assinatura e validade e devolve o id do usuário dono do token."""
    try:
        payload = jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],  # lista fixa: recusa "alg: none" e afins
            options={"require": ["exp", "iat", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError) as erro:
        raise TokenInvalidoError from erro
