"""
Production-Ready Head & Neck SCC Decision Engine
Output format mirrors institutional case examples exactly.
AJCC 8th Edition | Institutional HNSCC Protocol v1.0
"""

from .hn_models import HNInput, HNResult, Confidence
from .hn_config import (
    PROTOCOL_VERSION,
    CISPLATIN_MIN_CRCL,
    EARLY_STAGES,
    LOCALLY_ADVANCED_STAGES,
    EARLY_T_STAGES,
    ORAL_SUBSITE_LABELS,
    DOI_HIGH_RISK_THRESHOLD,
)


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _footer(confidence: Confidence, flags: list, mdt_required: bool, protocol: str) -> str:
    flag_str = ", ".join(flags) if flags else "None"
    return (
        f"\nConfidence → {confidence.value}\n"
        f"Flags → {flag_str}\n"
        f"MDT Required → {mdt_required}\n"
        f"Protocol Reference → {protocol}"
    )


def _cisplatin_check(crcl: float, hearing_adequate: bool, flags: list):
    """
    Returns (chemo_line, is_ineligible).
    Appends to flags in-place if ineligible.
    """
    if crcl < CISPLATIN_MIN_CRCL:
        flags.append("Renal impairment – cisplatin contraindicated")
        return (
            "Cisplatin contraindicated (CrCl < 50)\n"
            "Alternatives: Carboplatin AUC 2 weekly OR cetuximab\n"
            "MDT discussion required",
            True,
        )
    if not hearing_adequate:
        flags.append("Hearing impairment – cisplatin ototoxicity risk")
        return (
            "Cisplatin caution – ototoxicity risk\n"
            "Consider carboplatin or cetuximab\n"
            "MDT discussion required",
            True,
        )
    return "Weekly cisplatin 40 mg/m²", False


def _subsite_label(inp: HNInput) -> str:
    if inp.primary_site.value == "oral_cavity" and inp.oral_subsite:
        return ORAL_SUBSITE_LABELS.get(inp.oral_subsite.value, inp.oral_subsite.value)
    mapping = {
        "oropharynx":  "Oropharynx",
        "hypopharynx": "Hypopharynx",
        "larynx":      "Larynx",
    }
    return mapping.get(inp.primary_site.value, inp.primary_site.value)


def _node_label(inp: HNInput) -> str:
    """Human-readable node description."""
    n = inp.n_stage.value
    if n == "N0":
        return "Node-negative"
    if inp.bilateral_nodes or n == "N2c":
        return "Bilateral nodal disease"
    if n in ("N2b", "N3"):
        return "Multiple positive nodes"
    return "Node-positive"


# ─────────────────────────────────────────────────────────────────────────────
# Oral cavity sub-engine
# ─────────────────────────────────────────────────────────────────────────────

