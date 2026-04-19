"""
CNS TUMORS - Decision Engine
Institutional CNS Tumors Protocol v1.0 | WHO 2021 Classification
Main decision logic with correct risk stratification
"""

from .cns_config import (
    PROTOCOL_VERSION, CNSTumourType, WHOGrade, GliomaSubtype, ResectionExtent,
    Confidence, EpendymomaLocation, GLIOMA_CONFIG, MENINGIOMA_CONFIG,
    EPENDYMOMA_CONFIG, MEDULLOBLASTOMA_CONFIG, PITUITARY_CONFIG, FLAG_TEMPLATES,
    RT_STANDARDS
)
from .cns_models import CNSInput, CNSResult, RiskAssessment


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _footer(confidence: Confidence, flags: list, mdt_required: bool) -> str:
    """Generate footer with flags and confidence."""
    flag_str = ", ".join(flags) if flags else "None"
    return (
        f"\nConfidence → {confidence.value}\n"
        f"Flags → {flag_str}\n"
        f"MDT Required → {mdt_required}\n"
        f"Protocol Reference → {PROTOCOL_VERSION}"
    )


def _assess_lgg_risk(inp: CNSInput) -> RiskAssessment:
    """
    Assess risk for low-grade glioma (WHO Grade 2).
    
    HIGH-RISK if ANY criteria present:
    - Age ≥ 40
    - Tumor size > 6 cm
    - Crosses midline
    - Residual disease / STR / biopsy (not GTR)
    - Neurological deficit noted (for flags, but may not affect initial Tx)
    """
    
    criteria_met = []
    is_high_risk = False
    
    # Age criterion
    if inp.age >= 40:
        criteria_met.append(f"age ≥40 (actual: {inp.age})")
        is_high_risk = True
    
    # Tumor size criterion
    if inp.tumour_size_cm and inp.tumour_size_cm > 6:
        criteria_met.append(f"tumour >6 cm (actual: {inp.tumour_size_cm} cm)")
        is_high_risk = True
    
    # Midline crossing
    if inp.crosses_midline:
        criteria_met.append("crosses midline")
        is_high_risk = True
    
    # Resection extent: STR/biopsy → high-risk; GTR → low-risk
    if inp.resection_extent in (ResectionExtent.STR, ResectionExtent.BIOPSY):
        criteria_met.append("subtotal resection or biopsy")
        is_high_risk = True
    
    # Residual disease
    if inp.residual_disease:
        criteria_met.append("residual disease post-op")
        is_high_risk = True
    
    return RiskAssessment(
        is_high_risk=is_high_risk,
        risk_criteria_met=criteria_met,
        confidence=Confidence.GREEN if not is_high_risk else Confidence.AMBER
    )


