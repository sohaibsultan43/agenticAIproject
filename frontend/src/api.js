import axios from 'axios';

// Prefer explicit backend URL from environment, fall back to local dev FastAPI.
const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '') ||
    'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const searchPapers = async (query, maxResults = 20, tenantId = 'default', filters = {}) => {
    const payload = {
        query,
        max_results: maxResults,
        tenant_id: tenantId,
    };

    if (filters?.source) payload.source = filters.source;
    if (filters?.author) payload.author = filters.author;
    if (filters?.startDate) payload.start_date = filters.startDate;
    if (filters?.endDate) payload.end_date = filters.endDate;

    const response = await api.post('/search', payload);
    return response.data;
};

export const downloadPapers = async (papers, folder = null, tenantId = 'default') => {
    const response = await api.post('/download', { papers, folder, tenant_id: tenantId });
    return response.data;
};

export const ingestPapers = async (filenames = null, folder = null, tenantId = 'default') => {
    const response = await api.post('/ingest', { filenames, folder, tenant_id: tenantId });
    return response.data;
};

export const sendChatMessage = async (message, phase, history = [], tenantId = 'default') => {
    const response = await api.post('/chat', { message, phase, history, tenant_id: tenantId });
    return response.data;
};

export const getStatus = async (tenantId = null) => {
    const response = await api.get('/status', {
        params: tenantId ? { tenant_id: tenantId } : undefined,
    });
    return response.data;
};

export const clearKB = async (tenantId = 'default', folder = null) => {
    const response = await api.post('/clear_kb', { tenant_id: tenantId, folder });
    return response.data;
};

export const deletePaper = async (filename) => {
    const response = await api.post('/delete_paper', { filename });
    return response.data;
};

export default api;