def _oral_cavity(inp: HNInput) -> HNResult:
    flags       = []
    confidence  = Confidence.GREEN
    mdt_required = False

    stage    = inp.ajcc_stage.value
    t        = inp.t_stage.value
    n        = inp.n_stage.value
    subsite  = _subsite_label(inp)
    doi      = inp.doi_mm if inp.doi_mm is not None else 0.0
    node_lbl = _node_label(inp)

    chemo_line, chemo_ineligible = _cisplatin_check(
        inp.creatinine_clearance, inp.hearing_adequate, flags
    )
    if chemo_ineligible:
        confidence   = Confidence.AMBER
        mdt_required = True

    # ── ELDERLY / FRAIL  (age ≥ 70 with ECOG ≥ 2) ──────────────────────
    if inp.age >= 70 and inp.ecog >= 2:
        out = (
            f"1 Disease Subsite\n"
            f"{subsite}\n\n"
            f"2 Risk Stratification\n"
            f"Competing mortality risk high\n\n"
            f"3 Primary Treatment\n"
            f"Radiation alone preferred\n\n"
            f"4 Treatment Goal\n"
            f"Function preservation\n"
            f"Quality of life"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return HNResult(
            formatted_output=out,
            confidence=Confidence.AMBER,
            flags=flags,
            mdt_required=True,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ── UNRESECTABLE ─────────────────────────────────────────────────────
    if not inp.resectable:
        flags.append("Unresectable oral cavity – non-standard pathway")
        out = (
            f"1 Disease Subsite\n"
            f"{subsite}\n\n"
            f"2 Stage\n"
            f"Stage {stage} | {t} {n}\n\n"
            f"3 Risk Stratification\n"
            f"Unresectable disease → high-risk pathway\n\n"
            f"4 Primary Treatment\n"
            f"Definitive concurrent chemoradiation\n\n"
            f"5 Radiotherapy\n"
            f"66–70 Gy / 33–35# to primary + bilateral neck\n"
            f"IMRT/VMAT mandatory\n\n"
            f"6 Chemotherapy\n"
            f"{chemo_line}\n\n"
            f"7 Rationale\n"
            f"Unresectable oral cavity disease managed with definitive CRT\n"
            f"Surgical feasibility reassessed post-treatment"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return HNResult(
            formatted_output=out,
            confidence=Confidence.AMBER,
            flags=flags,
            mdt_required=True,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ─────────────────────────────────────────────────────────────────────
    # POST-SURGERY pathways
    # ─────────────────────────────────────────────────────────────────────
    if inp.prior_surgery:

        # HIGH RISK — margins positive or ECE (Peters criteria)
        if inp.margins_positive or inp.ece_present:
            risk_factors = []
            if inp.margins_positive:
                risk_factors.append("Positive margins")
            if inp.ece_present:
                risk_factors.append("Extranodal extension (ENE)")

            out = (
                f"1 Disease Subsite\n"
                f"{subsite}\n\n"
                f"2 Risk Stratification\n"
                f"{chr(10).join(risk_factors)}\n"
                f"High risk of locoregional recurrence\n\n"
                f"3 Primary Treatment\n"
                f"Postoperative concurrent chemoradiation\n\n"
                f"4 Radiotherapy\n"
                f"PORT to primary bed + bilateral neck\n"
                f"Dose:\n"
                f"• High risk: 60 Gy / 30#\n"
                f"• Elective: 50–54 Gy\n\n"
                f"5 Chemotherapy\n"
                f"{chemo_line}\n\n"
                f"6 Rationale\n"
                f"High-risk pathology mandates concurrent chemoradiation\n"
                f"(RTOG 9501 / EORTC 22931 – Peters criteria)"
            )
            out += _footer(confidence, flags, mdt_required, PROTOCOL_VERSION)
            return HNResult(
                formatted_output=out,
                confidence=confidence,
                flags=flags,
                mdt_required=mdt_required,
                protocol_reference=PROTOCOL_VERSION,
            )

        # INTERMEDIATE RISK — PNI / LVI / pT3–T4 / multiple nodes
        if (
            inp.pni_present
            or inp.lvi_present
            or t in ("T3", "T4a", "T4b")
            or inp.multiple_positive_nodes
            or n in ("N1", "N2a", "N2b", "N2c", "N3")
        ):
            risk_factors = []
            if inp.pni_present:
                risk_factors.append("Perineural invasion (PNI)")
            if inp.lvi_present:
                risk_factors.append("Lymphovascular invasion (LVI)")
            if t in ("T3", "T4a", "T4b"):
                risk_factors.append(f"Advanced T-stage ({t})")
            if inp.multiple_positive_nodes or n in ("N2b", "N2c", "N3"):
                risk_factors.append("Multiple positive nodes")
            elif n == "N1":
                risk_factors.append("Node-positive")
            if inp.bone_invasion:
                risk_factors.append("Bone invasion")

            out = (
                f"1 Disease Subsite\n"
                f"{subsite}\n\n"
                f"2 Risk Stratification\n"
                f"{chr(10).join(risk_factors)}\n\n"
                f"3 Primary Treatment\n"
                f"Postoperative radiotherapy\n\n"
                f"4 Adjuvant Therapy\n"
                f"Postoperative radiotherapy\n\n"
                f"5 Radiotherapy\n"
                f"PORT to tumor bed + {'bilateral' if inp.bilateral_nodes or n == 'N2c' else 'ipsilateral'} neck\n"
                f"Dose: 60 Gy\n\n"
                f"6 Chemotherapy\n"
                f"Not mandatory (unless ENE / margins positive)\n\n"
                f"7 Rationale\n"
                f"{subsite} cancers have high local recurrence risk"
            )
            out += _footer(Confidence.AMBER, flags, False, PROTOCOL_VERSION)
            return HNResult(
                formatted_output=out,
                confidence=Confidence.AMBER,
                flags=flags,
                mdt_required=False,
                protocol_reference=PROTOCOL_VERSION,
            )

        # LOW RISK — observation
        out = (
            f"1 Disease Subsite\n"
            f"{subsite}\n\n"
            f"2 Stage\n"
            f"Stage {stage}\n\n"
            f"3 Risk Stratification\n"
            f"Margins negative\n"
            f"Node-negative\n"
            f"No adverse pathological features → Low risk\n\n"
            f"4 Primary Treatment\n"
            f"Observation\n\n"
            f"5 Adjuvant Therapy\n"
            f"Not indicated\n\n"
            f"6 Radiotherapy\n"
            f"Not indicated\n\n"
            f"7 Chemotherapy\n"
            f"Not indicated\n\n"
            f"8 Rationale\n"
            f"No Sedlis-equivalent or high-risk features\n\n"
            f"9 Follow-up\n"
            f"3-monthly × 2 years\n"
            f"Then 6-monthly"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return HNResult(
            formatted_output=out,
            confidence=Confidence.GREEN,
            flags=flags,
            mdt_required=False,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ─────────────────────────────────────────────────────────────────────
    # PRE-SURGERY pathways (surgery not yet done)
    # ─────────────────────────────────────────────────────────────────────

    # Determine risk tier for pre-op cases
    doi_high   = doi >= DOI_HIGH_RISK_THRESHOLD
    node_pos   = (n != "N0")
    adv_t      = (t in ("T3", "T4a", "T4b"))
    bone_inv   = inp.bone_invasion

    # ── VERY HIGH RISK: T4a + multiple nodes OR bone invasion + nodes ──
    if (t in ("T4a", "T4b") and n in ("N2a", "N2b", "N2c", "N3")) or \
       (bone_inv and node_pos):

        risk_str_parts = []
        if bone_inv:
            risk_str_parts.append("Bone invasion")
        if inp.bilateral_nodes or n in ("N2b", "N2c", "N3"):
            risk_str_parts.append("Multiple nodes → Very high risk")
        elif node_pos:
            risk_str_parts.append("Nodal disease → High risk")
        else:
            risk_str_parts.append("Advanced T-stage → High risk")

        out = (
            f"1 Disease Subsite\n"
            f"{subsite}\n\n"
            f"2 Risk Stratification\n"
            f"{chr(10).join(risk_str_parts)}\n\n"
            f"3 Primary Treatment\n"
            f"Surgery + adjuvant, unfit for surgery – chemoradiation\n\n"
            f"4 Adjuvant Therapy\n"
            f"Postoperative concurrent chemoradiation\n\n"
            f"5 Radiotherapy\n"
            f"Primary bed + {'bilateral' if inp.bilateral_nodes or n == 'N2c' else 'bilateral'} neck\n"
            f"Dose: 66 Gy (high-risk)\n\n"
            f"6 Chemotherapy\n"
            f"{chemo_line}\n\n"
            f"7 Rationale\n"
            f"High nodal burden → improved locoregional control with CCRT"
        )
        out += _footer(confidence, flags, mdt_required, PROTOCOL_VERSION)
        return HNResult(
            formatted_output=out,
            confidence=confidence,
            flags=flags,
            mdt_required=mdt_required,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ── HIGH RISK: T4a single node OR T3 + nodes OR bone invasion (N0) ──
    if (adv_t and node_pos) or (bone_inv and not node_pos) or \
       (t == "T4a" and n == "N0"):

        risk_str_parts = []
        if bone_inv:
            risk_str_parts.append("Bone invasion → high risk")
        if adv_t and node_pos:
            risk_str_parts.append("Deep invasion")
            risk_str_parts.append("Nodal disease")
            risk_str_parts.append("High risk of recurrence")
        elif adv_t:
            risk_str_parts.append(f"Advanced T-stage ({t})")

        rt_dose = "60–66 Gy" if not (inp.bilateral_nodes or n in ("N2c",)) else "66 Gy (high-risk)"
        neck_coverage = "bilateral neck" if (inp.bilateral_nodes or n in ("N2b", "N2c", "N3")) else "ipsilateral neck"

        out = (
            f"1 Disease Subsite\n"
            f"{subsite}\n\n"
            f"2 Risk Stratification\n"
            f"{chr(10).join(risk_str_parts)}\n\n"
            f"3 Primary Treatment\n"
            f"Surgery\n\n"
            f"4 Adjuvant Therapy\n"
            f"{'Postoperative concurrent chemoradiation' if node_pos else 'Postoperative radiotherapy'}\n\n"
            f"5 Radiotherapy\n"
            f"{'PORT to primary + ' + neck_coverage}\n"
            f"Dose:\n"
            f"• High risk: 60 Gy / 30#\n"
            f"• Elective: 50–54 Gy\n\n"
            f"6 Chemotherapy\n"
            f"{'Weekly cisplatin 40 mg/m²' if node_pos else 'Only if margins positive / ENE'}\n\n"
            f"7 Rationale\n"
            f"{'DOI + nodal disease → survival benefit with CCRT' if node_pos else 'Bone invasion upgrades stage irrespective of size'}"
        )
        out += _footer(confidence, flags, mdt_required, PROTOCOL_VERSION)
        return HNResult(
            formatted_output=out,
            confidence=confidence,
            flags=flags,
            mdt_required=mdt_required,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ── INTERMEDIATE RISK: T2 N1 OR DOI ≥ 10 mm OR advanced T node-neg ──
    if node_pos or doi_high or adv_t:

        risk_str_parts = []
        if node_pos:
            risk_str_parts.append(node_lbl)
        if adv_t:
            risk_str_parts.append("Muscle invasion" if t == "T3" else f"Advanced T-stage ({t})")
        if doi_high:
            risk_str_parts.append(f"DOI {doi:.0f} mm → high nodal risk")

        neck_coverage = "ipsilateral neck" if not (inp.bilateral_nodes or n in ("N2b", "N2c", "N3")) else "bilateral neck"

        out = (
            f"1 Disease Subsite\n"
            f"{subsite}\n\n"
            f"2 Risk Stratification\n"
            f"{chr(10).join(risk_str_parts)}\n\n"
            f"3 Primary Treatment\n"
            f"Surgery\n\n"
            f"4 Adjuvant Therapy\n"
            f"Postoperative radiotherapy\n\n"
            f"5 Radiotherapy\n"
            f"PORT to tumor bed + {neck_coverage}\n"
            f"Dose: 60 Gy\n\n"
            f"6 Chemotherapy\n"
            f"Not mandatory (unless ENE/margins positive)\n\n"
            f"7 Rationale\n"
            f"{subsite} cancers have high local recurrence risk"
        )
        out += _footer(Confidence.AMBER, flags, False, PROTOCOL_VERSION)
        return HNResult(
            formatted_output=out,
            confidence=Confidence.AMBER,
            flags=flags,
            mdt_required=False,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ── EARLY STAGE: T1–T2 N0 DOI < 10 mm ───────────────────────────────
    doi_stage_note = "DOI-driven" if doi < DOI_HIGH_RISK_THRESHOLD else "DOI elevated – monitor closely"
    doi_risk_line  = f"DOI {doi:.0f} mm" if doi > 0 else "DOI <10 mm"

    out = (
        f"1 Disease Subsite\n"
        f"{subsite}\n\n"
        f"2 Stage\n"
        f"Stage {stage} ({doi_stage_note})\n\n"
        f"3 Risk Stratification\n"
        f"{doi_risk_line}\n"
        f"Margins negative\n"
        f"Node-negative → Low–intermediate risk\n\n"
        f"4 Primary Treatment\n"
        f"Surgery\n\n"
        f"5 Adjuvant Therapy\n"
        f"Observation if margins clear and no adverse features\n\n"
        f"6 Radiotherapy\n"
        f"Indicated as per institutional protocol\n\n"
        f"7 Chemotherapy\n"
        f"Not indicated\n\n"
        f"8 Guideline Rationale\n"
        f"Surgery alone may be inadequate for early-stage {subsite.lower()} cancer\n"
        f"Adjuvant decision based on final pathology\n\n"
        f"9 Follow-up\n"
        f"3-monthly × 2 years\n"
        f"Then 6-monthly"
    )
    out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
    return HNResult(
        formatted_output=out,
        confidence=Confidence.GREEN,
        flags=flags,
        mdt_required=False,
        protocol_reference=PROTOCOL_VERSION,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Non-oral-cavity sub-engine (Oropharynx / Hypopharynx / Larynx)
# ─────────────────────────────────────────────────────────────────────────────

def _non_oral(inp: HNInput) -> HNResult:
    flags        = []
    confidence   = Confidence.GREEN
    mdt_required = False

    stage    = inp.ajcc_stage.value
    t        = inp.t_stage.value
    n        = inp.n_stage.value
    site_lbl = _subsite_label(inp)

    chemo_line, chemo_ineligible = _cisplatin_check(
        inp.creatinine_clearance, inp.hearing_adequate, flags
    )
    if chemo_ineligible:
        confidence   = Confidence.AMBER
        mdt_required = True

    if inp.primary_site.value == "oropharynx" and inp.p16_positive:
        flags.append("HPV/p16-positive – favourable biology; de-escalation trials only")

    # EARLY STAGE (I–II or T1-T2 N0)
    if stage in EARLY_STAGES or (t in EARLY_T_STAGES and n == "N0"):
        if not inp.resectable or inp.organ_preservation_preferred:
            out = (
                f"1 Disease Subsite\n"
                f"{site_lbl}\n\n"
                f"2 Stage\n"
                f"Stage {stage} | {t} {n}\n\n"
                f"3 Risk Stratification\n"
                f"Early-stage disease → organ preservation pathway\n\n"
                f"4 Primary Treatment\n"
                f"Definitive radiotherapy\n\n"
                f"5 Radiotherapy\n"
                f"66–70 Gy / 33–35# to primary\n"
                f"Elective neck 50–54 Gy (N0)\n"
                f"IMRT mandatory\n\n"
                f"6 Chemotherapy\n"
                f"Not routinely required for early-stage disease\n\n"
                f"7 Rationale\n"
                f"Definitive RT achieves excellent local control with function preservation\n\n"
                f"8 Follow-up\n"
                f"Clinical + endoscopy at 6–8 weeks\n"
                f"PET-CT at 12 weeks if N+\n"
                f"3-monthly × 2 years"
            )
            out += _footer(confidence, flags, mdt_required, PROTOCOL_VERSION)
            return HNResult(
                formatted_output=out, confidence=confidence,
                flags=flags, mdt_required=mdt_required,
                protocol_reference=PROTOCOL_VERSION,
            )
        else:
            out = (
                f"1 Disease Subsite\n"
                f"{site_lbl}\n\n"
                f"2 Stage\n"
                f"Stage {stage} | {t} {n}\n\n"
                f"3 Risk Stratification\n"
                f"Resectable early-stage → surgery or definitive RT\n\n"
                f"4 Primary Treatment\n"
                f"Surgery (transoral / open) with neck dissection\n"
                f"OR definitive RT if organ preservation preferred\n\n"
                f"5 Adjuvant Therapy\n"
                f"Based on post-surgical histopathology\n"
                f"• No adverse features → Observation\n"
                f"• ECE or positive margins → Adjuvant CRT\n\n"
                f"6 Radiotherapy (adjuvant)\n"
                f"60–66 Gy / 30–33# (high risk)\n"
                f"56–60 Gy / 28–30# (intermediate risk)\n\n"
                f"7 Rationale\n"
                f"Both surgery and RT are acceptable for resectable early-stage {site_lbl}\n\n"
                f"8 Follow-up\n"
                f"3-monthly × 2 years\n"
                f"Then 6-monthly"
            )
            out += _footer(confidence, flags, mdt_required, PROTOCOL_VERSION)
            return HNResult(
                formatted_output=out, confidence=confidence,
                flags=flags, mdt_required=mdt_required,
                protocol_reference=PROTOCOL_VERSION,
            )

    # LOCALLY ADVANCED (III–IVB)
    if stage in LOCALLY_ADVANCED_STAGES:

        # Post-surgery adjuvant
        if inp.prior_surgery and inp.resectable and not inp.organ_preservation_preferred:
            if inp.margins_positive or inp.ece_present:
                risk_factors = []
                if inp.margins_positive:
                    risk_factors.append("Positive margins")
                if inp.ece_present:
                    risk_factors.append("Extranodal extension (ENE)")
                out = (
                    f"1 Disease Subsite\n"
                    f"{site_lbl}\n\n"
                    f"2 Risk Stratification\n"
                    f"{chr(10).join(risk_factors)}\n"
                    f"High risk of recurrence\n\n"
                    f"3 Primary Treatment\n"
                    f"Postoperative concurrent chemoradiation\n\n"
                    f"4 Radiotherapy\n"
                    f"60–66 Gy / 30–33# to primary bed + bilateral neck\n"
                    f"IMRT/VMAT mandatory\n\n"
                    f"5 Chemotherapy\n"
                    f"{chemo_line}\n\n"
                    f"6 Rationale\n"
                    f"High-risk pathology mandates concurrent CRT\n"
                    f"(RTOG 9501 / EORTC 22931)"
                )
                out += _footer(confidence, flags, mdt_required, PROTOCOL_VERSION)
                return HNResult(
                    formatted_output=out, confidence=confidence,
                    flags=flags, mdt_required=mdt_required,
                    protocol_reference=PROTOCOL_VERSION,
                )

            if inp.pni_present or inp.lvi_present or inp.multiple_positive_nodes:
                risk_factors = []
                if inp.pni_present:
                    risk_factors.append("Perineural invasion (PNI)")
                if inp.lvi_present:
                    risk_factors.append("Lymphovascular invasion (LVI)")
                if inp.multiple_positive_nodes:
                    risk_factors.append("Multiple positive nodes")
                out = (
                    f"1 Disease Subsite\n"
                    f"{site_lbl}\n\n"
                    f"2 Risk Stratification\n"
                    f"{chr(10).join(risk_factors)}\n\n"
                    f"3 Primary Treatment\n"
                    f"Postoperative radiotherapy\n\n"
                    f"4 Radiotherapy\n"
                    f"56–60 Gy / 28–30# to operative bed + neck\n"
                    f"IMRT mandatory\n\n"
                    f"5 Chemotherapy\n"
                    f"Not required for intermediate-risk features alone\n\n"
                    f"6 Rationale\n"
                    f"Intermediate-risk factors warrant adjuvant RT for locoregional control"
                )
                out += _footer(Confidence.AMBER, flags, False, PROTOCOL_VERSION)
                return HNResult(
                    formatted_output=out, confidence=Confidence.AMBER,
                    flags=flags, mdt_required=False,
                    protocol_reference=PROTOCOL_VERSION,
                )

            # Low risk post-surgery
            out = (
                f"1 Disease Subsite\n"
                f"{site_lbl}\n\n"
                f"2 Risk Stratification\n"
                f"No adverse pathological features → Low risk\n\n"
                f"3 Primary Treatment\n"
                f"Observation\n\n"
                f"4 Adjuvant Therapy\n"
                f"Not indicated\n\n"
                f"5 Rationale\n"
                f"Absence of high-risk or intermediate-risk features\n\n"
                f"6 Follow-up\n"
                f"3-monthly × 2 years\n"
                f"Then 6-monthly"
            )
            out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
            return HNResult(
                formatted_output=out, confidence=Confidence.GREEN,
                flags=flags, mdt_required=False,
                protocol_reference=PROTOCOL_VERSION,
            )

        # Pre-surgery / definitive CRT
        if inp.resectable and not inp.organ_preservation_preferred:
            out = (
                f"1 Disease Subsite\n"
                f"{site_lbl}\n\n"
                f"2 Stage\n"
                f"Stage {stage} | {t} {n}\n\n"
                f"3 Risk Stratification\n"
                f"Locally advanced resectable → surgery-first\n\n"
                f"4 Primary Treatment\n"
                f"Surgery + bilateral neck dissection\n\n"
                f"5 Adjuvant Therapy\n"
                f"Determined by final pathology:\n"
                f"• No adverse features → Observation\n"
                f"• Intermediate risk (PNI/LVI/multiple nodes) → Adjuvant RT\n"
                f"• High risk (positive margins / ENE) → Concurrent CRT\n\n"
                f"6 Radiotherapy (adjuvant)\n"
                f"60–66 Gy / 30–33# (CRT) OR 56–60 Gy / 28–30# (RT alone)\n"
                f"IMRT/VMAT mandatory\n\n"
                f"7 Rationale\n"
                f"Surgery first is preferred for resectable locally advanced {site_lbl}\n\n"
                f"8 Follow-up\n"
                f"3-monthly × 2 years\n"
                f"Then 6-monthly"
            )
            out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
            return HNResult(
                formatted_output=out, confidence=Confidence.GREEN,
                flags=flags, mdt_required=False,
                protocol_reference=PROTOCOL_VERSION,
            )

        # Unresectable / organ preservation → definitive CRT
        reason = "Organ preservation approach" if inp.organ_preservation_preferred else "Unresectable disease"
        out = (
            f"1 Disease Subsite\n"
            f"{site_lbl}\n\n"
            f"2 Stage\n"
            f"Stage {stage} | {t} {n}\n\n"
            f"3 Treatment Rationale\n"
            f"{reason} → Definitive chemoradiation\n\n"
            f"4 Primary Treatment\n"
            f"Definitive concurrent chemoradiation\n\n"
            f"5 Radiotherapy\n"
            f"66–70 Gy / 33–35# to primary + involved nodes (SIB)\n"
            f"54–56 Gy elective nodal volumes\n"
            f"IMRT/VMAT mandatory; IGRT recommended\n\n"
            f"6 Chemotherapy\n"
            f"{chemo_line}\n\n"
            f"7 Rationale\n"
            f"Definitive CRT is standard of care for unresectable / organ-preservation HNSCC\n"
            f"(MACH-NC meta-analysis; RTOG 91-11)\n\n"
            f"8 Follow-up\n"
            f"PET-CT at 12 weeks post RT\n"
            f"Clinical exam 2–3 monthly × 2 years"
        )
        out += _footer(confidence, flags, mdt_required, PROTOCOL_VERSION)
        return HNResult(
            formatted_output=out, confidence=confidence,
            flags=flags, mdt_required=mdt_required,
            protocol_reference=PROTOCOL_VERSION,
        )

    # Fallback within non-oral
    flags.append("Outside standard pathway – MDT required")
    out = (
        f"1 Disease Subsite\n"
        f"{site_lbl}\n\n"
        f"2 Stage\n"
        f"Stage {stage} | {t} {n}\n\n"
        f"3 Risk Stratification\n"
        f"Case does not fit a standard decision branch\n\n"
        f"4 Primary Treatment\n"
        f"MDT discussion required\n\n"
        f"5 Rationale\n"
        f"Individualised management needed"
    )
    out += _footer(Confidence.RED, flags, True, PROTOCOL_VERSION)
    return HNResult(
        formatted_output=out, confidence=Confidence.RED,
        flags=flags, mdt_required=True,
        protocol_reference=PROTOCOL_VERSION,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_hn_case(inp: HNInput) -> HNResult:

    stage = inp.ajcc_stage.value
    t     = inp.t_stage.value
    n     = inp.n_stage.value
    flags = []

    # ── STEP 1: Poor performance status ──────────────────────────────────
    if inp.ecog >= 3:
        site_lbl = _subsite_label(inp)
        out = (
            f"1 Disease Subsite\n"
            f"{site_lbl}\n\n"
            f"2 Risk Stratification\n"
            f"ECOG {inp.ecog} → unfit for standard chemoradiation\n\n"
            f"3 Primary Treatment\n"
            f"Palliative radiotherapy OR best supportive care\n\n"
            f"4 Treatment Goal\n"
            f"Symptom control\n"
            f"Quality of life"
        )
        out += _footer(Confidence.RED, ["Poor performance status – ECOG ≥ 3"], True, PROTOCOL_VERSION)
        return HNResult(
            formatted_output=out, confidence=Confidence.RED,
            flags=["Poor performance status – ECOG ≥ 3"],
            mdt_required=True, protocol_reference=PROTOCOL_VERSION,
        )

    # ── STEP 2: Metastatic (IVC / M1) ────────────────────────────────────
    if stage == "IVC" or inp.distant_metastasis:
        site_lbl = _subsite_label(inp)
        out = (
            f"1 Disease Subsite\n"
            f"{site_lbl}\n\n"
            f"2 Treatment Intent\n"
            f"Palliative\n\n"
            f"3 Primary Treatment\n"
            f"Platinum-based chemotherapy\n"
            f"± Pembrolizumab (PD-L1 / CPS-guided)\n\n"
            f"4 Radiotherapy\n"
            f"Palliative RT for bleeding / pain / airway compromise\n\n"
            f"5 Treatment Goal\n"
            f"Symptom control\n"
            f"Quality of life\n\n"
            f"6 Follow-up\n"
            f"Response-based; symptom-oriented review"
        )
        out += _footer(Confidence.AMBER, ["Metastatic disease – IVC / M1"], True, PROTOCOL_VERSION)
        return HNResult(
            formatted_output=out, confidence=Confidence.AMBER,
            flags=["Metastatic disease – IVC / M1"],
            mdt_required=True, protocol_reference=PROTOCOL_VERSION,
        )

    # ── STEP 3: Post-RT residual nodal disease ────────────────────────────
    if inp.post_rt_residual_nodes:
        site_lbl = _subsite_label(inp)
        out = (
            f"1 Disease Subsite\n"
            f"{site_lbl}\n\n"
            f"2 Evaluation\n"
            f"PET-CT at 12 weeks post RT recommended\n"
            f"Confirm persistent viable nodal disease\n\n"
            f"3 Management\n"
            f"Salvage neck dissection (selected cases)\n"
            f"MDT discussion mandatory before proceeding\n\n"
            f"4 Rationale\n"
            f"Residual nodal disease post-RT requires histological confirmation\n"
            f"Salvage dissection is standard for isolated nodal persistence"
        )
        out += _footer(Confidence.RED, ["Post-RT residual nodal disease – urgent MDT required"], True, PROTOCOL_VERSION)
        return HNResult(
            formatted_output=out, confidence=Confidence.RED,
            flags=["Post-RT residual nodal disease – urgent MDT required"],
            mdt_required=True, protocol_reference=PROTOCOL_VERSION,
        )

    # ── STEP 4: Recurrent disease ─────────────────────────────────────────
    if inp.recurrent_disease:
        site_lbl = _subsite_label(inp)
        flags_r  = []
        chemo_line, chemo_ineligible = _cisplatin_check(
            inp.creatinine_clearance, inp.hearing_adequate, flags_r
        )
        conf_r = Confidence.AMBER if chemo_ineligible else Confidence.GREEN
        mdt_r  = True

        if not inp.prior_rt:
            out = (
                f"1 Disease Subsite\n"
                f"{site_lbl}\n\n"
                f"2 Risk Stratification\n"
                f"Recurrent disease – no prior RT\n\n"
                f"3 Primary Treatment\n"
                f"Definitive RT ± concurrent chemotherapy\n\n"
                f"4 Radiotherapy\n"
                f"60–66 Gy / 30–33# to recurrent site\n\n"
                f"5 Chemotherapy\n"
                f"{chemo_line}\n\n"
                f"6 Rationale\n"
                f"No prior RT allows full-dose re-treatment\n\n"
                f"7 Follow-up\n"
                f"PET-CT at 12 weeks post RT"
            )
            out += _footer(conf_r, flags_r, mdt_r, PROTOCOL_VERSION)
            return HNResult(
                formatted_output=out, confidence=conf_r,
                flags=flags_r, mdt_required=mdt_r,
                protocol_reference=PROTOCOL_VERSION,
            )
        else:
            flags_r.append("Prior RT – re-irradiation carries high toxicity risk")
            out = (
                f"1 Disease Subsite\n"
                f"{site_lbl}\n\n"
                f"2 Risk Stratification\n"
                f"Recurrent disease – prior RT in field\n\n"
                f"3 Options\n"
                f"• Salvage surgery (if resectable)\n"
                f"• Re-irradiation (specialist centre only)\n"
                f"• Systemic therapy / immunotherapy\n\n"
                f"4 Radiotherapy\n"
                f"Re-irradiation: IMRT / Proton with strict dose constraints\n\n"
                f"5 Rationale\n"
                f"Prior irradiation substantially elevates re-treatment toxicity risk"
            )
            out += _footer(Confidence.RED, flags_r, True, PROTOCOL_VERSION)
            return HNResult(
                formatted_output=out, confidence=Confidence.RED,
                flags=flags_r, mdt_required=True,
                protocol_reference=PROTOCOL_VERSION,
            )

    # ── STEP 5: Symptomatic / palliative ─────────────────────────────────
    # GUARD: only enter this branch when there is genuinely no curative pathway.
    # Routine symptoms (dysphagia, pain on swallowing) are expected in resectable
    # curative-intent cases and must NOT redirect to palliative RT.
    # Palliative RT is only appropriate when the case is unresectable AND/OR
    # the stage is IVB (no systemic curative option remains).
    _no_curative_pathway = (not inp.resectable) or (stage == "IVB")
    if inp.symptomatic_bleeding_or_pain and _no_curative_pathway:
        site_lbl = _subsite_label(inp)
        out = (
            f"1 Disease Subsite\n"
            f"{site_lbl}\n\n"
            f"2 Stage\n"
            f"Stage {stage} | {t} {n}\n\n"
            f"3 Risk Stratification\n"
            f"Active symptoms → urgent palliation\n\n"
            f"4 Primary Treatment\n"
            f"Palliative radiotherapy\n\n"
            f"5 Radiotherapy\n"
            f"Short-course palliative RT (20 Gy / 5# or 30 Gy / 10#)\n\n"
            f"6 Chemotherapy\n"
            f"Not indicated for palliative RT alone\n\n"
            f"7 Rationale\n"
            f"Symptom control is the priority"
        )
        out += _footer(Confidence.AMBER, [], False, PROTOCOL_VERSION)
        return HNResult(
            formatted_output=out, confidence=Confidence.AMBER,
            flags=[], mdt_required=False,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ── STEP 6: Route to site-specific sub-engines ────────────────────────
    if inp.primary_site.value == "oral_cavity":
        return _oral_cavity(inp)
    else:
        return _non_oral(inp)