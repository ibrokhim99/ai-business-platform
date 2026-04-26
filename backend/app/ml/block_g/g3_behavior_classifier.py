from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_g import BehaviorClassifierIn, BehaviorClassifierOut

# MCC → consumer type mix and marketing insight
_MCC_PROFILES: dict[str, dict] = {
    "5812": {
        "types": [
            {"type": "morning_coffee_crowd", "share_pct": 25, "peak_hours": [7, 8, 9],
             "avg_spend": 6, "description": "Quick pre-work coffee and pastry grab"},
            {"type": "lunch_regular",         "share_pct": 35, "peak_hours": [12, 13, 14],
             "avg_spend": 18, "description": "Office workers seeking lunch nearby"},
            {"type": "evening_diner",         "share_pct": 28, "peak_hours": [18, 19, 20],
             "avg_spend": 35, "description": "Leisure evening dining, quality-focused"},
            {"type": "weekend_family",        "share_pct": 12, "peak_hours": [11, 12, 13],
             "avg_spend": 42, "description": "Weekend family outings with higher spend"},
        ],
        "dominant": "lunch_regular",
        "insight": "Focus on quick-service lunch formats and loyalty programs. "
                   "Evening premium dining is a strong secondary revenue driver.",
    },
    "5411": {
        "types": [
            {"type": "morning_shopper",  "share_pct": 30, "peak_hours": [8, 9, 10],
             "avg_spend": 25, "description": "Daily fresh produce and essentials purchase"},
            {"type": "evening_grocer",   "share_pct": 40, "peak_hours": [17, 18, 19],
             "avg_spend": 38, "description": "After-work bulk grocery run"},
            {"type": "bargain_hunter",   "share_pct": 20, "peak_hours": [11, 15, 16],
             "avg_spend": 15, "description": "Price-sensitive, seeks promotions"},
            {"type": "weekend_family",   "share_pct": 10, "peak_hours": [10, 11, 12],
             "avg_spend": 65, "description": "Large weekly family stock-up"},
        ],
        "dominant": "evening_grocer",
        "insight": "Stock promotions and bundles for evening shoppers. "
                   "Weekend large-basket purchases drive the highest revenue per transaction.",
    },
    "5912": {
        "types": [
            {"type": "prescription_patient",  "share_pct": 45, "peak_hours": [9, 10, 11, 14, 15],
             "avg_spend": 22, "description": "Regular prescription pickups"},
            {"type": "wellness_seeker",       "share_pct": 30, "peak_hours": [10, 11, 17],
             "avg_spend": 35, "description": "OTC vitamins and wellness products"},
            {"type": "emergency_buyer",       "share_pct": 25, "peak_hours": [8, 20, 21],
             "avg_spend": 18, "description": "Urgent medication needs, time-sensitive"},
        ],
        "dominant": "prescription_patient",
        "insight": "Convenience and fast service are key. "
                   "Wellness product cross-sell offers strong upsell potential.",
    },
    "7011": {
        "types": [
            {"type": "business_traveller",  "share_pct": 40, "peak_hours": [7, 8, 18, 19],
             "avg_spend": 120, "description": "Corporate stays, expense-account driven"},
            {"type": "leisure_tourist",     "share_pct": 35, "peak_hours": [10, 14, 20],
             "avg_spend": 85, "description": "Sightseeing tourists with flexible schedule"},
            {"type": "event_attendee",      "share_pct": 25, "peak_hours": [16, 17, 21],
             "avg_spend": 95, "description": "Conference or event-driven stays"},
        ],
        "dominant": "business_traveller",
        "insight": "Corporate accounts and booking platform presence are critical. "
                   "Weekend leisure packages can fill occupancy gaps.",
    },
}

_DEFAULT_PROFILE = {
    "types": [
        {"type": "morning_commuter", "share_pct": 22, "peak_hours": [7, 8, 9],
         "avg_spend": 8, "description": "Quick grab-and-go, pre-work"},
        {"type": "lunch_regular",    "share_pct": 30, "peak_hours": [12, 13, 14],
         "avg_spend": 15, "description": "Work-hour lunch visits"},
        {"type": "premium_leisure",  "share_pct": 18, "peak_hours": [18, 19, 20],
         "avg_spend": 45, "description": "Evening leisure, quality-focused"},
        {"type": "bargain_hunter",   "share_pct": 20, "peak_hours": [10, 11, 16],
         "avg_spend": 9,  "description": "Discount-driven, price-sensitive"},
        {"type": "weekend_family",   "share_pct": 10, "peak_hours": [11, 12, 13],
         "avg_spend": 35, "description": "Weekend family outings"},
    ],
    "dominant": "lunch_regular",
    "insight": "Mixed consumer base — invest in broad-range promotions and multi-daypart service.",
}


@register_model("M-G3")
class BehaviorClassifierModel(BaseMLModel[BehaviorClassifierIn, BehaviorClassifierOut]):
    metadata = ModelMetadata(
        model_id="M-G3", block="G",
        name="Consumer Behavior Classifier",
        version="1.0.0",
        algorithm="MCC-based rule classifier with time-pattern profiling",
        is_stub=False,
        feature_names=["lat", "lon", "radius_m", "mcc_code"],
        supported_explainers=["rule_based"],
        description="Consumer types: morning crowd, premium, bargain hunter, etc.",
    )

    def predict(self, input_data: BehaviorClassifierIn) -> BehaviorClassifierOut:
        profile = _MCC_PROFILES.get(input_data.mcc_code, _DEFAULT_PROFILE)
        return BehaviorClassifierOut(
            consumer_types=profile["types"],
            dominant_type=profile["dominant"],
            marketing_insight=profile["insight"],
        )

    def explain(self, input_data: BehaviorClassifierIn) -> dict:
        return {
            "transaction_timing": 0.40,
            "spend_pattern": 0.35,
            "mcc_sequence": 0.25,
        }
