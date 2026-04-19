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

from mcp.server.fastmcp import FastMCP

# ── Existing engines ──────────────────────────────────────────────────────────
from engines.cervix.models        import CervixInput
from engines.cervix.cervix_engine import evaluate_cervix_case
from engines.headneck.hn_models   import HNInput
from engines.headneck.hn_engine   import evaluate_hn_case
from engines.headneck.hn_config   import ESSENTIAL_PARAMS, ORAL_CAVITY_EXTRA_PARAMS
from engines.breast.breast_engine import evaluate_breast_case

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


# ═════════════════════════════════════════════════════════════════════════════
# Generic missing-parameter helper
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
# Parameter hint maps
# ═════════════════════════════════════════════════════════════════════════════

BREAST_ESSENTIAL = [
    "age","sex","ecog","menopausal_status","laterality","histology",
    "tumor_size_cm","grade","lvi","n_stage","nodes_examined","nodes_positive",
    "m_stage","er_status","pr_status","her2_status","t_stage","overall_stage","surgery_done",
]
BREAST_HINTS = {
    "age":"age (numeric, years)","sex":"sex (female | male)",
    "ecog":"ecog (0|1|2|3|4)","menopausal_status":"menopausal_status (premenopausal | perimenopausal | postmenopausal)",
    "laterality":"laterality (left | right)","histology":"histology (invasive ductal carcinoma | invasive lobular carcinoma | DCIS | other)",
    "tumor_size_cm":"tumor_size_cm (numeric, cm)","grade":"grade (1|2|3 — Nottingham grade)",
    "lvi":"lvi — lymphovascular invasion (true | false)","n_stage":"n_stage (N0|N1|N2|N3|pN0|pN1 etc.)",
    "nodes_examined":"nodes_examined (numeric)","nodes_positive":"nodes_positive (numeric)",
    "m_stage":"m_stage (M0 | M1)","er_status":"er_status (positive | negative)",
    "pr_status":"pr_status (positive | negative)","her2_status":"her2_status (positive | negative)",
    "t_stage":"t_stage (T1|T1a|T1b|T1c|T2|T3|T4 etc.)","overall_stage":"overall_stage (IA|IB|IIA|IIB|IIIA|IIIB|IIIC|IV)",
    "surgery_done":"surgery_done (true | false)",
    "surgery_type":"surgery_type (BCS | MRM | mastectomy | none)","margin_status":"margin_status (negative | close | positive | unknown)",
}

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
# Breast output formatter (12-section) — unchanged
# ═════════════════════════════════════════════════════════════════════════════

def _pos_neg(val: str) -> str:
    return "Positive (+)" if val.lower().strip() == "positive" else "Negative (−)"

def _mol_subtype(er, pr, her2, grade, ki67) -> str:
    er_ = er.lower().strip(); pr_ = pr.lower().strip(); her_ = her2.lower().strip()
    tn = (er_=="negative" and pr_=="negative" and her_=="negative")
    hrp = (er_=="positive" or pr_=="positive"); h2p = (her_=="positive")
    if tn: return "Triple-Negative Breast Cancer (TNBC)"
    if h2p and hrp: return "Luminal B (HER2-positive)"
    if h2p: return "HER2-Enriched"
    if hrp:
        ki = ki67 if ki67 is not None else 99
        if er_=="positive" and pr_=="positive" and her_=="negative" and grade<=2 and ki<=20: return "Luminal A"
        return "Luminal B (HER2-negative)"
    return "Unclassified"

def _disease_category(o: str) -> str:
    s = o.upper().strip()
    if s in ("IA","IB","I","IIA","IIB","II"): return "Early Breast Cancer (Stage I–II)"
    if s in ("IIIA","IIIB","IIIC","III"): return "Locally Advanced Breast Cancer (Stage III)"
    if s == "IV": return "Metastatic Breast Cancer (Stage IV)"
    return f"Stage {o}"

def _treatment_intent(o: str, conf: str) -> str:
    if o.upper()=="IV": return "Palliative / Disease control"
    if conf=="red": return "MDT decision required"
    return "Curative"

