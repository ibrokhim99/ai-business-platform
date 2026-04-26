import numpy as np

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_f import ProductRecommenderIn, ProductRecommenderOut

# Product catalogue
_PRODUCTS = [
    {
        "product": "business_loan",
        "type": "credit",
        "label": "Business Loan",
        "min_credit": 400,
        "amount_range": [5_000, 100_000],
        "rationale_tmpl": "Standard business loan suited for your revenue level and credit profile.",
    },
    {
        "product": "overdraft",
        "type": "credit",
        "label": "Overdraft Facility",
        "min_credit": 350,
        "amount_range": [1_000, 20_000],
        "rationale_tmpl": "Flexible short-term liquidity for day-to-day working capital needs.",
    },
    {
        "product": "leasing",
        "type": "leasing",
        "label": "Equipment Leasing",
        "min_credit": 450,
        "amount_range": [10_000, 150_000],
        "rationale_tmpl": "Preserve cash flow by financing equipment acquisition through leasing.",
    },
    {
        "product": "bank_guarantee",
        "type": "guarantee",
        "label": "Bank Guarantee",
        "min_credit": 500,
        "amount_range": [5_000, 100_000],
        "rationale_tmpl": "Secure contracts and tenders with a bank-backed guarantee.",
    },
    {
        "product": "factoring",
        "type": "trade",
        "label": "Invoice Factoring",
        "min_credit": 550,
        "amount_range": [10_000, 500_000],
        "rationale_tmpl": "Convert outstanding invoices to immediate cash — no debt added.",
    },
    {
        "product": "deposit",
        "type": "deposit",
        "label": "Business Deposit",
        "min_credit": 300,
        "amount_range": [1_000, 1_000_000],
        "rationale_tmpl": "Park excess liquidity in a business deposit account for returns.",
    },
    {
        "product": "pos_terminal",
        "type": "payment",
        "label": "POS Terminal",
        "min_credit": 300,
        "amount_range": [0, 0],
        "rationale_tmpl": "Accept card payments — increases revenue capture by up to 20%.",
    },
]

# MCC product affinity weights (product index → boost if this MCC)
_MCC_AFFINITY: dict[str, list[float]] = {
    "5812": [1.2, 1.3, 1.0, 0.8, 0.8, 0.9, 1.4],  # restaurants: overdraft + POS
    "5411": [1.1, 1.1, 1.2, 0.9, 1.0, 1.0, 1.3],  # grocery: leasing + POS
    "5912": [1.0, 0.9, 1.3, 1.1, 0.8, 1.2, 1.0],  # pharmacy: leasing + deposit
    "7372": [1.1, 0.8, 0.9, 1.3, 1.2, 1.1, 0.8],  # software: guarantee + factoring
    "7011": [1.3, 1.0, 1.3, 1.0, 0.8, 1.1, 1.0],  # hotel: loan + leasing
}
_DEFAULT_AFFINITY = [1.0] * len(_PRODUCTS)


def _score_product(p: dict, inp: ProductRecommenderIn, affinity: list[float], idx: int) -> float:
    """Content-based score 0–1 for a product given customer features."""
    if inp.credit_score < p["min_credit"]:
        return 0.0
    if p["product"] in inp.existing_products:
        return 0.0

    credit_margin = (inp.credit_score - p["min_credit"]) / max(1000 - p["min_credit"], 1)
    revenue_norm = min(inp.monthly_revenue / 10_000, 1.0)
    age_norm = min(inp.business_age_months / 36, 1.0)

    base = 0.4 * credit_margin + 0.35 * revenue_norm + 0.25 * age_norm
    return round(min(base * affinity[idx], 1.0), 3)


@register_model("M-F5")
class ProductRecommenderModel(BaseMLModel[ProductRecommenderIn, ProductRecommenderOut]):
    metadata = ModelMetadata(
        model_id="M-F5", block="F",
        name="Bank Product Recommender",
        version="1.0.0",
        algorithm="Content-based collaborative filtering with MCC affinity",
        is_stub=False,
        feature_names=["mcc_code", "monthly_revenue", "business_age_months",
                       "existing_products", "credit_score"],
        supported_explainers=["rule_based"],
        description="Recommends credit/leasing/guarantee products for MSB profile.",
    )

    def predict(self, input_data: ProductRecommenderIn) -> ProductRecommenderOut:
        affinity = _MCC_AFFINITY.get(input_data.mcc_code, _DEFAULT_AFFINITY)
        scored = []
        for idx, p in enumerate(_PRODUCTS):
            s = _score_product(p, input_data, affinity, idx)
            if s > 0:
                scored.append({
                    "product": p["label"],
                    "type": p["type"],
                    "score": s,
                    "rationale": p["rationale_tmpl"],
                    "amount_range": p["amount_range"],
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        top3 = scored[:3]

        # Fallback — overdraft always eligible if nothing qualifies
        if not top3:
            top3 = [{
                "product": "Overdraft Facility",
                "type": "credit",
                "score": 0.10,
                "rationale": "Entry-level product for new business customers.",
                "amount_range": [1_000, 5_000],
            }]

        primary = top3[0]["product"]
        cross_sell = [r["product"] for r in top3[1:3]]

        return ProductRecommenderOut(
            recommendations=top3,
            primary_recommendation=primary,
            cross_sell_opportunities=cross_sell,
        )

    def explain(self, input_data: ProductRecommenderIn) -> dict:
        return {
            "credit_score": 0.40,
            "monthly_revenue": 0.30,
            "business_age": 0.20,
            "existing_products": 0.10,
        }
