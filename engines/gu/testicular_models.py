"""
Pydantic Models — Testicular Cancer Decision Engine
Institutional GU Cancers Protocol v1.0
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class TesticularHistology(str, Enum):
    SEMINOMA = "seminoma"
    NSGCT    = "nsgct"     # Non-seminomatous germ cell tumour
    MIXED    = "mixed"     # Mixed GCT (treat as NSGCT)


class TesticularTStage(str, Enum):
    PTIS = "pTis"
    PT1  = "pT1"
    PT1A = "pT1a"
    PT1B = "pT1b"
    PT2  = "pT2"
    PT3  = "pT3"
    PT4  = "pT4"


class TesticularNStage(str, Enum):
    N0 = "N0"
    N1 = "N1"
    N2 = "N2"
    N3 = "N3"


class TesticularMStage(str, Enum):
    M0  = "M0"
    M1A = "M1a"
    M1B = "M1b"


class SStage(str, Enum):
    SX = "SX"
    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"


class TesticularOverallStage(str, Enum):
    ZERO = "0"
    I    = "I"
    IA   = "IA"
    IB   = "IB"
    IS   = "IS"
    IIA  = "IIA"
    IIB  = "IIB"
    IIC  = "IIC"
    IIIA = "IIIA"
    IIIB = "IIIB"
    IIIC = "IIIC"


class IGCCCGRisk(str, Enum):
    GOOD         = "good"
    INTERMEDIATE = "intermediate"
    POOR         = "poor"


class Confidence(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED   = "red"


class TesticularInput(BaseModel):
    # ── Core ──────────────────────────────────────────────────────────────
    age:  int  = Field(..., ge=1, le=80)
    ecog: int  = Field(..., ge=0, le=4)

    # ── Tumour characterisation ───────────────────────────────────────────
    histology:     TesticularHistology
    t_stage:       TesticularTStage
    n_stage:       TesticularNStage
    m_stage:       TesticularMStage
    s_stage:       SStage
    overall_stage: TesticularOverallStage

    # ── Surgical status ───────────────────────────────────────────────────
    orchiectomy_done: bool = False   # radical orchiectomy via inguinal approach

    # ── Histological risk factors ─────────────────────────────────────────
    lvi:              bool = False   # lymphovascular invasion
    rete_testis_invasion: bool = False

    # ── Marker status post-orchiectomy ────────────────────────────────────
    marker_normalised:         bool           = True
    marker_elevation_persistent: bool         = False   # Stage IS equivalent

    # ── Post-chemotherapy residual assessment ─────────────────────────────
    post_chemo_residual:   bool           = False
    residual_mass_cm:      Optional[float] = None    # max residual mass diameter in cm

    # ── IGCCCG risk (if known; computed from s_stage + histology if not provided) ──
    igcccg_risk: Optional[IGCCCGRisk] = None

    # ── Metastatic characterisation ───────────────────────────────────────
    non_pulmonary_visceral_mets: bool = False   # liver, bone, brain (worse prognosis)
    mediastinal_primary:         bool = False   # NSGCT mediastinal primary → poor risk

    @validator("residual_mass_cm")
    def residual_reasonable(cls, v):
        if v is not None and v > 30:
            raise ValueError("Residual mass > 30 cm – unrealistic")
        return v


class TesticularResult(BaseModel):
    formatted_output:  str
    confidence:        Confidence
    flags:             List[str]
    mdt_required:      bool
    protocol_reference: str
