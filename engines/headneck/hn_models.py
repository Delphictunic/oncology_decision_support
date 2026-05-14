"""
Pydantic Models — Head & Neck SCC Decision Engine
AJCC 8th Edition | Institutional HNSCC Protocol v1.0
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS — All fixed-choice fields for HN SCC
# ─────────────────────────────────────────────────────────────────────────────

class PrimarySite(str, Enum):
    """Head & Neck SCC primary tumor sites."""
    ORAL_CAVITY = "oral_cavity"
    OROPHARYNX = "oropharynx"
    HYPOPHARYNX = "hypopharynx"
    LARYNX = "larynx"


class OralSubsite(str, Enum):
    """Specific subsites within oral cavity."""
    ORAL_TONGUE = "oral_tongue"
    BUCCAL_MUCOSA = "buccal_mucosa"
    FLOOR_OF_MOUTH = "floor_of_mouth"
    RETROMOLAR_TRIGONE = "retromolar_trigone"
    ALVEOLUS_MANDIBULAR = "alveolus_mandibular"
    ALVEOLUS_MAXILLARY = "alveolus_maxillary"
    HARD_PALATE = "hard_palate"
    LIP = "lip"


class AJCCStage(str, Enum):
    """AJCC 8th edition overall staging."""
    I = "I"
    II = "II"
    III = "III"
    IVA = "IVA"
    IVB = "IVB"
    IVC = "IVC"


class TStage(str, Enum):
    """TNM T stage classification."""
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4a = "T4a"
    T4b = "T4b"


class NStage(str, Enum):
    """TNM N stage classification."""
    N0 = "N0"
    N1 = "N1"
    N2a = "N2a"
    N2b = "N2b"
    N2c = "N2c"
    N3 = "N3"


class Confidence(str, Enum):
    """Decision confidence level."""
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


# ─────────────────────────────────────────────────────────────────────────────
# HN INPUT MODEL
# ─────────────────────────────────────────────────────────────────────────────

class HNInput(BaseModel):
    """Clinical input for head & neck SCC decision support."""
    
    # ── Required patient data ──
    age: int = Field(
        ...,
        ge=10,
        le=100,
        description="age (numeric, years)"
    )
    ecog: int = Field(
        ...,
        ge=0,
        le=4,
        description="ecog (0|1|2|3|4)"
    )
    
    # ── Required disease characterization ──
    primary_site: PrimarySite = Field(
        ...,
        description="primary_site (oral_cavity | oropharynx | hypopharynx | larynx)"
    )
    ajcc_stage: AJCCStage = Field(
        ...,
        description="ajcc_stage — AJCC 8th edition (I|II|III|IVA|IVB|IVC)"
    )
    t_stage: TStage = Field(
        ...,
        description="t_stage (T1|T2|T3|T4a|T4b)"
    )
    n_stage: NStage = Field(
        ...,
        description="n_stage (N0|N1|N2a|N2b|N2c|N3)"
    )
    distant_metastasis: bool = Field(
        ...,
        description="distant_metastasis (true | false)"
    )
    
    # ── Oral cavity specifics (required when primary_site = oral_cavity) ──
    oral_subsite: Optional[OralSubsite] = Field(
        default=None,
        description="oral_subsite — required if primary_site is oral_cavity (oral_tongue | buccal_mucosa | floor_of_mouth | retromolar_trigone | alveolus_mandibular | alveolus_maxillary | hard_palate | lip)"
    )
    doi_mm: Optional[float] = Field(
        default=None,
        ge=0,
        le=50,
        description="doi_mm — depth of invasion in mm; required if primary_site is oral_cavity (numeric, 0–50 mm)"
    )
    bone_invasion: bool = Field(
        default=False,
        description="bone_invasion — mandibular or maxillary bone involvement (true | false)"
    )
    bilateral_nodes: bool = Field(
        default=False,
        description="bilateral_nodes — bilateral cervical lymph node involvement (true | false)"
    )
    
    # ── Required surgical status ──
    resectable: bool = Field(
        ...,
        description="resectable — tumor amenable to surgical resection (true | false)"
    )
    
    # ── Optional surgical history ──
    prior_surgery: bool = Field(
        default=False,
        description="prior_surgery (true | false)"
    )
    prior_rt: bool = Field(
        default=False,
        description="prior_rt — prior radiotherapy (true | false)"
    )
    
    # ── Optional pathological risk factors (post-surgery) ──
    margins_positive: bool = Field(
        default=False,
        description="margins_positive — positive surgical margins (true | false)"
    )
    ece_present: bool = Field(
        default=False,
        description="ece_present — extracapsular/extranodal extension (true | false)"
    )
    pni_present: bool = Field(
        default=False,
        description="pni_present — perineural invasion (true | false)"
    )
    lvi_present: bool = Field(
        default=False,
        description="lvi_present — lymphovascular invasion (true | false)"
    )
    multiple_positive_nodes: bool = Field(
        default=False,
        description="multiple_positive_nodes (true | false)"
    )
    
    # ── Oropharynx-specific ──
    p16_positive: bool = Field(
        default=False,
        description="p16_positive — p16/HPV status in oropharyngeal cancer (true | false)"
    )
    
    # ── Required chemotherapy eligibility ──
    creatinine_clearance: float = Field(
        ...,
        ge=0,
        le=200,
        description="creatinine_clearance (numeric, mL/min)"
    )
    hearing_adequate: bool = Field(
        default=True,
        description="hearing_adequate — adequate hearing for cisplatin toxicity monitoring (true | false)"
    )
    
    # ── Optional special scenarios ──
    recurrent_disease: bool = Field(
        default=False,
        description="recurrent_disease — recurrent or second primary (true | false)"
    )
    post_rt_residual_nodes: bool = Field(
        default=False,
        description="post_rt_residual_nodes — residual nodes after prior radiotherapy (true | false)"
    )
    organ_preservation_preferred: bool = Field(
        default=False,
        description="organ_preservation_preferred — patient preference for organ-preserving approach (true | false)"
    )
    symptomatic_bleeding_or_pain: bool = Field(
        default=False,
        description="symptomatic_bleeding_or_pain — active symptomatic disease (true | false)"
    )
    
    # ── Validators ──
    
    @field_validator("doi_mm", mode="after")
    @classmethod
    def doi_reasonable(cls, v: Optional[float]) -> Optional[float]:
        """Validate DOI is clinically reasonable."""
        if v is not None and v > 50:
            raise ValueError("DOI (depth of invasion) > 50 mm is unrealistic")
        return v
    
    @model_validator(mode="after")
    def check_oral_cavity_requirements(self) -> "HNInput":
        """
        Cross-field validation:
        If primary_site is oral_cavity, then oral_subsite and doi_mm are required.
        """
        if self.primary_site == PrimarySite.ORAL_CAVITY:
            if self.oral_subsite is None:
                raise ValueError("oral_subsite is required when primary_site is oral_cavity")
            if self.doi_mm is None:
                raise ValueError("doi_mm (depth of invasion) is required when primary_site is oral_cavity")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# HN RESULT MODEL
# ─────────────────────────────────────────────────────────────────────────────

class HNResult(BaseModel):
    """Structured output from HN SCC decision engine."""
    
    formatted_output: str = Field(
        ...,
        description="Final formatted recommendation"
    )
    confidence: Confidence = Field(
        ...,
        description="Decision confidence level (green | amber | red)"
    )
    flags: List[str] = Field(
        default_factory=list,
        description="List of clinical flags, warnings, or MDT notes"
    )
    mdt_required: bool = Field(
        default=False,
        description="Whether MDT discussion is required"
    )
    protocol_reference: str = Field(
        default="Institutional HNSCC Protocol v1.0",
        description="Protocol version reference"
    )