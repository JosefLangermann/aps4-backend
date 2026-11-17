from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Evento, Inscricao
from app.schemas.evento import EventoEntrada


def _valores(dados: EventoEntrada) -> dict:
    valores = dados.model_dump()
    valores["categoria"] = dados.categoria.value  # salva o texto ("Palestra"), não o Enum
    return valores


def listar(db: Session) -> list[Evento]:
    return list(db.scalars(select(Evento).order_by(Evento.id)))


def obter_por_id(db: Session, evento_id: int) -> Evento:
    evento = db.get(Evento, evento_id)
    if evento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evento não encontrado.")
    return evento


def registrar(db: Session, dados: EventoEntrada) -> Evento:
    novo_evento = Evento(**_valores(dados))
    db.add(novo_evento)
    db.commit()
    db.refresh(novo_evento)
    return novo_evento


def editar(db: Session, evento_id: int, dados: EventoEntrada) -> Evento:
    evento = obter_por_id(db, evento_id)

    # Não deixa a capacidade ficar menor do que o número de pessoas já inscritas
    if dados.capacidade < contar_inscritos(db, evento_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A capacidade não pode ser menor que o número de inscritos no evento.",
        )

    for campo, valor in _valores(dados).items():
        setattr(evento, campo, valor)
    db.commit()
    db.refresh(evento)
    return evento


def remover(db: Session, evento_id: int) -> None:
    evento = obter_por_id(db, evento_id)
    db.delete(evento)  # as inscrições do evento saem junto (cascade)
    db.commit()


def contar_inscritos(db: Session, evento_id: int) -> int:
    return db.scalar(select(func.count(Inscricao.id)).where(Inscricao.evento_id == evento_id))


def tem_vaga_disponivel(db: Session, evento: Evento) -> bool:
    """Regra de negócio: só há vaga se o número de inscritos ainda for menor que a capacidade."""
    return contar_inscritos(db, evento.id) < evento.capacidade
