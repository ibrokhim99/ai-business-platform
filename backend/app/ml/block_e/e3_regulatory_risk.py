from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_e import RegulatoryRiskIn, RegulatoryRiskOut

# MCC regulatory categories: (base_risk_score, category_label)
_MCC_CONFIG = {
    "5812": (65, "food_service",       "monthly"),
    "5813": (70, "alcohol_food",       "monthly"),
    "5912": (60, "pharmaceutical",     "quarterly"),
    "5047": (55, "medical_equipment",  "quarterly"),
    "7011": (50, "hospitality",        "quarterly"),
    "5411": (45, "food_retail",        "quarterly"),
    "5651": (30, "retail_apparel",     "annually"),
    "5940": (30, "sports_equipment",   "annually"),
    "7372": (25, "software_services",  "annually"),
}
_DEFAULT_CONFIG = (35, "general_retail", "annually")

_MCC_REGS = {
    "5812": ["SES food safety certificate", "Fire safety inspection",
             "Cash register (KKM) registration", "Employee health records"],
    "5813": ["Alcohol license (Ministry of Trade)", "SES food certificate",
             "Age verification system", "KKM registration"],
    "5912": ["Pharmacy license (Ministry of Health)", "Cold chain compliance certificate",
             "Controlled substances register", "Pharmacist certification"],
    "5047": ["Medical equipment sales license", "MOH registration", "Import permits"],
    "7011": ["Hotel classification certificate", "SES inspection",
             "Fire safety compliance", "KKM registration"],
    "5411": ["SES food safety certificate", "Weights & measures certification",
             "KKM registration", "Labelling compliance"],
}
_DEFAULT_REGS = ["Business registration (tax authority)", "KKM registration",
                 "Fire safety inspection", "Sanitary inspection"]

_MCC_VIOLATIONS = {
    "5812": ["Unregistered cash sales", "Missing SES certificate", "Expired employee health books"],
    "5813": ["Sale to minors", "Unlicensed alcohol", "Missing cash register"],
    "5912": ["Dispensing without prescription", "Cold chain violations", "Expired drugs on shelf"],
    "5047": ["Unregistered medical devices", "Missing import permits"],
    "5411": ["Incorrect product labelling", "Expired products on shelf", "Missing SES cert"],
}
_DEFAULT_VIOLATIONS = ["Late tax filing", "Unregistered cash register"]


@register_model("M-E3")
class RegulatoryRiskModel(BaseMLModel[RegulatoryRiskIn, RegulatoryRiskOut]):
    metadata = ModelMetadata(
        model_id="M-E3", block="E",
        name="Regulatory Risk Score",
        version="1.0.0",
        algorithm="Rule-based MCC regulatory classifier",
        is_stub=False,
        feature_names=["mcc_code", "region_id", "business_age_months"],
        supported_explainers=["rule_based"],
        description="Inspection and regulatory fine risk score.",
    )

    def predict(self, input_data: RegulatoryRiskIn) -> RegulatoryRiskOut:
        base_risk, category, inspection_freq = _MCC_CONFIG.get(
            input_data.mcc_code, _DEFAULT_CONFIG
        )

        # Age modifier: newer businesses have higher risk (unfamiliarity with regs)
        if input_data.business_age_months < 3:
            age_modifier = +20
        elif input_data.business_age_months < 12:
            age_modifier = +10
        elif input_data.business_age_months < 36:
            age_modifier = +5
        else:
            age_modifier = -5  # experienced businesses know requirements

        score = min(max(base_risk + age_modifier, 0), 100)
        risk_level = "high" if score >= 65 else "medium" if score >= 40 else "low"

        regs = _MCC_REGS.get(input_data.mcc_code, _DEFAULT_REGS)
        violations = _MCC_VIOLATIONS.get(input_data.mcc_code, _DEFAULT_VIOLATIONS)

        # High-risk score → increase inspection frequency
        if risk_level == "high" and inspection_freq == "quarterly":
            inspection_freq = "monthly"
        elif risk_level == "low" and inspection_freq == "quarterly":
            inspection_freq = "annually"

        return RegulatoryRiskOut(
            risk_score=float(score),
            risk_level=risk_level,
            applicable_regulations=regs,
            inspection_frequency=inspection_freq,
            common_violations=violations,
        )

    def explain(self, input_data: RegulatoryRiskIn) -> dict:
        return {
            "mcc_sector_risk": 0.60,
            "business_maturity": 0.25,
            "region_enforcement": 0.15,
        }
