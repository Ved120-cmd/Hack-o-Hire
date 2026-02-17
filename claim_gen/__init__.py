"""
SAR Claim Generator - Delta Stage Package
========================================

This package generates complete, auditable claim objects from upstream pipeline data.
The claim object is the structured input to RAG + LLM for SAR narrative generation.

Main Components:
    - ClaimGenerator: Main orchestration class
    - generate_claim(): Convenience function
    - ClaimPopulationService: Field mapping logic
    - ClaimStorage: Database persistence
    
Pipeline Position:
    Ingestion & Normalization → KYC Enrichment → Rules-Based Engine
    → Claim Generation (this package) → Narrative Generation (RAG + LLM)
    
Usage:
    from backend.claim_gen import generate_claim
    
    claim_object = generate_claim(
        case_id=case_id,
        alert_ids=alert_ids,
        customer_data=customer_data,  # From Beta
        pipeline_transforms=transforms,  # From Alpha→Gamma
        rule_results=rule_results,  # From Gamma
        fraud_scores=fraud_scores,  # From ML models
        rag_results=rag_results  # From RAG
    )
    
    # claim_object is ready for Omega stage (RAG + LLM narrative generation)
"""

__version__ = "1.0.0"
__stage__ = "claim_generation"

# Local imports so the package works from project root
from claim_gen.claim_gen import ClaimGenerator, generate_claim

__all__ = ["ClaimGenerator", "generate_claim"]