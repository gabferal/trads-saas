"""
routers/gestores.py – CRUD de Gestores.
Gestores são parceiros que encaminham ordens com precificação diferenciada.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Gestor, ServiceOrder
from app.schemas import GestorCreate, GestorUpdate, GestorOut

router = APIRouter(prefix="/gestores", tags=["Gestores"])


@router.get("/", response_model=List[GestorOut])
def listar_gestores(db: Session = Depends(get_db)):
    return db.query(Gestor).order_by(Gestor.nome).all()


@router.get("/{gestor_id}", response_model=GestorOut)
def obter_gestor(gestor_id: int, db: Session = Depends(get_db)):
    g = db.query(Gestor).filter(Gestor.id == gestor_id).first()
    if not g:
        raise HTTPException(404, "Gestor não encontrado")
    return g


@router.post("/", response_model=GestorOut, status_code=201)
def criar_gestor(payload: GestorCreate, db: Session = Depends(get_db)):
    g = Gestor(**payload.model_dump())
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


@router.patch("/{gestor_id}", response_model=GestorOut)
def atualizar_gestor(gestor_id: int, payload: GestorUpdate, db: Session = Depends(get_db)):
    g = db.query(Gestor).filter(Gestor.id == gestor_id).first()
    if not g:
        raise HTTPException(404, "Gestor não encontrado")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(g, campo, valor)
    db.commit()
    db.refresh(g)
    return g


@router.delete("/{gestor_id}", status_code=204)
def deletar_gestor(gestor_id: int, db: Session = Depends(get_db)):
    g = db.query(Gestor).filter(Gestor.id == gestor_id).first()
    if not g:
        raise HTTPException(404, "Gestor não encontrado")
    # Desvincula OS antes de deletar
    db.query(ServiceOrder).filter(ServiceOrder.gestor_id == gestor_id).update({"gestor_id": None})
    db.delete(g)
    db.commit()
