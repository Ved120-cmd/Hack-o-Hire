# SAR Narrative Generator - Refactoring Guide

## Overview

This document describes the refactored architecture of the SAR Narrative Generator, transformed from a prototype into a regulator-defensible, enterprise-grade system.

## Architecture Changes

### Phase 1: Case-Centric Wrapping ✅

**What Changed:**
- Introduced `cases` table as central entity
- Added `case_input_snapshots` for immutable input storage
- Added `sar_case_events` for canonical audit events
- Added `narrative_versions` for versioned narratives

**Key Files:**
- `backend/models/case.py`
- `backend/models/narrative_version.py`
- `backend/models/sar_case_event.py`

### Phase 2: Deterministic Rule Engine ✅

**What Changed:**
- Extracted rule logic from LLM prompts
- Created `RulesEngine` that evaluates rules deterministically BEFORE LLM
- Rules return structured JSON with typology mappings
- Rules are stored in `rule_evaluations` and `rule_evaluation_details`

**Key Files:**
- `backend/services/rules/rules_engine.py`
- `backend/models/rule_evaluation.py`

### Phase 3: RAG Decoupling ✅

**What Changed:**
- Created `RAGService` as the ONLY component allowed to query vector DB
- All retrievals logged with document IDs and similarity scores
- Tenant isolation enforced in vector queries
- Retrievals stored in `retrieval_events` and `retrieval_documents`

**Key Files:**
- `backend/services/rag/rag_service.py`
- `backend/models/rag_retrieval.py`

### Phase 4: LLM Hardening ✅

**What Changed:**
- Strict system prompts with anti-hallucination constraints
- JSON schema validation with retry logic
- Fallback template generation when LLM fails
- Stateless LLM calls (no memory, no chat history)
- Complete audit logging of prompts and responses

**Key Files:**
- `backend/services/llm/llm_orchestrator.py`
- `backend/services/llm/llm_prompts.py`
- `backend/services/llm/llm_validator.py`
- `backend/models/llm_request.py`

### Phase 5: Versioned Human-in-the-Loop ✅

**What Changed:**
- No UPDATE of narrative text - every edit creates new version
- `version_number` increments per case
- Approval/rejection tracked per version
- Complete version history maintained

**Key Files:**
- `backend/services/case/case_service.py` (edit_narrative, approve_narrative, reject_narrative)

### Phase 6: Audit Event Model ✅

**What Changed:**
- Canonical event types: `CASE_CREATED`, `RULES_EVALUATED`, `LLM_PROMPT_SENT`, etc.
- All events stored in `sar_case_events` (append-only)
- Events linked to cases, users, and timestamps

**Key Files:**
- `backend/services/audit/audit_service.py`
- `backend/models/sar_case_event.py`

### Phase 7: Hackathon Scalability ⏳

**Current State:**
- Synchronous processing (suitable for demo)
- Code structured as if event-driven (ready for Kafka)
- Comments indicate where async workers would go

**Future Enhancement:**
- Replace synchronous calls with Kafka events
- Add background workers for rule evaluation, RAG, LLM

### Phase 8: Tenant & RBAC ⏳

**Current State:**
- Tenant isolation enforced at service layer
- Basic tenant filtering in queries
- Minimal RBAC via headers (X-Tenant-ID, X-User-ID)

**Future Enhancement:**
- Full RBAC middleware with roles/permissions
- Row-level security in database
- Case-level access control

### Phase 9: Observability ✅

**What Changed:**
- Metrics service tracks LLM latency, rule triggers, narrative stats
- Structured logging with correlation IDs
- Monitoring endpoints: `/api/v1/monitoring/metrics`

**Key Files:**
- `backend/services/monitoring/metrics.py`
- `backend/api/routes/monitoring.py`

## Database Schema

### Core Tables

1. **cases** - Central case management
2. **case_input_snapshots** - Immutable input storage
3. **narrative_versions** - Versioned narratives
4. **sar_case_events** - Append-only audit log

### Processing Tables

