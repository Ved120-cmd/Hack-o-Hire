"""
Claim Generation Services Package

Contains:
- ClaimPopulationService: Maps upstream data to claim fields
- (Optionally) ClaimStorage: PostgreSQL persistence with audit trail

For lightweight usage (e.g., generating demo claims), only
ClaimPopulationService is imported to avoid requiring SQLAlchemy.
"""

from claim_gen.services.claim_population import ClaimPopulationService

__all__ = ["ClaimPopulationService"]