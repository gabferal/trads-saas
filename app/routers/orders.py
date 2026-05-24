"""
routers/orders.py – CRUD de Ordens de Serviço.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ServiceOrder, StatusOS
from app.schemas import ServiceOrderCreate, ServiceOrderOut, ServiceOrderUpdate

router = APIRouter(prefix="/orders", tags=["Ordens de Serviço"])


@router.get("/", response_model=List[ServiceOrderOut])
def listar_os(
    cliente_id: Optional[int] = Query(None),
    status: Optional[StatusOS] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(ServiceOrder)
    if cliente_id:
        q = q.filter(ServiceOrder.cliente_id == cliente_id)
    if status:
        q = q.filter(ServiceOrder.status_geral == status)
    return q.order_by(ServiceOrder.data_abertura.desc()).all()


@router.get("/{os_id}", response_model=ServiceOrderOut)
def obter_os(os_id: int, db: Session = Depends(get_db)):
    os_ = db.query(ServiceOrder).filter(ServiceOrder.id == os_id).first()
    if not os_:
        raise HTTPException(404, "OS não encontrada")
    return os_


@router.post("/", response_model=ServiceOrderOut, status_code=201)
def criar_os(payload: ServiceOrderCreate, db: Session = Depends(get_db)):
    os_ = ServiceOrder(**payload.model_dump())
    db.add(os_)
    db.commit()
    db.refresh(os_)
    return os_


@router.patch("/{os_id}", response_model=ServiceOrderOut)
def atualizar_os(os_id: int, payload: ServiceOrderUpdate, db: Session = Depends(get_db)):
    os_ = db.query(ServiceOrder).filter(ServiceOrder.id == os_id).first()
    if not os_:
        raise HTTPException(404, "OS não encontrada")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(os_, campo, valor)
    db.commit()
    db.refresh(os_)
    return os_
