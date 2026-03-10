"""Validate breast cancer decision engine against sample cases."""

import json
import sys

# Run from project root so engines package is on path
sys.path.insert(0, ".")
from engines.breast.breast_engine import evaluate_breast_case


def run_case(name, **kwargs):
    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"{'='*70}")
    result = evaluate_breast_case(**kwargs)
    d = result.to_dict()
    print(json.dumps(d, indent=2))
    print()
    return d


# ── SAMPLE CASE 1: Early-Stage HR-Positive ──
run_case(
    "CASE 1: Early-Stage HR-Positive (42F, T1cN0M0, ER+/PR+/HER2-)",
    age=42,
    sex="female",
    ecog=0,
    menopausal_status="premenopausal",
    laterality="left",
    histology="invasive ductal carcinoma",
    tumor_size_cm=1.8,
    grade=2,
    lvi=False,
    n_stage="N0",
    nodes_examined=2,
    nodes_positive=0,
    m_stage="M0",
    er_status="positive",
    pr_status="positive",
    her2_status="negative",
    t_stage="T1c",
    overall_stage="IA",
    surgery_done=True,
    surgery_type="BCS",
    margin_status="negative",
    axillary_procedure="SLNB",
    quadrant="upper outer",
    ki67_percent=12,
)

# ── SAMPLE CASE 2: Node-Positive HER2-Positive ──
run_case(
    "CASE 2: Node-Positive HER2-Positive (55F, T2N1M0, ER-/PR-/HER2+)",
    age=55,
    sex="female",
    ecog=1,
    menopausal_status="postmenopausal",
    laterality="right",
    histology="invasive ductal carcinoma",
    tumor_size_cm=2.5,
    grade=3,
    lvi=True,
    n_stage="N1",
    nodes_examined=15,
    nodes_positive=2,
    m_stage="M0",
    er_status="negative",
    pr_status="negative",
    her2_status="positive",
    t_stage="T2",
    overall_stage="IIA",
    surgery_done=False,
)

# Add more run_case() calls as needed for other sample cases.
