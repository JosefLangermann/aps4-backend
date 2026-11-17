from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config
from app.models import Perfil, Usuario
from app.schemas.usuario import UsuarioCadastro
from app.security.security import gerar_hash_senha

MSG_EMAIL_DUPLICADO = "Já existe um usuário cadastrado com este e-mail."


def obter_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))


def obter_por_id(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário não encontrado.")
    return usuario


def listar(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.id)))


def registrar(db: Session, dados: UsuarioCadastro) -> Usuario:
    """Cadastro público: o perfil é SEMPRE 'usuario', não importa o que o cliente mande."""
    email = dados.email.lower()
    if obter_por_email(db, email):
        raise HTTPException(status.HTTP_409_CONFLICT, MSG_EMAIL_DUPLICADO)

    novo_usuario = Usuario(
        nome=dados.nome,
        email=email,
        senha_hash=gerar_hash_senha(dados.senha),
        perfil=Perfil.USUARIO.value,
    )
    db.add(novo_usuario)
    try:
        db.commit()
    except IntegrityError:  # o banco também barra e-mail repetido (corrida entre requisições)
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, MSG_EMAIL_DUPLICADO)
    db.refresh(novo_usuario)
    return novo_usuario


def alterar_perfil(db: Session, usuario_id: int, novo_perfil: Perfil, quem_pede: Usuario) -> Usuario:
    if usuario_id == quem_pede.id:
        # evita o administrador se rebaixar sem querer e deixar o sistema sem admin
        raise HTTPException(status.HTTP_409_CONFLICT, "Você não pode alterar o seu próprio perfil.")
    usuario = obter_por_id(db, usuario_id)
    usuario.perfil = novo_perfil.value
    db.commit()
    db.refresh(usuario)
    return usuario


def garantir_admin_inicial(db: Session) -> None:
    """Cria o administrador inicial a partir das variáveis ADMIN_EMAIL / ADMIN_SENHA.

    Roda na subida da API. Se as variáveis não estiverem definidas, ou se o e-mail já
    existir, não faz nada. É a única forma de nascer um administrador sem outro admin.
    """
    if not config.ADMIN_EMAIL or not config.ADMIN_SENHA:
        return
    if obter_por_email(db, config.ADMIN_EMAIL):
        return
    db.add(
        Usuario(
            nome=config.ADMIN_NOME,
            email=config.ADMIN_EMAIL,
            senha_hash=gerar_hash_senha(config.ADMIN_SENHA),
            perfil=Perfil.ADMINISTRADOR.value,
        )
    )
    db.commit()