def _risk_summary(sz, grade, n_stage, n_pos, ki67, o_stage, age, lvi):
    parts = []
    if sz<=2: parts.append(f"Tumor size: {sz} cm (small)")
    elif sz<=5: parts.append(f"Tumor size: {sz} cm (intermediate)")
    else: parts.append(f"Tumor size: {sz} cm (large >5 cm)")
    gl = {1:"Low grade (Grade 1)",2:"Intermediate grade (Grade 2)",3:"High grade (Grade 3)"}
    parts.append(f"Tumor grade: {gl.get(grade, f'Grade {grade}')}")
    n = n_stage.replace("p","").replace("c","").upper()
    if n.startswith("N0"): parts.append("Nodal involvement: Node-negative (N0)")
    elif n_pos>0: parts.append(f"Nodal involvement: {n_pos} positive node(s) — {n_stage}")
    else: parts.append(f"Nodal involvement: {n_stage}")
    if ki67 is not None: parts.append(f"Ki-67: {ki67}% ({'low' if ki67<=20 else 'high'} proliferation)")
    else: parts.append("Ki-67: Not provided")
    if lvi: parts.append("Lymphovascular invasion: Present")
    if age<40: parts.append(f"Age: {age} years — very young (elevated risk)")
    elif age<50: parts.append(f"Age: {age} years — premenopausal")
    elif age>=70: parts.append(f"Age: {age} years — elderly")
    else: parts.append(f"Age: {age} years")
    return parts

def _genomics(er, pr, her2, n_stage, n_pos, o_stage, ki67, age):
    er_=er.lower().strip(); pr_=pr.lower().strip(); h_=her2.lower().strip()
    hrp=(er_=="positive" or pr_=="positive"); h2n=(h_=="negative"); np=n_pos
    if not hrp or not h2n: return "Not routinely indicated for this subtype"
    s=o_stage.upper().strip()
    if s=="IV": return "ESR1/PIK3CA mutation testing recommended for metastatic HR+ disease"
    lines=["Indicated (ER+/HER2-negative disease)"]
    if np==0: lines.append("Node-negative — standard indication for genomic assay")
    elif np<=3: lines.append("1–3 positive nodes — genomic testing recommended (RxPONDER)")
    else: lines.append("≥4 positive nodes — chemotherapy generally indicated regardless of score")
    if age<40: lines.append("Age <40: CANASSIST or Oncotype DX strongly recommended")
    elif age<50: lines.append("Age <50: CANASSIST or Oncotype DX recommended")
    else: lines.append("Recommended assay: CANASSIST / Oncotype DX")
    lines.append("Purpose: Guide adjuvant chemotherapy decision")
    return "\n".join(f"  • {l}" for l in lines)

