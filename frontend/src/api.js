/* API client for SAR backend */

const BASE_URL = '/api/v1';

function getToken() {
    return localStorage.getItem('sar_token');
}

async function request(path, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
    };

    const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

    if (res.status === 401) {
        localStorage.removeItem('sar_token');
        window.location.hash = '#/login';
        throw new Error('Unauthorized');
    }

    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
    }

    return res.json();
}

export const api = {
    // Auth
    login: (data) => request('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
    register: (data) => request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),

    // Cases
    listCases: () => request('/cases'),
    getCase: (id) => request(`/cases/${id}`),
    ingestCase: (data) => request('/cases/ingest', { method: 'POST', body: JSON.stringify(data) }),

    // Narratives
    getNarrative: (caseId) => request(`/cases/${caseId}/narrative`),
    editNarrative: (caseId, content) =>
        request(`/cases/${caseId}/narrative`, { method: 'PUT', body: JSON.stringify({ content }) }),
    approveNarrative: (caseId) =>
        request(`/cases/${caseId}/narrative/approve`, { method: 'POST' }),
    rejectNarrative: (caseId) =>
        request(`/cases/${caseId}/narrative/reject`, { method: 'POST' }),

    // Audit
    getAuditTrail: (caseId) => request(`/cases/${caseId}/audit`),
    reconstruct: (caseId, sentence) =>
        request(`/cases/${caseId}/audit/reconstruct?sentence=${encodeURIComponent(sentence || '')}`),

    // Alerts
    listAlerts: () => request('/alerts'),
};
