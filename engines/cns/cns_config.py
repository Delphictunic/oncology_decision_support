"""
CNS TUMORS - Configuration
Institutional CNS Tumors Protocol v1.0 | WHO 2021 Classification
Centralized configuration for all decision thresholds and protocols
"""

from enum import Enum
from typing import Dict, Any

PROTOCOL_VERSION = "Institutional CNS Tumors Protocol v1.0"

# ─────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ─────────────────────────────────────────────────────────────────────────────

class CNSTumourType(str, Enum):
    GLIOMA           = "glioma"
    MENINGIOMA       = "meningioma"
    EPENDYMOMA       = "ependymoma"
    MEDULLOBLASTOMA  = "medulloblastoma"
    PITUITARY        = "pituitary_adenoma"
    CRANIOPHARYNGIOMA = "craniopharyngioma"

class WHOGrade(str, Enum):
    G1 = "1"
    G2 = "2"
    G3 = "3"
    G4 = "4"

class GliomaSubtype(str, Enum):
    IDH_MUTANT_ASTROCYTOMA      = "idh_mutant_astrocytoma"
    IDH_MUTANT_OLIGODENDROGLIOMA = "idh_mutant_oligodendroglioma"
    IDH_WILDTYPE_GBM            = "idh_wildtype_gbm"
    ANAPLASTIC_ASTROCYTOMA      = "anaplastic_astrocytoma"
    OTHER                       = "other"

class ResectionExtent(str, Enum):
    GTR   = "gross_total_resection"
    STR   = "subtotal_resection"
    BIOPSY = "biopsy"
    NONE  = "none"

