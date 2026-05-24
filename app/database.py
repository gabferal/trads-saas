"""
database.py – Configuração da conexão com PostgreSQL (Neon) via SQLAlchemy.
A URL do banco é lida de variáveis de ambiente para segurança.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# DATABASE_URL deve ser definida no ambiente (ex: postgresql+psycopg2://user:pwd@host/db)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_IBLjro0Psp5J@ep-falling-wildflower-aceu8am6-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

# Para bancos Neon (SSL obrigatório) a URL já vem com ?sslmode=require
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # Reconecta automaticamente após idle
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency Injection – fornece sessão de banco para cada request FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
