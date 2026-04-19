"""
Pydantic Models — GI Cancers Decision Engine
Institutional GI Cancers Protocol v1.0
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class GISite(str, Enum):
    ESOPHAGUS   = "esophagus"
    STOMACH     = "stomach"
    RECTUM      = "rectum"
    ANAL_CANAL  = "anal_canal"
    PANCREAS    = "pancreas"
    COLON       = "colon"


class GIHistology(str, Enum):
    SCC             = "scc"
    ADENOCARCINOMA  = "adenocarcinoma"
    OTHER           = "other"


class EsophagusTStage(str, Enum):
    T1A = "T1a"; T1B = "T1b"; T1 = "T1"
    T2 = "T2"; T3 = "T3"
    T4A = "T4a"; T4B = "T4b"

class EsophagusNStage(str, Enum):
    N0 = "N0"; N1 = "N1"; N2 = "N2"; N3 = "N3"

class GIMStage(str, Enum):
    M0 = "M0"; M1 = "M1"; M1A = "M1a"; M1B = "M1b"; M1C = "M1c"

class EsophagusLocation(str, Enum):
    UPPER_CERVICAL  = "upper_cervical"
    MID_THORACIC    = "mid_thoracic"
    LOWER           = "lower"
    GEJ             = "gej"             # gastro-oesophageal junction


# ── Rectum ───────────────────────────────────────────────────────────────
class RectalTStage(str, Enum):
    T1="T1"; T2="T2"; T3="T3"; T4A="T4a"; T4B="T4b"

class RectalNStage(str, Enum):
    N0="N0"; N1="N1"; N1A="N1a"; N1B="N1b"; N1C="N1c"
    N2="N2"; N2A="N2a"; N2B="N2b"


# ── Anal Canal ───────────────────────────────────────────────────────────
class AnalTStage(str, Enum):
    T1="T1"; T2="T2"; T3="T3"; T4="T4"

class AnalNStage(str, Enum):
    N0="N0"; N1="N1"; N1A="N1a"; N1B="N1b"; N1C="N1c"


# ── Pancreas ─────────────────────────────────────────────────────────────
class PancreasResectability(str, Enum):
    RESECTABLE           = "resectable"
    BORDERLINE_RESECTABLE = "borderline_resectable"
    LOCALLY_ADVANCED     = "locally_advanced"
    METASTATIC           = "metastatic"


# ── Confidence ──────────────────────────────────────────────────────────
class Confidence(str, Enum):
    GREEN = "green"; AMBER = "amber"; RED = "red"


# ─────────────────────────────────────────────────────────────────────────
# Master input model — site-specific fields are Optional
# ─────────────────────────────────────────────────────────────────────────
class GIInput(BaseModel):
    # ── Core (always required)
    primary_site: GISite
    age:          int   = Field(..., ge=18, le=100)
    ecog:         int   = Field(..., ge=0, le=4)
    histology:    GIHistology

    # ── Esophagus-specific
    esophagus_t_stage:   Optional[str]                = None
    esophagus_n_stage:   Optional[str]                = None
    esophagus_m_stage:   Optional[str]                = None
    esophagus_location:  Optional[str]                = None  # EsophagusLocation
    esophagus_overall_stage: Optional[str]            = None

    # ── Stomach-specific
    stomach_t_stage:     Optional[str]                = None
    stomach_n_stage:     Optional[str]                = None
    stomach_m_stage:     Optional[str]                = None
    stomach_overall_stage: Optional[str]              = None
    her2_positive:       bool                         = False
    prior_surgery_stomach: bool                       = False

    # ── Rectum-specific
    rectum_t_stage:      Optional[str]                = None
    rectum_n_stage:      Optional[str]                = None
    rectum_m_stage:      Optional[str]                = None
    crm_threatened:      bool                         = False  # circumferential resection margin
    emvi_positive:       bool                         = False  # extramural vascular invasion
    rectum_location:     Optional[str]                = None   # upper / mid / lower
    prior_surgery_rectum: bool                        = False

    # ── Anal canal-specific
    anal_t_stage:        Optional[str]                = None
    anal_n_stage:        Optional[str]                = None
    anal_m_stage:        Optional[str]                = None
    hiv_positive:        bool                         = False

    # ── Pancreas-specific
    pancreas_resectability:  Optional[str]            = None  # PancreasResectability
    pancreas_t_stage:        Optional[str]            = None
    pancreas_n_stage:        Optional[str]            = None
    pancreas_m_stage:        Optional[str]            = None
    brca_mutation:           bool                     = False
    prior_surgery_pancreas:  bool                     = False
    pancreas_margin_status:  Optional[str]            = None  # R0/R1/R2

    # ── Colon-specific
    colon_t_stage:       Optional[str]                = None
    colon_n_stage:       Optional[str]                = None
    colon_m_stage:       Optional[str]                = None
    colon_overall_stage: Optional[str]                = None
    high_risk_features:  bool                         = False  # T4, <12 LN, LVSI, obstruction
    microsatellite_instability: Optional[str]         = None   # MSI-H / MSS / unknown
    kras_status:         Optional[str]                = None   # mutant / wild-type / unknown

    @validator("age")
    def age_reasonable(cls, v):
        if v > 100: raise ValueError("Age > 100 unrealistic")
        return v


class GIResult(BaseModel):
    formatted_output:   str
    confidence:         Confidence
    flags:              List[str]
    mdt_required:       bool
    protocol_reference: str
