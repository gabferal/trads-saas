"""
routers/audit.py – Consulta de logs de auditoria (somente leitura).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

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
    q = db.query(AuditLog)
    if entidade:
        q = q.filter(AuditLog.entidade_afetada.ilike(f"{entidade}%"))
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    return q.order_by(AuditLog.data_hora.desc()).limit(limit).all()