# ─────────────────────────────────────────────────────────────────────────────
# GLIOMA ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _glioma(inp: CNSInput) -> CNSResult:
    """Route glioma cases to appropriate subtype handler."""
    
    grade = inp.who_grade.value
    subtype = inp.glioma_subtype
    flags = []
    
    # ──────────────────────────────────────────────────────────────────────────
    # GLIOBLASTOMA (WHO Grade 4)
    # ──────────────────────────────────────────────────────────────────────────
    
    if grade == "4" or subtype == GliomaSubtype.IDH_WILDTYPE_GBM:
        return _glioma_gbm(inp)
    
    # ──────────────────────────────────────────────────────────────────────────
    # ANAPLASTIC ASTROCYTOMA (WHO Grade 3)
    # ──────────────────────────────────────────────────────────────────────────
    
    if grade == "3":
        out = (
            "1 Disease Type\n"
            "High-grade glioma (WHO Grade 3)\n\n"
            "2 Molecular Profile\n"
            "IDH: Mutant\n"
            "IDH-mutant anaplastic astrocytoma\n\n"
            "3 Risk Stratification\n"
            "High risk: Grade 3 malignancy\n\n"
            "4 Primary Treatment\n"
            "Maximal safe resection\n\n"
            "5 Adjuvant Therapy\n"
            "Radiotherapy + Chemotherapy (standard)\n\n"
            "6 Radiotherapy\n"
            "59–60 Gy / 30# (2 Gy/fraction)\n"
            "GTV: CE tumour + non-CE T2/FLAIR abnormality\n"
            "CTV: GTV + 2 cm\n"
            "PTV: CTV + 5 mm\n"
            "Technique: IMRT; fused MRI (T1+C + FLAIR)\n"
            "OAR: Brainstem <60 Gy; Optic chiasm <60 Gy\n\n"
            "7 Chemotherapy\n"
            "PCV × 6 cycles (Procarbazine + Lomustine + Vincristine) — standard\n"
            "OR Temozolomide if PCV not tolerated (equivalent outcomes)\n\n"
            "8 Rationale\n"
            "Grade 3 gliomas: adjuvant RT+chemo improves PFS vs RT alone\n"
            "PCV and TMZ show similar efficacy in prospective trials\n\n"
            "9 Follow-up\n"
            "MRI every 3 months × 2 years; then every 6 months; annual after 5 years"
        )
        flags.append("Grade 3 glioma – intensive adjuvant therapy required")
        out += _footer(Confidence.AMBER, flags, False)
        
        return CNSResult(
            formatted_output=out,
            confidence=Confidence.AMBER,
            flags=flags,
            mdt_required=False,
            protocol_reference=PROTOCOL_VERSION
        )
    
    # ──────────────────────────────────────────────────────────────────────────
    # LOW-GRADE GLIOMA (WHO Grade 2)
    # ──────────────────────────────────────────────────────────────────────────
    
    if grade == "2":
        risk_assessment = _assess_lgg_risk(inp)
        is_high_risk = risk_assessment.is_high_risk
        
        # Determine if GTR is possible (if not stated, assume no prior surgery = GTR possible)
        gtr_possible = (
            inp.resection_extent != ResectionExtent.STR and
            inp.resection_extent != ResectionExtent.BIOPSY and
            not inp.residual_disease
        )
        
        # LOW-RISK pathway
        if not is_high_risk:
            out = (
                "1 Disease Type\n"
                "Low-grade glioma\n\n"
                "2 WHO Grade\n"
                "Grade 2\n\n"
                "3 Molecular Profile\n"
                "IDH: Mutant – favourable prognosis\n"
                "IDH-mutant + 1p/19q intact → Diffuse astrocytoma\n\n"
                "4 Risk Stratification\n"
                f"Low risk (age <40, gross total resection possible)\n\n"
                "5 Primary Treatment\n"
                "Surgery (gross total resection if feasible)\n\n"
                "6 Adjuvant Therapy\n"
                "Observation if complete resection\n"
                "RT ± chemotherapy if high risk or recurrence\n\n"
                "7 Radiotherapy\n"
                "50–54 Gy / 25–27# (2 Gy/fraction) if indicated\n"
                "GTV: FLAIR abnormality + resection cavity + residual tumour\n"
                "CTV: GTV + 2 cm\n"
                "PTV: CTV + 5 mm\n"
                "Technique: 3DCRT/IMRT; fused MRI (FLAIR + T1+C)\n"
                "OAR: Brainstem <54 Gy; Optic chiasm <54 Gy; Hippocampus sparing if feasible\n\n"
                "8 Chemotherapy\n"
                "PCV or temozolomide (selected cases — consider on recurrence or if high risk)\n\n"
                "9 Rationale\n"
                "Indolent tumor with long survival — surgery ± observation often sufficient for young, low-risk patients\n"
                "EORTC 22845: early RT improves PFS but not OS — timing flexible\n\n"
                "10 Follow-up\n"
                "MRI every 6 months; annual assessment × 10 years (late recurrence common)"
            )
            
            flags = []
            if inp.neurological_deficit:
                flags.append("Seizures/neurological deficit at presentation — optimize seizure control")
            
            out += _footer(Confidence.GREEN, flags, False)
            
            return CNSResult(
                formatted_output=out,
                confidence=Confidence.GREEN,
                flags=flags,
                mdt_required=False,
                protocol_reference=PROTOCOL_VERSION
            )
        
        # HIGH-RISK pathway
        else:
            out = (
                "1 Disease Type\n"
                "Low-grade glioma\n\n"
                "2 WHO Grade\n"
                "Grade 2\n\n"
                "3 Molecular Profile\n"
                "IDH: Mutant – favourable prognosis\n"
                "IDH-mutant + 1p/19q intact → Diffuse astrocytoma\n\n"
                "4 Risk Stratification\n"
                f"High risk: {', '.join(risk_assessment.risk_criteria_met) if risk_assessment.risk_criteria_met else 'pre-op neurological deficit'}\n\n"
                "5 Primary Treatment\n"
                "Adjuvant radiotherapy + chemotherapy\n\n"
                "6 Radiotherapy\n"
                "50–54 Gy / 25–27# (2 Gy/fraction)\n"
                "GTV: FLAIR abnormality + resection cavity + residual tumour\n"
                "CTV: GTV + 2 cm\n"
                "PTV: CTV + 5 mm\n"
                "Technique: 3DCRT/IMRT; fused MRI (FLAIR + T1+C)\n"
                "OAR: Brainstem <54 Gy; Optic chiasm <54 Gy; Hippocampus sparing if feasible\n\n"
                "7 Chemotherapy\n"
                "PCV × 6 cycles (RTOG 9802: RT+PCV vs RT alone → OS 13.3 vs 7.8 yrs; standard)\n"
                "OR Temozolomide if PCV not tolerated (EORTC 22033-26033: similar outcomes)\n\n"
                "8 Rationale\n"
                "RTOG 9802: RT+PCV vs RT alone → OS 13.3 vs 7.8 years in high-risk LGG\n"
                "EORTC 22845: early RT improves PFS but not OS; RT timing after surgery acceptable\n\n"
                "9 Follow-up\n"
                "MRI every 6 months; annual assessment × 10 years (late recurrence common)"
            )
            
            flags_list = [FLAG_TEMPLATES["high_risk_lgg"]]
            if inp.neurological_deficit:
                flags_list.append("Seizures/neurological deficit — optimize seizure control during treatment")
            
            out += _footer(Confidence.AMBER, flags_list, False)
            
            return CNSResult(
                formatted_output=out,
                confidence=Confidence.AMBER,
                flags=flags_list,
                mdt_required=False,
                protocol_reference=PROTOCOL_VERSION
            )


