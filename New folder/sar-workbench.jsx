import { useState, useEffect, useCallback, createContext, useContext } from "react";

// ─── MOCK DATA ─────────────────────────────────────────────────────────────
const MOCK_USER = {
  id: "ANA-2847",
  name: "J. Hartwell",
  role: "Senior Analyst",
  purpose: "sar_drafting",
};

const MOCK_CASES = [
  {
    id: "SAR-2025-00142",
    customerId: "CUST-****-7821",
    typology: "Layering via Shell Entities",
    riskScore: 87,
    confidence: 91,
    dataQuality: "HIGH",
    status: "Human Review Required",
    updated: "2025-02-14 16:42",
  },
  {
    id: "SAR-2025-00138",
    customerId: "CUST-****-4402",
    typology: "Structuring / Smurfing",
    riskScore: 74,
    confidence: 83,
    dataQuality: "MEDIUM",
    status: "Reasoning Complete",
    updated: "2025-02-14 11:20",
  },
  {
    id: "SAR-2025-00131",
    customerId: "CUST-****-9913",
    typology: "Trade-Based ML (TBML)",
    riskScore: 92,
    confidence: 95,
    dataQuality: "HIGH",
    status: "Regulator-Ready",
    updated: "2025-02-13 09:05",
  },
  {
    id: "SAR-2025-00127",
    customerId: "CUST-****-3307",
    typology: "High-Risk Jurisdiction Flows",
    riskScore: 61,
    confidence: 67,
    dataQuality: "LOW",
    status: "Awaiting Ingestion",
    updated: "2025-02-12 14:33",
  },
  {
    id: "SAR-2025-00119",
    customerId: "CUST-****-6650",
    typology: "PEP Exposure + Unusual Patterns",
    riskScore: 79,
    confidence: 88,
    dataQuality: "HIGH",
    status: "Returned",
    updated: "2025-02-11 17:18",
  },
];

const TRIGGERED_RULES = [
  {
    id: "AML-VELOCITY-01",
    title: "Transaction Velocity Anomaly",
    severity: "HIGH",
    description:
      "42 transactions exceeding £9,000 threshold detected within 72-hour window. Pattern consistent with structured placement activity.",
    evidenceCount: 8,
    open: true,
  },
  {
    id: "AML-STRUCT-02",
    title: "Structuring Indicator",
    severity: "HIGH",
    description:
      "Multiple cash deposits slightly below £10,000 reporting threshold across 6 branches. Temporal clustering identified.",
    evidenceCount: 12,
    open: false,
  },
  {
    id: "AML-BEHAV-07",
    title: "Behavioural Deviation from Customer Profile",
    severity: "MEDIUM",
    description:
      "Transaction volume increased 340% versus 12-month baseline. Account activity inconsistent with declared business purpose.",
    evidenceCount: 5,
    open: false,
  },
];

const NARRATIVE_CONTENT = `Subject Overview

The subject entity, a limited company incorporated in England and Wales (Company No. ****2847), maintains three accounts at this institution. The primary account (****7821) has been active since March 2019, with declared business activity in commercial property consultancy.

Suspicious Activity Identified

Between 14 November 2024 and 24 January 2025, the account received forty-two (42) structured cash deposits totalling £387,450. Each deposit was made below the £10,000 reporting threshold, with amounts ranging from £8,200 to £9,850. Deposits were made across six branch locations, with no discernible operational justification.

Transaction analysis reveals that deposited funds were transferred within 24–72 hours to three third-party beneficiaries registered in jurisdictions flagged as high-risk by FATF: [ENTITY-A] in Cyprus, [ENTITY-B] in the UAE, and [ENTITY-C] in the British Virgin Islands.

Risk Assessment

The combination of structuring behaviour, rapid layering through offshore entities, and the significant deviation from the customer's declared business profile gives rise to a suspicion that the funds may represent the proceeds of criminal conduct, or may be intended for use in unlawful activity.

This report is submitted in accordance with the Proceeds of Crime Act 2002 (POCA), Section 330.`;

// ─── AUTH CONTEXT ───────────────────────────────────────────────────────────
const AuthContext = createContext(null);

function useAuth() {
  return useContext(AuthContext);
}

// ─── SESSION TIMER ──────────────────────────────────────────────────────────
function useSessionTimer(initialSeconds = 1800) {
  const [seconds, setSeconds] = useState(initialSeconds);
  useEffect(() => {
    const t = setInterval(() => setSeconds((s) => (s > 0 ? s - 1 : 0)), 1000);
    return () => clearInterval(t);
  }, []);
  const m = String(Math.floor(seconds / 60)).padStart(2, "0");
  const s = String(seconds % 60).padStart(2, "0");
  return `${m}:${s}`;
}

// ─── COLOUR HELPERS ─────────────────────────────────────────────────────────
const STATUS_COLORS = {
  "Awaiting Ingestion": { bg: "#FFF8E6", text: "#92600A", dot: "#F59E0B" },
  "Reasoning Complete": { bg: "#EFF6FF", text: "#1D4ED8", dot: "#3B82F6" },
  "Human Review Required": { bg: "#FFF1F2", text: "#9F1239", dot: "#F43F5E" },
  "Regulator-Ready": { bg: "#F0FDF4", text: "#166534", dot: "#22C55E" },
  Returned: { bg: "#F5F3FF", text: "#5B21B6", dot: "#8B5CF6" },
};

const QUALITY_COLORS = {
  HIGH: { bg: "#F0FDF4", text: "#166534" },
  MEDIUM: { bg: "#FFF8E6", text: "#92600A" },
  LOW: { bg: "#FFF1F2", text: "#9F1239" },
};

const SEVERITY_COLORS = {
  HIGH: { bg: "#FFF1F2", text: "#9F1239", border: "#FECDD3" },
  MEDIUM: { bg: "#FFF8E6", text: "#92600A", border: "#FDE68A" },
  LOW: { bg: "#F0FDF4", text: "#166534", border: "#BBF7D0" },
};

// ─── GOVERNANCE HEADER ──────────────────────────────────────────────────────
function GovernanceHeader({ user, sessionTime }) {
  return (
    <header
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        height: 56,
        background: "#FFFFFF",
        borderBottom: "1px solid #E2E8F0",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 24px",
        zIndex: 1000,
        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
      }}
    >
      {/* Left: Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 32,
              height: 32,
              background: "#0B3D91",
              borderRadius: 4,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span
            style={{
              fontWeight: 700,
              fontSize: 15,
              color: "#0B3D91",
              letterSpacing: "-0.01em",
            }}
          >
            SAR Workbench
          </span>
        </div>
        <div
          style={{
            width: 1,
            height: 28,
            background: "#E2E8F0",
            margin: "0 4px",
          }}
        />
        <div style={{ display: "flex", gap: 8 }}>
          {[
            "On-Prem Deployment",
            "UK Data Residency",
            "Approved LLM: GOV-GPT-V1",
          ].map((tag) => (
            <span
              key={tag}
              style={{
                fontSize: 11,
                fontWeight: 500,
                color: "#0B3D91",
                background: "#E6F0FF",
                border: "1px solid #BFDBFE",
                borderRadius: 4,
                padding: "2px 8px",
                letterSpacing: "0.01em",
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Right: User info */}
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 11, color: "#64748B", marginBottom: 1 }}>
            Session expires
          </div>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: sessionTime < "05:00" ? "#DC2626" : "#0B3D91",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {sessionTime}
          </div>
        </div>
        <div
          style={{
            width: 1,
            height: 28,
            background: "#E2E8F0",
          }}
        />
        <div>
          <div
            style={{ fontSize: 12, fontWeight: 600, color: "#0F172A" }}
          >
            {user.name}
          </div>
          <div style={{ fontSize: 11, color: "#64748B" }}>
            {user.id} · {user.role}
          </div>
        </div>
        <div>
          <span
            style={{
              fontSize: 11,
              fontWeight: 500,
              color: "#166534",
              background: "#F0FDF4",
              border: "1px solid #BBF7D0",
              borderRadius: 4,
              padding: "3px 10px",
            }}
          >
            ✓ COMPLIANT
          </span>
        </div>
        <div>
          <span
            style={{
              fontSize: 11,
              fontWeight: 500,
              color: "#475569",
              background: "#F1F5F9",
              border: "1px solid #E2E8F0",
              borderRadius: 4,
              padding: "3px 10px",
            }}
          >
            Purpose: {user.purpose}
          </span>
        </div>
      </div>
    </header>
  );
}

