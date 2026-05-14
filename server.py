"""
Unified Oncology Clinical Decision Support MCP Server
═══════════════════════════════════════════════════════════════════════════════
  cervix_cancer    — Cervical cancer (FIGO staging)
  hnscc_decision   — Head & Neck SCC (oral cavity / oropharynx / hypopharynx / larynx)
  breast_cancer    — Breast cancer (early / locally advanced / metastatic)
  gu_prostate      — Prostate cancer (localized / post-RP / mHSPC / CRPC)
  gu_bladder       — Bladder cancer (NMIBC / MIBC / bladder preservation / metastatic)
  gu_testicular    — Testicular GCT (seminoma + NSGCT, Stages 0–III, post-chemo residual)
  gi_cancer        — GI cancers (Esophagus / Stomach / Rectum / Anal / Pancreas / Colon)
  lymphoma         — Lymphoma (Hodgkin + NHL subtypes: DLBCL / FL / MZL / NK-T / PCNSL / MCL / PTCL)
  cns_tumor        — CNS tumours (Glioma / Meningioma / Ependymoma / Medulloblastoma / Pituitary / Craniopharyngioma)
═══════════════════════════════════════════════════════════════════════════════
AJCC 8th Edition | FIGO 2018 | WHO 2021 (CNS) | Lugano (Lymphoma)
Institutional Protocols v1.0

IMPORTANT: Decision-support only. All recommendations require clinical judgment.
Cases flagged RED require MDT discussion before treatment.
"""

from __future__ import annotations
from typing import Optional
from pydantic import ValidationError

from mcp.server.fastmcp import FastMCP

# ── Breast cancer engine (refactored) ──────────────────────────────────────
from engines.breast import evaluate_breast_case, BreastInput, BreastResult, Confidence

# ── Existing engines ──────────────────────────────────────────────────────────
from engines.cervix.models        import CervixInput
from engines.cervix.cervix_engine import evaluate_cervix_case
from engines.headneck.hn_models   import HNInput
from engines.headneck.hn_engine   import evaluate_hn_case
from engines.headneck.hn_config   import ESSENTIAL_PARAMS, ORAL_CAVITY_EXTRA_PARAMS

# ── GU engines ────────────────────────────────────────────────────────────────
from engines.gu.prostate_models   import ProstateInput
from engines.gu.prostate_engine   import evaluate_prostate_case
from engines.gu.bladder_models    import BladderInput
from engines.gu.bladder_engine    import evaluate_bladder_case
from engines.gu.testicular_models import TesticularInput
from engines.gu.testicular_engine import evaluate_testicular_case

# ── New engines ───────────────────────────────────────────────────────────────
from engines.gi.gi_models         import GIInput
from engines.gi.gi_engine         import evaluate_gi_case
from engines.lymphoma.lymphoma_engine import LymphomaInput, evaluate_lymphoma_case
from engines.cns.cns_engine       import CNSInput, evaluate_cns_case


mcp = FastMCP("Oncology Decision Support")


# ═════════════════════════════════════════════════════════════════════════════
# Generic missing-parameter helper (for non-refactored cancer sites)
# ═════════════════════════════════════════════════════════════════════════════

def _check_missing(params: dict, essential: list, hints: dict) -> Optional[str]:
    missing = [hints.get(p, p) for p in essential if params.get(p) is None]
    if not missing:
        return None
    return (
        "To generate the treatment recommendation, please provide the following:\n"
        + "\n".join(f"• {m}" for m in missing)
    )


# ═════════════════════════════════════════════════════════════════════════════
# Pydantic ValidationError formatter (for refactored cancer sites)
# ═════════════════════════════════════════════════════════════════════════════

def format_validation_errors(validation_error: ValidationError) -> str:
    """
    Convert Pydantic ValidationError into user-friendly message.
    Groups errors by field and displays field descriptions from the model.
    """
    error_messages = []
    for error in validation_error.errors():
        field = error.get("loc", ("unknown",))[0]
        msg = error.get("msg", "Invalid value")
        # Combine field name with error message
        error_messages.append(f"• {field}: {msg}")
    
    return (
        "Validation errors in your input. Please provide correct values:\n"
        + "\n".join(error_messages)
    )


# ═════════════════════════════════════════════════════════════════════════════
# Parameter hint maps (for non-refactored cancer sites)
# ═════════════════════════════════════════════════════════════════════════════