class Confidence(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED   = "red"

class EpendymomaLocation(str, Enum):
    POSTERIOR_FOSSA = "posterior_fossa"
    SPINAL          = "spinal"
    SUPRATENTORIAL  = "supratentorial"

# ─────────────────────────────────────────────────────────────────────────────
# GLIOMA CONFIGURATION (Low-grade, High-grade, GBM)
# ─────────────────────────────────────────────────────────────────────────────

GLIOMA_CONFIG = {
    # Low-Grade Glioma (WHO Grade 2, IDH-mutant)
    "low_grade": {
        "description": "Low-grade glioma (WHO Grade 2, IDH-mutant astrocytoma or oligodendroglioma)",
        
        # HIGH-RISK CRITERIA: Any ONE criterion makes case HIGH-RISK
        "high_risk_criteria": {
            "age_threshold": 40,                  # age >= 40 → HIGH-RISK
            "tumor_size_cm_threshold": 6,         # tumor > 6 cm → HIGH-RISK
            "crosses_midline": True,              # crosses midline → HIGH-RISK
            "has_neurological_deficit": True,     # seizures/neuro deficit → HIGH-RISK
            "subtotal_resection": True,           # STR/biopsy → HIGH-RISK
            "residual_disease": True,             # residual → HIGH-RISK
        },
        
        "low_risk_treatment": {
            "primary": "Surgery",
            "adjuvant": "Observation if complete resection; RT ± chemotherapy if high risk",
            "radiation": "50–54 Gy if indicated",
            "chemotherapy": "PCV or temozolomide (selected cases)",
            "rationale": "Indolent tumor with long survival",
            "followup": "MRI every 6 months",
        },
        
        "high_risk_treatment": {
            "primary": "Adjuvant radiotherapy + chemotherapy",
            "radiation": "50–54 Gy / 25–27# (2 Gy/fraction)",
            "chemotherapy": "PCV × 6 cycles (RTOG 9802: RT+PCV vs RT alone → OS 13.3 vs 7.8 yrs; standard) OR Temozolomide if PCV not tolerated",
            "rationale": "RTOG 9802: RT+PCV vs RT alone → OS 13.3 vs 7.8 years in high-risk LGG; EORTC 22845: early RT improves PFS but not OS; RT timing after surgery acceptable",
            "followup": "MRI every 6 months; annual assessment × 10 years (late recurrence common)",
        },
    },
    
    # High-Grade Glioma (WHO Grade 3, Anaplastic Astrocytoma)
    "anaplastic_astrocytoma": {
        "description": "Anaplastic astrocytoma (WHO Grade 3, IDH-mutant)",
        "treatment": {
            "primary": "Maximal safe resection",
            "radiation": "59–60 Gy / 30# (2 Gy/fraction)",
            "chemotherapy": "PCV × 6 cycles (standard) or Temozolomide",
            "rationale": "Grade 3 tumors: adjuvant RT+chemo improves PFS vs RT alone; equivalent outcomes between PCV and TMZ",
            "followup": "MRI every 3 months × 2 years; annual thereafter",
        },
    },
    
    # Glioblastoma (WHO Grade 4)
    "glioblastoma": {
        "description": "Glioblastoma (WHO Grade 4, IDH wild-type)",
        
        "standard_risk_young": {
            "age_threshold": 70,
            "ecog_threshold": 2,
            "treatment": {
                "primary": "Maximal safe resection → Concurrent chemoradiation (Stupp protocol)",
                "radiation": "60 Gy / 30# (2 Gy/fraction) — Stupp standard",
                "chemotherapy": "Temozolomide concurrent + adjuvant × 6 cycles",
                "rationale": "Stupp et al. NEJM 2005: RT+TMZ vs RT alone → median OS 14.6 vs 12.1 months; concurrent+adjuvant standard of care",
                "followup": "MRI every 8–12 weeks; clinical assessment every 4 weeks during RT",
            },
        },
        
        "elderly_poor_ps": {
            "age_threshold": 70,
            "ecog_threshold": 2,
            "treatment_options": [
                {
                    "name": "Hypofractionated RT (NORDIC preference if MGMT unmethylated)",
                    "radiation": "40 Gy / 15# (2.67 Gy/fraction)",
                    "chemotherapy": "Consider limited TMZ if MGMT methylated",
                },
                {
                    "name": "TMZ monotherapy (if MGMT methylated, not candidates for RT)",
                    "radiation": "None or very limited RT",
                    "chemotherapy": "Temozolomide × 6 cycles",
                },
                {
                    "name": "Ultra-short RT (ECOG 3 or <3 months expected survival)",
                    "radiation": "25 Gy / 5# (5 Gy/fraction)",
                    "chemotherapy": "None",
                },
            ],
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# MENINGIOMA CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

MENINGIOMA_CONFIG = {
    "grade_1": {
        "description": "Meningioma WHO Grade 1 (Benign)",
        "treatment": {
            "primary": "Surgery",
            "adjuvant": "Not required",
            "followup": "MRI surveillance",
            "rationale": "Low recurrence after complete resection",
        },
    },
    "grade_1_residual": {
        "description": "Meningioma WHO Grade 1 with residual disease",
        "treatment": {
            "primary": "Adjuvant radiotherapy",
            "radiation": "54–60 Gy",
            "rationale": "Improves local control",
        },
    },
    "grade_2": {
        "description": "Atypical Meningioma (WHO Grade 2)",
        "treatment": {
            "primary": "Surgery + adjuvant radiotherapy",
            "radiation": "60 Gy",
            "rationale": "High recurrence risk",
        },
    },
    "grade_3": {
        "description": "Anaplastic Meningioma (WHO Grade 3)",
        "treatment": {
            "primary": "Surgery + radiotherapy",
            "radiation": "60–66 Gy",
            "rationale": "Aggressive tumor behavior",
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# EPENDYMOMA CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

EPENDYMOMA_CONFIG = {
    "posterior_fossa": {
        "description": "Pediatric Posterior Fossa Ependymoma",
        "treatment": {
            "primary": "Surgery",
            "adjuvant": "Radiotherapy (even after GTR)",
            "radiation": "54–59.4 Gy",
            "rationale": "Improves local control",
        },
    },
    "spinal": {
        "description": "Spinal Ependymoma",
        "treatment": {
            "primary": "Surgery (preferably complete excision)",
            "adjuvant": "Observation if complete resection",
            "radiation": "Only if residual/recurrent",
            "rationale": "Good prognosis with surgery alone",
        },
    },
    "anaplastic": {
        "description": "Anaplastic Ependymoma (Grade 3)",
        "treatment": {
            "primary": "Surgery + radiotherapy",
            "radiation": "59.4–60 Gy",
            "rationale": "Higher recurrence risk",
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# MEDULLOBLASTOMA CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

MEDULLOBLASTOMA_CONFIG = {
    "standard_risk": {
        "csi_dose": "23.4 Gy / 13#",
        "boost_dose": "+32.4 Gy boost to posterior fossa = total 55.8 Gy",
        "chemotherapy": "Vincristine concurrent; PCV post-RT × 6–8 cycles",
    },
    "high_risk": {
        "csi_dose": "36 Gy / 20#",
        "boost_dose": "+19.8 Gy boost to posterior fossa / primary site = total 55.8 Gy",
        "chemotherapy": "Cisplatin + Lomustine + Vincristine intensified",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# PITUITARY ADENOMA CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

PITUITARY_CONFIG = {
    "complete_resection": {
        "treatment": {
            "primary": "Transsphenoidal surgery (preferred)",
            "adjuvant": "Not required if complete resection and hormonal remission",
        },
    },
    "residual_disease": {
        "treatment": {
            "primary": "Adjuvant radiotherapy (FSRT or SRS)",
            "radiation_fractionated": "50.4 Gy / 28# (functional) or 45 Gy / 25# (non-functional)",
            "radiation_srs": "12–20 Gy × 1# (if ≤3 cm and adequate OAR distance)",
        },
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# DECISION FLAGS
# ─────────────────────────────────────────────────────────────────────────────

FLAG_TEMPLATES = {
    "high_risk_lgg": "High-risk LGG (age ≥40, STR, tumour >6 cm, midline crossing, or neurological deficit)",
    "elderly_gbm": "Elderly/poor PS GBM – hypofractionated regimen (NORDIC/Perry)",
    "mgmt_status": "MGMT methylation status critical for treatment selection in GBM",
    "high_risk_medullo": "High-risk medulloblastoma (M+, STR, or high-risk molecular) – intensified CSI + chemo",
    "residual_pituitary": "Residual pituitary adenoma – adjuvant RT recommended",
    "poor_ps": "Poor performance status – individualised / palliative approach",
}

# ─────────────────────────────────────────────────────────────────────────────
# RADIATION ONCOLOGY DETAILS (OAR, Dosing Standards)
# ─────────────────────────────────────────────────────────────────────────────

RT_STANDARDS = {
    "lgg": {
        "dose": "50–54 Gy / 25–27# (2 Gy/fraction)",
        "gtv": "FLAIR abnormality + resection cavity + residual tumour",
        "ctv": "GTV + 2 cm",
        "ptv": "CTV + 5 mm",
        "technique": "3DCRT/IMRT; fused MRI (FLAIR + T1+C)",
        "oar": ["Brainstem <54 Gy", "Optic chiasm <54 Gy", "Hippocampus sparing if feasible"],
    },
    "gbm": {
        "dose": "60 Gy / 30# (2 Gy/fraction)",
        "gtv": "CE tumour + FLAIR abnormality + oedema",
        "ctv": "GTV + 2 cm",
        "ptv": "CTV + 5 mm",
        "technique": "IMRT/VMAT; IGRT mandatory; fused MRI (T1+C + FLAIR)",
        "oar": ["Brainstem <54 Gy", "Optic chiasm <54 Gy", "Cochlea <45 Gy", "Lens <7 Gy"],
    },
}