def _glioma_gbm(inp: CNSInput) -> CNSResult:
    """Glioblastoma (WHO Grade 4) decision logic."""
    
    flags = []
    age = inp.age
    ecog = inp.ecog
    
    # Determine if elderly/poor PS
    is_elderly_poor = (age >= 70 or ecog >= 2)
    
    if is_elderly_poor:
        flags.append(FLAG_TEMPLATES["elderly_gbm"])
        
        out = (
            "1 Disease Type\n"
            "High-grade glioma (Glioblastoma)\n\n"
            "2 WHO Grade\n"
            "Grade 4\n\n"
            "3 Molecular Profile\n"
            "IDH: Wild-type\n\n"
            "4 Patient Profile\n"
            f"Elderly / borderline performance status (age {age}, ECOG {ecog})\n\n"
            "5 Treatment Options\n"
            "Hypofractionated RT ± temozolomide\n"
            "OR Temozolomide monotherapy (if MGMT methylated, not candidates for RT)\n\n"
            "6 Radiotherapy\n"
            "40 Gy / 15# (2.67 Gy/fraction) — NORDIC preferred schedule\n"
            "OR 25 Gy / 5# ultra-short course (if ECOG ≥3 or <3 months expected survival)\n"
            "GTV: CE tumour + FLAIR abnormality + oedema\n"
            "CTV: GTV + 2 cm\n"
            "PTV: CTV + 5 mm\n"
            "Technique: IMRT or 3DCRT; fused MRI\n"
            "OAR: Brainstem <40 Gy; Optic chiasm <40 Gy\n\n"
            "7 Chemotherapy\n"
        )
        
        if inp.mgmt_methylated is True:
            out += (
                "Temozolomide: consider concurrent and adjuvant (MGMT methylated — responsive)\n"
                "NORDIC trial: TMZ monotherapy non-inferior to RT in selected elderly patients\n"
            )
        elif inp.mgmt_methylated is False:
            out += (
                "Limited benefit of TMZ if MGMT unmethylated — palliative approach preferred\n"
            )
        else:
            out += (
                "Temozolomide decision based on MGMT methylation status and clinical tolerance\n"
            )
        
        out += (
            "\n8 Rationale\n"
            "NORDIC trial: hypofractionated RT non-inferior to standard RT in elderly GBM\n"
            "MGMT methylation status critical for TMZ benefit; consider palliative intent if poor PS\n\n"
            "9 Follow-up\n"
            "MRI every 8–12 weeks; symptom-based assessment; palliative care involvement"
        )
        
        out += _footer(Confidence.AMBER, flags, False)
        
        return CNSResult(
            formatted_output=out,
            confidence=Confidence.AMBER,
            flags=flags,
            mdt_required=False,
            protocol_reference=PROTOCOL_VERSION
        )
    
    else:
        # Standard-risk younger GBM
        out = (
            "1 Disease Type\n"
            "High-grade glioma (Glioblastoma)\n\n"
            "2 WHO Grade\n"
            "Grade 4\n\n"
            "3 Molecular Profile\n"
            "IDH: Wild-type\n\n"
            "4 Primary Treatment\n"
            "Maximal safe resection → Concurrent chemoradiation (Stupp protocol)\n\n"
            "5 Adjuvant Therapy\n"
            "Concurrent chemoradiation + adjuvant chemotherapy\n\n"
            "6 Radiotherapy\n"
            "60 Gy / 30# (2 Gy/fraction) — Stupp standard\n"
            "Target: GTV1 (FLAIR + CE tumour + oedema) → CTV1 = GTV1 + 2 cm (46 Gy/23#)\n"
            "        GTV2 (CE tumour on T1) → CTV2 = GTV2 + 2 cm (boost 14 Gy/7#)\n"
            "PTV: CTV + 5 mm\n"
            "Technique: IMRT/VMAT; IGRT mandatory; fused MRI (T1+C + FLAIR)\n"
            "OAR: Brainstem <54 Gy; Optic chiasm <54 Gy; Cochlea <45 Gy; Lens <7 Gy\n\n"
            "7 Chemotherapy\n"
            "Concurrent: Temozolomide 75 mg/m²/day (during 6 weeks RT)\n"
            "Adjuvant: Temozolomide 150–200 mg/m² × 5 days, 28-day cycles × 6 cycles (Stupp)\n"
            "Consider brief interruption after RT for recovery\n\n"
            "8 Rationale\n"
            "Stupp et al. NEJM 2005: RT+concurrent+adjuvant TMZ vs RT alone → median OS 14.6 vs 12.1 months\n"
            "Concurrent chemoradiation: standard of care for newly diagnosed GBM, age <70, ECOG 0–2\n"
            "MGMT methylation: predictive of TMZ benefit but not mandatory for treatment decision\n\n"
            "9 Follow-up\n"
            "MRI every 8–12 weeks; clinical assessment every 4 weeks during RT; monitor for pseudoprogression"
        )
        
        if inp.mgmt_methylated is True:
            flags.append("MGMT methylated — favorable response to TMZ expected")
        elif inp.mgmt_methylated is False:
            flags.append("MGMT unmethylated — consider additional strategies (bevacizumab, re-resection)")
        
        out += _footer(Confidence.GREEN, flags, False)
        
        return CNSResult(
            formatted_output=out,
            confidence=Confidence.GREEN,
            flags=flags,
            mdt_required=False,
            protocol_reference=PROTOCOL_VERSION
        )


