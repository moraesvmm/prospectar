// app.js

const API_BASE = window.location.origin;

// DOM Elements
const pages = {
    home: document.getElementById('page-home'),
    search: document.getElementById('page-search')
};

const navLinks = {
    home: document.getElementById('nav-home'),
    search: document.getElementById('nav-search')
};

// State
let currentState = {
    lastResults: []
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStates();
    showPage('home');
});

// Navigation
function showPage(pageId) {
    // Hide all pages
    Object.values(pages).forEach(p => {
        if (p) p.classList.remove('active');
    });
    
    // Deactivate all links
    Object.values(navLinks).forEach(l => {
        if (l) l.classList.remove('active');
    });

    // Show selected
    if (pages[pageId]) {
        pages[pageId].classList.add('active');
        navLinks[pageId].classList.add('active');
    }
}

// Toast Notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '❌';
    if (type === 'warning') icon = '⚠️';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    // Initial animation frame
    requestAnimationFrame(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Prospect Search
async function loadStates() {
    try {
        const res = await fetch(`${API_BASE}/api/prospects/states`);
        const states = await res.json();
        const select = document.getElementById('stateSelect');
        
        states.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.uf;
            opt.textContent = s.name;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error('Error loading states:', err);
    }
}

async function loadCities() {
    const uf = document.getElementById('stateSelect').value;
    const citySelect = document.getElementById('citySelect');
    
    // Limpa o select antes de adicionar
    citySelect.innerHTML = '<option value="">Selecione a cidade</option>';
    
    if (!uf) return;

    try {
        const res = await fetch(`${API_BASE}/api/prospects/cities/${uf}`);
        const cities = await res.json();

        if (Array.isArray(cities)) {
            cities.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.name;
                opt.textContent = c.name;
                citySelect.appendChild(opt);
            });
        }
    } catch (err) {
        console.error('Error loading cities:', err);
        showToast('Erro ao carregar municípios da região.', 'error');
    }
}

async function searchProspects() {
    const sector = document.getElementById('businessSector').value;
    const email = document.getElementById('userEmail').value;
    const uf = document.getElementById('stateSelect').value;
    const city = document.getElementById('citySelect').value;

    if (!sector || !email || !uf || !city) {
        showToast('Preencha todos os campos obrigatórios (E-mail, Ramo, Estado e Cidade).', 'warning');
        return;
    }

    const searchBtn = document.getElementById('searchBtn');
    const loadingState = document.getElementById('searchLoading');
    const resultsPanel = document.getElementById('searchResults');
    const resultsList = document.getElementById('resultsList');

    searchBtn.disabled = true;
    loadingState.classList.remove('hidden');
    resultsPanel.classList.add('hidden');
    resultsList.innerHTML = '';
    
    currentState.lastResults = [];

    try {
        const res = await fetch(`${API_BASE}/api/prospects/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                business_sector: sector,
                email: email,
                uf: uf,
                municipio: city
            })
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || 'Erro na pesquisa');
        }

        displayResults(data);
        showToast(data.message, 'success');
        currentState.lastResults = data.results;

    } catch (err) {
        console.error('Search error:', err);
        showToast(err.message || 'Erro ao buscar clientes.', 'error');
    } finally {
        searchBtn.disabled = false;
        loadingState.classList.add('hidden');
    }
}

function displayResults(data) {
    const panel = document.getElementById('searchResults');
    const summary = document.getElementById('resultsSummary');
    const count = document.getElementById('resultsCount');
    const list = document.getElementById('resultsList');

    panel.classList.remove('hidden');
    
    // Safe output handling
    summary.innerHTML = `<p>${data.search_summary}</p>`;
    count.textContent = `${data.results_found} empresas localizadas ao vivo`;

    if (data.results.length === 0) {
        list.innerHTML = `
            <div class="glass-card" style="text-align: center; padding: 2rem;">
                <p>Nenhuma empresa encontrada com este perfil exato nesta região específica hoje.</p>
                <p>Tente expandir o ramo ou mudar a cidade.</p>
            </div>
        `;
        return;
    }

    data.results.forEach(company => {
        const card = document.createElement('div');
        card.className = 'company-card glass-card';
        
        card.innerHTML = `
            <div class="company-header">
                <h3 class="company-name">${company.nome_empresa}</h3>
            </div>
            <div class="company-body">
                <div class="company-info-item">
                    <span class="info-label">🟢 Setor IA</span>
                    <span class="info-value"><strong>${company.setor}</strong></span>
                </div>
                <div class="company-info-item">
                    <span class="info-label">📍 Endereço</span>
                    <span class="info-value">${company.endereco}</span>
                </div>
                <div class="company-info-item">
                    <span class="info-label">📞 Telefone</span>
                    <span class="info-value">${company.telefone}</span>
                </div>
                <div class="company-info-item">
                    <span class="info-label">🌐 Web</span>
                    <span class="info-value" style="color:#06b6d4;">${company.website}</span>
                </div>
            </div>
        `;
        list.appendChild(card);
    });
}

function downloadCSV() {
    if (!currentState.lastResults || currentState.lastResults.length === 0) {
        showToast("Nenhum dado para baixar. Faça a varredura primeiro.", "warning");
        return;
    }

    const headers = ['Nome da Empresa', 'Setor Detectado (IA)', 'Telefone', 'Endereço', 'Website'];
    
    let csvContent = "data:text/csv;charset=utf-8,\uFEFF"; // \uFEFF for BOM in excel pt-BR
    csvContent += headers.join(';') + "\r\n";

    currentState.lastResults.forEach(r => {
        let row = [
            `"${r.nome_empresa || ''}"`,
            `"${r.setor || ''}"`,
            `"${r.telefone || ''}"`,
            `"${r.endereco || ''}"`,
            `"${r.website || ''}"`
        ];
        csvContent += row.join(';') + "\r\n";
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `prospects_gerados_${new Date().getTime()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("Download da sua planilha iniciado!", "success");
}
