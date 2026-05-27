/**
 * api.js – Camada de comunicação com a API FastAPI.
 * Abstrai os fetch calls, injeta o token JWT e centraliza o tratamento de erros.
 */

const BASE_URL = '/api';

/** Recupera o token do sessionStorage. */
function getToken() {
  return sessionStorage.getItem('token') || '';
}

/**
 * Wrapper genérico para chamadas à API.
 * @param {string} path  - Caminho relativo (ex: '/documents')
 * @param {object} opts  - Opções do fetch (method, body, etc.)
 * @returns {Promise<any>} JSON da resposta
 */
async function apiFetch(path, opts = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    ...(opts.headers || {}),
  };

  const res = await fetch(`${BASE_URL}${path}`, { ...opts, headers });

  if (res.status === 401) {
    // Token expirado ou inválido → força logout
    sessionStorage.clear();
    location.reload();
    return;
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Erro desconhecido' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return null;  // No Content
  return res.json();
}

// ── Auth ───────────────────────────────────────────
const Api = {
  auth: {
    login: (email, senha) =>
      apiFetch('/auth/login', { method: 'POST', body: JSON.stringify({ email, senha }) }),
  },

  // ── Clientes ──────────────────────────────────────
  clients: {
    list: ()       => apiFetch('/clients/'),
    get:  (id)     => apiFetch(`/clients/${id}`),
    create: (data) => apiFetch('/clients/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id, data) => apiFetch(`/clients/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id)   => apiFetch(`/clients/${id}`, { method: 'DELETE' }),
  },

  // ── Gestores ──────────────────────────────────────
  gestores: {
    list: ()       => apiFetch('/gestores/'),
    get:  (id)     => apiFetch(`/gestores/${id}`),
    create: (data) => apiFetch('/gestores/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id, data) => apiFetch(`/gestores/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id)   => apiFetch(`/gestores/${id}`, { method: 'DELETE' }),
  },

  // ── Ordens de Serviço ─────────────────────────────
  orders: {
    list: (params = {}) => apiFetch('/orders/?' + new URLSearchParams(params)),
    get:  (id)          => apiFetch(`/orders/${id}`),
    create: (data)      => apiFetch('/orders/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id, data)  => apiFetch(`/orders/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },

  // ── Documentos ────────────────────────────────────
  documents: {
    list: (params = {}) => apiFetch('/documents/?' + new URLSearchParams(params)),
    get:  (id)          => apiFetch(`/documents/${id}`),
    create: (data)      => apiFetch('/documents/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id, data)  => apiFetch(`/documents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id)        => apiFetch(`/documents/${id}`, { method: 'DELETE' }),
  },

  // ── Malotes ───────────────────────────────────────
  batches: {
    list: (params = {}) => apiFetch('/batches/?' + new URLSearchParams(params)),
    get:  (id)          => apiFetch(`/batches/${id}`),
    create: (data)      => apiFetch('/batches/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id, data)  => apiFetch(`/batches/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id)        => apiFetch(`/batches/${id}`, { method: 'DELETE' }),
    bulkAssign: (data)  => apiFetch('/batches/bulk-assign', { method: 'POST', body: JSON.stringify(data) }),
  },

  // ── Financeiro ────────────────────────────────────
  financial: {
    list: (params = {}) => apiFetch('/financial/?' + new URLSearchParams(params)),
    create: (data)      => apiFetch('/financial/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id, data)  => apiFetch(`/financial/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },

  // ── Dashboard ─────────────────────────────────────
  dashboard: {
    metrics: () => apiFetch('/dashboard/metrics'),
  },

  // ── Auditoria ─────────────────────────────────────
  audit: {
    list: (params = {}) => apiFetch('/audit/?' + new URLSearchParams(params)),
  },
};