# ─────────────────────────────────────────────────────────────────────────────
# MENINGIOMA ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _meningioma(inp: CNSInput) -> CNSResult:
    """Meningioma decision logic."""
    
    grade = inp.meningioma_grade or int(inp.who_grade.value)
    has_complete_resection = inp.meningioma_complete_resection
    residual = inp.residual_disease
    
    flags = []
    
    if grade == 1:
        if not residual and has_complete_resection:
            # Grade 1, completely resected
            out = (
                "1 Disease Type\n"
                "Meningioma\n\n"
                "2 Grade\n"
                "WHO Grade 1 (Benign)\n\n"
                "3 Primary Treatment\n"
                "Surgery (complete excision achieved)\n\n"
                "4 Adjuvant Therapy\n"
                "Not required\n\n"
                "5 Rationale\n"
                "Low recurrence after complete resection\n\n"
                "6 Follow-up\n"
                "MRI surveillance every 12–24 months; clinical review annually"
            )
            out += _footer(Confidence.GREEN, flags, False)
        else:
            # Grade 1, residual/incomplete
            flags.append("Residual meningioma after incomplete resection")
            out = (
                "1 Disease Type\n"
                "Meningioma\n\n"
                "2 Grade\n"
                "WHO Grade 1\n\n"
                "3 Disease Status\n"
                "Residual disease post-surgery\n\n"
                "4 Primary Treatment\n"
                "Adjuvant radiotherapy\n\n"
                "5 Radiotherapy\n"
                "54–60 Gy / 27–30# (2 Gy/fraction)\n"
                "GTV: Post-contrast T1 CE meningioma + dural tail\n"
                "CTV: GTV + 1–2 cm\n"
                "PTV: CTV + 5 mm\n"
                "Technique: IMRT/VMAT; fused MRI; IGRT\n"
                "OAR: Optic chiasm <54 Gy; Brainstem <54 Gy; Hippocampus sparing if feasible\n\n"
                "6 Rationale\n"
                "Improves local control for incomplete resection (Simpson Grade III–V)\n\n"
                "7 Follow-up\n"
                "MRI every 6–12 months × 3 years; then annually"
            )
            out += _footer(Confidence.AMBER, flags, False)
    
    elif grade == 2:
        flags.append("Atypical meningioma — adjuvant RT recommended")
        out = (
            "1 Disease Type\n"
            "Meningioma\n\n"
            "2 Grade\n"
            "WHO Grade 2 (Atypical)\n\n"
            "3 Primary Treatment\n"
            "Surgery + adjuvant radiotherapy\n\n"
            "4 Radiotherapy\n"
            "60 Gy / 30# (2 Gy/fraction)\n"
            "GTV: Post-contrast T1 CE meningioma\n"
            "CTV: GTV + 1–2 cm\n"
            "PTV: CTV + 5 mm\n"
            "Technique: IMRT/VMAT; fused MRI\n"
            "OAR: Optic chiasm <60 Gy; Brainstem <60 Gy\n\n"
            "5 Rationale\n"
            "High recurrence risk for Grade 2 — adjuvant RT mandatory even after complete resection\n"
            "5-year recurrence-free survival: 70–80% with RT vs 20–40% without\n\n"
            "6 Follow-up\n"
            "MRI every 6 months × 2 years; then annually"
        )
        out += _footer(Confidence.AMBER, flags, False)
    
    elif grade == 3:
        flags.append("Anaplastic meningioma — aggressive; MDT discussion recommended")
        out = (
            "1 Disease Type\n"
            "Meningioma\n\n"
            "2 Grade\n"
            "WHO Grade 3 (Anaplastic)\n\n"
            "3 Primary Treatment\n"
            "Surgery + radiotherapy\n\n"
            "4 Radiotherapy\n"
            "60–66 Gy / 30–33# (2 Gy/fraction)\n"
            "Consider hypofractionation (e.g., 30 Gy / 10#) if comorbidities\n"
            "GTV: Post-contrast T1 CE meningioma\n"
            "CTV: GTV + 2 cm\n"
            "PTV: CTV + 5 mm\n"
            "Technique: IMRT/VMAT; daily IGRT\n"
            "OAR: Optic chiasm <60 Gy; Brainstem <54 Gy\n\n"
            "5 Adjuvant Options\n"
            "Consider adjuvant chemotherapy (temozolomide) in highly selected cases (MDT)\n\n"
            "6 Rationale\n"
            "Aggressive tumor behavior — high recurrence and mortality risk\n"
            "5-year survival: ~20–30%; adjuvant therapy recommended\n\n"
            "7 Follow-up\n"
            "MRI every 3–4 months × 2 years; then every 6 months"
        )
        out += _footer(Confidence.RED, flags, True)
    
    else:
        out = "Grade not specified; MDT discussion required"
        out += _footer(Confidence.RED, ["Unclear meningioma grade"], True)
    
    return CNSResult(
        formatted_output=out,
        confidence=Confidence.RED if grade == 3 else (Confidence.AMBER if grade == 2 else Confidence.GREEN),
        flags=flags,
        mdt_required=grade == 3,
        protocol_reference=PROTOCOL_VERSION
    )