HN_ESSENTIAL = ["age","ecog","primary_site","ajcc_stage","t_stage","n_stage","distant_metastasis","resectable","creatinine_clearance"]
HN_HINTS = {
    "age":"age (numeric, years)","ecog":"ecog (0|1|2|3|4)",
    "primary_site":"primary_site (oral_cavity | oropharynx | hypopharynx | larynx)",
    "ajcc_stage":"ajcc_stage (I|II|III|IVA|IVB|IVC)","t_stage":"t_stage (T1|T2|T3|T4a|T4b)",
    "n_stage":"n_stage (N0|N1|N2a|N2b|N2c|N3)","distant_metastasis":"distant_metastasis (true | false)",
    "resectable":"resectable (true | false)","creatinine_clearance":"creatinine_clearance (numeric, mL/min)",
    "oral_subsite":"oral_subsite (oral_tongue | buccal_mucosa | floor_of_mouth | retromolar_trigone | alveolus_mandibular | alveolus_maxillary | hard_palate | lip)",
    "doi_mm":"doi_mm — depth of invasion in mm (numeric)",
}

PROSTATE_ESSENTIAL = ["age","ecog","psa","t_stage","n_stage","m_stage","grade_group","overall_stage","creatinine_clearance"]
PROSTATE_HINTS = {
    "age":"age (numeric, years)","ecog":"ecog (0|1|2|3|4)","psa":"psa (numeric, ng/mL)",
    "t_stage":"t_stage (T1a|T1b|T1c|T2a|T2b|T2c|T3a|T3b|T4)",
    "n_stage":"n_stage (N0 | N1)","m_stage":"m_stage (M0|M1a|M1b|M1c)",
    "grade_group":"grade_group — ISUP Grade Group (1|2|3|4|5)",
    "overall_stage":"overall_stage (I|IIA|IIB|IIC|IIIA|IIIB|IIIC|IVA|IVB)",
    "creatinine_clearance":"creatinine_clearance (numeric, mL/min)",
}

BLADDER_ESSENTIAL = ["age","ecog","t_stage","n_stage","m_stage","grade","histology","turbt_done","creatinine_clearance"]
BLADDER_HINTS = {
    "age":"age (numeric, years)","ecog":"ecog (0|1|2|3|4)",
    "t_stage":"t_stage (Ta|Tis|T1|T2|T2a|T2b|T3|T3a|T3b|T4|T4a|T4b)",
    "n_stage":"n_stage (Nx|N0|N1|N2|N3)","m_stage":"m_stage (M0|M1a|M1b)",
    "grade":"grade (low | high)","histology":"histology (urothelial | scc | adenocarcinoma | other)",
    "turbt_done":"turbt_done (true | false)","creatinine_clearance":"creatinine_clearance (numeric, mL/min)",
}

TESTICULAR_ESSENTIAL = ["age","ecog","histology","t_stage","n_stage","m_stage","s_stage","overall_stage"]
TESTICULAR_HINTS = {
    "age":"age (numeric, years)","ecog":"ecog (0|1|2|3|4)",
    "histology":"histology (seminoma | nsgct | mixed)",
    "t_stage":"t_stage (pTis|pT1|pT1a|pT1b|pT2|pT3|pT4)",
    "n_stage":"n_stage (N0|N1|N2|N3)","m_stage":"m_stage (M0|M1a|M1b)",
    "s_stage":"s_stage (SX|S0|S1|S2|S3)",
    "overall_stage":"overall_stage (0|I|IA|IB|IS|IIA|IIB|IIC|IIIA|IIIB|IIIC)",
}

GI_ESSENTIAL = ["primary_site","age","ecog","histology"]
GI_HINTS = {
    "primary_site":"primary_site (esophagus | stomach | rectum | anal_canal | pancreas | colon)",
    "age":"age (numeric, years)","ecog":"ecog (0|1|2|3|4)",
    "histology":"histology (scc | adenocarcinoma | other)",
}

LYMPHOMA_ESSENTIAL = ["subtype","stage","age","ecog"]
LYMPHOMA_HINTS = {
    "subtype":"subtype (hodgkin | dlbcl | follicular | marginal_zone | nk_t_cell | primary_cns | ptcl | mantle_cell)",
    "stage":"stage (I|II|II_bulky|III|IV)","age":"age (numeric, years)","ecog":"ecog (0|1|2|3|4)",
}