def _format_breast(result, inputs: dict) -> str:
    r=result; age=inputs["age"]; sex=inputs["sex"]; ecog=inputs["ecog"]
    meno=inputs["menopausal_status"]; lat=inputs["laterality"].capitalize()
    histo=inputs["histology"]; sz=inputs["tumor_size_cm"]; grade=inputs["grade"]
    lvi=inputs["lvi"]; n_stage=inputs["n_stage"]; n_pos=inputs["nodes_positive"]
    m_stage=inputs["m_stage"]; er=inputs["er_status"]; pr=inputs["pr_status"]
    her2=inputs["her2_status"]; t_stage=inputs["t_stage"]; o_stage=inputs["overall_stage"]
    sx_done=inputs["surgery_done"]; sx_type=inputs.get("surgery_type","none")
    margin=inputs.get("margin_status","unknown"); ki67=inputs.get("ki67_percent")
    nact=inputs.get("neoadjuvant_chemo",False); chemo_r=inputs.get("chemo_response","not applicable")
    brca=inputs.get("brca_mutation",False); pdl1=inputs.get("pdl1_positive")

    subtype=_mol_subtype(er,pr,her2,grade,ki67)
    disease_cat=_disease_category(o_stage)
    intent=_treatment_intent(o_stage,r.confidence.value)
    risk_lines=_risk_summary(sz,grade,n_stage,n_pos,ki67,o_stage,age,lvi)
    genomics=_genomics(er,pr,her2,n_stage,n_pos,o_stage,ki67,age)
    sys_raw=r.systemic_therapy or "Not indicated"

    chemo_l=[]; tgt_l=[]; endo_l=[]
    for p in sys_raw.split(";"):
        p=p.strip()
        if not p: continue
        pl=p.lower()
        if any(k in pl for k in ["tamoxifen","aromatase","ai ","ai.","ovarian suppression","endocrine","fulvestrant"]): endo_l.append(p)
        elif any(k in pl for k in ["trastuzumab","pertuzumab","t-dm1","cdk4/6","parp","olaparib","bevacizumab","pembrolizumab","immunotherapy"]): tgt_l.append(p)
        else: chemo_l.append(p)

    cs = "\n".join(f"  • {l}" for l in chemo_l) if chemo_l else "  • Not indicated"
    ts = "\n".join(f"  • {l}" for l in tgt_l)   if tgt_l   else "  • Not applicable"
    es = "\n".join(f"  • {l}" for l in endo_l)   if endo_l  else "  • Not applicable"
    fs = "\n".join(f"  ⚑ {f}" for f in r.flags) if r.flags else "  None"

    if nact: ni,np2 = "Indicated (given)", f"Response: {chemo_r.upper()}"
    elif any(k in sys_raw.lower() for k in ["neoadjuvant","nact","tchp","dose-dense ac"]): ni,np2 = "Indicated (recommended)","Purpose: Downstaging"
    else: ni,np2 = "Not indicated","Surgery-first approach"

    rt_raw=r.radiation_therapy or "To be determined"
    sx_str=(f"  • Procedure: {sx_type.upper()}\n  • Margins: {margin.capitalize()}\n  • {r.surgery_recommendation}" if sx_done else f"  • {r.surgery_recommendation}")

    out ="1 Case Summary\n"
    out+=f"  • Age: {age} years\n  • Sex: {sex.capitalize()}\n  • ECOG: {ecog}\n  • Menopausal Status: {meno.capitalize()}\n"
    out+=f"  • Diagnosis: {lat} breast — {histo}\n  • Tumor Size: {sz} cm\n  • Grade: {grade} (Nottingham)\n"
    out+=f"  • Stage: {t_stage} {n_stage} {m_stage} → Overall Stage {o_stage}\n  • Biomarkers:\n"
    out+=f"      ER: {_pos_neg(er)}\n      PR: {_pos_neg(pr)}\n      HER2: {_pos_neg(her2)}\n"
    out+=f"      Ki-67: {f'{ki67}%' if ki67 is not None else 'Not provided'}\n"
    if brca: out+="      BRCA mutation: Positive\n"
    if pdl1 is not None: out+=f"      PD-L1: {'Positive' if pdl1 else 'Negative'}\n"
    out+="\n2 Molecular Subtype\n  • "+subtype+"\n\n"
    out+="3 Disease Category\n  • "+disease_cat+"\n\n"
    out+="4 Risk Stratification\n"
    for l in risk_lines: out+=f"  • {l}\n"
    out+="\n5 Treatment Intent\n  • "+intent+"\n\n"
    out+="6 Surgery\n"+sx_str+"\n\n"
    out+="7 Systemic Therapy\n  Chemotherapy\n"+cs+"\n  Targeted Therapy\n"+ts+"\n  Endocrine Therapy\n"+es+"\n\n"
    out+=f"8 Neoadjuvant Therapy\n  • {ni}\n  • {np2}\n\n"
    out+="9 Radiotherapy\n"+rt_raw+"\n\n"
    out+="10 Genomic Testing\n"+genomics+"\n\n"
    out+="11 Guideline Rationale\n  • "+r.reasoning+"\n  • Aligned with NCCN / ESMO guidelines\n"
    if r.flags: out+="  Flags:\n"+fs+"\n"
    out+="\n12 Follow-Up\n"
    for fl in (r.follow_up or "As per protocol").split(";"):
        fl=fl.strip()
        if fl: out+=f"  • {fl}\n"
    out+="  • Annual mammography\n  • Monitor toxicity and endocrine compliance\n"
    out+=f"\nConfidence → {r.confidence.value}\nMDT Required → {r.mdt_required}\nProtocol Reference → {r.protocol_reference}"
    return out


# ═════════════════════════════════════════════════════════════════════════════
# MCP Server
# ═════════════════════════════════════════════════════════════════════════════

