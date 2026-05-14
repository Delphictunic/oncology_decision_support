"""
Breast Cancer Clinical Decision Support Engine
Implements the Institutional Breast Cancer Decision Tree (AJCC 8th edition staging).
Steps 1-6 from the decision tree, with Step 7 output formatting.

IMPORTANT: This is a decision-SUPPORT tool. All recommendations require clinical judgment.
Cases flagged as "red" confidence MUST go through MDT discussion.
"""

from breast_models import BreastInput, BreastResult, Confidence
from breast_config import OUTPUT_TEMPLATE, PROTOCOL_REFERENCE, LUMINAL_A_KI67_THRESHOLD


# ── T and N stage helpers ──────────────────────────────────────────────────

T_STAGE_ORDER = {
    "Tis": 0, "T0": 0,
    "T1": 1, "T1a": 1, "T1b": 1, "T1c": 1, "T1mi": 1,
    "T2": 2,
    "T3": 3,
    "T4": 4, "T4a": 4, "T4b": 4, "T4c": 4, "T4d": 4,
}

N_STAGE_ORDER = {
    "N0": 0, "N0(i+)": 0,
    "N1": 1, "N1a": 1, "N1b": 1, "N1c": 1, "N1mi": 1,
    "N2": 2, "N2a": 2, "N2b": 2,
    "N3": 3, "N3a": 3, "N3b": 3, "N3c": 3,
}


def _t_value(stage: str) -> int:
    """Return numeric T value (0-4). Accepts pT or cT prefix."""
    s = stage.replace("p", "").replace("c", "")
    return T_STAGE_ORDER.get(s, -1)


def _n_value(stage: str) -> int:
    """Return numeric N value (0-3). Accepts pN or cN prefix."""
    s = stage.replace("p", "").replace("c", "")
    return N_STAGE_ORDER.get(s, -1)


def _is_early_t(t_stage: str) -> bool:
    """Check if T stage is early (T0-T2)."""
    v = _t_value(t_stage)
    return 0 <= v <= 2


def _is_node_positive(n_stage: str) -> bool:
    """Check if N stage indicates node involvement (N1+)."""
    return _n_value(n_stage) >= 1


def _overall_stage_numeric(stage: str) -> int:
    """Map overall stage string to a number for comparison."""
    s = stage.upper().strip()
    mapping = {
        "0": 0, "IA": 1, "IB": 1, "I": 1,
        "IIA": 2, "IIB": 2, "II": 2,
        "IIIA": 3, "IIIB": 3, "IIIC": 3, "III": 3,
        "IV": 4,
    }
    return mapping.get(s, -1)


def _is_luminal_a(
    er: str,
    pr: str,
    her2: str,
    grade: int,
    ki67_percent: float | None,
) -> bool:
    """True if tumor fits Luminal A: ER/PR+, HER2-, low Ki-67, low grade."""
    if er != "positive" or pr != "positive" or her2 != "negative":
        return False
    ki = ki67_percent if ki67_percent is not None else 99
    if ki > LUMINAL_A_KI67_THRESHOLD:
        return False
    return grade <= 2


# ── Main engine ───────────────────────────────────────────────────────────

