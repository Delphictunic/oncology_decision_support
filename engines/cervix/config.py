"""
Configuration — Cervix Cancer Decision Engine
Protocol constants and clinical thresholds.
Institutional Cervix Cancer Protocol v1.0 (FIGO 2018)
"""

# ─────────────────────────────────────────────────────────────────────────────
# PROTOCOL VERSION & CLINICAL THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────

PROTOCOL_VERSION = "Institutional Cervix Cancer Protocol v1.0"
PROTOCOL_REFERENCE = "Institutional Cervix Cancer Protocol v1.0 (FIGO 2018)"

# Renal function threshold for cisplatin eligibility
CISPLATIN_MIN_CRCL = 50.0  # mL/min — minimum creatinine clearance for cisplatin


# ─────────────────────────────────────────────────────────────────────────────
# DISEASE CLASSIFICATION CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Early-stage disease (candidates for surgery or brachytherapy-based RT)
EARLY_STAGES = ["IA1", "IA2", "IB1", "IB2"]

# Locally advanced disease (require concurrent chemoradiation)
LOCALLY_ADVANCED_STAGES = [
    "IB3", "IIA", "IIB", "IIIA", "IIIB", "IIIC", "IVA"
]

# Metastatic disease
METASTATIC_STAGES = ["IVB"]


# ─────────────────────────────────────────────────────────────────────────────
# CHEMOTHERAPY REGIMENS
# ─────────────────────────────────────────────────────────────────────────────

# Concurrent chemotherapy with radiotherapy
CHEMO_WEEKLY_CISPLATIN = "Weekly cisplatin 40 mg/m² × 5–6 cycles"
CHEMO_CARBOPLATIN_AUC = "Carboplatin AUC 2 (cisplatin-alternative for renal impairment)"

# Palliative chemotherapy
CHEMO_PALLIATIVE = "Platinum-based chemotherapy ± bevacizumab"


# ─────────────────────────────────────────────────────────────────────────────
# RADIOTHERAPY DOSE SCHEDULES
# ─────────────────────────────────────────────────────────────────────────────

# External beam radiotherapy (EBRT)
RT_EBRT_PELVIS_STANDARD = "50 Gy / 25 fractions"
RT_EBRT_PELVIS_WITH_PARA_AORTIC = "Pelvis 50 Gy / 25# + Para-aortic 45 Gy + Boost to gross nodes 56–60 Gy"

# Brachytherapy
RT_ICBT_DOSE_EQD2 = "80–85 Gy EQD2 to HR-CTV"
RT_VAGINAL_VAULT = "6 Gy per fraction / 2 fractions"

# Technique recommendations
RT_TECHNIQUE_IMRT = "IMRT/VMAT"
RT_TECHNIQUE_3DCRT = "3D conformal radiotherapy"


# ─────────────────────────────────────────────────────────────────────────────
# PROGNOSTIC & RISK CRITERIA
# ─────────────────────────────────────────────────────────────────────────────

# High-risk pathological factors (Sedlis criteria) — trigger adjuvant RT in early-stage post-surgery
SEDLIS_FACTORS = [
    "Positive pelvic lymph nodes",
    "Parametrial invasion",
    "Positive surgical margins",
    "Lymphovascular space invasion (LVSI) with grade 2–3",
]

# Peters criteria — high-risk features in early-stage disease
PETERS_HIGH_RISK = [
    "Positive pelvic lymph nodes",
    "Positive surgical margins",
    "Parametrial invasion",
]