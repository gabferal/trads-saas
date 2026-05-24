"""
audit.py – Utilitário para gravação de logs de auditoria.
Centraliza a lógica para garantir rastreabilidade em toda a aplicação.
"""

import json
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.models import AuditLog


def registrar_log(
    db: Session,
    acao: str,
    entidade_afetada: str,
    user_id: Optional[int] = None,
    detalhes: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Grava um registro imutável de auditoria.

    Args:
        db: Sessão ativa do banco de dados.
        acao: Descrição humana da ação (ex: "Alterou Status Documento").
        entidade_afetada: Identificador da entidade (ex: "Document:42").
        user_id: ID do usuário responsável (None para ops automáticas).
        detalhes: Dict opcional com dados antes/depois para diff.

    Returns:
        Instância do AuditLog persistida.
    """
    log = AuditLog(
        user_id=user_id,
        acao=acao,
        entidade_afetada=entidade_afetada,
        detalhes=json.dumps(detalhes, ensure_ascii=False, default=str) if detalhes else None,
    )
    db.add(log)
    db.flush()   # Grava sem commit para participar da mesma transação do caller
    return log
