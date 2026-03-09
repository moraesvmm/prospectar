/* ========================================
   ProspectaBR — Frontend Application Logic
   ======================================== */

const API_BASE = '';
let authToken = localStorage.getItem('authToken');
let currentUser = null;

// ========================================
// Initialization
// ========================================
document.addEventListener('DOMContentLoaded', () => {
    if (authToken) {
        fetchCurrentUser();
    }
    loadStates();
    loadDataStats();
});

// ========================================
// Navigation
// ========================================
function showPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));

    const pageEl = document.getElementById(`page-${page}`);
    const navEl = document.getElementById(`nav-${page}`);

    if (pageEl) pageEl.classList.add('active');
    if (navEl) navEl.classList.add('active');

    if (page === 'data') {
        loadDataStats();
        loadImportStatus();
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ========================================
// Auth
// ========================================
function showModal(name) {
    const modal = document.getElementById(`modal-${name}`);
    if (modal) modal.classList.add('active');
}

function closeModal(name) {
    const modal = document.getElementById(`modal-${name}`);
    if (modal) modal.classList.remove('active');
}

function switchModal(from, to) {
    closeModal(from);
    setTimeout(() => showModal(to), 200);
}

async function handleLogin(e) {
    e.preventDefault();
    const errorEl = document.getElementById('loginError');
    errorEl.classList.add('hidden');

    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();

        if (!res.ok) {
            errorEl.textContent = data.detail || 'Erro ao fazer login';
            errorEl.classList.remove('hidden');
            return;
        }

        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);
        currentUser = data.user;
        updateAuthUI();
        closeModal('login');
        showToast('Login realizado com sucesso!', 'success');
    } catch (err) {
        errorEl.textContent = 'Erro de conexão com o servidor';
        errorEl.classList.remove('hidden');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const errorEl = document.getElementById('registerError');
    errorEl.classList.add('hidden');

    const body = {
        company_name: document.getElementById('regCompany').value,
        email: document.getElementById('regEmail').value,
        password: document.getElementById('regPassword').value,
        business_sector: document.getElementById('regSector').value || null
    };

    try {
        const res = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await res.json();

        if (!res.ok) {
            errorEl.textContent = data.detail || 'Erro ao cadastrar';
            errorEl.classList.remove('hidden');
            return;
        }

        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);
        currentUser = data.user;
        updateAuthUI();
        closeModal('register');
        showToast('Conta criada com sucesso! Bem-vindo(a)!', 'success');

        if (body.business_sector) {
            document.getElementById('businessSector').value = body.business_sector;
        }
    } catch (err) {
        errorEl.textContent = 'Erro de conexão com o servidor';
        errorEl.classList.remove('hidden');
    }
}

