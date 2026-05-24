"""
schemas.py – Schemas Pydantic para validação de requests/responses da API.
Separados dos modelos ORM para evitar acoplamento.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, EmailStr, field_validator

from app.models import StatusDocumento, StatusMalote, StatusOS, TipoFinanceiro


# ──────────────────────────────────────────────
# User
# ──────────────────────────────────────────────

class UserCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str


class UserOut(BaseModel):
    id: int
    nome: str
    email: str
    ativo: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Client
# ──────────────────────────────────────────────

class ClientCreate(BaseModel):
    nome_completo: str
    telefone_whatsapp: str
    observacoes: Optional[str] = None


class ClientOut(BaseModel):
    id: int
    nome_completo: str
    telefone_whatsapp: str
    data_cadastro: datetime
    observacoes: Optional[str]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Service Order
# ──────────────────────────────────────────────

class ServiceOrderCreate(BaseModel):
    cliente_id: int
    descricao: Optional[str] = None


class ServiceOrderUpdate(BaseModel):
    status_geral: Optional[StatusOS] = None
    descricao: Optional[str] = None


class ServiceOrderOut(BaseModel):
    id: int
    cliente_id: int
    data_abertura: datetime
    status_geral: StatusOS
    descricao: Optional[str]

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Batch (Malote)
# ──────────────────────────────────────────────

class BatchCreate(BaseModel):
    codigo_identificacao: str
    observacoes: Optional[str] = None


class BatchUpdate(BaseModel):
    status: Optional[StatusMalote] = None
    data_envio: Optional[datetime] = None
    observacoes: Optional[str] = None


class BatchOut(BaseModel):
    id: int
    codigo_identificacao: str
    data_envio: Optional[datetime]
    status: StatusMalote
    observacoes: Optional[str]
    criado_em: datetime

    model_config = {"from_attributes": True}


class BatchBulkAssign(BaseModel):
    """Atribuição em lote: vincula múltiplos documentos a um malote."""
    document_ids: List[int]
    batch_id: int


# ──────────────────────────────────────────────
# Document
# ──────────────────────────────────────────────

class DocumentCreate(BaseModel):
    os_id: int
    tipo_documento: str
    idioma_origem: Optional[str] = "Espanhol"
    idioma_destino: Optional[str] = "Português"
    snapshot_url: Optional[str] = None
    pai_id: Optional[int] = None
    observacoes: Optional[str] = None


class DocumentUpdate(BaseModel):
    tipo_documento: Optional[str] = None
    status_documento: Optional[StatusDocumento] = None
    malote_id: Optional[int] = None
    snapshot_url: Optional[str] = None
    pai_id: Optional[int] = None
    observacoes: Optional[str] = None


class DocumentOut(BaseModel):
    id: int
    os_id: int
    malote_id: Optional[int]
    pai_id: Optional[int]
    tipo_documento: str
    status_documento: StatusDocumento
    idioma_origem: str
    idioma_destino: str
    snapshot_url: Optional[str]
    observacoes: Optional[str]
    criado_em: datetime
    filhos: List["DocumentOut"] = []

    model_config = {"from_attributes": True}

# Auto-referência precisa de update_forward_refs
DocumentOut.model_rebuild()


# ──────────────────────────────────────────────
# Financial
# ──────────────────────────────────────────────

class FinancialCreate(BaseModel):
    os_id: int
    tipo: TipoFinanceiro
    descricao: str
    valor: float

    @field_validator("valor")
    @classmethod
    def valor_positivo(cls, v):
        if v <= 0:
            raise ValueError("Valor deve ser positivo")
        return v


class FinancialUpdate(BaseModel):
    nf_lancada: Optional[bool] = None
    descricao: Optional[str] = None
    valor: Optional[float] = None


class FinancialOut(BaseModel):
    id: int
    os_id: int
    tipo: TipoFinanceiro
    descricao: str
    valor: float
    nf_lancada: bool
    data_registro: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Audit Log
# ──────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    acao: str
    entidade_afetada: str
    detalhes: Optional[str]
    data_hora: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────

class DashboardMetrics(BaseModel):
    documentos_pendentes_traducao: int
    documentos_em_transito: int
    malotes_abertos: int
    faturamento_mes: float
    pendencias_fiscais: int
    documentos_por_status: Dict[str, int] = {}


# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
