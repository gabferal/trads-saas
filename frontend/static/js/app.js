/**
 * app.js – Lógica principal da SPA TranslaDoc.
 * Gerencia navegação, carregamento de dados e operações CRUD.
 */

// ── Estado global ─────────────────────────────────────────────
let currentUser  = null;
let allClients   = [];
let allOrders    = [];
let allBatches   = [];
let allGestores  = [];
let statusChart  = null;

// ── Bootstrap ────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const token = sessionStorage.getItem('token');
  const user  = sessionStorage.getItem('user');

  if (token && user) {
    currentUser = JSON.parse(user);
    showApp();
  } else {
    document.getElementById('login-screen').classList.remove('hidden');
  }

  // Navegação por sidebar
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      navigate(item.dataset.page);
    });
  });
});

// ── Auth ──────────────────────────────────────────────────────

async function handleLogin() {
  const email = document.getElementById('login-email').value.trim();
  const senha = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');

  errEl.classList.add('hidden');
  try {
    const data = await Api.auth.login(email, senha);
    sessionStorage.setItem('token', data.access_token);
    sessionStorage.setItem('user', JSON.stringify(data.user));
    currentUser = data.user;
    document.getElementById('login-screen').classList.add('hidden');
    showApp();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
}

function handleLogout() {
  sessionStorage.clear();
  location.reload();
}

// ── App Init ──────────────────────────────────────────────────

function showApp() {
  document.getElementById('login-screen').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  document.getElementById('user-name-display').textContent = currentUser.nome.split(' ')[0];
  navigate('dashboard');
}

// ── Navigation ────────────────────────────────────────────────

function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const pageEl = document.getElementById(`page-${page}`);
  const navEl  = document.querySelector(`[data-page="${page}"]`);

  if (pageEl) pageEl.classList.add('active');
  if (navEl)  navEl.classList.add('active');

  // Carrega dados da página ativa
  const loaders = {
    dashboard:  loadDashboard,
    clientes:   loadClientes,
    gestores:   loadGestores,
    ordens:     loadOrdens,
    documentos: loadDocumentos,
    malotes:    loadMalotes,
    financeiro: loadFinanceiro,
    auditoria:  loadAuditoria,
  };
  loaders[page]?.();
}

// ── Helpers UI ────────────────────────────────────────────────

function toast(msg, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

function openModal(id) {
  document.getElementById(id).classList.remove('hidden');
}

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}

function badgeStatus(status) {
  const map = {
    'Recebido':    'badge-recebido',
    'Em Tradução': 'badge-em-traducao',
    'Traduzido':   'badge-traduzido',
    'Em Trânsito': 'badge-em-transito',
    'Em Trânsito para Assunção': 'badge-em-transito',
    'Finalizado':  'badge-finalizado',
    'Aberto':      'badge-aberto',
    'Entregue':    'badge-entregue',
    'Entrada':     'badge-entrada',
    'Saída':       'badge-saida',
  };
  const cls = map[status] || 'badge-recebido';
  return `<span class="badge ${cls}">${status}</span>`;
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function formatCurrency(val) {
  return 'R$ ' + Number(val).toLocaleString('pt-BR', { minimumFractionDigits: 2 });
}

// ── Dashboard ─────────────────────────────────────────────────

async function loadDashboard() {
  try {
    const [metrics, docs, logs, orders, clients] = await Promise.all([
      Api.dashboard.metrics(),
      Api.documents.list({ limit: 8 }),
      Api.audit.list({ limit: 10 }),
      Api.orders.list(),
      Api.clients.list(),
    ]);

    allOrders  = orders;
    allClients = clients;

    const clientMap   = Object.fromEntries(clients.map(c => [c.id, c.nome_completo]));
    const osClientMap = Object.fromEntries(orders.map(o => [o.id, clientMap[o.cliente_id] || '—']));

    // Métricas
    setMetric('metric-pendentes',   metrics.documentos_pendentes_traducao, metrics.documentos_pendentes_traducao > 5 ? 'warn' : '');
    setMetric('metric-transito',    metrics.documentos_em_transito, '');
    setMetric('metric-malotes',     metrics.malotes_abertos, '');
    setMetric('metric-faturamento', formatCurrency(metrics.faturamento_mes), 'good');
    setMetric('metric-fiscal',      metrics.pendencias_fiscais, metrics.pendencias_fiscais > 0 ? 'alert' : 'good');

    // Gráfico de status
    renderStatusChart(metrics.documentos_por_status || {});

    // Documentos recentes
    renderDashDocs(docs, osClientMap);

    // Auditoria recente
    renderAuditList(logs, 'dash-audit-list');

  } catch (err) {
    toast('Erro ao carregar dashboard: ' + err.message, 'error');
  }
}

function setMetric(id, value, cls) {
  const card = document.getElementById(id);
  card.classList.remove('loading', 'warn', 'good', 'alert');
  if (cls) card.classList.add(cls);
  card.querySelector('.metric-value').textContent = value;
}

function renderStatusChart(data) {
  const canvas = document.getElementById('chart-status');
  if (!canvas) return;

  if (statusChart) { statusChart.destroy(); statusChart = null; }

  const labels = ['Recebido', 'Em Tradução', 'Traduzido', 'Em Trânsito', 'Finalizado'];
  const values = labels.map(l => data[l] || 0);
  const colors = ['#aeaeb2', '#ff9500', '#007aff', '#ff6b00', '#34c759'];

  if (values.every(v => v === 0)) {
    canvas.parentElement.innerHTML = '<div class="loading-row">Sem documentos ainda.</div>';
    return;
  }

  statusChart = new Chart(canvas.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#fff',
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '62%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            font: { size: 11, family: 'Inter, -apple-system, sans-serif' },
            color: '#636366',
            padding: 10,
            boxWidth: 10,
            boxHeight: 10,
            usePointStyle: true,
            pointStyle: 'circle',
          },
        },
        tooltip: {
          callbacks: {
            label: ctx => `  ${ctx.label}: ${ctx.raw}`,
          },
        },
      },
    },
  });
}

