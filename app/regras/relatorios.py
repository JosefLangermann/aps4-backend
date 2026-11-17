from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Evento, Inscricao, Participante


def ocupacao_dos_eventos(db: Session) -> list[dict]:
    # outer join: evento sem inscrição também aparece (0 inscritos)
    consulta = (
        select(
            Evento.id,
            Evento.titulo,
            Evento.capacidade,
            func.count(Inscricao.id).label("inscritos"),
        )
        .outerjoin(Inscricao, Inscricao.evento_id == Evento.id)
        .group_by(Evento.id)
        .order_by(Evento.id)
    )

    resultado = []
    for linha in db.execute(consulta):
        percentual = round(linha.inscritos / linha.capacidade * 100, 2) if linha.capacidade > 0 else 0.0
        resultado.append(
            {
                "evento_id": linha.id,
                "titulo": linha.titulo,
                "capacidade": linha.capacidade,
                "total_inscritos": linha.inscritos,
                "vagas_disponiveis": max(linha.capacidade - linha.inscritos, 0),
                "percentual_ocupacao": percentual,
            }
        )
    return resultado


def eventos_por_categoria(db: Session) -> list[dict]:
    # Conta as inscrições por evento primeiro e só depois agrupa por categoria.
    # (Juntando tudo de uma vez, a capacidade seria somada várias vezes.)
    inscricoes_por_evento = (
        select(Inscricao.evento_id.label("evento_id"), func.count(Inscricao.id).label("qtd"))
        .group_by(Inscricao.evento_id)
        .subquery()
    )

    consulta = (
        select(
            Evento.categoria,
            func.count(Evento.id),
            func.sum(Evento.capacidade),
            func.coalesce(func.sum(inscricoes_por_evento.c.qtd), 0),
        )
        .outerjoin(inscricoes_por_evento, inscricoes_por_evento.c.evento_id == Evento.id)
        .group_by(Evento.categoria)
        .order_by(Evento.categoria)
    )

    return [
        {
            "categoria": categoria,
            "total_eventos": total_eventos,
            "capacidade_total": capacidade_total,
            "total_inscricoes": total_inscricoes,
        }
        for categoria, total_eventos, capacidade_total, total_inscricoes in db.execute(consulta)
    ]


def participacao_por_curso(db: Session) -> list[dict]:
    # count(distinct) evita contar o mesmo participante várias vezes
    consulta = (
        select(
            Participante.curso,
            func.count(func.distinct(Participante.id)),
            func.count(Inscricao.id),
        )
        .outerjoin(Inscricao, Inscricao.participante_id == Participante.id)
        .group_by(Participante.curso)
        .order_by(Participante.curso)
    )

    return [
        {"curso": curso, "total_participantes": participantes, "total_inscricoes": inscricoes}
        for curso, participantes, inscricoes in db.execute(consulta)
    ]