5. **rule_evaluations** - Rule evaluation runs
6. **rule_evaluation_details** - Individual rule triggers
7. **retrieval_events** - RAG retrieval events
8. **retrieval_documents** - Retrieved documents
9. **llm_requests** - LLM request log
10. **llm_responses** - LLM response log

## API Endpoints

### Case Management

- `POST /api/v1/cases/ingest` - Ingest new case and trigger pipeline
- `GET /api/v1/cases/{case_id}` - Get case details
- `GET /api/v1/cases/{case_id}/audit-trail` - Get audit trail

### Narrative Management

- `POST /api/v1/cases/{case_id}/narratives/edit` - Edit narrative (creates new version)
- `POST /api/v1/cases/{case_id}/narratives/approve` - Approve narrative version
- `POST /api/v1/cases/{case_id}/narratives/reject` - Reject narrative version
- `GET /api/v1/cases/{case_id}/narratives/{version_id}` - Get narrative version

### Monitoring

- `GET /api/v1/monitoring/metrics` - Get system metrics
- `GET /api/v1/monitoring/health` - Health check

## Data Flow

```
1. POST /cases/ingest
   ↓
2. Create Case + Store Input Snapshot
   ↓
3. RulesEngine.evaluate() → rule_evaluations
   ↓
4. RAGService.retrieve_context() → retrieval_events
   ↓
5. LLMOrchestrator.generate_narrative() → llm_requests/responses
   ↓
6. Create NarrativeVersion (machine_generated)
   ↓
7. Analyst reviews → Edit → New NarrativeVersion (analyst_edited)
   ↓
8. Approve → Update NarrativeVersion status
```

## Security Features

1. **Tenant Isolation**
   - All queries filtered by `tenant_id`
   - Vector DB collections partitioned by tenant

2. **Immutable Audit Trail**
   - Append-only events
   - No UPDATE/DELETE on audit tables
   - Cryptographic hashes for integrity

3. **Data Scope Enforcement**
   - LLM prompts explicitly restrict data scope
   - No cross-case references allowed
   - Validation ensures only provided data is used

## Compliance Features

1. **Complete Audit Trail**
   - Every action logged with user, timestamp, payload
   - Can reconstruct entire case lifecycle

2. **Version Control**
   - All narrative edits create new versions
   - Approval history tracked
   - Can roll back to any version

3. **Explainability**
   - `reasoning_trace` links narrative to rules and data
   - Document IDs tracked for regulatory references
   - Typology mappings stored

## Deployment

### Prerequisites

- PostgreSQL 12+
- Python 3.9+
- Vector DB (Chroma/Pinecone) - optional for demo

### Setup

1. **Database Migration**
   ```bash
   psql -U postgres -d sar_db -f backend/db/migrations/001_create_sar_tables.sql
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run API**
   ```bash
   python backend/api/main.py
   ```

### Docker (Future)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "backend/api/main.py"]
```

## Testing

### Sample Request

```bash
curl -X POST http://localhost:8000/api/v1/cases/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-User-ID: demo-user" \
  -d @data/sample_case_input.json
```

## Future Enhancements

1. **Full RBAC** - Role-based access control with permissions
2. **Async Processing** - Kafka-based event-driven pipeline
3. **Multi-region** - Data residency enforcement
4. **Advanced Monitoring** - Prometheus/Grafana integration
5. **Model Drift Detection** - Track LLM output quality over time

## Compliance Checklist

- ✅ Immutable audit trail
- ✅ Deterministic rule engine
- ✅ RAG retrieval logging
- ✅ LLM prompt/response logging
- ✅ Narrative versioning
- ✅ Tenant isolation
- ✅ Data scope enforcement
- ✅ Explainability (reasoning_trace)
- ⏳ Full RBAC (basic implemented)
- ⏳ Encryption at rest (DB-level)
- ⏳ WORM storage (object storage)

## Notes for Regulators

1. **Deterministic Rules**: All rules evaluated BEFORE LLM - no rule logic in prompts
2. **Complete Traceability**: Every step logged with inputs/outputs
3. **No Hallucination**: LLM prompts explicitly prohibit fabrication
4. **Version Control**: All edits create new versions - no data loss
5. **Tenant Isolation**: Multi-tenant safe with complete data separation