function renderDashDocs(docs, osClientMap = {}) {
  const el = document.getElementById('dash-docs-list');
  if (!docs.length) { el.innerHTML = '<div class="loading-row">Nenhum documento encontrado.</div>'; return; }
  el.innerHTML = `<table>
    <thead><tr><th>Tipo</th><th>Status</th><th>OS</th><th>Criado</th></tr></thead>
    <tbody>${docs.map(d => {
      const nome = (osClientMap[d.os_id] || '—').replace(/'/g, '&#39;');
      return `<tr>
        <td>${d.tipo_documento}</td>
        <td>${badgeStatus(d.status_documento)}</td>
        <td><span class="os-link" onclick="showOsPopover(event,${d.os_id},'${nome}')">#${d.os_id}</span></td>
        <td>${formatDate(d.criado_em)}</td>
      </tr>`;
    }).join('')}</tbody>
  </table>`;
}

function showOsPopover(event, osId, clientName) {
  event.stopPropagation();
  const pop = document.getElementById('os-popover');
  document.getElementById('os-popover-name').textContent = clientName;
  const x = Math.min(event.clientX - 10, window.innerWidth - 210);
  const y = event.clientY + 12;
  pop.style.left = x + 'px';
  pop.style.top  = y + 'px';
  pop.classList.remove('hidden');
}

document.addEventListener('click', () => {
  document.getElementById('os-popover')?.classList.add('hidden');
});

// ── Clientes ──────────────────────────────────────────────────

async function loadClientes() {
  try {
    allClients = await Api.clients.list();
    const el = document.getElementById('clientes-table');
    if (!allClients.length) { el.innerHTML = '<div class="loading-row">Nenhum cliente cadastrado.</div>'; return; }
    el.innerHTML = `<table>
      <thead><tr><th>Nome</th><th>CPF/CNPJ</th><th>E-mail</th><th>WhatsApp</th><th>Cidade/UF</th><th>Ações</th></tr></thead>
      <tbody>${allClients.map(c => `<tr>
        <td><strong>${c.nome_completo}</strong></td>
        <td>${c.cpf_cnpj || '<span class="text-muted">—</span>'}</td>
        <td>${c.email || '<span class="text-muted">—</span>'}</td>
        <td>
          <a class="btn-whatsapp" href="https://wa.me/${c.telefone_whatsapp}" target="_blank" rel="noopener">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>
            ${c.telefone_whatsapp}
          </a>
        </td>
        <td>${c.cidade ? `${c.cidade}${c.estado ? '/' + c.estado.toUpperCase() : ''}` : '<span class="text-muted">—</span>'}</td>
        <td style="white-space:nowrap">
          <button class="btn btn-sm" onclick="novaOSParaCliente(${c.id}, '${c.nome_completo.replace(/'/g,"\\'")}')">+ OS</button>
          <button class="btn-icon" title="Excluir cliente" onclick="deletarCliente(${c.id}, '${c.nome_completo.replace(/'/g,"\\'")}')">✕</button>
        </td>
      </tr>`).join('')}</tbody>
    </table>`;
  } catch (err) {
    toast('Erro ao carregar clientes: ' + err.message, 'error');
  }
}

