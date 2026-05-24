"""
routers/batches.py – CRUD de Malotes com auditoria e atribuição em lote.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Batch, Document, StatusMalote, StatusDocumento
from app.schemas import BatchCreate, BatchOut, BatchUpdate, BatchBulkAssign
from app.audit import registrar_log

router = APIRouter(prefix="/batches", tags=["Malotes"])


def _get_user_id(request: Request) -> Optional[int]:
    return getattr(request.state, "user_id", None)


@router.get("/", response_model=List[BatchOut])
def listar_malotes(
    status: Optional[StatusMalote] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Batch)
    if status:
        q = q.filter(Batch.status == status)
    return q.order_by(Batch.criado_em.desc()).all()


@router.get("/{batch_id}", response_model=BatchOut)
def obter_malote(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Malote não encontrado")
    return batch


@router.post("/", response_model=BatchOut, status_code=201)
def criar_malote(payload: BatchCreate, request: Request, db: Session = Depends(get_db)):
    # Código de identificação deve ser único
    existe = db.query(Batch).filter(Batch.codigo_identificacao == payload.codigo_identificacao).first()
    if existe:
        raise HTTPException(400, f"Malote '{payload.codigo_identificacao}' já existe")

    batch = Batch(**payload.model_dump())
    db.add(batch)
    db.flush()

    registrar_log(
        db,
        acao=f"Criou Malote {payload.codigo_identificacao}",
        entidade_afetada=f"Batch:{batch.id}",
        user_id=_get_user_id(request),
        detalhes=payload.model_dump(),
    )
    db.commit()
    db.refresh(batch)
    return batch


@router.patch("/{batch_id}", response_model=BatchOut)
def atualizar_malote(
    batch_id: int,
    payload: BatchUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Malote não encontrado")

    antes_status = batch.status
    dados = payload.model_dump(exclude_unset=True)
    for campo, valor in dados.items():
        setattr(batch, campo, valor)

    # Quando malote sai (Em Trânsito), atualiza docs vinculados automaticamente
    if payload.status == StatusMalote.em_transito:
        docs = db.query(Document).filter(Document.malote_id == batch_id).all()
        for doc in docs:
            doc.status_documento = StatusDocumento.em_transito
        registrar_log(
            db,
            acao=f"Malote {batch.codigo_identificacao} saiu → Em Trânsito ({len(docs)} docs atualizados)",
            entidade_afetada=f"Batch:{batch_id}",
            user_id=_get_user_id(request),
            detalhes={"status_anterior": antes_status, "docs_atualizados": len(docs)},
        )
    else:
        registrar_log(
            db,
            acao=f"Alterou Status Malote: {antes_status} → {payload.status or 'sem alteração'}",
            entidade_afetada=f"Batch:{batch_id}",
            user_id=_get_user_id(request),
            detalhes=dados,
        )

    db.commit()
    db.refresh(batch)
    return batch


@router.post("/bulk-assign", status_code=200)
def atribuir_documentos_em_lote(
    payload: BatchBulkAssign,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Atribuição em lote: vincula múltiplos documentos a um único malote.
    Documentos que não existirem são ignorados (retorna lista dos atualizados).
    """
    batch = db.query(Batch).filter(Batch.id == payload.batch_id).first()
    if not batch:
        raise HTTPException(404, "Malote não encontrado")

    if batch.status == StatusMalote.finalizado:
        raise HTTPException(400, "Malote finalizado não aceita novos documentos")

    atualizados = []
    for doc_id in payload.document_ids:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.malote_id = payload.batch_id
            atualizados.append(doc_id)

    registrar_log(
        db,
        acao=f"Atribuiu {len(atualizados)} documentos ao Malote {batch.codigo_identificacao}",
        entidade_afetada=f"Batch:{payload.batch_id}",
        user_id=_get_user_id(request),
        detalhes={"document_ids": atualizados},
    )
    db.commit()

    return {"atualizados": atualizados, "total": len(atualizados)}


@router.delete("/{batch_id}", status_code=204)
def deletar_malote(batch_id: int, request: Request, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Malote não encontrado")

    # Desvincula documentos antes de deletar
    db.query(Document).filter(Document.malote_id == batch_id).update({"malote_id": None})

    registrar_log(
        db,
        acao=f"Deletou Malote {batch.codigo_identificacao}",
        entidade_afetada=f"Batch:{batch_id}",
        user_id=_get_user_id(request),
    )
    db.delete(batch)
    db.commit()
