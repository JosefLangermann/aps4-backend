"""Cria o arquivo .env a partir do .env.example, já com uma chave JWT aleatória nova.

Uso:  python gerar_env.py

Não sobrescreve um .env que já exista. O .env não vai para o GitHub (está no .gitignore).
"""
import secrets
from pathlib import Path

raiz = Path(__file__).resolve().parent
modelo = raiz / ".env.example"
destino = raiz / ".env"

if destino.exists():
    print(".env já existe: nada foi alterado.")
    raise SystemExit(0)

linhas = []
for linha in modelo.read_text(encoding="utf-8").splitlines():
    if linha.startswith("JWT_SECRET_KEY="):
        linha = f"JWT_SECRET_KEY={secrets.token_urlsafe(48)}"
    linhas.append(linha)

destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")
print(".env criado com uma chave JWT aleatória.")
print("Administrador inicial: veja ADMIN_EMAIL e ADMIN_SENHA no .env (troque a senha se quiser).")