async function deletarCliente(id, nome) {
  if (!confirm(`Excluir cliente "${nome}"? Esta ação não pode ser desfeita.`)) return;
  try {
    await Api.clients.delete(id);
    toast('Cliente excluído.');
    loadClientes();
  } catch (err) { toast(err.message, 'error'); }
}

async function salvarCliente() {
  const data = {
    nome_completo:     document.getElementById('c-nome').value.trim(),
    telefone_whatsapp: document.getElementById('c-whatsapp').value.trim(),
    cpf_cnpj:          document.getElementById('c-cpf-cnpj').value.trim() || null,
    email:             document.getElementById('c-email').value.trim() || null,
    endereco:          document.getElementById('c-endereco').value.trim() || null,
    cep:               document.getElementById('c-cep').value.trim() || null,
    cidade:            document.getElementById('c-cidade').value.trim() || null,
    estado:            document.getElementById('c-estado').value.trim().toUpperCase() || null,
    observacoes:       document.getElementById('c-obs').value.trim() || null,
  };
  if (!data.nome_completo || !data.telefone_whatsapp) { toast('Preencha nome e WhatsApp.', 'error'); return; }
  try {
    await Api.clients.create(data);
    toast('Cliente cadastrado!');
    closeModal('modal-cliente');
    loadClientes();
  } catch (err) { toast(err.message, 'error'); }
}

// ── Gestores ──────────────────────────────────────────────────

async function loadGestores() {
  try {
    allGestores = await Api.gestores.list();
    const el = document.getElementById('gestores-table');
    if (!allGestores.length) { el.innerHTML = '<div class="loading-row">Nenhum gestor cadastrado.</div>'; return; }
    el.innerHTML = `<table>
      <thead><tr><th>Nome</th><th>Observações</th><th>Cadastro</th><th>Ações</th></tr></thead>
      <tbody>${allGestores.map(g => `<tr>
        <td><strong>${g.nome}</strong></td>
        <td class="text-muted">${g.observacoes || '—'}</td>
        <td>${formatDate(g.criado_em)}</td>
        <td>
          <button class="btn-icon" title="Excluir gestor" onclick="deletarGestor(${g.id}, '${g.nome.replace(/'/g,"\\'")}')">✕</button>
        </td>
      </tr>`).join('')}</tbody>
    </table>`;
  } catch (err) {
    toast('Erro ao carregar gestores: ' + err.message, 'error');
  }
}

async function salvarGestor() {
  const data = {
    nome:        document.getElementById('g-nome').value.trim(),
    observacoes: document.getElementById('g-obs').value.trim() || null,
  };
  if (!data.nome) { toast('Informe o nome do gestor.', 'error'); return; }
  try {
    await Api.gestores.create(data);
    toast('Gestor cadastrado!');
    closeModal('modal-gestor');
    document.getElementById('g-nome').value = '';
    document.getElementById('g-obs').value = '';
    loadGestores();
  } catch (err) { toast(err.message, 'error'); }
}

async function deletarGestor(id, nome) {
  if (!confirm(`Excluir gestor "${nome}"? As OS vinculadas serão desvinculadas.`)) return;
  try {
    await Api.gestores.delete(id);
    toast('Gestor excluído.');
    loadGestores();
  } catch (err) { toast(err.message, 'error'); }
}

// ── Ordens de Serviço ─────────────────────────────────────────