# ─────────────────────────────────────────────────────────────────────────────
# EPENDYMOMA ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _ependymoma(inp: CNSInput) -> CNSResult:
    """Ependymoma decision logic."""
    
    location = inp.ependymoma_location
    grade = inp.who_grade.value
    residual = inp.residual_disease
    flags = []
    
    if location == EpendymomaLocation.POSTERIOR_FOSSA:
        out = (
            "1 Disease Type\n"
            "Ependymoma\n\n"
            "2 Location\n"
            "Posterior fossa\n\n"
            "3 Primary Treatment\n"
            "Gross total resection (if feasible)\n\n"
            "4 Adjuvant Therapy\n"
            "Radiotherapy (recommended even after GTR)\n\n"
            "5 Radiotherapy\n"
            "54–59.4 Gy / 30–33# (1.8–2.0 Gy/fraction)\n"
            "GTV: Post-op T2/FLAIR abnormality + enhancing residual\n"
            "CTV: GTV + 1 cm (local field) — NO craniospinal irradiation for Grade 2\n"
            "PTV: CTV + 5 mm\n"
            "Technique: IMRT; prone position; fused MRI\n"
            "OAR: Brainstem <59.4 Gy; Cochlea <45 Gy (hearing preservation); Optic chiasm <55 Gy\n\n"
            "6 Rationale\n"
            "Local irradiation improves local control — CSI not required for Grade 2 posterior fossa\n\n"
            "7 Follow-up\n"
            "MRI brain + spine every 3 months × 2 years; then every 6 months"
        )
        out += _footer(Confidence.GREEN, flags, False)
    
    elif location == EpendymomaLocation.SPINAL:
        if inp.spinal_complete_resection and not residual:
            out = (
                "1 Disease Type\n"
                "Ependymoma\n\n"
                "2 Location\n"
                "Spinal cord\n\n"
                "3 Primary Treatment\n"
                "Complete surgical excision\n\n"
                "4 Adjuvant Therapy\n"
                "Observation if gross total resection achieved\n\n"
                "5 Radiotherapy\n"
                "Only if residual or recurrent disease\n\n"
                "6 Rationale\n"
                "Good prognosis with surgery alone for GTR — avoid unnecessary radiation toxicity\n\n"
                "7 Follow-up\n"
                "MRI spine every 6–12 months × 5 years; then annually"
            )
            out += _footer(Confidence.GREEN, [], False)
        else:
            out = (
                "1 Disease Type\n"
                "Ependymoma\n\n"
                "2 Location\n"
                "Spinal cord\n\n"
                "3 Disease Status\n"
                "Residual/incompletely resected\n\n"
                "4 Primary Treatment\n"
                "Adjuvant radiotherapy\n\n"
                "5 Radiotherapy\n"
                "50–54 Gy / 25–27# to spinal level involved + 1 cm margin\n"
                "Technique: IMRT; prone setup; MRI-based planning\n\n"
                "6 Follow-up\n"
                "MRI spine every 3–4 months × 2 years"
            )
            flags.append("Residual spinal ependymoma — adjuvant RT required")
            out += _footer(Confidence.AMBER, flags, False)
    
    else:
        out = (
            "1 Disease Type\n"
            "Ependymoma\n\n"
            "2 Grade\n"
            f"WHO Grade {grade}\n\n"
            "3 Primary Treatment\n"
            "Maximal safe surgical resection\n\n"
            "4 Adjuvant Therapy\n"
            "Radiotherapy ± chemotherapy (MDT decision based on grade/location)\n"
        )
        out += _footer(Confidence.AMBER, ["Ependymoma location not specified — MDT required"], True)
    
    return CNSResult(
        formatted_output=out,
        confidence=Confidence.GREEN if not flags else Confidence.AMBER,
        flags=flags,
        mdt_required=bool(flags),
        protocol_reference=PROTOCOL_VERSION
    )


