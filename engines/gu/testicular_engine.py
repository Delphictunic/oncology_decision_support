"""
Production-Ready Testicular Cancer Clinical Decision Support Engine
Institutional GU Cancers Protocol v1.0

Decision tree covers:
  Seminoma:
    • Stage 0 (pTis) – GCNIS
    • Stage I (IA/IB) – surveillance vs adjuvant carboplatin vs RT
    • Stage II (IIA/IIB/IIC) – RT vs BEP chemotherapy
    • Stage III – IGCCCG risk-based BEP chemotherapy
  NSGCT / Mixed GCT:
    • Stage IA – surveillance vs BEP × 1 vs RPLND
    • Stage IB – BEP × 2 or RPLND
    • Stage IS – BEP × 3 (persistent markers)
    • Stage II – RPLND ± chemo vs BEP × 3–4
    • Stage III – IGCCCG risk-based BEP/VIP chemotherapy
  Post-chemotherapy residual management:
    • Seminoma < 3 cm → Observe; ≥ 3 cm → PET-CT / resection
    • NSGCT ≥ 1 cm → RPLND

IMPORTANT: Decision-support only. All outputs require clinical judgment.
"""

from .testicular_models import (
    TesticularInput, TesticularResult, Confidence,
    TesticularHistology, TesticularMStage, IGCCCGRisk, SStage,
)
from .testicular_config import (
    PROTOCOL_VERSION,
    SEMINOMA_RESIDUAL_THRESHOLD_CM,
    NSGCT_RESIDUAL_THRESHOLD_CM,
    RT_PA_DOSE_GY, RT_PA_FRACTIONS,
    RT_STAGE_II_DOSE_GY, RT_STAGE_II_FRAC,
    PA_FIELD, DOG_LEG_FIELD,
    S_STAGE_TO_IGCCCG,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _footer(confidence: Confidence, flags: list, mdt_required: bool, protocol: str) -> str:
    flag_str = ", ".join(flags) if flags else "None"
    return (
        f"\nConfidence → {confidence.value}\n"
        f"Flags → {flag_str}\n"
        f"MDT Required → {mdt_required}\n"
        f"Protocol Reference → {protocol}"
    )


def _is_metastatic(inp: TesticularInput) -> bool:
    return inp.m_stage in (TesticularMStage.M1A, TesticularMStage.M1B)


def _resolve_igcccg(inp: TesticularInput) -> IGCCCGRisk:
    """Compute IGCCCG risk from s_stage + histology + metastatic features."""
    if inp.igcccg_risk:
        return inp.igcccg_risk

    hist = inp.histology
    s    = inp.s_stage.value

    # Seminoma: max = intermediate (no poor risk category)
    if hist == TesticularHistology.SEMINOMA:
        if inp.non_pulmonary_visceral_mets:
            return IGCCCGRisk.INTERMEDIATE
        return IGCCCGRisk.GOOD  # all seminoma without non-pulm visceral mets = good

    # NSGCT / Mixed
    if inp.mediastinal_primary or inp.non_pulmonary_visceral_mets or s == "S3":
        return IGCCCGRisk.POOR
    if s == "S2":
        return IGCCCGRisk.INTERMEDIATE
    return IGCCCGRisk.GOOD


def _bep_regimen(igcccg: IGCCCGRisk, histology: TesticularHistology) -> str:
    """Return BEP/VIP regimen string based on IGCCCG risk."""
    if histology == TesticularHistology.SEMINOMA:
        # Seminoma: good or intermediate only
        if igcccg == IGCCCGRisk.GOOD:
            return (
                "BEP × 3 cycles OR EP × 4 cycles\n"
                "• Bleomycin 30 IU days 1, 8, 15 + Etoposide 100 mg/m² days 1–5 "
                "+ Cisplatin 20 mg/m² days 1–5; q21d (BEP × 3)\n"
                "• OR Etoposide + Cisplatin × 4 cycles (EP; if bleomycin contraindicated)"
            )
        return (
            "BEP × 4 cycles\n"
            "• Bleomycin + Etoposide + Cisplatin q21d × 4 cycles"
        )

    # NSGCT / Mixed
    if igcccg == IGCCCGRisk.GOOD:
        return (
            "BEP × 3 cycles OR EP × 4 cycles (bleomycin-sparing if pulmonary risk)\n"
            "• BEP: Bleomycin 30 IU d1,8,15 + Etoposide 100 mg/m² d1–5 + Cisplatin 20 mg/m² d1–5; q21d\n"
            "• EP: Etoposide 100 mg/m² d1–5 + Cisplatin 20 mg/m² d1–5; q21d × 4"
        )
    if igcccg == IGCCCGRisk.INTERMEDIATE:
        return (
            "BEP × 4 cycles OR VIP × 4 cycles\n"
            "• BEP × 4: Bleomycin + Etoposide + Cisplatin q21d\n"
            "• VIP: Vinblastine + Ifosfamide + Cisplatin q21d (consider if bleomycin risk)"
        )
    # Poor risk
    return (
        "BEP × 4 cycles OR VIP × 4 cycles (clinical trial strongly recommended)\n"
        "• BEP × 4: Bleomycin + Etoposide + Cisplatin q21d\n"
        "• VIP × 4: Vinblastine + Ifosfamide + Cisplatin q21d\n"
        "• TIP salvage for incomplete response: Paclitaxel + Ifosfamide + Cisplatin"
    )


def _pa_field_str() -> str:
    p = PA_FIELD
    return (
        f"Field: Para-aortic (PA)\n"
        f"Upper border: {p['upper_border']} | Lower border: {p['lower_border']}\n"
        f"CTV: {p['ctv']}\n"
        f"PTV: {p['ptv']}\n"
        f"Technique: {p['portals']}\n"
        f"Dose: {RT_PA_DOSE_GY} Gy / {RT_PA_FRACTIONS}# (2 Gy/fraction)"
    )


def _dog_leg_str() -> str:
    d = DOG_LEG_FIELD
    return (
        "Field: Dog-leg (PA + ipsilateral pelvic LN)\n"
        f"Definition: {d['definition']}\n"
        f"Lower border: {d['lower_border']}\n"
        f"CTV: {d['ctv']}\n"
        f"PTV: {d['ptv']}\n"
        f"OAR: {d['kidney_constraint']}\n"
        f"Dose: {RT_STAGE_II_DOSE_GY} Gy / {RT_STAGE_II_FRAC}# (2 Gy/fraction)"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sub-engines
# ─────────────────────────────────────────────────────────────────────────────

def _poor_ps(inp: TesticularInput) -> TesticularResult:
    flags = [f"ECOG {inp.ecog} – poor performance status"]
    hist_label = inp.histology.value.upper()
    out = (
        "1 Disease Subsite\n"
        f"Testicular {hist_label}\n\n"
        "2 Risk Stratification\n"
        f"ECOG {inp.ecog} – unfit for standard chemotherapy protocols\n\n"
        "3 Primary Treatment\n"
        "Best supportive care / palliative intent\n\n"
        "4 Radiotherapy\n"
        "Palliative RT if symptomatic (pain, bleeding, cord compression)\n\n"
        "5 Rationale\n"
        "Poor performance status precludes curative-intent chemotherapy\n"
        "MDT review and individualised planning essential\n\n"
        "6 Follow-up\n"
        "Symptom-based; palliative care referral"
    )
    out += _footer(Confidence.RED, flags, True, PROTOCOL_VERSION)
    return TesticularResult(
        formatted_output=out, confidence=Confidence.RED,
        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
    )


def _gcnis_ptis(inp: TesticularInput) -> TesticularResult:
    """Stage 0 – GCNIS (pTis)."""
    out = (
        "1 Disease Subsite\n"
        "Testicular – Germ Cell Neoplasia In Situ (GCNIS)\n\n"
        "2 Stage\n"
        "Stage 0 | pTis N0 M0\n\n"
        "3 Histology\n"
        "GCNIS (previously CIS of testis)\n\n"
        "4 Primary Treatment\n"
        "Low-dose RT to affected testis (if contralateral testis normal)\n"
        "OR Surveillance if patient desires fertility preservation\n\n"
        "5 Radiotherapy\n"
        "20 Gy / 10# to affected testis (2 Gy per fraction)\n"
        "Contralateral testis shielded\n"
        "Alternatively: surveillance with serial biopsies if fertility a priority\n\n"
        "6 Rationale\n"
        "Low-dose RT prevents progression to invasive GCT\n"
        "Causes azoospermia – sperm banking mandatory before RT\n\n"
        "7 Follow-up\n"
        "Testicular examination + serum markers every 6 months\n"
        "Annual scrotal ultrasound"
    )
    out += _footer(Confidence.GREEN, [], False, PROTOCOL_VERSION)
    return TesticularResult(
        formatted_output=out, confidence=Confidence.GREEN,
        flags=[], mdt_required=False, protocol_reference=PROTOCOL_VERSION,
    )


def _seminoma_stage1(inp: TesticularInput) -> TesticularResult:
    """Seminoma Stage I (IA / IB)."""
    flags = []
    stage = inp.overall_stage.value
    t     = inp.t_stage.value

    # High-risk Stage IB features: pT2–T4 or LVI
    is_high_risk = (t in ("pT2", "pT3", "pT4") or inp.lvi)
    if is_high_risk:
        flags.append("Stage IB / high-risk features (pT2–T4 or LVI) – adjuvant therapy recommended")

    if is_high_risk:
        adjuvant = (
            "Adjuvant carboplatin AUC 7 × 1–2 cycles (preferred for Stage IB)\n"
            "OR Surveillance (acceptable; higher relapse rate ~20%)\n"
            "OR Adjuvant RT (PA field; less preferred due to secondary cancer risk)"
        )
        preferred = "Adjuvant carboplatin AUC 7 × 1 cycle (MRC TE19: equivalent to RT; less morbidity)"
    else:
        adjuvant = (
            "Surveillance (preferred – Stage IA relapse rate ~15%; salvage chemotherapy curative)\n"
            "OR Adjuvant carboplatin AUC 7 × 1 cycle (MRC TE19 / SWENOTECA: equivalent to RT)\n"
            "OR Adjuvant RT (PA field – 20 Gy / 10#; historical standard; risk of secondary cancer)"
        )
        preferred = "Surveillance (omit unnecessary prophylaxis; salvage chemotherapy highly effective)"

    out = (
        "1 Disease Subsite\n"
        "Testicular – Seminoma\n\n"
        f"2 Stage\n"
        f"Stage {stage} | {t} N0 M0 S0\n\n"
        "3 IGCCCG Risk\n"
        "Not applicable (Stage I – no metastatic markers)\n\n"
        "4 Primary Treatment\n"
        f"Radical inguinal orchiectomy {'(completed)' if inp.orchiectomy_done else '(proceed immediately)'}\n\n"
        "5 Adjuvant Options\n"
        f"{adjuvant}\n\n"
        "6 Preferred Approach\n"
        f"{preferred}\n\n"
        "7 Radiotherapy (if chosen)\n"
        f"{_pa_field_str()}\n"
        "Indication: Adjuvant (Stage I; only if patient declines surveillance and carboplatin)\n\n"
        "8 Follow-up\n"
        "Chest X-ray + serum markers (AFP, β-HCG, LDH) every 3–4 months × 3 years, then annually\n"
        "CT abdomen/pelvis at 3 and 12 months\n"
        "Sperm banking recommended before adjuvant therapy"
    )
    out += _footer(
        Confidence.AMBER if is_high_risk else Confidence.GREEN,
        flags, False, PROTOCOL_VERSION,
    )
    return TesticularResult(
        formatted_output=out,
        confidence=Confidence.AMBER if is_high_risk else Confidence.GREEN,
        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION,
    )


def _seminoma_stage2(inp: TesticularInput) -> TesticularResult:
    """Seminoma Stage II (IIA / IIB / IIC)."""
    flags = []
    stage = inp.overall_stage.value
    n     = inp.n_stage.value

    if n == "N1":  # IIA – nodes ≤ 2 cm
        rt_option = (
            "Radiotherapy (preferred for IIA/IIB):\n"
            f"{_dog_leg_str()}\n"
            "Boost: +6 Gy to involved node(s)\n"
            "Chemotherapy alternative: BEP × 3 or EP × 4 (equivalent; TIGM / MRC TE20)"
        )
        preferred = "Dog-leg field RT (30 Gy/15#) – superior local control for small-volume N1"
        confidence = Confidence.GREEN
    elif n == "N2":  # IIB – nodes 2–5 cm
        rt_option = (
            "Radiotherapy: Dog-leg field 30 Gy/15# (IIB acceptable if ≤ 3 cm)\n"
            "Chemotherapy (preferred for larger N2): BEP × 3 or EP × 4\n"
            f"{_dog_leg_str()}"
        )
        preferred = "BEP × 3 or RT – MDT decision based on node size and patient preference"
        confidence = Confidence.AMBER
        flags.append("Stage IIB – RT vs BEP: MDT discussion recommended")
    else:  # N3 – nodes > 5 cm
        rt_option = "Radiotherapy not standard for N3 (bulk disease)"
        preferred = "BEP × 4 cycles (large-volume N3 – chemotherapy preferred)"
        confidence = Confidence.GREEN
        flags.append("Stage IIC (N3) – chemotherapy preferred over RT")

    bep = _bep_regimen(IGCCCGRisk.GOOD, TesticularHistology.SEMINOMA)

    out = (
        "1 Disease Subsite\n"
        "Testicular – Seminoma\n\n"
        f"2 Stage\n"
        f"Stage {stage} | {inp.t_stage.value} {n} {inp.m_stage.value} {inp.s_stage.value}\n\n"
        "3 IGCCCG Risk\n"
        "Good risk (all metastatic seminoma without non-pulmonary visceral mets = good)\n\n"
        "4 Primary Treatment\n"
        f"Radical inguinal orchiectomy {'(completed)' if inp.orchiectomy_done else '(proceed)'} → "
        f"Adjuvant RT or Chemotherapy\n\n"
        "5 Radiotherapy\n"
        f"{rt_option}\n\n"
        "6 Chemotherapy (alternative)\n"
        f"{bep}\n\n"
        "7 Preferred Approach\n"
        f"{preferred}\n\n"
        "8 Follow-up\n"
        "Serum markers every 3 months × 2 years, then every 6 months\n"
        "CT abdomen/pelvis at 3, 6, 12 months, then annually × 5 years\n"
        "CXR at each visit"
    )
    out += _footer(confidence, flags, bool([f for f in flags if "MDT" in f]), PROTOCOL_VERSION)
    return TesticularResult(
        formatted_output=out, confidence=confidence,
        flags=flags, mdt_required=bool([f for f in flags if "MDT" in f]),
        protocol_reference=PROTOCOL_VERSION,
    )


def _nsgct_stage1(inp: TesticularInput) -> TesticularResult:
    """NSGCT Stage I (IA / IB / IS)."""
    flags = []
    stage = inp.overall_stage.value
    t     = inp.t_stage.value

    # Stage IS: persistent marker elevation after orchiectomy
    if stage == "IS" or inp.marker_elevation_persistent:
        flags.append("Stage IS / persistent marker elevation – treat as metastatic good risk")
        bep = _bep_regimen(IGCCCGRisk.GOOD, TesticularHistology.NSGCT)
        out = (
            "1 Disease Subsite\n"
            "Testicular – NSGCT\n\n"
            "2 Stage\n"
            f"Stage IS | {t} N0 M0 {inp.s_stage.value} (persistent marker elevation)\n\n"
            "3 IGCCCG Risk\n"
            "Good risk (S1 – low marker elevation)\n"
            "Re-stage if S2/S3: treat as metastatic intermediate/poor risk\n\n"
            "4 Primary Treatment\n"
            "Chemotherapy for persistent marker elevation post-orchiectomy\n\n"
            "5 Chemotherapy\n"
            f"{bep}\n"
            "(Institutional protocol: GOOD RISK – BEP × 3 / EP × 4)\n\n"
            "6 Radiotherapy\n"
            "Not indicated\n\n"
            "7 Post-treatment Management\n"
            "Repeat serum markers 3 weeks post-chemotherapy\n"
            "CT abdomen/pelvis at response assessment (3 months)\n"
            "RPLND if residual retroperitoneal mass > 1 cm\n\n"
            "8 Follow-up\n"
            "Serum markers + CXR monthly × 3 months, then every 3 months\n"
            "CT abdomen/pelvis at 3, 6, 12 months"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return TesticularResult(
            formatted_output=out, confidence=Confidence.GREEN,
            flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION,
        )

    # Stage IA: low-risk (pT1, no LVI)
    is_low_risk = (t in ("pT1", "pT1a", "pT1b") and not inp.lvi)
    # Stage IB: high-risk (pT2–T4 or LVI)
    is_high_risk = (t in ("pT2", "pT3", "pT4") or inp.lvi)

    if is_high_risk:
        flags.append("Stage IB / high-risk (pT2–T4 or LVI) – adjuvant BEP × 2 recommended")
        adjuvant = (
            "Adjuvant BEP × 2 cycles (preferred – SWENOTECA: reduces relapse from ~50% to <5%)\n"
            "OR RPLND (nerve-sparing laparoscopic / open) – staging + therapeutic\n"
            "OR Surveillance (only if patient understands high relapse risk ~50%)"
        )
        preferred = "Adjuvant BEP × 2 (excellent efficacy; superior to surveillance for IB)"
        confidence = Confidence.GREEN
    else:
        adjuvant = (
            "Surveillance (preferred – Stage IA relapse rate ~15–20%; BEP salvage curative)\n"
            "OR RPLND (nerve-sparing; staging + therapeutic; avoids surveillance commitment)\n"
            "OR Adjuvant BEP × 1 (reduces relapse to ~3%; slight overtreatment of 85% who won't relapse)"
        )
        preferred = "Surveillance with close monitoring (Stage IA: SWENOTECA data)"
        confidence = Confidence.GREEN

    out = (
        "1 Disease Subsite\n"
        "Testicular – NSGCT\n\n"
        f"2 Stage\n"
        f"Stage {stage} | {t} N0 M0 {inp.s_stage.value}\n\n"
        "3 IGCCCG Risk\n"
        "Not applicable (Stage I)\n\n"
        "4 Primary Treatment\n"
        f"Radical inguinal orchiectomy {'(completed)' if inp.orchiectomy_done else '(proceed)'}\n\n"
        "5 Adjuvant Options\n"
        f"{adjuvant}\n\n"
        "6 Preferred Approach\n"
        f"{preferred}\n\n"
        "7 Radiotherapy\n"
        "Not indicated for Stage I NSGCT\n\n"
        "8 Follow-up\n"
        "Serum markers (AFP, β-HCG, LDH) + CXR monthly × 1 year, then every 2 months × year 2\n"
        "CT abdomen/pelvis at 3, 6, 12 months (and 24 months for surveillance)\n"
        "RPLND if retroperitoneal nodes develop > 1 cm on surveillance"
    )
    out += _footer(confidence, flags, False, PROTOCOL_VERSION)
    return TesticularResult(
        formatted_output=out, confidence=confidence,
        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION,
    )


def _nsgct_stage2(inp: TesticularInput) -> TesticularResult:
    """NSGCT Stage II (IIA / IIB / IIC)."""
    flags = []
    stage = inp.overall_stage.value
    n     = inp.n_stage.value

    igcccg = _resolve_igcccg(inp)
    bep    = _bep_regimen(igcccg, inp.histology)

    if n == "N1":  # IIA – nodes ≤ 2 cm
        preferred = (
            "RPLND (nerve-sparing) – surgical staging + therapy for low-volume N1\n"
            "If pathological N+: adjuvant BEP × 2 (RLA findings guide)\n"
            "Alternative: Primary BEP × 3 cycles (equivalent outcomes; avoids surgery)"
        )
        confidence = Confidence.GREEN
    elif n == "N2":  # IIB – nodes 2–5 cm
        preferred = (
            "BEP × 3 cycles (preferred for IIB – chemotherapy first)\n"
            "OR RPLND with adjuvant BEP × 2 if pN2 or residual post-RPLND"
        )
        confidence = Confidence.GREEN
        flags.append("Stage IIB – primary chemotherapy preferred over RPLND")
    else:  # N3 – nodes > 5 cm
        preferred = "BEP × 4 cycles (bulk N3 – chemotherapy mandatory; RPLND for residual)"
        confidence = Confidence.GREEN
        flags.append("Stage IIC – primary chemotherapy; RPLND for residual > 1 cm post-BEP")

    out = (
        "1 Disease Subsite\n"
        "Testicular – NSGCT\n\n"
        f"2 Stage\n"
        f"Stage {stage} | {inp.t_stage.value} {n} {inp.m_stage.value} {inp.s_stage.value}\n\n"
        f"3 IGCCCG Risk\n"
        f"{igcccg.value.capitalize()}\n\n"
        "4 Primary Treatment\n"
        f"Radical inguinal orchiectomy {'(completed)' if inp.orchiectomy_done else '(proceed)'} → Chemotherapy ± RPLND\n\n"
        "5 Chemotherapy\n"
        f"{bep}\n\n"
        "6 Surgery (RPLND)\n"
        f"{preferred}\n\n"
        "7 Radiotherapy\n"
        "Not indicated for NSGCT Stage II\n\n"
        "8 Post-treatment Management\n"
        "CT abdomen/pelvis at response assessment (3 months post-chemo)\n"
        "RPLND if residual mass > 1 cm (any histology risk)\n"
        "If pCR on RPLND: surveillance\n\n"
        "9 Follow-up\n"
        "Serum markers every 3 months × 2 years, then every 6 months\n"
        "CT abdomen/pelvis at 3, 6, 12 months, then annually"
    )
    out += _footer(confidence, flags, bool([f for f in flags if "MDT" in f]), PROTOCOL_VERSION)
    return TesticularResult(
        formatted_output=out, confidence=confidence,
        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION,
    )


def _metastatic_gct(inp: TesticularInput) -> TesticularResult:
    """Stage III – metastatic GCT (seminoma or NSGCT)."""
    flags = ["Metastatic GCT – MDT recommended"]
    igcccg = _resolve_igcccg(inp)
    hist   = inp.histology

    if hist == TesticularHistology.SEMINOMA and igcccg == IGCCCGRisk.POOR:
        igcccg = IGCCCGRisk.INTERMEDIATE  # Seminoma has no poor-risk category
        flags.append("Seminoma: no 'poor risk' IGCCCG category; treated as intermediate")

    bep = _bep_regimen(igcccg, hist)

    if igcccg == IGCCCGRisk.POOR:
        flags.append("IGCCCG Poor risk – clinical trial strongly recommended; intensification protocols")

    hist_label = hist.value.upper() if hist != TesticularHistology.SEMINOMA else "Seminoma"
    stage = inp.overall_stage.value

    out = (
        "1 Disease Subsite\n"
        f"Testicular – {hist_label}\n\n"
        f"2 Stage\n"
        f"Stage {stage} | {inp.t_stage.value} {inp.n_stage.value} {inp.m_stage.value} {inp.s_stage.value}\n\n"
        f"3 IGCCCG Risk\n"
        f"{igcccg.value.capitalize()} risk\n"
        + (
            "(Non-pulmonary visceral mets → intermediate/poor)\n"
            if inp.non_pulmonary_visceral_mets else
            "(Based on S-stage marker levels and metastatic pattern)\n"
        )
        + f"\n"
        "4 Primary Treatment\n"
        f"Radical inguinal orchiectomy {'(completed)' if inp.orchiectomy_done else '(proceed; may start chemo simultaneously if urgent)'}\n"
        "Systemic chemotherapy – IGCCCG risk-stratified\n\n"
        "5 Chemotherapy\n"
        f"{bep}\n\n"
        "6 Radiotherapy\n"
        "Not indicated for metastatic GCT (chemo is primary)\n"
        "Palliative RT if CNS metastases or symptomatic bone lesions\n\n"
        "7 Post-treatment Management\n"
        f"{'Seminoma residual ≥ 3 cm → PET-CT at 6 weeks post-chemo; resection if PET-avid' if hist == TesticularHistology.SEMINOMA else 'NSGCT residual ≥ 1 cm → RPLND (bilateral template); pathology guides further therapy'}\n"
        f"{'Seminoma residual < 3 cm → Observe (institutional protocol)' if hist == TesticularHistology.SEMINOMA else 'NSGCT pCR at RPLND → surveillance; viable GCT → 2 further BEP cycles'}\n\n"
        "8 Follow-up\n"
        "Serum markers (AFP, β-HCG, LDH) + CXR monthly × 3 months post-chemo, then 3-monthly\n"
        "CT chest/abdomen/pelvis at 3, 6, 12 months post-treatment\n"
        "Long-term follow-up: cardiovascular risk, bleomycin lung toxicity, secondary malignancy"
    )
    out += _footer(
        Confidence.GREEN if igcccg == IGCCCGRisk.GOOD else Confidence.AMBER,
        flags, True, PROTOCOL_VERSION,
    )
    return TesticularResult(
        formatted_output=out,
        confidence=Confidence.GREEN if igcccg == IGCCCGRisk.GOOD else Confidence.AMBER,
        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
    )


def _post_chemo_residual(inp: TesticularInput) -> TesticularResult:
    """Post-chemotherapy residual mass management."""
    flags = ["Post-chemotherapy residual – management decision required"]
    hist       = inp.histology
    residual   = inp.residual_mass_cm if inp.residual_mass_cm is not None else 0.0
    hist_label = hist.value.upper() if hist != TesticularHistology.SEMINOMA else "Seminoma"

    if hist == TesticularHistology.SEMINOMA:
        if residual < SEMINOMA_RESIDUAL_THRESHOLD_CM:
            recommendation = (
                f"Residual {residual:.1f} cm < 3 cm → Observe\n"
                "CT abdomen/pelvis at 3, 6, 12 months post-chemotherapy\n"
                "Serum markers quarterly"
            )
            confidence = Confidence.GREEN
        else:
            recommendation = (
                f"Residual {residual:.1f} cm ≥ 3 cm → PET-CT assessment at ≥ 6 weeks post-chemo\n"
                "• PET-negative → Observe\n"
                "• PET-positive → Surgical resection or salvage chemotherapy\n"
                "Avoid immediate surgery without PET-CT (significant false-positive fibrosis)"
            )
            confidence = Confidence.AMBER
            flags.append("Seminoma residual ≥ 3 cm – PET-CT required before intervention")
    else:
        # NSGCT / Mixed
        if residual < NSGCT_RESIDUAL_THRESHOLD_CM:
            recommendation = (
                f"Residual {residual:.1f} cm < 1 cm → Observe (RPLND may still be considered)\n"
                "Serum markers + CT at 3 months"
            )
            confidence = Confidence.GREEN
        else:
            recommendation = (
                f"Residual {residual:.1f} cm ≥ 1 cm → RPLND (bilateral retroperitoneal lymph node dissection)\n"
                "• Pathology: Necrosis/fibrosis (50%) → surveillance\n"
                "• Teratoma (35%) → RPLND curative\n"
                "• Viable GCT (15%) → 2 further BEP cycles post-RPLND\n"
                "Nerve-sparing RPLND to preserve ejaculation"
            )
            confidence = Confidence.GREEN
            flags.append(f"NSGCT residual ≥ 1 cm – RPLND indicated")

    out = (
        "1 Disease Subsite\n"
        f"Testicular – {hist_label} (post-chemotherapy)\n\n"
        "2 Clinical Status\n"
        "Post-chemotherapy residual mass assessment\n\n"
        "3 Residual Mass\n"
        f"Size: {residual:.1f} cm\n"
        f"Threshold: {'3 cm (seminoma)' if hist == TesticularHistology.SEMINOMA else '1 cm (NSGCT)'}\n\n"
        "4 Management\n"
        f"{recommendation}\n\n"
        "5 Rationale\n"
        f"{'PET-CT distinguishes active tumour from fibrosis in seminoma residual (high sensitivity post 6 weeks)' if hist == TesticularHistology.SEMINOMA else 'RPLND removes mature teratoma (cannot be distinguished from viable GCT by imaging) – institutional protocol: >3cm RESECT'}\n\n"
        "6 Follow-up\n"
        "Serum markers every 3 months × 2 years\n"
        "CT abdomen/pelvis at 3, 6, 12 months, then annually"
    )
    out += _footer(confidence, flags, bool([f for f in flags if "PET" in f or "RPLND" in f and "≥" in f]), PROTOCOL_VERSION)
    return TesticularResult(
        formatted_output=out, confidence=confidence,
        flags=flags, mdt_required=bool([f for f in flags if "PET-CT required" in f]),
        protocol_reference=PROTOCOL_VERSION,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_testicular_case(inp: TesticularInput) -> TesticularResult:
    """Run the full testicular GCT decision tree and return a formatted result."""

    # ── STEP 1: Poor performance status ───────────────────────────────────
    if inp.ecog >= 3:
        return _poor_ps(inp)

    # ── STEP 2: Post-chemo residual assessment ────────────────────────────
    if inp.post_chemo_residual:
        return _post_chemo_residual(inp)

    stage = inp.overall_stage.value
    hist  = inp.histology

    # ── STEP 3: Stage 0 (GCNIS) ───────────────────────────────────────────
    if stage == "0" or inp.t_stage.value == "pTis":
        return _gcnis_ptis(inp)

    # ── STEP 4: Stage III / Metastatic ────────────────────────────────────
    if stage in ("IIIA", "IIIB", "IIIC") or _is_metastatic(inp):
        return _metastatic_gct(inp)

    # ── STEP 5: Seminoma Stage I (IA / IB / I) ────────────────────────────
    if hist == TesticularHistology.SEMINOMA and stage in ("I", "IA", "IB"):
        return _seminoma_stage1(inp)

    # ── STEP 6: Seminoma Stage II (IIA / IIB / IIC) ───────────────────────
    if hist == TesticularHistology.SEMINOMA and stage in ("IIA", "IIB", "IIC"):
        return _seminoma_stage2(inp)

    # ── STEP 7: NSGCT / Mixed Stage I (IA / IB / IS) ─────────────────────
    if hist in (TesticularHistology.NSGCT, TesticularHistology.MIXED) and stage in ("I", "IA", "IB", "IS"):
        return _nsgct_stage1(inp)

    # ── STEP 8: NSGCT / Mixed Stage II ────────────────────────────────────
    if hist in (TesticularHistology.NSGCT, TesticularHistology.MIXED) and stage in ("IIA", "IIB", "IIC"):
        return _nsgct_stage2(inp)

    # Fallback
    flags = ["Stage/histology combination not classified – MDT required"]
    out = (
        "1 Disease Subsite\n"
        f"Testicular – {hist.value.upper()}\n\n"
        "2 Stage\n"
        f"Stage {stage} | {inp.t_stage.value} {inp.n_stage.value} {inp.m_stage.value} {inp.s_stage.value}\n\n"
        "3 Primary Treatment\n"
        "MDT discussion required\n\n"
        "4 Rationale\n"
        "Case parameters do not fit a standard decision tree pathway"
    )
    out += _footer(Confidence.RED, flags, True, PROTOCOL_VERSION)
    return TesticularResult(
        formatted_output=out, confidence=Confidence.RED,
        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
    )
