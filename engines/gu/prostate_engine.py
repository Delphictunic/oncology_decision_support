"""
Production-Ready Prostate Cancer Clinical Decision Support Engine
Institutional GU Cancers Protocol v1.0 | AJCC 8th Edition

Decision tree covers:
  • Localized disease: Low / Favorable-IR / Unfavorable-IR / High / Very-High risk
  • Node-positive (Stage IVA)
  • Post-radical prostatectomy: adjuvant vs salvage RT
  • Metastatic hormone-sensitive (mHSPC)
  • Non-metastatic CRPC (nmCRPC)
  • Metastatic CRPC (mCRPC)

IMPORTANT: Decision-support only. All outputs require clinical judgment.
Cases flagged RED require MDT discussion before treatment.
"""

from .prostate_models import ProstateInput, ProstateResult, Confidence, ProstateMStage, ProstateOverallStage
from .prostate_config import (
    PROTOCOL_VERSION,
    CASTRATE_T_THRESHOLD,
    HIGH_RISK_PSADT_THRESHOLD,
    BCR_PSA_THRESHOLD,
    GRADE_GROUP_LABELS,
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


def _gleason_label(grade_group: int) -> str:
    return GRADE_GROUP_LABELS.get(grade_group, f"Grade Group {grade_group}")


def _is_metastatic(inp: ProstateInput) -> bool:
    return inp.m_stage in (ProstateMStage.M1A, ProstateMStage.M1B, ProstateMStage.M1C) \
        or inp.overall_stage == ProstateOverallStage.IVB


def _is_crpc(inp: ProstateInput) -> bool:
    """True if patient meets CRPC criteria: castrate testosterone + PSA rising on ADT."""
    return (
        inp.on_adt
        and inp.psa_rising_on_adt
        and inp.castrate_testosterone is not None
        and inp.castrate_testosterone < CASTRATE_T_THRESHOLD
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sub-engines by clinical scenario
# ─────────────────────────────────────────────────────────────────────────────

def _poor_ps(inp: ProstateInput) -> ProstateResult:
    out = (
        "1 Disease Subsite\n"
        "Prostate\n\n"
        "2 Risk Stratification\n"
        f"ECOG {inp.ecog} – unfit for standard therapy\n\n"
        "3 Primary Treatment\n"
        "Best supportive care / palliative intent\n\n"
        "4 Radiotherapy\n"
        "Palliative RT only if symptomatic (e.g. bone pain, bleeding)\n"
        "Short-course schedules preferred\n\n"
        "5 ADT\n"
        "Consider if hormone-sensitive and patient agrees\n\n"
        "6 Rationale\n"
        "Poor performance status precludes standard treatment protocols\n"
        "MDT review and palliative care integration essential\n\n"
        "7 Follow-up\n"
        "Symptom-based; palliative care referral"
    )
    out += _footer(Confidence.RED, [f"ECOG {inp.ecog} – poor performance status"], True, PROTOCOL_VERSION)
    return ProstateResult(
        formatted_output=out, confidence=Confidence.RED,
        flags=[f"ECOG {inp.ecog} – poor performance status"],
        mdt_required=True, protocol_reference=PROTOCOL_VERSION,
    )


def _mcrpc(inp: ProstateInput) -> ProstateResult:
    """Metastatic Castration-Resistant Prostate Cancer."""
    flags = ["Metastatic castration-resistant prostate cancer – MDT required"]
    lines = []

    # Sequencing based on prior therapies
    if not inp.prior_arpi and not inp.prior_docetaxel:
        first_line = (
            "First-line options (chemo-naive):\n"
            "• Abiraterone acetate + prednisolone (COU-AA-302)\n"
            "• Enzalutamide (PREVAIL)\n"
            "• Docetaxel 75 mg/m² q3w × 10 cycles (TAX 327)"
        )
        lines.append(first_line)
    elif inp.prior_arpi and not inp.prior_docetaxel:
        lines.append(
            "Post-ARPI options:\n"
            "• Docetaxel 75 mg/m² q3w × 10 cycles (TAX 327)\n"
            "• Cabazitaxel (if post-docetaxel)\n"
            "• Lutetium-177 PSMA-617 if PSMA PET-positive (VISION)"
        )
    elif inp.prior_docetaxel and not inp.prior_arpi:
        lines.append(
            "Post-docetaxel options:\n"
            "• Abiraterone or Enzalutamide\n"
            "• Cabazitaxel (TROPIC)\n"
            "• Lutetium-177 PSMA-617 if PSMA-positive (VISION)"
        )
    else:
        lines.append(
            "Post-ARPI + post-docetaxel:\n"
            "• Cabazitaxel (TROPIC)\n"
            "• Lutetium-177 PSMA-617 if PSMA-positive (VISION)\n"
            "• Clinical trial strongly recommended"
        )

    # Targeted therapy
    targeted = []
    if inp.psma_positive:
        targeted.append("Lutetium-177 PSMA-617 (VISION trial) – PSMA PET-positive confirmed")
    if inp.brca_mutation:
        targeted.append("Olaparib / Niraparib (PROfound trial) – HRR mutation present")
        flags.append("BRCA mutation – PARP inhibitor eligible")
    if inp.msi_high:
        targeted.append("Pembrolizumab (KEYNOTE-199) – MSI-high / dMMR")
        flags.append("MSI-high – immunotherapy eligible")
    if inp.bone_only_mets and not inp.visceral_mets:
        targeted.append("Radium-223 dichloride if symptomatic bone-only mets (ALSYMPCA) – no visceral mets")

    targeted_str = "\n".join(f"• {t}" for t in targeted) if targeted else "• No specific targeted therapy identified"

    rt_str = (
        "Palliative RT for symptomatic bone lesions\n"
        "• 8 Gy / 1# (single fraction) or 20 Gy / 5# for pain\n"
        "• 30 Gy / 10# for weight-bearing sites at fracture risk\n"
        "• Spinal cord compression: urgent RT / surgical decompression"
        if inp.symptomatic_bone_mets
        else "Palliative RT as needed for symptomatic sites"
    )

    gg_label = _gleason_label(inp.grade_group)
    t_str = inp.castrate_testosterone
    t_display = f"{t_str:.1f} ng/dL" if t_str is not None else "< 50 ng/dL (confirmed castrate)"

    out = (
        "1 Disease Status\n"
        "Metastatic castration-resistant prostate cancer (mCRPC)\n\n"
        "2 Disease Characterisation\n"
        f"Stage {inp.overall_stage.value} | {inp.t_stage.value} {inp.n_stage.value} {inp.m_stage.value}\n"
        f"PSA: {inp.psa} ng/mL | Grade Group {inp.grade_group} ({gg_label})\n"
        f"Testosterone: {t_display}\n"
        f"Metastatic pattern: {'Bone-only' if inp.bone_only_mets and not inp.visceral_mets else 'Visceral involvement' if inp.visceral_mets else 'Bone ± lymph node'}\n"
        f"Prior ARPI: {'Yes' if inp.prior_arpi else 'No'} | Prior docetaxel: {'Yes' if inp.prior_docetaxel else 'No'}\n\n"
        "3 Treatment Options\n"
        + "\n".join(lines) + "\n\n"
        "4 Targeted / Precision Therapy\n"
        + targeted_str + "\n\n"
        "5 Radiotherapy\n"
        + rt_str + "\n\n"
        "6 Rationale\n"
        "Continue ADT lifelong (castrate testosterone maintenance essential)\n"
        "Sequence ARPIs and chemotherapy per MDT; avoid re-challenging same class\n"
        "Annual bone health: zoledronic acid or denosumab if no prior\n\n"
        "7 Follow-up\n"
        "PSA + testosterone every 3 months\n"
        "Bone scan / CT every 3–6 months or at clinical progression\n"
        "Multidisciplinary team review at each progression event"
    )
    out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
    return ProstateResult(
        formatted_output=out, confidence=Confidence.AMBER,
        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
    )


def _nmcrpc(inp: ProstateInput) -> ProstateResult:
    """Non-Metastatic Castration-Resistant Prostate Cancer."""
    flags = ["Non-metastatic CRPC identified"]
    psadt = inp.psadt_months

    if psadt is not None and psadt < HIGH_RISK_PSADT_THRESHOLD:
        risk_label = f"High risk (PSADT {psadt:.1f} months – < 10 months)"
        treatment = (
            "Add second-generation ARPI + continue ADT:\n"
            "• Apalutamide (SPARTAN trial – OS benefit)\n"
            "• Enzalutamide (PROSPER trial – OS benefit)\n"
            "• Darolutamide (ARAMIS trial – OS benefit, fewer CNS AEs)"
        )
        confidence = Confidence.GREEN
        flags.append("PSADT < 10 months – high risk for metastasis; ARPI indicated")
    elif psadt is not None:
        risk_label = f"Lower risk (PSADT {psadt:.1f} months – ≥ 10 months)"
        treatment = (
            "Observation + continue ADT\n"
            "Close monitoring with conventional imaging every 6 months\n"
            "PSMA PET-CT may identify early occult metastases"
        )
        confidence = Confidence.GREEN
    else:
        risk_label = "PSADT not provided – assume high-risk nmCRPC for safety"
        treatment = (
            "Consider adding second-generation ARPI (PSADT assessment recommended):\n"
            "• Apalutamide / Enzalutamide / Darolutamide + continue ADT"
        )
        confidence = Confidence.AMBER
        flags.append("PSADT not provided – full risk stratification incomplete")

    t_str = inp.castrate_testosterone
    t_display = f"{t_str:.1f} ng/dL" if t_str is not None else "< 50 ng/dL"

    out = (
        "1 Disease Status\n"
        "Non-metastatic castration-resistant prostate cancer (nmCRPC)\n\n"
        "2 CRPC Characterisation\n"
        f"PSA: {inp.psa} ng/mL (rising on ADT)\n"
        f"Testosterone: {t_display} (castrate level)\n"
        f"Conventional imaging: No distant metastasis\n"
        f"PSA risk profile: {risk_label}\n\n"
        "3 Treatment\n"
        f"{treatment}\n\n"
        "4 Radiotherapy\n"
        "Not indicated (no metastases on conventional imaging)\n"
        "PSMA PET-CT: Consider if available to detect early oligometastatic disease\n\n"
        "5 Rationale\n"
        "SPARTAN, PROSPER, ARAMIS: all three ARPIs improved MFS and OS\n"
        "PSADT < 10 months strongly predicts rapid metastatic evolution\n"
        "Continue ADT throughout as backbone therapy\n\n"
        "6 Follow-up\n"
        "PSA every 3 months\n"
        "Conventional imaging (bone scan + CT) every 6 months\n"
        "PSMA PET-CT if PSA rises significantly or new symptoms develop"
    )
    out += _footer(confidence, flags, len([f for f in flags if "MDT" in f]) > 0, PROTOCOL_VERSION)
    return ProstateResult(
        formatted_output=out, confidence=confidence,
        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION,
    )


def _mhspc(inp: ProstateInput) -> ProstateResult:
    """Metastatic Hormone-Sensitive Prostate Cancer."""
    flags = ["Metastatic hormone-sensitive prostate cancer – MDT recommended"]

    m = inp.m_stage.value
    metastatic_site = (
        "Bone-only" if inp.bone_only_mets and not inp.visceral_mets
        else "Visceral + bone" if inp.visceral_mets
        else "Lymph node ± bone"
    )
    volume = "Low-volume" if inp.low_volume_mets else "High-volume"

    # RT to prostate in low-volume mHSPC (STAMPEDE benefit)
    rt_str = (
        "RT to prostate recommended (STAMPEDE: OS benefit in low-volume M1)\n"
        "• Dose: 55 Gy / 20# (hypofractionated) or 36 Gy / 6# (SBRT)\n"
        "• Target: Prostate ± proximal seminal vesicles\n"
        "Palliative RT for symptomatic bone sites: 8 Gy / 1# or 20 Gy / 5#"
        if inp.low_volume_mets
        else "Palliative RT for symptomatic bone metastases: 8 Gy / 1# or 20 Gy / 5#\n"
             "RT to prostate primary not recommended in high-volume disease (STAMPEDE)"
    )

    out = (
        "1 Disease Status\n"
        "Metastatic hormone-sensitive prostate cancer (mHSPC)\n\n"
        "2 Disease Characterisation\n"
        f"Stage {inp.overall_stage.value} | PSA: {inp.psa} ng/mL\n"
        f"Grade Group {inp.grade_group} ({_gleason_label(inp.grade_group)})\n"
        f"Metastatic site: {metastatic_site} | Volume: {volume}\n\n"
        "3 Primary Treatment\n"
        "ADT + androgen receptor pathway inhibitor (doublet / triplet therapy)\n\n"
        "4 Options\n"
        "Doublet (ADT + one of):\n"
        "• Abiraterone acetate + prednisolone (LATITUDE, STAMPEDE)\n"
        "• Enzalutamide (ENZAMET)\n"
        "• Apalutamide (TITAN)\n"
        "• Docetaxel 75 mg/m² × 6 cycles (CHAARTED, STAMPEDE) – high-volume, fit patients\n"
        "Triplet (ADT + Docetaxel + ARPI):\n"
        "• ADT + Docetaxel + Darolutamide (ARASENS – OS benefit without added toxicity)\n\n"
        "5 Radiotherapy\n"
        f"{rt_str}\n\n"
        "6 Rationale\n"
        "Combination ADT + ARPI improves OS vs ADT alone (LATITUDE, TITAN, ENZAMET)\n"
        "Docetaxel preferred in high-volume, fit patients (CHAARTED: high-volume OS benefit)\n"
        "Bone-protective therapy: zoledronic acid or denosumab + calcium + vitamin D\n\n"
        "7 Follow-up\n"
        "PSA + testosterone every 3 months\n"
        "Imaging (bone scan + CT) every 6 months or at clinical progression\n"
        "Monitor for castration resistance: PSA kinetics + imaging"
    )
    out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
    return ProstateResult(
        formatted_output=out, confidence=Confidence.AMBER,
        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
    )


def _node_positive(inp: ProstateInput) -> ProstateResult:
    """Stage IVA – N1 M0: node-positive localized/locally advanced."""
    flags = ["Node-positive disease (N1) – MDT discussion recommended"]

    out = (
        "1 Disease Subsite\n"
        "Prostate – Node-positive (Stage IVA)\n\n"
        "2 Risk Stratification\n"
        f"Node-positive | PSA {inp.psa} ng/mL | Grade Group {inp.grade_group} ({_gleason_label(inp.grade_group)})\n"
        f"T-stage: {inp.t_stage.value} N1 M0\n\n"
        "3 Primary Treatment\n"
        "Definitive RT + long-term ADT (preferred over surgery alone)\n"
        "OR pelvic lymph node dissection → adjuvant RT + ADT if pN1\n\n"
        "4 Radiotherapy\n"
        "Target: Prostate + seminal vesicles + pelvic lymph nodes\n"
        "Prostate dose: 76–80 Gy / 38–40# (conventional)\n"
        "OR 60 Gy / 20# with SIB to prostate (CHHiP-adapted)\n"
        "Pelvic LN dose: 45–50.4 Gy / 25–28#\n"
        "Technique: IMRT/VMAT mandatory; IGRT recommended\n"
        "CTV: Prostate + full SV + obturator, ext/int iliac, presacral LN (RTOG 0924)\n\n"
        "5 ADT\n"
        "Long-term: 2–3 years (EORTC 22961, DART 01/05)\n"
        "Start ADT 2–3 months prior to RT (neoadjuvant component)\n\n"
        "6 Rationale\n"
        "SPCG-7: RT + ADT superior to ADT alone in locally advanced/node+ disease\n"
        "STAMPEDE: pelvic RT + ADT improves failure-free survival in N1 setting\n\n"
        "7 Follow-up\n"
        "PSA every 3 months during ADT, then every 6 months\n"
        "Testosterone recovery monitoring after ADT completion\n"
        "Annual bone density (DEXA) during long-term ADT"
    )
    out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
    return ProstateResult(
        formatted_output=out, confidence=Confidence.GREEN,
        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION,
    )


def _post_rp(inp: ProstateInput) -> ProstateResult:
    """Post-radical prostatectomy: adjuvant RT vs salvage RT decision."""
    flags = []
    post_psa = inp.post_rp_psa if inp.post_rp_psa is not None else 0.0

    # Identify high-risk pathological features
    path_risk = []
    if inp.margin_positive:
        path_risk.append("Positive surgical margins (R1)")
    if inp.seminal_vesicle_invasion:
        path_risk.append("Seminal vesicle invasion (pT3b)")
    if inp.ece_present:
        path_risk.append("Extracapsular extension (pT3a)")
    if inp.ln_positive_post_rp:
        path_risk.append("Lymph node positive (pN1)")
        flags.append("pN1 at RP – pelvic RT + long-term ADT indicated")
    if inp.grade_group >= 4:
        path_risk.append(f"High-grade disease: Grade Group {inp.grade_group}")

    path_risk_str = "\n".join(f"• {f}" for f in path_risk) if path_risk else "• No adverse pathological features identified"

    # BCR / PSA state
    is_bcr = post_psa >= BCR_PSA_THRESHOLD
    is_persistent_psa = post_psa > 0.0 and not is_bcr

    # ── Biochemical recurrence (PSA ≥ 0.2) ───────────────────────────────
    if is_bcr:
        flags.append(f"Biochemical recurrence: PSA {post_psa:.2f} ng/mL (≥ 0.2 threshold)")
        adt_str = (
            "ADT + salvage RT (RTOG 0534/SPPORT: pelvic RT + 6 months ADT improves PFS)\n"
            "• Duration: 6 months minimum; 2 years if high-risk features (pT3b, GG ≥4, pN1)\n"
            "• Consider bicalutamide or GnRH agonist/antagonist"
            if (inp.grade_group >= 4 or inp.seminal_vesicle_invasion or inp.ln_positive_post_rp)
            else "ADT with salvage RT: 6 months total (RTOG 0534)\n"
                 "• Recommended for PSA > 0.5 or rapidly rising PSA"
        )
        pelvic_rt = (
            "Include pelvic lymph nodes in salvage RT (RTOG 0534/SPPORT)\n"
            "• Pelvic LN: 45 Gy; prostate bed: 64–66 Gy"
            if (inp.ln_positive_post_rp or inp.grade_group >= 4 or inp.seminal_vesicle_invasion)
            else "Prostate bed only (consider pelvic LN if Gleason ≥8 or pT3b)"
        )
        confidence = Confidence.GREEN
        treatment_rec = (
            "Salvage RT to prostate bed ± pelvic lymph nodes\n"
            "(Early salvage RT preferred when PSA < 0.5 for best outcomes)"
        )
    # ── Persistent low PSA (not quite BCR but not undetectable) ──────────
    elif is_persistent_psa:
        flags.append(f"Persistent PSA post-RP: {post_psa:.2f} ng/mL – possible residual disease")
        treatment_rec = "Early salvage RT to prostate bed (PSA persistent – likely residual local disease)"
        adt_str = "Consider short-course ADT 6 months alongside early SRT"
        pelvic_rt = "Prostate bed ± pelvic LN (assess imaging before decision)"
        confidence = Confidence.AMBER
    # ── Undetectable PSA but high-risk pathology ──────────────────────────
    else:
        treatment_rec = (
            "Observation with early salvage RT trigger at PSA ≥ 0.2 ng/mL\n"
            "(RADICALS-RT, RAVES, GETUG-AFU 17: early SRT ≥ ART in outcomes; avoids overtreatment)\n"
            "Immediate adjuvant RT reserved for very high-risk selected cases after MDT discussion"
            if path_risk
            else "Observation – no adverse pathological features; RT not indicated"
        )
        adt_str = (
            "Not indicated for observation phase\n"
            "Initiate at SRT if PSA trigger met and high-risk features present"
            if path_risk
            else "Not indicated"
        )
        pelvic_rt = (
            "Include pelvic LN at time of salvage RT if pN1 or high-risk features (RTOG 0534)"
            if (inp.ln_positive_post_rp or inp.grade_group >= 4)
            else "Prostate bed alone unless high-risk triggers develop"
        )
        confidence = Confidence.GREEN if not path_risk else Confidence.AMBER

    out = (
        "1 Disease Status\n"
        "Post-radical prostatectomy\n\n"
        "2 Pathological Risk Features\n"
        f"{path_risk_str}\n\n"
        "3 Treatment Recommendation\n"
        f"{treatment_rec}\n\n"
        "4 Radiotherapy\n"
        f"Target: Prostate bed (vesicourethral anastomosis → apex of prostate, ESTRO-ACROP 2021)\n"
        f"Dose: 64–66 Gy / 33–34# (conventional) or 52.5–55 Gy / 20–25# (hypofractionated)\n"
        f"Pelvic LN: {pelvic_rt}\n"
        "Technique: IMRT/VMAT; IGRT recommended\n\n"
        "5 ADT\n"
        f"{adt_str}\n\n"
        "6 Rationale\n"
        "RADICALS-RT / RAVES / GETUG-AFU 17 / ARTISTIC meta-analysis:\n"
        "Early salvage RT = adjuvant RT in long-term outcomes; avoids overtreatment in undetectable PSA\n"
        "RTOG 0534 (SPPORT): salvage RT + ADT + pelvic LN → best PFS in BCR setting\n\n"
        "7 Follow-up\n"
        "PSA every 3 months for 2 years, then every 6 months\n"
        "Testosterone recovery if ADT used (monitor annually)\n"
        "PSMA PET-CT at BCR trigger for localisation before salvage RT"
    )
    out += _footer(confidence, flags, bool([f for f in flags if "MDT" in f or "pN1" in f]), PROTOCOL_VERSION)
    return ProstateResult(
        formatted_output=out, confidence=confidence,
        flags=flags, mdt_required=bool([f for f in flags if "pN1" in f]),
        protocol_reference=PROTOCOL_VERSION,
    )


def _localized(inp: ProstateInput) -> ProstateResult:
    """Localized prostate cancer: Low / Intermediate / High / Very High risk."""
    flags = []
    stage = inp.overall_stage.value
    psa   = inp.psa
    gg    = inp.grade_group
    t     = inp.t_stage.value

    gg_label = _gleason_label(gg)

    # ── LOW RISK: Stage I ──────────────────────────────────────────────────
    if stage == "I":
        out = (
            "1 Disease Subsite\n"
            "Prostate\n\n"
            "2 Risk Stratification\n"
            "Low risk\n"
            f"(PSA <10, {gg_label}, T1–T2a)\n\n"
            "3 Primary Treatment Options\n"
            "Active surveillance / Surgery / Radiotherapy\n\n"
            "4 Preferred Approach\n"
            "Active surveillance (PIVOT, ProtecT trials: no OS benefit from immediate treatment)\n\n"
            "5 Radiotherapy\n"
            "If chosen: 74–78 Gy / 37–39# (conventional)\n"
            "OR 60 Gy / 20# (moderate hypofractionation – CHHiP; non-inferior)\n"
            "OR 36.25 Gy / 5# (SBRT – PACE-B; safe; long-term data awaited)\n"
            "Technique: IMRT; image-guided RT (IGRT) recommended\n\n"
            "6 ADT\n"
            "Not indicated\n\n"
            "7 Rationale\n"
            "Indolent disease – avoid overtreatment\n"
            "Active surveillance validated with PIVOT, ProtecT, PRIAS registry\n"
            "Surgery / RT equally effective; patient preference guides choice\n\n"
            "8 Follow-up\n"
            "PSA every 6 months\n"
            "Annual DRE\n"
            "Repeat MRI / biopsy if PSA doubling or grade reclassification"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return ProstateResult(
            formatted_output=out, confidence=Confidence.GREEN,
            flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION,
        )

    # ── FAVORABLE INTERMEDIATE RISK: Stage IIA ────────────────────────────
    if stage == "IIA":
        out = (
            "1 Disease Subsite\n"
            "Prostate\n\n"
            "2 Risk Stratification\n"
            "Intermediate risk – Favorable\n"
            f"(PSA 10–20 ng/mL, Grade Group 1, T1–T2)\n\n"
            "3 Primary Treatment\n"
            "Radical prostatectomy / Radiotherapy\n"
            "(Both are equivalent; patient preference and comorbidity guide choice)\n\n"
            "4 Preferred Approach\n"
            "Definitive RT – dose-escalated or moderate hypofractionation\n\n"
            "5 Radiotherapy\n"
            "76–80 Gy / 38–40# (conventional – RTOG 0126: dose escalation benefit)\n"
            "OR 60 Gy / 20# (moderate hypofractionation – CHHiP, PROFIT: equivalent)\n"
            "Technique: IMRT/VMAT; IGRT mandatory\n"
            "CTV: Prostate ± SV base (favorable IR – omit SV if Gleason ≤6, PSA <10)\n\n"
            "6 ADT\n"
            "Optional for favorable intermediate-risk (NRG/RTOG 0815: no OS benefit)\n"
            "If used: 4–6 months (short-term neoadjuvant + concurrent)\n\n"
            "7 Rationale\n"
            "Dose escalation improves biochemical control (RTOG 0126)\n"
            "Short-term ADT: limited added benefit in strictly favorable IR (RTOG 0815)\n"
            "RT vs surgery: equivalent outcomes; surgeon expertise and patient factors decide\n\n"
            "8 Follow-up\n"
            "PSA every 3–6 months for 2 years, then annually\n"
            "Testosterone recovery monitoring if ADT used"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return ProstateResult(
            formatted_output=out, confidence=Confidence.GREEN,
            flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION,
        )

    # ── UNFAVORABLE INTERMEDIATE RISK: Stage IIB / IIC ───────────────────
    if stage in ("IIB", "IIC"):
        # Stage IIC with GG4 behaves closer to high-risk
        is_gg4_in_iic = (stage == "IIC" and gg >= 4)
        adt_dur = "Long-term: 2–3 years" if is_gg4_in_iic else "Short-term: 4–6 months"
        adt_rationale = (
            "Grade Group 4 in Stage IIC approaches high-risk behaviour; long-term ADT recommended (EORTC 22961)"
            if is_gg4_in_iic
            else "Short-term ADT improves biochemical control in unfavorable IR (RTOG 0815, DART 01/05)"
        )
        if is_gg4_in_iic:
            flags.append("Grade Group 4 in Stage IIC – consider treating as high-risk; MDT review")

        out = (
            "1 Disease Subsite\n"
            "Prostate\n\n"
            "2 Risk Stratification\n"
            f"Intermediate risk – Unfavorable\n"
            f"(PSA {psa} ng/mL, {gg_label}, {t})\n\n"
            "3 Primary Treatment\n"
            "Radical prostatectomy / Radiotherapy\n\n"
            "4 Preferred Approach\n"
            "Definitive RT + ADT preferred for unfavorable intermediate-risk\n\n"
            "5 Radiotherapy\n"
            "76–80 Gy / 38–40# (conventional)\n"
            "OR 60 Gy / 20# (moderate hypofractionation – CHHiP/PROFIT: non-inferior)\n"
            "Technique: IMRT/VMAT; IGRT mandatory\n"
            "CTV: Prostate + SV base (proximal 1–2 cm; ESTRO guidelines)\n"
            "Elective pelvic LN RT: optional if nodal risk > 15–20% (RTOG 0924 criteria)\n\n"
            "6 ADT\n"
            f"{adt_dur} (RTOG 0815, DART 01/05)\n"
            f"Initiate 2–3 months neoadjuvant, then concurrent + short adjuvant\n\n"
            "7 Rationale\n"
            f"{adt_rationale}\n"
            "ASCENDE-RT: brachytherapy boost improves biochemical control but more GU toxicity\n"
            "Surgery: acceptable if patient fit; adjuvant therapy based on final pathology\n\n"
            "8 Follow-up\n"
            "PSA every 3 months for 2 years, then every 6 months\n"
            "Testosterone monitoring after ADT completion"
        )
        out += _footer(
            Confidence.AMBER if is_gg4_in_iic else Confidence.GREEN,
            flags,
            is_gg4_in_iic,
            PROTOCOL_VERSION,
        )
        return ProstateResult(
            formatted_output=out,
            confidence=Confidence.AMBER if is_gg4_in_iic else Confidence.GREEN,
            flags=flags, mdt_required=is_gg4_in_iic, protocol_reference=PROTOCOL_VERSION,
        )

    # ── HIGH RISK: Stage IIIA / IIIB ─────────────────────────────────────
    if stage in ("IIIA", "IIIB"):
        is_t3b_t4 = inp.t_stage.value in ("T3b", "T4")
        pelvic_ln_note = (
            "Pelvic LN RT: Recommended (nodal risk > 15–20%)\n"
            "Dose: 45–50.4 Gy / 25–28# to pelvic LN volumes (RTOG 0924)"
        )
        out = (
            "1 Disease Subsite\n"
            "Prostate\n\n"
            "2 Risk Stratification\n"
            "High risk\n"
            f"(PSA {psa} ng/mL, {gg_label}, {t})\n\n"
            "3 Primary Treatment\n"
            "Radiotherapy + long-term ADT (preferred)\n"
            "OR Surgery + multimodality therapy (selected cases with cT3a, fit patients)\n\n"
            "4 Radiotherapy\n"
            "Prostate + SV: 76–80 Gy / 38–40# (conventional – RTOG 0126)\n"
            "OR 60 Gy / 20# (moderate hypo – CHHiP: non-inferior in intermediate/high risk)\n"
            "Technique: IMRT/VMAT mandatory; IGRT essential\n"
            f"CTV: Prostate + full seminal vesicles\n"
            f"{pelvic_ln_note}\n\n"
            "5 ADT\n"
            "2–3 years (EORTC 22961: 36 months ADT improves OS; DART 01/05: confirmed)\n"
            "Initiate 2–3 months neoadjuvant, concurrent + long adjuvant\n"
            "GnRH agonist/antagonist + anti-androgen flare prophylaxis\n\n"
            "6 Rationale\n"
            "Improves OS and DFS vs RT alone (EORTC 22961, SPCG-7/SFUO-3)\n"
            "SPCG-7: adding RT to ADT improved 10-year OS by 12%\n"
            "Surgery alone inadequate for T3b/T4; adjuvant RT + ADT likely required\n\n"
            "7 Follow-up\n"
            "PSA every 3 months during ADT, then every 6 months × 5 years, then annually\n"
            "Testosterone: check at ADT cessation; monitor recovery\n"
            "Annual DEXA scan during long-term ADT (osteoporosis prevention)\n"
            "Calcium + vitamin D supplementation throughout ADT"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return ProstateResult(
            formatted_output=out, confidence=Confidence.GREEN,
            flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION,
        )

    # ── VERY HIGH RISK: Stage IIIC (Grade Group 5) ────────────────────────
    if stage == "IIIC":
        flags.append("Grade Group 5 (Gleason 9–10) – very high-risk; MDT discussion recommended")
        out = (
            "1 Disease Subsite\n"
            "Prostate\n\n"
            "2 Risk Stratification\n"
            "Very high risk\n"
            f"(Grade Group 5 – {gg_label}, PSA {psa} ng/mL, {t})\n\n"
            "3 Primary Treatment\n"
            "Radiotherapy + long-term ADT (standard)\n"
            "Consider multimodal: RT + ADT ± abiraterone (STAMPEDE: abiraterone + RT + ADT)\n\n"
            "4 Radiotherapy\n"
            "Prostate + full SV + pelvic LN: 76–78 Gy prostate; 45–50.4 Gy pelvic LN\n"
            "Technique: IMRT/VMAT mandatory; IGRT essential\n"
            "FLAME technique: dose-painting boost to intraprostatic lesion (95 Gy; FLAME trial)\n\n"
            "5 ADT\n"
            "Long-term: 2–3 years\n"
            "Consider abiraterone + ADT + RT (STAMPEDE arm: improved OS in high-risk localized)\n\n"
            "6 Rationale\n"
            "STAMPEDE (abiraterone arm): abiraterone + ADT + RT improved failure-free survival\n"
            "GG5 has highest local recurrence risk; aggressive therapy warranted\n"
            "MDT review for surgery vs RT decision in selected fit patients\n\n"
            "7 Follow-up\n"
            "PSA every 3 months for 3 years, then every 6 months\n"
            "PSMA PET-CT if PSA failure to localise recurrence\n"
            "Annual DEXA; bone-protective therapy during long-term ADT"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return ProstateResult(
            formatted_output=out, confidence=Confidence.AMBER,
            flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
        )

    # Fallback
    flags.append("Stage not classified – MDT required")
    out = (
        "1 Disease Subsite\n"
        "Prostate\n\n"
        "2 Risk Stratification\n"
        f"Unclassified – Stage {stage}\n\n"
        "3 Primary Treatment\n"
        "MDT discussion required\n\n"
        "4 Rationale\n"
        "Case does not fit a standard decision tree pathway"
    )
    out += _footer(Confidence.RED, flags, True, PROTOCOL_VERSION)
    return ProstateResult(
        formatted_output=out, confidence=Confidence.RED,
        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_prostate_case(inp: ProstateInput) -> ProstateResult:
    """Run the full prostate cancer decision tree and return a formatted result."""

    # ── STEP 1: Poor performance status ───────────────────────────────────
    if inp.ecog >= 3:
        return _poor_ps(inp)

    is_met = _is_metastatic(inp)
    is_cr  = _is_crpc(inp)

    # ── STEP 2: Metastatic CRPC ───────────────────────────────────────────
    if is_cr and is_met:
        return _mcrpc(inp)

    # ── STEP 3: Non-metastatic CRPC ───────────────────────────────────────
    if is_cr and not is_met:
        return _nmcrpc(inp)

    # ── STEP 4: Metastatic hormone-sensitive ──────────────────────────────
    if is_met:
        return _mhspc(inp)

    # ── STEP 5: Node-positive (Stage IVA) ────────────────────────────────
    if inp.n_stage.value == "N1" and not is_met:
        return _node_positive(inp)

    # ── STEP 6: Post-radical prostatectomy ───────────────────────────────
    if inp.prior_rp:
        return _post_rp(inp)

    # ── STEP 7: Localized disease (risk-group based) ──────────────────────
    return _localized(inp)
