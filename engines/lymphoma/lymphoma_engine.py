"""
Production-Ready Lymphoma Clinical Decision Support Engine
Institutional Oncology Protocol v1.0

Subtypes covered:
  Hodgkin Lymphoma:
    • Early favourable (Stage I–II, no bulk, no risk factors)
    • Early unfavourable (Stage I–II with risk factors)
    • Advanced (Stage III–IV)
  Non-Hodgkin Lymphoma:
    • DLBCL (all stages; CNS prophylaxis criteria)
    • Follicular Lymphoma (Stage I–II ISRT; Stage III–IV watch-and-wait / systemic)
    • Marginal Zone Lymphoma (gastric MALT; non-gastric)
    • NK/T-cell lymphoma (nasal/extranasal)
    • Primary CNS Lymphoma
    • Peripheral T-cell Lymphoma
    • Mantle Cell Lymphoma

OUTPUT FORMAT mirrors institutional sample case templates.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from dataclasses import dataclass


PROTOCOL_VERSION = "Institutional Oncology Protocol v1.0 – Lymphoma"


class LymphomaSubtype(str, Enum):
    HODGKIN              = "hodgkin"
    DLBCL                = "dlbcl"
    FOLLICULAR           = "follicular"
    MARGINAL_ZONE        = "marginal_zone"
    NK_T_CELL            = "nk_t_cell"
    PRIMARY_CNS          = "primary_cns"
    PERIPHERAL_T_CELL    = "ptcl"
    MANTLE_CELL          = "mantle_cell"


class LuganoStage(str, Enum):
    I       = "I"
    II      = "II"
    II_BULKY = "II_bulky"
    III     = "III"
    IV      = "IV"


class Confidence(str, Enum):
    GREEN = "green"; AMBER = "amber"; RED = "red"


class LymphomaInput(BaseModel):
    subtype:       LymphomaSubtype
    stage:         LuganoStage
    age:           int  = Field(..., ge=1, le=100)
    ecog:          int  = Field(..., ge=0, le=4)

    # Risk factors
    bulky_disease:     bool = False   # ≥6–10 cm depending on subtype
    b_symptoms:        bool = False
    extranodal_sites:  int  = 0       # number of extranodal sites
    ldh_elevated:      bool = False
    esr_elevated:      bool = False   # ESR ≥50 (HL risk factor)
    involved_areas:    int  = 1       # number of involved nodal areas (HL)

    # Response / prior therapy
    interim_pet_negative: Optional[bool] = None  # for HL de-escalation
    relapsed_refractory:  bool = False

    # GI/site specifics
    gastric_malt:     bool = False    # for MZL: H. pylori positive gastric MALT

    # Molecular / prognostic
    ipi_score:        Optional[int]  = None   # IPI for DLBCL (0–5)
    r_ipi:            Optional[str]  = None   # very_good / good / poor
    ki67_percent:     Optional[float] = None

    # CNS prophylaxis
    cns_involvement:  bool = False
    kidney_adrenal:   bool = False
    hiv_positive:     bool = False
    testicular:       bool = False

    # Treatment history
    prior_rituximab:  bool = False


class LymphomaResult(BaseModel):
    formatted_output:   str
    confidence:         Confidence
    flags:              List[str]
    mdt_required:       bool
    protocol_reference: str


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _footer(confidence: Confidence, flags: list, mdt_required: bool) -> str:
    flag_str = ", ".join(flags) if flags else "None"
    return (
        f"\nConfidence → {confidence.value}\n"
        f"Flags → {flag_str}\n"
        f"MDT Required → {mdt_required}\n"
        f"Protocol Reference → {PROTOCOL_VERSION}"
    )


def _cns_prophylaxis_indicated(inp: LymphomaInput) -> bool:
    """Return True if CNS prophylaxis criteria met (institutional protocol)."""
    criteria_count = sum([
        inp.age > 60,
        inp.ldh_elevated,
        inp.stage in (LuganoStage.III, LuganoStage.IV),
        inp.kidney_adrenal,
        inp.hiv_positive,
        inp.testicular,
    ])
    return criteria_count >= 2 or inp.cns_involvement or inp.testicular or inp.hiv_positive


# ─────────────────────────────────────────────────────────────────────────────
# Hodgkin Lymphoma
# ─────────────────────────────────────────────────────────────────────────────

def _hodgkin(inp: LymphomaInput) -> LymphomaResult:
    flags = []
    stage = inp.stage.value
    bulky = inp.bulky_disease
    b_sx  = inp.b_symptoms
    esr   = inp.esr_elevated
    areas = inp.involved_areas

    # GHSG risk factor count (early HL): ESR≥50/B-sx, bulky mediastinum, extranodal,
    # >2–3 involved areas
    risk_factors = sum([bulky, b_sx, esr, inp.extranodal_sites > 0, areas > 2])

    # ── Advanced Stage III–IV ────────────────────────────────────────────
    if stage in ("III","IV"):
        flags.append("Advanced Hodgkin lymphoma – ABVD/BrECADD; interim PET guides treatment")
        ipt = inp.interim_pet_negative
        if ipt is True:
            escalation = "Interim PET-negative → continue ABVD × 6 total cycles (de-escalation: RATHL trial)\n"
        elif ipt is False:
            escalation = "Interim PET-positive → escalate to BEACOPPesc or BrECADD × 4 + 2 cycles\n"
            flags.append("Interim PET-positive – treatment escalation required; MDT review")
        else:
            escalation = "Interim PET-CT recommended after 2 cycles (RATHL) for treatment decision\n"

        out = (
            f"1 Lymphoma Type\nHodgkin lymphoma – Advanced ({stage})\n\n"
            "2 Stage\n"
            f"Stage {stage}{' + Bulky' if bulky else ''}{' + B-symptoms' if b_sx else ''}\n\n"
            "3 Primary Treatment\n"
            "ABVD × 6 cycles (Doxorubicin + Bleomycin + Vinblastine + Dacarbazine)\n"
            "OR BrECADD × 6 cycles (Brentuximab vedotin + Etoposide + Cyclophosphamide + Doxorubicin + Dacarbazine) – HD21: superior outcomes\n\n"
            "4 Interim PET-CT Assessment (after 2 cycles)\n"
            f"{escalation}\n"
            "5 Consolidation Radiotherapy\n"
            "IF residual mass on end-of-treatment PET-CT (Deauville 4–5):\n"
            "30–36 Gy ISRT to PET-positive residual site(s)\n"
            "Technique: ISRT (involved site RT); IMRT\n\n"
            "6 Rationale\n"
            "RATHL: PET-adapted treatment; PET-2 negative → bleomycin omission safe\n"
            "HD21: BrECADD improved PFS and reduced toxicity vs BEACOPPesc\n\n"
            "7 Follow-up\n"
            "PET-CT at end of treatment; CT every 6 months × 2 years, then annually\n"
            "Late effects monitoring: cardiac, pulmonary, secondary malignancy"
        )
        out += _footer(Confidence.GREEN, flags, bool([f for f in flags if "MDT" in f]))
        return LymphomaResult(formatted_output=out, confidence=Confidence.GREEN,
                              flags=flags, mdt_required=bool([f for f in flags if "MDT" in f]),
                              protocol_reference=PROTOCOL_VERSION)

    # ── Early Stage I–II ─────────────────────────────────────────────────
    if risk_factors == 0 and not bulky:
        # Early Favourable
        out = (
            "1 Lymphoma Type\nHodgkin lymphoma – Early Favourable\n\n"
            f"2 Stage\nStage {stage} (no risk factors, no bulk)\n\n"
            "3 Primary Treatment\nABVD × 2 cycles + ISRT 20 Gy (GHSG HD10: standard)\n"
            "PET-CT after 2 cycles: if negative, 20 Gy ISRT; if positive, 30 Gy or escalation\n\n"
            "4 Radiotherapy\nISRT (Involved Site Radiotherapy): 20–30 Gy / 10–15#\n"
            "Target: Originally involved LN region with 2 cm margin\n"
            "Technique: ISRT per ILROG guidelines; IMRT preferred\n\n"
            "5 Rationale\nGHSG HD10: 2×ABVD + 20 Gy ISRT: 5-yr PFS 93%; minimal toxicity\n"
            "PET-adapted strategy (RAPID trial): omit RT if PET-negative → slightly higher relapse\n\n"
            "6 Follow-up\nPET-CT end of treatment; CT every 6 months × 2 years, then annually"
        )
        out += _footer(Confidence.GREEN, flags, False)
        return LymphomaResult(formatted_output=out, confidence=Confidence.GREEN,
                              flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)
    else:
        # Early Unfavourable
        flags.append("Early unfavourable HL – 4× ABVD + ISRT 30 Gy (GHSG HD11)")
        out = (
            "1 Lymphoma Type\nHodgkin lymphoma – Early Unfavourable\n\n"
            f"2 Stage\nStage {stage} with risk factors: "
            f"{'Bulky; ' if bulky else ''}{'B-symptoms; ' if b_sx else ''}{'ESR elevated; ' if esr else ''}"
            f"{'Extranodal; ' if inp.extranodal_sites > 0 else ''}{'≥3 areas' if areas > 2 else ''}\n\n"
            "3 Primary Treatment\nABVD × 4 cycles + ISRT 30 Gy (GHSG HD11 standard)\n"
            "BrECADD × 4 cycles + ISRT 30 Gy: consider if HD17/HD21 criteria (PET-adapted)\n\n"
            "4 Radiotherapy\nISRT: 30 Gy / 15# (standard) or 20 Gy if PET-negative after chemo\n"
            "Target: Involved sites per ILROG ISRT guidelines\n"
            "Technique: IMRT; IGRT recommended\n\n"
            "5 Rationale\nGHSG HD11: 4×ABVD + 30 Gy ISRT: 5-yr FFTF 81%\n"
            "Bulky mediastinal disease: mediastinal RT mandatory\n\n"
            "6 Follow-up\nPET-CT end of treatment; CT every 6 months × 2 years; Late effects monitoring"
        )
        out += _footer(Confidence.GREEN, flags, False)
        return LymphomaResult(formatted_output=out, confidence=Confidence.GREEN,
                              flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# DLBCL
# ─────────────────────────────────────────────────────────────────────────────

def _dlbcl(inp: LymphomaInput) -> LymphomaResult:
    flags   = []
    stage   = inp.stage.value
    ipi     = inp.ipi_score if inp.ipi_score is not None else 0
    r_ipi   = (inp.r_ipi or "good").lower()
    cns_pro = _cns_prophylaxis_indicated(inp)
    bulky   = inp.bulky_disease

    if cns_pro:
        flags.append("CNS prophylaxis indicated (institutional criteria met)")
    if bulky:
        flags.append("Bulky disease ≥10 cm – consolidation RT to bulky site recommended")

    # ── Relapsed/Refractory ──────────────────────────────────────────────
    if inp.relapsed_refractory:
        flags.append("Relapsed/refractory DLBCL – salvage therapy + auto-SCT or CAR-T")
        out = (
            "1 Disease Status\nRelapsed / Refractory DLBCL\n\n"
            "2 Salvage Treatment\nR-ICE or R-DHAP × 2–3 cycles → PET-CT reassessment\n"
            "If chemosensitive (PET-negative CR/PR) → High-dose chemo + Autologous SCT\n"
            "If refractory/multiple relapses → CAR-T cell therapy (Axicabtagene / Lisocabtagene)\n\n"
            "3 Bridging Radiotherapy\nISRT 30–40 Gy to bulky site if localised relapse pre-SCT or pre-CAR-T\n\n"
            "4 Rationale\nCORAL trial: R-ICE vs R-DHAP – equivalent; PET response predicts SCT outcome\n"
            "ZUMA-7 / TRANSFORM: CAR-T superior to auto-SCT in early relapse\n\n"
            "5 Follow-up\nPET-CT post-salvage; CT every 3 months post-SCT/CAR-T × 2 years"
        )
        out += _footer(Confidence.AMBER, flags, True)
        return LymphomaResult(formatted_output=out, confidence=Confidence.AMBER,
                              flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)

    # ── Stage I–II ───────────────────────────────────────────────────────
    if stage in ("I","II"):
        out = (
            "1 Lymphoma Type\nDLBCL – Limited Stage\n\n"
            f"2 Stage\nStage {stage}{', Bulky' if bulky else ''}\n\n"
            "3 Primary Treatment\nR-CHOP × 4 cycles + ISRT 30–36 Gy\n"
            "OR R-CHOP × 6 cycles ± ISRT (MInT trial: ISRT improves PFS in bulky/extranodal Stage II)\n\n"
            "4 Radiotherapy\nISRT: 30–36 Gy / 15–18#\n"
            "Target: Initially involved site(s); ILROG ISRT guidelines\n"
            "Technique: IMRT; IGRT\n"
            + (f"\nBulky site: 36 Gy boost to site ≥10 cm\n" if bulky else "")
            + "\n5 CNS Prophylaxis\n"
            + ("High-dose MTX 3 g/m² × 2–4 cycles interspersed with R-CHOP (institutional protocol)\n"
               "OR Intrathecal MTX × 4 (if HD-MTX not feasible)\n"
               if cns_pro
               else "Not indicated (low CNS risk)\n")
            + "\n6 Rationale\nMInT trial: R-CHOP + ISRT improves EFS and OS in limited DLBCL\n"
            "GELA LNH 93-1: CMT (chemo + RT) superior to chemo alone in Stage I–II\n\n"
            "7 Follow-up\nPET-CT end of treatment; CT every 6 months × 2 years, then annually"
        )
        out += _footer(Confidence.GREEN, flags, bool(cns_pro))
        return LymphomaResult(formatted_output=out, confidence=Confidence.GREEN,
                              flags=flags, mdt_required=bool(cns_pro), protocol_reference=PROTOCOL_VERSION)

    # ── Stage III–IV ─────────────────────────────────────────────────────
    r_ipi_label = r_ipi.replace("_"," ").title()
    out = (
        "1 Lymphoma Type\nDLBCL – Advanced Stage\n\n"
        f"2 Stage\nStage {stage} | IPI score: {ipi} | R-IPI: {r_ipi_label}\n\n"
        "3 Primary Treatment\nR-CHOP × 6 cycles (standard)\n"
        "Polatuzumab vedotin + R-CHP (Pola-R-CHP) × 6 cycles: superior EFS in IPI 2+ (POLARIX trial)\n\n"
        "4 Consolidation Radiotherapy\n"
        + ("ISRT 30–36 Gy to bulky site (≥10 cm) post-chemo if PET-positive at bulk site\n" if bulky else
           "Not routinely indicated for Stage III–IV without bulk or residual disease\n")
        + "\n5 CNS Prophylaxis\n"
        + ("High-dose MTX 3 g/m² × 2–4 cycles (institutional protocol)\nIndicators: "
           + ("Age >60; " if inp.age > 60 else "")
           + ("LDH elevated; " if inp.ldh_elevated else "")
           + ("Stage III/IV; " if True else "")
           + ("Kidney/adrenal involvement; " if inp.kidney_adrenal else "")
           + ("HIV/Testicular; " if inp.hiv_positive or inp.testicular else "")
           + "\n"
           if cns_pro
           else "Not indicated (criteria not met)\n")
        + "\n6 Rationale\n"
        "POLARIX: Pola-R-CHP improves EFS vs R-CHOP in IPI ≥2\n"
        "R-CHOP remains standard where Pola not available\n\n"
        "7 Follow-up\nPET-CT end of treatment; CT every 6 months × 2 years"
    )
    conf = Confidence.GREEN if ipi <= 2 else Confidence.AMBER
    out += _footer(conf, flags, bool(cns_pro))
    return LymphomaResult(formatted_output=out, confidence=conf,
                          flags=flags, mdt_required=bool(cns_pro), protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# Follicular Lymphoma
# ─────────────────────────────────────────────────────────────────────────────

def _follicular(inp: LymphomaInput) -> LymphomaResult:
    flags = []
    stage = inp.stage.value
    bulky = inp.bulky_disease

    if stage in ("I","II"):
        out = (
            "1 Lymphoma Type\nFollicular Lymphoma – Limited Stage\n\n"
            f"2 Stage\nStage {stage}{', Bulky' if bulky else ''}\n\n"
            "3 Primary Treatment\nInvolved site RT (ISRT) – potentially curative for localised FL\n"
            "OR Rituximab monotherapy × 4–8 cycles (if RT not feasible)\n\n"
            "4 Radiotherapy\nISRT: 24–30 Gy / 12–15# (24 Gy adequate for Grade 1–2; FORT trial)\n"
            "Target: Involved nodal region(s) + 2 cm margin\n"
            "Technique: ISRT per ILROG; IMRT\n\n"
            "5 Rationale\nBritish National Lymphoma Investigation (BNLI): RT alone achieves 40–50% cure in Stage I/II FL\n"
            "FORT trial: 24 Gy non-inferior to 40 Gy with less toxicity\n\n"
            "6 Follow-up\nCT every 6 months × 2 years, then annually; PET-CT end of RT"
        )
        out += _footer(Confidence.GREEN, flags, False)
        return LymphomaResult(formatted_output=out, confidence=Confidence.GREEN,
                              flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # Advanced FL
    flags.append("Advanced FL – watch-and-wait if asymptomatic; GELF criteria guide treatment initiation")
    out = (
        "1 Lymphoma Type\nFollicular Lymphoma – Advanced Stage\n\n"
        f"2 Stage\nStage {stage}\n\n"
        "3 Management\nWatch-and-wait if asymptomatic (GELF criteria negative)\n\n"
        "4 GELF Criteria for Treatment\n"
        "Any ONE of: Symptomatic disease / Threatened end-organ damage / Cytopenias / "
        "Bulky disease ≥7 cm / Rapid progression\n\n"
        "5 When Treatment Required\n"
        "R-CHOP × 6 cycles OR R-CVP × 6–8 cycles (if anthracycline concerns)\n"
        "Maintenance Rituximab × 2 years after response (PRIMA trial: improved PFS)\n"
        "Obinutuzumab + chemo (GALLIUM trial: superior PFS vs rituximab + chemo)\n\n"
        "6 Radiotherapy\nPalliative ISRT: 4 Gy / 2# (LD-RT) for symptomatic sites\n"
        "OR 24 Gy / 12# ISRT for solitary progressive site (consolidation / palliation)\n\n"
        "7 Rationale\nFOLLOW-UP / RESORT: watch-and-wait non-inferior to early rituximab in GELF-negative\n"
        "PRIMA: maintenance rituximab doubles 5-yr PFS (75% vs 58%)\n\n"
        "8 Follow-up\nCT every 6 months × 2 years, then annually"
    )
    out += _footer(Confidence.AMBER, flags, False)
    return LymphomaResult(formatted_output=out, confidence=Confidence.AMBER,
                          flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# Marginal Zone Lymphoma
# ─────────────────────────────────────────────────────────────────────────────

def _marginal_zone(inp: LymphomaInput) -> LymphomaResult:
    flags = []
    stage = inp.stage.value
    gastric = inp.gastric_malt

    if gastric:
        out = (
            "1 Lymphoma Type\nGastric MALT Lymphoma (Marginal Zone)\n\n"
            f"2 Stage\nStage {stage}\n\n"
            "3 Primary Treatment\nH. pylori eradication (triple therapy) – First-line for all stages\n"
            "Clarithromycin + Amoxicillin + PPI (or Metronidazole if resistant) × 14 days\n\n"
            "4 Response Assessment\nRepeat endoscopy + biopsy 3–6 months after eradication\n\n"
            "5 If Persistent After H. pylori Eradication\n"
            "Stage I–II: ISRT 24–30 Gy (stomach + perigastric LN) – highly effective\n"
            "Rituximab monotherapy × 4–6 cycles (if RT not feasible)\n"
            "Surgery: rarely required; reserved for perforation/obstruction\n\n"
            "6 Rationale\nH. pylori eradication achieves CR in ~75% of Stage I gastric MALT\n"
            "RT achieves >95% local control in eradication-resistant cases\n\n"
            "7 Follow-up\nEndoscopy + biopsy every 6 months × 2 years, then annually"
        )
        out += _footer(Confidence.GREEN, flags, False)
        return LymphomaResult(formatted_output=out, confidence=Confidence.GREEN,
                              flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # Non-gastric MZL
    out = (
        "1 Lymphoma Type\nNon-gastric Marginal Zone Lymphoma\n\n"
        f"2 Stage\nStage {stage}\n\n"
        "3 Primary Treatment\nISRT / Rituximab / Surgery (site-dependent)\n\n"
        "4 By Site\n"
        "Ocular adnexa: ISRT 24 Gy; consider antibiotic eradication (Chlamydia psittaci)\n"
        "Salivary gland / thyroid: ISRT 24–30 Gy or rituximab\n"
        "Splenic MZL: Rituximab monotherapy; splenectomy if rituximab-refractory\n\n"
        "5 Rationale\nISRT achieves excellent long-term control (>90% DFS) for localised MZL\n\n"
        "6 Follow-up\nCT every 6 months × 2 years, then annually; site-specific endoscopy/imaging"
    )
    out += _footer(Confidence.GREEN, flags, False)
    return LymphomaResult(formatted_output=out, confidence=Confidence.GREEN,
                          flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# NK/T-cell Lymphoma
# ─────────────────────────────────────────────────────────────────────────────

def _nk_t_cell(inp: LymphomaInput) -> LymphomaResult:
    flags = []
    stage = inp.stage.value

    if stage in ("I","II"):
        out = (
            "1 Lymphoma Type\nExtranodal NK/T-cell Lymphoma – Nasal Type\n\n"
            f"2 Stage\nStage {stage} (limited)\n\n"
            "3 Primary Treatment\nConcurrent chemoradiotherapy (primary modality)\n\n"
            "4 Radiotherapy\n50 Gy / 25# (institutional protocol)\n"
            "Target: Primary nasal/paranasal tumour + bilateral cervical LN (N0 elective) / involved LN (N+)\n"
            "Technique: IMRT; IGRT; head neck thermoplastic mask\n"
            "OAR: Lens <7 Gy; Retina <50 Gy; Optic chiasm <54 Gy; Brainstem <54 Gy\n\n"
            "5 Chemotherapy\nDeVIC (Dexamethasone + Etoposide + Ifosfamide + Carboplatin) or\n"
            "SMILE (Dexamethasone + MTX + Ifosfamide + L-Asparaginase + Etoposide) concurrent\n"
            "(L-asparaginase based regimens preferred: superior response; ENKTL-001)\n\n"
            "6 Rationale\nNK/T-cell lymphoma is radioresistant to anthracyclines; RT + L-Asp regimen improves OS\n"
            "Primary RT with concurrent chemo superior to chemo-first (local failure risk)\n\n"
            "7 Follow-up\nPET-CT end of treatment; CT every 6 months × 2 years; EBV monitoring"
        )
        out += _footer(Confidence.GREEN, flags, False)
        return LymphomaResult(formatted_output=out, confidence=Confidence.GREEN,
                              flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    flags.append("Advanced NK/T-cell lymphoma – systemic L-asparaginase based regimen; RT to primary site")
    out = (
        "1 Lymphoma Type\nExtranodal NK/T-cell Lymphoma – Nasal Type, Advanced\n\n"
        f"2 Stage\nStage {stage}\n\n"
        "3 Primary Treatment\nL-asparaginase based chemotherapy: SMILE × 2–4 cycles + ISRT 50 Gy to primary\n\n"
        "4 Radiotherapy\n50 Gy / 25# to primary nasal site ± involved regional LN\n\n"
        "5 Consolidation\nAutologous SCT in CR1 for high-risk patients\n\n"
        "6 Rationale\nEBV-driven; MDR-1 expression limits CHOP efficacy; L-Asp regimens overcome resistance\n\n"
        "7 Follow-up\nPET-CT end of treatment; EBV-DNA monitoring; CT every 3 months × 2 years"
    )
    out += _footer(Confidence.AMBER, flags, True)
    return LymphomaResult(formatted_output=out, confidence=Confidence.AMBER,
                          flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# Primary CNS Lymphoma
# ─────────────────────────────────────────────────────────────────────────────

def _primary_cns(inp: LymphomaInput) -> LymphomaResult:
    flags = ["Primary CNS Lymphoma – high-dose MTX based protocol; WBRT only after chemo response"]
    elderly = (inp.age >= 60)

    out = (
        "1 Lymphoma Type\nPrimary CNS Lymphoma (PCNSL)\n\n"
        "2 Stage\nCNS confined\n\n"
        "3 Primary Treatment\nHigh-dose Methotrexate (HD-MTX) based chemotherapy\n\n"
        "4 Induction Chemotherapy\n"
        "HD-MTX 3 g/m² every 2 weeks × 4–8 cycles\n"
        "MATRix: HD-MTX + Cytarabine + Thiotepa + Rituximab (IELSG32: CR rate 49%)\n"
        "R-MPV: Rituximab + MTX + Procarbazine + Vincristine (MSKCC protocol)\n\n"
        "5 Consolidation\n"
        + ("Whole Brain RT (WBRT) 30–36 Gy / 15–18# after CR: standard consolidation (post-chemo)\n"
           "High-dose chemo + auto-SCT: preferred consolidation if fit/young (avoids WBRT neurotoxicity)\n"
           if not elderly else
           "WBRT 40 Gy / 20# (post-chemo CR) OR reduced-dose WBRT 23.4 Gy (after CR)\n"
           "Avoid WBRT if severe cognitive impairment risk; palliative HD-MTX maintenance\n")
        + "\n6 Response Assessment\nMRI brain with contrast after 4 cycles; PET-CT if vitreoretinal involvement\n\n"
        "7 CNS Protocol Doses (Institutional)\n"
        "Post-chemo CR: 36 Gy / 20#\n"
        "Post-chemo PR: 40 Gy / 20#\n"
        "Palliative: 30 Gy / 10#\n\n"
        "8 Rationale\nHD-MTX crosses BBB; backbone of PCNSL treatment\n"
        "IELSG32: MATRix improved CR rate; international standard for fit patients\n\n"
        "9 Follow-up\nMRI brain every 3 months × 2 years; ophthalmic assessment if vitreoretinal involvement"
    )
    out += _footer(Confidence.AMBER, flags, True)
    return LymphomaResult(formatted_output=out, confidence=Confidence.AMBER,
                          flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# Peripheral T-cell Lymphoma
# ─────────────────────────────────────────────────────────────────────────────

def _ptcl(inp: LymphomaInput) -> LymphomaResult:
    flags = ["PTCL – aggressive histology; auto-SCT in first CR for eligible patients"]
    stage = inp.stage.value
    out = (
        "1 Lymphoma Type\nPeripheral T-cell Lymphoma (PTCL)\n\n"
        f"2 Stage\nStage {stage}\n\n"
        "3 Primary Treatment\nCHOP or CHOEP × 6 cycles (Etoposide added for patients <60 years)\n"
        "CHOEP superior to CHOP in young patients (Nordic trial)\n\n"
        "4 Consolidation\nAutologous SCT in first CR for eligible patients (age <65, fit)\n"
        "ISRT 30–40 Gy to bulky/extranodal sites post-chemo\n\n"
        "5 Radiotherapy\nISRT: 30–36 Gy / 15–18# to involved sites\n"
        "Definitive RT: 50–54 Gy for localised extranodal PTCL if surgery/systemic not feasible\n\n"
        "6 Rationale\nPTCL generally has poor prognosis; auto-SCT improves DFS in CR1\n"
        "ALK+ ALCL: excellent outcomes with CHOP; SCT may not add benefit\n\n"
        "7 Follow-up\nPET-CT end of treatment; CT every 3 months × 2 years"
    )
    out += _footer(Confidence.AMBER, flags, True)
    return LymphomaResult(formatted_output=out, confidence=Confidence.AMBER,
                          flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# Mantle Cell Lymphoma
# ─────────────────────────────────────────────────────────────────────────────

def _mantle_cell(inp: LymphomaInput) -> LymphomaResult:
    flags = []
    elderly = (inp.age >= 65)
    stage   = inp.stage.value

    if stage in ("I","II") and not inp.bulky_disease:
        out = (
            "1 Lymphoma Type\nMantle Cell Lymphoma – Limited Stage\n\n"
            f"2 Stage\nStage {stage} (non-bulky)\n\n"
            "3 Primary Treatment\nR-CHOP × 4–6 cycles + ISRT 30–36 Gy (combined modality)\n\n"
            "4 Rationale\nLimited stage MCL rare; CMT achieves good local control\n"
            "Indolent MCL (SOX11-negative, non-nodal): watch-and-wait acceptable\n\n"
            "5 Follow-up\nCT every 6 months × 2 years; MRD monitoring if available"
        )
        out += _footer(Confidence.GREEN, flags, False)
        return LymphomaResult(formatted_output=out, confidence=Confidence.GREEN,
                              flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    flags.append("Advanced MCL – intensive induction + ASCT (young fit) or R-CHOP maintenance (elderly)")
    out = (
        "1 Lymphoma Type\nMantle Cell Lymphoma – Advanced Stage\n\n"
        f"2 Stage\nStage {stage}\n\n"
        "3 Primary Treatment\n"
        + ("Nordic MCL regimen (R-CHOP alternating with R-HAD) + ASCT × 1 (young fit patients)\n"
           "Triangle trial: Ibrutinib addition improves PFS\n"
           if not elderly else
           "R-CHOP × 6 cycles + Rituximab maintenance (SHINE: Ibrutinib + BR improves PFS in elderly)\n")
        + "\n4 Consolidation Radiotherapy\nISRT 30–36 Gy to bulky disease post-chemo\n\n"
        "5 Rationale\nNordic MCL2: ASCT in CR1 improves OS in young fit MCL\n"
        "BTK inhibitors (Ibrutinib, Acalabrutinib): approved for relapsed MCL\n\n"
        "6 Follow-up\nCT + MRD monitoring every 6 months × 3 years"
    )
    out += _footer(Confidence.AMBER, flags, True)
    return LymphomaResult(formatted_output=out, confidence=Confidence.AMBER,
                          flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_lymphoma_case(inp: LymphomaInput) -> LymphomaResult:
    """Route to subtype-specific engine."""
    if inp.ecog >= 3:
        flags = ["Poor performance status – palliative / BSC"]
        out = (
            "1 Lymphoma Type\n"
            f"{inp.subtype.value.upper()}\n\n"
            "2 Performance Status\nECOG ≥ 3 – unfit for standard chemotherapy\n\n"
            "3 Treatment\nBest supportive care / palliative intent\n"
            "Palliative RT (30 Gy/10#) for symptomatic sites\n\n"
            "4 Follow-up\nSymptom-based; palliative care referral"
        )
        out += _footer(Confidence.RED, flags, True)
        return LymphomaResult(formatted_output=out, confidence=Confidence.RED,
                              flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)

    s = inp.subtype
    if s == LymphomaSubtype.HODGKIN:           return _hodgkin(inp)
    if s == LymphomaSubtype.DLBCL:             return _dlbcl(inp)
    if s == LymphomaSubtype.FOLLICULAR:        return _follicular(inp)
    if s == LymphomaSubtype.MARGINAL_ZONE:     return _marginal_zone(inp)
    if s == LymphomaSubtype.NK_T_CELL:         return _nk_t_cell(inp)
    if s == LymphomaSubtype.PRIMARY_CNS:       return _primary_cns(inp)
    if s == LymphomaSubtype.PERIPHERAL_T_CELL: return _ptcl(inp)
    if s == LymphomaSubtype.MANTLE_CELL:       return _mantle_cell(inp)

    flags = ["Subtype not recognised – MDT required"]
    out = (
        f"1 Lymphoma Subtype\n{inp.subtype.value}\n\n"
        "2 Recommendation\nMDT discussion required\n"
    )
    out += _footer(Confidence.RED, flags, True)
    return LymphomaResult(formatted_output=out, confidence=Confidence.RED,
                          flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)