async function loadOrdens() {
  try {
    const gestorFiltro = document.getElementById('os-filter-gestor')?.value || '';
    const params = gestorFiltro ? { gestor_id: gestorFiltro } : {};

    [allOrders, allClients, allGestores] = await Promise.all([
      Api.orders.list(params),
      Api.clients.list(),
      Api.gestores.list(),
    ]);

    // Popula filtro de gestor
    const filterSel = document.getElementById('os-filter-gestor');
    if (filterSel && filterSel.options.length <= 1) {
      allGestores.forEach(g => {
        const opt = document.createElement('option');
        opt.value = g.id;
        opt.textContent = g.nome;
        filterSel.appendChild(opt);
      });
      if (gestorFiltro) filterSel.value = gestorFiltro;
    }

    const clientMap = Object.fromEntries(allClients.map(c => [c.id, c.nome_completo]));
    const el = document.getElementById('os-table');
    if (!allOrders.length) { el.innerHTML = '<div class="loading-row">Nenhuma OS encontrada.</div>'; return; }
    el.innerHTML = `<table>
      <thead><tr><th>#</th><th>Cliente</th><th>Gestor</th><th>Descrição</th><th>Status</th><th>Abertura</th><th>Ações</th></tr></thead>
      <tbody>${allOrders.map(o => `<tr>
        <td>#${o.id}</td>
        <td>${clientMap[o.cliente_id] || '—'}</td>
        <td>${o.gestor_nome ? `<span class="badge" style="background:var(--accent-dim);color:var(--accent)">${o.gestor_nome}</span>` : '<span class="text-muted">—</span>'}</td>
        <td class="text-muted" style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${o.descricao || '—'}</td>
        <td>${badgeStatus(o.status_geral)}</td>
        <td>${formatDate(o.data_abertura)}</td>
        <td>
          <select class="status-select" onchange="updateOSStatus(${o.id}, this.value)">
            ${['Aberta','Em Andamento','Concluída','Cancelada'].map(s =>
              `<option value="${s}" ${s === o.status_geral ? 'selected' : ''}>${s}</option>`
            ).join('')}
          </select>
        </td>
      </tr>`).join('')}</tbody>
    </table>`;
  } catch (err) {
    toast('Erro ao carregar OS: ' + err.message, 'error');
  }
}

async function updateOSStatus(id, status) {
  try {
    await Api.orders.update(id, { status_geral: status });
    toast('Status atualizado!');
  } catch (err) { toast(err.message, 'error'); }
}

async function salvarOS() {
  const gestorVal = document.getElementById('os-gestor-id').value;
  const data = {
    cliente_id: parseInt(document.getElementById('os-cliente-id').value),
    gestor_id:  gestorVal ? parseInt(gestorVal) : null,
    descricao:  document.getElementById('os-desc').value.trim() || null,
  };
  if (!data.cliente_id) { toast('Selecione um cliente.', 'error'); return; }
  try {
    await Api.orders.create(data);
    toast('Ordem de Serviço criada!');
    closeModal('modal-os');
    loadOrdens();
  } catch (err) { toast(err.message, 'error'); }
}

function novaOSParaCliente(clienteId, nome) {
  navigate('ordens');
  setTimeout(async () => {
    openModal('modal-os');
    await Promise.all([
      populateClienteSelect('os-cliente-id', clienteId),
      populateGestorSelect('os-gestor-id'),
    ]);
  }, 100);
}

// ── Documentos ────────────────────────────────────────────────

async function loadDocumentos() {
  try {
    const status = document.getElementById('doc-filter-status')?.value || '';
    const params = status ? { status } : {};
    const [docs, orders, clients] = await Promise.all([
      Api.documents.list(params),
      Api.orders.list(),
      Api.clients.list(),
    ]);
    allOrders  = orders;
    allClients = clients;
    const clientMap = Object.fromEntries(clients.map(c => [c.id, c.nome_completo]));
    const osClientMap = Object.fromEntries(orders.map(o => [o.id, clientMap[o.cliente_id] || '—']));
    renderDocsTable(docs, osClientMap);
  } catch (err) {
    toast('Erro ao carregar documentos: ' + err.message, 'error');
  }
}