// ─── SIDEBAR ────────────────────────────────────────────────────────────────
function Sidebar({ currentPage, navigate, activeCaseId }) {
  const topItems = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2" />
          <rect x="14" y="3" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2" />
          <rect x="3" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2" />
          <rect x="14" y="14" width="7" height="7" rx="1" stroke="currentColor" strokeWidth="2" />
        </svg>
      ),
    },
    {
      id: "cases",
      label: "Cases",
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      id: "audit",
      label: "Audit Logs",
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M9 12h6M9 16h6M9 8h6M5 3h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      ),
    },
    {
      id: "admin",
      label: "Admin",
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
          <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" stroke="currentColor" strokeWidth="2" />
        </svg>
      ),
    },
  ];

  const caseSubItems = activeCaseId
    ? [
        { id: "ingestion", label: "Ingestion" },
        { id: "workbench", label: "Workbench" },
        { id: "review", label: "Review" },
        { id: "submission", label: "Submission" },
        { id: "post-submission", label: "Post-Submission" },
      ]
    : [];

  const isActive = (id) => currentPage === id;

  return (
    <nav
      style={{
        position: "fixed",
        top: 56,
        left: 0,
        bottom: 0,
        width: 220,
        background: "#FFFFFF",
        borderRight: "1px solid #E2E8F0",
        display: "flex",
        flexDirection: "column",
        padding: "16px 0",
        overflowY: "auto",
        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
        zIndex: 900,
      }}
    >
      <div style={{ padding: "0 12px", flex: 1 }}>
        {topItems.map((item) => (
          <div key={item.id}>
            <button
              onClick={() => navigate(item.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                width: "100%",
                padding: "8px 10px",
                borderRadius: 6,
                border: "none",
                cursor: "pointer",
                background: isActive(item.id) ? "#0B3D91" : "transparent",
                color: isActive(item.id) ? "#FFFFFF" : "#475569",
                fontSize: 13,
                fontWeight: isActive(item.id) ? 600 : 400,
                fontFamily: "inherit",
                textAlign: "left",
                marginBottom: 2,
                transition: "background 0.15s, color 0.15s",
              }}
              onMouseEnter={(e) => {
                if (!isActive(item.id)) {
                  e.currentTarget.style.background = "#E6F0FF";
                  e.currentTarget.style.color = "#0B3D91";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive(item.id)) {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "#475569";
                }
              }}
            >
              <span style={{ opacity: isActive(item.id) ? 1 : 0.7 }}>
                {item.icon}
              </span>
              {item.label}
            </button>

            {/* Case sub-items */}
            {item.id === "cases" && activeCaseId && (
              <div
                style={{
                  marginLeft: 16,
                  marginTop: 2,
                  marginBottom: 4,
                  borderLeft: "2px solid #E2E8F0",
                  paddingLeft: 12,
                }}
              >
                <div
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    color: "#94A3B8",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    padding: "4px 0",
                  }}
                >
                  {activeCaseId}
                </div>
                {caseSubItems.map((sub) => (
                  <button
                    key={sub.id}
                    onClick={() => navigate(sub.id)}
                    style={{
                      display: "block",
                      width: "100%",
                      padding: "6px 8px",
                      borderRadius: 5,
                      border: "none",
                      cursor: "pointer",
                      background: isActive(sub.id) ? "#E6F0FF" : "transparent",
                      color: isActive(sub.id) ? "#0B3D91" : "#64748B",
                      fontSize: 12,
                      fontWeight: isActive(sub.id) ? 600 : 400,
                      fontFamily: "inherit",
                      textAlign: "left",
                      marginBottom: 1,
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive(sub.id)) {
                        e.currentTarget.style.background = "#F1F5F9";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive(sub.id)) {
                        e.currentTarget.style.background = "transparent";
                      }
                    }}
                  >
                    {sub.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: "12px 16px",
          borderTop: "1px solid #F1F5F9",
          marginTop: 8,
        }}
      >
        <div style={{ fontSize: 10, color: "#94A3B8", lineHeight: 1.5 }}>
          UKFIU Compliant · v4.2.1
          <br />
          Policy Rev: 2025-Q1
        </div>
      </div>
    </nav>
  );
}

// ─── PAGE WRAPPER ────────────────────────────────────────────────────────────
function PageContent({ children }) {
  return (
    <main
      style={{
        marginLeft: 220,
        marginTop: 56,
        minHeight: "calc(100vh - 56px)",
        background: "#F8FAFC",
        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
      }}
    >
      {children}
    </main>
  );
}

// ─── SHARED: PAGE HEADER ─────────────────────────────────────────────────────
function PageHeader({ title, subtitle, actions }) {
  return (
    <div
      style={{
        background: "#FFFFFF",
        borderBottom: "1px solid #E2E8F0",
        padding: "20px 32px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <div>
        <h1
          style={{
            fontSize: 20,
            fontWeight: 700,
            color: "#0F172A",
            margin: 0,
            letterSpacing: "-0.02em",
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p style={{ fontSize: 13, color: "#64748B", margin: "4px 0 0" }}>
            {subtitle}
          </p>
        )}
      </div>
      {actions && <div style={{ display: "flex", gap: 8 }}>{actions}</div>}
    </div>
  );
}

// ─── BUTTON COMPONENTS ───────────────────────────────────────────────────────
function PrimaryButton({ children, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        background: disabled ? "#94A3B8" : "#0B3D91",
        color: "#FFFFFF",
        border: "none",
        borderRadius: 6,
        padding: "8px 20px",
        fontSize: 13,
        fontWeight: 600,
        cursor: disabled ? "not-allowed" : "pointer",
        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
        letterSpacing: "0.01em",
        transition: "background 0.15s",
      }}
      onMouseEnter={(e) => {
        if (!disabled) e.currentTarget.style.background = "#0A2F6E";
      }}
      onMouseLeave={(e) => {
        if (!disabled) e.currentTarget.style.background = "#0B3D91";
      }}
    >
      {children}
    </button>
  );
}

function SecondaryButton({ children, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: "#FFFFFF",
        color: "#0B3D91",
        border: "1px solid #BFDBFE",
        borderRadius: 6,
        padding: "8px 16px",
        fontSize: 13,
        fontWeight: 500,
        cursor: "pointer",
        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
        transition: "background 0.15s",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "#E6F0FF";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "#FFFFFF";
      }}
    >
      {children}
    </button>
  );
}

// ─── LOGIN PAGE ──────────────────────────────────────────────────────────────
function LoginPage({ onLogin }) {
  const [id, setId] = useState("");
  const [pass, setPass] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = () => {
    if (id === "analyst" && pass === "demo2025") {
      onLogin();
    } else {
      setError("Invalid credentials. Use analyst / demo2025");
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0B3D91",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
      }}
    >
      <div
        style={{
          background: "#FFFFFF",
          borderRadius: 8,
          padding: 48,
          width: 400,
          boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
        }}
      >
        {/* Logo */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 32,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              background: "#0B3D91",
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div>
            <div
              style={{ fontWeight: 700, fontSize: 16, color: "#0B3D91" }}
            >
              SAR Workbench
            </div>
            <div style={{ fontSize: 11, color: "#64748B" }}>
              Intelligent Reporting Platform
            </div>
          </div>
        </div>

        <h2
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: "#0F172A",
            margin: "0 0 6px",
          }}
        >
          Secure Sign-In
        </h2>
        <p style={{ fontSize: 13, color: "#64748B", margin: "0 0 28px" }}>
          UKFIU-compliant access · Audit-logged session
        </p>

        <div style={{ marginBottom: 16 }}>
          <label
            style={{
              display: "block",
              fontSize: 12,
              fontWeight: 600,
              color: "#374151",
              marginBottom: 6,
            }}
          >
            Analyst ID
          </label>
          <input
            value={id}
            onChange={(e) => setId(e.target.value)}
            placeholder="e.g. analyst"
            style={{
              width: "100%",
              padding: "9px 12px",
              border: "1px solid #D1D5DB",
              borderRadius: 6,
              fontSize: 13,
              color: "#0F172A",
              fontFamily: "inherit",
              boxSizing: "border-box",
              outline: "none",
            }}
            onFocus={(e) => (e.target.style.borderColor = "#0B3D91")}
            onBlur={(e) => (e.target.style.borderColor = "#D1D5DB")}
          />
        </div>

        <div style={{ marginBottom: 24 }}>
          <label
            style={{
              display: "block",
              fontSize: 12,
              fontWeight: 600,
              color: "#374151",
              marginBottom: 6,
            }}
          >
            Password
          </label>
          <input
            type="password"
            value={pass}
            onChange={(e) => setPass(e.target.value)}
            placeholder="••••••••"
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            style={{
              width: "100%",
              padding: "9px 12px",
              border: "1px solid #D1D5DB",
              borderRadius: 6,
              fontSize: 13,
              fontFamily: "inherit",
              boxSizing: "border-box",
              outline: "none",
            }}
            onFocus={(e) => (e.target.style.borderColor = "#0B3D91")}
            onBlur={(e) => (e.target.style.borderColor = "#D1D5DB")}
          />
        </div>

        {error && (
          <div
            style={{
              background: "#FFF1F2",
              border: "1px solid #FECDD3",
              borderRadius: 6,
              padding: "8px 12px",
              fontSize: 12,
              color: "#9F1239",
              marginBottom: 16,
            }}
          >
            {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          style={{
            width: "100%",
            background: "#0B3D91",
            color: "#FFFFFF",
            border: "none",
            borderRadius: 6,
            padding: "10px",
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            fontFamily: "inherit",
          }}
        >
          Sign In
        </button>

        <div
          style={{
            marginTop: 20,
            padding: "10px",
            background: "#F8FAFC",
            borderRadius: 6,
            fontSize: 11,
            color: "#64748B",
            textAlign: "center",
          }}
        >
          Demo: analyst / demo2025
        </div>

        <div
          style={{
            marginTop: 16,
            fontSize: 11,
            color: "#94A3B8",
            textAlign: "center",
            lineHeight: 1.6,
          }}
        >
          This system is for authorised use only.
          <br />
          All sessions are recorded and audited.
        </div>
      </div>
    </div>
  );
}

// ─── DASHBOARD PAGE ──────────────────────────────────────────────────────────
function CaseCard({ caseData, onClick }) {
  const statusStyle = STATUS_COLORS[caseData.status] || {};
  const qualityStyle = QUALITY_COLORS[caseData.dataQuality] || {};

  return (
    <div
      onClick={onClick}
      style={{
        background: "#FFFFFF",
        border: "1px solid #E2E8F0",
        borderRadius: 8,
        padding: "16px 20px",
        cursor: "pointer",
        transition: "border-color 0.15s, box-shadow 0.15s",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "#0B3D91";
        e.currentTarget.style.boxShadow = "0 2px 8px rgba(11,61,145,0.08)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "#E2E8F0";
        e.currentTarget.style.boxShadow = "none";
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 12,
        }}
      >
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#0B3D91" }}>
            {caseData.id}
          </div>
          <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
            {caseData.customerId}
          </div>
        </div>
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: statusStyle.text,
            background: statusStyle.bg,
            padding: "3px 8px",
            borderRadius: 4,
            display: "flex",
            alignItems: "center",
            gap: 5,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: statusStyle.dot,
              display: "inline-block",
            }}
          />
          {caseData.status}
        </span>
      </div>

      <div
        style={{
          fontSize: 12,
          color: "#374151",
          marginBottom: 12,
          fontWeight: 500,
        }}
      >
        {caseData.typology}
      </div>

      {/* Risk Score Bar */}
      <div style={{ marginBottom: 10 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginBottom: 4,
          }}
        >
          <span style={{ fontSize: 11, color: "#64748B" }}>
            Composite Risk Score
          </span>
          <span
            style={{ fontSize: 11, fontWeight: 700, color: "#0B3D91" }}
          >
            {caseData.riskScore}
          </span>
        </div>
        <div
          style={{
            background: "#E6F0FF",
            borderRadius: 3,
            height: 6,
          }}
        >
          <div
            style={{
              background: caseData.riskScore >= 85 ? "#DC2626" : caseData.riskScore >= 70 ? "#0B3D91" : "#3B82F6",
              borderRadius: 3,
              height: 6,
              width: `${caseData.riskScore}%`,
              transition: "width 0.4s ease",
            }}
          />
        </div>
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <span style={{ fontSize: 11, color: "#64748B" }}>
            Confidence:{" "}
          </span>
          <span style={{ fontSize: 11, fontWeight: 600, color: "#0F172A" }}>
            {caseData.confidence}%
          </span>
        </div>
        <span
          style={{
            fontSize: 10,
            fontWeight: 600,
            color: qualityStyle.text,
            background: qualityStyle.bg,
            padding: "2px 6px",
            borderRadius: 4,
          }}
        >
          DQ: {caseData.dataQuality}
        </span>
      </div>

      <div
        style={{
          fontSize: 10,
          color: "#94A3B8",
          marginTop: 10,
          paddingTop: 10,
          borderTop: "1px solid #F1F5F9",
        }}
      >
        Updated: {caseData.updated}
      </div>
    </div>
  );
}

