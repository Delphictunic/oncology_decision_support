"""
Genitourinary Cancer Clinical Decision Support Engines
Prostate | Bladder | Testicular
Institutional GU Cancers Protocol v1.0
"""

from .prostate_engine import evaluate_prostate_case
from .prostate_models import ProstateInput, ProstateResult
from .bladder_engine import evaluate_bladder_case
from .bladder_models import BladderInput, BladderResult
from .testicular_engine import evaluate_testicular_case
from .testicular_models import TesticularInput, TesticularResult

__all__ = [
    "evaluate_prostate_case", "ProstateInput", "ProstateResult",
    "evaluate_bladder_case", "BladderInput", "BladderResult",
    "evaluate_testicular_case", "TesticularInput", "TesticularResult",
]
