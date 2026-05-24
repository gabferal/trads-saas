"""
routers/dashboard.py – Métricas do painel principal.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document, Batch, Financial, StatusDocumento, StatusMalote, TipoFinanceiro
from app.schemas import DashboardMetrics

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
def obter_metricas(db: Session = Depends(get_db)):
    agora = datetime.now(timezone.utc)

    # Documentos pendentes de tradução
    pendentes = db.query(func.count(Document.id)).filter(
        Document.status_documento.in_([StatusDocumento.recebido, StatusDocumento.em_traducao])
    ).scalar() or 0

    # Documentos em trânsito
    em_transito = db.query(func.count(Document.id)).filter(
        Document.status_documento == StatusDocumento.em_transito
    ).scalar() or 0

    # Malotes abertos
    malotes_abertos = db.query(func.count(Batch.id)).filter(
        Batch.status.in_([StatusMalote.aberto, StatusMalote.em_transito])
    ).scalar() or 0

    # Faturamento do mês (entradas com NF ou sem)
    faturamento_mes = db.query(func.coalesce(func.sum(Financial.valor), 0)).filter(
        Financial.tipo == TipoFinanceiro.entrada,
        extract("month", Financial.data_registro) == agora.month,
        extract("year", Financial.data_registro) == agora.year,
    ).scalar() or 0.0

    # Pendências fiscais: entradas sem NF
    pendencias_fiscais = db.query(func.count(Financial.id)).filter(
        Financial.tipo == TipoFinanceiro.entrada,
        Financial.nf_lancada == False,
    ).scalar() or 0

    # Documentos por status
    status_rows = (
        db.query(Document.status_documento, func.count(Document.id))
        .group_by(Document.status_documento)
        .all()
    )
    docs_por_status = {s.value: c for s, c in status_rows}

    return DashboardMetrics(
        documentos_pendentes_traducao=pendentes,
        documentos_em_transito=em_transito,
        malotes_abertos=malotes_abertos,
        faturamento_mes=float(faturamento_mes),
        pendencias_fiscais=pendencias_fiscais,
        documentos_por_status=docs_por_status,
    )
