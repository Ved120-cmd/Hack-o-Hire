"""
Omega Finalization Stage Package

This package contains the Omega finalization stage for SAR report generation.

Omega responsibilities:
1. Take claim + narrative (from Theta/RAG stage)
2. Run 10-point regulatory validation
3. Store final bundle to sar_final_filings table
4. Return regulatory_ready status
"""

from backend.omega.omega_finalization import (
    OmegaFinalizer,
    OmegaFinalizationError,
    RegulatoryValidationError,
    run_omega,
)

__all__ = [
    "OmegaFinalizer",
    "OmegaFinalizationError",
    "RegulatoryValidationError",
    "run_omega",
]
