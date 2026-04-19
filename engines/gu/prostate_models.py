"""
Pydantic Models — Prostate Cancer Decision Engine
Institutional GU Cancers Protocol v1.0 | AJCC 8th Edition
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ProstateTStage(str, Enum):
    T1A = "T1a"
    T1B = "T1b"
    T1C = "T1c"
    T2A = "T2a"
    T2B = "T2b"
    T2C = "T2c"
    T3A = "T3a"
    T3B = "T3b"
    T4  = "T4"


class ProstateNStage(str, Enum):
    N0 = "N0"
    N1 = "N1"


class ProstateMStage(str, Enum):
    M0  = "M0"
    M1A = "M1a"
    M1B = "M1b"
    M1C = "M1c"


class ProstateOverallStage(str, Enum):
    I    = "I"
    IIA  = "IIA"
    IIB  = "IIB"
    IIC  = "IIC"
    IIIA = "IIIA"
    IIIB = "IIIB"
    IIIC = "IIIC"
    IVA  = "IVA"
    IVB  = "IVB"


class Confidence(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED   = "red"


class ProstateInput(BaseModel):
    # ── Core ──────────────────────────────────────────────────────────────
    age:  int   = Field(..., ge=18, le=100)
    ecog: int   = Field(..., ge=0, le=4)

    # ── Disease characterisation ──────────────────────────────────────────
    psa:           float              = Field(..., ge=0, description="PSA in ng/mL")
    t_stage:       ProstateTStage
    n_stage:       ProstateNStage
    m_stage:       ProstateMStage
    grade_group:   int                = Field(..., ge=1, le=5, description="ISUP Grade Group 1–5")
    overall_stage: ProstateOverallStage

    # ── Renal function ────────────────────────────────────────────────────
    creatinine_clearance: float = Field(..., ge=0)

    # ── Surgical history ──────────────────────────────────────────────────
    prior_rp:               bool           = False
    post_rp_psa:            Optional[float] = None   # PSA post-RP in ng/mL; 0 = undetectable

    # ── Pathological risk factors (post-RP) ───────────────────────────────
    margin_positive:          bool = False
    seminal_vesicle_invasion: bool = False  # pT3b
    ece_present:              bool = False  # extracapsular extension, pT3a
    ln_positive_post_rp:      bool = False  # pN1 at RP

    # ── ADT / CRPC assessment ─────────────────────────────────────────────
    on_adt:                  bool           = False
    psa_rising_on_adt:       bool           = False
    castrate_testosterone:   Optional[float] = None  # ng/dL; <50 = castrate
    psadt_months:            Optional[float] = None  # PSA doubling time (months)

    # ── Metastatic characterisation ───────────────────────────────────────
    bone_only_mets:       bool = False
    visceral_mets:        bool = False
    symptomatic_bone_mets: bool = False
    low_volume_mets:      bool = False  # ≤4 bone lesions (for RT to prostate, STAMPEDE)

    # ── Molecular / targeted therapy eligibility ─────────────────────────
    psma_positive:  bool = False
    brca_mutation:  bool = False
    msi_high:       bool = False

    # ── Prior systemic therapy (mCRPC sequencing) ─────────────────────────
    prior_arpi:      bool = False   # prior abiraterone or enzalutamide
    prior_docetaxel: bool = False

    @validator("creatinine_clearance")
    def crcl_reasonable(cls, v):
        if v > 200:
            raise ValueError("CrCl > 200 – unrealistic value")
        return v

    @validator("psa")
    def psa_reasonable(cls, v):
        if v > 10000:
            raise ValueError("PSA > 10,000 ng/mL – unrealistic value")
        return v


class ProstateResult(BaseModel):
    formatted_output:  str
    confidence:        Confidence
    flags:             List[str]
    mdt_required:      bool
    protocol_reference: str
