"""
Production-Ready GI Cancers Clinical Decision Support Engine
Institutional GI Cancers Protocol v1.0

Sites:
  • Esophagus — Early (T1a→EMR) / Locally advanced (CROSS-based CRT→surgery) /
                Definitive CRT / Cervical / Metastatic
  • Stomach   — Early / Perioperative FLOT / Post-op CRT / Unresectable / Metastatic
  • Rectum    — Early / Low-risk (SCRT or LCRT→TME) / High-risk (TNT: SCRT+chemo) /
                Watch-and-wait (cCR) / Post-op CRT
  • Anal Canal — T1–T4 definitive chemoRT (organ preservation) / Metastatic
  • Pancreas  — Resectable / Borderline / LAPC / Metastatic
  • Colon     — Stage I–IV adjuvant decision tree

IMPORTANT: Decision-support only. All outputs require clinical judgment.
Cases flagged RED require MDT discussion before treatment.
"""

from .gi_models  import GIInput, GIResult, Confidence
from .gi_config  import (
    PROTOCOL_VERSION,
    ESOPHAGUS_PREOP_RT_DOSE, ESOPHAGUS_DEFINITIVE_RT_DOSE,
    ESOPHAGUS_POSTOP_RT_DOSE, ESOPHAGUS_CERVICAL_RT_DOSE,
    STOMACH_POSTOP_RT_DOSE,
    RECTUM_LCRT_DOSE, RECTUM_SCRT_DOSE,
    ANAL_EARLY_RT_DOSE, ANAL_ADVANCED_RT_DOSE, ANAL_ELECTIVE_LN_DOSE,
    PANCREAS_ADJUVANT_RT_DOSE, PANCREAS_DEFINITIVE_RT_DOSE,
    COLON_ADJUVANT_CHEMO_LOW, COLON_ADJUVANT_CHEMO_HIGH,
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


def _poor_ps(site: str) -> GIResult:
    flags = ["Poor performance status – ECOG ≥ 3"]
    out = (
        f"1 Disease Subsite\n{site.title()}\n\n"
        "2 Performance Status\nECOG ≥ 3 – unfit for standard treatment\n\n"
        "3 Primary Treatment\nBest supportive care / palliative intent\n\n"
        "4 Radiotherapy\nPalliative short-course RT if symptomatic\n\n"
        "5 Rationale\nPoor PS precludes curative-intent therapy; individualised MDT plan\n\n"
        "6 Follow-up\nSymptom-based; palliative care referral"
    )
    out += _footer(Confidence.RED, flags, True, PROTOCOL_VERSION)
    return GIResult(formatted_output=out, confidence=Confidence.RED,
                    flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# ESOPHAGUS ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _esophagus(inp: GIInput) -> GIResult:
    flags   = []
    t       = (inp.esophagus_t_stage or "").upper()
    n       = (inp.esophagus_n_stage or "N0").upper()
    m       = (inp.esophagus_m_stage or "M0").upper()
    loc     = (inp.esophagus_location or "lower").lower()
    hist    = inp.histology.value
    stage   = (inp.esophagus_overall_stage or "").upper()
    is_scc  = (hist == "scc")
    is_met  = (m == "M1" or "M1" in m)

    # ── Metastatic ──────────────────────────────────────────────────────
    if is_met:
        flags.append("Metastatic disease – palliative intent")
        out = (
            "1 Disease Subsite\n"
            f"{loc.replace('_',' ').title()} esophagus\n\n"
            "2 Histology\n"
            f"{hist.upper()}\n\n"
            "3 Stage\nStage IVA/IVB – Metastatic\n\n"
            "4 Primary Treatment\nPalliative systemic chemotherapy\n\n"
            "5 Chemotherapy Options\n"
            "• Carboplatin + Paclitaxel (preferred for frail / borderline fit)\n"
            "• Cisplatin + 5-FU / FOLFOX (fit patients)\n"
            "• Pembrolizumab ± chemo for PD-L1 CPS ≥10 (adenocarcinoma: CheckMate 649 / KEYNOTE-590)\n\n"
            "6 Radiotherapy\nPalliative RT: 30 Gy/10# for dysphagia / bleeding\n\n"
            "7 Rationale\nCurative intent not achievable; systemic control + symptom management priority\n\n"
            "8 Follow-up\nResponse-based imaging; symptom-oriented review"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.AMBER,
                        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)

    # ── Very Early (T1a) → EMR ───────────────────────────────────────────
    if t in ("T1A", "T1"):
        out = (
            "1 Disease Subsite\n"
            f"{loc.replace('_',' ').title()} esophagus\n\n"
            "2 Histology\n"
            f"{hist.upper()}\n\n"
            "3 Stage\nStage I (T1a N0 M0)\n\n"
            "4 Primary Treatment\nEndoscopic mucosal resection (EMR) / Endoscopic submucosal dissection (ESD)\n\n"
            "5 Adjuvant Therapy\nNot required for T1a mucosal disease\n\n"
            "6 Rationale\nMucosal disease → minimal nodal risk (<2%); organ-preserving endoscopic resection curative\n"
            "Barrett's surveillance programme post-EMR for adenocarcinoma\n\n"
            "7 Follow-up\nEndoscopic surveillance every 3 months × 1 year, then annually\n"
            "Ablation of residual Barrett's mucosa if adenocarcinoma"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # ── Cervical esophagus / upper third → definitive CRT (avoid surgery) ─
    if loc == "upper_cervical":
        flags.append("Cervical esophagus – surgery carries high morbidity; definitive CRT preferred")
        out = (
            "1 Disease Subsite\nCervical / upper esophagus\n\n"
            f"2 Histology\n{hist.upper()}\n\n"
            f"3 Stage\n{t} {n} M0\n\n"
            "4 Primary Treatment\nDefinitive concurrent chemoradiation\n\n"
            f"5 Radiotherapy\n{ESOPHAGUS_CERVICAL_RT_DOSE}\n"
            "Target: Primary + bilateral SCF + mediastinal LN\n"
            "Technique: IMRT; IGRT recommended\n\n"
            "6 Chemotherapy\nWeekly Carboplatin + Paclitaxel (CROSS regimen) OR Cisplatin + 5-FU q3w\n\n"
            "7 Rationale\nLaryngopharyngectomy carries high morbidity; definitive CRT offers equivalent control\n"
            "Surgery reserved for CRT failure\n\n"
            "8 Response Assessment\nPET-CT / endoscopy at 6–8 weeks post-CRT\n\n"
            "9 Follow-up\nUGI scopy every 6 months × 1 year, then annually"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # ── Locally advanced T2–T4a, N0–N+ → neoadjuvant CRT then surgery ────
    # (T4b unresectable → definitive CRT)
    if t in ("T4B",):
        flags.append("T4b – unresectable; definitive CRT only")
        out = (
            "1 Disease Subsite\n"
            f"{loc.replace('_',' ').title()} esophagus\n\n"
            f"2 Histology\n{hist.upper()}\n\n"
            f"3 Stage\nStage IIIc–IVA ({t} {n} M0) – Unresectable\n\n"
            "4 Primary Treatment\nDefinitive concurrent chemoradiation\n\n"
            f"5 Radiotherapy\n{ESOPHAGUS_DEFINITIVE_RT_DOSE}\n"
            "Technique: IMRT/VMAT; IGRT mandatory\n\n"
            "6 Chemotherapy\nWeekly Carboplatin + Paclitaxel (CROSS)\nOR Cisplatin + 5-FU q3w\n\n"
            "7 Rationale\nT4b involves vital structures; surgery not feasible; definitive CRT is standard (INT 0123, RTOG 8501)\n\n"
            "8 Response Assessment\nPET-CT at 6–8 weeks; UGI scopy; CT chest with upper abdomen\n\n"
            "9 Follow-up\nUGI scopy every 6 months × 1 year, then annually"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.AMBER,
                        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)

    # ── Resectable locally advanced T2–T4a ───────────────────────────────
    adeno_note = (
        "FLOT perioperative chemotherapy preferred for adenocarcinoma GEJ/lower esophagus (ESOPEC: OS benefit)"
        if hist == "adenocarcinoma"
        else "CROSS protocol (Carboplatin + Paclitaxel + RT 41.4 Gy): standard for SCC"
    )
    n_positive = (n != "N0")
    out = (
        "1 Disease Subsite\n"
        f"{loc.replace('_',' ').title()} esophagus\n\n"
        f"2 Histology\n{hist.upper()}\n\n"
        f"3 Stage\nStage II–III ({t} {n} M0) – Locally Advanced Resectable\n\n"
        "4 Primary Treatment\nNeoadjuvant chemoradiation → Surgery (Ivor-Lewis / transhiatal oesophagectomy)\n\n"
        f"5 Radiotherapy\n{ESOPHAGUS_PREOP_RT_DOSE}\n"
        "Technique: IMRT; IGRT recommended\n"
        "CTV: Primary + periesophageal + mediastinal LN; celiac axis LN for lower/GEJ tumors\n"
        "PTV: CTV + 0.5–1 cm\n\n"
        "6 Chemotherapy (concurrent)\nWeekly Carboplatin (AUC 2) + Paclitaxel 50 mg/m² × 5 weeks (CROSS)\n"
        "Alternatively: Cisplatin + 5-FU q3w\n\n"
        f"7 Key Trial Rationale\n{adeno_note}\n"
        "CROSS trial: pCR ~29%, R0 resection ↑, median OS 49.4 vs 24.0 months\n\n"
        "8 Adjuvant Therapy\n"
        + ("Nivolumab 240 mg q2w × 12 months if residual disease post-surgery (CheckMate 577: DFS benefit)" 
           if hist == "adenocarcinoma"
           else "No routine adjuvant therapy if pCR; consider nivolumab for residual SCC per CheckMate 577")
        + "\n\n"
        "9 Response Assessment\nPET-CT / UGI scopy / CT chest with upper abdomen 4–6 weeks post-CRT\n\n"
        "10 Follow-up\nUGI scopy every 6 months × 1 year, then annually\nCT chest/abdomen at 6, 12, 24 months"
    )
    out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
    return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                    flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# STOMACH ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _stomach(inp: GIInput) -> GIResult:
    flags  = []
    t      = (inp.stomach_t_stage or "").upper()
    n      = (inp.stomach_n_stage or "N0").upper()
    m      = (inp.stomach_m_stage or "M0").upper()
    stage  = (inp.stomach_overall_stage or "").upper()
    is_met = (m == "M1" or stage == "4B")
    her2   = inp.her2_positive
    prior_sx = inp.prior_surgery_stomach

    # ── Metastatic ──────────────────────────────────────────────────────
    if is_met:
        flags.append("Metastatic disease – palliative intent")
        her2_line = "Trastuzumab + Cisplatin/Oxaliplatin + 5-FU/Capecitabine (ToGA trial)" if her2 else "FOLFOX or CAPOX (first-line)"
        out = (
            "1 Stage\nStage IVB – Metastatic gastric cancer\n\n"
            "2 Primary Treatment\nPalliative systemic chemotherapy\n\n"
            f"3 Regimen\n{her2_line}\n"
            "Nivolumab + chemotherapy: CheckMate 649 – CPS ≥5 PD-L1 tumors benefit\n"
            "Pembrolizumab: KEYNOTE-590 / KEYNOTE-811 (HER2+ with pembrolizumab)\n\n"
            "4 Rationale\nCurative surgery not indicated; systemic control and QoL management priority\n\n"
            "5 Follow-up\nResponse assessment CT every 2–3 cycles; symptom monitoring"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.AMBER,
                        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)

    # ── Early gastric cancer (T1a/T1b) ──────────────────────────────────
    if t in ("T1A", "T1B", "T1"):
        out = (
            "1 Stage\nEarly gastric cancer (T1 N0 M0)\n\n"
            "2 Primary Treatment\nEndoscopic resection (EMR/ESD) for T1a mucosal disease\n"
            "Surgical gastrectomy (D2) if T1b or submucosal involvement\n\n"
            "3 Adjuvant Therapy\nNot required for T1a with clear margins\n"
            "Consider adjuvant chemo for T1b with high-risk features (LVI, grade 3)\n\n"
            "4 Rationale\nMucosal disease confined – endoscopic resection is curative\n"
            "Submucosal disease requires surgical staging and LN assessment\n\n"
            "5 Follow-up\nUGI scopy every 6 months × 1 year, then annually\n"
            "Monitor Vitamin B12 and iron post-gastrectomy"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # ── Post-op (prior surgery, no neoadjuvant) → adjuvant CRT / chemo ──
    if prior_sx:
        flags.append("Prior surgery without neoadjuvant therapy – adjuvant therapy decision")
        out = (
            "1 Stage\n"
            f"Post-surgical gastric cancer – {t} {n} M0\n\n"
            "2 Adjuvant Options\n"
            "Option A: Adjuvant CRT (INT-0116/Macdonald): 45 Gy + Cisplatin/5-FU\n"
            "  → Indicated if no preoperative chemotherapy and D1 or less dissection\n"
            "Option B: Adjuvant chemotherapy (CLASSIC): CapeOX × 8 cycles post D2 dissection\n"
            "  → Preferred if adequate D2 dissection performed\n\n"
            "3 Radiotherapy (if CRT chosen)\n"
            f"{STOMACH_POSTOP_RT_DOSE}\n"
            "Target: Tumour bed + perigastric LN ± mediastinal/splenic LN (as per location)\n"
            "Technique: 3DCRT/IMRT; IGRT recommended\n\n"
            "4 Chemotherapy\n"
            "CRT: Cisplatin + 5-FU concurrent (INT-0116) OR Capecitabine concurrent\n"
            "Chemo alone: CapeOX × 8 cycles OR FOLFOX × 6 months (CLASSIC)\n\n"
            "5 Rationale\nINT-0116: CRT improves 3-yr OS (50% vs 41%) when no preop chemo\n"
            "CLASSIC: CapeOX post-D2 improves DFS and OS in Stage II/III\n\n"
            "6 Follow-up\nUGI scopy 6 monthly × 1 year, then annually × 5 years; Vit B12/Iron monitoring"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # ── Unresectable locally advanced ────────────────────────────────────
    t4b = (t == "T4B" or stage == "4A")
    if t4b:
        flags.append("Unresectable / Stage IVA – definitive CRT or systemic therapy")
        out = (
            "1 Stage\nLocally advanced unresectable gastric cancer (T4b / IVA)\n\n"
            "2 Primary Treatment\nDefinitive concurrent chemoradiation\n\n"
            "3 Radiotherapy\n50–54 Gy / 25–28#\n"
            "Target: Gross tumour + regional LN per location\n"
            "Technique: IMRT; IGRT recommended\n\n"
            "4 Chemotherapy\nFOLFOX-based CRT (ACCORD-17/PRODIGE) OR Oxaliplatin + Capecitabine\n\n"
            "5 Rationale\nChemoRT superior to RT alone in unresectable disease (ACCORD/PRODIGE meta-analysis)\n"
            "Conversion surgery considered if significant response\n\n"
            "6 Follow-up\nCT reassessment every 2 cycles; surgical re-evaluation after 4–6 cycles"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.AMBER,
                        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)

    # ── Resectable locally advanced → perioperative FLOT ────────────────
    out = (
        "1 Stage\n"
        f"Locally advanced resectable gastric cancer – {t} {n} M0 (Stage II/III)\n\n"
        "2 Primary Treatment\nPerioperative chemotherapy + surgery (D2 gastrectomy)\n\n"
        "3 Regimen\nFLOT: Docetaxel + Oxaliplatin + Leucovorin + 5-FU q2w × 4 cycles pre-op + 4 cycles post-op\n"
        "(FLOT-4 trial: superior OS vs ECF; preferred for fit patients)\n"
        "Moderate PS: FOLFOX q2w × 6 cycles perioperatively\n\n"
        "4 Surgery\nD2 gastrectomy (subtotal or total depending on location)\n"
        "Aim: R0 resection; ≥15 lymph nodes examined\n\n"
        "5 Post-operative Management\n"
        "Complete remaining 4 FLOT cycles post-operatively if tolerated\n"
        "Post-op CRT (INT-0116): only if no neoadjuvant therapy was given and D1 dissection\n\n"
        "6 Rationale\nFLOT-4: superior pCR (15% vs 6%) and OS vs ECF; FLOT is preferred standard\n"
        "MAGIC trial: perioperative ECF improves OS over surgery alone\n\n"
        "7 Follow-up\nUGI scopy 6 monthly × 1 year; CT scan at 6 and 12 months; Vit B12 / Iron annually"
    )
    out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
    return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                    flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# RECTUM ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _rectum(inp: GIInput) -> GIResult:
    flags   = []
    t       = (inp.rectum_t_stage or "").upper()
    n       = (inp.rectum_n_stage or "N0").upper()
    m       = (inp.rectum_m_stage or "M0").upper()
    crm     = inp.crm_threatened
    emvi    = inp.emvi_positive
    loc     = (inp.rectum_location or "mid").lower()
    prior_sx = inp.prior_surgery_rectum
    is_met  = ("M1" in m)

    if is_met:
        flags.append("Metastatic rectal cancer – MDT; consider surgical resection of isolated liver/lung mets")
        out = (
            "1 Stage\nStage IV – Metastatic rectal cancer\n\n"
            "2 Primary Treatment\nSystemic chemotherapy (FOLFOX / FOLFIRI / FOLFOXIRI ± bevacizumab or anti-EGFR)\n"
            "Consider pelvic RT for local symptom control\n\n"
            "3 Rationale\nMDT review for resectability of metastases; KRAS/RAS/BRAF status guides targeted therapy\n"
            "Resection of synchronous liver/lung mets in selected patients improves OS\n\n"
            "4 Follow-up\nCEA every 3 months; CT abdomen/pelvis at 3-monthly intervals"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.AMBER,
                        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)

    # ── Early rectal cancer (T1–T2 N0) ─────────────────────────────────
    if t in ("T1","T2") and n == "N0":
        out = (
            "1 Stage\nStage I – Early rectal cancer (T1–T2 N0 M0)\n\n"
            "2 Primary Treatment\nLow anterior resection (LAR) or APR with total mesorectal excision (TME)\n"
            "Local excision (TEM/TAMIS) for T1 lesions with favourable features (well-diff, <3 cm, no LVSI)\n\n"
            "3 Neoadjuvant Therapy\nNot routinely required for T1–T2 N0\n"
            "Consider short-course RT (5×5 Gy) for T2 tumours in low rectum if sphincter preservation uncertain\n\n"
            "4 Rationale\nEarly disease; surgery alone achieves excellent local control\n"
            "Watch-and-wait after radical chemoRT is emerging but not standard for T1–T2\n\n"
            "5 Follow-up\nCEA every 3 months × 2 years, then 6 monthly × 5 years\n"
            "Colonoscopy 1 year post-surgery; CT abdomen/pelvis yearly"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # ── Post-op rectal (prior surgery without neoadjuvant) ──────────────
    if prior_sx:
        flags.append("Prior surgery without neoadjuvant therapy – adjuvant CRT indicated if high-risk features")
        out = (
            "1 Disease Status\nPost-operative rectal cancer\n\n"
            "2 Adjuvant Therapy\n"
            "Adjuvant CRT recommended for R1/R2 resection or T3–T4 tumours without adequate preoperative RT\n\n"
            "3 Radiotherapy\n"
            f"{RECTUM_LCRT_DOSE}\n"
            "Target: Mesorectal bed + presacral space + internal iliac LN; extend to ext iliac if pT4\n"
            "Technique: IMRT; IGRT; full bladder\n\n"
            "4 Chemotherapy\nCapecitabine concurrent (825 mg/m² bd on RT days)\n\n"
            "5 Rationale\nGerman Rectal Cancer Study: postop CRT inferior to preop CRT in local control\n"
            "Post-op CRT only if no preoperative RT administered and high-risk features present\n\n"
            "6 Follow-up\nCEA every 3 months × 2 years; CT abdomen/pelvis yearly"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # ── Locally advanced rectal cancer (T3/T4 or N+) ─────────────────────
    high_risk = crm or emvi or t in ("T4A","T4B") or "N2" in n
    if high_risk:
        flags.append("High-risk LARC features – TNT approach (RAPIDO/PRODIGE 23) recommended")
        if crm: flags.append("CRM threatened – intensified treatment required")
        if emvi: flags.append("EMVI positive – systemic chemotherapy prioritised")

        out = (
            "1 Risk Features\n"
            f"{'CRM threatened; ' if crm else ''}{'EMVI positive; ' if emvi else ''}{t} {n} – High-risk LARC\n\n"
            "2 Primary Treatment\nTotal Neoadjuvant Therapy (TNT) – preferred for high-risk features\n\n"
            "3 TNT Options\n"
            "RAPIDO strategy: Short-course RT (25 Gy/5#) → CAPOX × 6 or FOLFOX × 9 cycles → TME\n"
            "PRODIGE 23 strategy: FOLFIRINOX × 6 cycles → Long-course CRT (50.4 Gy + Capecitabine) → TME\n\n"
            "4 Radiotherapy\n"
            f"Short-course RT: {RECTUM_SCRT_DOSE} then delayed surgery\n"
            f"Long-course CRT: {RECTUM_LCRT_DOSE}\n"
            "Target: Entire rectum + mesorectum + presacral space + internal iliac LN\n"
            "T4: Include external iliac LN; Technique: IMRT; IGRT mandatory; Full bladder\n"
            "OAR: Small bowel Dmax <50 Gy; Bladder V45 <65cc; Femur V40 <40%\n\n"
            "5 Chemotherapy\nCapecitabine 825 mg/m² bd (concurrent with LCRT)\n"
            "FOLFIRINOX or FOLFOX/CAPOX (systemic component of TNT)\n\n"
            "6 Surgery\nTME (LAR / APR depending on level and sphincter function)\n"
            "Aim: R0 resection; CRM >1 mm\n"
            "Watch-and-wait: Consider for clinical complete response (cCR) post-TNT (OPRA data)\n\n"
            "7 Rationale\nRAPIDA/PRODIGE 23: TNT improves pCR (~28%), reduces distant mets, enables organ preservation\n"
            "German Rectal Cancer Study: preop CRT → LR 6% vs 13% postop; no OS difference\n\n"
            "8 Follow-up\nCEA every 3 months × 2 years; colonoscopy 1 year post-op\n"
            "CT abdomen/pelvis yearly; MRI pelvis every 6 months if watch-and-wait"
        )
        out += _footer(Confidence.GREEN, flags, bool([f for f in flags if "MDT" in f]), PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # ── Standard locally advanced (T3 N0–N1) ─────────────────────────────
    out = (
        "1 Risk Features\n"
        f"{t} {n} – Locally advanced rectal cancer\n\n"
        "2 Primary Treatment\nNeoadjuvant chemoradiation → TME surgery\n\n"
        "3 Radiotherapy\n"
        f"Long-course CRT: {RECTUM_LCRT_DOSE}\n"
        "OR Short-course RT (25 Gy/5#) with delayed surgery (Stockholm III: equivalent pCR with delay)\n"
        "Target: Rectum + mesorectum + presacral + internal iliac LN\n"
        "Technique: IMRT; IGRT; Full bladder\n\n"
        "4 Chemotherapy\nCapecitabine 825 mg/m² bd on RT days (concurrent)\n\n"
        "5 Surgery\nTME 6–12 weeks post-CRT (LAR preferred if sphincter-preserving feasible)\n\n"
        "6 Rationale\nPreoperative CRT improves margin negativity and local control\n"
        "German Rectal Cancer Study: preop CRT superior to postop CRT for local control\n\n"
        "7 Follow-up\nCEA every 3 months × 2 years; CT abdomen/pelvis yearly; colonoscopy 1 year post-op"
    )
    out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
    return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                    flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# ANAL CANAL ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _anal_canal(inp: GIInput) -> GIResult:
    flags = []
    t     = (inp.anal_t_stage or "T1").upper()
    n     = (inp.anal_n_stage or "N0").upper()
    m     = (inp.anal_m_stage or "M0").upper()
    hiv   = inp.hiv_positive
    is_met = ("M1" in m)

    if hiv:
        flags.append("HIV positive – modified CRT; careful immunostatus assessment; MMC dose may be reduced")

    if is_met:
        flags.append("Metastatic anal cancer – palliative systemic therapy")
        out = (
            "1 Stage\nStage IV – Metastatic anal cancer\n\n"
            "2 Primary Treatment\nPalliative systemic chemotherapy\n"
            "Carboplatin + Paclitaxel (InterAACT: superior response vs Cisplatin+5-FU, less toxicity)\n\n"
            "3 Rationale\nInterAACT 2020: Carbo+Pacli new standard for metastatic anal SCC\n\n"
            "4 Follow-up\nResponse-based imaging; symptom monitoring"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.AMBER,
                        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)

    # ── Determine dose based on T/N ──────────────────────────────────────
    n_size_large = ("N1B" in n or "N1C" in n or n == "N1")  # proxy for N>3cm
    t_advanced   = t in ("T3","T4")

    if t == "T1":
        ptv_dose = "54 Gy / 30#"
        ln_dose  = "50.4 Gy / 30#" if not n_size_large else "54 Gy / 30#"
        elective_dose = ANAL_ELECTIVE_LN_DOSE
    elif t == "T2":
        ptv_dose = "50.4 Gy / 28#"
        ln_dose  = "42 Gy / 28# (N0) or 50.4 Gy (N+)"
        elective_dose = ANAL_ELECTIVE_LN_DOSE
    else:
        ptv_dose = "54–59 Gy / 30–33#"
        ln_dose  = "54 Gy / 30# for enlarged nodes"
        elective_dose = ANAL_ELECTIVE_LN_DOSE

    stage_label = (
        "Stage I" if t == "T1" and n == "N0" else
        "Stage IIA" if t == "T2" and n == "N0" else
        "Stage IIB" if t == "T3" and n == "N0" else
        "Stage III" if n != "N0" or t == "T4" else "Stage II"
    )

    out = (
        f"1 Disease Subsite\nAnal canal – Squamous cell carcinoma\n\n"
        f"2 Stage\n{stage_label} ({t} {n} M0)\n\n"
        "3 Primary Treatment\nDefinitive concurrent chemoradiation (organ preservation – standard of care)\n\n"
        f"4 Radiotherapy (RTOG 0529 / IMRT-based SIB)\n"
        f"PTV primary (anal tumour + 2 cm): {ptv_dose}\n"
        f"PTV involved LN (GTV-N + 1 cm): {ln_dose}\n"
        f"PTV elective (mesorectum + internal/external iliac + inguinal LN): {elective_dose}\n"
        "Technique: IMRT (SIB); IGRT (daily kV + weekly CBCT)\n"
        "Position: Supine; full bladder; from L1 to mid-femur\n"
        "OAR: Small bowel Dmax <50 Gy; Bladder V35 <50%; Femur V44 <5%; Genitalia V40 <5%\n\n"
        "5 Chemotherapy\nMitomycin C 12 mg/m² IV bolus day 1 + 5-Fluorouracil 1000 mg/m²/day d1–4 (wk 1 + wk 5)\n"
        "(Standard: ACT II, RTOG 8704 – MMC superior to cisplatin in concurrent setting)\n"
        + (f"\nHIV modification: Reduce MMC dose; monitor CD4 count closely; avoid immunosuppression\n" if hiv else "")
        + "\n6 Organ Preservation Rationale\n"
        "UKCCCR / EORTC 22861: CRT vs RT alone – superior local control and colostomy-free survival\n"
        "Surgery (APR) reserved for CRT failure / residual disease at 12-week assessment\n\n"
        "7 Response Assessment\nDRE + anoscopy at 8–12 weeks post-CRT; CT abdomen/pelvis at 12 weeks\n"
        "Biopsy only if clinical incomplete response\n\n"
        "8 Follow-up\nDRE + inguinal LN exam every 3 months × 5 years\n"
        "Anoscopy every 6 months × 3 years; CT abdomen/pelvis yearly × 3 years"
    )
    out += _footer(Confidence.GREEN, flags, bool(flags), PROTOCOL_VERSION)
    return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                    flags=flags, mdt_required=bool(flags), protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# PANCREAS ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _pancreas(inp: GIInput) -> GIResult:
    flags  = []
    resect = (inp.pancreas_resectability or "resectable").lower()
    t      = (inp.pancreas_t_stage or "").upper()
    n      = (inp.pancreas_n_stage or "N0").upper()
    m      = (inp.pancreas_m_stage or "M0").upper()
    margin = (inp.pancreas_margin_status or "unknown").lower()
    brca   = inp.brca_mutation
    prior_sx = inp.prior_surgery_pancreas

    # ── Metastatic ──────────────────────────────────────────────────────
    if resect == "metastatic" or m == "M1":
        flags.append("Metastatic disease – palliative intent")
        brca_note = "\nOlaparib maintenance after platinum response (POLO trial: improved PFS) – BRCA-mutated" if brca else ""
        out = (
            "1 Stage\nStage IV – Metastatic pancreatic cancer\n\n"
            "2 Primary Treatment\nSystemic chemotherapy (palliative intent)\n\n"
            "3 Regimen\nmFOLFIRINOX (Oxaliplatin + Irinotecan + Leucovorin + 5-FU) – fit patients (PRODIGE-4: OS 11.1 vs 6.8 mo)\n"
            "Gemcitabine + Nab-paclitaxel (MPACT: OS 8.5 vs 6.7 mo) – ECOG 2 / borderline fit\n"
            f"{brca_note}\n\n"
            "4 Rationale\nFOLFIRINOX preferred for fit patients; gem + nab-pacli for ECOG 1–2\n"
            "Supportive care: biliary stent / coeliac plexus block for pain\n\n"
            "5 Follow-up\nCA 19-9 every 2–3 cycles; CT scan every 2–3 cycles for response assessment"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.AMBER,
                        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)

    # ── Locally advanced (unresectable) ─────────────────────────────────
    if resect == "locally_advanced":
        flags.append("Locally advanced pancreatic cancer – induction chemo then reassess resectability")
        out = (
            "1 Stage\nLocally advanced unresectable pancreatic cancer (Stage III)\n\n"
            "2 Primary Treatment\nInduction systemic chemotherapy (4–6 months) → Reassess resectability\n\n"
            "3 Induction Regimen\nmFOLFIRINOX × 6–8 cycles (preferred fit patients)\n"
            "Gemcitabine + Nab-paclitaxel × 4–6 cycles (ECOG 2 / borderline)\n\n"
            "4 After Induction Response\nIf downstaging / stable: Consider consolidation CRT\n"
            f"Consolidation RT: {PANCREAS_DEFINITIVE_RT_DOSE}\n"
            "Target: GTV (primary + nodes) + 5 mm PTV; Technique: IMRT/SBRT\n"
            "LAP07 trial: CRT delayed local progression but did not improve OS vs chemo alone\n\n"
            "5 If Conversion to Resectable\nProceed to surgery (Whipple or distal pancreatectomy)\n\n"
            "6 Rationale\nNeoadjuvant chemo ± CRT: NABPLAGEM: FOLFIRINOX slightly better conversion rate\n"
            "Stent placement (ERCP) if biliary obstruction before chemotherapy\n\n"
            "7 Follow-up\nCA 19-9 + CT abdomen/pelvis every 2 cycles; MDT reassessment after 4 cycles"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.AMBER,
                        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)

    # ── Borderline resectable ────────────────────────────────────────────
    if resect == "borderline_resectable":
        flags.append("Borderline resectable – neoadjuvant therapy required before surgery")
        out = (
            "1 Stage\nBorderline resectable pancreatic cancer\n\n"
            "2 Primary Treatment\nNeoadjuvant chemotherapy → Re-evaluate → Surgery if resectable\n\n"
            "3 Neoadjuvant Regimen\nmFOLFIRINOX × 4–6 cycles (preferred) – PREOPANC: improved DFS and R0 resection\n"
            "Gemcitabine + Nab-paclitaxel × 3–4 cycles (ECOG 2)\n\n"
            "4 Neoadjuvant CRT (optional after chemo)\n45–54 Gy / 25–30# + Gemcitabine or Capecitabine concurrent\n"
            "PREOPANC: CRT improved R0 resection and DFS in borderline group\n\n"
            "5 Surgery (if response)\nWhipple's (pancreaticoduodenectomy) or distal pancreatectomy\n"
            "Aim: R0 resection; vascular reconstruction if required (SMV/PV involvement)\n\n"
            "6 Post-operative Adjuvant\nmFOLFIRINOX × 4 cycles if not given pre-op (PRODIGE-24: OS 54.4 vs 35 mo)\n\n"
            "7 Rationale\nFOLFIRINOX is preferred regimen for fit patients with borderline resectable disease\n"
            "Downstaging improves R0 resection and overall outcomes\n\n"
            "8 Follow-up\nCA 19-9 every 3 months; CT abdomen/pelvis every 3 months × 2 years"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # ── Resectable ───────────────────────────────────────────────────────
    is_r1 = (margin in ("r1", "r2", "positive"))
    adjuvant_rt_note = (
        f"Adjuvant RT indicated (R1 resection): {PANCREAS_ADJUVANT_RT_DOSE}\n"
        "Target: Post-op bed + PA LN + proximal SMA + celiac axis + PV region\n"
        "Concurrent: 5-FU or Gemcitabine\n"
        if is_r1
        else "Adjuvant RT: Not routine for R0 resection; only R1/R2 margins\n"
    )

    out = (
        "1 Stage\n"
        f"Resectable pancreatic cancer – {t} {n} M0\n\n"
        "2 Primary Treatment\n"
        f"Surgery: Whipple's (pancreaticoduodenectomy) for head / {'Distal pancreatectomy for body-tail'}\n\n"
        "3 Adjuvant Chemotherapy\nmFOLFIRINOX × 12 cycles (preferred; PRODIGE-24: OS 54.4 vs 35 months vs gemcitabine)\n"
        "Gemcitabine + Capecitabine × 6 cycles (ESPAC-4: OS 28 vs 25.5 mo – alternative for unfit)\n"
        "Start adjuvant chemotherapy within 12 weeks of surgery\n\n"
        f"4 Adjuvant Radiotherapy\n{adjuvant_rt_note}\n"
        "5 Rationale\n"
        "PRODIGE-24/ACCORD: mFOLFIRINOX new adjuvant gold standard after R0 resection\n"
        "CONKO-001: adjuvant gemcitabine improves DFS and OS vs observation\n"
        "ESPAC-1: adjuvant chemo preferred over CRT alone\n\n"
        "6 Follow-up\nCA 19-9 every 3 months × 2 years; CT abdomen/pelvis every 3–6 months"
    )
    out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
    return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                    flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# COLON ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _colon(inp: GIInput) -> GIResult:
    flags   = []
    t       = (inp.colon_t_stage or "").upper()
    n       = (inp.colon_n_stage or "N0").upper()
    m       = (inp.colon_m_stage or "M0").upper()
    stage   = (inp.colon_overall_stage or "").upper()
    hrf     = inp.high_risk_features
    msi     = (inp.microsatellite_instability or "unknown").lower()
    kras    = (inp.kras_status or "unknown").lower()
    is_met  = ("M1" in m or "IV" in stage)

    # ── Metastatic ──────────────────────────────────────────────────────
    if is_met:
        flags.append("Metastatic colon cancer – assess resectability; molecular testing essential")
        kras_note = (
            "KRAS wild-type: Cetuximab or Panitumumab + FOLFIRI/FOLFOX (anti-EGFR; left-sided tumours)"
            if kras == "wild-type"
            else "KRAS/RAS mutant: Bevacizumab + FOLFOX/FOLFIRI or CAPOX + Bevacizumab"
            if kras == "mutant"
            else "RAS/KRAS/BRAF testing essential to guide targeted therapy"
        )
        msi_note = "\nMSI-H / dMMR: Pembrolizumab first-line (KEYNOTE-177: superior PFS vs chemo)" if msi == "msi-h" else ""
        out = (
            "1 Stage\nStage IVA/IVB/IVC – Metastatic colon cancer\n\n"
            "2 Primary Treatment\nSystemic chemotherapy ± targeted therapy\n\n"
            f"3 Regimen\n{kras_note}{msi_note}\n"
            "FOLFOXIRI + Bevacizumab for fit patients with multiple/bilobar liver mets (TRIBE trial)\n\n"
            "4 Surgical Consideration\nResection of isolated liver or lung mets in selected patients (curative intent)\n"
            "Ablation (RFA/MWA) for small unresectable hepatic lesions\n\n"
            "5 Rationale\nMolecular testing (RAS/RAF/MSI) mandatory before first-line therapy\n"
            "Left vs right-sided tumour biology affects anti-EGFR benefit\n\n"
            "6 Follow-up\nCEA every 3 months; CT every 2–3 cycles"
        )
        out += _footer(Confidence.AMBER, flags, True, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.AMBER,
                        flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)

    # ── Stage I ─────────────────────────────────────────────────────────
    if stage in ("I","1") or (t in ("T1","T2") and n == "N0"):
        msi_note = "\nNote: MSI-H is a favourable prognostic factor; adjuvant chemo not beneficial in MSI-H Stage II" if msi == "msi-h" else ""
        out = (
            "1 Stage\nStage I – Early colon cancer (T1–T2 N0 M0)\n\n"
            "2 Primary Treatment\nOncologic colectomy with lymph node dissection (≥12 LN required)\n\n"
            "3 Adjuvant Therapy\nNot indicated for Stage I (T1–T2 N0)\n"
            f"{msi_note}\n\n"
            "4 Rationale\nExcellent prognosis with surgery alone; no proven benefit from adjuvant chemo\n\n"
            "5 Follow-up\nCEA every 6 months × 3 years; colonoscopy 1 year post-op; CT abdomen/pelvis annually"
        )
        out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # ── Stage II ─────────────────────────────────────────────────────────
    if n == "N0" and not ("IV" in stage):
        msi_note = "MSI-H Stage II: adjuvant chemotherapy NOT beneficial (potential harm); observation preferred" if msi == "msi-h" else ""
        if hrf:
            flags.append("High-risk Stage II (T4, <12 LN, LVSI, perforation/obstruction) – adjuvant chemo indicated")
            out = (
                "1 Stage\nStage II – High-risk colon cancer\n\n"
                "2 Primary Treatment\nOncologic colectomy with LN dissection\n\n"
                "3 Adjuvant Therapy\nHigh-risk Stage II: FOLFOX × 6 months or CAPOX × 3 months\n"
                f"{msi_note}\n"
                "Risk features: T4, <12 nodes, LVSI, obstruction/perforation, grade 3, R1\n\n"
                "4 Rationale\nHigh-risk Stage II has ~25% recurrence risk; chemo reduces recurrence\n"
                "MSI-H does not benefit from 5-FU based adjuvant chemotherapy\n\n"
                "5 Follow-up\nCEA every 3 months × 2 years; CT abdomen/pelvis annually"
            )
        else:
            out = (
                "1 Stage\nStage II – Low-risk colon cancer\n\n"
                "2 Primary Treatment\nOncologic colectomy with LN dissection (≥12 LN)\n\n"
                "3 Adjuvant Therapy\nObservation (standard for low-risk Stage II)\n"
                "Consider adjuvant chemo if patient preference and high anxiety about recurrence\n"
                f"{msi_note}\n\n"
                "4 Rationale\nMOSAIC trial: FOLFOX adds modest benefit in Stage II but not routinely recommended\n"
                "MSI-H Stage II: excellent prognosis without chemo\n\n"
                "5 Follow-up\nCEA every 6 months × 3 years; CT annually; colonoscopy 1 year"
            )
        out += _footer(Confidence.GREEN, flags, bool(flags), PROTOCOL_VERSION)
        return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                        flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)

    # ── Stage III ─────────────────────────────────────────────────────────
    n2_high = ("N2" in n)
    t4_present = t in ("T4A","T4B")
    chemo = COLON_ADJUVANT_CHEMO_HIGH if (n2_high or t4_present or hrf) else COLON_ADJUVANT_CHEMO_LOW

    out = (
        "1 Stage\n"
        f"Stage III – Node-positive colon cancer ({t} {n} M0)\n\n"
        "2 Primary Treatment\nOncologic colectomy with LN dissection (≥12 LN)\n\n"
        f"3 Adjuvant Chemotherapy\n{chemo}\n"
        "KRAS/NRAS/BRAF/MSI testing recommended for prognostic stratification\n\n"
        "4 Rationale\nMOSAIC trial: FOLFOX improves 5-yr OS vs 5-FU in Stage III\n"
        "XELOXA trial: CAPOX equivalent to FOLFOX; preferred for convenience\n"
        "Duration optimisation (IDEA): 3-month CAPOX sufficient for low-risk T1-3N1\n\n"
        "5 Follow-up\nCEA every 3 months × 2 years, then 6 monthly × 5 years\n"
        "CT abdomen/pelvis yearly; colonoscopy 1 year post-op"
    )
    out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
    return GIResult(formatted_output=out, confidence=Confidence.GREEN,
                    flags=flags, mdt_required=False, protocol_reference=PROTOCOL_VERSION)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_gi_case(inp: GIInput) -> GIResult:
    """Route to site-specific engine based on primary_site."""
    if inp.ecog >= 3:
        return _poor_ps(inp.primary_site.value)

    site = inp.primary_site.value
    if site == "esophagus":   return _esophagus(inp)
    if site == "stomach":     return _stomach(inp)
    if site == "rectum":      return _rectum(inp)
    if site == "anal_canal":  return _anal_canal(inp)
    if site == "pancreas":    return _pancreas(inp)
    if site == "colon":       return _colon(inp)

    flags = ["Primary site not recognised – MDT required"]
    out = (
        f"1 Primary Site\n{site}\n\n"
        "2 Recommendation\nMDT discussion required – site not in standard decision tree\n"
    )
    out += _footer(Confidence.RED, flags, True, PROTOCOL_VERSION)
    return GIResult(formatted_output=out, confidence=Confidence.RED,
                    flags=flags, mdt_required=True, protocol_reference=PROTOCOL_VERSION)