function DashboardPage({ navigate, setActiveCase }) {
  const statuses = [
    "Awaiting Ingestion",
    "Reasoning Complete",
    "Human Review Required",
    "Regulator-Ready",
    "Returned",
  ];

  const grouped = statuses.reduce((acc, s) => {
    acc[s] = MOCK_CASES.filter((c) => c.status === s);
    return acc;
  }, {});

  return (
    <>
      <PageHeader
        title="Case Dashboard"
        subtitle="Active SAR pipeline · UKFIU Reporting Unit"
        actions={
          <>
            <SecondaryButton>Export Report</SecondaryButton>
            <PrimaryButton>+ New Case</PrimaryButton>
          </>
        }
      />
      <div style={{ padding: "24px 32px" }}>
        {/* Stats Row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(5, 1fr)",
            gap: 12,
            marginBottom: 28,
          }}
        >
          {[
            { label: "Total Active", value: "24", delta: "+3 this week" },
            { label: "High Risk (≥85)", value: "7", delta: "2 escalated" },
            { label: "Pending Review", value: "5", delta: "Due today" },
            { label: "Submitted MTD", value: "18", delta: "Target: 20" },
            { label: "Avg. Confidence", value: "84.7%", delta: "+2.1% vs Q4" },
          ].map((stat) => (
            <div
              key={stat.label}
              style={{
                background: "#FFFFFF",
                border: "1px solid #E2E8F0",
                borderRadius: 8,
                padding: "16px 20px",
              }}
            >
              <div style={{ fontSize: 11, color: "#64748B", marginBottom: 6 }}>
                {stat.label}
              </div>
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  color: "#0B3D91",
                  marginBottom: 4,
                }}
              >
                {stat.value}
              </div>
              <div style={{ fontSize: 11, color: "#94A3B8" }}>{stat.delta}</div>
            </div>
          ))}
        </div>

        {/* Case Columns */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 20,
          }}
        >
          {statuses.slice(0, 3).map((status) => {
            const sc = STATUS_COLORS[status];
            return (
              <div key={status}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 12,
                  }}
                >
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: sc.dot,
                      display: "inline-block",
                    }}
                  />
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: "#374151",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    {status}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      color: "#64748B",
                      background: "#F1F5F9",
                      padding: "1px 6px",
                      borderRadius: 4,
                      marginLeft: "auto",
                    }}
                  >
                    {grouped[status].length}
                  </span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {grouped[status].length > 0 ? (
                    grouped[status].map((c) => (
                      <CaseCard
                        key={c.id}
                        caseData={c}
                        onClick={() => {
                          setActiveCase(c.id);
                          navigate("ingestion");
                        }}
                      />
                    ))
                  ) : (
                    <div
                      style={{
                        background: "#FFFFFF",
                        border: "1px dashed #E2E8F0",
                        borderRadius: 8,
                        padding: 20,
                        textAlign: "center",
                        color: "#94A3B8",
                        fontSize: 12,
                      }}
                    >
                      No cases
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Second row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, 1fr)",
            gap: 20,
            marginTop: 20,
          }}
        >
          {statuses.slice(3).map((status) => {
            const sc = STATUS_COLORS[status];
            return (
              <div key={status}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 12,
                  }}
                >
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: sc.dot,
                      display: "inline-block",
                    }}
                  />
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: "#374151",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    {status}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      color: "#64748B",
                      background: "#F1F5F9",
                      padding: "1px 6px",
                      borderRadius: 4,
                      marginLeft: "auto",
                    }}
                  >
                    {grouped[status].length}
                  </span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {grouped[status].map((c) => (
                    <CaseCard
                      key={c.id}
                      caseData={c}
                      onClick={() => {
                        setActiveCase(c.id);
                        navigate("ingestion");
                      }}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

// ─── CONFIDENCE GAUGE ────────────────────────────────────────────────────────
function ConfidenceGauge({ label, value, size = 80 }) {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (value / 100) * circ;
  const color = value >= 80 ? "#0B3D91" : value >= 60 ? "#F59E0B" : "#DC2626";

  return (
    <div style={{ textAlign: "center" }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#E6F0FF"
          strokeWidth={8}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={8}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
        />
      </svg>
      <div
        style={{
          fontSize: 18,
          fontWeight: 700,
          color,
          marginTop: -4,
        }}
      >
        {value}%
      </div>
      <div style={{ fontSize: 11, color: "#64748B", marginTop: 4 }}>
        {label}
      </div>
    </div>
  );
}

// ─── INGESTION PAGE ──────────────────────────────────────────────────────────
function IngestionPage({ caseId, navigate }) {
  const [acknowledged, setAcknowledged] = useState(false);

  const issues = [
    {
      severity: "HIGH",
      msg: "3 transactions missing beneficiary account reference",
    },
    { severity: "HIGH", msg: "KYC documentation expired (>12 months)" },
    {
      severity: "MEDIUM",
      msg: "Alert source cross-reference partially unavailable",
    },
    {
      severity: "MEDIUM",
      msg: "Counterparty data lacks LEI for 2 entities",
    },
    { severity: "LOW", msg: "Non-critical metadata field missing in 7 records" },
  ];

  return (
    <>
      <PageHeader
        title="Data Ingestion & Quality Assessment"
        subtitle={`Case: ${caseId} · Ingestion validation in progress`}
      />
      <div style={{ padding: "24px 32px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          {/* Gauges */}
          <div
            style={{
              background: "#FFFFFF",
              border: "1px solid #E2E8F0",
              borderRadius: 8,
              padding: 24,
            }}
          >
            <h3
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: "#0F172A",
                margin: "0 0 24px",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Data Quality Dimensions
            </h3>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, 1fr)",
                gap: 24,
              }}
            >
              <ConfidenceGauge label="KYC Confidence" value={76} size={90} />
              <ConfidenceGauge label="Transaction Chain" value={91} size={90} />
              <ConfidenceGauge label="Alert Integrity" value={84} size={90} />
              <ConfidenceGauge label="Data Lineage" value={58} size={90} />
            </div>

            <div
              style={{
                marginTop: 24,
                padding: "12px 16px",
                background: "#E6F0FF",
                borderRadius: 6,
                border: "1px solid #BFDBFE",
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 600, color: "#0B3D91" }}>
                Composite Data Quality Score
              </div>
              <div
                style={{
                  fontSize: 24,
                  fontWeight: 700,
                  color: "#0B3D91",
                  marginTop: 4,
                }}
              >
                77.3%{" "}
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 400,
                    color: "#64748B",
                  }}
                >
                  · MEDIUM-HIGH
                </span>
              </div>
            </div>
          </div>

          {/* Issues Panel */}
          <div
            style={{
              background: "#FFFFFF",
              border: "1px solid #E2E8F0",
              borderRadius: 8,
              padding: 24,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <h3
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: "#0F172A",
                margin: "0 0 16px",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Flagged Issues ({issues.length})
            </h3>
            <div
              style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}
            >
              {issues.map((issue, i) => {
                const sc = SEVERITY_COLORS[issue.severity];
                return (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 10,
                      padding: "10px 12px",
                      background: sc.bg,
                      border: `1px solid ${sc.border}`,
                      borderRadius: 6,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        color: sc.text,
                        background: sc.border,
                        padding: "2px 6px",
                        borderRadius: 3,
                        whiteSpace: "nowrap",
                        marginTop: 1,
                      }}
                    >
                      {issue.severity}
                    </span>
                    <span style={{ fontSize: 12, color: "#374151", lineHeight: 1.5 }}>
                      {issue.msg}
                    </span>
                  </div>
                );
              })}
            </div>

            <div
              style={{
                marginTop: 20,
                padding: "12px 14px",
                background: "#F8FAFC",
                borderRadius: 6,
                border: "1px solid #E2E8F0",
              }}
            >
              <label
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={acknowledged}
                  onChange={(e) => setAcknowledged(e.target.checked)}
                  style={{ marginTop: 2, accentColor: "#0B3D91" }}
                />
                <span style={{ fontSize: 12, color: "#374151", lineHeight: 1.5 }}>
                  I acknowledge the flagged data quality issues and confirm these
                  have been reviewed before proceeding to AI-assisted reasoning.
                </span>
              </label>
            </div>

            <div style={{ marginTop: 16 }}>
              <PrimaryButton
                disabled={!acknowledged}
                onClick={() => navigate("workbench")}
              >
                Proceed with Reasoning →
              </PrimaryButton>
            </div>
          </div>
        </div>

        {/* Source Summary */}
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            padding: 20,
            marginTop: 20,
          }}
        >
          <h3
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "#0F172A",
              margin: "0 0 14px",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Ingested Data Sources
          </h3>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 12,
            }}
          >
            {[
              { label: "Transaction Records", count: "247", status: "OK" },
              { label: "KYC Documents", count: "14", status: "PARTIAL" },
              { label: "Alert Records", count: "6", status: "OK" },
              { label: "Counterparty Data", count: "31", status: "PARTIAL" },
            ].map((source) => (
              <div
                key={source.label}
                style={{
                  padding: "12px 16px",
                  background: "#F8FAFC",
                  borderRadius: 6,
                  border: "1px solid #E2E8F0",
                }}
              >
                <div style={{ fontSize: 12, color: "#64748B", marginBottom: 4 }}>
                  {source.label}
                </div>
                <div
                  style={{
                    fontSize: 20,
                    fontWeight: 700,
                    color: "#0B3D91",
                    marginBottom: 4,
                  }}
                >
                  {source.count}
                </div>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    color:
                      source.status === "OK" ? "#166534" : "#92600A",
                    background:
                      source.status === "OK" ? "#F0FDF4" : "#FFF8E6",
                    padding: "2px 6px",
                    borderRadius: 3,
                  }}
                >
                  {source.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

// ─── WORKBENCH PAGE ──────────────────────────────────────────────────────────
function WorkbenchPage({ caseId, navigate }) {
  const [openRules, setOpenRules] = useState({ "AML-VELOCITY-01": true });
  const [showDrawer, setShowDrawer] = useState(false);
  const [editingNarrative, setEditingNarrative] = useState(false);
  const [narrativeText, setNarrativeText] = useState(NARRATIVE_CONTENT);

  const toggleRule = (id) => {
    setOpenRules((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <>
      <PageHeader
        title="Analysis Workbench"
        subtitle={`Case: ${caseId} · AI-assisted reasoning in progress`}
        actions={
          <>
            <SecondaryButton onClick={() => setShowDrawer(!showDrawer)}>
              Prompt Transparency
            </SecondaryButton>
            <PrimaryButton onClick={() => navigate("review")}>
              Submit for Review →
            </PrimaryButton>
          </>
        }
      />
      <div
        style={{
          display: "grid",
          gridTemplateColumns: showDrawer ? "1fr 1fr 280px" : "1fr 1fr",
          gap: 0,
          height: "calc(100vh - 56px - 65px)",
        }}
      >
        {/* LEFT PANE: Rules */}
        <div
          style={{
            borderRight: "1px solid #E2E8F0",
            overflowY: "auto",
            background: "#FFFFFF",
          }}
        >
          <div
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid #E2E8F0",
              background: "#F8FAFC",
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              Triggered Rules
            </div>
            <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
              3 rules matched · Policy engine v2.4
            </div>
          </div>

          <div style={{ padding: 16 }}>
            {TRIGGERED_RULES.map((rule) => {
              const sc = SEVERITY_COLORS[rule.severity];
              const isOpen = openRules[rule.id];
              return (
                <div
                  key={rule.id}
                  style={{
                    border: "1px solid #E2E8F0",
                    borderRadius: 7,
                    marginBottom: 10,
                    overflow: "hidden",
                  }}
                >
                  <button
                    onClick={() => toggleRule(rule.id)}
                    style={{
                      width: "100%",
                      padding: "12px 16px",
                      background: isOpen ? "#E6F0FF" : "#FFFFFF",
                      border: "none",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                      textAlign: "left",
                    }}
                  >
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        color: sc.text,
                        background: sc.bg,
                        border: `1px solid ${sc.border}`,
                        padding: "2px 6px",
                        borderRadius: 3,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {rule.severity}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          fontSize: 12,
                          fontWeight: 600,
                          color: "#0F172A",
                        }}
                      >
                        {rule.id}
                      </div>
                      <div style={{ fontSize: 11, color: "#64748B" }}>
                        {rule.title}
                      </div>
                    </div>
                    <span
                      style={{
                        fontSize: 11,
                        color: "#94A3B8",
                        transform: isOpen ? "rotate(180deg)" : "rotate(0deg)",
                        transition: "transform 0.2s",
                        display: "inline-block",
                      }}
                    >
                      ▾
                    </span>
                  </button>
                  {isOpen && (
                    <div
                      style={{
                        padding: "12px 16px",
                        background: "#FAFBFC",
                        borderTop: "1px solid #E2E8F0",
                      }}
                    >
                      <p
                        style={{
                          fontSize: 12,
                          color: "#374151",
                          margin: "0 0 10px",
                          lineHeight: 1.6,
                        }}
                      >
                        {rule.description}
                      </p>
                      <div style={{ fontSize: 11, color: "#64748B" }}>
                        Evidence records linked: {" "}
                        <strong style={{ color: "#0B3D91" }}>
                          {rule.evidenceCount}
                        </strong>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Evidence Graph Placeholder */}
          <div style={{ padding: "0 16px 16px" }}>
            <div
              style={{
                border: "1px solid #E2E8F0",
                borderRadius: 7,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  padding: "12px 16px",
                  background: "#F8FAFC",
                  borderBottom: "1px solid #E2E8F0",
                  fontSize: 12,
                  fontWeight: 700,
                  color: "#374151",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Evidence Graph
              </div>
              <div
                style={{
                  height: 160,
                  background: "#FFFFFF",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                {/* Simulated graph nodes */}
                {[
                  { x: "50%", y: "50%", label: "SUBJECT", primary: true },
                  { x: "20%", y: "25%", label: "ENTITY-A" },
                  { x: "80%", y: "25%", label: "ENTITY-B" },
                  { x: "20%", y: "75%", label: "ACC-7821" },
                  { x: "80%", y: "75%", label: "ENTITY-C" },
                ].map((node, i) => (
                  <div
                    key={i}
                    style={{
                      position: "absolute",
                      left: node.x,
                      top: node.y,
                      transform: "translate(-50%, -50%)",
                      width: node.primary ? 44 : 36,
                      height: node.primary ? 44 : 36,
                      borderRadius: "50%",
                      background: node.primary ? "#0B3D91" : "#E6F0FF",
                      border: `2px solid ${node.primary ? "#0B3D91" : "#BFDBFE"}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexDirection: "column",
                    }}
                  >
                    <span
                      style={{
                        fontSize: 8,
                        fontWeight: 700,
                        color: node.primary ? "#FFFFFF" : "#0B3D91",
                        textAlign: "center",
                        lineHeight: 1.1,
                      }}
                    >
                      {node.label}
                    </span>
                  </div>
                ))}
                {/* Lines */}
                <svg
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: "100%",
                    pointerEvents: "none",
                  }}
                >
                  {[
                    ["50%", "50%", "20%", "25%"],
                    ["50%", "50%", "80%", "25%"],
                    ["50%", "50%", "20%", "75%"],
                    ["50%", "50%", "80%", "75%"],
                  ].map((line, i) => (
                    <line
                      key={i}
                      x1={line[0]}
                      y1={line[1]}
                      x2={line[2]}
                      y2={line[3]}
                      stroke="#BFDBFE"
                      strokeWidth="1.5"
                      strokeDasharray="4 3"
                    />
                  ))}
                </svg>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT PANE: Narrative */}
        <div
          style={{
            borderRight: showDrawer ? "1px solid #E2E8F0" : "none",
            overflowY: "auto",
            background: "#FFFFFF",
          }}
        >
          <div
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid #E2E8F0",
              background: "#F8FAFC",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                SAR Narrative Draft
              </div>
              <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                Confidence: 91% · 4 claims mapped
              </div>
            </div>
            <SecondaryButton onClick={() => setEditingNarrative(!editingNarrative)}>
              {editingNarrative ? "Save" : "Edit"}
            </SecondaryButton>
          </div>

          <div style={{ padding: "20px 24px" }}>
            {/* Confidence indicators */}
            <div
              style={{
                display: "flex",
                gap: 8,
                marginBottom: 16,
              }}
            >
              {[
                { label: "Overall Confidence", val: "91%", color: "#0B3D91" },
                { label: "Claim Coverage", val: "4/4", color: "#166534" },
                { label: "Unresolved", val: "0", color: "#94A3B8" },
              ].map((ind) => (
                <div
                  key={ind.label}
                  style={{
                    padding: "6px 10px",
                    background: "#F8FAFC",
                    border: "1px solid #E2E8F0",
                    borderRadius: 5,
                    fontSize: 11,
                  }}
                >
                  <span style={{ color: "#64748B" }}>{ind.label}: </span>
                  <span style={{ fontWeight: 700, color: ind.color }}>
                    {ind.val}
                  </span>
                </div>
              ))}
            </div>

            {editingNarrative ? (
              <textarea
                value={narrativeText}
                onChange={(e) => setNarrativeText(e.target.value)}
                style={{
                  width: "100%",
                  minHeight: 400,
                  padding: 16,
                  border: "1px solid #BFDBFE",
                  borderRadius: 6,
                  fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
                  fontSize: 12,
                  lineHeight: 1.7,
                  color: "#0F172A",
                  resize: "vertical",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            ) : (
              <div
                style={{
                  border: "1px solid #E2E8F0",
                  borderRadius: 6,
                  overflow: "hidden",
                }}
              >
                {narrativeText.split("\n\n").map((section, i) => {
                  const lines = section.split("\n");
                  const isHeader =
                    lines[0] &&
                    !lines[0].startsWith(" ") &&
                    lines.length === 1;
                  if (isHeader) {
                    return (
                      <div
                        key={i}
                        style={{
                          padding: "10px 16px",
                          background: "#0B3D91",
                          color: "#FFFFFF",
                          fontSize: 12,
                          fontWeight: 700,
                          letterSpacing: "0.04em",
                        }}
                      >
                        {lines[0]}
                      </div>
                    );
                  }
                  return (
                    <div
                      key={i}
                      style={{
                        padding: "12px 16px",
                        borderBottom:
                          i < narrativeText.split("\n\n").length - 1
                            ? "1px solid #F1F5F9"
                            : "none",
                      }}
                    >
                      {lines.map((line, j) =>
                        j === 0 && line && !line.startsWith(" ") ? (
                          <div
                            key={j}
                            style={{
                              fontSize: 12,
                              fontWeight: 700,
                              color: "#0B3D91",
                              marginBottom: 6,
                            }}
                          >
                            {line}
                          </div>
                        ) : (
                          <p
                            key={j}
                            style={{
                              fontSize: 12,
                              color: "#374151",
                              lineHeight: 1.7,
                              margin: "0 0 6px",
                            }}
                          >
                            {line}
                          </p>
                        )
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* DRAWER: Prompt Transparency */}
        {showDrawer && (
          <div
            style={{
              overflowY: "auto",
              background: "#F8FAFC",
            }}
          >
            <div
              style={{
                padding: "16px 16px",
                borderBottom: "1px solid #E2E8F0",
                background: "#0B3D91",
              }}
            >
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: "#FFFFFF",
                  marginBottom: 2,
                }}
              >
                Prompt Contract
              </div>
              <div style={{ fontSize: 11, color: "#93C5FD" }}>
                Transparency & audit record
              </div>
            </div>
            <div style={{ padding: 16 }}>
              {[
                {
                  label: "Data Exposure",
                  value: "No raw data exposed to model",
                  ok: true,
                },
                {
                  label: "Model Version",
                  value: "GOV-GPT-V1 (approved)",
                  ok: true,
                },
                {
                  label: "Prompt Template",
                  value: "SAR-NARR-v3.2",
                  ok: true,
                },
                {
                  label: "Output Reviewed",
                  value: "Pending analyst sign-off",
                  ok: false,
                },
                {
                  label: "PII Handling",
                  value: "Masked before inference",
                  ok: true,
                },
                {
                  label: "Jurisdiction",
                  value: "UK on-premises only",
                  ok: true,
                },
              ].map((item) => (
                <div
                  key={item.label}
                  style={{
                    padding: "10px 12px",
                    background: "#FFFFFF",
                    border: "1px solid #E2E8F0",
                    borderRadius: 6,
                    marginBottom: 8,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: 3,
                    }}
                  >
                    <span style={{ fontSize: 11, color: "#64748B" }}>
                      {item.label}
                    </span>
                    <span style={{ fontSize: 12 }}>{item.ok ? "✓" : "⏳"}</span>
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: item.ok ? "#166534" : "#92600A",
                    }}
                  >
                    {item.value}
                  </div>
                </div>
              ))}

              <div
                style={{
                  marginTop: 8,
                  padding: "10px 12px",
                  background: "#E6F0FF",
                  border: "1px solid #BFDBFE",
                  borderRadius: 6,
                  fontSize: 11,
                  color: "#1D4ED8",
                  lineHeight: 1.5,
                }}
              >
                All inferences are governed by the AI Governance Policy v2.1. The
                model receives only structured, pseudonymised data inputs.
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

// ─── REVIEW PAGE ──────────────────────────────────────────────────────────────
function ReviewPage({ caseId, navigate }) {
  const [trackChanges, setTrackChanges] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editPurpose, setEditPurpose] = useState("");

  const versions = [
    { v: "v1.0", by: "GOV-GPT-V1", time: "14 Feb 16:32", note: "Initial AI draft" },
    { v: "v1.1", by: "J. Hartwell", time: "14 Feb 17:10", note: "Factual correction: deposit count" },
    { v: "v1.2", by: "J. Hartwell", time: "14 Feb 17:44", note: "Amended beneficiary details" },
  ];

  return (
    <>
      <PageHeader
        title="Human Review"
        subtitle={`Case: ${caseId} · Review and approve before submission`}
        actions={
          <>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                background: "#F8FAFC",
                border: "1px solid #E2E8F0",
                borderRadius: 6,
                padding: "4px 12px",
              }}
            >
              <span style={{ fontSize: 12, color: "#64748B" }}>
                Track Changes
              </span>
              <div
                onClick={() => setTrackChanges(!trackChanges)}
                style={{
                  width: 36,
                  height: 20,
                  background: trackChanges ? "#0B3D91" : "#CBD5E1",
                  borderRadius: 10,
                  cursor: "pointer",
                  position: "relative",
                  transition: "background 0.2s",
                }}
              >
                <div
                  style={{
                    width: 14,
                    height: 14,
                    background: "#FFFFFF",
                    borderRadius: "50%",
                    position: "absolute",
                    top: 3,
                    left: trackChanges ? 19 : 3,
                    transition: "left 0.2s",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.15)",
                  }}
                />
              </div>
            </div>
            <SecondaryButton onClick={() => setShowEditModal(true)}>
              Request Edit
            </SecondaryButton>
            <PrimaryButton onClick={() => navigate("submission")}>
              Approve & Continue →
            </PrimaryButton>
          </>
        }
      />

      <div style={{ padding: "24px 32px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: 24 }}>
          {/* Narrative */}
          <div>
            {/* Track changes banner */}
            {trackChanges && (
              <div
                style={{
                  padding: "8px 14px",
                  background: "#FFF8E6",
                  border: "1px solid #FDE68A",
                  borderRadius: 6,
                  fontSize: 12,
                  color: "#92600A",
                  marginBottom: 12,
                }}
              >
                ⚡ Track Changes mode active — edits highlighted in amber
              </div>
            )}

            <div
              style={{
                background: "#FFFFFF",
                border: "1px solid #E2E8F0",
                borderRadius: 8,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  padding: "12px 16px",
                  background: "#F8FAFC",
                  borderBottom: "1px solid #E2E8F0",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div style={{ fontSize: 12, fontWeight: 700, color: "#374151", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  SAR Narrative · v1.2
                </div>
                <span
                  style={{
                    fontSize: 11,
                    color: "#64748B",
                  }}
                >
                  Under Review
                </span>
              </div>

              <div style={{ padding: "20px 24px" }}>
                {NARRATIVE_CONTENT.split("\n\n").map((section, i) => {
                  const lines = section.split("\n");
                  const isHeader = lines.length === 1;
                  if (isHeader) {
                    return (
                      <div
                        key={i}
                        style={{
                          fontSize: 13,
                          fontWeight: 700,
                          color: "#0B3D91",
                          margin: "16px 0 6px",
                          paddingBottom: 6,
                          borderBottom: "1px solid #E6F0FF",
                        }}
                      >
                        {lines[0]}
                      </div>
                    );
                  }
                  return (
                    <div key={i} style={{ marginBottom: 12 }}>
                      {lines.map((line, j) => {
                        const isChanged =
                          trackChanges && line.includes("forty-two");
                        return (
                          <p
                            key={j}
                            style={{
                              fontSize: 13,
                              color: "#374151",
                              lineHeight: 1.7,
                              margin: "0 0 6px",
                              background: isChanged
                                ? "#FFFBEB"
                                : "transparent",
                              borderLeft: isChanged
                                ? "3px solid #F59E0B"
                                : "none",
                              paddingLeft: isChanged ? 8 : 0,
                            }}
                          >
                            {line}
                            {isChanged && (
                              <span
                                style={{
                                  fontSize: 10,
                                  color: "#92600A",
                                  marginLeft: 8,
                                  fontWeight: 600,
                                }}
                              >
                                [EDITED v1.1]
                              </span>
                            )}
                          </p>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Version History */}
          <div>
            <div
              style={{
                background: "#FFFFFF",
                border: "1px solid #E2E8F0",
                borderRadius: 8,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  padding: "12px 16px",
                  background: "#F8FAFC",
                  borderBottom: "1px solid #E2E8F0",
                  fontSize: 12,
                  fontWeight: 700,
                  color: "#374151",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Version History
              </div>
              {versions.map((v, i) => (
                <div
                  key={v.v}
                  style={{
                    padding: "12px 16px",
                    borderBottom:
                      i < versions.length - 1 ? "1px solid #F1F5F9" : "none",
                    background: i === versions.length - 1 ? "#E6F0FF" : "#FFFFFF",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: 4,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#0B3D91",
                      }}
                    >
                      {v.v}
                    </span>
                    {i === versions.length - 1 && (
                      <span
                        style={{
                          fontSize: 10,
                          color: "#0B3D91",
                          fontWeight: 600,
                        }}
                      >
                        CURRENT
                      </span>
                    )}
                  </div>
                  <div
                    style={{ fontSize: 11, color: "#374151", marginBottom: 2 }}
                  >
                    {v.note}
                  </div>
                  <div style={{ fontSize: 10, color: "#94A3B8" }}>
                    {v.by} · {v.time}
                  </div>
                </div>
              ))}
            </div>

            {/* Reviewer Notes */}
            <div
              style={{
                background: "#FFFFFF",
                border: "1px solid #E2E8F0",
                borderRadius: 8,
                padding: 16,
                marginTop: 16,
              }}
            >
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: "#374151",
                  marginBottom: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Review Notes
              </div>
              <textarea
                placeholder="Add review annotation..."
                style={{
                  width: "100%",
                  minHeight: 80,
                  padding: "8px 10px",
                  border: "1px solid #E2E8F0",
                  borderRadius: 5,
                  fontSize: 12,
                  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                  resize: "vertical",
                  outline: "none",
                  boxSizing: "border-box",
                  color: "#374151",
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Edit Modal */}
      {showEditModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 2000,
          }}
        >
          <div
            style={{
              background: "#FFFFFF",
              borderRadius: 8,
              width: 440,
              overflow: "hidden",
              boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
            }}
          >
            <div
              style={{
                padding: "16px 20px",
                background: "#0B3D91",
                color: "#FFFFFF",
              }}
            >
              <div style={{ fontSize: 14, fontWeight: 700 }}>Request Edit</div>
              <div style={{ fontSize: 12, color: "#93C5FD" }}>
                Document reason for modification
              </div>
            </div>
            <div style={{ padding: 20 }}>
              <label
                style={{
                  display: "block",
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#374151",
                  marginBottom: 8,
                }}
              >
                Purpose of Change
              </label>
              <select
                value={editPurpose}
                onChange={(e) => setEditPurpose(e.target.value)}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  border: "1px solid #D1D5DB",
                  borderRadius: 6,
                  fontSize: 13,
                  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                  marginBottom: 16,
                  outline: "none",
                  color: "#0F172A",
                }}
              >
                <option value="">Select purpose...</option>
                <option>Factual correction</option>
                <option>Legal compliance update</option>
                <option>Supervisor instruction</option>
                <option>Completeness amendment</option>
                <option>Policy alignment</option>
              </select>
              <label
                style={{
                  display: "block",
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#374151",
                  marginBottom: 8,
                }}
              >
                Details
              </label>
              <textarea
                placeholder="Describe the specific change requested..."
                style={{
                  width: "100%",
                  minHeight: 80,
                  padding: "8px 12px",
                  border: "1px solid #D1D5DB",
                  borderRadius: 6,
                  fontSize: 12,
                  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                  resize: "vertical",
                  outline: "none",
                  boxSizing: "border-box",
                  color: "#374151",
                }}
              />
              <div
                style={{
                  display: "flex",
                  gap: 8,
                  justifyContent: "flex-end",
                  marginTop: 16,
                }}
              >
                <SecondaryButton onClick={() => setShowEditModal(false)}>
                  Cancel
                </SecondaryButton>
                <PrimaryButton
                  disabled={!editPurpose}
                  onClick={() => setShowEditModal(false)}
                >
                  Submit Edit Request
                </PrimaryButton>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ─── SUBMISSION PAGE ──────────────────────────────────────────────────────────
function SubmissionPage({ caseId, navigate }) {
  const [submitted, setSubmitted] = useState(false);

  const checks = [
    { label: "All narrative sections complete", done: true },
    { label: "All claims mapped to evidence", done: true },
    { label: "No low-confidence unresolved claims", done: true },
    { label: "Human review sign-off recorded", done: true },
    { label: "Data quality acknowledgment logged", done: true },
    { label: "Supervisor approval obtained", done: false },
  ];

  const allDone = checks.every((c) => c.done);

  if (submitted) {
    navigate("post-submission");
  }

  return (
    <>
      <PageHeader
        title="Submission Compliance Check"
        subtitle={`Case: ${caseId} · Pre-submission validation`}
      />
      <div style={{ padding: "24px 32px", maxWidth: 700 }}>
        {/* Compliance Checklist */}
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            overflow: "hidden",
            marginBottom: 20,
          }}
        >
          <div
            style={{
              padding: "14px 20px",
              background: "#F8FAFC",
              borderBottom: "1px solid #E2E8F0",
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}
          >
            <div
              style={{
                fontSize: 13,
                fontWeight: 700,
                color: "#374151",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Compliance Checklist
            </div>
            <span
              style={{
                fontSize: 11,
                background: allDone ? "#F0FDF4" : "#FFF1F2",
                color: allDone ? "#166534" : "#9F1239",
                padding: "2px 8px",
                borderRadius: 4,
                fontWeight: 600,
              }}
            >
              {checks.filter((c) => c.done).length}/{checks.length} Complete
            </span>
          </div>
          {checks.map((check, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "14px 20px",
                borderBottom:
                  i < checks.length - 1 ? "1px solid #F1F5F9" : "none",
                background: check.done ? "#FFFFFF" : "#FFFBEB",
              }}
            >
              <div
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: "50%",
                  background: check.done ? "#0B3D91" : "#E2E8F0",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                {check.done ? (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                    <path
                      d="M20 6L9 17l-5-5"
                      stroke="white"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : (
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: "#F59E0B",
                    }}
                  />
                )}
              </div>
              <span
                style={{
                  fontSize: 13,
                  color: check.done ? "#0F172A" : "#92600A",
                  fontWeight: check.done ? 400 : 500,
                }}
              >
                {check.label}
              </span>
              {!check.done && (
                <span
                  style={{
                    marginLeft: "auto",
                    fontSize: 11,
                    color: "#92600A",
                    background: "#FFF8E6",
                    border: "1px solid #FDE68A",
                    padding: "2px 8px",
                    borderRadius: 4,
                    fontWeight: 600,
                  }}
                >
                  PENDING
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Warning */}
        {!allDone && (
          <div
            style={{
              padding: "12px 16px",
              background: "#FFF8E6",
              border: "1px solid #FDE68A",
              borderRadius: 6,
              fontSize: 12,
              color: "#92600A",
              marginBottom: 20,
              lineHeight: 1.5,
            }}
          >
            ⚠ One or more compliance checks are incomplete. Submission is disabled
            until all checks pass. Contact your supervisor to obtain approval.
          </div>
        )}

        {/* SAR Summary */}
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            padding: 20,
            marginBottom: 20,
          }}
        >
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: "#374151",
              marginBottom: 14,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Submission Summary
          </div>
          {[
            ["Case Reference", caseId],
            ["Subject ID", "CUST-****-7821"],
            ["Typology", "Layering via Shell Entities"],
            ["Reporting Obligation", "POCA 2002, s.330"],
            ["Jurisdiction", "England & Wales"],
            ["UKFIU Destination", "ukfiu-sar@nationalcrimeagency.gov.uk"],
          ].map(([k, v]) => (
            <div
              key={k}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "7px 0",
                borderBottom: "1px solid #F1F5F9",
                fontSize: 12,
              }}
            >
              <span style={{ color: "#64748B" }}>{k}</span>
              <span style={{ fontWeight: 600, color: "#0F172A" }}>{v}</span>
            </div>
          ))}
        </div>

        <PrimaryButton
          disabled={!allDone}
          onClick={() => setSubmitted(true)}
        >
          Submit SAR to UKFIU →
        </PrimaryButton>
      </div>
    </>
  );
}

// ─── POST-SUBMISSION PAGE ────────────────────────────────────────────────────
function PostSubmissionPage({ caseId }) {
  const timestamp = "2025-02-14T18:03:42Z";
  const refNum = "UKFIU-2025-SAR-047821";
  const auditHash = "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069";

  return (
    <>
      <PageHeader
        title="Submission Complete"
        subtitle={`Case: ${caseId} · SAR successfully submitted to UKFIU`}
      />
      <div style={{ padding: "32px", maxWidth: 680 }}>
        {/* Success Banner */}
        <div
          style={{
            padding: "20px 24px",
            background: "#F0FDF4",
            border: "1px solid #BBF7D0",
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            gap: 16,
            marginBottom: 24,
          }}
        >
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: "50%",
              background: "#22C55E",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path
                d="M20 6L9 17l-5-5"
                stroke="white"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#166534" }}>
              SAR Successfully Submitted
            </div>
            <div style={{ fontSize: 12, color: "#15803D", marginTop: 2 }}>
              Transmitted to UKFIU · Acknowledgement pending
            </div>
          </div>
        </div>

        {/* Details */}
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            overflow: "hidden",
            marginBottom: 20,
          }}
        >
          <div
            style={{
              padding: "12px 20px",
              background: "#F8FAFC",
              borderBottom: "1px solid #E2E8F0",
              fontSize: 12,
              fontWeight: 700,
              color: "#374151",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Submission Record
          </div>
          {[
            ["Submission Timestamp", timestamp],
            ["Submitted By", "J. Hartwell (ANA-2847)"],
            ["UKFIU Reference Number", refNum],
            ["Case ID", caseId],
            ["Transmission Method", "Encrypted SFTP · Gov.UK Gateway"],
          ].map(([k, v]) => (
            <div
              key={k}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "12px 20px",
                borderBottom: "1px solid #F1F5F9",
                fontSize: 12,
              }}
            >
              <span style={{ color: "#64748B" }}>{k}</span>
              <span
                style={{
                  fontWeight: 600,
                  color: "#0F172A",
                  fontFamily:
                    k === "UKFIU Reference Number"
                      ? "'IBM Plex Mono', monospace"
                      : "inherit",
                  fontSize: k === "UKFIU Reference Number" ? 11 : 12,
                }}
              >
                {v}
              </span>
            </div>
          ))}
        </div>

        {/* Audit Hash */}
        <div
          style={{
            background: "#0B3D91",
            borderRadius: 8,
            padding: "16px 20px",
            marginBottom: 20,
          }}
        >
          <div
            style={{
              fontSize: 11,
              color: "#93C5FD",
              fontWeight: 600,
              marginBottom: 6,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Immutable Audit Hash
          </div>
          <div
            style={{
              fontSize: 11,
              color: "#FFFFFF",
              fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
              wordBreak: "break-all",
              lineHeight: 1.5,
            }}
          >
            {auditHash}
          </div>
          <div
            style={{
              fontSize: 10,
              color: "#93C5FD",
              marginTop: 8,
            }}
          >
            SHA-256 · Tamper-evident · Logged to immutable audit ledger
          </div>
        </div>

        {/* Download buttons */}
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            padding: 20,
          }}
        >
          <div
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: "#374151",
              marginBottom: 14,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Download Documents
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {[
              { label: "SAR PDF", desc: "Redacted official document", icon: "📄" },
              { label: "Audit Bundle ZIP", desc: "Full evidence package", icon: "📦" },
              { label: "JSON Export", desc: "Machine-readable data", icon: "{ }" },
            ].map((dl) => (
              <button
                key={dl.label}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "10px 16px",
                  border: "1px solid #BFDBFE",
                  borderRadius: 6,
                  background: "#FFFFFF",
                  cursor: "pointer",
                  fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                  transition: "background 0.15s",
                }}
                onMouseEnter={(e) =>
                  (e.currentTarget.style.background = "#E6F0FF")
                }
                onMouseLeave={(e) =>
                  (e.currentTarget.style.background = "#FFFFFF")
                }
              >
                <span style={{ fontSize: 18 }}>{dl.icon}</span>
                <div style={{ textAlign: "left" }}>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      color: "#0B3D91",
                    }}
                  >
                    {dl.label}
                  </div>
                  <div style={{ fontSize: 10, color: "#64748B" }}>
                    {dl.desc}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

// ─── CASES LIST PAGE ──────────────────────────────────────────────────────────
function CasesPage({ navigate, setActiveCase }) {
  return (
    <>
      <PageHeader
        title="Case Management"
        subtitle="All active and historical SAR cases"
        actions={
          <>
            <SecondaryButton>Filter</SecondaryButton>
            <PrimaryButton>+ New Case</PrimaryButton>
          </>
        }
      />
      <div style={{ padding: "24px 32px" }}>
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#F8FAFC" }}>
                {[
                  "Case ID",
                  "Customer",
                  "Typology",
                  "Risk Score",
                  "Status",
                  "Data Quality",
                  "Updated",
                  "",
                ].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "10px 16px",
                      textAlign: "left",
                      fontSize: 11,
                      fontWeight: 700,
                      color: "#64748B",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      borderBottom: "1px solid #E2E8F0",
                      fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MOCK_CASES.map((c, i) => {
                const sc = STATUS_COLORS[c.status] || {};
                const qc = QUALITY_COLORS[c.dataQuality] || {};
                return (
                  <tr
                    key={c.id}
                    style={{
                      borderBottom:
                        i < MOCK_CASES.length - 1
                          ? "1px solid #F1F5F9"
                          : "none",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background = "#F8FAFC")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = "transparent")
                    }
                  >
                    <td
                      style={{
                        padding: "12px 16px",
                        fontSize: 12,
                        fontWeight: 700,
                        color: "#0B3D91",
                        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                      }}
                    >
                      {c.id}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        fontSize: 12,
                        color: "#64748B",
                        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                      }}
                    >
                      {c.customerId}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        fontSize: 12,
                        color: "#374151",
                        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                      }}
                    >
                      {c.typology}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div
                          style={{
                            width: 60,
                            height: 5,
                            background: "#E6F0FF",
                            borderRadius: 3,
                          }}
                        >
                          <div
                            style={{
                              width: `${c.riskScore}%`,
                              height: 5,
                              background:
                                c.riskScore >= 85
                                  ? "#DC2626"
                                  : "#0B3D91",
                              borderRadius: 3,
                            }}
                          />
                        </div>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            color: c.riskScore >= 85 ? "#DC2626" : "#0B3D91",
                            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                          }}
                        >
                          {c.riskScore}
                        </span>
                      </div>
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 600,
                          color: sc.text,
                          background: sc.bg,
                          padding: "3px 8px",
                          borderRadius: 4,
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                        }}
                      >
                        <span
                          style={{
                            width: 5,
                            height: 5,
                            borderRadius: "50%",
                            background: sc.dot,
                          }}
                        />
                        {c.status}
                      </span>
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 600,
                          color: qc.text,
                          background: qc.bg,
                          padding: "2px 6px",
                          borderRadius: 3,
                          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                        }}
                      >
                        {c.dataQuality}
                      </span>
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        fontSize: 11,
                        color: "#94A3B8",
                        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                      }}
                    >
                      {c.updated}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <button
                        onClick={() => {
                          setActiveCase(c.id);
                          navigate("ingestion");
                        }}
                        style={{
                          fontSize: 12,
                          fontWeight: 500,
                          color: "#0B3D91",
                          background: "#E6F0FF",
                          border: "none",
                          borderRadius: 5,
                          padding: "5px 12px",
                          cursor: "pointer",
                          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                        }}
                      >
                        Open →
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

// ─── AUDIT LOGS PAGE ─────────────────────────────────────────────────────────
function AuditPage() {
  const logs = [
    { ts: "2025-02-14 18:03:42", user: "ANA-2847", action: "SAR_SUBMITTED", ref: "SAR-2025-00142", detail: "Submitted to UKFIU" },
    { ts: "2025-02-14 17:44:11", user: "ANA-2847", action: "NARRATIVE_EDITED", ref: "SAR-2025-00142", detail: "v1.2 — Amended beneficiary details" },
    { ts: "2025-02-14 17:10:03", user: "ANA-2847", action: "NARRATIVE_EDITED", ref: "SAR-2025-00142", detail: "v1.1 — Factual correction: deposit count" },
    { ts: "2025-02-14 16:42:17", user: "GOV-GPT-V1", action: "AI_DRAFT_GENERATED", ref: "SAR-2025-00142", detail: "Initial narrative draft at 91% confidence" },
    { ts: "2025-02-14 16:38:05", user: "ANA-2847", action: "INGESTION_ACKNOWLEDGED", ref: "SAR-2025-00142", detail: "Data quality issues acknowledged" },
    { ts: "2025-02-14 16:30:00", user: "ANA-2847", action: "CASE_ACCESSED", ref: "SAR-2025-00142", detail: "Session opened · Purpose: sar_drafting" },
    { ts: "2025-02-13 09:15:22", user: "ANA-2291", action: "SAR_SUBMITTED", ref: "SAR-2025-00131", detail: "Submitted to UKFIU" },
    { ts: "2025-02-12 14:35:10", user: "ANA-3301", action: "CASE_CREATED", ref: "SAR-2025-00127", detail: "New case ingested from alert pipeline" },
  ];

  const actionColors = {
    SAR_SUBMITTED: { bg: "#F0FDF4", text: "#166534" },
    NARRATIVE_EDITED: { bg: "#E6F0FF", text: "#1D4ED8" },
    AI_DRAFT_GENERATED: { bg: "#F5F3FF", text: "#5B21B6" },
    INGESTION_ACKNOWLEDGED: { bg: "#FFF8E6", text: "#92600A" },
    CASE_ACCESSED: { bg: "#F1F5F9", text: "#475569" },
    CASE_CREATED: { bg: "#F0FDF4", text: "#166534" },
  };

  return (
    <>
      <PageHeader
        title="Audit Logs"
        subtitle="Immutable event log · All actions recorded"
        actions={<SecondaryButton>Export CSV</SecondaryButton>}
      />
      <div style={{ padding: "24px 32px" }}>
        <div
          style={{
            background: "#FFFFFF",
            border: "1px solid #E2E8F0",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#F8FAFC" }}>
                {["Timestamp", "User / System", "Action", "Case Ref", "Detail"].map(
                  (h) => (
                    <th
                      key={h}
                      style={{
                        padding: "10px 16px",
                        textAlign: "left",
                        fontSize: 11,
                        fontWeight: 700,
                        color: "#64748B",
                        textTransform: "uppercase",
                        letterSpacing: "0.06em",
                        borderBottom: "1px solid #E2E8F0",
                        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                      }}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {logs.map((log, i) => {
                const ac = actionColors[log.action] || { bg: "#F1F5F9", text: "#475569" };
                return (
                  <tr
                    key={i}
                    style={{
                      borderBottom: i < logs.length - 1 ? "1px solid #F1F5F9" : "none",
                    }}
                  >
                    <td
                      style={{
                        padding: "10px 16px",
                        fontSize: 11,
                        color: "#64748B",
                        fontFamily: "'IBM Plex Mono', monospace",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {log.ts}
                    </td>
                    <td
                      style={{
                        padding: "10px 16px",
                        fontSize: 12,
                        fontWeight: 600,
                        color: "#0F172A",
                        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                      }}
                    >
                      {log.user}
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          color: ac.text,
                          background: ac.bg,
                          padding: "3px 8px",
                          borderRadius: 4,
                          fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                          letterSpacing: "0.04em",
                        }}
                      >
                        {log.action}
                      </span>
                    </td>
                    <td
                      style={{
                        padding: "10px 16px",
                        fontSize: 11,
                        fontWeight: 600,
                        color: "#0B3D91",
                        fontFamily: "'IBM Plex Mono', monospace",
                      }}
                    >
                      {log.ref}
                    </td>
                    <td
                      style={{
                        padding: "10px 16px",
                        fontSize: 12,
                        color: "#374151",
                        fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
                      }}
                    >
                      {log.detail}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

// ─── ADMIN PAGE ───────────────────────────────────────────────────────────────
function AdminPage() {
  return (
    <>
      <PageHeader
        title="Administration"
        subtitle="System configuration · Role management · Policy settings"
      />
      <div style={{ padding: "24px 32px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 20,
            marginBottom: 24,
          }}
        >
          {[
            { label: "Active Users", value: "14", sub: "3 roles configured" },
            { label: "Policy Version", value: "v2.1", sub: "Rev: 2025-Q1" },
            { label: "Model Approval", value: "GOV-GPT-V1", sub: "Approved · Valid" },
          ].map((card) => (
            <div
              key={card.label}
              style={{
                background: "#FFFFFF",
                border: "1px solid #E2E8F0",
                borderRadius: 8,
                padding: 20,
              }}
            >
              <div style={{ fontSize: 11, color: "#64748B", marginBottom: 6 }}>
                {card.label}
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#0B3D91", marginBottom: 4 }}>
                {card.value}
              </div>
              <div style={{ fontSize: 11, color: "#94A3B8" }}>{card.sub}</div>
            </div>
          ))}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 20,
          }}
        >
          {/* User Roles */}
          <div
            style={{
              background: "#FFFFFF",
              border: "1px solid #E2E8F0",
              borderRadius: 8,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "12px 20px",
                background: "#F8FAFC",
                borderBottom: "1px solid #E2E8F0",
                fontSize: 12,
                fontWeight: 700,
                color: "#374151",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              User Roles
            </div>
            {[
              { role: "Analyst", users: 8, perms: "Draft, Ingest, Workbench" },
              { role: "Reviewer", users: 4, perms: "Review, Approve, Request Edit" },
              { role: "Supervisor", users: 2, perms: "All + Final Approval" },
            ].map((r, i) => (
              <div
                key={r.role}
                style={{
                  padding: "12px 20px",
                  borderBottom: i < 2 ? "1px solid #F1F5F9" : "none",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 3,
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#0F172A" }}>
                    {r.role}
                  </span>
                  <span style={{ fontSize: 11, color: "#64748B" }}>
                    {r.users} users
                  </span>
                </div>
                <div style={{ fontSize: 11, color: "#94A3B8" }}>{r.perms}</div>
              </div>
            ))}
          </div>

          {/* System Config */}
          <div
            style={{
              background: "#FFFFFF",
              border: "1px solid #E2E8F0",
              borderRadius: 8,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "12px 20px",
                background: "#F8FAFC",
                borderBottom: "1px solid #E2E8F0",
                fontSize: 12,
                fontWeight: 700,
                color: "#374151",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              System Configuration
            </div>
            {[
              { k: "Deployment Mode", v: "On-Premises" },
              { k: "Data Residency", v: "UK Only" },
              { k: "Encryption", v: "AES-256 at rest + transit" },
              { k: "Session Timeout", v: "30 minutes" },
              { k: "Audit Retention", v: "7 years (POCA compliance)" },
              { k: "LLM Approved", v: "GOV-GPT-V1" },
            ].map(([k, v]) => (
              <div
                key={k}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "9px 20px",
                  borderBottom: "1px solid #F1F5F9",
                  fontSize: 12,
                }}
              >
                <span style={{ color: "#64748B" }}>{k}</span>
                <span style={{ fontWeight: 600, color: "#0F172A" }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

// ─── ROOT APPLICATION ────────────────────────────────────────────────────────
export default function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [currentPage, setCurrentPage] = useState("dashboard");
  const [activeCaseId, setActiveCaseId] = useState(null);
  const sessionTime = useSessionTimer(1800);

  const navigate = useCallback((page) => {
    setCurrentPage(page);
  }, []);

  const setActiveCase = useCallback((id) => {
    setActiveCaseId(id);
  }, []);

  if (!authenticated) {
    return <LoginPage onLogin={() => setAuthenticated(true)} />;
  }

  const renderPage = () => {
    switch (currentPage) {
      case "dashboard":
        return (
          <DashboardPage navigate={navigate} setActiveCase={setActiveCase} />
        );
      case "cases":
        return (
          <CasesPage navigate={navigate} setActiveCase={setActiveCase} />
        );
      case "audit":
        return <AuditPage />;
      case "admin":
        return <AdminPage />;
      case "ingestion":
        return (
          <IngestionPage
            caseId={activeCaseId || "SAR-2025-00142"}
            navigate={navigate}
          />
        );
      case "workbench":
        return (
          <WorkbenchPage
            caseId={activeCaseId || "SAR-2025-00142"}
            navigate={navigate}
          />
        );
      case "review":
        return (
          <ReviewPage
            caseId={activeCaseId || "SAR-2025-00142"}
            navigate={navigate}
          />
        );
      case "submission":
        return (
          <SubmissionPage
            caseId={activeCaseId || "SAR-2025-00142"}
            navigate={navigate}
          />
        );
      case "post-submission":
        return (
          <PostSubmissionPage caseId={activeCaseId || "SAR-2025-00142"} />
        );
      default:
        return (
          <DashboardPage navigate={navigate} setActiveCase={setActiveCase} />
        );
    }
  };

  return (
    <div style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif" }}>
      <GovernanceHeader user={MOCK_USER} sessionTime={sessionTime} />
      <Sidebar
        currentPage={currentPage}
        navigate={navigate}
        activeCaseId={
          ["ingestion", "workbench", "review", "submission", "post-submission"].includes(
            currentPage
          )
            ? activeCaseId
            : null
        }
      />
      <PageContent>{renderPage()}</PageContent>
    </div>
  );
}
