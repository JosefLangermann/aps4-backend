from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Participante
from app.schemas.participante import ParticipanteEntrada

MSG_EMAIL_DUPLICADO = "Já existe um participante cadastrado com este e-mail."


def listar(db: Session) -> list[Participante]:
    return list(db.scalars(select(Participante).order_by(Participante.id)))


def obter_por_id(db: Session, participante_id: int) -> Participante:
    participante = db.get(Participante, participante_id)
    if participante is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participante não encontrado.")
    return participante


def _email_em_uso(db: Session, email: str, ignorar_id: int | None = None) -> bool:
    consulta = select(Participante.id).where(Participante.email == email)
    if ignorar_id is not None:
        consulta = consulta.where(Participante.id != ignorar_id)
    return db.scalar(consulta) is not None


def registrar(db: Session, dados: ParticipanteEntrada) -> Participante:
    valores = dados.model_dump()
    valores["email"] = valores["email"].lower()

    if _email_em_uso(db, valores["email"]):
        raise HTTPException(status.HTTP_409_CONFLICT, MSG_EMAIL_DUPLICADO)

    novo_participante = Participante(**valores)
    db.add(novo_participante)
    try:
        db.commit()
    except IntegrityError:  # o banco também barra e-mail repetido
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, MSG_EMAIL_DUPLICADO)
    db.refresh(novo_participante)
    return novo_participante


def editar(db: Session, participante_id: int, dados: ParticipanteEntrada) -> Participante:
    participante = obter_por_id(db, participante_id)
    valores = dados.model_dump()
    valores["email"] = valores["email"].lower()

    if _email_em_uso(db, valores["email"], ignorar_id=participante_id):
        raise HTTPException(status.HTTP_409_CONFLICT, MSG_EMAIL_DUPLICADO)

    for campo, valor in valores.items():
        setattr(participante, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, MSG_EMAIL_DUPLICADO)
    db.refresh(participante)
    return participante


def remover(db: Session, participante_id: int) -> None:
    participante = obter_por_id(db, participante_id)
    db.delete(participante)  # as inscrições dele saem junto (cascade)
    db.commit()
