"""
Configuration — Head & Neck SCC Decision Engine
Protocol constants and clinical thresholds.
Institutional HNSCC Protocol v1.0 | AJCC 8th Edition
"""

# ─────────────────────────────────────────────────────────────────────────────
# PROTOCOL VERSION & CLINICAL THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────

PROTOCOL_VERSION = "Institutional HNSCC Protocol v1.0"
PROTOCOL_REFERENCE = "Institutional HNSCC Protocol v1.0 (AJCC 8th Edition)"

# Renal function threshold for cisplatin eligibility
CISPLATIN_MIN_CRCL = 50.0  # mL/min — minimum creatinine clearance for cisplatin


# ─────────────────────────────────────────────────────────────────────────────
# DISEASE CLASSIFICATION CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Early-stage disease
EARLY_STAGES = ["I", "II"]

# Locally advanced disease
LOCALLY_ADVANCED_STAGES = ["III", "IVA", "IVB"]

# Metastatic/unresectable disease
METASTATIC_STAGES = ["IVC"]

# T stage classifications
EARLY_T_STAGES = ["T1", "T2"]
ADVANCED_T_STAGES = ["T3", "T4a", "T4b"]


# ─────────────────────────────────────────────────────────────────────────────
# ORAL CAVITY SPECIFIC CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Oral cavity subsites → display labels
ORAL_SUBSITE_LABELS = {
    "oral_tongue": "Oral tongue",
    "buccal_mucosa": "Buccal mucosa",
    "floor_of_mouth": "Floor of mouth",
    "retromolar_trigone": "Retromolar trigone",
    "alveolus_mandibular": "Mandibular alveolus",
    "alveolus_maxillary": "Maxillary alveolus",
    "hard_palate": "Hard palate",
    "lip": "Lip",
}

# DOI threshold (mm) for high-risk nodal upgrade in oral cavity
DOI_HIGH_RISK_THRESHOLD = 10.0  # >10 mm DOI → N1 upgrade consideration


# ─────────────────────────────────────────────────────────────────────────────
# PARAMETER REQUIREMENTS
# ─────────────────────────────────────────────────────────────────────────────

# Essential parameters required for ALL cases
ESSENTIAL_PARAMS = [
    "age",
    "ecog",
    "primary_site",
    "ajcc_stage",
    "t_stage",
    "n_stage",
    "distant_metastasis",
    "resectable",
    "creatinine_clearance",
]

# Additional essentials when primary_site = oral_cavity
ORAL_CAVITY_EXTRA_PARAMS = [
    "oral_subsite",
    "doi_mm",
]


# ─────────────────────────────────────────────────────────────────────────────
# CHEMOTHERAPY REGIMENS
# ─────────────────────────────────────────────────────────────────────────────

# Concurrent chemotherapy with radiotherapy
CHEMO_WEEKLY_CISPLATIN = "Cisplatin 40 mg/m² weekly × 6–7 cycles"
CHEMO_CISPLATIN_3WEEKLY = "Cisplatin 100 mg/m² every 3 weeks × 3 cycles"
CHEMO_CARBOPLATIN_ALT = "Carboplatin AUC 2 (alternative for renal impairment or toxicity)"
CHEMO_CETUXIMAB = "Cetuximab weekly (alternative to cisplatin for ineligible patients)"

# Induction chemotherapy
CHEMO_INDUCTION_TPF = "Docetaxel 75 mg/m² + Cisplatin 100 mg/m² + 5-FU 1000 mg/m²/day × 4 days, every 3 weeks × 3 cycles"

# Palliative chemotherapy
CHEMO_PALLIATIVE = "Platinum-based chemotherapy ± cetuximab or immunotherapy"


# ─────────────────────────────────────────────────────────────────────────────
# RADIOTHERAPY DOSE SCHEDULES
# ─────────────────────────────────────────────────────────────────────────────

# Conventional fractionation
RT_DOSE_DEFINITIVE = "70 Gy / 35 fractions (2 Gy/fraction)"
RT_DOSE_ADJUVANT = "60–66 Gy / 30–33 fractions"
RT_DOSE_PALLIATIVE = "30 Gy / 10 fractions or 20 Gy / 5 fractions"

# Hypofractionated schedules (emerging evidence)
RT_DOSE_HYPOFRACTIONATED = "60 Gy / 20 fractions (2.5–3 Gy/fraction) or 55 Gy / 20 fractions"

# Technique recommendations
RT_TECHNIQUE_IMRT = "IMRT or VMAT (intensity-modulated radiotherapy)"
RT_TECHNIQUE_PBT = "Proton beam therapy (when available, selected cases)"


# ─────────────────────────────────────────────────────────────────────────────
# HIGH-RISK PATHOLOGICAL FEATURES
# ─────────────────────────────────────────────────────────────────────────────

# Features triggering adjuvant concurrent chemoradiation in early-stage post-surgery
HIGH_RISK_PATHOLOGICAL_FEATURES = [
    "Positive surgical margins",
    "Extracapsular/extranodal extension (ECE)",
    "Perineural invasion (PNI)",
    "Lymphovascular invasion (LVI)",
    "Multiple positive nodes (≥2 nodes)",
]


# ─────────────────────────────────────────────────────────────────────────────
# SPECIAL CONSIDERATIONS
# ─────────────────────────────────────────────────────────────────────────────

# Oropharyngeal cancer — HPV/p16 status significance
HPV_POSITIVE_RISK_REDUCTION = 30  # percentage reduction in recurrence with HPV+ status (approximate)

# Organ preservation candidates
ORGAN_PRESERVATION_CANDIDATES = [
    "Laryngeal SCC (appropriately selected T3, T4a)",
    "Oropharyngeal SCC (selected cases)",
    "Hypopharyngeal SCC (selected T3, early T4a)",
]