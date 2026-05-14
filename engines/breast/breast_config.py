"""
Configuration — Breast Cancer Decision Engine
Protocol constants, clinical thresholds, and output formatting template.
Institutional Breast Cancer Protocol v1.0 (aligned with NCCN/ESMO)
"""

# ─────────────────────────────────────────────────────────────────────────────
# PROTOCOL VERSION & CLINICAL THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────

PROTOCOL_VERSION = "1.0"
PROTOCOL_REFERENCE = "Institutional Breast Cancer Protocol v1.0 (aligned with NCCN/ESMO)"

# Biomarker thresholds
LUMINAL_A_KI67_THRESHOLD = 20  # %; upper bound for "low" Ki-67 in Luminal A classification


# ─────────────────────────────────────────────────────────────────────────────
# RADIATION THERAPY CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Breast-conserving surgery (BCS) doses
RT_BCS_LUMINAL_A = "40 Gy / 2.67 Gy per fraction / 15 fractions or 50 Gy / 2 Gy per fraction / 25 fractions"
RT_BCS_STANDARD = "50 Gy / 2 Gy per fraction / 25 fractions"

# Post-mastectomy radiation therapy (PMRT)
RT_PMRT_STANDARD = "50 Gy / 25 fractions"

# Boost and technique
RT_BOOST_STANDARD = "Tumor bed boost recommended"
RT_BOOST_LUMINAL_A_CONDITIONAL = "Boost to tumor bed if age <50 or grade ≥3 or close margins"
RT_TECHNIQUE = "3DCRT"

# Organs-at-risk (OAR) constraints
OAR_HEART_LEFT_BREAST = "Heart mean dose < 4 Gy (DIBH advised)"


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEMIC THERAPY CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Chemotherapy regimens
CHEMO_ANTHRACYCLINE_TAXANE = "Anthracycline + taxane (dose-dense AC followed by dose-dense paclitaxel)"
CHEMO_DC_4CYC = "Docetaxel + Cyclophosphamide × 4 cycles"
CHEMO_PACLITAXEL_WEEKLY = "Paclitaxel weekly × 12"
CHEMO_NOT_ROUTINELY_INDICATED = "Chemotherapy: not routinely indicated"
CHEMO_CONSIDER_BY_ASSAY = "Chemotherapy: consider based on genomic assay"

# HER2-directed therapy
HER2_TRASTUZUMAB_1YEAR = "Trastuzumab to complete 1 year"
HER2_PACLITAXEL_TRASTUZUMAB = "Paclitaxel weekly × 12 + Trastuzumab to complete 1 year"
HER2_TRASTUZUMAB_PERTUZUMAB = "Chemotherapy + trastuzumab ± pertuzumab"
HER2_T_DM1_RESIDUAL = "T-DM1 if residual after neoadjuvant"

# Endocrine therapy
ENDO_TAMOXIFEN_LONG = "Tamoxifen × 5–10 years"
ENDO_TAMOXIFEN_5Y = "Tamoxifen × 5 years"
ENDO_AI_5Y = "Aromatase inhibitor × 5 years"
ENDO_AI_CONTRAINDICATED = "Tamoxifen if AI contraindicated"
ENDO_OVARIAN_SUPPRESSION_AI = "Ovarian suppression + AI"

# Genomic testing
GENOMIC_ASSAY_CANASSIST = "CANASSIST"
GENOMIC_TEST_STRONGLY_RECOMMENDED = "Genomic testing strongly recommended"
GENOMIC_TEST_RECOMMENDED = "Genomic testing recommended"
GENOMIC_TEST_NOT_REQUIRED = "Genomic testing not required (very low risk, screen-detected type)"

# PARP inhibitors
PARP_OLAPARIB = "Consider PARP inhibitor (olaparib) if high-risk"
PARP_PLATINUM_BASED = "Consider platinum-based regimen; consider PARP inhibitor (olaparib) if high-risk"


# ─────────────────────────────────────────────────────────────────────────────
# FOLLOW-UP SCHEDULES
# ─────────────────────────────────────────────────────────────────────────────

# BCS follow-up
FU_BCS_STANDARD = "Clinical exam every 6 months, annual mammogram"
FU_BCS_LUMINAL_A_POSTMENOPAUSAL = "Annual mammography; clinical exam every 6–12 months; bone health monitoring (AI)"

# Post-mastectomy follow-up
FU_MRM_STANDARD = "Clinical exam every 6 months, annual mammogram"
FU_MRM_5YEAR = "Clinical exam every 6 months × 5 years; annual imaging"


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_TEMPLATE = """CASE SUMMARY
{case_summary}

PRIMARY RECOMMENDATION
{primary_recommendation}

CLINICAL REASONING
{reasoning}

TREATMENT DETAILS
Surgery: {surgery_recommendation}
Systemic Therapy: {systemic_therapy}
Radiation Therapy: {radiation_therapy}
Follow-up Care: {follow_up}"""