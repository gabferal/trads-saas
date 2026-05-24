"""
auth.py – Utilitários de autenticação: hash de senha e JWT simples.
"""

import os
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY  = os.getenv("SECRET_KEY", "change-me-in-production-please")
ALGORITHM   = "HS256"
TOKEN_EXPIRE_HOURS = 8

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    """Gera o hash da senha usando bcrypt puro."""
    salt = bcrypt.gensalt()
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), salt)
    # Retorna como string para ser salva no banco PostgreSQL
    return senha_hash.decode('utf-8')

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    """Verifica se a senha plana bate com o hash salvo."""
    return bcrypt.checkpw(senha_plana.encode('utf-8'), senha_hash.encode('utf-8'))


def criar_token(user_id: int, nome: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "nome": nome, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decodificar_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
