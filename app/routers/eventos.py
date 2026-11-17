from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import obter_sessao
from app.regras import eventos as regras_eventos
from app.schemas.evento import EventoEntrada, EventoSaida
from app.security.dependencias import exigir_administrador, obter_usuario_atual

# Todas as rotas deste router exigem login; criar/editar/excluir exigem administrador.
router = APIRouter(
    prefix="/eventos",
    tags=["Eventos"],
    dependencies=[Depends(obter_usuario_atual)],
    responses={401: {"description": "Token ausente, inválido ou expirado."}},
)

SOMENTE_ADMIN = {403: {"description": "Exige perfil administrador."}}


@router.post(
    "",
    response_model=EventoSaida,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(exigir_administrador)],
    responses=SOMENTE_ADMIN,
)
def criar_evento(dados: EventoEntrada, db: Session = Depends(obter_sessao)):
    return regras_eventos.registrar(db, dados)


@router.get("", response_model=list[EventoSaida])
def obter_eventos(db: Session = Depends(obter_sessao)):
    return regras_eventos.listar(db)


@router.get("/{evento_id}", response_model=EventoSaida)
def obter_evento(evento_id: int, db: Session = Depends(obter_sessao)):
    return regras_eventos.obter_por_id(db, evento_id)


@router.put(
    "/{evento_id}",
    response_model=EventoSaida,
    dependencies=[Depends(exigir_administrador)],
    responses=SOMENTE_ADMIN,
)
def atualizar_evento(evento_id: int, dados: EventoEntrada, db: Session = Depends(obter_sessao)):
    return regras_eventos.editar(db, evento_id, dados)


@router.delete(
    "/{evento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(exigir_administrador)],
    responses=SOMENTE_ADMIN,
)
def apagar_evento(evento_id: int, db: Session = Depends(obter_sessao)) -> None:
    regras_eventos.remover(db, evento_id)
