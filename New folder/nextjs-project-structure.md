# 🏛 SAR Workbench — Next.js 14 Project Structure

## Setup

```bash
npx create-next-app@latest sar-workbench \
  --typescript --tailwind --app --src-dir
cd sar-workbench
npx shadcn-ui@latest init
npm install lucide-react
npm run dev
```

---

## Folder Structure

```
sar-workbench/
├── src/
│   ├── app/
│   │   ├── layout.tsx                    ← RootLayout
│   │   ├── globals.css
│   │   ├── page.tsx                      ← redirect → /dashboard
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   ├── cases/
│   │   │   ├── page.tsx                  ← Case list
│   │   │   └── [caseId]/
│   │   │       ├── layout.tsx            ← Case sub-layout
│   │   │       ├── ingestion/page.tsx
│   │   │       ├── workbench/page.tsx
│   │   │       ├── review/page.tsx
│   │   │       ├── submission/page.tsx
│   │   │       └── post-submission/page.tsx
│   │   ├── audit/
│   │   │   └── page.tsx
│   │   └── admin/
│   │       └── page.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── GovernanceHeader.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── CaseSubNav.tsx
│   │   ├── dashboard/
│   │   │   ├── CaseCard.tsx
│   │   │   └── StatusColumn.tsx
│   │   ├── ingestion/
│   │   │   ├── ConfidenceGauge.tsx
│   │   │   └── IssuesList.tsx
│   │   ├── workbench/
│   │   │   ├── RulesAccordion.tsx
│   │   │   ├── EvidenceGraph.tsx
│   │   │   ├── NarrativeEditor.tsx
│   │   │   └── PromptDrawer.tsx
│   │   ├── review/
│   │   │   ├── TrackChangesToggle.tsx
│   │   │   ├── EditModal.tsx
│   │   │   └── VersionHistory.tsx
│   │   ├── submission/
│   │   │   └── ComplianceChecklist.tsx
│   │   └── shared/
│   │       ├── StatusBadge.tsx
│   │       ├── PageHeader.tsx
│   │       └── DataQualityBadge.tsx
│   ├── context/
│   │   ├── AuthContext.tsx
│   │   └── SessionContext.tsx
│   ├── lib/
│   │   ├── mock-data.ts
│   │   ├── types.ts
│   │   └── auth.ts
│   └── middleware.ts
├── tailwind.config.ts
└── next.config.ts
```

---

## Key Files

### `middleware.ts`

```typescript
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login"];
const ROLE_PROTECTED: Record<string, string[]> = {
  "/admin": ["supervisor", "admin"],
};

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const session = request.cookies.get("sar_session")?.value;

  if (!session) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  try {
    const user = JSON.parse(atob(session));

    for (const [path, roles] of Object.entries(ROLE_PROTECTED)) {
      if (pathname.startsWith(path) && !roles.includes(user.role)) {
        return NextResponse.redirect(new URL("/dashboard", request.url));
      }
    }
  } catch {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
```

---

### `src/lib/types.ts`

```typescript
export type CaseStatus =
  | "Awaiting Ingestion"
  | "Reasoning Complete"
  | "Human Review Required"
  | "Regulator-Ready"
  | "Returned";

export type DataQuality = "HIGH" | "MEDIUM" | "LOW";

export type UserRole = "analyst" | "reviewer" | "supervisor" | "admin";

export interface SARCase {
  id: string;
  customerId: string;
  typology: string;
  riskScore: number;
  confidence: number;
  dataQuality: DataQuality;
  status: CaseStatus;
  updated: string;
}

export interface TriggeredRule {
  id: string;
  title: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  description: string;
  evidenceCount: number;
}

export interface AuditEvent {
  timestamp: string;
  userId: string;
  action: string;
  caseRef: string;
  detail: string;
}

export interface SessionUser {
  id: string;
  name: string;
  role: UserRole;
  purpose: "sar_drafting" | "review" | "audit";
}
```

---

### `src/context/AuthContext.tsx`

```typescript
"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { SessionUser } from "@/lib/types";

interface AuthContextType {
  user: SessionUser | null;
  login: (id: string, password: string) => Promise<boolean>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);

  const login = useCallback(async (id: string, password: string) => {
    // Replace with real auth
    if (id === "analyst" && password === "demo2025") {
      const sessionUser: SessionUser = {
        id: "ANA-2847",
        name: "J. Hartwell",
        role: "analyst",
        purpose: "sar_drafting",
      };
      setUser(sessionUser);
      // Set session cookie
      document.cookie = `sar_session=${btoa(JSON.stringify(sessionUser))}; path=/`;
      return true;
    }
    return false;
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    document.cookie = "sar_session=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, login, logout, isAuthenticated: !!user }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
```

---

### `src/app/layout.tsx`