async function fetchCurrentUser() {
    try {
        const res = await fetch(`${API_BASE}/api/auth/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        if (res.ok) {
            currentUser = await res.json();
            updateAuthUI();
        } else if (res.status === 401) {
            // Token truly expired or invalid — clear it
            authToken = null;
            currentUser = null;
            localStorage.removeItem('authToken');
            updateAuthUI();
        }
        // For other errors (500, network), keep token and retry later
    } catch {
        // Network error — keep token, don't logout
    }
}

function updateAuthUI() {
    const authButtons = document.getElementById('authButtons');
    const userMenu = document.getElementById('userMenu');
    const userName = document.getElementById('userName');

    if (currentUser) {
        authButtons.classList.add('hidden');
        userMenu.classList.remove('hidden');
        userName.textContent = currentUser.company_name;
    } else {
        authButtons.classList.remove('hidden');
        userMenu.classList.add('hidden');
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    updateAuthUI();
    showToast('Logout realizado', 'info');
}

// ========================================
// States & Cities
// ========================================
async function loadStates() {
    try {
        const res = await fetch(`${API_BASE}/api/prospects/states`);
        const states = await res.json();

        const selects = [
            document.getElementById('stateSelect'),
            document.getElementById('importState')
        ];

        selects.forEach(select => {
            if (!select) return;
            const currentVal = select.value;
            select.innerHTML = '<option value="">Selecione o estado</option>';
            states.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.uf;
                opt.textContent = `${s.name} (${s.uf})`;
                select.appendChild(opt);
            });
            if (currentVal) select.value = currentVal;
        });
    } catch (err) {
        console.error('Error loading states:', err);
    }
}

async function loadCities() {
    const uf = document.getElementById('stateSelect').value;
    const citySelect = document.getElementById('citySelect');
    citySelect.innerHTML = '<option value="">Selecione a cidade</option>';

    if (!uf) return;

    try {
        const res = await fetch(`${API_BASE}/api/prospects/cities/${uf}`);
        const cities = await res.json();

        cities.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.name;
            opt.textContent = c.name;
            citySelect.appendChild(opt);
        });
    } catch (err) {
        console.error('Error loading cities:', err);
    }
}

// ========================================
// Prospect Search
// ========================================
async function searchProspects() {
    if (!authToken) {
        showModal('login');
        showToast('Faça login para buscar clientes', 'info');
        return;
    }

    const sector = document.getElementById('businessSector').value.trim();
    const uf = document.getElementById('stateSelect').value;

    if (!sector) {
        showToast('Informe o ramo de atuação da sua empresa', 'error');
        return;
    }
    if (!uf) {
        showToast('Selecione um estado', 'error');
        return;
    }

    const city = document.getElementById('citySelect').value;
    if (!city) {
        showToast('Selecione uma cidade', 'error');
        return;
    }

    // Show loading
    document.getElementById('searchResults').classList.add('hidden');
    document.getElementById('searchLoading').classList.remove('hidden');
    document.getElementById('searchBtn').disabled = true;

    try {
        const res = await fetch(`${API_BASE}/api/prospects/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                business_sector: sector,
                uf: uf,
                municipio: city
            })
        });

        const data = await res.json();

        if (!res.ok) {
            if (res.status === 401) {
                // Token expired — prompt re-login
                authToken = null;
                currentUser = null;
                localStorage.removeItem('authToken');
                updateAuthUI();
                showModal('login');
                showToast('Sessão expirada. Faça login novamente.', 'info');
            } else {
                showToast(data.detail || 'Erro na busca', 'error');
            }
            return;
        }

        displayResults(data);
    } catch (err) {
        showToast('Erro de conexão com o servidor', 'error');
    } finally {
        document.getElementById('searchLoading').classList.add('hidden');
        document.getElementById('searchBtn').disabled = false;
    }
}

function displayResults(data) {
    const resultsSection = document.getElementById('searchResults');
    const summaryEl = document.getElementById('resultsSummary');
    const countEl = document.getElementById('resultsCount');
    const cnaesEl = document.getElementById('matchedCnaes');
    const listEl = document.getElementById('resultsList');

    summaryEl.textContent = data.search_summary;
    countEl.textContent = `${data.total} empresas encontradas`;

    // Matched CNAEs tags
    cnaesEl.innerHTML = '';
    data.matched_cnaes.forEach(cnae => {
        const tag = document.createElement('span');
        tag.className = 'cnae-tag';
        tag.textContent = `${cnae.code} — ${cnae.description} (${(cnae.score * 100).toFixed(0)}%)`;
        cnaesEl.appendChild(tag);
    });

    // Results list
    listEl.innerHTML = '';
    data.results.forEach(company => {
        const card = document.createElement('div');
        card.className = 'result-card';

        const address = [company.logradouro, company.numero, company.bairro]
            .filter(Boolean)
            .join(', ');

        const contactParts = [];
        if (company.telefone) contactParts.push(`📞 ${company.telefone}`);
        if (company.email) contactParts.push(`✉️ ${company.email}`);

        card.innerHTML = `
            <div class="result-info">
                <div class="result-company-name">${company.razao_social || 'Nome não disponível'}</div>
                ${company.nome_fantasia ? `<div class="result-fantasy">${company.nome_fantasia}</div>` : ''}
                <div class="result-details">
                    <div class="result-detail">
                        <span class="result-detail-icon">📍</span>
                        ${company.municipio_nome || ''} - ${company.uf || ''}
                    </div>
                    ${address ? `<div class="result-detail"><span class="result-detail-icon">🏠</span>${address}</div>` : ''}
                    <div class="result-detail">
                        <span class="result-detail-icon">🏷️</span>
                        ${company.cnae_descricao || company.cnae_fiscal || ''}
                    </div>
                    ${contactParts.map(c => `<div class="result-detail">${c}</div>`).join('')}
                    ${company.cnpj_full ? `<div class="result-detail"><span class="result-detail-icon">📄</span>CNPJ: ${formatCNPJ(company.cnpj_full)}</div>` : ''}
                </div>
            </div>
            <div class="result-score">
                <span class="score-value">${(company.relevance_score * 100).toFixed(0)}%</span>
                <span class="score-label">Relevância</span>
            </div>
        `;
        listEl.appendChild(card);
    });

    resultsSection.classList.remove('hidden');

    if (data.total === 0) {
        listEl.innerHTML = `
            <div style="text-align: center; padding: 48px; color: var(--text-muted);">
                <div style="font-size: 3rem; margin-bottom: 16px;">🔍</div>
                <p>Nenhuma empresa encontrada para esta busca.</p>
                <p style="font-size: 0.85rem; margin-top: 8px;">Tente ampliar a região ou verifique se os dados do estado foram importados.</p>
            </div>
        `;
    }
}

