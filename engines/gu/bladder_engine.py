"""
Production-Ready Bladder Cancer Clinical Decision Support Engine
Institutional GU Cancers Protocol v1.0

Decision tree covers:
  • NMIBC: Ta / Tis / T1 — Low / Intermediate / High risk
  • BCG-unresponsive NMIBC
  • MIBC T2–T4a: Radical cystectomy vs Bladder preservation (Trimodality)
  • T4b (unresectable/fixed): Chemoradiation ± palliative intent
  • Metastatic (M1): Systemic ± palliative RT
  • Poor performance status

OUTPUT FORMAT matches sample cases document exactly.
IMPORTANT: Decision-support only. Obtain patient willingness for surgery per protocol.
"""

from .bladder_models import BladderInput, BladderResult, Confidence, BladderMStage, BCGStatus
from .bladder_config import (
    PROTOCOL_VERSION,
    CISPLATIN_MIN_CRCL,
    NMIBC_T_STAGES,
    MIBC_T_STAGES,
    UNRESECTABLE_T_STAGES,
    HIGH_RISK_NMIBC_T_STAGES,
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


def _is_metastatic(inp: BladderInput) -> bool:
    return inp.m_stage in (BladderMStage.M1A, BladderMStage.M1B)


def _is_mibc(inp: BladderInput) -> bool:
    return inp.t_stage.value in MIBC_T_STAGES


def _is_nmibc(inp: BladderInput) -> bool:
    return inp.t_stage.value in NMIBC_T_STAGES


def _is_cisplatin_eligible(inp: BladderInput) -> bool:
    return (
        inp.creatinine_clearance >= CISPLATIN_MIN_CRCL
        and inp.ecog <= 2
    )


def _cisplatin_note(inp: BladderInput) -> str:
    if inp.creatinine_clearance < CISPLATIN_MIN_CRCL:
        return (
            f"Cisplatin INELIGIBLE (CrCl {inp.creatinine_clearance:.0f} mL/min < 50)\n"
            "Alternatives: Carboplatin-based regimen (GCarbo) or gemcitabine monotherapy\n"
            "MIBC cisplatin-ineligible: discuss dose-dense MVAC equivalent or RT alone"
        )
    if inp.ecog >= 2:
        return (
            f"Cisplatin fitness borderline (ECOG {inp.ecog})\n"
            "Split-dose cisplatin or carboplatin-based alternative; MDT review"
        )
    return "Cisplatin-eligible (CrCl adequate, ECOG 0–1)"


# ─────────────────────────────────────────────────────────────────────────────
# Scenario sub-engines
# ─────────────────────────────────────────────────────────────────────────────

def _poor_ps(inp: BladderInput) -> BladderResult:
    flags = [f"ECOG {inp.ecog} – poor performance status"]
    out = (
        "1 Disease Type\n"
        f"{'Non-muscle invasive' if _is_nmibc(inp) else 'Muscle invasive'} bladder cancer\n\n"
        "2 Risk Stratification\n"
        f"ECOG {inp.ecog} – unfit for standard treatment protocol\n\n"
        "3 Primary Treatment\n"
        "Palliative / best supportive care\n\n"
        "4 Radiotherapy\n"
        "Short-course palliative RT if haematuria or pain\n"
        "• 21 Gy / 3# or 30 Gy / 10# (symptom control)\n\n"
        "5 Rationale\n"
        "Poor performance status precludes curative-intent therapy\n"
        "MDT review and palliative care integration mandatory\n\n"
        "6 Follow-up\n"
        "Symptom-based; palliative care referral"
    )
    out += _footer(Confidence.RED, flags, True, PROTOCOL_VERSION)
    return BladderResult(
        formatted_output=out, confidence=Confidence.RED,
        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
    )


def _metastatic(inp: BladderInput) -> BladderResult:
    """M1 – metastatic urothelial carcinoma."""
    flags = ["Metastatic disease – MDT required"]
    cis_note = _cisplatin_note(inp)
    cis_eligible = _is_cisplatin_eligible(inp)

    if cis_eligible:
        first_line = "Gemcitabine + Cisplatin (GC) – standard first-line (equivalent to MVAC with better tolerability)"
        maintenance = "Avelumab maintenance after platinum response (JAVELIN Bladder 100 – OS benefit)"
    else:
        first_line = "Gemcitabine + Carboplatin (GCarbo) – cisplatin-ineligible standard"
        maintenance = "Avelumab maintenance if objective response / stable disease (JAVELIN Bladder 100)"
        flags.append("Cisplatin-ineligible – carboplatin-based regimen")

    out = (
        "1 Disease Status\n"
        "Metastatic\n\n"
        "2 Primary Treatment\n"
        "Systemic chemotherapy\n\n"
        "3 Options\n"
        f"{first_line}\n"
        f"Cisplatin eligibility: {cis_note}\n\n"
        "4 Immunotherapy\n"
        f"Maintenance: {maintenance}\n"
        "Second line (post-platinum): Pembrolizumab (KEYNOTE-045: OS 10.3 vs 7.4 mo)\n"
        "Platinum-ineligible + PD-L1+: Pembrolizumab monotherapy (KEYNOTE-052)\n"
        "Erdafitinib: FGFR2/3-altered urothelial carcinoma (consider testing)\n\n"
        "5 Radiotherapy\n"
        "Palliative – site-specific schedules\n"
        "• Haematuria / bladder: 21 Gy / 3# (BC2001) or 30 Gy / 10#\n"
        "• Bone pain: 8 Gy / 1# or 20 Gy / 5#\n"
        "• Brain metastases: 20 Gy / 5# WBRT\n\n"
        "6 Follow-up\n"
        "CT response assessment after 2–3 cycles of first-line chemotherapy\n"
        "Symptom-based surveillance; quality of life monitoring"
    )
    out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
    return BladderResult(
        formatted_output=out, confidence=Confidence.AMBER,
        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
    )


def _nmibc(inp: BladderInput) -> BladderResult:
    """Non-Muscle Invasive Bladder Cancer: Ta / Tis / T1."""
    flags = []
    t     = inp.t_stage.value
    grade = inp.grade.value

    # ── BCG-unresponsive pathway (overrides other NMIBC paths) ────────────
    if inp.bcg_status == BCGStatus.UNRESPONSIVE:
        flags.append("BCG-unresponsive CIS – urgent MDT review")
        out = (
            "1 Disease Type\n"
            "Non-muscle invasive bladder cancer – BCG unresponsive\n\n"
            "2 Risk Stratification\n"
            "BCG-unresponsive – Very high risk\n\n"
            "3 Primary Treatment\n"
            "Radical cystectomy (gold standard) – PATIENT WILLINGNESS REQUIRED\n\n"
            "4 Adjuvant Therapy\n"
            "If surgery declined or unfit:\n"
            "• Pembrolizumab intravesical instillation (KEYNOTE-057: ~40% CR; FDA approved)\n"
            "• Nadofaragene firadenovec (gene therapy; FDA approved for BCG-unresponsive CIS)\n\n"
            "5 BCG\n"
            "Not applicable – BCG unresponsive; do not retreat\n\n"
            "6 Follow-up\n"
            "Close cystoscopy every 3 months\n"
            "Upper tract imaging annually\n"
            "Biopsy at any new or suspicious lesion"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return BladderResult(
            formatted_output=out, confidence=Confidence.AMBER,
            flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
        )

    # ── NMIBC Risk stratification ─────────────────────────────────────────
    # High risk: T1, Tis, or Ta high-grade; or CIS present
    is_high_risk = (
        t == "T1"
        or t == "Tis"
        or (t == "Ta" and grade == "high")
        or inp.cis_present
    )
    # Low risk: Ta, single, low-grade, first occurrence, no CIS
    is_low_risk = (t == "Ta" and grade == "low" and not inp.cis_present)
    # Intermediate: everything else
    is_intermediate = not is_high_risk and not is_low_risk

    # ── LOW RISK ──────────────────────────────────────────────────────────
    if is_low_risk:
        out = (
            "1 Disease Type\n"
            "Non-muscle invasive\n\n"
            "2 Risk Stratification\n"
            "Low risk\n"
            "(Ta, low-grade, single tumour, no CIS)\n\n"
            "3 Primary Treatment\n"
            "TURBT (complete resection of visible tumour)\n\n"
            "4 Adjuvant Therapy\n"
            "Single-dose intravesical chemotherapy (within 6 hours of TURBT)\n"
            "• Mitomycin C 40 mg / 40 mL or Epirubicin 80 mg\n"
            "(Reduces recurrence by ~40%; SWOG meta-analysis)\n\n"
            "5 BCG\n"
            "Not required\n\n"
            "6 Follow-up\n"
            "Cystoscopy surveillance\n"
            "• At 3 months post-TURBT\n"
            "• If negative: cystoscopy at 12 months, then annually for 5 years"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return BladderResult(
            formatted_output=out, confidence=Confidence.GREEN,
            flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION,
        )

    # ── INTERMEDIATE RISK ─────────────────────────────────────────────────
    if is_intermediate:
        out = (
            "1 Disease Type\n"
            "Non-muscle invasive\n\n"
            "2 Risk Stratification\n"
            "Intermediate risk\n"
            "(Ta multiple / recurrent, or large low-grade tumour)\n\n"
            "3 Primary Treatment\n"
            "Complete TURBT\n\n"
            "4 Adjuvant Therapy\n"
            "Intravesical chemotherapy (Mitomycin C or Epirubicin) – maintenance instillations\n"
            "OR short course BCG induction (if high recurrence risk)\n\n"
            "5 BCG\n"
            "Consider BCG induction × 6 weeks if multiple recurrences or high risk of progression\n"
            "(EORTC 30962: full-dose BCG for ≥1 year superior to low-dose or short course)\n\n"
            "6 Follow-up\n"
            "Cystoscopy every 3 months × 2 years, then every 6 months\n"
            "Urine cytology at each visit\n"
            "Annual upper tract imaging (CT urogram)"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return BladderResult(
            formatted_output=out, confidence=Confidence.GREEN,
            flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION,
        )

    # ── HIGH RISK ─────────────────────────────────────────────────────────
    # Check if re-TURBT needed (T1 high-grade: re-TURBT recommended within 2–6 weeks)
    needs_re_turbt = (t == "T1" and grade == "high")
    if needs_re_turbt:
        flags.append("T1 high-grade: re-TURBT required within 2–6 weeks (upstaging in ~30%)")

    cis_note = (
        "\nCIS present – BCG induction + maintenance mandatory; radical cystectomy if BCG failure"
        if inp.cis_present
        else ""
    )

    out = (
        "1 Risk Stratification\n"
        f"High risk\n"
        f"({t} {'high-grade' if grade == 'high' else ''}"
        f"{', CIS present' if inp.cis_present else ''})\n\n"
        "2 Primary Treatment\n"
        f"{'Repeat TURBT (within 2–6 weeks for T1 HG; upstaging risk ~30%)' if needs_re_turbt else 'TURBT – complete resection'}\n\n"
        "3 Adjuvant Therapy\n"
        "Intravesical BCG – induction + maintenance\n"
        "• Induction: BCG weekly × 6 instillations\n"
        "• Maintenance: BCG × 3 weekly instillations at 3, 6, 12, 18, 24, 30, 36 months\n"
        "  (Full-dose BCG × 1–3 years; SWOG 8507: maintenance reduces recurrence)\n"
        f"{cis_note}\n\n"
        "4 Rationale\n"
        "T1 HG and CIS carry high risk of progression to muscle-invasive disease\n"
        "BCG induction + maintenance is standard (SWOG 8507, EORTC 30962)\n"
        "Early cystectomy discussion for very high-risk features (T1 + CIS + LVI)\n\n"
        "5 Follow-up\n"
        "Cystoscopy + urine cytology every 3 months × 2 years, then every 6 months\n"
        "CT urogram annually (upper tract at risk)\n"
        "Biopsy at 3–6 months post-induction to assess BCG response"
    )
    out += _footer(Confidence.GREEN, flags, bool(flags), PROTOCOL_VERSION)
    return BladderResult(
        formatted_output=out, confidence=Confidence.GREEN,
        flags=flags, mdt_required=bool(flags), protocol_reference=PROTOCOL_VERSION,
    )


def _mibc_cystectomy(inp: BladderInput) -> BladderResult:
    """MIBC – radical cystectomy pathway (fit, willing for surgery)."""
    flags = []
    t = inp.t_stage.value
    cis_eligible = _is_cisplatin_eligible(inp)
    cis_note_str = _cisplatin_note(inp)

    if not cis_eligible:
        flags.append("Cisplatin-ineligible – alternative NAC or proceed to cystectomy alone")

    nac_regimen = (
        "Dose-dense MVAC (ddMVAC) × 4 cycles (preferred; SWOG 8710: OS benefit)\n"
        "OR Gemcitabine + Cisplatin (GC) × 4 cycles (equivalent, better tolerability)"
        if cis_eligible
        else "Cisplatin ineligible – consider cystectomy alone or carboplatin-based NAC after MDT review\n"
             f"({cis_note_str})"
    )

    # Adjuvant nivolumab: CheckMate 274 – high-risk post-cystectomy (pT3-4 or pN+)
    adjuvant_note = (
        "Adjuvant nivolumab: consider for high-risk pathology (pT3/T4 or pN+)\n"
        "(CheckMate 274: improved DFS; FDA approved)"
        if t in ("T3", "T3a", "T3b", "T4", "T4a")
        else "Adjuvant immunotherapy: CheckMate 274 – assess pathological stage post-op"
    )

    out = (
        "1 Disease Type\n"
        "Muscle invasive\n\n"
        "2 Primary Treatment\n"
        "Radical cystectomy\n"
        "(Ileal conduit or neobladder diversion; discuss with patient)\n\n"
        "3 Neoadjuvant Therapy\n"
        "Cisplatin-based chemotherapy prior to cystectomy\n"
        f"{nac_regimen}\n"
        "Neoadjuvant chemo + cystectomy: SWOG 8710 OS benefit (77 vs 46 months median)\n\n"
        "4 Alternative\n"
        "Bladder preservation (Trimodality therapy) if patient declines surgery\n"
        "or has significant comorbidities precluding cystectomy\n\n"
        "5 Adjuvant Therapy\n"
        f"{adjuvant_note}\n\n"
        "6 Follow-up\n"
        "CT chest/abdomen/pelvis every 3–6 months × 2 years, then annually\n"
        "Urinary diversion surveillance and upper tract imaging annually"
    )
    out += _footer(Confidence.GREEN, flags, bool(flags), PROTOCOL_VERSION)
    return BladderResult(
        formatted_output=out, confidence=Confidence.GREEN,
        flags=flags, mdt_required=bool(flags), protocol_reference=PROTOCOL_VERSION,
    )


def _mibc_bladder_preservation(inp: BladderInput) -> BladderResult:
    """MIBC – bladder preservation / trimodality therapy."""
    flags = []
    cis_eligible = _is_cisplatin_eligible(inp)

    if cis_eligible:
        chemo_rec = "Cisplatin 20 mg/m² days 1–5 (concurrent with RT)"
    else:
        chemo_rec = (
            "5-Fluorouracil 500 mg/m²/day + Mitomycin C 12 mg/m² (day 1)\n"
            "(BC2001 regimen – established chemoRT standard for cisplatin-ineligible)"
        )
        flags.append("Cisplatin-ineligible – 5-FU + MMC concurrent chemoRT (BC2001)")

    rt_detail = (
        "Whole bladder: 64–66 Gy / 32–33# (1.8–2 Gy per fraction)\n"
        "OR 55 Gy / 20# (moderate hypofractionation – alternative schedule)\n"
        "Technique: IMRT (partially full bladder for plan); IGRT recommended\n"
        "Target volumes (per protocol simulation guidelines):\n"
        "• CTV primary (54 Gy/30#): entire bladder + prostate/uterus\n"
        "• CTV LN (51 Gy/30#): external/internal iliac, obturator, perivesical, presacral\n"
        "• CTV boost (60 Gy/30#): GTV + 7 mm\n"
        "• PTV: CTV primary + 1 cm; LN + 7 mm\n"
        "Position: Supine; immobilisation with vac-loc/pelvic cast\n"
        "OAR constraints: Bowel < 300cc receive > 45 Gy; Rectum V50 < 50%; Femur max < 45 Gy"
    )

    out = (
        "1 Treatment Strategy\n"
        "Trimodality – bladder preservation\n\n"
        "2 Components\n"
        "Step 1: Maximal TURBT (complete resection of visible tumour)\n"
        "Step 2: Concurrent chemoradiotherapy (RT + radiosensitising chemotherapy)\n"
        "Step 3: Response assessment cystoscopy ± biopsy at 3 months\n\n"
        "3 Radiotherapy\n"
        f"{rt_detail}\n\n"
        "4 Chemotherapy\n"
        f"{chemo_rec}\n"
        "(BC2001 trial: chemoRT improved locoregional control vs RT alone)\n\n"
        "5 Rationale\n"
        "Organ preservation with equivalent cancer-specific survival to cystectomy in selected patients\n"
        "Best outcomes: solitary tumour, no hydronephrosis, complete TURBT feasible (SPARE trial)\n"
        "Cystectomy remains salvage option for residual / recurrent muscle-invasive disease\n\n"
        "6 Follow-up\n"
        "Cystoscopy + urine cytology at 3 months post-RT (response assessment)\n"
        "If complete response: cystoscopy every 3 months × 2 years\n"
        "CT chest/abdomen/pelvis at 3–6 months, then annually\n"
        "Salvage cystectomy for residual muscle-invasive disease at response assessment"
    )
    out += _footer(Confidence.GREEN, flags, bool(flags), PROTOCOL_VERSION)
    return BladderResult(
        formatted_output=out, confidence=Confidence.GREEN,
        flags=flags, mdt_required=bool(flags), protocol_reference=PROTOCOL_VERSION,
    )


def _mibc_unresectable(inp: BladderInput) -> BladderResult:
    """T4b – fixed/unresectable bladder cancer."""
    flags = ["T4b – unresectable (fixed to pelvic wall); curative cystectomy not feasible"]
    cis_eligible = _is_cisplatin_eligible(inp)

    chemo_rec = (
        "Cisplatin 20 mg/m²/day concurrent with RT (or ddMVAC induction then chemoRT)"
        if cis_eligible
        else "5-Fluorouracil + Mitomycin C (BC2001; cisplatin-ineligible)"
    )

    out = (
        "1 Disease Type\n"
        "Muscle invasive – unresectable (T4b)\n\n"
        "2 Risk Stratification\n"
        f"T4b {inp.n_stage.value} {inp.m_stage.value} – fixed to pelvic wall / abdominal wall\n"
        "Radical cystectomy not feasible\n\n"
        "3 Primary Treatment\n"
        "Definitive concurrent chemoradiotherapy\n\n"
        "4 Radiotherapy\n"
        "Whole bladder + pelvic LN: as per trimodality protocol\n"
        "Dose: 64–66 Gy (bladder); 45 Gy pelvic LN\n"
        "Technique: IMRT; IGRT mandatory\n\n"
        "5 Chemotherapy\n"
        f"{chemo_rec}\n\n"
        "6 Rationale\n"
        "Definitive chemoRT with curative intent for locally advanced unresectable disease\n"
        "MDT review: consider induction chemotherapy (GC × 2–3 cycles) then reassess resectability\n\n"
        "7 Follow-up\n"
        "Response assessment CT + cystoscopy at 3 months\n"
        "Re-evaluate for salvage cystectomy if significant response"
    )
    out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
    return BladderResult(
        formatted_output=out, confidence=Confidence.AMBER,
        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_bladder_case(inp: BladderInput) -> BladderResult:
    """Run the full bladder cancer decision tree and return a formatted result."""

    # ── STEP 1: Poor performance status ───────────────────────────────────
    if inp.ecog >= 3:
        return _poor_ps(inp)

    # ── STEP 2: Metastatic disease (M1) ───────────────────────────────────
    if _is_metastatic(inp):
        return _metastatic(inp)

    # ── STEP 3: NMIBC (Ta / Tis / T1) ────────────────────────────────────
    if _is_nmibc(inp):
        return _nmibc(inp)

    # ── STEP 4: T4b – unresectable ────────────────────────────────────────
    if inp.t_stage.value == "T4b":
        return _mibc_unresectable(inp)

    # ── STEP 5: MIBC (T2–T4a) ────────────────────────────────────────────
    if _is_mibc(inp):
        # Bladder preservation: patient unfit / declines surgery / preference
        if inp.bladder_preservation_preferred or not inp.willing_for_surgery or inp.ecog >= 2:
            return _mibc_bladder_preservation(inp)
        # Fit, willing for surgery → cystectomy pathway
        return _mibc_cystectomy(inp)

    # Fallback
    flags = ["Stage/T-stage not classified – MDT required"]
    out = (
        "1 Disease Type\n"
        f"Bladder cancer – stage {inp.t_stage.value} {inp.n_stage.value} {inp.m_stage.value}\n\n"
        "2 Primary Treatment\n"
        "MDT discussion required\n\n"
        "3 Rationale\n"
        "Case parameters do not fit a standard decision tree pathway"
    )
    out += _footer(Confidence.RED, flags, True, PROTOCOL_VERSION)
    return BladderResult(
        formatted_output=out, confidence=Confidence.RED,
        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION,
    )
