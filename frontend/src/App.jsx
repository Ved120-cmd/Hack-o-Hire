import { useState, useEffect } from 'react';
import { HashRouter as Router, Routes, Route, Navigate, Link, useNavigate, useParams, useLocation } from 'react-router-dom';
import { api } from './api';

/* ============================================================
   AUTH CONTEXT
   ============================================================ */
function useAuth() {
    const [user, setUser] = useState(() => {
        const token = localStorage.getItem('sar_token');
        const username = localStorage.getItem('sar_username');
        const role = localStorage.getItem('sar_role');
        return token ? { token, username, role } : null;
    });

    const login = async (username, password) => {
        const data = await api.login({ username, password });
        localStorage.setItem('sar_token', data.access_token);
        localStorage.setItem('sar_username', data.username);
        localStorage.setItem('sar_role', data.role);
        setUser({ token: data.access_token, username: data.username, role: data.role });
    };

    const register = async (username, email, password) => {
        const data = await api.register({ username, email, password, role: 'analyst' });
        localStorage.setItem('sar_token', data.access_token);
        localStorage.setItem('sar_username', data.username);
        localStorage.setItem('sar_role', data.role);
        setUser({ token: data.access_token, username: data.username, role: data.role });
    };

    const logout = () => {
        localStorage.removeItem('sar_token');
        localStorage.removeItem('sar_username');
        localStorage.removeItem('sar_role');
        setUser(null);
    };

    return { user, login, register, logout };
}

/* ============================================================
   SIDEBAR
   ============================================================ */
function Sidebar({ user, logout }) {
    const location = useLocation();
    const path = location.pathname;

    const navItems = [
        { to: '/', icon: '📊', label: 'Dashboard' },
        { to: '/ingest', icon: '📥', label: 'New Case' },
        { to: '/alerts', icon: '🔔', label: 'Alerts' },
    ];

    return (
        <aside className="sidebar">
            <div className="sidebar-logo">
                <div className="sidebar-logo-icon">S</div>
                <h1>SAR Generator</h1>
            </div>
            <nav className="sidebar-nav">
                {navItems.map(item => (
                    <Link
                        key={item.to}
                        to={item.to}
                        className={`nav-link ${path === item.to ? 'active' : ''}`}
                    >
                        <span className="nav-icon">{item.icon}</span>
                        {item.label}
                    </Link>
                ))}
            </nav>
            <div className="sidebar-footer">
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                    Signed in as <strong style={{ color: 'var(--text-primary)' }}>{user?.username}</strong>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={logout} style={{ width: '100%', justifyContent: 'center' }}>
                    Sign Out
                </button>
            </div>
        </aside>
    );
}

/* ============================================================
   LOGIN PAGE
   ============================================================ */
