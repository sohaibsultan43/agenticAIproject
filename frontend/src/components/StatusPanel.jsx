import React, { useEffect, useMemo, useState } from 'react';
import { Database, FileText, Activity, Server, AlertCircle, Trash2, Loader2 } from 'lucide-react';
import { getStatus, deletePaper } from '../api';
import './StatusPanel.css';

export default function StatusPanel() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [deleting, setDeleting] = useState(null); // Track which paper is being deleted

    const safeParseArray = (key) => {
        try {
            const raw = localStorage.getItem(key);
            const parsed = raw ? JSON.parse(raw) : [];
            return Array.isArray(parsed) ? parsed : [];
        } catch {
            return [];
        }
    };

    const safeParseObject = (key) => {
        try {
            const raw = localStorage.getItem(key);
            const parsed = raw ? JSON.parse(raw) : {};
            if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed;
            return {};
        } catch {
            return {};
        }
    };

    const getSessionLabel = (id) => {
        const meta = safeParseObject('chat_session_meta');
        const name = meta?.[id]?.name;
        if (name) return name;
        return id === 'default' ? 'Default' : id.replace('session-', 'Chat ');
    };

    const initialSelectedSession = useMemo(() => {
        const current = localStorage.getItem('chat_current_session');
        if (current) return current;
        const sessions = safeParseArray('chat_sessions');
        return sessions[0] || 'default';
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const [sessions, setSessions] = useState(() => {
        const current = localStorage.getItem('chat_current_session');
        const list = safeParseArray('chat_sessions');
        const merged = Array.from(new Set([...(list || []), ...(current ? [current] : [])]));
        return merged.length ? merged : ['default'];
    });
    const [selectedSessionId, setSelectedSessionId] = useState(initialSelectedSession);

    useEffect(() => {
        fetchStatus(selectedSessionId);
        // Poll every 30s
        const interval = setInterval(() => fetchStatus(selectedSessionId), 30000);
        return () => clearInterval(interval);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedSessionId]);

    useEffect(() => {
        const onStorage = (e) => {
            if (!e?.key) return;
            if (e.key !== 'chat_sessions' && e.key !== 'chat_current_session' && e.key !== 'chat_session_meta') return;
            const current = localStorage.getItem('chat_current_session');
            const list = safeParseArray('chat_sessions');
            const merged = Array.from(new Set([...(list || []), ...(current ? [current] : [])]));
            const next = merged.length ? merged : ['default'];
            setSessions(next);
            if (selectedSessionId && next.includes(selectedSessionId)) return;
            setSelectedSessionId(current || next[0] || 'default');
        };

        window.addEventListener('storage', onStorage);
        return () => window.removeEventListener('storage', onStorage);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedSessionId]);

    const fetchStatus = async (tenantId) => {
        try {
            const res = await getStatus(tenantId || 'default');
            setData(res);
            setError(null);
        } catch (err) {
            setError("Failed to fetch system status.");
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleDeletePaper = async (filename) => {
        if (!confirm(`Delete "${filename}" and its chunks from the knowledge base?`)) {
            return;
        }
        
        setDeleting(filename);
        try {
            const result = await deletePaper(filename);
            console.log('Delete result:', result);
            // Refresh status after deletion
            await fetchStatus();
        } catch (err) {
            console.error('Failed to delete paper:', err);
            setError(`Failed to delete ${filename}`);
        } finally {
            setDeleting(null);
        }
    };

    if (loading && !data) return <div className="loading-state">Loading status...</div>;

    return (
        <div className="status-panel">
            {error && (
                <div className="error-banner glass-panel">
                    <AlertCircle size={20} /> {error}
                </div>
            )}

            <div className="status-topbar">
                <div className="status-title">Knowledge Base</div>
                <div className="status-session">
                    <span className="status-session-label">Session</span>
                    <select
                        className="status-session-select"
                        value={selectedSessionId}
                        onChange={(e) => setSelectedSessionId(e.target.value)}
                    >
                        {(sessions.length ? sessions : ['default']).map((id) => (
                            <option key={id} value={id}>
                                {getSessionLabel(id)}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Metrics Grid */}
            <div className="metrics-grid">
                <StatusCard
                    icon={<Server size={24} />}
                    label="Weaviate Status"
                    value={data?.weaviate_connected ? "Connected" : "Disconnected"}
                    status={data?.weaviate_connected ? "success" : "error"}
                />
                <StatusCard
                    icon={<Database size={24} />}
                    label="Indexed Chunks"
                    value={
                        typeof data?.indexed_chunks_all === 'number' && (data?.indexed_chunks_all !== data?.indexed_chunks)
                            ? `${data?.indexed_chunks || 0} (all: ${data?.indexed_chunks_all || 0})`
                            : (data?.indexed_chunks || 0)
                    }
                    status="neutral"
                />
                <StatusCard
                    icon={<FileText size={24} />}
                    label="Downloaded Papers"
                    value={data?.downloaded_papers || 0}
                    status="neutral"
                />
            </div>

            {/* Paper List */}
            <div className="paper-list-section glass-panel">
                <h3 className="section-title">Knowledge Base Library</h3>
                {data?.paper_list && data.paper_list.length > 0 ? (
                    <ul className="paper-list">
                        {data.paper_list.map((paper, i) => (
                            <li key={i} className="paper-item">
                                <div className="paper-info">
                                    <FileText size={16} className="item-icon" />
                                    <span className="paper-name" title={paper}>{paper}</span>
                                </div>
                                <button
                                    className="delete-btn"
                                    onClick={() => handleDeletePaper(paper)}
                                    disabled={deleting === paper}
                                    title="Delete paper and its chunks"
                                >
                                    {deleting === paper ? (
                                        <Loader2 size={16} className="spin" />
                                    ) : (
                                        <Trash2 size={16} />
                                    )}
                                </button>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="empty-state">No papers downloaded yet.</p>
                )}
            </div>
        </div>
    );
}

function StatusCard({ icon, label, value, status }) {
    return (
        <div className={`status-card glass-panel ${status}`}>
            <div className="card-icon">{icon}</div>
            <div className="card-info">
                <span className="card-label">{label}</span>
                <span className="card-value">{value}</span>
            </div>
        </div>
    );
}
