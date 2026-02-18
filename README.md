# SAR Narrative Generator with Full Audit Trail

AI-powered Suspicious Activity Report generation system with deterministic rule engine, ML classification, RAG-enhanced narrative generation, and immutable audit trail.

## Architecture

```
Input JSON → Data Normalizer → Rule Engine (8 rules) → ML Classifier
    → RAG Retrieval (ChromaDB) → Narrative Generator (LLM/Fallback)
    → Audit Trail (every step logged)
```

## Quick Start

### Prerequisites
- Python 3.11+, Node.js 20+, PostgreSQL 15+
- (Optional) Docker & Docker Compose, Ollama for LLM

### 1. Environment Setup
```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 2. Backend
```bash
pip install -r requirements.txt
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

### 4. Docker (Alternative)
```bash
docker-compose up --build
```

Open http://localhost:5173 → Register → Ingest a case → View results.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Get JWT token |
| POST | `/api/v1/cases/ingest` | Run full pipeline |
| GET | `/api/v1/cases` | List cases |
| GET | `/api/v1/cases/{id}` | Case detail |
| GET | `/api/v1/cases/{id}/narrative` | Get narrative |
| PUT | `/api/v1/cases/{id}/narrative` | Edit narrative |
| POST | `/api/v1/cases/{id}/narrative/approve` | Approve |
| POST | `/api/v1/cases/{id}/narrative/reject` | Reject |
| GET | `/api/v1/cases/{id}/audit` | Audit trail |
| GET | `/api/v1/cases/{id}/audit/reconstruct` | Why-chain |
| GET | `/api/v1/alerts` | List alerts |

## Sample Data

- `data/sample_input.json` – 50-txn structuring/layering scenario
- `data/sample_output_narrative.md` – Expected SAR output
- `data/sample_audit_record.json` – Full audit trail example

## Project Structure

```
backend/
├── api/           # FastAPI routes + main app
├── core/          # Config, auth, database
├── models/        # SQLAlchemy ORM models
├── schemas/       # Pydantic request/response schemas
└── services/      # Business logic (normalizer, rules, ML, RAG, narrative, audit, orchestrator)
frontend/
├── src/
│   ├── App.jsx    # React SPA (dashboard, ingest, case detail, audit, alerts)
│   ├── api.js     # API client
│   └── index.css  # Design system
data/              # Sample input/output
scripts/           # RAG ingestion
```

## Key Design Decisions

- **Rules before LLM**: Deterministic evaluation precedes LLM calls for explainability
- **Immutable audit**: Append-only `audit_events` table for regulatory reconstruction
- **Anti-hallucination**: Strict system prompt constrains LLM to evidence-only generation
- **Template fallback**: Works without LLM — generates narrative from templates
- **Versioned narratives**: Each edit creates a new version, preserving history
