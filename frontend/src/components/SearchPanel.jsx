import React, { useEffect, useMemo, useState } from 'react';
import { Search, Download, Check, FileText, Loader2 } from 'lucide-react';
import { searchPapers, downloadPapers, ingestPapers } from '../api';
import './SearchPanel.css'; // We'll create specific styles or use global

export default function SearchPanel() {
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

    const [query, setQuery] = useState('');
    const [source, setSource] = useState('arxiv');

    // Choose which chat session (tenant) to store downloaded + ingested papers into
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

    const [author, setAuthor] = useState('');
    const [startDate, setStartDate] = useState('');
    const [endDate, setEndDate] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [downloading, setDownloading] = useState(false);
    const [ingesting, setIngesting] = useState(false);
    const [selectedIndices, setSelectedIndices] = useState(new Set());
    const [downloadedCount, setDownloadedCount] = useState(0);
    const [downloadedFilenames, setDownloadedFilenames] = useState([]);

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setResults([]);
        setSelectedIndices(new Set());
        setDownloadedCount(0);
        setDownloadedFilenames([]);
        try {
            const data = await searchPapers(query, 20, selectedSessionId || 'default', {
                source,
                author: author.trim() || undefined,
                startDate: startDate || undefined,
                endDate: endDate || undefined,
            });
            setResults(data);
        } catch (err) {
            console.error("Search failed", err);
            alert("Search failed. Check backend.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        // Keep session list in sync if chats are created/deleted in ChatPanel
        const onStorage = (e) => {
            if (!e?.key) return;
            if (e.key !== 'chat_sessions' && e.key !== 'chat_current_session') return;
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

    const clearFilters = () => {
        setAuthor('');
        setStartDate('');
        setEndDate('');
    };

    const toggleSelection = (index) => {
        const newSelection = new Set(selectedIndices);
        if (newSelection.has(index)) {
            newSelection.delete(index);
        } else {
            newSelection.add(index);
        }
        setSelectedIndices(newSelection);
    };

    const handleDownload = async () => {
        const papersToDownload = results.filter((_, i) => selectedIndices.has(i));
        if (papersToDownload.length === 0) return;

        setDownloading(true);
        try {
            const tenantId = selectedSessionId || 'default';
            const res = await downloadPapers(papersToDownload, tenantId, tenantId);
            setDownloadedCount(res.downloaded);
            const downloaded = Array.isArray(res?.papers) ? res.papers : [];
            const filenames = downloaded
                .map(p => (p?.local_path || '').split(/[/\\]+/).pop())
                .filter(Boolean);
            setDownloadedFilenames(filenames);

            // Update local state to show they are downloaded?
            // For now just alert or toast
            // Automatically trigger ingest? Or existing flow? 
            // Paper said "two-step". User can download then ingest.
        } catch (err) {
            console.error("Download failed", err);
        } finally {
            setDownloading(false);
        }
    };

    const handleIngest = async () => {
        setIngesting(true);
        try {
            const tenantId = selectedSessionId || 'default';
            // Ingest only newly downloaded files to avoid duplicate indexing
            const res = await ingestPapers(downloadedFilenames.length ? downloadedFilenames : null, tenantId, tenantId);
            alert(`Ingested ${res.metrics?.total_nodes || 0} chunks!`);
        } catch (err) {
            console.error("Ingest failed", err);
        } finally {
            setIngesting(false);
        }
    };

    return (
        <div className="search-panel">
            {/* Search Bar */}
            <form onSubmit={handleSearch} className="search-bar-container">
                <div className="search-shell glass-panel">
                    <div className="search-shell-top">
                        <div className="search-query-row">
                            <Search className="search-icon" size={18} />
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Search papers..."
                                className="input-base"
                            />
                        </div>
                        <button type="submit" className="search-button" disabled={loading}>
                            {loading ? <Loader2 className="spin" /> : 'Search'}
                        </button>
                    </div>

                    <div className="search-shell-divider" />

                    <div className="search-shell-filters">
                        <div className="filters-header">
                            <span className="filters-title">Filters</span>
                            <button
                                type="button"
                                className="filters-clear"
                                onClick={clearFilters}
                                disabled={!author && !startDate && !endDate}
                                title="Clear filters"
                            >
                                Clear
                            </button>
                        </div>

                        <div className="filters-grid">
                            <div className="field field-source">
                                <label className="field-label">Source</label>
                                <select
                                    value={source}
                                    onChange={(e) => setSource(e.target.value)}
                                    className="input-base"
                                >
                                    <option value="arxiv">ArXiv</option>
                                    <option value="semantic_scholar">Semantic Scholar (open-access PDFs)</option>
                                </select>
                            </div>
                            <div className="field field-session">
                                <label className="field-label">Session</label>
                                <select
                                    value={selectedSessionId}
                                    onChange={(e) => setSelectedSessionId(e.target.value)}
                                    className="input-base"
                                >
                                    {(sessions.length ? sessions : ['default']).map((id) => (
                                        <option key={id} value={id}>
                                            {getSessionLabel(id)}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="field field-author">
                                <label className="field-label">Author</label>
                                <input
                                    type="text"
                                    value={author}
                                    onChange={(e) => setAuthor(e.target.value)}
                                    placeholder="e.g., Geoffrey Hinton"
                                    className="input-base"
                                />
                            </div>
                            <div className="field field-from">
                                <label className="field-label">From</label>
                                <input
                                    type="date"
                                    value={startDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    className="input-base"
                                />
                            </div>
                            <div className="field field-to">
                                <label className="field-label">To</label>
                                <input
                                    type="date"
                                    value={endDate}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    className="input-base"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </form>

            {/* Actions */}
            {results.length > 0 && (
                <div className="actions-bar">
                    <button
                        onClick={handleDownload}
                        disabled={selectedIndices.size === 0 || downloading}
                        className="action-btn primary"
                    >
                        {downloading ? (
                            <><Loader2 size={16} className="spin" /> Downloading...</>
                        ) : (
                            <><Download size={16} /> Download Selected ({selectedIndices.size})</>
                        )}
                    </button>

                    {downloadedCount > 0 && (
                        <button
                            onClick={handleIngest}
                            disabled={ingesting}
                            className="action-btn success"
                        >
                            {ingesting ? <Loader2 size={16} className="spin" /> : <Check size={16} />}
                            Process Papers
                        </button>
                    )}
                </div>
            )}

            {/* Results Grid */}
            <div className="results-grid">
                {results.map((paper, index) => (
                    <div
                        key={index}
                        className={`paper-card glass-panel ${selectedIndices.has(index) ? 'selected' : ''}`}
                        onClick={() => toggleSelection(index)}
                    >
                        <div className="paper-header">
                            <div className="checkbox-wrapper">
                                <div className={`checkbox ${selectedIndices.has(index) ? 'checked' : ''}`}>
                                    {selectedIndices.has(index) && <Check size={12} />}
                                </div>
                            </div>
                            <h3 className="paper-title" title={paper.title}>{paper.title}</h3>
                        </div>
                        <p className="paper-authors">{paper.authors.slice(0, 3).join(', ')}{paper.authors.length > 3 ? '...' : ''}</p>
                        <p className="paper-date">{paper.published}</p>
                        <p className="paper-abstract">{paper.abstract.slice(0, 150)}...</p>
                        <a href={paper.pdf_url} target="_blank" rel="noreferrer" className="pdf-link" onClick={e => e.stopPropagation()}>
                            <FileText size={12} /> PDF
                        </a>
                    </div>
                ))}
            </div>
        </div>
    );
}
