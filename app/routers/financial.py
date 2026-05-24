"""
routers/financial.py – Lançamentos financeiros com rastreamento de NF.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Financial, TipoFinanceiro
from app.schemas import FinancialCreate, FinancialOut, FinancialUpdate
from app.audit import registrar_log

router = APIRouter(prefix="/financial", tags=["Financeiro"])


def _get_user_id(request: Request) -> Optional[int]:
    return getattr(request.state, "user_id", None)


@router.get("/", response_model=List[FinancialOut])
def listar_lancamentos(
    os_id: Optional[int] = Query(None),
    tipo: Optional[TipoFinanceiro] = Query(None),
    nf_lancada: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Financial)
    if os_id:
        q = q.filter(Financial.os_id == os_id)
    if tipo:
        q = q.filter(Financial.tipo == tipo)
    if nf_lancada is not None:
        q = q.filter(Financial.nf_lancada == nf_lancada)
    return q.order_by(Financial.data_registro.desc()).all()


@router.post("/", response_model=FinancialOut, status_code=201)
def criar_lancamento(payload: FinancialCreate, request: Request, db: Session = Depends(get_db)):
    fin = Financial(**payload.model_dump())
    db.add(fin)
    db.flush()
    registrar_log(
        db,
        acao=f"Lançou {payload.tipo} R$ {payload.valor:.2f}",
        entidade_afetada=f"Financial:{fin.id}",
        user_id=_get_user_id(request),
        detalhes=payload.model_dump(),
    )
    db.commit()
    db.refresh(fin)
    return fin


@router.patch("/{fin_id}", response_model=FinancialOut)
def atualizar_lancamento(
    fin_id: int,
    payload: FinancialUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    fin = db.query(Financial).filter(Financial.id == fin_id).first()
    if not fin:
        raise HTTPException(404, "Lançamento não encontrado")

    dados = payload.model_dump(exclude_unset=True)
    for campo, valor in dados.items():
        setattr(fin, campo, valor)

    # Log específico para marcação de NF
    if payload.nf_lancada is True:
        registrar_log(
            db,
            acao="Lançou NF no sistema tributário externo",
            entidade_afetada=f"Financial:{fin_id}",
            user_id=_get_user_id(request),
            detalhes={"os_id": fin.os_id, "valor": fin.valor},
        )
    db.commit()
    db.refresh(fin)
    return fin
