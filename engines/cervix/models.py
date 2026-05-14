"""
Pydantic Models — Cervix Cancer Decision Engine
Institutional Cervix Cancer Protocol v1.0 (FIGO 2018)
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS — All fixed-choice fields for cervix cancer
# ─────────────────────────────────────────────────────────────────────────────

class FIGOStage(str, Enum):
    """FIGO 2018 cervical cancer staging."""
    IA1 = "IA1"
    IA2 = "IA2"
    IB1 = "IB1"
    IB2 = "IB2"
    IB3 = "IB3"
    IIA = "IIA"
    IIB = "IIB"
    IIIA = "IIIA"
    IIIB = "IIIB"
    IIIC = "IIIC"
    IVA = "IVA"
    IVB = "IVB"


class Histology(str, Enum):
    """Cervical cancer histological types."""
    SCC = "scc"
    ADENO = "adenocarcinoma"
    ADENOSQUAMOUS = "adenosquamous"


class Confidence(str, Enum):
    """Decision confidence level."""
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


# ─────────────────────────────────────────────────────────────────────────────
# CERVIX INPUT MODEL
# ─────────────────────────────────────────────────────────────────────────────

class CervixInput(BaseModel):
    """Clinical input for cervix cancer decision support."""
    
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
    
    # ── Required staging ──
    figo_stage: FIGOStage = Field(
        ...,
        description="figo_stage — FIGO 2018 (IA1|IA2|IB1|IB2|IB3|IIA|IIB|IIIA|IIIB|IIIC|IVA|IVB)"
    )
    
    # ── Required tumor data ──
    histology: Histology = Field(
        ...,
        description="histology (scc | adenocarcinoma | adenosquamous)"
    )
    tumor_size_cm: float = Field(
        ...,
        ge=0,
        le=20,
        description="tumor_size_cm (numeric, cm; max 20 cm)"
    )
    
    # ── Required nodal status ──
    pelvic_nodes_positive: bool = Field(
        ...,
        description="pelvic_nodes_positive (true | false)"
    )
    para_aortic_nodes_positive: bool = Field(
        ...,
        description="para_aortic_nodes_positive (true | false)"
    )
    hydronephrosis: bool = Field(
        ...,
        description="hydronephrosis — presence of hydronephrosis (true | false)"
    )
    
    # ── Required renal function ──
    creatinine_clearance: float = Field(
        ...,
        ge=0,
        description="creatinine_clearance (numeric, mL/min)"
    )
    
    # ── Optional pathological factors ──
    prior_surgery: bool = Field(
        default=False,
        description="prior_surgery — prior hysterectomy or surgical intervention (true | false)"
    )
    margins_positive: bool = Field(
        default=False,
        description="margins_positive — positive surgical margins (true | false)"
    )
    lvsi_present: bool = Field(
        default=False,
        description="lvsi_present — lymphovascular space invasion (true | false)"
    )
    parametrial_invasion: bool = Field(
        default=False,
        description="parametrial_invasion (true | false)"
    )
    
    # ── Optional metastatic/clinical flags ──
    distant_metastasis: bool = Field(
        default=False,
        description="distant_metastasis (true | false)"
    )
    symptomatic_bleeding: bool = Field(
        default=False,
        description="symptomatic_bleeding — active symptomatic vaginal bleeding (true | false)"
    )
    post_crt_residual: bool = Field(
        default=False,
        description="post_crt_residual — residual disease after prior chemoradiation (true | false)"
    )
    
    # ── Validators ──
    
    @field_validator("tumor_size_cm", mode="after")
    @classmethod
    def tumor_reasonable(cls, v: float) -> float:
        """Validate tumor size is clinically reasonable."""
        if v > 20:
            raise ValueError("Tumor size > 20 cm is unrealistic for cervical cancer")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# CERVIX RESULT MODEL
# ─────────────────────────────────────────────────────────────────────────────

class CervixResult(BaseModel):
    """Structured output from cervix cancer decision engine."""
    
    formatted_output: str = Field(
        ...,
        description="Final formatted recommendation with 9-section structure"
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
        default="Institutional Cervix Cancer Protocol v1.0",
        description="Protocol version reference"
    )