function renderDocsTable(docs, osClientMap = {}) {
  const el = document.getElementById('docs-table');
  if (!docs.length) { el.innerHTML = '<div class="loading-row">Nenhum documento encontrado.</div>'; return; }

  el.innerHTML = `<table>
    <thead><tr><th>Tipo de Documento</th><th>Cliente</th><th>OS</th><th>Status</th><th>Malote</th><th>Snapshot</th><th></th></tr></thead>
    <tbody>${docs.map(doc => {
      const cliente = osClientMap[doc.os_id] || '—';
      const snapshotLink = doc.snapshot_url
        ? `<a class="snapshot-link" href="${doc.snapshot_url}" target="_blank">Ver</a>`
        : '<span class="text-muted">—</span>';
      return `<tr>
        <td>${doc.tipo_documento}</td>
        <td class="text-muted">${cliente}</td>
        <td>#${doc.os_id}</td>
        <td>
          <select class="status-select" onchange="updateDocStatus(${doc.id}, this.value)">
            ${['Recebido','Em Tradução','Traduzido','Em Trânsito','Finalizado'].map(s =>
              `<option value="${s}" ${s === doc.status_documento ? 'selected' : ''}>${s}</option>`
            ).join('')}
          </select>
        </td>
        <td>${doc.malote_id ? `#${doc.malote_id}` : '<span class="text-muted">—</span>'}</td>
        <td>${snapshotLink}</td>
        <td><button class="btn-icon" title="Excluir" onclick="deletarDoc(${doc.id})">✕</button></td>
      </tr>`;
    }).join('')}</tbody>
  </table>`;
}

async function updateDocStatus(id, status) {
  try {
    await Api.documents.update(id, { status_documento: status });
    toast('Status atualizado!');
  } catch (err) { toast(err.message, 'error'); }
}

async function deletarDoc(id) {
  if (!confirm('Confirma exclusão do documento?')) return;
  try {
    await Api.documents.delete(id);
    toast('Documento excluído.');
    loadDocumentos();
  } catch (err) { toast(err.message, 'error'); }
}

async function salvarDocumento() {
  const data = {
    os_id:          parseInt(document.getElementById('doc-os-id').value),
    tipo_documento: document.getElementById('doc-tipo').value.trim(),
    idioma_origem:  document.getElementById('doc-origem').value.trim(),
    idioma_destino: document.getElementById('doc-destino').value.trim(),
    snapshot_url:   document.getElementById('doc-snapshot').value.trim() || null,
    observacoes:    document.getElementById('doc-obs').value.trim() || null,
  };
  if (!data.os_id || !data.tipo_documento) { toast('Preencha OS e tipo do documento.', 'error'); return; }
  try {
    await Api.documents.create(data);
    toast('Documento criado!');
    closeModal('modal-documento');
    loadDocumentos();
  } catch (err) { toast(err.message, 'error'); }
}

// ── Malotes ───────────────────────────────────────────────────

async function loadMalotes() {
  try {
    [allBatches] = await Promise.all([Api.batches.list()]);

    // Popula select de malote no bulk assign
    const bulkSelect = document.getElementById('bulk-malote-select');
    bulkSelect.innerHTML = '<option value="">Selecione o malote destino...</option>' +
      allBatches.filter(b => b.status !== 'Finalizado')
        .map(b => `<option value="${b.id}">${b.codigo_identificacao} (${b.status})</option>`).join('');

    // Carrega documentos sem malote para o bulk assign
    const semMalote = await Api.documents.list({ sem_malote: true });
    renderBulkDocs(semMalote);

    // Tabela de malotes
    const el = document.getElementById('malotes-table');
    if (!allBatches.length) { el.innerHTML = '<div class="loading-row">Nenhum malote cadastrado.</div>'; return; }
    el.innerHTML = `<table>
      <thead><tr><th>Código</th><th>Status</th><th>Data Envio</th><th>Ações</th></tr></thead>
      <tbody>${allBatches.map(b => `<tr>
        <td><strong>${b.codigo_identificacao}</strong></td>
        <td>${badgeStatus(b.status)}</td>
        <td>${formatDate(b.data_envio)}</td>
        <td>
          <select class="status-select" onchange="updateMaloteStatus(${b.id}, this.value)">
            ${['Aberto','Em Trânsito para Assunção','Entregue','Finalizado'].map(s =>
              `<option value="${s}" ${s === b.status ? 'selected' : ''}>${s}</option>`
            ).join('')}
          </select>
          <button class="btn-icon" onclick="deletarMalote(${b.id})" title="Excluir">✕</button>
        </td>
      </tr>`).join('')}</tbody>
    </table>`;
  } catch (err) {
    toast('Erro ao carregar malotes: ' + err.message, 'error');
  }
}

