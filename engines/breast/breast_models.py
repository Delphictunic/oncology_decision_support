"""
Pydantic Models — Breast Cancer Decision Engine
Institutional Breast Cancer Protocol v1.0 (aligned with NCCN/ESMO)
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS — All fixed-choice fields for breast cancer inputs
# ─────────────────────────────────────────────────────────────────────────────

class Sex(str, Enum):
    FEMALE = "female"
    MALE = "male"


class Histology(str, Enum):
    IDC = "invasive ductal carcinoma"
    ILC = "invasive lobular carcinoma"
    DCIS = "DCIS"
    OTHER = "other"


class Laterality(str, Enum):
    LEFT = "left"
    RIGHT = "right"


class SurgeryType(str, Enum):
    BCS = "BCS"
    MRM = "MRM"
    MASTECTOMY = "mastectomy"
    NONE = "none"


class AxillaryProcedure(str, Enum):
    SLNB = "SLNB"
    ALND = "ALND"
    NONE = "none"


class MarginStatus(str, Enum):
    NEGATIVE = "negative"
    CLOSE = "close"
    POSITIVE = "positive"
    UNKNOWN = "unknown"


class ERStatus(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class PRStatus(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class HER2Status(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class MenopausalStatus(str, Enum):
    PREMENOPAUSAL = "premenopausal"
    PERIMENOPAUSAL = "perimenopausal"
    POSTMENOPAUSAL = "postmenopausal"


class ChemoResponse(str, Enum):
    PCR = "pCR"
    PARTIAL = "partial"
    RESIDUAL = "residual"
    NOT_APPLICABLE = "not applicable"


class Confidence(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class Quadrant(str, Enum):
    UPPER_OUTER = "upper outer"
    UPPER_INNER = "upper inner"
    LOWER_OUTER = "lower outer"
    LOWER_INNER = "lower inner"
    CENTRAL = "central"
    MULTIFOCAL = "multifocal"
    MULTICENTRIC = "multicentric"


# ─────────────────────────────────────────────────────────────────────────────
# BREAST INPUT MODEL
# ─────────────────────────────────────────────────────────────────────────────

class BreastInput(BaseModel):
    """Clinical input for breast cancer decision support. Required and optional fields."""
    
    # ── Required patient data ──
    age: int = Field(
        ...,
        ge=18,
        le=100,
        description="age (numeric, years)"
    )
    sex: Sex = Field(
        ...,
        description="sex (female | male)"
    )
    ecog: int = Field(
        ...,
        ge=0,
        le=4,
        description="ecog (0|1|2|3|4)"
    )
    menopausal_status: MenopausalStatus = Field(
        ...,
        description="menopausal_status (premenopausal | perimenopausal | postmenopausal)"
    )
    
    # ── Required tumor data ──
    laterality: Laterality = Field(
        ...,
        description="laterality (left | right)"
    )
    histology: Histology = Field(
        ...,
        description="histology (invasive ductal carcinoma | invasive lobular carcinoma | DCIS | other)"
    )
    tumor_size_cm: float = Field(
        ...,
        ge=0,
        description="tumor_size_cm (numeric, cm)"
    )
    grade: int = Field(
        ...,
        ge=1,
        le=3,
        description="grade (1|2|3 — Nottingham grade)"
    )
    lvi: bool = Field(
        ...,
        description="lvi — lymphovascular invasion (true | false)"
    )
    
    # ── Required nodal / metastatic ──
    n_stage: str = Field(
        ...,
        description="n_stage (N0|N1|N2|N3|pN0|pN1 etc.)"
    )
    nodes_examined: int = Field(
        ...,
        ge=0,
        description="nodes_examined (numeric)"
    )
    nodes_positive: int = Field(
        ...,
        ge=0,
        description="nodes_positive (numeric)"
    )
    m_stage: str = Field(
        ...,
        description="m_stage (M0 | M1)"
    )
    
    # ── Required biomarkers ──
    er_status: ERStatus = Field(
        ...,
        description="er_status (positive | negative)"
    )
    pr_status: PRStatus = Field(
        ...,
        description="pr_status (positive | negative)"
    )
    her2_status: HER2Status = Field(
        ...,
        description="her2_status (positive | negative)"
    )
    
    # ── Required staging ──
    t_stage: str = Field(
        ...,
        description="t_stage (T1|T1a|T1b|T1c|T2|T3|T4 etc.)"
    )
    overall_stage: str = Field(
        ...,
        description="overall_stage (IA|IB|IIA|IIB|IIIA|IIIB|IIIC|IV)"
    )
    
    # ── Surgery (base) ──
    surgery_done: bool = Field(
        ...,
        description="surgery_done (true | false)"
    )
    
    # ── Surgery (conditional — required only if surgery_done=True) ──
    surgery_type: Optional[SurgeryType] = Field(
        default=None,
        description="surgery_type (BCS | MRM | mastectomy | none)"
    )
    margin_status: Optional[MarginStatus] = Field(
        default=None,
        description="margin_status (negative | close | positive | unknown)"
    )
    
    # ── Optional fields ──
    axillary_procedure: AxillaryProcedure = Field(
        default=AxillaryProcedure.NONE,
        description="axillary_procedure (SLNB | ALND | none)"
    )
    quadrant: Quadrant = Field(
        default=Quadrant.UPPER_OUTER,
        description="quadrant (upper outer | upper inner | lower outer | lower inner | central | multifocal | multicentric)"
    )
    ki67_percent: Optional[float] = Field(
        default=None,
        description="ki67_percent (numeric, 0-100)"
    )
    neoadjuvant_chemo: bool = Field(
        default=False,
        description="neoadjuvant_chemo (true | false)"
    )
    chemo_response: ChemoResponse = Field(
        default=ChemoResponse.NOT_APPLICABLE,
        description="chemo_response (pCR | partial | residual | not applicable)"
    )
    extracapsular_extension: bool = Field(
        default=False,
        description="extracapsular_extension (true | false)"
    )
    imn_involvement: bool = Field(
        default=False,
        description="imn_involvement — internal mammary node involvement (true | false)"
    )
    scf_involvement: bool = Field(
        default=False,
        description="scf_involvement — supraclavicular fossa involvement (true | false)"
    )
    symptomatic_metastasis: bool = Field(
        default=False,
        description="symptomatic_metastasis (true | false)"
    )
    surgery_feasible_after_nact: bool = Field(
        default=True,
        description="surgery_feasible_after_nact (true | false)"
    )
    prior_chest_rt: bool = Field(
        default=False,
        description="prior_chest_rt (true | false)"
    )
    progression_on_endocrine: bool = Field(
        default=False,
        description="progression_on_endocrine (true | false)"
    )
    bone_only_metastases: bool = Field(
        default=False,
        description="bone_only_metastases (true | false)"
    )
    visceral_metastases: bool = Field(
        default=False,
        description="visceral_metastases (true | false)"
    )
    brca_mutation: bool = Field(
        default=False,
        description="brca_mutation (true | false)"
    )
    
    # ── Validators ──
    
    @field_validator("ki67_percent", mode="after")
    @classmethod
    def ki67_in_range(cls, v: Optional[float]) -> Optional[float]:
        """Validate Ki-67 percentage is clinically reasonable (0–100%)."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Ki-67 percentage must be between 0 and 100")
        return v
    
    @model_validator(mode="after")
    def check_surgery_fields(self) -> "BreastInput":
        """
        Cross-field validation:
        1. If surgery_done=True, surgery_type and margin_status are required.
        2. Nodes consistency: nodes_positive should not exceed nodes_examined.
        """
        # Surgery conditional: if surgery_done, surgery_type and margin_status must be provided
        if self.surgery_done:
            if self.surgery_type is None:
                raise ValueError("surgery_type is required when surgery_done=True")
            if self.margin_status is None:
                raise ValueError("margin_status is required when surgery_done=True")
        
        # Nodes consistency: nodes_positive <= nodes_examined
        if self.nodes_positive > self.nodes_examined:
            raise ValueError(
                f"nodes_positive ({self.nodes_positive}) cannot exceed "
                f"nodes_examined ({self.nodes_examined})"
            )
        
        return self


# ─────────────────────────────────────────────────────────────────────────────
# BREAST RESULT MODEL
# ─────────────────────────────────────────────────────────────────────────────

class BreastResult(BaseModel):
    """Structured output from breast cancer decision engine."""
    
    formatted_output: str = Field(
        ...,
        description="Final formatted recommendation (produced by OUTPUT_TEMPLATE in config)"
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
        default="Institutional Breast Cancer Protocol v1.0 (aligned with NCCN/ESMO)",
        description="Protocol version reference"
    )