function LoginPage({ onLogin, onRegister }) {
    const [isRegister, setIsRegister] = useState(false);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [email, setEmail] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            if (isRegister) {
                await onRegister(username, email, password);
            } else {
                await onLogin(username, password);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-card">
                <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                    <div className="sidebar-logo-icon" style={{ width: 48, height: 48, fontSize: '1.3rem', margin: '0 auto 1rem' }}>S</div>
                    <h2>SAR Narrative Generator</h2>
                    <p className="login-subtitle">AI-Powered Compliance Intelligence</p>
                </div>

                {error && <div className="login-error">{error}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label className="form-label">Username</label>
                        <input
                            id="login-username"
                            className="form-input"
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                        />
                    </div>
                    {isRegister && (
                        <div className="form-group">
                            <label className="form-label">Email</label>
                            <input
                                id="register-email"
                                className="form-input"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                            />
                        </div>
                    )}
                    <div className="form-group">
                        <label className="form-label">Password</label>
                        <input
                            id="login-password"
                            className="form-input"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button id="login-submit" className="btn btn-primary" type="submit" disabled={loading}>
                        {loading ? 'Please wait…' : isRegister ? 'Create Account' : 'Sign In'}
                    </button>
                </form>

                <p style={{ textAlign: 'center', marginTop: '1.25rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
                    <button
                        onClick={() => { setIsRegister(!isRegister); setError(''); }}
                        style={{ background: 'none', border: 'none', color: 'var(--accent-blue)', cursor: 'pointer', fontFamily: 'inherit', fontSize: 'inherit' }}
                    >
                        {isRegister ? 'Sign In' : 'Create one'}
                    </button>
                </p>
            </div>
        </div>
    );
}

/* ============================================================
   DASHBOARD
   ============================================================ */
function Dashboard() {
    const [cases, setCases] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        api.listCases().then(setCases).catch(() => { }).finally(() => setLoading(false));
    }, []);

    const stats = {
        total: cases.length,
        high: cases.filter(c => c.risk_category === 'High').length,
        pending: cases.filter(c => c.status === 'pending_review').length,
        approved: cases.filter(c => c.status === 'approved').length,
    };

    if (loading) return <div className="loading-center"><div className="spinner" /><span>Loading cases…</span></div>;

    return (
        <div>
            <div className="page-header">
                <h2>Dashboard</h2>
                <p>Overview of SAR cases and pipeline status</p>
            </div>

            <div className="stats-row">
                <div className="stat-card blue">
                    <div className="stat-label">Total Cases</div>
                    <div className="stat-value">{stats.total}</div>
                </div>
                <div className="stat-card rose">
                    <div className="stat-label">High Risk</div>
                    <div className="stat-value">{stats.high}</div>
                </div>
                <div className="stat-card amber">
                    <div className="stat-label">Pending Review</div>
                    <div className="stat-value">{stats.pending}</div>
                </div>
                <div className="stat-card emerald">
                    <div className="stat-label">Approved</div>
                    <div className="stat-value">{stats.approved}</div>
                </div>
            </div>

            {cases.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                    <p style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>No cases yet</p>
                    <Link to="/ingest" className="btn btn-primary">Ingest First Case</Link>
                </div>
            ) : (
                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Case ID</th>
                                <th>Status</th>
                                <th>Risk</th>
                                <th>Score</th>
                                <th>ML Confidence</th>
                                <th>Created</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {cases.map(c => (
                                <tr key={c.case_id}>
                                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.case_id}</td>
                                    <td><span className={`badge badge-${c.status === 'pending_review' ? 'pending' : c.status}`}>{c.status}</span></td>
                                    <td><span className={`badge badge-${(c.risk_category || 'low').toLowerCase()}`}>{c.risk_category || 'N/A'}</span></td>
                                    <td>{(c.risk_score || 0).toFixed(2)}</td>
                                    <td>{((c.ml_confidence || 0) * 100).toFixed(0)}%</td>
                                    <td>{c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}</td>
                                    <td>
                                        <button className="btn btn-ghost btn-sm" onClick={() => navigate(`/cases/${c.case_id}`)}>
                                            View →
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

/* ============================================================
   INGEST PAGE
   ============================================================ */
function IngestPage() {
    const [json, setJson] = useState('');
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(''); setResult(null); setLoading(true);
        try {
            const data = JSON.parse(json);
            const res = await api.ingestCase(data);
            setResult(res);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const loadSample = async () => {
        try {
            const res = await fetch('/sample_input.json');
            const data = await res.json();
            setJson(JSON.stringify(data, null, 2));
        } catch {
            setError('Could not load sample data');
        }
    };

    return (
        <div>
            <div className="page-header">
                <h2>Ingest New Case</h2>
                <p>Submit case data to run the full SAR pipeline</p>
            </div>

            {result ? (
                <div className="card">
                    <div className="card-header">
                        <h3>✅ Pipeline Complete</h3>
                        <span className={`badge badge-${result.risk_category?.toLowerCase()}`}>{result.risk_category}</span>
                    </div>

                    <div className="stats-row" style={{ marginBottom: '1rem' }}>
                        <div className="stat-card blue">
                            <div className="stat-label">Case ID</div>
                            <div className="stat-value" style={{ fontSize: '1rem' }}>{result.case_id}</div>
                        </div>
                        <div className="stat-card rose">
                            <div className="stat-label">Risk Score</div>
                            <div className="stat-value">{(result.risk_score || 0).toFixed(2)}</div>
                        </div>
                        <div className="stat-card amber">
                            <div className="stat-label">Rules Triggered</div>
                            <div className="stat-value">{result.triggered_rules?.length || 0}</div>
                        </div>
                        <div className="stat-card emerald">
                            <div className="stat-label">ML Confidence</div>
                            <div className="stat-value">{((result.ml_confidence || 0) * 100).toFixed(0)}%</div>
                        </div>
                    </div>

                    {result.typologies?.length > 0 && (
                        <div style={{ marginBottom: '1rem' }}>
                            <strong style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Typologies: </strong>
                            {result.typologies.map(t => (
                                <span key={t} className="badge badge-high" style={{ marginRight: '0.4rem' }}>{t}</span>
                            ))}
                        </div>
                    )}

                    {result.narrative_preview && (
                        <div style={{ marginBottom: '1rem' }}>
                            <strong style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Narrative Preview:</strong>
                            <div className="json-viewer" style={{ marginTop: '0.5rem', maxHeight: '200px' }}>
                                {result.narrative_preview}
                            </div>
                        </div>
                    )}

                    <div className="actions-row">
                        <button className="btn btn-primary" onClick={() => navigate(`/cases/${result.case_id}`)}>
                            View Full Case →
                        </button>
                        <button className="btn btn-ghost" onClick={() => { setResult(null); setJson(''); }}>
                            Ingest Another
                        </button>
                    </div>
                </div>
            ) : (
                <form onSubmit={handleSubmit}>
                    <div className="card">
                        {error && <div className="login-error">{error}</div>}
                        <div className="card-header">
                            <h3>Case Data (JSON)</h3>
                            <button type="button" className="btn btn-ghost btn-sm" onClick={loadSample}>
                                Load Sample Data
                            </button>
                        </div>
                        <textarea
                            id="ingest-json"
                            className="form-textarea"
                            value={json}
                            onChange={(e) => setJson(e.target.value)}
                            placeholder='Paste case JSON here...'
                            style={{ minHeight: '400px', fontFamily: 'monospace', fontSize: '0.82rem' }}
                        />
                        <div style={{ marginTop: '1rem' }}>
                            <button id="ingest-submit" className="btn btn-primary" type="submit" disabled={loading || !json.trim()}>
                                {loading ? '⏳ Processing Pipeline…' : '🚀 Run Pipeline'}
                            </button>
                        </div>
                    </div>
                </form>
            )}
        </div>
    );
}

/* ============================================================
   CASE DETAIL PAGE
   ============================================================ */
function CaseDetailPage() {
    const { caseId } = useParams();
    const [caseData, setCaseData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [tab, setTab] = useState('overview');

    useEffect(() => {
        setLoading(true);
        api.getCase(caseId).then(setCaseData).catch(() => { }).finally(() => setLoading(false));
    }, [caseId]);

    if (loading) return <div className="loading-center"><div className="spinner" /><span>Loading case…</span></div>;
    if (!caseData) return <div className="card"><p>Case not found</p></div>;

    const tabs = [
        { key: 'overview', label: '📋 Overview' },
        { key: 'rules', label: '⚖️ Rules' },
        { key: 'narrative', label: '📝 Narrative' },
        { key: 'audit', label: '🔍 Audit Trail' },
    ];

    return (
        <div>
            <div className="page-header">
                <h2>{caseData.case_id}</h2>
                <p>
                    <span className={`badge badge-${caseData.status === 'pending_review' ? 'pending' : caseData.status}`}>{caseData.status}</span>
                    {' '}
                    <span className={`badge badge-${(caseData.risk_category || 'low').toLowerCase()}`}>{caseData.risk_category || 'N/A'}</span>
                </p>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
                {tabs.map(t => (
                    <button
                        key={t.key}
                        className={`btn ${tab === t.key ? 'btn-primary' : 'btn-ghost'} btn-sm`}
                        onClick={() => setTab(t.key)}
                    >
                        {t.label}
                    </button>
                ))}
            </div>

            {tab === 'overview' && <CaseOverview data={caseData} />}
            {tab === 'rules' && <RulesTab rules={caseData.rule_evaluations || []} />}
            {tab === 'narrative' && <NarrativeTab caseId={caseId} narrative={caseData.narrative} />}
            {tab === 'audit' && <AuditTab caseId={caseId} />}
        </div>
    );
}

function CaseOverview({ data }) {
    const riskClass = (data.risk_category || 'low').toLowerCase();
    return (
        <div>
            <div className="stats-row">
                <div className="stat-card rose">
                    <div className="stat-label">Risk Score</div>
                    <div className="stat-value">{(data.risk_score || 0).toFixed(2)}</div>
                    <div className="risk-meter">
                        <div className={`risk-meter-fill ${riskClass}`} style={{ width: `${(data.risk_score || 0) * 100}%` }} />
                    </div>
                </div>
                <div className="stat-card amber">
                    <div className="stat-label">ML Confidence</div>
                    <div className="stat-value">{((data.ml_confidence || 0) * 100).toFixed(0)}%</div>
                </div>
                <div className="stat-card blue">
                    <div className="stat-label">Created By</div>
                    <div className="stat-value" style={{ fontSize: '1rem' }}>{data.created_by || '—'}</div>
                </div>
                <div className="stat-card emerald">
                    <div className="stat-label">Created</div>
                    <div className="stat-value" style={{ fontSize: '0.9rem' }}>
                        {data.created_at ? new Date(data.created_at).toLocaleString() : '—'}
                    </div>
                </div>
            </div>

            {data.alerts?.length > 0 && (
                <div className="card" style={{ marginBottom: '1rem' }}>
                    <h3 style={{ marginBottom: '0.75rem', color: 'var(--status-high)' }}>🔔 Alerts</h3>
                    {data.alerts.map((a, i) => (
                        <div key={i} style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--border-subtle)' }}>
                            <strong>{a.alert_type}</strong> – {a.message}
                        </div>
                    ))}
                </div>
            )}

            <div className="card">
                <h3 style={{ marginBottom: '0.75rem' }}>Raw Input Data</h3>
                <div className="json-viewer">{JSON.stringify(data.raw_input, null, 2)}</div>
            </div>
        </div>
    );
}

function RulesTab({ rules }) {
    const triggered = rules.filter(r => r.triggered);
    const notTriggered = rules.filter(r => !r.triggered);

    return (
        <div>
            <div className="card" style={{ marginBottom: '1rem' }}>
                <h3 style={{ marginBottom: '1rem' }}>Triggered Rules ({triggered.length})</h3>
                {triggered.length === 0 ? <p style={{ color: 'var(--text-muted)' }}>No rules triggered</p> :
                    triggered.map((r, i) => (
                        <div key={i} className="recon-chain-step" style={{ borderLeftColor: 'var(--status-high)' }}>
                            <div className="step-name">{r.rule_name} {r.typology && <span className="badge badge-high" style={{ marginLeft: '0.5rem' }}>{r.typology}</span>}</div>
                            <div className="step-summary">{r.reasoning || 'No reasoning provided'}</div>
                            {r.evidence?.length > 0 && (
                                <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                    Evidence: {r.evidence.join(' | ')}
                                </div>
                            )}
                            <div style={{ marginTop: '0.3rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                Confidence: {((r.confidence || 0) * 100).toFixed(0)}%
                            </div>
                        </div>
                    ))
                }
            </div>

            {notTriggered.length > 0 && (
                <div className="card">
                    <h3 style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>Not Triggered ({notTriggered.length})</h3>
                    {notTriggered.map((r, i) => (
                        <div key={i} style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontSize: '0.88rem' }}>
                            {r.rule_name} — {r.reasoning || 'Conditions not met'}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function NarrativeTab({ caseId, narrative: initialNarrative }) {
    const [narrative, setNarrative] = useState(initialNarrative);
    const [content, setContent] = useState(initialNarrative?.content || '');
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');

    const handleSave = async () => {
        setSaving(true); setMessage('');
        try {
            const updated = await api.editNarrative(caseId, content);
            setNarrative(updated);
            setMessage('✅ Saved as version ' + updated.version);
        } catch (err) {
            setMessage('❌ ' + err.message);
        } finally {
            setSaving(false);
        }
    };

    const handleApprove = async () => {
        try {
            const updated = await api.approveNarrative(caseId);
            setNarrative(updated);
            setMessage('✅ Narrative approved');
        } catch (err) {
            setMessage('❌ ' + err.message);
        }
    };

    const handleReject = async () => {
        try {
            const updated = await api.rejectNarrative(caseId);
            setNarrative(updated);
            setMessage('⚠️ Narrative rejected');
        } catch (err) {
            setMessage('❌ ' + err.message);
        }
    };

    if (!narrative) return <div className="card"><p>No narrative generated yet</p></div>;

    return (
        <div>
            <div className="card" style={{ marginBottom: '1rem' }}>
                <div className="card-header">
                    <h3>SAR Narrative (v{narrative.version})</h3>
                    <span className={`badge badge-${narrative.status}`}>{narrative.status}</span>
                </div>

                {message && (
                    <div style={{ padding: '0.5rem 0.9rem', marginBottom: '1rem', borderRadius: 'var(--radius-md)', background: 'var(--bg-input)', fontSize: '0.85rem' }}>
                        {message}
                    </div>
                )}

                <div className="narrative-editor">
                    <textarea
                        id="narrative-content"
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                    />
                    <div className="narrative-toolbar">
                        <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
                            {saving ? 'Saving…' : '💾 Save Edit'}
                        </button>
                        <button className="btn btn-success btn-sm" onClick={handleApprove}>✅ Approve</button>
                        <button className="btn btn-danger btn-sm" onClick={handleReject}>❌ Reject</button>
                    </div>
                </div>
            </div>
        </div>
    );
}

function AuditTab({ caseId }) {
    const [trail, setTrail] = useState([]);
    const [loading, setLoading] = useState(true);
    const [recon, setRecon] = useState(null);
    const [reconLoading, setReconLoading] = useState(false);

    useEffect(() => {
        api.getAuditTrail(caseId).then(setTrail).catch(() => { }).finally(() => setLoading(false));
    }, [caseId]);

    const handleReconstruct = async () => {
        setReconLoading(true);
        try {
            const data = await api.reconstruct(caseId);
            setRecon(data);
        } catch (err) {
            setRecon({ error: err.message });
        } finally {
            setReconLoading(false);
        }
    };

    if (loading) return <div className="loading-center"><div className="spinner" /><span>Loading audit trail…</span></div>;

    return (
        <div>
            <div className="card" style={{ marginBottom: '1rem' }}>
                <div className="card-header">
                    <h3>Full Audit Trail ({trail.length} events)</h3>
                    <button className="btn btn-ghost btn-sm" onClick={handleReconstruct} disabled={reconLoading}>
                        {reconLoading ? 'Reconstructing…' : '🔗 Reconstruct Reasoning'}
                    </button>
                </div>

                <div className="audit-timeline">
                    {trail.map((event, i) => (
                        <div key={i} className="audit-event">
                            <div className="audit-event-header">
                                <span className="audit-event-type">{event.event_type}</span>
                                <span className="audit-event-time">
                                    {event.timestamp ? new Date(event.timestamp).toLocaleString() : '—'}
                                </span>
                            </div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                                by {event.user_id}
                            </div>
                            <div className="audit-event-data">
                                {JSON.stringify(event.event_data, null, 2)}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {recon && (
                <div className="recon-panel">
                    <h3 style={{ marginBottom: '1rem' }}>🔗 Reasoning Chain Reconstruction</h3>
                    {recon.error ? (
                        <p style={{ color: 'var(--status-high)' }}>{recon.error}</p>
                    ) : (
                        <div>
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                                Tracing: <strong>{recon.case_id}</strong> – reconstructing why the system produced this output
                            </p>
                            {recon.chain?.map((step, i) => (
                                <div key={i} className="recon-chain-step">
                                    <div className="step-name">Step {i + 1}: {step.step}</div>
                                    <div className="step-summary">{step.summary}</div>
                                    {step.triggered_rules && (
                                        <div style={{ fontSize: '0.78rem', marginTop: '0.25rem', color: 'var(--accent-amber)' }}>
                                            Rules: {step.triggered_rules.join(', ')}
                                        </div>
                                    )}
                                    {step.llm_provider && (
                                        <div style={{ fontSize: '0.78rem', marginTop: '0.25rem', color: 'var(--accent-cyan)' }}>
                                            LLM: {step.llm_provider}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

/* ============================================================
   ALERTS PAGE
   ============================================================ */
function AlertsPage() {
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        api.listAlerts().then(setAlerts).catch(() => { }).finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="loading-center"><div className="spinner" /><span>Loading alerts…</span></div>;

    return (
        <div>
            <div className="page-header">
                <h2>Alerts</h2>
                <p>High-risk case notifications</p>
            </div>

            {alerts.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
                    <p style={{ color: 'var(--text-muted)' }}>No alerts</p>
                </div>
            ) : (
                <div className="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Case ID</th>
                                <th>Type</th>
                                <th>Risk Score</th>
                                <th>Message</th>
                                <th>Created</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {alerts.map((a, i) => (
                                <tr key={i}>
                                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{a.case_id}</td>
                                    <td><span className="badge badge-high">{a.alert_type}</span></td>
                                    <td>{(a.risk_score || 0).toFixed(2)}</td>
                                    <td style={{ maxWidth: 400 }}>{a.message}</td>
                                    <td>{a.created_at ? new Date(a.created_at).toLocaleString() : '—'}</td>
                                    <td>
                                        <button className="btn btn-ghost btn-sm" onClick={() => navigate(`/cases/${a.case_id}`)}>
                                            View →
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}

/* ============================================================
   APP SHELL
   ============================================================ */
export default function App() {
    const { user, login, register, logout } = useAuth();

    if (!user) {
        return <LoginPage onLogin={login} onRegister={register} />;
    }

    return (
        <Router>
            <div className="app-layout">
                <Sidebar user={user} logout={logout} />
                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/ingest" element={<IngestPage />} />
                        <Route path="/cases/:caseId" element={<CaseDetailPage />} />
                        <Route path="/alerts" element={<AlertsPage />} />
                        <Route path="*" element={<Navigate to="/" />} />
                    </Routes>
                </main>
            </div>
        </Router>
    );
}