function renderBulkDocs(docs) {
  const el = document.getElementById('bulk-docs-list');
  if (!docs.length) { el.innerHTML = '<div class="loading-row" style="font-size:12px">Todos os documentos já estão em malotes.</div>'; return; }
  el.innerHTML = docs.map(d => `
    <label class="bulk-doc-item" onclick="this.classList.toggle('selected')">
      <input type="checkbox" value="${d.id}" />
      <span>${d.tipo_documento} <span class="text-muted">(OS#${d.os_id})</span></span>
    </label>
  `).join('');
}

async function executeBulkAssign() {
  const batchId = parseInt(document.getElementById('bulk-malote-select').value);
  if (!batchId) { toast('Selecione um malote.', 'error'); return; }

  const checked = [...document.querySelectorAll('.bulk-doc-item.selected input')].map(i => parseInt(i.value));
  if (!checked.length) { toast('Selecione ao menos um documento.', 'error'); return; }

  try {
    const res = await Api.batches.bulkAssign({ document_ids: checked, batch_id: batchId });
    toast(`${res.total} documento(s) atribuído(s) ao malote!`);
    loadMalotes();
  } catch (err) { toast(err.message, 'error'); }
}

async function updateMaloteStatus(id, status) {
  const payload = { status };
  if (status === 'Em Trânsito para Assunção') {
    payload.data_envio = new Date().toISOString();
  }
  try {
    await Api.batches.update(id, payload);
    toast('Status do malote atualizado!');
    loadMalotes();
  } catch (err) { toast(err.message, 'error'); }
}

async function deletarMalote(id) {
  if (!confirm('Confirma exclusão do malote? Os documentos vinculados serão desvinculados.')) return;
  try {
    await Api.batches.delete(id);
    toast('Malote excluído.');
    loadMalotes();
  } catch (err) { toast(err.message, 'error'); }
}

async function salvarMalote() {
  const data = {
    codigo_identificacao: document.getElementById('mal-codigo').value.trim(),
    observacoes:          document.getElementById('mal-obs').value.trim() || null,
  };
  if (!data.codigo_identificacao) { toast('Informe o código do malote.', 'error'); return; }
  try {
    await Api.batches.create(data);
    toast('Malote criado!');
    closeModal('modal-malote');
    loadMalotes();
  } catch (err) { toast(err.message, 'error'); }
}

// ── Financeiro ────────────────────────────────────────────────

async function loadFinanceiro() {
  try {
    const [lancamentos, orders] = await Promise.all([Api.financial.list(), Api.orders.list()]);
    allOrders = orders;
    const el = document.getElementById('fin-table');
    if (!lancamentos.length) { el.innerHTML = '<div class="loading-row">Nenhum lançamento encontrado.</div>'; return; }
    el.innerHTML = `<table>
      <thead><tr><th>OS</th><th>Tipo</th><th>Descrição</th><th>Valor</th><th>NF</th><th>Data</th><th>Ação</th></tr></thead>
      <tbody>${lancamentos.map(f => `<tr>
        <td>#${f.os_id}</td>
        <td>${badgeStatus(f.tipo)}</td>
        <td>${f.descricao}</td>
        <td class="${f.tipo === 'Entrada' ? 'amount-pos' : 'amount-neg'}">${formatCurrency(f.valor)}</td>
        <td>
          ${f.nf_lancada
            ? '<span class="badge badge-nf-ok">Lançada ✓</span>'
            : `<button class="btn btn-sm" onclick="marcarNF(${f.id})">Marcar NF</button>`}
        </td>
        <td>${formatDate(f.data_registro)}</td>
        <td></td>
      </tr>`).join('')}</tbody>
    </table>`;
  } catch (err) {
    toast('Erro ao carregar financeiro: ' + err.message, 'error');
  }
}

async function marcarNF(id) {
  try {
    await Api.financial.update(id, { nf_lancada: true });
    toast('NF marcada como lançada!');
    loadFinanceiro();
  } catch (err) { toast(err.message, 'error'); }
}