```typescript
import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { GovernanceHeader } from "@/components/layout/GovernanceHeader";
import { Sidebar } from "@/components/layout/Sidebar";

const ibmPlexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-ibm-plex-sans",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-ibm-plex-mono",
});

export const metadata: Metadata = {
  title: "SAR Workbench | UKFIU Compliant",
  description: "Intelligent Suspicious Activity Report generation platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${ibmPlexSans.variable} ${ibmPlexMono.variable}`}>
        <AuthProvider>
          <GovernanceHeader />
          <Sidebar />
          <main className="ml-[220px] mt-[56px] min-h-[calc(100vh-56px)] bg-slate-50">
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}
```

---

### `tailwind.config.ts`

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0B3D91",
          light: "#E6F0FF",
          border: "#BFDBFE",
        },
      },
      fontFamily: {
        sans: ["var(--font-ibm-plex-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-ibm-plex-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
```

---

### `src/components/layout/GovernanceHeader.tsx`

```typescript
"use client";

import { useAuth } from "@/context/AuthContext";
import { useSessionTimer } from "@/lib/hooks/useSessionTimer";

export function GovernanceHeader() {
  const { user } = useAuth();
  const sessionTime = useSessionTimer(1800);

  return (
    <header className="fixed top-0 left-0 right-0 h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 z-50">
      {/* Brand + env tags */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-brand rounded flex items-center justify-center">
            {/* Icon */}
          </div>
          <span className="font-bold text-[15px] text-brand tracking-tight">
            SAR Workbench
          </span>
        </div>
        <div className="w-px h-7 bg-slate-200" />
        {["On-Prem Deployment", "UK Data Residency", "Approved LLM: GOV-GPT-V1"].map(
          (tag) => (
            <span
              key={tag}
              className="text-[11px] font-medium text-brand bg-brand-light border border-brand-border rounded px-2 py-0.5"
            >
              {tag}
            </span>
          )
        )}
      </div>

      {/* Right: user info */}
      <div className="flex items-center gap-5">
        <div className="text-right">
          <div className="text-[11px] text-slate-500">Session expires</div>
          <div className="text-[13px] font-semibold text-brand tabular-nums">
            {sessionTime}
          </div>
        </div>
        <div className="w-px h-7 bg-slate-200" />
        <div>
          <div className="text-[12px] font-semibold text-slate-900">{user?.name}</div>
          <div className="text-[11px] text-slate-500">
            {user?.id} · {user?.role}
          </div>
        </div>
        <span className="text-[11px] font-medium text-green-700 bg-green-50 border border-green-200 rounded px-2.5 py-1">
          ✓ COMPLIANT
        </span>
        <span className="text-[11px] font-medium text-slate-500 bg-slate-100 border border-slate-200 rounded px-2.5 py-1">
          Purpose: {user?.purpose}
        </span>
      </div>
    </header>
  );
}
```

---

### `src/components/ingestion/ConfidenceGauge.tsx`

```typescript
interface ConfidenceGaugeProps {
  label: string;
  value: number;
  size?: number;
}

export function ConfidenceGauge({ label, value, size = 90 }: ConfidenceGaugeProps) {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (value / 100) * circ;
  const color =
    value >= 80 ? "#0B3D91" : value >= 60 ? "#F59E0B" : "#DC2626";

  return (
    <div className="text-center">
      <svg
        width={size}
        height={size}
        style={{ transform: "rotate(-90deg)" }}
      >
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
      <div style={{ color }} className="text-lg font-bold -mt-1">
        {value}%
      </div>
      <div className="text-[11px] text-slate-500 mt-1">{label}</div>
    </div>
  );
}
```

---

### `src/lib/mock-data.ts`

```typescript
import { SARCase, TriggeredRule, AuditEvent } from "./types";

export const MOCK_CASES: SARCase[] = [
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
  // ... more cases
];

export const TRIGGERED_RULES: TriggeredRule[] = [
  {
    id: "AML-VELOCITY-01",
    title: "Transaction Velocity Anomaly",
    severity: "HIGH",
    description:
      "42 transactions exceeding £9,000 threshold detected within 72-hour window.",
    evidenceCount: 8,
  },
  // ... more rules
];
```

---

## Design Tokens

| Token | Value | Usage |
|-------|-------|-------|
| Primary Blue | `#0B3D91` | Headers, buttons, active states |
| Light Blue | `#E6F0FF` | Backgrounds, hover states |
| Blue Border | `#BFDBFE` | Card borders, inputs |
| Background | `#F8FAFC` | Page background |
| Text Primary | `#0F172A` | Headers |
| Text Secondary | `#374151` | Body text |
| Text Muted | `#64748B` | Labels, metadata |
| Border | `#E2E8F0` | Dividers, card borders |

## Policy Compliance

- All sessions logged with analyst ID, purpose, and timestamp
- PII masked before model inference
- Immutable SHA-256 audit hash on submission
- 7-year audit retention (POCA 2002)
- On-premises deployment only
- UK data residency enforced
