from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import obter_sessao
from app.models import Usuario
from app.regras import usuarios as regras_usuarios
from app.schemas.usuario import AlterarPerfil, UsuarioCadastro, UsuarioSaida
from app.security.dependencias import exigir_administrador

router = APIRouter(prefix="/usuarios", tags=["Usuários"])

RESPOSTAS_ADMIN = {
    401: {"description": "Token ausente, inválido ou expirado."},
    403: {"description": "Usuário sem permissão (exige perfil administrador)."},
}


@router.post(
    "",
    response_model=UsuarioSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastro público de usuário (sempre com perfil 'usuario')",
)
def criar_usuario(dados: UsuarioCadastro, db: Session = Depends(obter_sessao)):
    return regras_usuarios.registrar(db, dados)


@router.get(
    "",
    response_model=list[UsuarioSaida],
    summary="Lista os usuários (administrador)",
    dependencies=[Depends(exigir_administrador)],
    responses=RESPOSTAS_ADMIN,
)
def listar_usuarios(db: Session = Depends(obter_sessao)):
    return regras_usuarios.listar(db)


@router.patch(
    "/{usuario_id}/perfil",
    response_model=UsuarioSaida,
    summary="Promove ou rebaixa um usuário (administrador)",
    responses=RESPOSTAS_ADMIN,
)
def alterar_perfil_do_usuario(
    usuario_id: int,
    dados: AlterarPerfil,
    db: Session = Depends(obter_sessao),
    admin: Usuario = Depends(exigir_administrador),
):
    return regras_usuarios.alterar_perfil(db, usuario_id, dados.perfil, admin)
