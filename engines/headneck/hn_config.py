"""
Configuration — Head & Neck SCC Protocol
Institutional HNSCC Protocol v1.0 | AJCC 8th Edition
"""

PROTOCOL_VERSION = "Institutional HNSCC Protocol v1.0"

CISPLATIN_MIN_CRCL = 50.0

EARLY_STAGES            = ["I", "II"]
LOCALLY_ADVANCED_STAGES = ["III", "IVA", "IVB"]

EARLY_T_STAGES    = ["T1", "T2"]
ADVANCED_T_STAGES = ["T3", "T4a", "T4b"]

# Oral cavity subsites → display labels
ORAL_SUBSITE_LABELS = {
    "oral_tongue":         "Oral tongue",
    "buccal_mucosa":       "Buccal mucosa",
    "floor_of_mouth":      "Floor of mouth",
    "retromolar_trigone":  "Retromolar trigone",
    "alveolus_mandibular": "Mandibular alveolus",
    "alveolus_maxillary":  "Maxillary alveolus",
    "hard_palate":         "Hard palate",
    "lip":                 "Lip",
}

# DOI threshold (mm) for high-risk nodal upgrade in oral cavity
DOI_HIGH_RISK_THRESHOLD = 10.0

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
