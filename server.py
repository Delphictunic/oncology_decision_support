"""
Unified Oncology Clinical Decision Support MCP Server
Cervix | Head & Neck SCC | Breast Cancer
AJCC 8th Edition | Institutional Protocols v1.0
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from engines.cervix.models import CervixInput
from engines.cervix.cervix_engine import evaluate_cervix_case
from engines.headneck.hn_models import HNInput
from engines.headneck.hn_engine import evaluate_hn_case
from engines.headneck.hn_config import ESSENTIAL_PARAMS, ORAL_CAVITY_EXTRA_PARAMS
from engines.breast.breast_engine import evaluate_breast_case


# ─────────────────────────────────────────────────────────────────────────────
# Breast: required params and missing-parameter check
# ─────────────────────────────────────────────────────────────────────────────

BREAST_ESSENTIAL_PARAMS = [
    "age", "sex", "ecog", "menopausal_status", "laterality", "histology",
    "tumor_size_cm", "grade", "lvi", "n_stage", "nodes_examined", "nodes_positive",
    "m_stage", "er_status", "pr_status", "her2_status", "t_stage", "overall_stage", "surgery_done",
]
BREAST_FIELD_HINTS = {
    "age": "age (numeric, years)",
    "sex": "sex (female | male)",
    "ecog": "ecog (0 | 1 | 2 | 3 | 4)",
    "menopausal_status": "menopausal_status (premenopausal | perimenopausal | postmenopausal)",
    "laterality": "laterality (left | right)",
    "histology": "histology (invasive ductal carcinoma | invasive lobular carcinoma | DCIS | other)",
    "tumor_size_cm": "tumor_size_cm (numeric, centimeters)",
    "grade": "grade (1 | 2 | 3  — Nottingham grade)",
    "lvi": "lvi — lymphovascular invasion (true | false)",
    "n_stage": "n_stage (N0 | N1 | N2 | N3 | pN0 | pN1 … etc.)",
    "nodes_examined": "nodes_examined (numeric — total nodes examined)",
    "nodes_positive": "nodes_positive (numeric — positive nodes)",
    "m_stage": "m_stage (M0 | M1)",
    "er_status": "er_status (positive | negative)",
    "pr_status": "pr_status (positive | negative)",
    "her2_status": "her2_status (positive | negative)",
    "t_stage": "t_stage (T1 | T1a | T1b | T1c | T2 | T3 | T4 … etc.)",
    "overall_stage": "overall_stage (IA | IB | IIA | IIB | IIIA | IIIB | IIIC | IV)",
    "surgery_done": "surgery_done (true | false)",
}
BREAST_SURGERY_PARAMS = {
    "surgery_type": "surgery_type (BCS | MRM | mastectomy | none)",
    "margin_status": "margin_status (negative | close | positive | unknown)",
}


def _check_missing_breast(params: dict) -> Optional[str]:
    missing = []
    for p in BREAST_ESSENTIAL_PARAMS:
        if params.get(p) is None:
            missing.append(BREAST_FIELD_HINTS.get(p, p))
    if params.get("surgery_done") is True:
        for p, hint in BREAST_SURGERY_PARAMS.items():
            if params.get(p) is None:
                missing.append(hint)
    if not missing:
        return None
    return "To generate the treatment recommendation, please provide the following:\n" + "\n".join(f"• {m}" for m in missing)


# ─────────────────────────────────────────────────────────────────────────────
# Head & Neck: missing-parameter check
# ─────────────────────────────────────────────────────────────────────────────

HN_FIELD_HINTS = {
    "age": "age (numeric, years)",
    "ecog": "ecog (0 | 1 | 2 | 3 | 4)",
    "primary_site": "primary_site (oral_cavity | oropharynx | hypopharynx | larynx)",
    "ajcc_stage": "ajcc_stage (I | II | III | IVA | IVB | IVC)",
    "t_stage": "t_stage (T1 | T2 | T3 | T4a | T4b)",
    "n_stage": "n_stage (N0 | N1 | N2a | N2b | N2c | N3)",
    "distant_metastasis": "distant_metastasis (true | false)",
    "resectable": "resectable (true | false)",
    "creatinine_clearance": "creatinine_clearance (numeric ml/min)",
    "oral_subsite": "oral_subsite (oral_tongue | buccal_mucosa | floor_of_mouth | retromolar_trigone | alveolus_mandibular | alveolus_maxillary | hard_palate | lip)",
    "doi_mm": "doi_mm — depth of invasion in mm (numeric)",
}


def _check_missing_hnscc(params: dict) -> Optional[str]:
    missing = []
    for p in ESSENTIAL_PARAMS:
        if params.get(p) is None:
            missing.append(HN_FIELD_HINTS.get(p, p))
    if params.get("primary_site") == "oral_cavity":
        for p in ORAL_CAVITY_EXTRA_PARAMS:
            if params.get(p) is None:
                missing.append(HN_FIELD_HINTS.get(p, p))
    if not missing:
        return None
    return "To generate the treatment recommendation, please provide the following:\n" + "\n".join(f"• {m}" for m in missing)


# ─────────────────────────────────────────────────────────────────────────────
# Breast: 12-section output formatter (presentation only, no engine logic)
# ─────────────────────────────────────────────────────────────────────────────

def _pos_neg(val: str) -> str:
    v = val.lower().strip()
    return "Positive (+)" if v == "positive" else "Negative (−)"


def _mol_subtype(er, pr, her2, grade, ki67) -> str:
    er_ = er.lower().strip()
    pr_ = pr.lower().strip()
    her_ = her2.lower().strip()
    tn = (er_ == "negative" and pr_ == "negative" and her_ == "negative")
    hrp = (er_ == "positive" or pr_ == "positive")
    h2p = (her_ == "positive")
    if tn:
        return "Triple-Negative Breast Cancer (TNBC)"
    if h2p and hrp:
        return "Luminal B (HER2-positive)"
    if h2p:
        return "HER2-Enriched"
    if hrp:
        ki = ki67 if ki67 is not None else 99
        if er_ == "positive" and pr_ == "positive" and her_ == "negative" and grade <= 2 and ki <= 20:
            return "Luminal A"
        return "Luminal B (HER2-negative)"
    return "Unclassified"


def _disease_category(overall_stage: str) -> str:
    s = overall_stage.upper().strip()
    if s in ("IA", "IB", "I", "IIA", "IIB", "II"):
        return "Early Breast Cancer (Stage I–II)"
    if s in ("IIIA", "IIIB", "IIIC", "III"):
        return "Locally Advanced Breast Cancer (Stage III)"
    if s == "IV":
        return "Metastatic Breast Cancer (Stage IV)"
    return f"Stage {overall_stage}"


def _treatment_intent(overall_stage: str, confidence_val: str) -> str:
    s = overall_stage.upper().strip()
    if s == "IV":
        return "Palliative / Disease control"
    if confidence_val == "red":
        return "MDT decision required"
    return "Curative"


def _risk_summary(tumor_size_cm, grade, n_stage, nodes_positive, ki67_percent, overall_stage, age, lvi) -> list:
    parts = []
    if tumor_size_cm <= 2:
        parts.append(f"Tumor size: {tumor_size_cm} cm (T1/T2 range — small)")
    elif tumor_size_cm <= 5:
        parts.append(f"Tumor size: {tumor_size_cm} cm (intermediate)")
    else:
        parts.append(f"Tumor size: {tumor_size_cm} cm (large — >5 cm)")
    grade_labels = {1: "Low grade (Grade 1)", 2: "Intermediate grade (Grade 2)", 3: "High grade (Grade 3)"}
    parts.append(f"Tumor grade: {grade_labels.get(grade, f'Grade {grade}')}")
    n = n_stage.replace("p", "").replace("c", "").upper()
    if n.startswith("N0"):
        parts.append("Nodal involvement: Node-negative (N0)")
    elif nodes_positive > 0:
        parts.append(f"Nodal involvement: {nodes_positive} positive node(s) — {n_stage}")
    else:
        parts.append(f"Nodal involvement: {n_stage}")
    if ki67_percent is not None:
        ki_risk = "low" if ki67_percent <= 20 else "high"
        parts.append(f"Proliferation index (Ki-67): {ki67_percent}% ({ki_risk} proliferation)")
    else:
        parts.append("Proliferation index (Ki-67): Not provided")
    if lvi:
        parts.append("Lymphovascular invasion: Present")
    if age < 40:
        parts.append(f"Age: {age} years — very young (elevated risk)")
    elif age < 50:
        parts.append(f"Age: {age} years — premenopausal age group")
    elif age >= 70:
        parts.append(f"Age: {age} years — elderly (competing mortality consideration)")
    else:
        parts.append(f"Age: {age} years")
    return parts


def _genomic_testing_section(er, pr, her2, n_stage, nodes_positive, overall_stage, ki67_percent, age) -> str:
    er_, pr_ = er.lower().strip(), pr.lower().strip()
    h_ = her2.lower().strip()
    hrp = (er_ == "positive" or pr_ == "positive")
    h2n = (h_ == "negative")
    np = nodes_positive
    if not hrp or not h2n:
        return "Not routinely indicated for this subtype"
    s = overall_stage.upper().strip()
    if s == "IV":
        return "ESR1 / PIK3CA mutation testing recommended for metastatic HR+ disease"
    lines = ["Indicated (ER+/HER2-negative disease)"]
    if np == 0:
        lines.append("Node-negative — standard indication for genomic assay")
    elif np <= 3:
        lines.append("1–3 positive nodes — genomic testing recommended (RxPONDER criteria)")
    else:
        lines.append("≥4 positive nodes — chemotherapy generally indicated regardless of genomic score")
    if age < 40:
        lines.append("Age <40: CANASSIST or Oncotype DX strongly recommended to confirm chemotherapy omission")
    elif age < 50:
        lines.append("Age <50: CANASSIST or Oncotype DX recommended")
    else:
        lines.append("Recommended assay: CANASSIST / Oncotype DX")
    lines.append("Purpose: Guide decision on adjuvant chemotherapy omission vs. inclusion")
    return "\n".join(f"  • {l}" for l in lines)


def _format_breast_output(result, inputs: dict) -> str:
    r, age = result, inputs["age"]
    sex, ecog = inputs["sex"], inputs["ecog"]
    meno = inputs["menopausal_status"]
    lat, histo = inputs["laterality"].capitalize(), inputs["histology"]
    sz, grade, lvi = inputs["tumor_size_cm"], inputs["grade"], inputs["lvi"]
    n_stage = inputs["n_stage"]
    n_pos, n_exam = inputs["nodes_positive"], inputs["nodes_examined"]
    m_stage = inputs["m_stage"]
    er, pr, her2 = inputs["er_status"], inputs["pr_status"], inputs["her2_status"]
    t_stage, o_stage = inputs["t_stage"], inputs["overall_stage"]
    sx_done = inputs["surgery_done"]
    sx_type = inputs.get("surgery_type", "none")
    margin = inputs.get("margin_status", "unknown")
    ki67 = inputs.get("ki67_percent")
    nact = inputs.get("neoadjuvant_chemo", False)
    chemo_r = inputs.get("chemo_response", "not applicable")
    brca = inputs.get("brca_mutation", False)
    pdl1 = inputs.get("pdl1_positive")
    subtype = _mol_subtype(er, pr, her2, grade, ki67)
    disease_cat = _disease_category(o_stage)
    intent = _treatment_intent(o_stage, r.confidence.value)
    risk_lines = _risk_summary(sz, grade, n_stage, n_pos, ki67, o_stage, age, lvi)
    genomics = _genomic_testing_section(er, pr, her2, n_stage, n_pos, o_stage, ki67, age)
    systemic_raw = r.systemic_therapy or "Not indicated"
    chemo_lines, targeted_lines, endocrine_lines = [], [], []
    for part in systemic_raw.split(";"):
        p = part.strip()
        if not p:
            continue
        pl = p.lower()
        if any(k in pl for k in ["tamoxifen", "aromatase", "ai ", "ai.", "ovarian suppression", "endocrine", "fulvestrant"]):
            endocrine_lines.append(p)
        elif any(k in pl for k in ["trastuzumab", "pertuzumab", "t-dm1", "cdk4/6", "parp", "olaparib", "cdk 4/6", "bevacizumab", "pembrolizumab", "immunotherapy"]):
            targeted_lines.append(p)
        else:
            chemo_lines.append(p)
    chemo_str = "\n".join(f"  • {l}" for l in chemo_lines) if chemo_lines else "  • Not indicated"
    targeted_str = "\n".join(f"  • {l}" for l in targeted_lines) if targeted_lines else "  • Not applicable"
    endocrine_str = "\n".join(f"  • {l}" for l in endocrine_lines) if endocrine_lines else "  • Not applicable"
    flags_str = "\n".join(f"  ⚑ {f}" for f in r.flags) if r.flags else "  None"
    if nact:
        nact_indicated = "Indicated (given)"
        nact_purpose = f"Purpose: Tumor downstaging / increase BCS feasibility / assess treatment response\n  • Response: {chemo_r.upper()}"
    elif any(k in systemic_raw.lower() for k in ["neoadjuvant", "nact", "tchp", "dose-dense ac"]):
        nact_indicated = "Indicated (recommended pre-surgery)"
        nact_purpose = "Purpose: Tumor downstaging / increase BCS feasibility / assess treatment response"
    else:
        nact_indicated = "Not indicated"
        nact_purpose = "Surgery-first approach"
    rt_raw = r.radiation_therapy or "To be determined"
    if sx_done:
        surgery_str = f"  • Procedure: {sx_type.upper()}\n  • Margins: {margin.capitalize()}\n  • {r.surgery_recommendation}"
    else:
        surgery_str = f"  • {r.surgery_recommendation}"
    out = ""
    out += "1 Case Summary\n"
    out += f"  • Age: {age} years\n  • Sex: {sex.capitalize()}\n  • ECOG Performance Status: {ecog}\n  • Menopausal Status: {meno.capitalize()}\n"
    out += f"  • Diagnosis: {lat} breast — {histo}\n  • Histology: {histo.capitalize()}\n  • Tumor Size: {sz} cm\n  • Grade: {grade} (Nottingham)\n"
    out += f"  • Stage (TNM): {t_stage} {n_stage} {m_stage} → Overall Stage {o_stage}\n  • Biomarkers:\n"
    out += f"      ER:    {_pos_neg(er)}\n      PR:    {_pos_neg(pr)}\n      HER2:  {_pos_neg(her2)}\n"
    ki67_display = f"{ki67}%" if ki67 is not None else "Not provided"
    out += f"      Ki-67: {ki67_display}\n"
    if brca:
        out += "      BRCA mutation: Positive\n"
    if pdl1 is not None:
        out += f"      PD-L1: {'Positive' if pdl1 else 'Negative'}\n"
    out += "\n2 Molecular Subtype Classification\n  • " + subtype + "\n\n"
    out += "3 Disease Category\n  • " + disease_cat + "\n\n"
    out += "4 Risk Stratification\n"
    for line in risk_lines:
        out += f"  • {line}\n"
    out += "\n5 Treatment Intent\n  • " + intent + "\n\n"
    out += "6 Primary Treatment Strategy\n  Surgery\n" + surgery_str + "\n\n"
    out += "7 Systemic Therapy Strategy\n  Chemotherapy\n" + chemo_str + "\n  Targeted Therapy\n" + targeted_str + "\n  Endocrine Therapy (HR-positive)\n" + endocrine_str + "\n\n"
    out += "8 Role of Neoadjuvant Therapy\n  • " + nact_indicated + "\n  • " + nact_purpose + "\n\n"
    out += "9 Radiotherapy Decision Module\n" + rt_raw + "\n\n"
    out += "10 Genomic / Predictive Testing\n" + genomics + "\n\n"
    out += "11 Guideline Rationale\n  • " + r.reasoning + "\n  • Treatment aligned with NCCN / ESMO guidelines\n"
    if r.flags:
        out += "  Clinical flags:\n" + flags_str + "\n"
    out += "\n12 Follow-Up & Surveillance\n"
    for fl in (r.follow_up or "As per institutional protocol").split(";"):
        fl = fl.strip()
        if fl:
            out += f"  • {fl}\n"
    out += "  • Annual mammography\n  • Monitor treatment toxicity and endocrine therapy compliance\n"
    out += f"\nConfidence → {r.confidence.value}\nMDT Required → {r.mdt_required}\nProtocol Reference → {r.protocol_reference}"
    return out


# ─────────────────────────────────────────────────────────────────────────────
# MCP Server
# ─────────────────────────────────────────────────────────────────────────────

mcp = FastMCP(
    "Oncology Decision Support",
    instructions=(
        "You are a clinical decision support assistant for oncology (Cervix, Head & Neck SCC, Breast).\n"
        "You have three tools: cervix_cancer, hnscc_decision, breast_cancer. Use the one that matches the user's cancer type.\n\n"
        "Collect ALL required parameters for the chosen tool BEFORE calling it. If any are missing, ask for them in one message and do NOT call the tool.\n"
        "NEVER infer or assume parameter values (e.g. do not assume ECOG 0 from 'fit').\n\n"
        "When a tool returns successfully: copy its output to the user EXACTLY as-is. Do NOT summarize, rewrite, or add prose.\n"
        "When a tool returns missing parameters: present them clearly and ask the user to supply them.\n"
        "When a tool errors: respond ONLY with 'TOOL ERROR: Clinical decision engine unavailable. Please retry or contact support.'\n\n"
        "You are NEVER permitted to generate clinical recommendations or treatment plans from your own knowledge. All clinical output must come from the tools."
    ),
)


# ─────────────────────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def cervix_cancer(
    age: int,
    ecog: int,
    figo_stage: str,
    histology: str,
    tumor_size_cm: float,
    pelvic_nodes_positive: bool,
    para_aortic_nodes_positive: bool,
    hydronephrosis: bool,
    creatinine_clearance: float,
    prior_surgery: bool = False,
    margins_positive: bool = False,
    lvsi_present: bool = False,
    parametrial_invasion: bool = False,
    distant_metastasis: bool = False,
    symptomatic_bleeding: bool = False,
    post_crt_residual: bool = False,
) -> str:
    """Evaluate a cervix cancer case. Returns treatment recommendation per Institutional Cervix Cancer Protocol v1.0."""
    try:
        input_data = CervixInput(
            age=age,
            ecog=ecog,
            figo_stage=figo_stage,
            histology=histology,
            tumor_size_cm=tumor_size_cm,
            pelvic_nodes_positive=pelvic_nodes_positive,
            para_aortic_nodes_positive=para_aortic_nodes_positive,
            hydronephrosis=hydronephrosis,
            creatinine_clearance=creatinine_clearance,
            prior_surgery=prior_surgery,
            margins_positive=margins_positive,
            lvsi_present=lvsi_present,
            parametrial_invasion=parametrial_invasion,
            distant_metastasis=distant_metastasis,
            symptomatic_bleeding=symptomatic_bleeding,
            post_crt_residual=post_crt_residual,
        )
        result = evaluate_cervix_case(input_data)
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\nDo NOT answer clinically. Report this error to the user and stop.\n```"


@mcp.tool()
def hnscc_decision(
    age: Optional[int] = None,
    ecog: Optional[int] = None,
    primary_site: Optional[str] = None,
    ajcc_stage: Optional[str] = None,
    t_stage: Optional[str] = None,
    n_stage: Optional[str] = None,
    distant_metastasis: Optional[bool] = None,
    resectable: Optional[bool] = None,
    creatinine_clearance: Optional[float] = None,
    oral_subsite: Optional[str] = None,
    doi_mm: Optional[float] = None,
    bone_invasion: bool = False,
    bilateral_nodes: bool = False,
    prior_surgery: bool = False,
    prior_rt: bool = False,
    margins_positive: bool = False,
    ece_present: bool = False,
    pni_present: bool = False,
    lvi_present: bool = False,
    multiple_positive_nodes: bool = False,
    p16_positive: bool = True,
    hearing_adequate: bool = True,
    recurrent_disease: bool = False,
    post_rt_residual_nodes: bool = False,
    organ_preservation_preferred: bool = False,
    symptomatic_bleeding_or_pain: bool = False,
) -> str:
    """Head & Neck SCC clinical decision support. Required: age, ecog, primary_site, ajcc_stage, t_stage, n_stage, distant_metastasis, resectable, creatinine_clearance. For oral_cavity also: oral_subsite, doi_mm."""
    try:
        params = {
            "age": age, "ecog": ecog, "primary_site": primary_site, "ajcc_stage": ajcc_stage,
            "t_stage": t_stage, "n_stage": n_stage, "distant_metastasis": distant_metastasis,
            "resectable": resectable, "creatinine_clearance": creatinine_clearance,
            "oral_subsite": oral_subsite, "doi_mm": doi_mm,
        }
        missing_msg = _check_missing_hnscc(params)
        if missing_msg:
            return missing_msg
        input_data = HNInput(
            age=age, ecog=ecog, primary_site=primary_site, ajcc_stage=ajcc_stage,
            t_stage=t_stage, n_stage=n_stage, distant_metastasis=distant_metastasis,
            oral_subsite=oral_subsite, doi_mm=doi_mm, bone_invasion=bone_invasion,
            bilateral_nodes=bilateral_nodes, resectable=resectable, prior_surgery=prior_surgery,
            prior_rt=prior_rt, margins_positive=margins_positive, ece_present=ece_present,
            pni_present=pni_present, lvi_present=lvi_present, multiple_positive_nodes=multiple_positive_nodes,
            p16_positive=p16_positive, creatinine_clearance=creatinine_clearance,
            hearing_adequate=hearing_adequate, recurrent_disease=recurrent_disease,
            post_rt_residual_nodes=post_rt_residual_nodes, organ_preservation_preferred=organ_preservation_preferred,
            symptomatic_bleeding_or_pain=symptomatic_bleeding_or_pain,
        )
        result = evaluate_hn_case(input_data)
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\nDo NOT answer clinically. Report this error to the user and stop.\n```"


@mcp.tool()
def breast_cancer(
    age: Optional[int] = None,
    sex: Optional[str] = None,
    ecog: Optional[int] = None,
    menopausal_status: Optional[str] = None,
    laterality: Optional[str] = None,
    histology: Optional[str] = None,
    tumor_size_cm: Optional[float] = None,
    grade: Optional[int] = None,
    lvi: Optional[bool] = None,
    n_stage: Optional[str] = None,
    nodes_examined: Optional[int] = None,
    nodes_positive: Optional[int] = None,
    m_stage: Optional[str] = None,
    er_status: Optional[str] = None,
    pr_status: Optional[str] = None,
    her2_status: Optional[str] = None,
    t_stage: Optional[str] = None,
    overall_stage: Optional[str] = None,
    surgery_done: Optional[bool] = None,
    surgery_type: Optional[str] = None,
    margin_status: Optional[str] = None,
    axillary_procedure: str = "none",
    quadrant: str = "upper outer",
    ki67_percent: Optional[float] = None,
    neoadjuvant_chemo: bool = False,
    chemo_response: str = "not applicable",
    extracapsular_extension: bool = False,
    imn_involvement: bool = False,
    scf_involvement: bool = False,
    symptomatic_metastasis: bool = False,
    surgery_feasible_after_nact: bool = True,
    prior_chest_rt: bool = False,
    progression_on_endocrine: bool = False,
    bone_only_metastases: bool = False,
    visceral_metastases: bool = False,
    brca_mutation: bool = False,
    pdl1_positive: Optional[bool] = None,
) -> str:
    """Evaluate a breast cancer case. Returns 12-section treatment recommendation per Institutional Breast Cancer Protocol v1.0. Required: age, sex, ecog, menopausal_status, laterality, histology, tumor_size_cm, grade, lvi, n_stage, nodes_examined, nodes_positive, m_stage, er_status, pr_status, her2_status, t_stage, overall_stage, surgery_done. If surgery_done=true also: surgery_type, margin_status."""
    try:
        params = {
            "age": age, "sex": sex, "ecog": ecog, "menopausal_status": menopausal_status,
            "laterality": laterality, "histology": histology, "tumor_size_cm": tumor_size_cm,
            "grade": grade, "lvi": lvi, "n_stage": n_stage, "nodes_examined": nodes_examined,
            "nodes_positive": nodes_positive, "m_stage": m_stage, "er_status": er_status,
            "pr_status": pr_status, "her2_status": her2_status, "t_stage": t_stage,
            "overall_stage": overall_stage, "surgery_done": surgery_done,
            "surgery_type": surgery_type if surgery_done is True else "skip",
            "margin_status": margin_status if surgery_done is True else "skip",
        }
        check_params = {k: (None if v == "skip" else v) for k, v in params.items()}
        missing_msg = _check_missing_breast(check_params)
        if missing_msg:
            return missing_msg
        resolved_surgery_type = surgery_type if surgery_type is not None else "none"
        resolved_margin_status = margin_status if margin_status is not None else "unknown"
        result = evaluate_breast_case(
            age=age, sex=sex, ecog=ecog, menopausal_status=menopausal_status,
            laterality=laterality, histology=histology, tumor_size_cm=tumor_size_cm,
            grade=grade, lvi=lvi, n_stage=n_stage, nodes_examined=nodes_examined,
            nodes_positive=nodes_positive, m_stage=m_stage, er_status=er_status,
            pr_status=pr_status, her2_status=her2_status, t_stage=t_stage,
            overall_stage=overall_stage, surgery_done=surgery_done,
            surgery_type=resolved_surgery_type, margin_status=resolved_margin_status,
            axillary_procedure=axillary_procedure, quadrant=quadrant, ki67_percent=ki67_percent,
            neoadjuvant_chemo=neoadjuvant_chemo, chemo_response=chemo_response,
            extracapsular_extension=extracapsular_extension, imn_involvement=imn_involvement,
            scf_involvement=scf_involvement, symptomatic_metastasis=symptomatic_metastasis,
            surgery_feasible_after_nact=surgery_feasible_after_nact, prior_chest_rt=prior_chest_rt,
            progression_on_endocrine=progression_on_endocrine, bone_only_metastases=bone_only_metastases,
            visceral_metastases=visceral_metastases, brca_mutation=brca_mutation,
        )
        inputs = {
            "age": age, "sex": sex, "ecog": ecog, "menopausal_status": menopausal_status,
            "laterality": laterality, "histology": histology, "tumor_size_cm": tumor_size_cm,
            "grade": grade, "lvi": lvi, "n_stage": n_stage, "nodes_examined": nodes_examined,
            "nodes_positive": nodes_positive, "m_stage": m_stage, "er_status": er_status,
            "pr_status": pr_status, "her2_status": her2_status, "t_stage": t_stage,
            "overall_stage": overall_stage, "surgery_done": surgery_done,
            "surgery_type": resolved_surgery_type, "margin_status": resolved_margin_status,
            "ki67_percent": ki67_percent, "neoadjuvant_chemo": neoadjuvant_chemo,
            "chemo_response": chemo_response, "brca_mutation": brca_mutation,
            "pdl1_positive": pdl1_positive,
        }
        formatted = _format_breast_output(result, inputs)
        return "```\n" + formatted + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\nDo NOT answer clinically. Report this error to the user and stop.\n```"


if __name__ == "__main__":
    import sys
    print("Oncology MCP server running (stdio). Waiting for input. Press Ctrl+C to stop.", file=sys.stderr)
    sys.stderr.flush()
    mcp.run(transport="stdio")