def evaluate_breast_case(case: BreastInput) -> BreastResult:
    """
    Run the full decision tree (Steps 1-6) and return structured result.
    
    Args:
        case: BreastInput — validated clinical case data
    
    Returns:
        BreastResult — formatted recommendation, confidence, flags, MDT flag, protocol reference
    """
    
    flags: list[str] = []
    recommendations: list[str] = []
    reasoning_parts: list[str] = []
    confidence = Confidence.GREEN
    mdt_required = False
    
    # ── Extract and normalize values ──
    age = case.age
    sex = case.sex.value.lower()
    ecog = case.ecog
    menopausal_status = case.menopausal_status.value.lower()
    
    laterality = case.laterality.value.lower()
    histology_lower = case.histology.value.lower()
    tumor_size_cm = case.tumor_size_cm
    grade = case.grade
    lvi = case.lvi
    
    n_stage = case.n_stage.upper().strip()
    nodes_examined = case.nodes_examined
    nodes_positive = case.nodes_positive
    m_stage = case.m_stage.upper().strip()
    
    er = case.er_status.value.lower()
    pr = case.pr_status.value.lower()
    her2 = case.her2_status.value.lower()
    
    t_stage = case.t_stage.upper().strip()
    overall_stage = case.overall_stage.upper().strip()
    
    surgery_done = case.surgery_done
    surgery_t = case.surgery_type.value.upper() if case.surgery_type else "NONE"
    margin = case.margin_status.value.lower() if case.margin_status else "unknown"
    
    quadrant = case.quadrant.value.lower()
    ki67_percent = case.ki67_percent
    neoadjuvant_chemo = case.neoadjuvant_chemo
    chemo_resp = case.chemo_response.value.lower()
    extracapsular_extension = case.extracapsular_extension
    imn_involvement = case.imn_involvement
    scf_involvement = case.scf_involvement
    symptomatic_metastasis = case.symptomatic_metastasis
    brca_mutation = case.brca_mutation
    
    # ── Derive molecular classification ──
    is_triple_negative = (er == "negative" and pr == "negative" and her2 == "negative")
    is_hr_positive = (er == "positive" or pr == "positive")
    is_her2_positive = (her2 == "positive")
    overall_numeric = _overall_stage_numeric(overall_stage)
    node_positive = _is_node_positive(n_stage) or nodes_positive > 0
    is_luminal_a = _is_luminal_a(er, pr, her2, grade, ki67_percent)
    
    if is_triple_negative:
        mol_subtype = "Triple Negative"
    elif is_her2_positive and is_hr_positive:
        mol_subtype = "Luminal B (HER2+)"
    elif is_her2_positive:
        mol_subtype = "HER2-enriched"
    elif is_hr_positive:
        mol_subtype = "Luminal A" if is_luminal_a else "Luminal B (HER2-)"
    else:
        mol_subtype = "Unclassified"
    
    # ── Build case summary ──
    meno_label = "premenopausal" if "pre" in menopausal_status else (
        "perimenopausal" if "peri" in menopausal_status else "postmenopausal"
    )
    sex_label = "woman" if sex == "female" else "man"
    
    case_summary = (
        f"{age}-year-old {meno_label} {sex_label} with {laterality} breast "
        f"{histology_lower}, {t_stage}{n_stage}{m_stage}, Grade {grade}, "
        f"ER {'+'  if er == 'positive' else '-'}/PR {'+'  if pr == 'positive' else '-'}/HER2 {'+'  if her2 == 'positive' else '-'}"
        f"{f', Ki-67 {ki67_percent}%' if ki67_percent is not None else ''}"
        f". Molecular subtype: {mol_subtype}."
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 1: BASIC ELIGIBILITY CHECK (Rule 1)
    # ═══════════════════════════════════════════════════════════════════════
    
    is_invasive = histology_lower in (
        "invasive ductal carcinoma", "idc",
        "invasive lobular carcinoma", "ilc",
        "invasive ductal ca", "invasive carcinoma",
        "other",
    )
    
    if not is_invasive:
        flags.append("Non-invasive histology – MDT discussion required")
        mdt_required = True
        confidence = Confidence.RED
    
    if ecog > 2:
        flags.append("ECOG > 2 – MDT discussion required")
        mdt_required = True
        confidence = Confidence.RED
    
    if not is_invasive or ecog > 2:
        if not is_invasive and ecog > 2:
            reasoning = "Patient has non-invasive histology and poor performance status (ECOG > 2). MDT discussion required."
        elif not is_invasive:
            reasoning = "Non-invasive histology (DCIS or LCIS) — standard decision tree does not apply. MDT discussion required."
        else:
            reasoning = f"ECOG {ecog} — treatment tolerance uncertain. MDT discussion required."
        
        reasoning_parts.append(reasoning)
        recommendations.append("MDT discussion required")
        
        return BreastResult(
            formatted_output=OUTPUT_TEMPLATE.format(
                case_summary=case_summary,
                primary_recommendation="; ".join(recommendations),
                reasoning=reasoning,
                surgery_recommendation="See MDT",
                systemic_therapy="See MDT",
                radiation_therapy="See MDT",
                follow_up="See MDT",
            ),
            confidence=confidence,
            flags=flags,
            mdt_required=mdt_required,
            protocol_reference=PROTOCOL_REFERENCE,
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 2: METASTATIC DISEASE (Rule 2A)
    # ═══════════════════════════════════════════════════════════════════════
    
    if m_stage == "M1" or symptomatic_metastasis:
        recommendations.append("Metastatic disease – systemic therapy + supportive care")
        reasoning_parts.append(f"Stage IV disease ({m_stage})")
        confidence = Confidence.AMBER
        mdt_required = True
        flags.append("Metastatic disease – MDT required")
        
        systemic_parts = []
        if is_triple_negative:
            systemic_parts.append("Chemotherapy: platinum-based (consider capecitabine if visceral metastases)")
            if brca_mutation:
                systemic_parts.append("PARP inhibitor (olaparib) per protocol")
        elif is_her2_positive:
            systemic_parts.append("Chemotherapy + trastuzumab ± pertuzumab")
        elif is_hr_positive:
            systemic_parts.append("Endocrine therapy ± chemotherapy (per symptoms, visceral involvement)")
        
        rt_detail = "Palliative RT to symptomatic sites; CNS screening if indicated"
        follow_up_m1 = "Multidisciplinary coordination; symptom-guided imaging"
        
        return BreastResult(
            formatted_output=OUTPUT_TEMPLATE.format(
                case_summary=case_summary,
                primary_recommendation="; ".join(recommendations),
                reasoning="; ".join(reasoning_parts),
                surgery_recommendation="Per MDT",
                systemic_therapy="; ".join(systemic_parts) if systemic_parts else "Per MDT",
                radiation_therapy=rt_detail,
                follow_up=follow_up_m1,
            ),
            confidence=confidence,
            flags=flags,
            mdt_required=mdt_required,
            protocol_reference=PROTOCOL_REFERENCE,
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 3A: POST-BCS (Rules 2A, 2B)
    # ═══════════════════════════════════════════════════════════════════════
    
    if surgery_t in ("BCS", "LUMPECTOMY"):
        reasoning_parts.append(f"Post-BCS, {t_stage}{n_stage}{m_stage}")
        
        # ── Margin assessment ──
        boost = False
        rt_detail = ""
        
        if margin == "negative":
            recommendations.append("Whole breast irradiation")
            reasoning_parts.append(f"Negative margins post-BCS")
            boost = not is_luminal_a or grade >= 3 or node_positive or age < 50
            
            rt_detail = f"Whole breast RT indicated if BCS.\nDose: 50 Gy / 25 fractions\nTechnique: 3DCRT"
            
            if is_luminal_a:
                rt_detail = f"Whole breast RT indicated if BCS.\nDose: 40 Gy / 15 fractions or 50 Gy / 25 fractions.\nTechnique: 3DCRT"
            
            if boost and not is_luminal_a:
                rt_detail += "\nBoost: tumor bed boost recommended"
            elif boost and is_luminal_a:
                rt_detail += "\nBoost to tumor bed if age <50 or grade ≥3 or close margins"
            
            if laterality == "left":
                rt_detail += "\nOAR: Heart mean dose < 4 Gy (DIBH advised)"
        
        elif margin == "positive":
            recommendations.append("Re-excision recommended; then WBI")
            flags.append("Positive margins – re-excision needed")
            confidence = Confidence.AMBER
            reasoning_parts.append("Positive margins after BCS – re-excision recommended")
            rt_detail = "WBI after re-excision achieves negative margins"
        
        else:
            recommendations.append("Whole breast irradiation")
            rt_detail = "Adjuvant WBI"
        
        # ── Systemic therapy for early stage ──
        systemic_parts = []
        if is_luminal_a:
            systemic_parts.append("Chemotherapy: not routinely indicated")
            if age < 40:
                systemic_parts.append("Consider genomic assay (e.g. CANASSIST) due to age <40 to confirm chemo omission")
            if node_positive:
                systemic_parts.append("Genomic testing strongly recommended (node-positive Luminal A)")
            elif not node_positive and tumor_size_cm <= 2 and grade <= 1 and "post" in menopausal_status:
                systemic_parts.append("Genomic testing not required (very low risk, screen-detected type)")
            elif not node_positive:
                systemic_parts.append("Genomic testing recommended (node-negative, ER+, HER2-) to confirm chemo omission")
            
            if "pre" in menopausal_status:
                systemic_parts.append("Endocrine: Tamoxifen × 5–10 years; consider ovarian suppression + AI if high-risk on genomic testing")
            else:
                systemic_parts.append("Endocrine: Aromatase inhibitor × 5 years (Tamoxifen if AI contraindicated)")
        
        elif is_hr_positive:
            if "pre" in menopausal_status:
                systemic_parts.append("Endocrine therapy: Tamoxifen")
            else:
                systemic_parts.append("Endocrine therapy: Aromatase inhibitor")
            if node_positive or grade >= 3 or tumor_size_cm > 2:
                systemic_parts.append("Chemotherapy: consider based on genomic assay")
            else:
                systemic_parts.append("Chemotherapy: not indicated")
        
        elif is_triple_negative:
            systemic_parts.append("Adjuvant chemotherapy: Anthracycline + taxane (dose-dense AC followed by dose-dense paclitaxel)")
            if brca_mutation:
                systemic_parts.append("Consider platinum-based regimen; consider PARP inhibitor (olaparib) if high-risk")
        
        elif is_her2_positive:
            systemic_parts.append("Paclitaxel weekly × 12 + Trastuzumab to complete 1 year (consider de-escalated regimen per APT trial if small node-negative)")
        
        # ── Regional nodal irradiation (Step 4) ──
        if node_positive or scf_involvement or imn_involvement:
            rni_parts = ["Axillary", "Supraclavicular"]
            if imn_involvement or quadrant in ("central", "upper inner", "lower inner"):
                rni_parts.append("IMN")
            rni_detail = f"\nRegional nodal irradiation: {' + '.join(rni_parts)}"
            rt_detail += rni_detail
            reasoning_parts.append("RNI indicated (node-positive or nodal involvement)")
        
        follow_up_bcs = "Clinical exam every 6 months, annual mammogram"
        if is_luminal_a and "post" in menopausal_status:
            follow_up_bcs = "Annual mammography; clinical exam every 6–12 months; bone health monitoring (AI)"
        
        return BreastResult(
            formatted_output=OUTPUT_TEMPLATE.format(
                case_summary=case_summary,
                primary_recommendation="; ".join(recommendations),
                reasoning="; ".join(reasoning_parts),
                surgery_recommendation="BCS completed",
                systemic_therapy="; ".join(systemic_parts) if systemic_parts else "Not indicated",
                radiation_therapy=rt_detail,
                follow_up=follow_up_bcs,
            ),
            confidence=confidence,
            flags=flags,
            mdt_required=mdt_required,
            protocol_reference=PROTOCOL_REFERENCE,
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # STEP 3B: POST-MASTECTOMY (Rules 2B, 2C)
    # ═══════════════════════════════════════════════════════════════════════
    
    if surgery_t in ("MRM", "MASTECTOMY"):
        reasoning_parts.append(f"Post-MRM, {t_stage}{n_stage}")
        
        if not node_positive:
            # Rule 2B: PMRT Node Negative
            high_risk = []
            if tumor_size_cm > 5:
                high_risk.append("tumor > 5 cm")
            if lvi:
                high_risk.append("LVI present")
            if margin in ("close", "positive"):
                high_risk.append(f"{margin} margins")
            
            if high_risk:
                recommendations.append("PMRT recommended (high-risk features)")
                flags.append(f"Node-negative but high-risk features: {', '.join(high_risk)} – MDT discussion")
                confidence = Confidence.AMBER
                mdt_required = True
                reasoning_parts.append(f"High-risk features despite N0: {', '.join(high_risk)}")
                
                rt_detail = (
                    "PMRT indicated (high-risk features)\n"
                    "Target: Chest wall\n"
                    "Dose: 50 Gy / 25 fractions\n"
                    "Technique: 3DCRT"
                )
            else:
                recommendations.append("No RT indicated")
                reasoning_parts.append("Post-MRM, node-negative, no high-risk features – no RT")
                rt_detail = "No RT indicated"
        
        else:
            # Rule 2C: PMRT Node Positive
            recommendations.append("Chest wall + Regional nodal irradiation")
            reasoning_parts.append("Node-positive post-MRM – PMRT with RNI indicated")
            
            rni_parts = ["SCF", "Axilla level II-III"]
            if imn_involvement or quadrant in ("central", "upper inner", "lower inner"):
                rni_parts.append("IMN")
            
            rt_detail = (
                "PMRT indicated\n"
                f"Targets: Chest wall + {' + '.join(rni_parts)}\n"
                "Dose: 50 Gy / 25 fractions\n"
                "Technique: 3DCRT"
            )
        
        if laterality == "left":
            rt_detail += "\nOAR: DIBH advised; heart mean dose < 4 Gy"
        
        # ── Systemic therapy ──
        systemic_parts = []
        if is_luminal_a:
            if node_positive:
                systemic_parts.append("Chemotherapy: Docetaxel + Cyclophosphamide × 4 cycles")
                systemic_parts.append("Genomic testing strongly recommended (RxPONDER: chemo benefit limited in postmenopausal, selective in premenopausal)")
                if "pre" in menopausal_status or "peri" in menopausal_status:
                    systemic_parts.append("Endocrine: Ovarian suppression + AI (preferred) or Tamoxifen if low risk")
                else:
                    systemic_parts.append("Endocrine: Aromatase inhibitor")
            else:
                systemic_parts.append("Chemotherapy: not indicated")
                if "pre" in menopausal_status:
                    systemic_parts.append("Endocrine: Tamoxifen × 5–10 years")
                else:
                    systemic_parts.append("Endocrine: Aromatase inhibitor × 5 years (Tamoxifen if AI contraindicated)")
        
        elif is_hr_positive:
            if "pre" in menopausal_status:
                systemic_parts.append("Endocrine therapy: Tamoxifen")
            else:
                systemic_parts.append("Endocrine therapy: Aromatase inhibitor")
            if node_positive or grade >= 3 or tumor_size_cm > 2:
                if is_her2_positive:
                    systemic_parts.append("Chemotherapy + trastuzumab ± pertuzumab (T-DM1 if residual after neoadjuvant)")
                elif is_triple_negative:
                    systemic_parts.append("Chemotherapy: dose-dense AC + paclitaxel; capecitabine if residual after NACT")
                elif is_hr_positive:
                    systemic_parts.append("Chemotherapy: consider based on risk")
        
        if is_her2_positive and "trastuzumab" not in str(systemic_parts):
            systemic_parts.append("Trastuzumab")
        
        follow_up_mrm = "Clinical exam every 6 months, annual mammogram"
        if is_luminal_a and node_positive:
            follow_up_mrm = "Clinical exam every 6 months × 5 years; annual imaging"
        
        return BreastResult(
            formatted_output=OUTPUT_TEMPLATE.format(
                case_summary=case_summary,
                primary_recommendation="; ".join(recommendations),
                reasoning="; ".join(reasoning_parts),
                surgery_recommendation=f"{surgery_t} completed",
                systemic_therapy="; ".join(systemic_parts) if systemic_parts else "Not indicated",
                radiation_therapy=rt_detail,
                follow_up=follow_up_mrm,
            ),
            confidence=confidence,
            flags=flags,
            mdt_required=mdt_required,
            protocol_reference=PROTOCOL_REFERENCE,
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # FALLBACK — should not normally reach here
    # ═══════════════════════════════════════════════════════════════════════
    
    return BreastResult(
        formatted_output=OUTPUT_TEMPLATE.format(
            case_summary=case_summary,
            primary_recommendation="MDT discussion required – unable to determine recommendation",
            reasoning="Case parameters did not match standard decision tree pathways",
            surgery_recommendation="See MDT",
            systemic_therapy="See MDT",
            radiation_therapy="See MDT",
            follow_up="See MDT",
        ),
        confidence=Confidence.RED,
        flags=["Unclassified case – MDT required"],
        mdt_required=True,
        protocol_reference=PROTOCOL_REFERENCE,
    )