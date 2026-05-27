"""
routers/audit.py – Consulta de logs de auditoria (somente leitura).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import AuditLog
from app.schemas import AuditLogOut

router = APIRouter(prefix="/audit", tags=["Auditoria"])


@router.get("/", response_model=List[AuditLogOut])
def listar_logs(
    entidade: Optional[str] = Query(None, description="Filtrar por prefixo de entidade, ex: 'Batch'"),
    user_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog).options(joinedload(AuditLog.user))
    if entidade:
        q = q.filter(AuditLog.entidade_afetada.ilike(f"{entidade}%"))
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    logs = q.order_by(AuditLog.data_hora.desc()).limit(limit).all()

    return [
        AuditLogOut(
            id=log.id,
            user_id=log.user_id,
            user_nome=log.user.nome if log.user else None,
            acao=log.acao,
            entidade_afetada=log.entidade_afetada,
            detalhes=log.detalhes,
            data_hora=log.data_hora,
        )
        for log in logs
    ]
