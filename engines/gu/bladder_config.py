"""
Configuration — Bladder Cancer Protocol
Institutional GU Cancers Protocol v1.0
"""

PROTOCOL_VERSION = "Institutional GU Cancers Protocol v1.0 – Bladder"

CISPLATIN_MIN_CRCL = 50.0

# T-stages by category
NMIBC_T_STAGES = ["Ta", "Tis", "T1"]
MIBC_T_STAGES  = ["T2", "T2a", "T2b", "T3", "T3a", "T3b", "T4", "T4a", "T4b"]

# T4b is considered unresectable / fixed
UNRESECTABLE_T_STAGES = ["T4b"]

# High-risk NMIBC criteria (any one of these → high risk)
HIGH_RISK_NMIBC_T_STAGES = ["T1", "Tis"]