CNS_ESSENTIAL = ["tumour_type","who_grade","age","ecog"]
CNS_HINTS = {
    "tumour_type":"tumour_type (glioma | meningioma | ependymoma | medulloblastoma | pituitary_adenoma | craniopharyngioma)",
    "who_grade":"who_grade (1|2|3|4)","age":"age (numeric, years)","ecog":"ecog (0|1|2|3|4)",
}


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 1 — Cervix
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def cervix_cancer(
    age: Optional[int] = None, figo_stage: Optional[str] = None, histology: Optional[str] = None,
    scc_antigen: Optional[float] = None, pelvic_mass_size_cm: Optional[float] = None,
    parametrial_involvement: bool = False, rectosigmoid_involvement: bool = False,
    bladder_involvement: bool = False, distant_metastasis: bool = False,
) -> str:
    """Cervical cancer decision support (FIGO 2018 staging)."""
    try:
        result = evaluate_cervix_case(CervixInput(
            age=age, figo_stage=figo_stage, histology=histology,
            scc_antigen=scc_antigen, pelvic_mass_size_cm=pelvic_mass_size_cm,
            parametrial_involvement=parametrial_involvement,
            rectosigmoid_involvement=rectosigmoid_involvement,
            bladder_involvement=bladder_involvement,
            distant_metastasis=distant_metastasis,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 2 — Head & Neck SCC
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def hnscc_decision(
    age: Optional[int] = None, ecog: Optional[int] = None,
    primary_site: Optional[str] = None, ajcc_stage: Optional[str] = None,
    t_stage: Optional[str] = None, n_stage: Optional[str] = None,
    distant_metastasis: Optional[bool] = None, resectable: Optional[bool] = None,
    creatinine_clearance: Optional[float] = None, oral_subsite: Optional[str] = None,
    doi_mm: Optional[float] = None, hpv_positive: Optional[bool] = None,
    p16_positive: Optional[bool] = None,
) -> str:
    """Head & Neck SCC decision support (AJCC 8th edition)."""
    try:
        m = _check_missing(
            {"age":age,"ecog":ecog,"primary_site":primary_site,"ajcc_stage":ajcc_stage,
             "t_stage":t_stage,"n_stage":n_stage,"distant_metastasis":distant_metastasis,
             "resectable":resectable,"creatinine_clearance":creatinine_clearance},
            HN_ESSENTIAL, HN_HINTS
        )
        if m: return m
        result = evaluate_hn_case(HNInput(
            age=age, ecog=ecog, primary_site=primary_site, ajcc_stage=ajcc_stage,
            t_stage=t_stage, n_stage=n_stage, distant_metastasis=distant_metastasis,
            resectable=resectable, creatinine_clearance=creatinine_clearance,
            oral_subsite=oral_subsite, doi_mm=doi_mm, hpv_positive=hpv_positive,
            p16_positive=p16_positive,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 3 — Breast (REFACTORED)
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def breast_cancer(
    age: Optional[int] = None, sex: Optional[str] = None, ecog: Optional[int] = None,
    menopausal_status: Optional[str] = None, laterality: Optional[str] = None,
    histology: Optional[str] = None, tumor_size_cm: Optional[float] = None,
    grade: Optional[int] = None, lvi: Optional[bool] = None, n_stage: Optional[str] = None,
    nodes_examined: Optional[int] = None, nodes_positive: Optional[int] = None,
    m_stage: Optional[str] = None, er_status: Optional[str] = None, pr_status: Optional[str] = None,
    her2_status: Optional[str] = None, t_stage: Optional[str] = None, overall_stage: Optional[str] = None,
    surgery_done: Optional[bool] = None, surgery_type: Optional[str] = None,
    margin_status: Optional[str] = None, axillary_procedure: str = "none",
    quadrant: str = "upper outer", ki67_percent: Optional[float] = None,
    neoadjuvant_chemo: bool = False, chemo_response: str = "not applicable",
    extracapsular_extension: bool = False, imn_involvement: bool = False, scf_involvement: bool = False,
    symptomatic_metastasis: bool = False, surgery_feasible_after_nact: bool = True,
    prior_chest_rt: bool = False, progression_on_endocrine: bool = False,
    bone_only_metastases: bool = False, visceral_metastases: bool = False,
    brca_mutation: bool = False,
) -> str:
    """
    Breast cancer clinical decision support (structured output).
    Protocol: Institutional Breast Cancer v1.0.
    Required: age, sex, ecog, menopausal_status, laterality, histology, tumor_size_cm, grade,
    lvi, n_stage, nodes_examined, nodes_positive, m_stage, er_status, pr_status, her2_status,
    t_stage, overall_stage, surgery_done. If surgery_done=true: surgery_type, margin_status.
    """
    try:
        # Construct BreastInput — Pydantic validates all fields and constraints
        breast_input = BreastInput(
            age=age,
            sex=sex,
            ecog=ecog,
            menopausal_status=menopausal_status,
            laterality=laterality,
            histology=histology,
            tumor_size_cm=tumor_size_cm,
            grade=grade,
            lvi=lvi,
            n_stage=n_stage,
            nodes_examined=nodes_examined,
            nodes_positive=nodes_positive,
            m_stage=m_stage,
            er_status=er_status,
            pr_status=pr_status,
            her2_status=her2_status,
            t_stage=t_stage,
            overall_stage=overall_stage,
            surgery_done=surgery_done,
            surgery_type=surgery_type,
            margin_status=margin_status,
            axillary_procedure=axillary_procedure,
            quadrant=quadrant,
            ki67_percent=ki67_percent,
            neoadjuvant_chemo=neoadjuvant_chemo,
            chemo_response=chemo_response,
            extracapsular_extension=extracapsular_extension,
            imn_involvement=imn_involvement,
            scf_involvement=scf_involvement,
            symptomatic_metastasis=symptomatic_metastasis,
            surgery_feasible_after_nact=surgery_feasible_after_nact,
            prior_chest_rt=prior_chest_rt,
            progression_on_endocrine=progression_on_endocrine,
            bone_only_metastases=bone_only_metastases,
            visceral_metastases=visceral_metastases,
            brca_mutation=brca_mutation,
        )
        
        # Call engine with validated input
        result: BreastResult = evaluate_breast_case(breast_input)
        
        # Return formatted output
        return "```\n" + result.formatted_output + "\n```"
    
    except ValidationError as e:
        # Format Pydantic validation errors into readable message
        error_msg = format_validation_errors(e)
        return "```\n" + error_msg + "\n```"
    
    except Exception as e:
        # Catch any other exceptions (clinical logic errors, etc.)
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 4 — GU: Prostate
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def gu_prostate(
    age: Optional[int] = None, ecog: Optional[int] = None, psa: Optional[float] = None,
    t_stage: Optional[str] = None, n_stage: Optional[str] = None, m_stage: Optional[str] = None,
    grade_group: Optional[int] = None, overall_stage: Optional[str] = None,
    creatinine_clearance: Optional[float] = None, prior_rp: bool = False,
    post_rp_psa: Optional[float] = None, margin_positive: bool = False,
    seminal_vesicle_invasion: bool = False, ece_present: bool = False,
    ln_positive_post_rp: bool = False, on_adt: bool = False, psa_rising_on_adt: bool = False,
    castrate_testosterone: Optional[float] = None, psadt_months: Optional[float] = None,
    bone_only_mets: bool = False, visceral_mets: bool = False,
    symptomatic_bone_mets: bool = False, low_volume_mets: bool = False,
    psma_positive: bool = False, brca_mutation: bool = False, msi_high: bool = False,
    prior_arpi: bool = False, prior_docetaxel: bool = False,
) -> str:
    """
    Prostate cancer decision support. Protocol: Institutional GU Cancers v1.0.
    Required: age, ecog, psa, t_stage, n_stage, m_stage, grade_group, overall_stage, creatinine_clearance.
    """
    try:
        m = _check_missing(
            {"age":age,"ecog":ecog,"psa":psa,"t_stage":t_stage,"n_stage":n_stage,
             "m_stage":m_stage,"grade_group":grade_group,"overall_stage":overall_stage,
             "creatinine_clearance":creatinine_clearance},
            PROSTATE_ESSENTIAL, PROSTATE_HINTS
        )
        if m: return m
        result = evaluate_prostate_case(ProstateInput(
            age=age, ecog=ecog, psa=psa, t_stage=t_stage, n_stage=n_stage, m_stage=m_stage,
            grade_group=grade_group, overall_stage=overall_stage, creatinine_clearance=creatinine_clearance,
            prior_rp=prior_rp, post_rp_psa=post_rp_psa, margin_positive=margin_positive,
            seminal_vesicle_invasion=seminal_vesicle_invasion, ece_present=ece_present,
            ln_positive_post_rp=ln_positive_post_rp, on_adt=on_adt,
            psa_rising_on_adt=psa_rising_on_adt, castrate_testosterone=castrate_testosterone,
            psadt_months=psadt_months, bone_only_mets=bone_only_mets,
            visceral_mets=visceral_mets, symptomatic_bone_mets=symptomatic_bone_mets,
            low_volume_mets=low_volume_mets, psma_positive=psma_positive,
            brca_mutation=brca_mutation, msi_high=msi_high, prior_arpi=prior_arpi,
            prior_docetaxel=prior_docetaxel,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 5 — GU: Bladder
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def gu_bladder(
    age: Optional[int] = None, ecog: Optional[int] = None, t_stage: Optional[str] = None,
    n_stage: Optional[str] = None, m_stage: Optional[str] = None, grade: Optional[str] = None,
    histology: Optional[str] = None, turbt_done: Optional[bool] = None,
    creatinine_clearance: Optional[float] = None, bcg_naive: bool = True,
    prior_systemic_chemo: bool = False, prior_checkpoint_inhibitor: bool = False,
    variant_histology: bool = False, high_risk_nmibc: bool = False,
) -> str:
    """
    Bladder cancer decision support. Protocol: Institutional GU Cancers v1.0.
    Required: age, ecog, t_stage, n_stage, m_stage, grade, histology, turbt_done, creatinine_clearance.
    """
    try:
        m = _check_missing(
            {"age":age,"ecog":ecog,"t_stage":t_stage,"n_stage":n_stage,"m_stage":m_stage,
             "grade":grade,"histology":histology,"turbt_done":turbt_done,"creatinine_clearance":creatinine_clearance},
            BLADDER_ESSENTIAL, BLADDER_HINTS
        )
        if m: return m
        result = evaluate_bladder_case(BladderInput(
            age=age, ecog=ecog, t_stage=t_stage, n_stage=n_stage, m_stage=m_stage,
            grade=grade, histology=histology, turbt_done=turbt_done,
            creatinine_clearance=creatinine_clearance, bcg_naive=bcg_naive,
            prior_systemic_chemo=prior_systemic_chemo,
            prior_checkpoint_inhibitor=prior_checkpoint_inhibitor,
            variant_histology=variant_histology, high_risk_nmibc=high_risk_nmibc,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 6 — GU: Testicular
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def gu_testicular(
    age: Optional[int] = None, ecog: Optional[int] = None, histology: Optional[str] = None,
    t_stage: Optional[str] = None, n_stage: Optional[str] = None, m_stage: Optional[str] = None,
    s_stage: Optional[str] = None, overall_stage: Optional[str] = None,
    post_chemo_resid_mass_cm: Optional[float] = None, late_relapser: bool = False,
    poor_prognosis_markers: bool = False,
) -> str:
    """
    Testicular GCT decision support. Protocol: Institutional GU Cancers v1.0.
    Required: age, ecog, histology, t_stage, n_stage, m_stage, s_stage, overall_stage.
    """
    try:
        m = _check_missing(
            {"age":age,"ecog":ecog,"histology":histology,"t_stage":t_stage,"n_stage":n_stage,
             "m_stage":m_stage,"s_stage":s_stage,"overall_stage":overall_stage},
            TESTICULAR_ESSENTIAL, TESTICULAR_HINTS
        )
        if m: return m
        result = evaluate_testicular_case(TesticularInput(
            age=age, ecog=ecog, histology=histology, t_stage=t_stage, n_stage=n_stage,
            m_stage=m_stage, s_stage=s_stage, overall_stage=overall_stage,
            post_chemo_resid_mass_cm=post_chemo_resid_mass_cm, late_relapser=late_relapser,
            poor_prognosis_markers=poor_prognosis_markers,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 7 — GI Cancers
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def gi_cancer(
    primary_site: Optional[str] = None, age: Optional[int] = None, ecog: Optional[int] = None,
    histology: Optional[str] = None,
    # Esophagus
    esophagus_t_stage: Optional[str] = None, esophagus_n_stage: Optional[str] = None,
    esophagus_m_stage: Optional[str] = None, esophagus_location: Optional[str] = None,
    esophagus_overall_stage: Optional[str] = None,
    # Stomach
    stomach_t_stage: Optional[str] = None, stomach_n_stage: Optional[str] = None,
    stomach_m_stage: Optional[str] = None, stomach_overall_stage: Optional[str] = None,
    her2_positive: bool = False, prior_surgery_stomach: bool = False,
    # Rectum
    rectum_t_stage: Optional[str] = None, rectum_n_stage: Optional[str] = None,
    rectum_m_stage: Optional[str] = None, crm_threatened: bool = False,
    emvi_positive: bool = False, rectum_location: Optional[str] = None,
    prior_surgery_rectum: bool = False,
    # Anal
    anal_t_stage: Optional[str] = None, anal_n_stage: Optional[str] = None,
    anal_m_stage: Optional[str] = None, hiv_positive: bool = False,
    # Pancreas
    pancreas_resectability: Optional[str] = None, pancreas_t_stage: Optional[str] = None,
    pancreas_n_stage: Optional[str] = None, pancreas_m_stage: Optional[str] = None,
    brca_mutation: bool = False, prior_surgery_pancreas: bool = False,
    pancreas_margin_status: Optional[str] = None,
    # Colon
    colon_t_stage: Optional[str] = None, colon_n_stage: Optional[str] = None,
    colon_m_stage: Optional[str] = None, colon_overall_stage: Optional[str] = None,
    high_risk_features: bool = False, microsatellite_instability: Optional[str] = None,
    kras_status: Optional[str] = None,
) -> str:
    """
    GI cancers clinical decision support. Protocol: Institutional GI Cancers v1.0.
    Required: primary_site, age, ecog, histology.
    primary_site: esophagus | stomach | rectum | anal_canal | pancreas | colon
    """
    try:
        m = _check_missing(
            {"primary_site":primary_site,"age":age,"ecog":ecog,"histology":histology},
            GI_ESSENTIAL, GI_HINTS
        )
        if m: return m
        result = evaluate_gi_case(GIInput(
            primary_site=primary_site, age=age, ecog=ecog, histology=histology,
            esophagus_t_stage=esophagus_t_stage, esophagus_n_stage=esophagus_n_stage,
            esophagus_m_stage=esophagus_m_stage, esophagus_location=esophagus_location,
            esophagus_overall_stage=esophagus_overall_stage,
            stomach_t_stage=stomach_t_stage, stomach_n_stage=stomach_n_stage,
            stomach_m_stage=stomach_m_stage, stomach_overall_stage=stomach_overall_stage,
            her2_positive=her2_positive, prior_surgery_stomach=prior_surgery_stomach,
            rectum_t_stage=rectum_t_stage, rectum_n_stage=rectum_n_stage,
            rectum_m_stage=rectum_m_stage, crm_threatened=crm_threatened,
            emvi_positive=emvi_positive, rectum_location=rectum_location,
            prior_surgery_rectum=prior_surgery_rectum,
            anal_t_stage=anal_t_stage, anal_n_stage=anal_n_stage,
            anal_m_stage=anal_m_stage, hiv_positive=hiv_positive,
            pancreas_resectability=pancreas_resectability, pancreas_t_stage=pancreas_t_stage,
            pancreas_n_stage=pancreas_n_stage, pancreas_m_stage=pancreas_m_stage,
            brca_mutation=brca_mutation, prior_surgery_pancreas=prior_surgery_pancreas,
            pancreas_margin_status=pancreas_margin_status,
            colon_t_stage=colon_t_stage, colon_n_stage=colon_n_stage, colon_m_stage=colon_m_stage,
            colon_overall_stage=colon_overall_stage, high_risk_features=high_risk_features,
            microsatellite_instability=microsatellite_instability, kras_status=kras_status,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 8 — Lymphoma
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def lymphoma(
    subtype: Optional[str] = None, stage: Optional[str] = None, age: Optional[int] = None,
    ecog: Optional[int] = None, bulky_disease: bool = False, b_symptoms: bool = False,
    extranodal_sites: int = 0, ldh_elevated: bool = False, esr_elevated: bool = False,
    involved_areas: int = 1, interim_pet_negative: Optional[bool] = None,
    relapsed_refractory: bool = False, gastric_malt: bool = False, ipi_score: Optional[int] = None,
    r_ipi: Optional[str] = None, ki67_percent: Optional[float] = None, cns_involvement: bool = False,
    kidney_adrenal: bool = False, hiv_positive: bool = False, testicular: bool = False,
    prior_rituximab: bool = False,
) -> str:
    """
    Lymphoma clinical decision support. Protocol: Institutional Oncology v1.0.
    Required: subtype, stage, age, ecog.
    subtype: hodgkin | dlbcl | follicular | marginal_zone | nk_t_cell | primary_cns | ptcl | mantle_cell
    stage (Lugano): I | II | II_bulky | III | IV
    """
    try:
        m = _check_missing(
            {"subtype":subtype,"stage":stage,"age":age,"ecog":ecog},
            LYMPHOMA_ESSENTIAL, LYMPHOMA_HINTS
        )
        if m: return m
        result = evaluate_lymphoma_case(LymphomaInput(
            subtype=subtype, stage=stage, age=age, ecog=ecog, bulky_disease=bulky_disease,
            b_symptoms=b_symptoms, extranodal_sites=extranodal_sites, ldh_elevated=ldh_elevated,
            esr_elevated=esr_elevated, involved_areas=involved_areas,
            interim_pet_negative=interim_pet_negative, relapsed_refractory=relapsed_refractory,
            gastric_malt=gastric_malt, ipi_score=ipi_score, r_ipi=r_ipi,
            ki67_percent=ki67_percent, cns_involvement=cns_involvement,
            kidney_adrenal=kidney_adrenal, hiv_positive=hiv_positive,
            testicular=testicular, prior_rituximab=prior_rituximab,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 9 — CNS Tumours
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def cns_tumor(
    tumour_type: Optional[str] = None, who_grade: Optional[str] = None, age: Optional[int] = None,
    ecog: Optional[int] = None, glioma_subtype: Optional[str] = None, idh_mutant: Optional[bool] = None,
    codeletion_1p19q: Optional[bool] = None, mgmt_methylated: Optional[bool] = None,
    tert_mutant: Optional[bool] = None, resection_extent: str = "none",
    gross_total_resection: bool = False, residual_disease: bool = False,
    meningioma_grade: Optional[int] = None, meningioma_complete_resection: bool = False,
    ependymoma_location: Optional[str] = None, spinal_complete_resection: bool = False,
    medulloblastoma_risk: Optional[str] = None, medulloblastoma_metastatic: bool = False,
    pituitary_functional: Optional[bool] = None, tumour_size_cm: Optional[float] = None,
    crosses_midline: bool = False, neurological_deficit: bool = False,
) -> str:
    """
    CNS tumour clinical decision support. Protocol: Institutional CNS Tumors v1.0.
    Required: tumour_type, who_grade, age, ecog.
    tumour_type: glioma | meningioma | ependymoma | medulloblastoma | pituitary_adenoma | craniopharyngioma
    who_grade: 1 | 2 | 3 | 4
    """
    try:
        m = _check_missing(
            {"tumour_type":tumour_type,"who_grade":who_grade,"age":age,"ecog":ecog},
            CNS_ESSENTIAL, CNS_HINTS
        )
        if m: return m
        result = evaluate_cns_case(CNSInput(
            tumour_type=tumour_type, who_grade=who_grade, age=age, ecog=ecog,
            glioma_subtype=glioma_subtype, idh_mutant=idh_mutant,
            codeletion_1p19q=codeletion_1p19q, mgmt_methylated=mgmt_methylated,
            tert_mutant=tert_mutant, resection_extent=resection_extent,
            gross_total_resection=gross_total_resection, residual_disease=residual_disease,
            meningioma_grade=meningioma_grade,
            meningioma_complete_resection=meningioma_complete_resection,
            ependymoma_location=ependymoma_location,
            spinal_complete_resection=spinal_complete_resection,
            medulloblastoma_risk=medulloblastoma_risk,
            medulloblastoma_metastatic=medulloblastoma_metastatic,
            pituitary_functional=pituitary_functional, tumour_size_cm=tumour_size_cm,
            crosses_midline=crosses_midline, neurological_deficit=neurological_deficit,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# Entry point
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    print(
        "Unified Oncology MCP Server — 9 tools\n"
        "cervix_cancer | hnscc_decision | breast_cancer | "
        "gu_prostate | gu_bladder | gu_testicular | "
        "gi_cancer | lymphoma | cns_tumor\n"
        "Press Ctrl+C to stop.",
        file=sys.stderr,
    )
    sys.stderr.flush()
    mcp.run(transport="stdio")