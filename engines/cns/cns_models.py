"""
CNS TUMORS - Data Models
Pydantic models for input validation and structured outputs
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from .cns_config import (
    CNSTumourType, WHOGrade, GliomaSubtype, ResectionExtent, 
    Confidence, EpendymomaLocation
)


# ─────────────────────────────────────────────────────────────────────────────
# INPUT MODELS
# ─────────────────────────────────────────────────────────────────────────────

class CNSInput(BaseModel):
    """Main input model for CNS tumor cases."""
    
    # Required base fields
    tumour_type:        CNSTumourType
    who_grade:          WHOGrade
    age:                int = Field(..., ge=1, le=100, description="Patient age in years")
    ecog:               int = Field(..., ge=0, le=4, description="ECOG performance status")
    
    # Glioma-specific fields
    glioma_subtype:     Optional[GliomaSubtype] = None
    idh_mutant:         Optional[bool] = None
    codeletion_1p19q:   Optional[bool] = None
    mgmt_methylated:    Optional[bool] = None
    tert_mutant:        Optional[bool] = None
    
    # Treatment/tumor status
    resection_extent:   ResectionExtent = ResectionExtent.NONE
    gross_total_resection: bool = False
    residual_disease:   bool = False
    
    # Meningioma-specific
    meningioma_grade:   Optional[int] = None
    meningioma_complete_resection: bool = False
    
    # Ependymoma-specific
    ependymoma_location: Optional[EpendymomaLocation] = None
    spinal_complete_resection: bool = False
    
    # Medulloblastoma-specific
    medulloblastoma_risk: Optional[str] = None
    medulloblastoma_metastatic: bool = False
    
    # Pituitary-specific
    pituitary_functional: Optional[bool] = None
    
    # High-risk criteria (for stratification)
    tumour_size_cm:     Optional[float] = None
    crosses_midline:    bool = False
    neurological_deficit: bool = False
    
    class Config:
        use_enum_values = False


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT MODELS
# ─────────────────────────────────────────────────────────────────────────────

class CNSResult(BaseModel):
    """Structured output from decision engine."""
    
    formatted_output:   str = Field(..., description="Formatted text output matching template")
    confidence:         Confidence = Field(..., description="GREEN/AMBER/RED confidence level")
    flags:              List[str] = Field(default_factory=list, description="Clinical decision flags")
    mdt_required:       bool = Field(default=False, description="Whether MDT discussion required")
    protocol_reference: str = Field(..., description="Protocol version reference")
    
    class Config:
        use_enum_values = True


# ─────────────────────────────────────────────────────────────────────────────
# INTERMEDIATE MODELS (for structured processing)
# ─────────────────────────────────────────────────────────────────────────────

class RiskAssessment(BaseModel):
    """Risk stratification results."""
    is_high_risk: bool
    risk_criteria_met: List[str] = Field(default_factory=list)
    confidence: Confidence = Confidence.GREEN


class TreatmentRecommendation(BaseModel):
    """Structured treatment plan."""
    primary_treatment: str
    adjuvant_therapy: Optional[str] = None
    radiotherapy_details: Optional[str] = None
    chemotherapy_details: Optional[str] = None
    rationale: str
    followup_plan: str
    oar_constraints: Optional[List[str]] = None
