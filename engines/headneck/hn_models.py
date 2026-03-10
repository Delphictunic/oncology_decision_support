"""
Pydantic models — Head & Neck SCC Decision Engine
AJCC 8th Edition
"""

from enum import Enum
from pydantic import BaseModel, Field, validator
from typing import List, Optional


class PrimarySite(str, Enum):
    ORAL_CAVITY = "oral_cavity"
    OROPHARYNX  = "oropharynx"
    HYPOPHARYNX = "hypopharynx"
    LARYNX      = "larynx"


class OralSubsite(str, Enum):
    ORAL_TONGUE         = "oral_tongue"
    BUCCAL_MUCOSA       = "buccal_mucosa"
    FLOOR_OF_MOUTH      = "floor_of_mouth"
    RETROMOLAR_TRIGONE  = "retromolar_trigone"
    ALVEOLUS_MANDIBULAR = "alveolus_mandibular"
    ALVEOLUS_MAXILLARY  = "alveolus_maxillary"
    HARD_PALATE         = "hard_palate"
    LIP                 = "lip"


class AJCCStage(str, Enum):
    I   = "I"
    II  = "II"
    III = "III"
    IVA = "IVA"
    IVB = "IVB"
    IVC = "IVC"


class TStage(str, Enum):
    T1  = "T1"
    T2  = "T2"
    T3  = "T3"
    T4a = "T4a"
    T4b = "T4b"


class NStage(str, Enum):
    N0  = "N0"
    N1  = "N1"
    N2a = "N2a"
    N2b = "N2b"
    N2c = "N2c"
    N3  = "N3"


class Confidence(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED   = "red"


class HNInput(BaseModel):
    # ── Core ──────────────────────────────────────────────────────────────
    age:  int   = Field(..., ge=10, le=100)
    ecog: int   = Field(..., ge=0,  le=4)

    # ── Disease characterisation ──────────────────────────────────────────
    primary_site:       PrimarySite
    ajcc_stage:         AJCCStage
    t_stage:            TStage
    n_stage:            NStage
    distant_metastasis: bool

    # ── Oral cavity specifics (required when primary_site = oral_cavity) ──
    oral_subsite: Optional[OralSubsite] = None
    doi_mm:       Optional[float]       = None   # depth of invasion in mm
    bone_invasion: bool = False                  # mandible / maxilla involvement
    bilateral_nodes: bool = False                # bilateral cervical nodes

    # ── Surgical status ───────────────────────────────────────────────────
    resectable:    bool
    prior_surgery: bool = False
    prior_rt:      bool = False

    # ── Pathological risk factors (post-surgery) ──────────────────────────
    margins_positive:       bool = False
    ece_present:            bool = False   # extracapsular / extranodal extension
    pni_present:            bool = False   # perineural invasion
    lvi_present:            bool = False   # lymphovascular invasion
    multiple_positive_nodes: bool = False

    # ── Oropharynx-specific ───────────────────────────────────────────────
    p16_positive: bool = False

    # ── Chemotherapy eligibility ──────────────────────────────────────────
    creatinine_clearance: float = Field(..., ge=0)
    hearing_adequate:     bool  = True

    # ── Special scenarios ─────────────────────────────────────────────────
    recurrent_disease:           bool = False
    post_rt_residual_nodes:      bool = False
    organ_preservation_preferred: bool = False
    symptomatic_bleeding_or_pain: bool = False

    @validator("creatinine_clearance")
    def crcl_reasonable(cls, v):
        if v > 200:
            raise ValueError("Creatinine clearance value unrealistic (>200)")
        return v

    @validator("doi_mm")
    def doi_reasonable(cls, v):
        if v is not None and v > 50:
            raise ValueError("DOI value unrealistic (>50 mm)")
        return v


class HNResult(BaseModel):
    formatted_output:  str
    confidence:        Confidence
    flags:             List[str]
    mdt_required:      bool
    protocol_reference: str
