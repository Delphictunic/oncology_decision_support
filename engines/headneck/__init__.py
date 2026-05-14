"""
Head & Neck SCC Clinical Decision Support Engine
Institutional Protocol v1.0 (AJCC 8th Edition)

Public API for external consumers (e.g., MCP server, UI integration).
"""

from .hn_engine import evaluate_hn_case
from .hn_models import HNInput, HNResult, Confidence


__all__ = [
    # Engine function
    "evaluate_hn_case",
    
    # Input/Output models
    "HNInput",
    "HNResult",
    
    # Confidence levels
    "Confidence",
]