async function salvarFinanceiro() {
  const data = {
    os_id:    parseInt(document.getElementById('fin-os-id').value),
    tipo:     document.getElementById('fin-tipo').value,
    descricao: document.getElementById('fin-desc').value.trim(),
    valor:    parseFloat(document.getElementById('fin-valor').value),
  };
  if (!data.os_id || !data.descricao || isNaN(data.valor)) { toast('Preencha todos os campos.', 'error'); return; }
  try {
    await Api.financial.create(data);
    toast('Lançamento registrado!');
    closeModal('modal-financeiro');
    loadFinanceiro();
  } catch (err) { toast(err.message, 'error'); }
}

// ── Auditoria ─────────────────────────────────────────────────

async function loadAuditoria() {
  try {
    const logs = await Api.audit.list({ limit: 100 });
    const el = document.getElementById('audit-table');
    if (!logs.length) { el.innerHTML = '<div class="loading-row">Nenhum log registrado.</div>'; return; }
    el.innerHTML = `<table>
      <thead><tr><th>Ação</th><th>Entidade</th><th>Usuário</th><th>Data/Hora</th></tr></thead>
      <tbody>${logs.map(l => `<tr>
        <td>${l.acao}</td>
        <td><code style="font-size:11px;color:var(--accent)">${l.entidade_afetada}</code></td>
        <td>${l.user_nome || '<span class="text-muted">Sistema</span>'}</td>
        <td>${new Date(l.data_hora).toLocaleString('pt-BR')}</td>
      </tr>`).join('')}</tbody>
    </table>`;
  } catch (err) {
    toast('Erro ao carregar auditoria: ' + err.message, 'error');
  }
}

function renderAuditList(logs, containerId) {
  const el = document.getElementById(containerId);
  if (!logs.length) { el.innerHTML = '<div class="loading-row">Sem atividade recente.</div>'; return; }
  el.innerHTML = logs.map(l => `
    <div class="audit-item">
      <div class="audit-action">${l.acao}</div>
      <div class="audit-meta">${l.entidade_afetada} · ${new Date(l.data_hora).toLocaleString('pt-BR')}</div>
    </div>
  `).join('');
}

// ── Populate Selects ──────────────────────────────────────────

async function populateClienteSelect(selectId, selectedId = null) {
  if (!allClients.length) allClients = await Api.clients.list();
  const sel = document.getElementById(selectId);
  sel.innerHTML = allClients.map(c =>
    `<option value="${c.id}" ${selectedId == c.id ? 'selected' : ''}>${c.nome_completo}</option>`
  ).join('');
}

async function populateGestorSelect(selectId, selectedId = null) {
  if (!allGestores.length) allGestores = await Api.gestores.list();
  const sel = document.getElementById(selectId);
  // Mantém a opção "Nenhum" e adiciona gestores
  const base = sel.options[0]?.value === '' ? sel.options[0].outerHTML : '<option value="">— Nenhum gestor —</option>';
  sel.innerHTML = base + allGestores.map(g =>
    `<option value="${g.id}" ${selectedId == g.id ? 'selected' : ''}>${g.nome}</option>`
  ).join('');
}

async function populateOSSelect(selectId) {
  if (!allOrders.length) allOrders = await Api.orders.list();
  const sel = document.getElementById(selectId);
  sel.innerHTML = allOrders.map(o =>
    `<option value="${o.id}">#${o.id} – OS${o.id}</option>`
  ).join('');
}

// Preenche selects quando modais abrem
document.getElementById('modal-os').addEventListener('click', async (e) => {
  if (e.target.closest('.modal') && !document.getElementById('os-cliente-id').options.length) {
    await populateClienteSelect('os-cliente-id');
    await populateGestorSelect('os-gestor-id');
  }
});

document.getElementById('modal-documento').addEventListener('click', async (e) => {
  if (e.target.closest('.modal') && !document.getElementById('doc-os-id').options.length) {
    await populateOSSelect('doc-os-id');
  }
});

document.getElementById('modal-financeiro').addEventListener('click', async (e) => {
  if (e.target.closest('.modal') && !document.getElementById('fin-os-id').options.length) {
    await populateOSSelect('fin-os-id');
  }
});

// Fecha modais ao clicar no overlay
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) overlay.classList.add('hidden');
  });
});
