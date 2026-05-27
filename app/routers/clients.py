"""
routers/clients.py – CRUD de Clientes.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Client, ServiceOrder, Document
from app.schemas import ClientCreate, ClientOut

router = APIRouter(prefix="/clients", tags=["Clientes"])


@router.get("/", response_model=List[ClientOut])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(Client).order_by(Client.data_cadastro.desc()).all()


@router.get("/{client_id}", response_model=ClientOut)
def obter_cliente(client_id: int, db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c:
        raise HTTPException(404, "Cliente não encontrado")
    return c


@router.post("/", response_model=ClientOut, status_code=201)
def criar_cliente(payload: ClientCreate, db: Session = Depends(get_db)):
    cliente = Client(**payload.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.patch("/{client_id}", response_model=ClientOut)
def atualizar_cliente(client_id: int, payload: ClientCreate, db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c:
        raise HTTPException(404, "Cliente não encontrado")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(c, campo, valor)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{client_id}", status_code=204)
def deletar_cliente(client_id: int, db: Session = Depends(get_db)):
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c:
        raise HTTPException(404, "Cliente não encontrado")
    # Verifica se há OS vinculadas
    ordens = db.query(ServiceOrder).filter(ServiceOrder.cliente_id == client_id).count()
    if ordens:
        raise HTTPException(400, f"Cliente possui {ordens} ordem(s) de serviço. Remova-as primeiro.")
    db.delete(c)
    db.commit()
