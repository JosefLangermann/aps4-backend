from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Inscricao, Participante
from app.regras import eventos as regras_eventos
from app.regras import participantes as regras_participantes

MSG_JA_INSCRITO = "Participante já está inscrito neste evento."


def existe_vinculo(db: Session, evento_id: int, participante_id: int) -> bool:
    consulta = select(Inscricao.id).where(
        Inscricao.evento_id == evento_id,
        Inscricao.participante_id == participante_id,
    )
    return db.scalar(consulta) is not None


def confirmar_inscricao(db: Session, evento_id: int, participante_id: int) -> Inscricao:
    # 1. O evento precisa existir
    evento = regras_eventos.obter_por_id(db, evento_id)

    # 2. O participante precisa existir
    regras_participantes.obter_por_id(db, participante_id)

    # 3. Não pode haver inscrição duplicada
    if existe_vinculo(db, evento_id, participante_id):
        raise HTTPException(status.HTTP_409_CONFLICT, MSG_JA_INSCRITO)

    # 4. Precisa haver vaga disponível
    if not regras_eventos.tem_vaga_disponivel(db, evento):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Não existem vagas disponíveis para este evento.",
        )

    nova_inscricao = Inscricao(evento_id=evento_id, participante_id=participante_id)
    db.add(nova_inscricao)
    try:
        db.commit()
    except IntegrityError:  # a constraint única do banco também barra duplicidade
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, MSG_JA_INSCRITO)
    db.refresh(nova_inscricao)
    return nova_inscricao


def listar_inscritos_do_evento(db: Session, evento_id: int) -> list[Participante]:
    evento = regras_eventos.obter_por_id(db, evento_id)  # garante que o evento existe

    # usa os relacionamentos: evento -> inscricoes -> participante
    inscricoes = sorted(evento.inscricoes, key=lambda inscricao: inscricao.id)
    return [inscricao.participante for inscricao in inscricoes]