# ─────────────────────────────────────────────────────────────────────────────
# MEDULLOBLASTOMA ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _medulloblastoma(inp: CNSInput) -> CNSResult:
    """Medulloblastoma decision logic."""
    
    risk = (inp.medulloblastoma_risk or "standard").lower()
    is_high = (risk == "high" or inp.medulloblastoma_metastatic)
    flags = []
    
    if is_high:
        flags.append(FLAG_TEMPLATES["high_risk_medullo"])
        csi_dose = "36 Gy / 20#"
        boost_dose = "+19.8 Gy boost to posterior fossa = total 55.8 Gy"
    else:
        csi_dose = "23.4 Gy / 13#"
        boost_dose = "+32.4 Gy boost to posterior fossa = total 55.8 Gy"
    
    out = (
        "1 Disease Type\n"
        "Medulloblastoma\n\n"
        f"2 Risk Classification\n"
        f"{'High risk' if is_high else 'Standard risk'}\n\n"
        "3 Primary Treatment\n"
        "Maximal safe resection (posterior fossa craniotomy)\n\n"
        "4 Adjuvant Therapy\n"
        "Craniospinal irradiation (CSI) + posterior fossa boost + chemotherapy\n\n"
        "5 Radiotherapy (Craniospinal Irradiation)\n"
        f"CSI dose: {csi_dose}\n"
        f"Boost: {boost_dose}\n"
        "CSI technique:\n"
        "  CTV brain: all CSF space including cribriform plate; prepontine cistern; optic nerves to globe\n"
        "  CTV spine: thecal sac from cranial junction to S1–S3 (2 cm from thecal sac inferiorly)\n"
        "  PTV brain: CTV + 3 mm; PTV spine: CTV + 5 mm\n"
        "  Position: Supine, arms by side, neck hyperextended\n"
        "  CT: vertex to mid-thigh; AP-PA fields for spine; IMRT for cranial component\n"
        "OAR: Lens <7 Gy; Cochlea <35 Gy (hearing loss risk); Hypothalamus <40 Gy; Hippocampus mean <16 Gy\n\n"
        "6 Chemotherapy\n"
        "Concurrent: Weekly Vincristine (during RT)\n"
        f"Adjuvant: Cisplatin + Lomustine + Vincristine × 6–8 cycles (post-RT)\n"
        "Consider intensification in high-risk cohort\n\n"
        "7 Rationale\n"
        "CSI mandatory — medulloblastoma has CSF pathway seeding risk\n"
        "Concurrent Vincristine + post-RT PCV: COG/ACNS trials show improved OS vs RT alone\n"
        + ("High-risk: full-dose CSI (36 Gy) + intensive post-RT chemo required for disease control\n" if is_high else "")
        + "\n8 Follow-up\n"
        "MRI brain + spine every 3 months × 2 years; then every 6 months; annual endocrine monitoring"
    )
    
    out += _footer(
        Confidence.AMBER if is_high else Confidence.GREEN,
        flags,
        bool(flags)
    )
    
    return CNSResult(
        formatted_output=out,
        confidence=Confidence.AMBER if is_high else Confidence.GREEN,
        flags=flags,
        mdt_required=bool(flags),
        protocol_reference=PROTOCOL_VERSION
    )


