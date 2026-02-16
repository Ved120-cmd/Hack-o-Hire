# Omega Finalization Stage

## Overview

The Omega finalization stage is the final step in the SAR generation pipeline. It takes a validated `ClaimObject` from the Delta stage (claim generation) and produces a finalized SAR report ready for regulatory filing.

## Pipeline Position

```
Alpha (Ingestion) → Beta (KYC Enrichment) → Gamma (Rules Engine)
→ Delta (Claim Generation) → Omega Finalization (YOU ARE HERE)
```

## Responsibilities

1. **Take ClaimObject** from Delta stage (`claim_gen.generate_claim()`)
2. **Generate SAR Narrative** via RAG pipeline + LLM (placeholder implementation)
3. **Log Audit Events** to `audit_logs` table:
   - `SAR_GENERATION_STARTED`
   - `SAR_REPORT_GENERATED`
   - `SAR_REPORT_SUBMITTED` (optional, if filing)
4. **Update Claim Audit Trail** with Omega stage actions
5. **Return Finalized Claim** ready for regulatory filing

## Integration Points

### INPUT: Delta Stage (Claim Generation)

```python
from claim_gen.claim_gen import generate_claim

claim = generate_claim(
    case_id="sar-123",
    alert_ids=["alert-1"],
    customer_data={...},
    pipeline_transforms=[...],
    rule_results={...},
    fraud_scores={...},
    rag_results={...},
)
```

### OUTPUT: Finalized Claim + Audit Events

```python
from backend.omega.omega_finalization import run_omega

omega_result = run_omega(omega_input)
# Returns:
# {
#     "case_id": str,
#     "claim": Dict[str, Any],      # Finalized ClaimObject
#     "narrative": str,              # SAR narrative text
#     "audit_events": List[Dict],    # AuditLog entries created
# }
```

### AUDIT TRAIL CONNECTION

All SAR events are logged to the `audit_logs` table using your exact `AuditLog` model:

```python
from backend.query_audit_trail import query_sar_trail

# Query SAR-specific audit trail
audit_logs = query_sar_trail(case_id)

# Query pattern (from query_audit_trail.py):
# db.query(AuditLog).filter(
#     AuditLog.case_id == case_id,
#     AuditLog.event_type.in_([
#         AuditEventType.SAR_GENERATION_STARTED,
#         AuditEventType.SAR_REPORT_GENERATED,
#         AuditEventType.SAR_REPORT_SUBMITTED,
#     ])
# )
```

### RAG PIPELINE CONNECTION (TODO)

The `_generate_sar_narrative()` method is currently a placeholder. Replace it with your actual RAG pipeline + LLM integration:

**Current Placeholder:**
- Generates basic narrative from claim object fields
- Uses `claim.regulatory_hooks` for regulatory references
- Uses `claim.suspicious_patterns` for pattern summaries

**Expected RAG Integration:**
1. **RAG Retrieval:**
   - Input: `claim.regulatory_hooks` (from Delta stage)
   - Input: `claim.suspicious_patterns` (patterns detected)
   - Output: Regulatory context + SAR templates

2. **LLM Generation:**
   - Input: RAG context + claim object
   - Output: SAR narrative text
   - Metadata: Token usage, model version, temperature

**Integration Point:**
```python
# In omega_finalization.py, replace _generate_sar_narrative():
def _generate_sar_narrative(self, claim: ClaimObject) -> Tuple[str, Dict]:
    # TODO: Call RAG pipeline
    rag_context = rag_service.retrieve(
        regulatory_hooks=claim.regulatory_hooks,
        patterns=claim.suspicious_patterns,
    )
    
    # TODO: Call LLM
    narrative = llm_service.generate(
        prompt=build_prompt(rag_context, claim),
        model="your-llm-model",
    )
    
    return narrative, llm_metadata
```

## Usage Example

See `example_usage.py` for a complete example showing:
1. Delta stage claim generation
2. Omega stage finalization
3. Audit trail querying

## File Structure

```
backend/omega/
├── __init__.py              # Package exports
├── omega_finalization.py    # Main Omega implementation
├── example_usage.py         # Usage examples
└── README.md                # This file
```

## Dependencies

- `backend.db.session.SessionLocal` - Database session factory
- `backend.models.audit_log.AuditLog` - Audit log model
- `claim_gen.models.claim_schema.ClaimObject` - Claim schema model
- `claim_gen.claim_gen.generate_claim` - Claim generator function

## Database Schema

Uses your exact `audit_logs` table schema:
- `event_type`: `SAR_GENERATION_STARTED`, `SAR_REPORT_GENERATED`, `SAR_REPORT_SUBMITTED`
- `case_id`: Case identifier (indexed)
- `sar_report_content`: Generated narrative text
- `sar_report_metadata`: Generation metadata (LLM tokens, etc.)
- `sar_filing_number`: Filing number (if submitted)
- `environment_data`: Complete environment snapshot (JSONB)

## Querying Audit Trail

After Omega finalization, query the audit trail:

```python
from backend.query_audit_trail import query_sar_trail

# Get all SAR events for a case
audit_logs = query_sar_trail("sar-123")

# Or query by filing number
from backend.query_audit_trail import query_by_filing_number
log = query_by_filing_number("SAR-2024-0001")
```

## Placeholders for Future Integration

1. **RAG Pipeline** (`_generate_sar_narrative()`):
   - Replace placeholder with actual RAG retrieval service
   - Use `claim.regulatory_hooks` for context retrieval

2. **LLM Service** (`_generate_sar_narrative()`):
   - Replace placeholder with actual LLM API call
   - Capture token usage and model metadata

3. **Model Configuration**:
   - Currently uses placeholder model names
   - Replace with actual model versions from config

4. **Error Handling**:
   - Add retry logic for LLM calls
   - Add fallback narrative generation

## Notes

- All audit events use your exact `AuditLog` model schema
- Query patterns match your `query_audit_trail.py` implementation
- Claim object updates follow your `claim_schema.py` structure
- Environment data is captured exactly as provided in `omega_input`
