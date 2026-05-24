"""
models.py – Modelos SQLAlchemy para o sistema de gestão de traduções.
Reflete todas as entidades, relações e constraints definidas nas regras de negócio.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, func
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ──────────────────────────────────────────────
# Enumerações de domínio
# ──────────────────────────────────────────────

class StatusDocumento(str, enum.Enum):
    recebido       = "Recebido"
    em_traducao    = "Em Tradução"
    traduzido      = "Traduzido"
    em_transito    = "Em Trânsito"
    finalizado     = "Finalizado"


class StatusMalote(str, enum.Enum):
    aberto         = "Aberto"
    em_transito    = "Em Trânsito para Assunção"
    entregue       = "Entregue"
    finalizado     = "Finalizado"


class StatusOS(str, enum.Enum):
    aberta         = "Aberta"
    em_andamento   = "Em Andamento"
    concluida      = "Concluída"
    cancelada      = "Cancelada"


class TipoFinanceiro(str, enum.Enum):
    entrada        = "Entrada"
    saida          = "Saída"


# ──────────────────────────────────────────────
# Tabelas
# ──────────────────────────────────────────────

class User(Base):
    """Usuários do sistema – acesso único nível."""
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    nome          = Column(String(120), nullable=False)
    email         = Column(String(180), unique=True, nullable=False, index=True)
    senha_hash    = Column(String(256), nullable=False)
    ativo         = Column(Boolean, default=True)
    criado_em     = Column(DateTime(timezone=True), server_default=func.now())

    # relações
    logs          = relationship("AuditLog", back_populates="user")


class Client(Base):
    """Clientes do escritório."""
    __tablename__ = "clients"

    id                = Column(Integer, primary_key=True, index=True)
    nome_completo     = Column(String(200), nullable=False)
    telefone_whatsapp = Column(String(30), nullable=False)
    data_cadastro     = Column(DateTime(timezone=True), server_default=func.now())
    observacoes       = Column(Text, nullable=True)

    # relações
    ordens_servico    = relationship("ServiceOrder", back_populates="cliente")


class ServiceOrder(Base):
    """Ordem de Serviço – agrupa documentos de um cliente."""
    __tablename__ = "service_orders"

    id              = Column(Integer, primary_key=True, index=True)
    cliente_id      = Column(Integer, ForeignKey("clients.id"), nullable=False)
    data_abertura   = Column(DateTime(timezone=True), server_default=func.now())
    status_geral    = Column(Enum(StatusOS), default=StatusOS.aberta, nullable=False)
    descricao       = Column(Text, nullable=True)

    # relações
    cliente         = relationship("Client", back_populates="ordens_servico")
    documentos      = relationship("Document", back_populates="ordem_servico")
    financeiros     = relationship("Financial", back_populates="ordem_servico")


class Batch(Base):
    """Malote físico enviado entre escritórios."""
    __tablename__ = "batches"

    id                   = Column(Integer, primary_key=True, index=True)
    codigo_identificacao = Column(String(30), unique=True, nullable=False, index=True)
    data_envio           = Column(DateTime(timezone=True), nullable=True)
    status               = Column(Enum(StatusMalote), default=StatusMalote.aberto, nullable=False)
    observacoes          = Column(Text, nullable=True)
    criado_em            = Column(DateTime(timezone=True), server_default=func.now())

    # relações
    documentos           = relationship("Document", back_populates="malote")


class Document(Base):
    """
    Documento individual dentro de uma OS.
    Suporta hierarquia pai/filho: um 'Plano Analítico' pode ser pai
    de vários subdocumentos (históricos, ementas, etc.).
    O vínculo com malote é INDIVIDUAL – filhos podem ir em malotes diferentes do pai.
    """
    __tablename__ = "documents"

    id              = Column(Integer, primary_key=True, index=True)
    os_id           = Column(Integer, ForeignKey("service_orders.id"), nullable=False)
    malote_id       = Column(Integer, ForeignKey("batches.id"), nullable=True)
    pai_id          = Column(Integer, ForeignKey("documents.id"), nullable=True)

    tipo_documento  = Column(String(120), nullable=False)   # Ex: Programa de Estudios, Certificado de Calificaciones
    status_documento = Column(Enum(StatusDocumento), default=StatusDocumento.recebido, nullable=False)
    snapshot_url    = Column(String(512), nullable=True)    # URL da imagem de conferência
    idioma_origem   = Column(String(60), default="Espanhol")
    idioma_destino  = Column(String(60), default="Português")
    observacoes     = Column(Text, nullable=True)
    criado_em       = Column(DateTime(timezone=True), server_default=func.now())
    atualizado_em   = Column(DateTime(timezone=True), onupdate=func.now())

    # relações
    ordem_servico   = relationship("ServiceOrder", back_populates="documentos")
    malote          = relationship("Batch", back_populates="documentos")

    # auto-referência pai ↔ filhos
    pai             = relationship("Document", remote_side="Document.id", back_populates="filhos")
    filhos          = relationship("Document", back_populates="pai", cascade="all, delete-orphan")


class Financial(Base):
    """Lançamentos financeiros vinculados a uma OS."""
    __tablename__ = "financials"

    id              = Column(Integer, primary_key=True, index=True)
    os_id           = Column(Integer, ForeignKey("service_orders.id"), nullable=False)
    tipo            = Column(Enum(TipoFinanceiro), nullable=False)
    descricao       = Column(String(300), nullable=False)
    valor           = Column(Float, nullable=False)
    nf_lancada      = Column(Boolean, default=False)        # Nota fiscal emitida no sistema tributário externo?
    data_registro   = Column(DateTime(timezone=True), server_default=func.now())

    # relações
    ordem_servico   = relationship("ServiceOrder", back_populates="financeiros")


class AuditLog(Base):
    """
    Log de auditoria imutável.
    Gravado a cada operação crítica: criação/alteração de malotes,
    mudança de status de documentos, lançamento de NF, etc.
    """
    __tablename__ = "audit_logs"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable para ops automáticas
    acao             = Column(String(200), nullable=False)          # Ex: "Criou Malote MAL-2026-001"
    entidade_afetada = Column(String(100), nullable=False)          # Ex: "Batch:5", "Document:12"
    detalhes         = Column(Text, nullable=True)                  # JSON ou texto livre com diff
    data_hora        = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # relações
    user             = relationship("User", back_populates="logs")