# ─────────────────────────────────────────────────────────────────────────────
# PITUITARY ADENOMA ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _pituitary(inp: CNSInput) -> CNSResult:
    """Pituitary adenoma decision logic."""
    
    func = inp.pituitary_functional
    residual = inp.residual_disease
    flags = []
    
    func_label = (
        "Functional (secreting)" if func else
        "Non-functional" if func is False else
        "Functional status unknown"
    )
    
    if not residual:
        out = (
            "1 Disease Type\n"
            "Pituitary Adenoma\n\n"
            f"2 Tumour Type\n"
            f"{func_label}\n\n"
            "3 Primary Treatment\n"
            "Transsphenoidal surgery (preferred for most adenomas)\n\n"
            "4 Adjuvant Therapy\n"
            "Not required if complete resection and hormonal remission\n\n"
            "5 Medical Management\n"
            + ("Dopamine agonists (Cabergoline) first-line for prolactinomas\n"
               "Somatostatin analogues for acromegaly (Octreotide/Lanreotide)\n"
               if func else
               "Hormone replacement therapy as needed post-operatively\n")
            + "\n6 Rationale\n"
            "Transsphenoidal resection: high remission rates for micro/macroprolactinomas; acromegaly also responsive\n\n"
            "7 Follow-up\n"
            "Hormonal assessment 3 months post-op; MRI pituitary annually"
        )
        out += _footer(Confidence.GREEN, flags, False)
    
    else:
        flags.append(FLAG_TEMPLATES["residual_pituitary"])
        out = (
            "1 Disease Type\n"
            "Pituitary Adenoma\n\n"
            f"2 Tumour Type\n"
            f"{func_label}\n\n"
            "3 Disease Status\n"
            "Residual disease post-surgery\n\n"
            "4 Primary Treatment\n"
            "Adjuvant radiotherapy (FSRT or SRS depending on size/proximity to OAR)\n\n"
            "5 Radiotherapy\n"
            "50.4 Gy / 28# (2 Gy/fraction) — Fractionated IMRT\n"
            "OR SRS: 12–20 Gy × 1# (Gamma Knife/CyberKnife — if ≤3 cm, adequate OAR distance)\n"
            "GTV: CE tumour on post-contrast T1 MRI\n"
            "CTV: GTV (pituitary adenoma)\n"
            "PTV: CTV + 5 mm (fractionated) or CTV + 2 mm (SRS)\n"
            "Technique: IMRT/VMAT; fused MRI; daily CBCT\n"
            "OAR: Optic chiasm <54 Gy (fractionated) / <8 Gy (SRS); Brainstem <54 Gy\n\n"
            "6 Rationale\n"
            "Fractionated RT: local control >90% for residual adenoma; SRS equivalent for small lesions\n\n"
            "7 Follow-up\n"
            "MRI pituitary every 6 months × 2 years; hormonal reassessment; annual thereafter"
        )
        out += _footer(Confidence.AMBER, flags, False)
    
    return CNSResult(
        formatted_output=out,
        confidence=Confidence.GREEN if not residual else Confidence.AMBER,
        flags=flags,
        mdt_required=False,
        protocol_reference=PROTOCOL_VERSION
    )


