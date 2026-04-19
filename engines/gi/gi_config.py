"""
Configuration — GI Cancers Protocol
Institutional Oncology Protocol v1.0
Covers: Esophagus | Stomach | Rectum | Anal Canal | Pancreas | Colon
"""

PROTOCOL_VERSION = "Institutional GI Cancers Protocol v1.0"

# ── Esophagus ─────────────────────────────────────────────────────────────
ESOPHAGUS_PREOP_RT_DOSE         = "41.4–50.4 Gy / 23–28#"
ESOPHAGUS_DEFINITIVE_RT_DOSE    = "50.4 Gy / 28#"
ESOPHAGUS_POSTOP_RT_DOSE        = "45–50.4 Gy / 25–28#"
ESOPHAGUS_CERVICAL_RT_DOSE      = "60 Gy / 30#"

# ── Stomach ───────────────────────────────────────────────────────────────
STOMACH_POSTOP_RT_DOSE          = "45 Gy / 25#"
STOMACH_UNRESECTABLE_RT_DOSE    = "50–54 Gy / 25–28#"

# ── Rectum ────────────────────────────────────────────────────────────────
RECTUM_LCRT_DOSE                = "45–50.4 Gy / 25–28#"
RECTUM_SCRT_DOSE                = "25 Gy / 5# (5×5 Gy)"
RECTUM_BOOST_DOSE               = "+5.4 Gy boost if CRM threatened"

# ── Anal Canal ────────────────────────────────────────────────────────────
ANAL_EARLY_RT_DOSE              = "50.4–54 Gy / 28–30#"
ANAL_ADVANCED_RT_DOSE           = "54–59 Gy / 30–33#"
ANAL_ELECTIVE_LN_DOSE           = "45 Gy / 25# (elective LN)"

# ── Pancreas ──────────────────────────────────────────────────────────────
PANCREAS_ADJUVANT_RT_DOSE       = "50.4 Gy / 28# + boost to 54–56 Gy if R1"
PANCREAS_DEFINITIVE_RT_DOSE     = "54 Gy / 30# (LAPC after induction chemo)"

# ── Colon ─────────────────────────────────────────────────────────────────
COLON_ADJUVANT_CHEMO_LOW        = "CAPOX × 3 months or FOLFOX × 6 months (low-risk Stage III)"
COLON_ADJUVANT_CHEMO_HIGH       = "FOLFOX or CAPOX × 6 months (Stage II high-risk / Stage III high)"
