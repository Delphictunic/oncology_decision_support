from enum import Enum
from pydantic import BaseModel, Field, validator
from typing import List


class FIGOStage(str, Enum):
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
    SCC = "scc"
    ADENO = "adenocarcinoma"
    ADENOSQUAMOUS = "adenosquamous"


class Confidence(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class CervixInput(BaseModel):
    age: int = Field(..., ge=10, le=100)
    ecog: int = Field(..., ge=0, le=4)
    figo_stage: FIGOStage
    histology: Histology
    tumor_size_cm: float = Field(..., ge=0)
    pelvic_nodes_positive: bool
    para_aortic_nodes_positive: bool
    hydronephrosis: bool
    creatinine_clearance: float = Field(..., ge=0)
    prior_surgery: bool = False
    margins_positive: bool = False
    lvsi_present: bool = False
    parametrial_invasion: bool = False
    distant_metastasis: bool = False
    symptomatic_bleeding: bool = False
    post_crt_residual: bool = False

    @validator("tumor_size_cm")
    def tumor_reasonable(cls, v):
        if v > 20:
            raise ValueError("Tumor size unrealistic")
        return v


class CervixResult(BaseModel):
    formatted_output: str
    confidence: Confidence
    flags: List[str]
    mdt_required: bool
    protocol_reference: str
