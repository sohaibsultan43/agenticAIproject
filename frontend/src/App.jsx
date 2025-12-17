import { useState } from 'react'
import { Search, Bot, Database } from 'lucide-react'
import SearchPanel from './components/SearchPanel'
import ChatPanel from './components/ChatPanel'
import StatusPanel from './components/StatusPanel'
import './index.css'

function App() {
    const [activeTab, setActiveTab] = useState('chat')

    return (
        <div className="app-container" style={{
            display: 'grid',
            gridTemplateColumns: '80px 1fr',
            height: '100vh',
            overflow: 'hidden',
            background: 'var(--bg-primary)'
        }}>
            {/* Sidebar */}
            <aside className="sidebar glass-panel" style={{
                margin: '1rem',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'flex-start',
                padding: '0.9rem 0',
                gap: '1rem',
                zIndex: 10,
                width: '60px',
                minWidth: '60px'
            }}>
                <div className="sidebar-brand">
                    <img
                        className="sidebar-icon"
                        src="/favicon.png"
                        alt="ScholarSync"
                        onError={(e) => {
                            if (!e?.target?.src) return;
                            e.target.src = '/logo_light.png';
                        }}
                    />
                </div>

                <NavButton
                    icon={<Bot size={20} />}
                    label="Chat"
                    active={activeTab === 'chat'}
                    onClick={() => setActiveTab('chat')}
                />
                <NavButton
                    icon={<Search size={20} />}
                    label="Search"
                    active={activeTab === 'search'}
                    onClick={() => setActiveTab('search')}
                />
                <NavButton
                    icon={<Database size={20} />}
                    label="Data"
                    active={activeTab === 'data'}
                    onClick={() => setActiveTab('data')}
                />
            </aside>

            {/* Main Content */}
            <main style={{
                margin: '1rem 1rem 1rem 0',
                display: 'flex',
                flexDirection: 'column',
                minHeight: 0,
                overflow: 'hidden'
            }}>
                <div className="glass-panel" style={{
                    flex: 1,
                    padding: '1.5rem',
                    display: 'flex',
                    flexDirection: 'column',
                    minHeight: 0,
                    overflow: 'hidden'
                }}>
                    {activeTab !== 'chat' && (
                        <h1 className="gradient-text" style={{ fontSize: '1.75rem', marginBottom: '1rem', flexShrink: 0 }}>
                            {activeTab === 'search' && 'Discover Papers'}
                            {activeTab === 'data' && 'Knowledge Base Status'}
                        </h1>
                    )}

                    {/* Content area - different handling for chat vs others */}
                    {activeTab === 'chat' ? (
                        <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
                            <ChatPanel />
                        </div>
                    ) : (
                        <div className="content-area custom-scrollbar" style={{ flex: 1, overflowY: 'auto' }}>
                            {activeTab === 'search' && <SearchPanel />}
                            {activeTab === 'data' && <StatusPanel />}
                        </div>
                    )}
                </div>
            </main>
        </div>
    )
}

function NavButton({ icon, label, active, onClick }) {
    return (
        <button
            onClick={onClick}
            style={{
                padding: '10px',
                borderRadius: '10px',
                color: active ? 'var(--accent-primary)' : 'var(--text-secondary)',
                background: active ? 'var(--accent-glow)' : 'transparent',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
            }}
            title={label}
        >
            {icon}
        </button>
    )
}

export default App
