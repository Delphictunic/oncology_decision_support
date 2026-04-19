"""
Pydantic Models — Bladder Cancer Decision Engine
Institutional GU Cancers Protocol v1.0
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class BladderTStage(str, Enum):
    TA  = "Ta"
    TIS = "Tis"
    T1  = "T1"
    T2  = "T2"
    T2A = "T2a"
    T2B = "T2b"
    T3  = "T3"
    T3A = "T3a"
    T3B = "T3b"
    T4  = "T4"
    T4A = "T4a"
    T4B = "T4b"


class BladderNStage(str, Enum):
    NX = "Nx"
    N0 = "N0"
    N1 = "N1"
    N2 = "N2"
    N3 = "N3"


class BladderMStage(str, Enum):
    M0  = "M0"
    M1A = "M1a"
    M1B = "M1b"


class TumorGrade(str, Enum):
    LOW  = "low"
    HIGH = "high"


class BladderHistology(str, Enum):
    UROTHELIAL    = "urothelial"
    SCC           = "scc"
    ADENOCARCINOMA = "adenocarcinoma"
    OTHER         = "other"


class BCGStatus(str, Enum):
    NAIVE        = "naive"
    RESPONSIVE   = "responsive"
    UNRESPONSIVE = "unresponsive"


class Confidence(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED   = "red"


class BladderInput(BaseModel):
    # ── Core ──────────────────────────────────────────────────────────────
    age:  int  = Field(..., ge=18, le=100)
    ecog: int  = Field(..., ge=0, le=4)

    # ── Tumour characterisation ───────────────────────────────────────────
    t_stage:   BladderTStage
    n_stage:   BladderNStage
    m_stage:   BladderMStage
    grade:     TumorGrade
    histology: BladderHistology

    # ── Surgical status ───────────────────────────────────────────────────
    turbt_done:             bool
    willing_for_surgery:    bool = True   # Cystectomy willingness (protocol mandates obtaining this)

    # ── Renal function (chemotherapy eligibility) ─────────────────────────
    creatinine_clearance: float = Field(..., ge=0)

    # ── NMIBC-specific ────────────────────────────────────────────────────
    cis_present:          bool      = False
    bcg_status:           BCGStatus = BCGStatus.NAIVE
    prior_bcg_courses:    int       = 0   # number of prior BCG induction courses

    # ── Treatment preferences ─────────────────────────────────────────────
    bladder_preservation_preferred: bool = False

    # ── Symptomatic ───────────────────────────────────────────────────────
    haematuria_active: bool = False

    @validator("creatinine_clearance")
    def crcl_reasonable(cls, v):
        if v > 200:
            raise ValueError("CrCl > 200 – unrealistic value")
        return v


class BladderResult(BaseModel):
    formatted_output:  str
    confidence:        Confidence
    flags:             List[str]
    mdt_required:      bool
    protocol_reference: str
