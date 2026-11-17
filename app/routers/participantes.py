from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import obter_sessao
from app.regras import participantes as regras_participantes
from app.schemas.participante import ParticipanteEntrada, ParticipanteSaida
from app.security.dependencias import exigir_administrador, obter_usuario_atual

# Todas as rotas exigem login; atualizar/excluir exigem administrador.
router = APIRouter(
    prefix="/participantes",
    tags=["Participantes"],
    dependencies=[Depends(obter_usuario_atual)],
    responses={401: {"description": "Token ausente, inválido ou expirado."}},
)

SOMENTE_ADMIN = {403: {"description": "Exige perfil administrador."}}


@router.post("", response_model=ParticipanteSaida, status_code=status.HTTP_201_CREATED)
def criar_participante(dados: ParticipanteEntrada, db: Session = Depends(obter_sessao)):
    return regras_participantes.registrar(db, dados)


@router.get("", response_model=list[ParticipanteSaida])
def obter_participantes(db: Session = Depends(obter_sessao)):
    return regras_participantes.listar(db)


@router.get("/{participante_id}", response_model=ParticipanteSaida)
def obter_participante(participante_id: int, db: Session = Depends(obter_sessao)):
    return regras_participantes.obter_por_id(db, participante_id)


@router.put(
    "/{participante_id}",
    response_model=ParticipanteSaida,
    dependencies=[Depends(exigir_administrador)],
    responses=SOMENTE_ADMIN,
)
def atualizar_participante(
    participante_id: int, dados: ParticipanteEntrada, db: Session = Depends(obter_sessao)
):
    return regras_participantes.editar(db, participante_id, dados)


@router.delete(
    "/{participante_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(exigir_administrador)],
    responses=SOMENTE_ADMIN,
)
def apagar_participante(participante_id: int, db: Session = Depends(obter_sessao)) -> None:
    regras_participantes.remover(db, participante_id)
