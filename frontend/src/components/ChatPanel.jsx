import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Search as SearchIcon, Download, Check, Loader2, FileText, Trash2 } from 'lucide-react';
import { sendChatMessage, searchPapers, downloadPapers, ingestPapers, clearKB } from '../api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import './ChatPanel.css';

const safeParseObject = (key) => {
    try {
        const raw = localStorage.getItem(key);
        const parsed = raw ? JSON.parse(raw) : {};
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed;
        localStorage.removeItem(key);
        return {};
    } catch {
        return {};
    }
};

const safeParseArray = (key) => {
    try {
        const raw = localStorage.getItem(key);
        const parsed = raw ? JSON.parse(raw) : [];
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
};

const _extractTimestamp = (sessionId) => {
    // session-<timestamp>
    if (typeof sessionId !== 'string') return null;
    const m = sessionId.match(/^session-(\d{10,})$/);
    if (!m) return null;
    const ts = Number(m[1]);
    return Number.isFinite(ts) ? ts : null;
};

const ensureSessionMeta = (sessionIds) => {
    const meta = safeParseObject('chat_session_meta');
    const ids = Array.isArray(sessionIds) ? sessionIds : [];

    // Determine existing max "Chat N"
    let maxN = 0;
    for (const v of Object.values(meta)) {
        const name = v?.name;
        const m = typeof name === 'string' ? name.match(/^Chat\s+(\d+)$/i) : null;
        if (m) maxN = Math.max(maxN, Number(m[1]) || 0);
    }

    // Stable order: by timestamp if present, otherwise as given
    const ordered = [...ids].sort((a, b) => {
        const ta = _extractTimestamp(a) ?? Number.MAX_SAFE_INTEGER;
        const tb = _extractTimestamp(b) ?? Number.MAX_SAFE_INTEGER;
        if (ta !== tb) return ta - tb;
        return String(a).localeCompare(String(b));
    });

    let changed = false;
    for (const id of ordered) {
        if (!id) continue;
        if (meta[id]?.name) continue;
        maxN += 1;
        meta[id] = {
            name: `Chat ${maxN}`,
            createdAt: _extractTimestamp(id) || Date.now(),
        };
        changed = true;
    }

    if (changed) {
        localStorage.setItem('chat_session_meta', JSON.stringify(meta));
    }
    return meta;
};

const getSessionLabel = (id) => {
    const meta = safeParseObject('chat_session_meta');
    const name = meta?.[id]?.name;
    if (name) return name;
    // Fallback (older ids)
    return typeof id === 'string' ? id.replace('session-', 'Chat ') : String(id);
};

const _basename = (p) => {
    if (!p || typeof p !== 'string') return null;
    const parts = p.split(/[/\\]+/);
    return parts[parts.length - 1] || null;
};

export default function ChatPanel() {
    const initialSessions = (() => {
        const existing = safeParseArray('chat_sessions');
        if (existing.length) return existing;
        const first = `session-${Date.now()}`;
        localStorage.setItem('chat_sessions', JSON.stringify([first]));
        localStorage.setItem('chat_current_session', first);
        return [first];
    })();

    const initialCurrent = (() => {
        const saved = localStorage.getItem('chat_current_session');
        return saved || initialSessions[0];
    })();

    // Ensure friendly names exist for sessions (and migrate older sessions)
    ensureSessionMeta([initialCurrent, ...initialSessions]);

    const [sessions, setSessions] = useState(initialSessions);
    const [currentSessionId, setCurrentSessionId] = useState(initialCurrent);
    const [messages, setMessages] = useState(() => {
        const all = safeParseObject('chat_messages');
        return all[initialCurrent] || [];
    });
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [chatSearchQuery, setChatSearchQuery] = useState(() => {
        const all = safeParseObject('chat_paper_results');
        return all?.[initialCurrent]?.query || '';
    });
    // Always isolate downloads/ingestion per session
    const [chatFolder, setChatFolder] = useState(initialCurrent);
    const [chatResults, setChatResults] = useState(() => {
        const all = safeParseObject('chat_paper_results');
        const saved = all?.[initialCurrent]?.results;
        return Array.isArray(saved) ? saved : [];
    });
    const [chatSelected, setChatSelected] = useState(new Set());
    const [chatDownloading, setChatDownloading] = useState(false);
    const [papersOpen, setPapersOpen] = useState(true);
    const [papersNotice, setPapersNotice] = useState('');
    const [papersError, setPapersError] = useState('');
    const [chatProcessed, setChatProcessed] = useState(() => {
        const all = safeParseObject('chat_processed');
        return all[initialCurrent] || false;
    });
    const messagesEndRef = useRef(null);

    const showEmptyState = messages.length === 0 && !input.trim();

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    useEffect(() => {
        let all = safeParseObject('chat_messages');
        if (!all || typeof all !== 'object' || Array.isArray(all)) all = {};
        all[currentSessionId] = messages;
        localStorage.setItem('chat_messages', JSON.stringify(all));

        let allProcessed = safeParseObject('chat_processed');
        if (!allProcessed || typeof allProcessed !== 'object' || Array.isArray(allProcessed)) allProcessed = {};
        allProcessed[currentSessionId] = chatProcessed;
        localStorage.setItem('chat_processed', JSON.stringify(allProcessed));

        const nextSessions = Array.from(new Set([currentSessionId, ...sessions]));
        if (nextSessions.length !== sessions.length) setSessions(nextSessions);
        localStorage.setItem('chat_sessions', JSON.stringify(nextSessions));
        localStorage.setItem('chat_current_session', currentSessionId);
        ensureSessionMeta(nextSessions);
    }, [messages, chatProcessed, currentSessionId]);

    // Keep folder aligned with active session for strict isolation
    useEffect(() => {
        setChatFolder(currentSessionId);
    }, [currentSessionId]);

    // Persist paper discovery list per session (so user can come back and download more later)
    useEffect(() => {
        const all = safeParseObject('chat_paper_results');
        all[currentSessionId] = {
            query: chatSearchQuery || '',
            results: Array.isArray(chatResults) ? chatResults : [],
            updatedAt: Date.now(),
        };
        localStorage.setItem('chat_paper_results', JSON.stringify(all));
    }, [chatResults, chatSearchQuery, currentSessionId]);

    // Restore paper list when switching sessions
    useEffect(() => {
        const all = safeParseObject('chat_paper_results');
        const saved = all?.[currentSessionId];
        setChatResults(Array.isArray(saved?.results) ? saved.results : []);
        setChatSearchQuery(saved?.query || '');
        setChatSelected(new Set());
        setPapersNotice('');
        setPapersError('');
        setPapersOpen(false);
    }, [currentSessionId]);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = input.trim();
        setInput('');
        setLoading(true);

        const newHistory = [...messages, { role: 'user', parts: [userMsg] }];
        setMessages(newHistory);

        try {
            const apiHistory = messages.map(m => ({ role: m.role, parts: m.parts }));
            const phaseToUse = chatProcessed ? 'analyst' : 'consultant';
            const tenantId = currentSessionId;
            const data = await sendChatMessage(userMsg, phaseToUse, apiHistory, tenantId);
            const updated = [...newHistory, {
                role: 'model',
                parts: [data.response],
                searchQuery: data.search_query,
                agent: data.agent || null  // Add agent field for badge
            }];
            setMessages(updated);
        } catch (err) {
            console.error("Chat failed", err);
            setMessages([...newHistory, { role: 'model', parts: ["Sorry, I encountered an error. Please try again."] }]);
        } finally {
            setLoading(false);
        }
    };

    const toggleChatSelection = (index) => {
        const next = new Set(chatSelected);
        next.has(index) ? next.delete(index) : next.add(index);
        setChatSelected(next);
    };

    const handleChatDownloadAndProcess = async () => {
        const papers = chatResults.filter((_, i) => chatSelected.has(i));
        if (papers.length === 0) return;
        setChatDownloading(true);
        setPapersError('');
        setPapersNotice('Downloading...');
        try {
            const tenantId = currentSessionId;
            const res = await downloadPapers(papers, currentSessionId, tenantId);
            const downloaded = Array.isArray(res?.papers) ? res.papers : [];

            // Update local list with local_path for downloaded items
            if (downloaded.length) {
                const byUrl = new Map(downloaded.map(p => [p.pdf_url, p]));
                setChatResults(prev =>
                    prev.map(p => {
                        const d = byUrl.get(p.pdf_url);
                        return d ? { ...p, local_path: d.local_path } : p;
                    })
                );
            }

            const filenames = downloaded
                .map(p => _basename(p.local_path))
                .filter(Boolean);

            setPapersNotice(`Downloaded ${res.downloaded}. Processing...`);
            // Ingest only newly downloaded files to avoid duplicate indexing
            const ingestRes = await ingestPapers(filenames.length ? filenames : null, currentSessionId, tenantId);
            const total = ingestRes.metrics?.total_nodes || 0;
            setPapersNotice(`Processed and indexed. Chunks: ${total}`);
            setChatProcessed(true);
        } catch (err) {
            setPapersError('Download or processing failed. Please try again.');
        } finally {
            setChatDownloading(false);
        }
    };

    const handleSearch = async (query) => {
        const runId = currentSessionId;
        setChatFolder(runId);
        setChatSearchQuery(query);
        setChatSelected(new Set());
        setChatResults([]);
        // Keep chat readable: start collapsed, user can expand when ready
        setPapersOpen(false);
        setPapersNotice('Searching...');
        setPapersError('');
        setLoading(true);
        try {
            setPapersNotice('');
            setPapersError('');
            const results = await searchPapers(query, 20, runId);
            console.log('Search results received:', results);
            console.log('First paper source:', results[0]?.source);
            setChatResults(results);
            setPapersNotice(`Found ${results.length} papers. Select to download.`);
        } catch (err) {
            setPapersError('Search failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-layout">
            {/* Main Chat Area */}
            <div className="chat-main">
                {/* Messages */}
                <div className="messages-area custom-scrollbar">
                    <div className={`empty-chat ${showEmptyState ? 'show' : 'hide'}`}>
                        <img
                            className="empty-chat-logo"
                            src="/logo_light.png"
                            alt="ScholarSync"
                            onError={(e) => {
                                if (!e?.target?.src) return;
                                e.target.src = '/logo_dark.png';
                            }}
                        />
                        <p>Start a conversation</p>
                    </div>
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`message-wrapper ${msg.role}`}>
                            {msg.role === 'model' && (
                                <div className="message-header">
                                    <div className="avatar">
                                        <img
                                            className="assistant-icon"
                                            src="/favicon.png"
                                            alt=""
                                        />
                                    </div>
                                    <span className="role-name">
                                        {msg.agent ? msg.agent : 'Assistant'}
                                    </span>
                                    {msg.agent && (
                                        <span className="agent-badge">Agent</span>
                                    )}
                                </div>
                            )}
                            <div className="message-content">
                                <div className="message-text">
                                    {msg.role === 'model' ? (
                                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                                            {msg.parts[0]}
                                        </ReactMarkdown>
                                    ) : (
                                        msg.parts[0].split('\n').map((line, i) => (
                                            <p key={i}>{line || '\u00A0'}</p>
                                        ))
                                    )}
                                </div>
                            </div>
                            {msg.searchQuery && (
                                <div className="message-action">
                                    <button
                                        className="inline-action-btn"
                                        onClick={() => handleSearch(msg.searchQuery)}
                                    >
                                        <SearchIcon size={14} /> Search with this query
                                    </button>
                                </div>
                            )}
                        </div>
                    ))}
                    {loading && (
                        <div className="message-wrapper model">
                            <div className="message-header">
                                <div className="avatar">
                                    <img
                                        className="assistant-icon"
                                        src="/favicon.png"
                                        alt=""
                                    />
                                </div>
                                <span className="role-name">Assistant</span>
                            </div>
                            <div className="message-content">
                                <div className="typing-indicator">
                                    <span></span><span></span><span></span>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Search Results */}
                {chatResults.length > 0 && (
                    <div className={`search-results-panel ${papersOpen ? 'open' : 'collapsed'}`}>
                        <div className="search-results-inner">
                            <div className="search-results-header">
                                <div>
                                    <strong>{chatResults.length} papers found</strong>
                                    <span style={{ color: 'var(--text-secondary)', marginLeft: '0.5rem', fontSize: '0.85rem' }}>
                                        Select to download
                                    </span>
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                    <button
                                        type="button"
                                        className="inline-action-btn"
                                        onClick={() => setPapersOpen(v => !v)}
                                        style={{ background: 'rgba(0,0,0,0.05)', color: 'var(--text-primary)' }}
                                    >
                                        {papersOpen ? 'Hide' : 'Show'}
                                    </button>
                                    <button
                                        className="inline-action-btn"
                                        onClick={handleChatDownloadAndProcess}
                                        disabled={chatSelected.size === 0 || chatDownloading}
                                    >
                                        {chatDownloading ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
                                        {chatDownloading ? 'Processing...' : chatProcessed ? 'Done' : `Download (${chatSelected.size})`}
                                    </button>
                                </div>
                            </div>
                            {(papersNotice || papersError) && (
                                <div className={`papers-status ${papersError ? 'error' : ''}`}>
                                    {papersError || papersNotice}
                                </div>
                            )}
                            <div className="chat-results-list">
                                {chatResults.map((paper, index) => (
                                    <div
                                        key={index}
                                        className={`chat-result-row ${chatSelected.has(index) ? 'selected' : ''}`}
                                        onClick={() => toggleChatSelection(index)}
                                    >
                                        <div className="chat-result-checkbox">
                                            <div className={`checkbox ${chatSelected.has(index) ? 'checked' : ''}`}>
                                                {chatSelected.has(index) && <Check size={10} />}
                                            </div>
                                        </div>
                                        <div className="chat-result-main">
                                            <div className="chat-result-title" title={paper.title}>{paper.title}</div>
                                            <div className="chat-result-meta">
                                                {paper.authors.slice(0, 2).join(', ')}{paper.authors.length > 2 ? '…' : ''} • {paper.published}
                                                {paper.source && (
                                                    <span className="source-badge" data-source={paper.source}>
                                                        {paper.source === 'semantic_scholar' ? 'Semantic Scholar' :
                                                            paper.source === 'arxiv' ? 'ArXiv' :
                                                                paper.source === 'core' ? 'CORE' :
                                                                    paper.source === 'pubmed' ? 'PubMed' :
                                                                        paper.source}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                        <a
                                            href={paper.pdf_url}
                                            target="_blank"
                                            rel="noreferrer"
                                            className="chat-result-link"
                                            onClick={e => e.stopPropagation()}
                                        >
                                            <FileText size={12} /> PDF
                                        </a>
                                    </div>
                                ))}
                            </div>
                            {chatProcessed && (
                                <div style={{ marginTop: '0.5rem', textAlign: 'right' }}>
                                    <button
                                        className="inline-action-btn"
                                        style={{ background: '#ef4444' }}
                                        onClick={async () => {
                                            try {
                                                setLoading(true);
                                                await clearKB(currentSessionId, currentSessionId);
                                                setPapersError('');
                                                setPapersNotice('Knowledge base cleared.');
                                                setChatProcessed(false);
                                            } catch (err) {
                                                setPapersError('Failed to clear KB.');
                                            } finally {
                                                setLoading(false);
                                            }
                                        }}
                                    >
                                        Clear KB
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Input */}
                <div className="input-container">
                    <form onSubmit={handleSend} className="input-area">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Message..."
                            className="chat-input"
                            disabled={loading}
                        />
                        <button type="submit" disabled={loading || !input.trim()} className="send-btn">
                            <Send size={18} />
                        </button>
                    </form>
                </div>
            </div>

            {/* Sessions Panel */}
            <div className="sessions-panel glass-panel">
                <div className="sessions-header">
                    <span>Sessions</span>
                    <button
                        className="inline-action-btn"
                        onClick={() => {
                            const newId = `session-${Date.now()}`;
                            // Pre-create friendly label for the new chat
                            ensureSessionMeta([newId]);
                            setCurrentSessionId(newId);
                            setMessages([]);
                            setChatProcessed(false);
                            setChatResults([]);
                            setChatSelected(new Set());
                            setChatFolder(newId);
                            setChatSearchQuery('');
                        }}
                    >
                        New Chat
                    </button>
                </div>
                <div className="sessions-list custom-scrollbar">
                    {Array.from(new Set([...sessions, currentSessionId])).map(id => (
                        <div key={id} className={`session-item-row ${id === currentSessionId ? 'active' : ''}`}>
                            <button
                                className="session-item-btn"
                                onClick={() => {
                                    setCurrentSessionId(id);
                                    const savedMsgs = safeParseObject('chat_messages');
                                    setMessages(savedMsgs[id] || []);
                                    const savedProcessed = safeParseObject('chat_processed');
                                    setChatProcessed(savedProcessed[id] || false);
                                    const savedPapers = safeParseObject('chat_paper_results');
                                    const saved = savedPapers?.[id];
                                    setChatResults(Array.isArray(saved?.results) ? saved.results : []);
                                    setChatSearchQuery(saved?.query || '');
                                    setChatSelected(new Set());
                                    setChatFolder(id);
                                }}
                            >
                                {getSessionLabel(id)}
                            </button>
                            <button
                                className="session-delete-btn"
                                onClick={async (e) => {
                                    e.stopPropagation();
                                    if (!confirm('Delete this session and its history?')) return;

                                    // Remove from localStorage
                                    const allMsgs = safeParseObject('chat_messages');
                                    delete allMsgs[id];
                                    localStorage.setItem('chat_messages', JSON.stringify(allMsgs));

                                    const allProcessed = safeParseObject('chat_processed');
                                    delete allProcessed[id];
                                    localStorage.setItem('chat_processed', JSON.stringify(allProcessed));

                                    const allMeta = safeParseObject('chat_session_meta');
                                    delete allMeta[id];
                                    localStorage.setItem('chat_session_meta', JSON.stringify(allMeta));

                                    const allPapers = safeParseObject('chat_paper_results');
                                    delete allPapers[id];
                                    localStorage.setItem('chat_paper_results', JSON.stringify(allPapers));

                                    // Remove from sessions list
                                    const newSessions = sessions.filter(s => s !== id);
                                    setSessions(newSessions);
                                    localStorage.setItem('chat_sessions', JSON.stringify(newSessions));

                                    // Clear KB + delete this session's download folder
                                    try {
                                        await clearKB(id, id);
                                    } catch (err) {
                                        console.error(err);
                                    }

                                    // If deleting current session, switch to another or create new
                                    if (id === currentSessionId) {
                                        if (newSessions.length > 0) {
                                            const nextId = newSessions[0];
                                            setCurrentSessionId(nextId);
                                            const savedMsgs = safeParseObject('chat_messages');
                                            setMessages(savedMsgs[nextId] || []);
                                            const savedProcessed = safeParseObject('chat_processed');
                                            setChatProcessed(savedProcessed[nextId] || false);
                                        } else {
                                            const newId = `session-${Date.now()}`;
                                            setCurrentSessionId(newId);
                                            setMessages([]);
                                            setChatProcessed(false);
                                        }
                                        setChatResults([]);
                                        setChatSelected(new Set());
                                        setChatFolder(newSessions.length > 0 ? newSessions[0] : currentSessionId);
                                    }
                                }}
                                title="Delete session"
                            >
                                <Trash2 size={14} />
                            </button>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