function formatCNPJ(cnpj) {
    if (!cnpj || cnpj.length !== 14) return cnpj;
    return `${cnpj.slice(0,2)}.${cnpj.slice(2,5)}.${cnpj.slice(5,8)}/${cnpj.slice(8,12)}-${cnpj.slice(12)}`;
}

// ========================================
// Data Import
// ========================================
async function loadDataStats() {
    try {
        const res = await fetch(`${API_BASE}/api/data/stats`);
        const stats = await res.json();

        // Hero stats
        document.getElementById('statCompanies').textContent = formatNumber(stats.total_companies);
        document.getElementById('statStates').textContent = stats.states_imported.length;
        document.getElementById('statCnaes').textContent = formatNumber(stats.total_cnaes);

        // Data page stats
        document.getElementById('dbCompanies').textContent = formatNumber(stats.total_companies);
        document.getElementById('dbCnaes').textContent = formatNumber(stats.total_cnaes);
        document.getElementById('dbMunicipalities').textContent = formatNumber(stats.total_municipalities);
        document.getElementById('dbStates').textContent = stats.states_imported.length;

        // States list
        if (stats.states_imported.length > 0) {
            const statesImportedEl = document.getElementById('statesImported');
            const statesList = document.getElementById('statesList');
            statesImportedEl.classList.remove('hidden');
            statesList.innerHTML = stats.states_imported
                .map(s => `<span class="state-tag">${s}</span>`)
                .join('');
        }
    } catch (err) {
        console.error('Error loading stats:', err);
    }
}

async function startImport() {
    const uf = document.getElementById('importState').value;
    if (!uf) {
        showToast('Selecione um estado para importar', 'error');
        return;
    }

    const importBtn = document.getElementById('importBtn');
    importBtn.disabled = true;
    importBtn.textContent = 'Importando...';

    try {
        const res = await fetch(`${API_BASE}/api/data/import`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ uf, file_count: 10 })
        });
        const data = await res.json();

        if (!res.ok) {
            showToast(data.detail || 'Erro ao iniciar importação', 'error');
            return;
        }

        showToast(data.message, 'success');
        document.getElementById('importStatus').classList.remove('hidden');

        // Start polling for status
        pollImportStatus();
    } catch (err) {
        showToast('Erro de conexão com o servidor', 'error');
    } finally {
        importBtn.disabled = false;
        importBtn.textContent = 'Iniciar Importação';
    }
}

let pollInterval = null;

function pollImportStatus() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
        await loadImportStatus();
        await loadDataStats();
    }, 5000);
}

async function loadImportStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/data/import/status`);
        const statuses = await res.json();

        if (statuses.length === 0) return;

        document.getElementById('importStatus').classList.remove('hidden');
        const listEl = document.getElementById('importStatusList');

        listEl.innerHTML = statuses.map(s => `
            <div class="status-item">
                <span class="status-badge ${s.status}">${translateStatus(s.status)}</span>
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" style="width: ${s.progress}%"></div>
                </div>
                <span class="status-info">
                    ${s.uf_filter || ''} — ${formatNumber(s.records_imported)} empresas — ${s.progress.toFixed(1)}%
                </span>
            </div>
        `).join('');

        // Stop polling if all done
        const allDone = statuses.every(s => s.status === 'done' || s.status === 'error');
        if (allDone && pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    } catch (err) {
        console.error('Error loading import status:', err);
    }
}

function translateStatus(status) {
    const map = {
        'pending': 'Pendente',
        'downloading': 'Baixando',
        'processing': 'Processando',
        'done': 'Concluído',
        'error': 'Erro'
    };
    return map[status] || status;
}

// ========================================
// Utilities
// ========================================
function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