mcp = FastMCP(
    "Unified Oncology Decision Support",
    instructions=(
        "You are a clinical decision support assistant for oncology.\n"
        "You have NINE tools covering nine cancer categories:\n"
        "  • cervix_cancer    — Cervical cancer (FIGO)\n"
        "  • hnscc_decision   — Head & Neck SCC (oral cavity / oropharynx / hypopharynx / larynx)\n"
        "  • breast_cancer    — Breast cancer (early / LA / metastatic; all subtypes)\n"
        "  • gu_prostate      — Prostate (localized / post-RP / mHSPC / CRPC)\n"
        "  • gu_bladder       — Bladder (NMIBC / MIBC / preservation / metastatic)\n"
        "  • gu_testicular    — Testicular GCT (seminoma + NSGCT, all stages)\n"
        "  • gi_cancer        — GI cancers (esophagus | stomach | rectum | anal | pancreas | colon)\n"
        "  • lymphoma         — Lymphoma (Hodgkin + NHL: DLBCL / FL / MZL / NK-T / PCNSL / MCL / PTCL)\n"
        "  • cns_tumor        — CNS (glioma / meningioma / ependymoma / medulloblastoma / pituitary / craniopharyngioma)\n\n"
        "RULES:\n"
        "1. Use the tool matching the user's cancer type.\n"
        "2. Collect ALL required parameters BEFORE calling a tool.\n"
        "3. If any are missing, ask for them in ONE message — do NOT call the tool.\n"
        "4. NEVER infer, assume, or guess parameter values.\n"
        "5. On success: copy the tool output EXACTLY as-is — do NOT summarise or rewrite.\n"
        "6. On tool error: respond ONLY with 'TOOL ERROR: Clinical decision engine unavailable.'\n"
        "7. NEVER generate clinical recommendations from your own knowledge."
    ),
)


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 1 — Cervix
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def cervix_cancer(
    age: int, ecog: int, figo_stage: str, histology: str, tumor_size_cm: float,
    pelvic_nodes_positive: bool, para_aortic_nodes_positive: bool, hydronephrosis: bool,
    creatinine_clearance: float, prior_surgery: bool = False, margins_positive: bool = False,
    lvsi_present: bool = False, parametrial_invasion: bool = False,
    distant_metastasis: bool = False, symptomatic_bleeding: bool = False,
    post_crt_residual: bool = False,
) -> str:
    """
    Cervix cancer clinical decision support. Protocol: Institutional Cervix Cancer v1.0.
    Required: age, ecog, figo_stage, histology, tumor_size_cm, pelvic_nodes_positive,
    para_aortic_nodes_positive, hydronephrosis, creatinine_clearance.
    """
    try:
        result = evaluate_cervix_case(CervixInput(
            age=age, ecog=ecog, figo_stage=figo_stage, histology=histology,
            tumor_size_cm=tumor_size_cm, pelvic_nodes_positive=pelvic_nodes_positive,
            para_aortic_nodes_positive=para_aortic_nodes_positive, hydronephrosis=hydronephrosis,
            creatinine_clearance=creatinine_clearance, prior_surgery=prior_surgery,
            margins_positive=margins_positive, lvsi_present=lvsi_present,
            parametrial_invasion=parametrial_invasion, distant_metastasis=distant_metastasis,
            symptomatic_bleeding=symptomatic_bleeding, post_crt_residual=post_crt_residual,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 2 — Head & Neck SCC
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def hnscc_decision(
    age: Optional[int]=None, ecog: Optional[int]=None, primary_site: Optional[str]=None,
    ajcc_stage: Optional[str]=None, t_stage: Optional[str]=None, n_stage: Optional[str]=None,
    distant_metastasis: Optional[bool]=None, resectable: Optional[bool]=None,
    creatinine_clearance: Optional[float]=None, oral_subsite: Optional[str]=None,
    doi_mm: Optional[float]=None, bone_invasion: bool=False, bilateral_nodes: bool=False,
    prior_surgery: bool=False, prior_rt: bool=False, margins_positive: bool=False,
    ece_present: bool=False, pni_present: bool=False, lvi_present: bool=False,
    multiple_positive_nodes: bool=False, p16_positive: bool=True, hearing_adequate: bool=True,
    recurrent_disease: bool=False, post_rt_residual_nodes: bool=False,
    organ_preservation_preferred: bool=False, symptomatic_bleeding_or_pain: bool=False,
) -> str:
    """
    Head & Neck SCC decision support. Protocol: Institutional HNSCC v1.0.
    Required: age, ecog, primary_site, ajcc_stage, t_stage, n_stage, distant_metastasis,
    resectable, creatinine_clearance. For oral_cavity: also oral_subsite, doi_mm.
    """
    try:
        params = {"age":age,"ecog":ecog,"primary_site":primary_site,"ajcc_stage":ajcc_stage,
                  "t_stage":t_stage,"n_stage":n_stage,"distant_metastasis":distant_metastasis,
                  "resectable":resectable,"creatinine_clearance":creatinine_clearance,
                  "oral_subsite":oral_subsite,"doi_mm":doi_mm}
        m = _check_missing({k:v for k,v in params.items() if k in HN_ESSENTIAL+["oral_subsite","doi_mm"]
                            and not (k in ["oral_subsite","doi_mm"] and primary_site!="oral_cavity")},
                           HN_ESSENTIAL + (["oral_subsite","doi_mm"] if primary_site=="oral_cavity" else []),
                           HN_HINTS)
        if m: return m
        result = evaluate_hn_case(HNInput(
            age=age, ecog=ecog, primary_site=primary_site, ajcc_stage=ajcc_stage,
            t_stage=t_stage, n_stage=n_stage, distant_metastasis=distant_metastasis,
            oral_subsite=oral_subsite, doi_mm=doi_mm, bone_invasion=bone_invasion,
            bilateral_nodes=bilateral_nodes, resectable=resectable, prior_surgery=prior_surgery,
            prior_rt=prior_rt, margins_positive=margins_positive, ece_present=ece_present,
            pni_present=pni_present, lvi_present=lvi_present,
            multiple_positive_nodes=multiple_positive_nodes, p16_positive=p16_positive,
            creatinine_clearance=creatinine_clearance, hearing_adequate=hearing_adequate,
            recurrent_disease=recurrent_disease, post_rt_residual_nodes=post_rt_residual_nodes,
            organ_preservation_preferred=organ_preservation_preferred,
            symptomatic_bleeding_or_pain=symptomatic_bleeding_or_pain,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 3 — Breast
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def breast_cancer(
    age: Optional[int]=None, sex: Optional[str]=None, ecog: Optional[int]=None,
    menopausal_status: Optional[str]=None, laterality: Optional[str]=None,
    histology: Optional[str]=None, tumor_size_cm: Optional[float]=None,
    grade: Optional[int]=None, lvi: Optional[bool]=None, n_stage: Optional[str]=None,
    nodes_examined: Optional[int]=None, nodes_positive: Optional[int]=None,
    m_stage: Optional[str]=None, er_status: Optional[str]=None, pr_status: Optional[str]=None,
    her2_status: Optional[str]=None, t_stage: Optional[str]=None, overall_stage: Optional[str]=None,
    surgery_done: Optional[bool]=None, surgery_type: Optional[str]=None,
    margin_status: Optional[str]=None, axillary_procedure: str="none",
    quadrant: str="upper outer", ki67_percent: Optional[float]=None,
    neoadjuvant_chemo: bool=False, chemo_response: str="not applicable",
    extracapsular_extension: bool=False, imn_involvement: bool=False, scf_involvement: bool=False,
    symptomatic_metastasis: bool=False, surgery_feasible_after_nact: bool=True,
    prior_chest_rt: bool=False, progression_on_endocrine: bool=False,
    bone_only_metastases: bool=False, visceral_metastases: bool=False,
    brca_mutation: bool=False, pdl1_positive: Optional[bool]=None,
) -> str:
    """
    Breast cancer clinical decision support (12-section structured output).
    Protocol: Institutional Breast Cancer v1.0.
    Required: age, sex, ecog, menopausal_status, laterality, histology, tumor_size_cm, grade,
    lvi, n_stage, nodes_examined, nodes_positive, m_stage, er_status, pr_status, her2_status,
    t_stage, overall_stage, surgery_done. If surgery_done=true: surgery_type, margin_status.
    """
    try:
        check = {"age":age,"sex":sex,"ecog":ecog,"menopausal_status":menopausal_status,
                 "laterality":laterality,"histology":histology,"tumor_size_cm":tumor_size_cm,
                 "grade":grade,"lvi":lvi,"n_stage":n_stage,"nodes_examined":nodes_examined,
                 "nodes_positive":nodes_positive,"m_stage":m_stage,"er_status":er_status,
                 "pr_status":pr_status,"her2_status":her2_status,"t_stage":t_stage,
                 "overall_stage":overall_stage,"surgery_done":surgery_done,
                 "surgery_type":surgery_type if surgery_done else "skip",
                 "margin_status":margin_status if surgery_done else "skip"}
        cp = {k:(None if v=="skip" else v) for k,v in check.items()}
        essential = BREAST_ESSENTIAL + (["surgery_type","margin_status"] if surgery_done else [])
        m = _check_missing(cp, essential, BREAST_HINTS)
        if m: return m
        st = surgery_type or "none"; ms = margin_status or "unknown"
        result = evaluate_breast_case(
            age=age, sex=sex, ecog=ecog, menopausal_status=menopausal_status,
            laterality=laterality, histology=histology, tumor_size_cm=tumor_size_cm,
            grade=grade, lvi=lvi, n_stage=n_stage, nodes_examined=nodes_examined,
            nodes_positive=nodes_positive, m_stage=m_stage, er_status=er_status,
            pr_status=pr_status, her2_status=her2_status, t_stage=t_stage,
            overall_stage=overall_stage, surgery_done=surgery_done,
            surgery_type=st, margin_status=ms, axillary_procedure=axillary_procedure,
            quadrant=quadrant, ki67_percent=ki67_percent, neoadjuvant_chemo=neoadjuvant_chemo,
            chemo_response=chemo_response, extracapsular_extension=extracapsular_extension,
            imn_involvement=imn_involvement, scf_involvement=scf_involvement,
            symptomatic_metastasis=symptomatic_metastasis,
            surgery_feasible_after_nact=surgery_feasible_after_nact,
            prior_chest_rt=prior_chest_rt, progression_on_endocrine=progression_on_endocrine,
            bone_only_metastases=bone_only_metastases, visceral_metastases=visceral_metastases,
            brca_mutation=brca_mutation,
        )
        inputs = {"age":age,"sex":sex,"ecog":ecog,"menopausal_status":menopausal_status,
                  "laterality":laterality,"histology":histology,"tumor_size_cm":tumor_size_cm,
                  "grade":grade,"lvi":lvi,"n_stage":n_stage,"nodes_examined":nodes_examined,
                  "nodes_positive":nodes_positive,"m_stage":m_stage,"er_status":er_status,
                  "pr_status":pr_status,"her2_status":her2_status,"t_stage":t_stage,
                  "overall_stage":overall_stage,"surgery_done":surgery_done,
                  "surgery_type":st,"margin_status":ms,"ki67_percent":ki67_percent,
                  "neoadjuvant_chemo":neoadjuvant_chemo,"chemo_response":chemo_response,
                  "brca_mutation":brca_mutation,"pdl1_positive":pdl1_positive}
        return "```\n" + _format_breast(result, inputs) + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 4 — GU: Prostate
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def gu_prostate(
    age: Optional[int]=None, ecog: Optional[int]=None, psa: Optional[float]=None,
    t_stage: Optional[str]=None, n_stage: Optional[str]=None, m_stage: Optional[str]=None,
    grade_group: Optional[int]=None, overall_stage: Optional[str]=None,
    creatinine_clearance: Optional[float]=None, prior_rp: bool=False,
    post_rp_psa: Optional[float]=None, margin_positive: bool=False,
    seminal_vesicle_invasion: bool=False, ece_present: bool=False,
    ln_positive_post_rp: bool=False, on_adt: bool=False, psa_rising_on_adt: bool=False,
    castrate_testosterone: Optional[float]=None, psadt_months: Optional[float]=None,
    bone_only_mets: bool=False, visceral_mets: bool=False,
    symptomatic_bone_mets: bool=False, low_volume_mets: bool=False,
    psma_positive: bool=False, brca_mutation: bool=False, msi_high: bool=False,
    prior_arpi: bool=False, prior_docetaxel: bool=False,
) -> str:
    """
    Prostate cancer decision support. Protocol: Institutional GU Cancers v1.0.
    Required: age, ecog, psa, t_stage, n_stage, m_stage, grade_group, overall_stage, creatinine_clearance.
    """
    try:
        m = _check_missing({"age":age,"ecog":ecog,"psa":psa,"t_stage":t_stage,"n_stage":n_stage,
                            "m_stage":m_stage,"grade_group":grade_group,"overall_stage":overall_stage,
                            "creatinine_clearance":creatinine_clearance},
                           PROSTATE_ESSENTIAL, PROSTATE_HINTS)
        if m: return m
        result = evaluate_prostate_case(ProstateInput(
            age=age, ecog=ecog, psa=psa, t_stage=t_stage, n_stage=n_stage, m_stage=m_stage,
            grade_group=grade_group, overall_stage=overall_stage, creatinine_clearance=creatinine_clearance,
            prior_rp=prior_rp, post_rp_psa=post_rp_psa, margin_positive=margin_positive,
            seminal_vesicle_invasion=seminal_vesicle_invasion, ece_present=ece_present,
            ln_positive_post_rp=ln_positive_post_rp, on_adt=on_adt, psa_rising_on_adt=psa_rising_on_adt,
            castrate_testosterone=castrate_testosterone, psadt_months=psadt_months,
            bone_only_mets=bone_only_mets, visceral_mets=visceral_mets,
            symptomatic_bone_mets=symptomatic_bone_mets, low_volume_mets=low_volume_mets,
            psma_positive=psma_positive, brca_mutation=brca_mutation, msi_high=msi_high,
            prior_arpi=prior_arpi, prior_docetaxel=prior_docetaxel,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 5 — GU: Bladder
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def gu_bladder(
    age: Optional[int]=None, ecog: Optional[int]=None, t_stage: Optional[str]=None,
    n_stage: Optional[str]=None, m_stage: Optional[str]=None, grade: Optional[str]=None,
    histology: Optional[str]=None, turbt_done: Optional[bool]=None,
    creatinine_clearance: Optional[float]=None, willing_for_surgery: bool=True,
    bladder_preservation_preferred: bool=False, cis_present: bool=False,
    bcg_status: str="naive", prior_bcg_courses: int=0, haematuria_active: bool=False,
) -> str:
    """
    Bladder cancer decision support. Protocol: Institutional GU Cancers v1.0.
    Required: age, ecog, t_stage, n_stage, m_stage, grade, histology, turbt_done, creatinine_clearance.
    NOTE: Patient willingness for cystectomy must be obtained per institutional protocol.
    """
    try:
        m = _check_missing({"age":age,"ecog":ecog,"t_stage":t_stage,"n_stage":n_stage,
                            "m_stage":m_stage,"grade":grade,"histology":histology,
                            "turbt_done":turbt_done,"creatinine_clearance":creatinine_clearance},
                           BLADDER_ESSENTIAL, BLADDER_HINTS)
        if m: return m
        result = evaluate_bladder_case(BladderInput(
            age=age, ecog=ecog, t_stage=t_stage, n_stage=n_stage, m_stage=m_stage,
            grade=grade, histology=histology, turbt_done=turbt_done,
            creatinine_clearance=creatinine_clearance, willing_for_surgery=willing_for_surgery,
            bladder_preservation_preferred=bladder_preservation_preferred,
            cis_present=cis_present, bcg_status=bcg_status, prior_bcg_courses=prior_bcg_courses,
            haematuria_active=haematuria_active,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 6 — GU: Testicular
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def gu_testicular(
    age: Optional[int]=None, ecog: Optional[int]=None, histology: Optional[str]=None,
    t_stage: Optional[str]=None, n_stage: Optional[str]=None, m_stage: Optional[str]=None,
    s_stage: Optional[str]=None, overall_stage: Optional[str]=None,
    orchiectomy_done: bool=False, lvi: bool=False, rete_testis_invasion: bool=False,
    marker_normalised: bool=True, marker_elevation_persistent: bool=False,
    post_chemo_residual: bool=False, residual_mass_cm: Optional[float]=None,
    igcccg_risk: Optional[str]=None, non_pulmonary_visceral_mets: bool=False,
    mediastinal_primary: bool=False,
) -> str:
    """
    Testicular GCT decision support. Protocol: Institutional GU Cancers v1.0.
    Required: age, ecog, histology, t_stage, n_stage, m_stage, s_stage, overall_stage.
    """
    try:
        m = _check_missing({"age":age,"ecog":ecog,"histology":histology,"t_stage":t_stage,
                            "n_stage":n_stage,"m_stage":m_stage,"s_stage":s_stage,
                            "overall_stage":overall_stage},
                           TESTICULAR_ESSENTIAL, TESTICULAR_HINTS)
        if m: return m
        result = evaluate_testicular_case(TesticularInput(
            age=age, ecog=ecog, histology=histology, t_stage=t_stage, n_stage=n_stage,
            m_stage=m_stage, s_stage=s_stage, overall_stage=overall_stage,
            orchiectomy_done=orchiectomy_done, lvi=lvi, rete_testis_invasion=rete_testis_invasion,
            marker_normalised=marker_normalised, marker_elevation_persistent=marker_elevation_persistent,
            post_chemo_residual=post_chemo_residual, residual_mass_cm=residual_mass_cm,
            igcccg_risk=igcccg_risk, non_pulmonary_visceral_mets=non_pulmonary_visceral_mets,
            mediastinal_primary=mediastinal_primary,
        ))
        return "```\n" + result.formatted_output + "\n```"
    except Exception as e:
        return "```\nTOOL ERROR\nReason: " + str(e) + "\n```"


# ═════════════════════════════════════════════════════════════════════════════
# TOOL 7 — GI Cancers
# ═════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def gi_cancer(
    primary_site: Optional[str] = None,
    age:          Optional[int] = None,
    ecog:         Optional[int] = None,
    histology:    Optional[str] = None,
    # ── Esophagus ──────────────────────────────────────────────────────
    esophagus_t_stage:       Optional[str] = None,
    esophagus_n_stage:       Optional[str] = None,
    esophagus_m_stage:       Optional[str] = None,
    esophagus_location:      Optional[str] = None,
    esophagus_overall_stage: Optional[str] = None,
    # ── Stomach ────────────────────────────────────────────────────────
    stomach_t_stage:         Optional[str] = None,
    stomach_n_stage:         Optional[str] = None,
    stomach_m_stage:         Optional[str] = None,
    stomach_overall_stage:   Optional[str] = None,
    her2_positive:           bool          = False,
    prior_surgery_stomach:   bool          = False,
    # ── Rectum ─────────────────────────────────────────────────────────
    rectum_t_stage:          Optional[str] = None,
    rectum_n_stage:          Optional[str] = None,
    rectum_m_stage:          Optional[str] = None,
    crm_threatened:          bool          = False,
    emvi_positive:           bool          = False,
    rectum_location:         Optional[str] = None,
    prior_surgery_rectum:    bool          = False,
    # ── Anal Canal ─────────────────────────────────────────────────────
    anal_t_stage:            Optional[str] = None,
    anal_n_stage:            Optional[str] = None,
    anal_m_stage:            Optional[str] = None,
    hiv_positive:            bool          = False,
    # ── Pancreas ───────────────────────────────────────────────────────
    pancreas_resectability:  Optional[str] = None,
    pancreas_t_stage:        Optional[str] = None,
    pancreas_n_stage:        Optional[str] = None,
    pancreas_m_stage:        Optional[str] = None,
    brca_mutation:           bool          = False,
    prior_surgery_pancreas:  bool          = False,
    pancreas_margin_status:  Optional[str] = None,
    # ── Colon ──────────────────────────────────────────────────────────
    colon_t_stage:           Optional[str] = None,
    colon_n_stage:           Optional[str] = None,
    colon_m_stage:           Optional[str] = None,
    colon_overall_stage:     Optional[str] = None,
    high_risk_features:      bool          = False,
    microsatellite_instability: Optional[str] = None,
    kras_status:             Optional[str] = None,
) -> str:
    """
    GI cancers decision support. Protocol: Institutional GI Cancers v1.0.
    Required: primary_site, age, ecog, histology.
    primary_site: esophagus | stomach | rectum | anal_canal | pancreas | colon
    Esophagus also requires: esophagus_t_stage, esophagus_n_stage, esophagus_m_stage, esophagus_location.
    Rectum also requires: rectum_t_stage, rectum_n_stage, rectum_m_stage.
    Anal canal also requires: anal_t_stage, anal_n_stage, anal_m_stage.
    Pancreas also requires: pancreas_resectability.
    Colon also requires: colon_t_stage, colon_n_stage, colon_m_stage.
    """
    try:
        m = _check_missing({"primary_site":primary_site,"age":age,"ecog":ecog,"histology":histology},
                           GI_ESSENTIAL, GI_HINTS)
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
            anal_t_stage=anal_t_stage, anal_n_stage=anal_n_stage, anal_m_stage=anal_m_stage,
            hiv_positive=hiv_positive,
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
    subtype:       Optional[str] = None,
    stage:         Optional[str] = None,
    age:           Optional[int] = None,
    ecog:          Optional[int] = None,
    bulky_disease:     bool          = False,
    b_symptoms:        bool          = False,
    extranodal_sites:  int           = 0,
    ldh_elevated:      bool          = False,
    esr_elevated:      bool          = False,
    involved_areas:    int           = 1,
    interim_pet_negative: Optional[bool] = None,
    relapsed_refractory:  bool          = False,
    gastric_malt:         bool          = False,
    ipi_score:            Optional[int] = None,
    r_ipi:                Optional[str] = None,
    ki67_percent:         Optional[float] = None,
    cns_involvement:      bool          = False,
    kidney_adrenal:       bool          = False,
    hiv_positive:         bool          = False,
    testicular:           bool          = False,
    prior_rituximab:      bool          = False,
) -> str:
    """
    Lymphoma clinical decision support. Protocol: Institutional Oncology v1.0.
    Required: subtype, stage, age, ecog.
    subtype: hodgkin | dlbcl | follicular | marginal_zone | nk_t_cell | primary_cns | ptcl | mantle_cell
    stage (Lugano): I | II | II_bulky | III | IV
    """
    try:
        m = _check_missing({"subtype":subtype,"stage":stage,"age":age,"ecog":ecog},
                           LYMPHOMA_ESSENTIAL, LYMPHOMA_HINTS)
        if m: return m
        result = evaluate_lymphoma_case(LymphomaInput(
            subtype=subtype, stage=stage, age=age, ecog=ecog,
            bulky_disease=bulky_disease, b_symptoms=b_symptoms,
            extranodal_sites=extranodal_sites, ldh_elevated=ldh_elevated,
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
    tumour_type:  Optional[str] = None,
    who_grade:    Optional[str] = None,
    age:          Optional[int] = None,
    ecog:         Optional[int] = None,
    # Glioma
    glioma_subtype:   Optional[str]   = None,
    idh_mutant:       Optional[bool]  = None,
    codeletion_1p19q: Optional[bool]  = None,
    mgmt_methylated:  Optional[bool]  = None,
    tert_mutant:      Optional[bool]  = None,
    # Surgery
    resection_extent:      str            = "none",
    gross_total_resection: bool           = False,
    residual_disease:      bool           = False,
    # Meningioma
    meningioma_grade:              Optional[int]  = None,
    meningioma_complete_resection: bool           = False,
    # Ependymoma
    ependymoma_location:  Optional[str] = None,
    spinal_complete_resection: bool     = False,
    # Medulloblastoma
    medulloblastoma_risk:      Optional[str] = None,
    medulloblastoma_metastatic: bool         = False,
    # Pituitary
    pituitary_functional: Optional[bool] = None,
    # High-risk LGG criteria
    tumour_size_cm:    Optional[float] = None,
    crosses_midline:   bool            = False,
    neurological_deficit: bool         = False,
) -> str:
    """
    CNS tumour clinical decision support. Protocol: Institutional CNS Tumors v1.0.
    Required: tumour_type, who_grade, age, ecog.
    tumour_type: glioma | meningioma | ependymoma | medulloblastoma | pituitary_adenoma | craniopharyngioma
    who_grade: 1 | 2 | 3 | 4
    For glioma: also provide glioma_subtype, idh_mutant, mgmt_methylated (GBM), codeletion_1p19q.
    For meningioma: meningioma_grade, meningioma_complete_resection, residual_disease.
    For ependymoma: ependymoma_location (posterior_fossa | spinal | supratentorial), residual_disease.
    For medulloblastoma: medulloblastoma_risk (standard | high), medulloblastoma_metastatic.
    """
    try:
        m = _check_missing({"tumour_type":tumour_type,"who_grade":who_grade,"age":age,"ecog":ecog},
                           CNS_ESSENTIAL, CNS_HINTS)
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