# ─────────────────────────────────────────────────────────────────────────────
# CRANIOPHARYNGIOMA ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _craniopharyngioma(inp: CNSInput) -> CNSResult:
    """Craniopharyngioma decision logic."""
    
    flags = []
    
    out = (
        "1 Disease Type\n"
        "Craniopharyngioma\n\n"
        "2 Primary Treatment\n"
        "Limited resection (sparing hypothalamus) + Adjuvant RT\n"
        "OR Gross total resection if hypothalamus not involved\n\n"
        "3 Adjuvant Therapy\n"
        "RT after subtotal resection (reduces recurrence without excess toxicity)\n\n"
        "4 Radiotherapy\n"
        "50–54 Gy / 25–27# (1.8–2.0 Gy/fraction) fractionated IMRT\n"
        "OR Proton therapy if available (reduces dose to hypothalamic/hippocampal structures)\n"
        "GTV: CE tumour + cystic component\n"
        "CTV: GTV + 0.5–1 cm\n"
        "PTV: CTV + 5 mm\n"
        "Technique: IMRT; MRI-based fusion; IGRT\n"
        "OAR: Optic chiasm <54 Gy; Hypothalamus mean <45 Gy; Hippocampus mean <16 Gy\n\n"
        "5 Intracystic Therapy\n"
        "Interferon-α or bleomycin for predominantly cystic tumours (institutional protocol)\n\n"
        "6 Rationale\n"
        "Hypothalamic-sparing approach: reduces obesity, cognitive decline, and endocrine morbidity\n"
        "Limited surgery + RT: equivalent oncological control vs radical surgery, with less hypothalamic damage\n\n"
        "7 Follow-up\n"
        "MRI annually; comprehensive endocrine assessment (growth hormone, TSH, ACTH, ADH — panhypopituitarism risk)"
    )
    
    out += _footer(Confidence.GREEN, flags, False)
    
    return CNSResult(
        formatted_output=out,
        confidence=Confidence.GREEN,
        flags=flags,
        mdt_required=False,
        protocol_reference=PROTOCOL_VERSION
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_cns_case(inp: CNSInput) -> CNSResult:
    """
    Main entry point: route case to tumour-specific engine.
    
    Input: CNSInput (Pydantic model with all case details)
    Output: CNSResult (formatted text + confidence + flags)
    """
    
    # Check for very poor performance status
    if inp.ecog >= 3 and inp.tumour_type != CNSTumourType.MEDULLOBLASTOMA:
        flags = ["Poor performance status – individualised / palliative approach"]
        out = (
            f"1 Disease Type\n"
            f"{inp.tumour_type.value.replace('_', ' ').title()}\n\n"
            f"2 WHO Grade\n"
            f"Grade {inp.who_grade.value}\n\n"
            "3 Performance Status\n"
            "ECOG ≥ 3 – standard treatment not feasible\n\n"
            "4 Treatment Recommendation\n"
            "Best supportive care / palliative intent\n"
            "Hypofractionated RT (25–34 Gy) if clinical benefit expected\n\n"
            "5 Follow-up\n"
            "Symptom-based; palliative care referral; advance care planning"
        )
        out += _footer(Confidence.RED, flags, True)
        return CNSResult(
            formatted_output=out,
            confidence=Confidence.RED,
            flags=flags,
            mdt_required=True,
            protocol_reference=PROTOCOL_VERSION
        )
    
    # Route to tumour-specific engine
    t = inp.tumour_type
    
    if t == CNSTumourType.GLIOMA:
        return _glioma(inp)
    elif t == CNSTumourType.MENINGIOMA:
        return _meningioma(inp)
    elif t == CNSTumourType.EPENDYMOMA:
        return _ependymoma(inp)
    elif t == CNSTumourType.MEDULLOBLASTOMA:
        return _medulloblastoma(inp)
    elif t == CNSTumourType.PITUITARY:
        return _pituitary(inp)
    elif t == CNSTumourType.CRANIOPHARYNGIOMA:
        return _craniopharyngioma(inp)
    
    else:
        flags = ["Tumour type not recognised – MDT required"]
        out = (
            f"1 Disease Type\n"
            f"{inp.tumour_type.value.replace('_', ' ').title()}\n\n"
            "2 Recommendation\n"
            "MDT discussion required – not in standard decision tree\n"
        )
        out += _footer(Confidence.RED, flags, True)
        return CNSResult(
            formatted_output=out,
            confidence=Confidence.RED,
            flags=flags,
            mdt_required=True,
            protocol_reference=PROTOCOL_VERSION
        )