"""
Production-Ready Cervix Cancer Decision Engine
"""

from .models import CervixInput, CervixResult, Confidence
from .config import (
    PROTOCOL_VERSION,
    CISPLATIN_MIN_CRCL,
    LOCALLY_ADVANCED_STAGES,
    EARLY_STAGES,
)


def _footer(confidence: Confidence, flags: list, mdt_required: bool, protocol: str) -> str:
    flag_str = ", ".join(flags) if flags else "None"
    return (
        f"\nConfidence → {confidence.value}\n"
        f"Flags → {flag_str}\n"
        f"MDT Required → {mdt_required}\n"
        f"Protocol Reference → {protocol}"
    )


def evaluate_cervix_case(input_data: CervixInput) -> CervixResult:

    flags = []
    confidence = Confidence.GREEN
    mdt_required = False
    stage = input_data.figo_stage.value

    # ------------------------------------------------
    # STEP 1 — Poor Performance Status (ECOG > 2)
    # ------------------------------------------------
    if input_data.ecog > 2:
        out = (
            f"1 Disease Category\n"
            f"Carcinoma cervix – poor performance status\n\n"
            f"2 FIGO Stage\n"
            f"{stage}\n\n"
            f"3 Risk Stratification\n"
            f"ECOG {input_data.ecog} → unfit for standard protocol\n\n"
            f"4 Primary Treatment\n"
            f"MDT discussion required\n\n"
            f"5 Radiotherapy\n"
            f"Individualised based on tolerance\n\n"
            f"6 Chemotherapy\n"
            f"Individualised or omitted\n\n"
            f"7 Brachytherapy\n"
            f"Individualised\n\n"
            f"8 Rationale\n"
            f"Poor performance status requires individualised planning\n\n"
            f"9 Follow-up\n"
            f"As per MDT"
        )
        out += _footer(Confidence.RED, ["Poor performance status"], True, PROTOCOL_VERSION)
        return CervixResult(
            formatted_output=out,
            confidence=Confidence.RED,
            flags=["Poor performance status"],
            mdt_required=True,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ------------------------------------------------
    # STEP 2 — Post-CRT Residual Disease
    # ------------------------------------------------
    if input_data.post_crt_residual:
        out = (
            "1 Disease Status\n"
            "Residual carcinoma cervix\n\n"
            "2 Evaluation\n"
            "Biopsy-proven residual\n"
            "Rule out distant metastasis\n\n"
            "3 Management Options\n"
            "• Salvage hysterectomy (central disease)\n"
            "• Pelvic exenteration (selected cases)\n\n"
            "4 Radiotherapy\n"
            "Re-irradiation only in selected centers\n\n"
            "5 Rationale\n"
            "Surgery is salvage option for localized residual disease"
        )
        out += _footer(Confidence.RED, ["Post-CRT residual disease – urgent MDT required"], True, PROTOCOL_VERSION)
        return CervixResult(
            formatted_output=out,
            confidence=Confidence.RED,
            flags=["Post-CRT residual disease – urgent MDT required"],
            mdt_required=True,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ------------------------------------------------
    # STEP 3 — Metastatic (IVB / distant metastasis)
    # ------------------------------------------------
    if stage == "IVB" or input_data.distant_metastasis:
        out = (
            "1 Disease Category\n"
            "Metastatic carcinoma cervix\n\n"
            "2 Treatment Intent\n"
            "Palliative\n\n"
            "3 Systemic Therapy\n"
            "Platinum-based chemotherapy ± bevacizumab\n\n"
            "4 Role of Radiotherapy\n"
            "Palliative RT for bleeding / pain\n\n"
            "5 Treatment Goal\n"
            "Symptom control\n"
            "Quality of life\n\n"
            "6 Follow-up\n"
            "Response-based, symptom-oriented"
        )
        out += _footer(Confidence.AMBER, ["Metastatic disease"], True, PROTOCOL_VERSION)
        return CervixResult(
            formatted_output=out,
            confidence=Confidence.AMBER,
            flags=["Metastatic disease"],
            mdt_required=True,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ------------------------------------------------
    # STEP 4 — Bulky Early Stage (IB3)
    # ------------------------------------------------
    if stage == "IB3":
        chemo = "Weekly cisplatin 40 mg/m² × 5–6 cycles"
        if input_data.creatinine_clearance < CISPLATIN_MIN_CRCL:
            chemo = "Cisplatin contraindicated – consider carboplatin AUC 2 or alternative\nMDT discussion required"
            confidence = Confidence.AMBER
            mdt_required = True
            flags.append("Renal impairment – cisplatin contraindicated")

        out = (
            f"1 Disease Category\n"
            f"Bulky early-stage cervix\n\n"
            f"2 FIGO Stage\n"
            f"{stage}\n\n"
            f"3 Risk Stratification\n"
            f"Tumor >4 cm\n"
            f"High risk for adjuvant therapy post surgery\n\n"
            f"4 Primary Treatment\n"
            f"Definitive concurrent chemoradiation\n\n"
            f"5 Radiotherapy\n"
            f"EBRT pelvis 50 Gy / 25#\n"
            f"Followed by ICBT\n\n"
            f"6 Brachytherapy\n"
            f"HDR ICBT\n"
            f"Dose EQD2 ≥ 80–85 Gy to HR-CTV\n\n"
            f"7 Chemotherapy\n"
            f"{chemo}\n\n"
            f"8 Rationale\n"
            f"Avoids tri-modality treatment morbidity\n\n"
            f"9 Follow-up\n"
            f"Clinical exam + imaging at 3 months"
        )
        out += _footer(confidence, flags, mdt_required, PROTOCOL_VERSION)
        return CervixResult(
            formatted_output=out,
            confidence=confidence,
            flags=flags,
            mdt_required=mdt_required,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ------------------------------------------------
    # STEP 5 — Node-positive with Para-aortic (IIIC2)
    # ------------------------------------------------
    if input_data.para_aortic_nodes_positive:
        chemo = "Weekly cisplatin\nConsider dose modification if toxicity"
        if input_data.creatinine_clearance < CISPLATIN_MIN_CRCL:
            chemo = "Cisplatin contraindicated – consider carboplatin AUC 2\nMDT discussion required"
            confidence = Confidence.AMBER
            flags.append("Renal impairment – cisplatin contraindicated")

        flags.append("Para-aortic nodal disease – extended field RT required")
        mdt_required = True

        out = (
            f"1 Disease Category\n"
            f"Locally advanced, node-positive cervix\n\n"
            f"2 FIGO Stage\n"
            f"{stage}\n\n"
            f"3 Risk Stratification\n"
            f"Para-aortic nodal disease → Very high risk\n\n"
            f"4 Primary Treatment\n"
            f"Extended-field concurrent chemoradiation\n\n"
            f"5 Radiotherapy\n"
            f"Pelvis + para-aortic nodes\n"
            f"50 Gy / 25# to pelvis + 45Gy to para aortic node, + boost to gross nodes upto 56 to 60Gy\n"
            f"IMRT/VMAT  mandatory\n\n"
            f"6 Chemotherapy\n"
            f"{chemo}\n\n"
            f"7 Brachytherapy\n"
            f"Essential\n"
            f"Hybrid / interstitial if needed\n\n"
            f"8 Treatment Goal\n"
            f"Curative intent\n\n"
            f"9 Rationale\n"
            f"Nodal disease controlled with EFRT + chemo\n\n"
            f"10 Follow-up\n"
            f"PET-CT at 3–6 months"
        )
        out += _footer(confidence, flags, mdt_required, PROTOCOL_VERSION)
        return CervixResult(
            formatted_output=out,
            confidence=confidence,
            flags=flags,
            mdt_required=mdt_required,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ------------------------------------------------
    # STEP 6 — Locally Advanced (IIB–IVA, no para-aortic)
    # ------------------------------------------------
    if stage in LOCALLY_ADVANCED_STAGES:
        chemo = "Weekly cisplatin 40 mg/m²"
        if input_data.creatinine_clearance < CISPLATIN_MIN_CRCL:
            chemo = "Cisplatin contraindicated – consider carboplatin AUC 2\nMDT discussion required"
            confidence = Confidence.AMBER
            mdt_required = True
            flags.append("Renal impairment – cisplatin contraindicated")

        # Elderly / frail — Case 5 format: NO FIGO Stage field
        if input_data.age >= 70 and input_data.ecog >= 1:
            out = (
                "1 Disease Category\n"
                "Locally advanced cervix – elderly\n\n"
                "2 Risk Stratification\n"
                "Age + comorbidities → limited tolerance\n\n"
                "3 Primary Treatment\n"
                "Definitive radiotherapy\n\n"
                "4 Chemotherapy\n"
                "May be omitted or weekly cisplatin with caution OR weekly carboplatin\n\n"
                "5 Radiotherapy\n"
                "Pelvic EBRT + brachytherapy\n\n"
                "6 Brachytherapy\n"
                "Essential for local control\n\n"
                "7 Rationale\n"
                "RT alone acceptable when chemo contraindicated\n\n"
                "8 Follow-up\n"
                "Symptom-based\n"
                "Avoid aggressive investigations"
            )
            out += _footer(Confidence.AMBER, flags, mdt_required, PROTOCOL_VERSION)
            return CervixResult(
                formatted_output=out,
                confidence=Confidence.AMBER,
                flags=flags,
                mdt_required=mdt_required,
                protocol_reference=PROTOCOL_VERSION,
            )

        risk_detail = (
            "Parametrial involvement\nPelvic nodal disease → High risk"
            if input_data.pelvic_nodes_positive
            else "Parametrial involvement or advanced stage → High risk"
        )

        out = (
            f"1 Disease Category\n"
            f"Locally advanced carcinoma cervix\n\n"
            f"2 FIGO Stage\n"
            f"{stage}\n\n"
            f"3 Risk Stratification\n"
            f"{risk_detail}\n\n"
            f"4 Primary Treatment\n"
            f"Definitive concurrent chemoradiation\n\n"
            f"5 External Beam RT\n"
            f"Pelvis ± nodes\n"
            f"50 Gy / 25#\n\n"
            f"6 Chemotherapy\n"
            f"{chemo}\n\n"
            f"7 Brachytherapy\n"
            f"Mandatory\n"
            f"ICBT / Hybrid brachytherapy\n"
            f"HR-CTV EQD2 ≥ 85 Gy\n\n"
            f"8 Technique Considerations\n"
            f"IMRT preferred\n"
            f"IGRT for bladder/rectum sparing\n\n"
            f"9 Rationale\n"
            f"CRT + brachytherapy is curative standard\n\n"
            f"10 Follow-up\n"
            f"Response assessment at 3 months post RT"
        )
        out += _footer(confidence, flags, mdt_required, PROTOCOL_VERSION)
        return CervixResult(
            formatted_output=out,
            confidence=confidence,
            flags=flags,
            mdt_required=mdt_required,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ------------------------------------------------
    # STEP 7 — Early Stage (IA1–IB2)
    # ------------------------------------------------
    if stage in EARLY_STAGES and input_data.tumor_size_cm <= 4:

        # Pre-surgery
        if not input_data.prior_surgery:
            out = (
                f"1 Disease Category\n"
                f"Early-stage carcinoma cervix\n\n"
                f"2 FIGO Stage\n"
                f"{stage}\n\n"
                f"3 Risk Stratification\n"
                f"Tumor <4 cm\n"
                f"No parametrial involvement\n"
                f"Node-negative → Low–intermediate risk\n\n"
                f"4 Primary Treatment\n"
                f"Radical hysterectomy (Type C1) + pelvic lymph node dissection\n\n"
                f"5 Adjuvant Therapy\n"
                f"Based on final histopathology\n"
                f"• Sedlis factors → Adjuvant RT\n"
                f"• High-risk factors [positive nodes, positive parametrium, positive margins] → Concurrent chemoradiation\n\n"
                f"6 Radiotherapy (if indicated)\n"
                f"Pelvic EBRT 50 Gy / 25#\n"
                f"± Vaginal vault brachytherapy 6Gy/#/2#\n\n"
                f"7 Chemotherapy\n"
                f"Not upfront\n"
                f"Cisplatin only if high-risk factors present\n\n"
                f"8 Guideline Rationale\n"
                f"Surgery preferred for operable early-stage disease\n\n"
                f"9 Follow-up\n"
                f"3–6 monthly for 2 years\n"
                f"6–12 monthly thereafter"
            )
            out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
            return CervixResult(
                formatted_output=out,
                confidence=Confidence.GREEN,
                flags=flags,
                mdt_required=False,
                protocol_reference=PROTOCOL_VERSION,
            )

        # Post-surgery — Low risk
        if not any([
            input_data.margins_positive,
            input_data.pelvic_nodes_positive,
            input_data.lvsi_present,
            input_data.parametrial_invasion,
        ]):
            out = (
                f"1 Disease Category\n"
                f"Early-stage carcinoma cervix – post-surgery\n\n"
                f"2 FIGO Stage\n"
                f"{stage}\n\n"
                f"3 Risk Stratification\n"
                f"No adverse pathological factors → Low risk\n\n"
                f"4 Primary Treatment\n"
                f"Observation\n\n"
                f"5 Adjuvant Therapy\n"
                f"Not indicated\n\n"
                f"6 Radiotherapy\n"
                f"Not indicated\n\n"
                f"7 Chemotherapy\n"
                f"Not indicated\n\n"
                f"8 Rationale\n"
                f"No Sedlis or high-risk features\n\n"
                f"9 Follow-up\n"
                f"3–6 monthly for 2 years\n"
                f"6–12 monthly thereafter"
            )
            out += _footer(Confidence.GREEN, flags, False, PROTOCOL_VERSION)
            return CervixResult(
                formatted_output=out,
                confidence=Confidence.GREEN,
                flags=flags,
                mdt_required=False,
                protocol_reference=PROTOCOL_VERSION,
            )

        # Post-surgery — High risk
        if (
            input_data.margins_positive
            or input_data.pelvic_nodes_positive
            or input_data.parametrial_invasion
        ):
            chemo = "Weekly cisplatin 40 mg/m²"
            if input_data.creatinine_clearance < CISPLATIN_MIN_CRCL:
                chemo = "Cisplatin contraindicated – consider alternative\nMDT discussion required"
                confidence = Confidence.AMBER
                mdt_required = True
                flags.append("Renal impairment – cisplatin contraindicated")

            risk_factors = []
            if input_data.margins_positive:
                risk_factors.append("Positive margins")
            if input_data.pelvic_nodes_positive:
                risk_factors.append("Positive pelvic nodes")
            if input_data.parametrial_invasion:
                risk_factors.append("Parametrial invasion")

            out = (
                f"1 Disease Category\n"
                f"Early-stage carcinoma cervix – post-surgery, high risk\n\n"
                f"2 FIGO Stage\n"
                f"{stage}\n\n"
                f"3 Risk Stratification\n"
                f"High-risk pathological features\n"
                f"{chr(10).join(risk_factors)}\n\n"
                f"4 Primary Treatment\n"
                f"Postoperative concurrent chemoradiation\n\n"
                f"5 Radiotherapy\n"
                f"Pelvic EBRT 50 Gy / 25#\n\n"
                f"6 Brachytherapy\n"
                f"Vaginal vault brachytherapy if margins involved\n\n"
                f"7 Chemotherapy\n"
                f"{chemo}\n\n"
                f"8 Rationale\n"
                f"High-risk features mandate concurrent chemoradiation (Peters criteria)\n\n"
                f"9 Follow-up\n"
                f"3–6 monthly for 2 years\n"
                f"6–12 monthly thereafter"
            )
            out += _footer(confidence, flags, mdt_required, PROTOCOL_VERSION)
            return CervixResult(
                formatted_output=out,
                confidence=confidence,
                flags=flags,
                mdt_required=mdt_required,
                protocol_reference=PROTOCOL_VERSION,
            )

        # Post-surgery — Intermediate risk (Sedlis)
        if input_data.lvsi_present:
            out = (
                f"1 Disease Category\n"
                f"Early-stage carcinoma cervix – post-surgery, intermediate risk\n\n"
                f"2 FIGO Stage\n"
                f"{stage}\n\n"
                f"3 Risk Stratification\n"
                f"Sedlis criteria positive\n"
                f"LVSI present → Intermediate risk\n\n"
                f"4 Primary Treatment\n"
                f"Postoperative pelvic radiotherapy\n\n"
                f"5 Radiotherapy\n"
                f"Pelvic EBRT 50 Gy / 25#\n\n"
                f"6 Brachytherapy\n"
                f"± Vaginal vault brachytherapy 6Gy/#/2#\n\n"
                f"7 Chemotherapy\n"
                f"Not required for Sedlis criteria alone\n\n"
                f"8 Rationale\n"
                f"Sedlis factors warrant adjuvant RT (GOG 92)\n\n"
                f"9 Follow-up\n"
                f"3–6 monthly for 2 years\n"
                f"6–12 monthly thereafter"
            )
            out += _footer(Confidence.AMBER, flags, False, PROTOCOL_VERSION)
            return CervixResult(
                formatted_output=out,
                confidence=Confidence.AMBER,
                flags=flags,
                mdt_required=False,
                protocol_reference=PROTOCOL_VERSION,
            )

    # ------------------------------------------------
    # STEP 8 — Symptomatic Bleeding
    # ------------------------------------------------
    if input_data.symptomatic_bleeding:
        out = (
            f"1 Disease Category\n"
            f"Symptomatic carcinoma cervix\n\n"
            f"2 FIGO Stage\n"
            f"{stage}\n\n"
            f"3 Risk Stratification\n"
            f"Active symptomatic bleeding → Urgent palliation\n\n"
            f"4 Primary Treatment\n"
            f"Palliative pelvic radiotherapy\n\n"
            f"5 Radiotherapy\n"
            f"Short-course palliative RT\n\n"
            f"6 Chemotherapy\n"
            f"Not indicated\n\n"
            f"7 Brachytherapy\n"
            f"Not applicable\n\n"
            f"8 Rationale\n"
            f"Symptom control priority\n\n"
            f"9 Follow-up\n"
            f"As needed – symptom-based"
        )
        out += _footer(Confidence.AMBER, flags, False, PROTOCOL_VERSION)
        return CervixResult(
            formatted_output=out,
            confidence=Confidence.AMBER,
            flags=flags,
            mdt_required=False,
            protocol_reference=PROTOCOL_VERSION,
        )

    # ------------------------------------------------
    # Fallback
    # ------------------------------------------------
    out = (
        f"1 Disease Category\n"
        f"Unclassified – outside standard pathway\n\n"
        f"2 FIGO Stage\n"
        f"{stage}\n\n"
        f"3 Risk Stratification\n"
        f"Case does not fit standard decision tree\n\n"
        f"4 Primary Treatment\n"
        f"MDT discussion required\n\n"
        f"5 Rationale\n"
        f"Individualised management needed\n\n"
        f"6 Follow-up\n"
        f"As per MDT"
    )
    out += _footer(Confidence.RED, ["Outside pathway"], True, PROTOCOL_VERSION)
    return CervixResult(
        formatted_output=out,
        confidence=Confidence.RED,
        flags=["Outside pathway"],
        mdt_required=True,
        protocol_reference=PROTOCOL_VERSION,
    )
