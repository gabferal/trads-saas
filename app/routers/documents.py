"""
routers/documents.py – CRUD de Documentos com auditoria integrada.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, StatusDocumento
from app.schemas import DocumentCreate, DocumentOut, DocumentUpdate
from app.audit import registrar_log

router = APIRouter(prefix="/documents", tags=["Documentos"])


def _get_user_id(request: Request) -> Optional[int]:
    """Extrai user_id do state (definido pelo middleware de auth no main.py)."""
    return getattr(request.state, "user_id", None)


@router.get("/", response_model=List[DocumentOut])
def listar_documentos(
    os_id: Optional[int] = Query(None),
    status: Optional[StatusDocumento] = Query(None),
    sem_malote: Optional[bool] = Query(None, description="Filtrar documentos sem malote"),
    apenas_raiz: Optional[bool] = Query(None, description="Apenas documentos sem pai (raiz)"),
    db: Session = Depends(get_db),
):
    """Lista documentos com filtros opcionais. Carrega filhos recursivamente."""
    q = db.query(Document)
    if os_id:
        q = q.filter(Document.os_id == os_id)
    if status:
        q = q.filter(Document.status_documento == status)
    if sem_malote:
        q = q.filter(Document.malote_id.is_(None))
    if apenas_raiz:
        q = q.filter(Document.pai_id.is_(None))
    return q.order_by(Document.criado_em.desc()).all()


@router.get("/{doc_id}", response_model=DocumentOut)
def obter_documento(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Documento não encontrado")
    return doc


@router.post("/", response_model=DocumentOut, status_code=201)
def criar_documento(payload: DocumentCreate, request: Request, db: Session = Depends(get_db)):
    # Valida pai se informado
    if payload.pai_id:
        pai = db.query(Document).filter(Document.id == payload.pai_id).first()
        if not pai:
            raise HTTPException(400, "Documento pai não encontrado")

    doc = Document(**payload.model_dump())
    db.add(doc)
    db.flush()

    registrar_log(
        db,
        acao=f"Criou Documento '{payload.tipo_documento}'",
        entidade_afetada=f"Document:{doc.id}",
        user_id=_get_user_id(request),
        detalhes={"os_id": payload.os_id, "tipo": payload.tipo_documento, "pai_id": payload.pai_id},
    )
    db.commit()
    db.refresh(doc)
    return doc


@router.patch("/{doc_id}", response_model=DocumentOut)
def atualizar_documento(
    doc_id: int,
    payload: DocumentUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Documento não encontrado")

    antes = {"status": doc.status_documento, "malote_id": doc.malote_id}
    dados = payload.model_dump(exclude_unset=True)

    for campo, valor in dados.items():
        setattr(doc, campo, valor)

    # Log específico para mudança de status
    if "status_documento" in dados:
        registrar_log(
            db,
            acao=f"Alterou Status Documento: {antes['status']} → {payload.status_documento}",
            entidade_afetada=f"Document:{doc_id}",
            user_id=_get_user_id(request),
            detalhes={"antes": antes, "depois": dados},
        )
    # Log para atribuição de malote
    elif "malote_id" in dados:
        registrar_log(
            db,
            acao=f"Atribuiu Documento ao Malote {payload.malote_id}",
            entidade_afetada=f"Document:{doc_id}",
            user_id=_get_user_id(request),
            detalhes={"malote_anterior": antes["malote_id"], "malote_novo": payload.malote_id},
        )
    else:
        registrar_log(
            db,
            acao="Editou Documento",
            entidade_afetada=f"Document:{doc_id}",
            user_id=_get_user_id(request),
            detalhes=dados,
        )

    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{doc_id}", status_code=204)
def deletar_documento(doc_id: int, request: Request, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Documento não encontrado")
    registrar_log(
        db,
        acao=f"Deletou Documento '{doc.tipo_documento}'",
        entidade_afetada=f"Document:{doc_id}",
        user_id=_get_user_id(request),
    )
    db.delete(doc)
    db.commit()
