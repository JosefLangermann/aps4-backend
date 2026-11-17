from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import obter_sessao
from app.regras import relatorios as regras_relatorios
from app.schemas.relatorio import CategoriaSaida, CursoSaida, OcupacaoEventoSaida
from app.security.dependencias import exigir_administrador

# Os relatórios consolidados são restritos a administradores.
router = APIRouter(
    prefix="/relatorios",
    tags=["Relatórios"],
    dependencies=[Depends(exigir_administrador)],
    responses={
        401: {"description": "Token ausente, inválido ou expirado."},
        403: {"description": "Exige perfil administrador."},
    },
)


@router.get("/eventos/ocupacao", response_model=list[OcupacaoEventoSaida])
def relatorio_de_ocupacao(db: Session = Depends(obter_sessao)):
    return regras_relatorios.ocupacao_dos_eventos(db)


@router.get("/eventos/categorias", response_model=list[CategoriaSaida])
def relatorio_por_categoria(db: Session = Depends(obter_sessao)):
    return regras_relatorios.eventos_por_categoria(db)


@router.get("/participantes/cursos", response_model=list[CursoSaida])
def relatorio_por_curso(db: Session = Depends(obter_sessao)):
    return regras_relatorios.participacao_por_curso(db)
