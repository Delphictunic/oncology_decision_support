"""
Configuration — Prostate Cancer Protocol
Institutional GU Cancers Protocol v1.0
AJCC 8th Edition
"""

PROTOCOL_VERSION = "Institutional GU Cancers Protocol v1.0 – Prostate"

CISPLATIN_MIN_CRCL = 50.0

# AJCC 8th Edition staging groups
LOW_RISK_STAGES          = ["I"]
FAVORABLE_IR_STAGES      = ["IIA"]                        # PSA 10–20, GG1
UNFAVORABLE_IR_STAGES    = ["IIB", "IIC"]                 # GG2–4 (IIC incl. GG4)
HIGH_RISK_STAGES         = ["IIIA", "IIIB"]
VERY_HIGH_RISK_STAGES    = ["IIIC"]
NODE_POSITIVE_STAGE      = "IVA"
METASTATIC_STAGE         = "IVB"

# Castrate testosterone threshold (ng/dL)
CASTRATE_T_THRESHOLD = 50.0

# PSADT threshold for high-risk nmCRPC (months)
HIGH_RISK_PSADT_THRESHOLD = 10.0

# PSA BCR threshold post-RP (ng/mL)
BCR_PSA_THRESHOLD = 0.2

# Grade Group → approximate Gleason text
GRADE_GROUP_LABELS = {
    1: "Gleason ≤6 (3+3)",
    2: "Gleason 7 (3+4)",
    3: "Gleason 7 (4+3)",
    4: "Gleason 8 (4+4 / 3+5 / 5+3)",
    5: "Gleason 9–10",
}
