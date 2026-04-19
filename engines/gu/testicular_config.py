"""
Configuration — Testicular Cancer Protocol
Institutional GU Cancers Protocol v1.0
"""

PROTOCOL_VERSION = "Institutional GU Cancers Protocol v1.0 – Testicular"

# Residual mass thresholds post-chemotherapy
SEMINOMA_RESIDUAL_THRESHOLD_CM    = 3.0   # ≥3 cm → resection / PET-CT assessment
NSGCT_RESIDUAL_THRESHOLD_CM       = 1.0   # ≥1 cm → RPLND

# Radiotherapy dose and fields
RT_PA_DOSE_GY       = 20   # Gy — Stage I seminoma adjuvant PA field
RT_PA_FRACTIONS     = 10   # fractions (2 Gy / fraction)
RT_STAGE_II_DOSE_GY = 30   # Gy — Stage IIA/B PA + dog-leg field
RT_STAGE_II_FRAC    = 15   # fractions

# Para-aortic (PA) field borders
PA_FIELD = {
    "upper_border": "T11–T12",
    "lower_border": "L5–S1",
    "ctv":          "Aorta +1.9 cm; IVC +1.2 cm",
    "ptv":          "CTV + 0.5 cm",
    "portals":      "AP/PA",
}

# Dog-leg field (PA + ipsilateral pelvic nodes)
DOG_LEG_FIELD = {
    "definition": "PA field + ipsilateral common iliac, external iliac, proximal internal iliac LN",
    "lower_border": "Mid obturator foramen or top of acetabulum",
    "ctv": "PA CTV + 1.2 cm around ipsilateral iliac vessels",
    "ptv": "CTV + 0.7 cm",
    "kidney_constraint": "D50 < 8 Gy each kidney",
}

# IGCCCG RISK – S-stage approximate mapping
# S0/S1 → good; S2 → intermediate; S3 → poor (NSGCT) / intermediate (seminoma)
S_STAGE_TO_IGCCCG = {
    "S0": "good",
    "S1": "good",
    "S2": "intermediate",
    "S3": "poor",   # for NSGCT; seminoma has no "poor" risk
}
