"""Configurações lidas de variáveis de ambiente (ou do arquivo .env, se existir).

Nenhum segredo fica escrito no código: a chave do JWT e os dados do administrador
inicial vêm do ambiente. Veja o arquivo .env.example e o README.
"""
import logging
import os
import secrets

from dotenv import load_dotenv

load_dotenv()  # lê o .env da raiz do projeto, se ele existir

logger = logging.getLogger("uvicorn.error")

# --- JWT ---------------------------------------------------------------------
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRA_MINUTOS = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()
if not JWT_SECRET_KEY:
    # Sem chave configurada: gera uma aleatória só para este processo. É seguro (ninguém
    # conhece a chave), mas os tokens deixam de valer quando a API reinicia.
    JWT_SECRET_KEY = secrets.token_urlsafe(48)
    logger.warning(
        "JWT_SECRET_KEY não definida: usando uma chave aleatória temporária. "
        "Os tokens perdem a validade ao reiniciar a API. Defina a variável no .env."
    )

# --- Administrador inicial (criado na subida da API, se ainda não existir) --------
ADMIN_NOME = os.getenv("ADMIN_NOME", "Administrador").strip() or "Administrador"
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
ADMIN_SENHA = os.getenv("ADMIN_SENHA", "")
