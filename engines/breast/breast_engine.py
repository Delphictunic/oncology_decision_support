"""
Breast Cancer Clinical Decision Support Engine
Implements the Institutional Breast Cancer Decision Tree (AJCC 8th edition staging).
Steps 1-6 from the decision tree, with Step 7 output formatting.

IMPORTANT: This is a decision-SUPPORT tool. All recommendations require clinical judgment.
Cases flagged as "red" confidence MUST go through MDT discussion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Enums for fixed-choice fields ──────────────────────────────────────────

class Sex(str, Enum):
    FEMALE = "female"
    MALE = "male"

class Histology(str, Enum):
    IDC = "invasive ductal carcinoma"
    ILC = "invasive lobular carcinoma"
    DCIS = "DCIS"
    OTHER = "other"

class Laterality(str, Enum):
    LEFT = "left"
    RIGHT = "right"

class SurgeryType(str, Enum):
    BCS = "BCS"
    MRM = "MRM"
    MASTECTOMY = "mastectomy"
    NONE = "none"

class AxillaryProcedure(str, Enum):
    SLNB = "SLNB"
    ALND = "ALND"
    NONE = "none"

class MarginStatus(str, Enum):
    NEGATIVE = "negative"
    CLOSE = "close"
    POSITIVE = "positive"
    UNKNOWN = "unknown"

class ERStatus(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"

class PRStatus(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"

class HER2Status(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"

class MenopausalStatus(str, Enum):
    PREMENOPAUSAL = "premenopausal"
    PERIMENOPAUSAL = "perimenopausal"
    POSTMENOPAUSAL = "postmenopausal"

class ChemoResponse(str, Enum):
    PCR = "pCR"
    PARTIAL = "partial"
    RESIDUAL = "residual"
    NOT_APPLICABLE = "not applicable"

class Confidence(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"

class Quadrant(str, Enum):
    UPPER_OUTER = "upper outer"
    UPPER_INNER = "upper inner"
    LOWER_OUTER = "lower outer"
    LOWER_INNER = "lower inner"
    CENTRAL = "central"
    MULTIFOCAL = "multifocal"
    MULTICENTRIC = "multicentric"


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
    v = _t_value(t_stage)
    return 0 <= v <= 2


def _is_node_positive(n_stage: str) -> bool:
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


# Luminal A: ER+/PR+, HER2-, low Ki-67 (usually <14–20%), low grade, endocrine-sensitive
LUMINAL_A_KI67_THRESHOLD = 20  # %; upper bound for "low" Ki-67


def _is_luminal_a(
    er: str,
    pr: str,
    her2: str,
    grade: int,
    ki67_percent: Optional[float],
) -> bool:
    """True if tumor fits Luminal A: ER/PR+, HER2-, low Ki-67, low grade."""
    if er != "positive" or pr != "positive" or her2 != "negative":
        return False
    ki = ki67_percent if ki67_percent is not None else 99
    if ki > LUMINAL_A_KI67_THRESHOLD:
        return False
    return grade <= 2


# ── Result dataclass ──────────────────────────────────────────────────────

@dataclass
class BreastDecisionResult:
    primary_recommendation: str
    confidence: Confidence
    reasoning: str
    flags: list[str] = field(default_factory=list)
    protocol_reference: str = "Institutional Breast Cancer Protocol v1.0 (aligned with NCCN/ESMO)"
    mdt_required: bool = False

    # Extended output fields
    case_summary: str = ""
    surgery_recommendation: str = ""
    systemic_therapy: str = ""
    radiation_therapy: str = ""
    follow_up: str = ""

    def to_dict(self) -> dict:
        return {
            "case_summary": self.case_summary,
            "primary_recommendation": self.primary_recommendation,
            "confidence": self.confidence.value,
            "reasoning": self.reasoning,
            "flags": self.flags,
            "protocol_reference": self.protocol_reference,
            "mdt_required": self.mdt_required,
            "details": {
                "surgery": self.surgery_recommendation,
                "systemic_therapy": self.systemic_therapy,
                "radiation_therapy": self.radiation_therapy,
                "follow_up": self.follow_up,
            },
        }


# ── Main engine ───────────────────────────────────────────────────────────

def evaluate_breast_case(
    # ── Mandatory patient data ──
    age: int,
    sex: str,
    ecog: int,
    menopausal_status: str,
    # ── Mandatory tumor data ──
    laterality: str,
    histology: str,
    tumor_size_cm: float,
    grade: int,
    lvi: bool,
    # ── Mandatory nodal / metastatic ──
    n_stage: str,           # clinical or pathological N stage
    nodes_examined: int,
    nodes_positive: int,
    m_stage: str,           # M0 or M1
    # ── Mandatory biomarkers ──
    er_status: str,
    pr_status: str,
    her2_status: str,
    # ── Mandatory staging ──
    t_stage: str,
    overall_stage: str,
    # ── Surgery ──
    surgery_done: bool,
    surgery_type: str = "none",
    margin_status: str = "unknown",
    axillary_procedure: str = "none",
    # ── Optional ──
    quadrant: str = "upper outer",
    ki67_percent: Optional[float] = None,
    neoadjuvant_chemo: bool = False,
    chemo_response: str = "not applicable",
    extracapsular_extension: bool = False,
    imn_involvement: bool = False,
    scf_involvement: bool = False,
    symptomatic_metastasis: bool = False,
    surgery_feasible_after_nact: bool = True,
    # Luminal A–specific optional
    prior_chest_rt: bool = False,
    progression_on_endocrine: bool = False,
    bone_only_metastases: bool = False,
    visceral_metastases: bool = False,
    brca_mutation: bool = False,
) -> BreastDecisionResult:
    """Run the full decision tree (Steps 1-6) and return structured result."""

    flags: list[str] = []
    recommendations: list[str] = []
    reasoning_parts: list[str] = []
    confidence = Confidence.GREEN
    mdt_required = False

    # Normalize enums
    sex = sex.lower().strip()
    histology_lower = histology.lower().strip()
    er = er_status.lower().strip()
    pr = pr_status.lower().strip()
    her2 = her2_status.lower().strip()
    surgery_t = surgery_type.upper().strip()
    margin = margin_status.lower().strip()
    meno = menopausal_status.lower().strip()
    chemo_resp = chemo_response.lower().strip()
    quad = quadrant.lower().strip()
    m = m_stage.upper().strip()

    is_triple_negative = (er == "negative" and pr == "negative" and her2 == "negative")
    is_hr_positive = (er == "positive" or pr == "positive")
    is_her2_positive = (her2 == "positive")
    overall_numeric = _overall_stage_numeric(overall_stage)
    node_positive = _is_node_positive(n_stage) or nodes_positive > 0
    is_luminal_a = _is_luminal_a(er, pr, her2, grade, ki67_percent)

    # Derive molecular subtype
    if is_triple_negative:
        mol_subtype = "Triple Negative"
    elif is_her2_positive and is_hr_positive:
        mol_subtype = "Luminal B (HER2+)"
    elif is_her2_positive:
        mol_subtype = "HER2-enriched"
    elif is_hr_positive:
        mol_subtype = (
            "Luminal A"
            if _is_luminal_a(er, pr, her2, grade, ki67_percent)
            else "Luminal B (HER2-)"
        )
    else:
        mol_subtype = "Unclassified"

    # ── Build case summary ──
    case_summary = (
        f"{age}-year-old {'premenopausal' if 'pre' in meno else 'perimenopausal' if 'peri' in meno else 'postmenopausal'} "
        f"{'woman' if sex == 'female' else 'man'} with {laterality} breast "
        f"{histology}, {t_stage}{n_stage}{m}, Grade {grade}, "
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
            reasoning = "Non-invasive histology. MDT discussion required before proceeding."
        else:
            reasoning = "Poor performance status (ECOG > 2). MDT discussion required."

        return BreastDecisionResult(
            primary_recommendation="MDT discussion required before treatment planning",
            confidence=Confidence.RED,
            reasoning=reasoning,
            flags=flags,
            mdt_required=True,
            case_summary=case_summary,
        )

    reasoning_parts.append(f"Invasive carcinoma confirmed, ECOG {ecog} (eligible)")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 6: PALLIATIVE SETTING (check early – overrides other steps)
    # ═══════════════════════════════════════════════════════════════════════
    if overall_numeric == 4 or m == "M1" or symptomatic_metastasis:
        reasoning_parts.append("Stage IV / metastatic disease identified")
        flags.append("Metastatic disease – palliative intent")

        # Luminal A MBC – structured first-line and later-line therapy
        if is_luminal_a:
            if progression_on_endocrine:
                # Case 10: Endocrine-resistant Luminal A MBC
                recommendations.append("Fulvestrant + CDK4/6 inhibitor")
                systemic = (
                    "Next-line: Fulvestrant + CDK4/6 inhibitor. "
                    "Chemotherapy reserved for later lines. "
                    "ESR1 / PIK3CA mutation testing recommended."
                )
                rt_rec = "Palliative RT only if symptomatic (e.g. bone pain, fracture risk)"
            else:
                # Cases 8–9: First-line Luminal A MBC
                recommendations.append("Endocrine + CDK4/6 inhibitor; palliative RT if symptomatic")
                if "pre" in meno:
                    systemic = (
                        "First-line: Ovarian suppression + AI + CDK4/6 inhibitor. "
                        "Ovarian ablation followed by AI or CDK4/6 if premenopausal."
                    )
                else:
                    systemic = "First-line: Aromatase inhibitor + CDK4/6 inhibitor."
                systemic += " Chemotherapy not indicated in first line."
                if bone_only_metastases or not visceral_metastases:
                    systemic += (
                        " Bone-directed therapy: zoledronic acid or denosumab; "
                        "calcium + vitamin D."
                    )
                rt_rec = (
                    "Palliative RT for pain / fracture risk: 30 Gy / 3 Gy per fraction / 10#. "
                    "SBRT technique can be considered if indicated."
                )
            follow_up_mbc = (
                "Treatment goal: disease control, quality of life. "
                "Clinical and imaging monitoring every 6 months."
            )
            return BreastDecisionResult(
                primary_recommendation="; ".join(recommendations),
                confidence=Confidence.AMBER,
                reasoning="Luminal A metastatic breast cancer. " + "; ".join(reasoning_parts),
                flags=flags,
                mdt_required=True,
                case_summary=case_summary,
                surgery_recommendation="Not indicated in palliative setting unless for local control",
                systemic_therapy=systemic,
                radiation_therapy=rt_rec,
                follow_up=follow_up_mbc,
            )

        # Luminal B MBC: first-line endocrine + CDK4/6; chemo reserved for later
        if is_hr_positive and not is_luminal_a and not is_her2_positive:
            recommendations.append("First-line: Aromatase inhibitor + CDK4/6 inhibitor; palliative RT if symptomatic")
            systemic = "First-line: Aromatase inhibitor + CDK4/6 inhibitor. Chemotherapy reserved for endocrine-refractory disease."
            if bone_only_metastases or not visceral_metastases:
                systemic += " Bone-directed therapy: zoledronic acid or denosumab; calcium + vitamin D."
            return BreastDecisionResult(
                primary_recommendation="; ".join(recommendations),
                confidence=Confidence.AMBER,
                reasoning="Luminal B metastatic breast cancer. " + "; ".join(reasoning_parts),
                flags=flags,
                mdt_required=True,
                case_summary=case_summary,
                surgery_recommendation="Not indicated in palliative setting unless for local control",
                systemic_therapy=systemic,
                radiation_therapy="Palliative RT for symptoms; site-specific dose schedules",
                follow_up="Clinical assessment every 2–3 months; imaging every 4–6 months",
            )

        recommendations.append("Palliative RT with site-specific dose schedules")
        systemic = "Systemic therapy as per MDT decision"
        if is_her2_positive:
            systemic += "; first-line: Docetaxel + Trastuzumab + Pertuzumab (HER2-directed therapy with chemotherapy)"
        if is_triple_negative:
            systemic += "; consider immunotherapy + chemotherapy if PD-L1 positive"

        return BreastDecisionResult(
            primary_recommendation="Palliative radiotherapy; systemic therapy as indicated",
            confidence=Confidence.AMBER,
            reasoning="Stage IV disease. " + "; ".join(reasoning_parts),
            flags=flags,
            mdt_required=True,
            case_summary=case_summary,
            surgery_recommendation="Not indicated in palliative setting unless for local control",
            systemic_therapy=systemic,
            radiation_therapy="Palliative RT – site-specific dose schedules",
            follow_up="As per palliative care pathway",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 5: BIOLOGY-BASED FLAGS (Rule 5A, 5B)
    # ═══════════════════════════════════════════════════════════════════════

    # Rule 5A: Triple Negative / HER2+
    if is_triple_negative:
        flags.append("Aggressive biology (Triple Negative) – neoadjuvant chemo recommended for all stages, then surgery")
    if is_her2_positive:
        flags.append("HER2 positive – neoadjuvant chemo + trastuzumab recommended for all stages, then surgery")

    # Rule 5B: Elderly / Frail
    if age > 70 and overall_numeric <= 2 and not node_positive:
        flags.append("Elderly with low-risk disease – consider BCS/hypofractionation")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 3: LOCALLY ADVANCED BREAST CANCER (Stage III / neoadjuvant)
    # ═══════════════════════════════════════════════════════════════════════
    is_labc = overall_numeric == 3 or neoadjuvant_chemo

    if is_labc:
        reasoning_parts.append("Locally advanced breast cancer (Stage III or neoadjuvant chemo given)")

        # Luminal A LABC – NACT AC + Pacli, then surgery; if no response, pre-op RT
        if is_luminal_a:
            flags.append("Luminal A LABC – endocrine-responsive; favorable biology")
            nact_regimen = "Neoadjuvant chemotherapy: AC 4 cycles + Paclitaxel 4 cycles"
            if not surgery_done:
                recommendations.append(nact_regimen)
                recommendations.append("If no response to chemo, consider pre-operative RT")
                reasoning_parts.append("Luminal A LABC: NACT for downstaging; pre-op RT if no response")
            if surgery_done and neoadjuvant_chemo:
                recommendations.append("Continue adjuvant endocrine; consider CDK4/6 inhibitor if high-risk")

        # HER2+ LABC – TCHP ×6; T-DM1 if residual
        if is_her2_positive and not surgery_done:
            recommendations.append("Neoadjuvant TCHP (Docetaxel + Carboplatin + Trastuzumab + Pertuzumab) ×6 cycles")
            reasoning_parts.append("HER2+ LABC: neoadjuvant HER2 blockade; T-DM1 if residual disease post-surgery")

        # TNBC LABC – dose-dense anthracycline + taxane; consider platinum/immunotherapy
        if is_triple_negative and not surgery_done:
            recommendations.append("Neoadjuvant chemotherapy: dose-dense AC + paclitaxel; consider platinum; consider immunotherapy if eligible")

        if surgery_done:
            # Rule 3A: LABC after Surgery
            rt_target = "Chest wall" if surgery_t in ("MRM", "MASTECTOMY") else "Whole breast"
            recommendations.append(f"{rt_target} + Regional nodal irradiation")
            reasoning_parts.append("Post-surgery RT: chest wall/breast + regional nodes indicated")

            surgery_rec = f"{surgery_type} completed"
            systemic = ""
            if neoadjuvant_chemo:
                systemic = f"Neoadjuvant chemotherapy completed (response: {chemo_response})"
                if is_triple_negative and chemo_resp in ("partial", "residual"):
                    systemic += "; consider capecitabine (residual disease)"
                if is_her2_positive:
                    systemic += "; continue trastuzumab ± pertuzumab; switch to T-DM1 for 14 cycles if residual disease"
            if is_hr_positive:
                if "pre" in meno:
                    systemic += "; Endocrine therapy: Tamoxifen"
                else:
                    systemic += "; Endocrine therapy: Aromatase inhibitor"
                if not is_luminal_a:
                    systemic += "; consider CDK4/6 inhibitor if high-risk"

            # RT details
            if surgery_t in ("MRM", "MASTECTOMY"):
                rt_detail = (
                    "PMRT indicated\n"
                    "Targets: Chest wall + SCF + Axilla level II-III"
                )
            else:
                rt_detail = (
                    "Adjuvant RT indicated\n"
                    "Targets: Whole breast + regional nodes (SCF"
                )
                if imn_involvement or quad in ("central", "upper inner", "lower inner"):
                    rt_detail += " + IMN"
                rt_detail += ")"

            # Dose
            if surgery_t == "BCS":
                rt_detail += "\nDose: 40 Gy / 15 fractions"
                if age < 50 or grade >= 3 or margin == "close":
                    rt_detail += "\nBoost to tumor bed recommended"
            else:
                rt_detail += "\nDose: 50 Gy / 25 fractions"

            rt_detail += "\nTechnique: 3DCRT/IMRT"
            if laterality.lower() == "left":
                rt_detail += "\nOAR: DIBH advised (left-sided); heart mean dose < 4 Gy"

            return BreastDecisionResult(
                primary_recommendation="; ".join(recommendations),
                confidence=Confidence.GREEN,
                reasoning="; ".join(reasoning_parts),
                flags=flags,
                mdt_required=bool(flags),
                case_summary=case_summary,
                surgery_recommendation=surgery_rec,
                systemic_therapy=systemic.strip("; "),
                radiation_therapy=rt_detail,
                follow_up="Clinical exam every 6 months, annual mammogram",
            )

        else:
            # Inoperable / unresectable after NACT
            if not surgery_feasible_after_nact:
                recommendations.append("Second-line chemotherapy / pre-operative radiotherapy, then reassess for surgery")
                flags.append("Inoperable after neoadjuvant chemo – MDT required")
                mdt_required = True
                confidence = Confidence.RED
                reasoning_parts.append("Surgery not feasible after neoadjuvant chemo")

                return BreastDecisionResult(
                    primary_recommendation="Second-line chemo / pre-operative RT; reassess for surgery",
                    confidence=Confidence.RED,
                    reasoning="; ".join(reasoning_parts),
                    flags=flags,
                    mdt_required=True,
                    case_summary=case_summary,
                    surgery_recommendation="Not feasible – reassess after further therapy",
                    systemic_therapy="Second-line chemotherapy",
                    radiation_therapy="Consider pre-operative RT",
                    follow_up="MDT reassessment after therapy",
                )
            else:
                # Neoadjuvant given, surgery pending
                recommendations.append("Proceed to surgery, then chest wall/breast + regional nodal RT")
                reasoning_parts.append("Neoadjuvant chemo given; surgery feasible; plan post-op RT")

                if chemo_resp == "not applicable" and is_luminal_a:
                    systemic = "Neoadjuvant chemotherapy: AC 4 cycles + Paclitaxel 4 cycles (recommended). If no response, consider pre-operative RT. Then surgery; then endocrine therapy long-term; CDK4/6 inhibitor may be considered (very high-risk)."
                else:
                    systemic = f"Neoadjuvant chemotherapy given (response: {chemo_response})"
                    if is_her2_positive:
                        systemic += "; continue trastuzumab ± pertuzumab; T-DM1 for 14 cycles if residual disease"
                    if is_triple_negative and chemo_resp in ("partial", "residual"):
                        systemic += "; consider capecitabine post-surgery"
                    if is_luminal_a:
                        systemic += "; Continue endocrine therapy long-term; CDK4/6 inhibitor may be considered (very high-risk)"

                rt_pending = "Post-surgery: chest wall/breast + regional nodal RT"
                if is_luminal_a:
                    rt_pending = (
                        "Mandatory: Chest wall + regional nodal irradiation (axilla + SCF; + IMN if multiple axillary nodes positive). "
                        "Dose: 50 Gy / 2 Gy per fraction / 25#. DIBH for all left-sided breast cancers. Technique: 3DCRT."
                    )

                if is_her2_positive:
                    surgery_rec = "Modified radical mastectomy after response to neoadjuvant HER2 therapy"
                else:
                    surgery_rec = "Modified radical mastectomy after adequate downstaging with chemo" if is_luminal_a else "BCS or MRM – MDT to decide based on response"

                return BreastDecisionResult(
                    primary_recommendation="Surgery followed by adjuvant chest wall/breast + regional nodal RT",
                    confidence=Confidence.AMBER,
                    reasoning="; ".join(reasoning_parts),
                    flags=flags,
                    mdt_required=bool(flags),
                    case_summary=case_summary,
                    surgery_recommendation=surgery_rec,
                    systemic_therapy=systemic,
                    radiation_therapy=rt_pending,
                    follow_up="Clinical exam every 6 months; long-term endocrine compliance monitoring" if is_luminal_a else "Clinical exam every 6 months, annual mammogram",
                )

    # ═══════════════════════════════════════════════════════════════════════
    # STEP 2: EARLY BREAST CANCER (Stage I-II)
    # ═══════════════════════════════════════════════════════════════════════

    if not surgery_done:
        # Surgery not yet done for early-stage – recommend surgery
        if is_triple_negative or is_her2_positive:
            rec = "Neoadjuvant chemotherapy"
            if is_her2_positive:
                rec += " (TCHP or paclitaxel + trastuzumab) + trastuzumab to complete 1 year"
            else:
                rec += " (dose-dense AC + paclitaxel)"
            if brca_mutation and is_triple_negative:
                rec += "; consider platinum-based regimen; consider PARP inhibitor if high-risk"
            rec += ", then surgery"
            return BreastDecisionResult(
                primary_recommendation=rec,
                confidence=Confidence.GREEN,
                reasoning="Early-stage with aggressive biology; neoadjuvant approach recommended",
                flags=flags,
                mdt_required=bool(flags),
                case_summary=case_summary,
                surgery_recommendation="Planned after neoadjuvant therapy",
                systemic_therapy=rec,
                radiation_therapy="To be determined post-surgery",
                follow_up="Reassess after neoadjuvant therapy",
            )

        # Elderly/comorbid: primary endocrine acceptable (Luminal A or Luminal B)
        if age >= 70 and ecog >= 2 and is_hr_positive:
            return BreastDecisionResult(
                primary_recommendation="Primary endocrine therapy acceptable; surgery optional based on fitness",
                confidence=Confidence.AMBER,
                reasoning="Elderly with competing mortality risk; hormone-responsive biology. Life expectancy–adjusted treatment; avoid overtreatment.",
                flags=flags + ["Competing mortality risk high – consider primary endocrine therapy"],
                mdt_required=True,
                case_summary=case_summary,
                surgery_recommendation="Surgery optional based on fitness",
                systemic_therapy="Chemotherapy not indicated. Endocrine: AI preferred if tolerated; Tamoxifen if frailty / bone risk.",
                radiation_therapy="Can be omitted",
                follow_up="Symptom-based follow-up; imaging only if clinically indicated.",
            )

        if is_luminal_a:
            surgery_rec = (
                "Breast-conserving surgery (preferred) OR Mastectomy (based on patient preference). "
                "Luminal A: BCS preferred when feasible."
            )
            if prior_chest_rt:
                surgery_rec = "Mastectomy recommended (prior chest irradiation); SLNB indicated. Avoid re-irradiation."
            return BreastDecisionResult(
                primary_recommendation="Surgery recommended: BCS preferred or mastectomy per preference",
                confidence=Confidence.GREEN,
                reasoning="Early-stage Luminal A; surgery first. Neoadjuvant chemo not routinely indicated.",
                flags=flags,
                mdt_required=bool(flags),
                case_summary=case_summary,
                surgery_recommendation=surgery_rec,
                systemic_therapy="Chemotherapy not routinely indicated; consider genomic assay (e.g. CANASSIST) if age <40. Endocrine therapy post-surgery.",
                radiation_therapy="To be determined post-surgery (WBI if BCS; consider RT omission if age ≥70, tumor ≤2 cm, compliant with endocrine therapy). Contraindicated if prior chest RT.",
                follow_up="Post-surgical pathology will guide adjuvant treatment; annual mammography.",
            )

        return BreastDecisionResult(
            primary_recommendation="Surgery recommended (BCS or mastectomy based on clinical assessment)",
            confidence=Confidence.AMBER,
            reasoning="Early-stage breast cancer; surgery not yet performed. Surgical planning needed.",
            flags=flags,
            mdt_required=bool(flags),
            case_summary=case_summary,
            surgery_recommendation="BCS or mastectomy – clinical decision",
            systemic_therapy="To be determined post-surgery",
            radiation_therapy="To be determined post-surgery",
            follow_up="Post-surgical pathology will guide adjuvant treatment",
        )

    # ── A. Post-BCS (Rule 2A) ──
    if surgery_t == "BCS":
        reasoning_parts.append(f"Post-BCS, {t_stage}, margins {margin}")

        # Luminal A: RT omission consideration (PRIME II / CALGB) for age ≥70, tumor ≤2 cm, compliant with ET
        if is_luminal_a and prior_chest_rt:
            recommendations.append("RT contraindicated due to prior chest irradiation")
            rt_detail = "Radiotherapy contraindicated due to prior chest RT. Avoid re-irradiation."
        elif is_luminal_a and age >= 70 and tumor_size_cm <= 2 and not node_positive:
            recommendations.append("Whole breast RT recommended; consider RT omission if compliant with endocrine therapy (PRIME II / CALGB)")
            rt_detail = (
                "Whole breast RT recommended. Consider RT omission if: age ≥70, tumor ≤2 cm, compliant with endocrine therapy.\n"
                "If RT given: 40 Gy / 2.67 Gy per fraction / 15# or 50 Gy / 2 Gy per fraction / 25#.\n"
                "Technique: 3DCRT. DIBH advised for left-sided."
            )
        elif _is_early_t(t_stage) and margin in ("negative", "close"):
            # Whole breast irradiation
            rt_rec = "Whole breast irradiation (WBI)"
            boost = False

            # Boost decision (age <50, LVI, high grade, close margins)
            if age < 50 or grade >= 3 or margin == "close" or lvi:
                rt_rec += " with tumor bed boost"
                boost = True
                boost_reasons = []
                if age < 50:
                    boost_reasons.append("young age")
                if grade >= 3:
                    boost_reasons.append("high grade")
                if margin == "close":
                    boost_reasons.append("close margins")
                if lvi:
                    boost_reasons.append("LVI")
                reasoning_parts.append(f"Boost indicated ({', '.join(boost_reasons)})")

            recommendations.append(rt_rec)

            # Dose/fractionation (Luminal A: 40Gy/15# or 50Gy/25#)
            rt_detail = (
                "Adjuvant RT\n"
                "Whole breast irradiation\n"
                "Dose: 40 Gy / 15 fractions"
            )
            if is_luminal_a:
                rt_detail = (
                    "Whole breast RT indicated if BCS.\n"
                    "Dose: 40 Gy / 2.67 Gy per fraction / 15# or 50 Gy / 2 Gy per fraction / 25#.\n"
                    "Technique: 3DCRT"
                )
            if boost and not is_luminal_a:
                rt_detail += "\nBoost: tumor bed boost recommended"
            elif boost and is_luminal_a:
                rt_detail += "\nBoost to tumor bed if age <50 or grade ≥3 or close margins"
            if not is_luminal_a:
                rt_detail += "\nTechnique: 3DCRT"
            if laterality.lower() == "left":
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

        # Systemic therapy for early stage
        systemic_parts = []
        if is_luminal_a:
            systemic_parts.append("Chemotherapy: not routinely indicated")
            if age < 40:
                systemic_parts.append("Consider genomic assay (e.g. CANASSIST) due to age <40 to confirm chemo omission")
            if node_positive:
                systemic_parts.append("Genomic testing strongly recommended (node-positive Luminal A)")
            elif not node_positive and tumor_size_cm <= 2 and grade <= 1 and "post" in meno:
                systemic_parts.append("Genomic testing not required (very low risk, screen-detected type)")
            elif not node_positive:
                systemic_parts.append("Genomic testing recommended (node-negative, ER+, HER2-) to confirm chemo omission")
            if "pre" in meno:
                systemic_parts.append("Endocrine: Tamoxifen × 5–10 years; consider ovarian suppression + AI if high-risk features on genomic testing")
            else:
                systemic_parts.append("Endocrine: Aromatase inhibitor × 5 years (Tamoxifen if AI contraindicated)")
        elif is_hr_positive:
            if "pre" in meno:
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
            systemic_parts.append("Paclitaxel weekly ×12 + Trastuzumab to complete 1 year (consider de-escalated regimen per APT trial if small node-negative)")

        # Regional nodal irradiation (Step 4)
        rni_detail = ""
        if node_positive or scf_involvement or imn_involvement:
            rni_parts = ["Axillary", "Supraclavicular"]
            if imn_involvement or quad in ("central", "upper inner", "lower inner"):
                rni_parts.append("IMN")
            rni_detail = f"\nRegional nodal irradiation: {' + '.join(rni_parts)}"
            rt_detail += rni_detail
            reasoning_parts.append("RNI indicated (node-positive or nodal involvement)")

        follow_up_bcs = "Clinical exam every 6 months, annual mammogram"
        if is_luminal_a and "post" in meno:
            follow_up_bcs = "Annual mammography; clinical exam every 6–12 months; bone health monitoring (AI)"

        return BreastDecisionResult(
            primary_recommendation="; ".join(recommendations),
            confidence=confidence,
            reasoning="; ".join(reasoning_parts),
            flags=flags,
            mdt_required=bool([f for f in flags if "MDT" in f]),
            case_summary=case_summary,
            surgery_recommendation="BCS completed",
            systemic_therapy="; ".join(systemic_parts) if systemic_parts else "Not indicated",
            radiation_therapy=rt_detail,
            follow_up=follow_up_bcs,
        )

    # ── B. Post-Mastectomy (Rules 2B, 2C) ──
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
            if imn_involvement or quad in ("central", "upper inner", "lower inner"):
                rni_parts.append("IMN")

            rt_detail = (
                "PMRT indicated\n"
                f"Targets: Chest wall + {' + '.join(rni_parts)}\n"
                "Dose: 50 Gy / 25 fractions\n"
                "Technique: 3DCRT"
            )

        if laterality.lower() == "left":
            rt_detail += "\nOAR: DIBH advised; heart mean dose < 4 Gy"

        # Systemic therapy
        systemic_parts = []
        if is_luminal_a:
            if node_positive:
                systemic_parts.append("Chemotherapy: Docetaxel + Cyclophosphamide × 4 cycles")
                systemic_parts.append("Genomic testing strongly recommended (RxPONDER: chemo benefit limited in postmenopausal, selective in premenopausal)")
                if "pre" in meno or "peri" in meno:
                    systemic_parts.append("Endocrine: Ovarian suppression + AI (preferred) or Tamoxifen if low risk")
                else:
                    systemic_parts.append("Endocrine: Aromatase inhibitor")
            else:
                systemic_parts.append("Chemotherapy: not indicated")
                if "pre" in meno:
                    systemic_parts.append("Endocrine: Tamoxifen × 5–10 years")
                else:
                    systemic_parts.append("Endocrine: Aromatase inhibitor × 5 years (Tamoxifen if AI contraindicated)")
        elif is_hr_positive:
            if "pre" in meno:
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

        return BreastDecisionResult(
            primary_recommendation="; ".join(recommendations),
            confidence=confidence,
            reasoning="; ".join(reasoning_parts),
            flags=flags,
            mdt_required=mdt_required or bool([f for f in flags if "MDT" in f]),
            case_summary=case_summary,
            surgery_recommendation=f"{surgery_type} completed",
            systemic_therapy="; ".join(systemic_parts) if systemic_parts else "Not indicated",
            radiation_therapy=rt_detail,
            follow_up=follow_up_mrm,
        )

    # Fallback – should not normally reach here
    return BreastDecisionResult(
        primary_recommendation="MDT discussion required – unable to determine recommendation",
        confidence=Confidence.RED,
        reasoning="Case parameters did not match standard decision tree pathways",
        flags=["Unclassified case – MDT required"],
        mdt_required=True,
        case_summary=case_summary,
    )


