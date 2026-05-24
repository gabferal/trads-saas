"""
main.py – Ponto de entrada da aplicação FastAPI.
Registra todos os routers, middleware de autenticação JWT e serve o frontend estático.
"""

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.database import engine
from app.models import Base
from app.auth import decodificar_token

# Importa todos os routers
from app.routers import (
    auth, clients, orders, documents, batches, financial, dashboard, audit
)


# ──────────────────────────────────────────────
# Lifespan: cria tabelas na inicialização
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria todas as tabelas se não existirem (produção usa Alembic)
    Base.metadata.create_all(bind=engine)
    yield


# ──────────────────────────────────────────────
# Aplicação
# ──────────────────────────────────────────────

app = FastAPI(
    title="TranslaDoc – Gestão de Traduções e Legalizações",
    version="1.0.0",
    description="Sistema de gestão operacional, documental e financeira para escritórios de tradução.",
    lifespan=lifespan,
)

# CORS – ajustar origins em produção
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Middleware de autenticação JWT
# ──────────────────────────────────────────────

ROTAS_PUBLICAS = {"/api/auth/login", "/api/auth/register", "/docs", "/openapi.json", "/"}

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Extrai o user_id do token JWT e coloca em request.state.
    Rotas públicas passam sem token. Rotas de API retornam 401 se token inválido.
    """
    path = request.url.path

    # Libera rotas públicas e arquivos estáticos
    if path in ROTAS_PUBLICAS or path.startswith("/static") or not path.startswith("/api"):
        response = await call_next(request)
        return response

    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    payload = decodificar_token(token) if token else None

    if not payload:
        return Response(content='{"detail":"Não autenticado"}', status_code=401, media_type="application/json")

    request.state.user_id = int(payload.get("sub", 0))
    response = await call_next(request)
    return response


# ──────────────────────────────────────────────
# Registro dos routers (prefixo /api)
# ──────────────────────────────────────────────

API_PREFIX = "/api"

app.include_router(auth.router,       prefix=API_PREFIX)
app.include_router(clients.router,    prefix=API_PREFIX)
app.include_router(orders.router,     prefix=API_PREFIX)
app.include_router(documents.router,  prefix=API_PREFIX)
app.include_router(batches.router,    prefix=API_PREFIX)
app.include_router(financial.router,  prefix=API_PREFIX)
app.include_router(dashboard.router,  prefix=API_PREFIX)
app.include_router(audit.router,      prefix=API_PREFIX)


# ──────────────────────────────────────────────
# Serve o frontend estático
# ──────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

@app.get("/", include_in_schema=False)
async def serve_frontend():
    return FileResponse("frontend/index.html")
