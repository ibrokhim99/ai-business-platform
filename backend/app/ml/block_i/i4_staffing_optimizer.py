import math

from app.ml.base import BaseMLModel, ModelMetadata
from app.ml.registry import register_model
from app.schemas.block_i import StaffingOptimizerIn, StaffingOptimizerOut


@register_model("M-I4")
class StaffingOptimizerModel(BaseMLModel[StaffingOptimizerIn, StaffingOptimizerOut]):
    """
    Per-hour staffing recommendation: ceil(demand_h / units_per_staff_hour)
    bounded by min_staff_per_open_hour and max_staff. Closed hours get 0 staff.
    """

    metadata = ModelMetadata(
        model_id="M-I4", block="I",
        name="Staffing Optimizer",
        version="1.0.0",
        algorithm="Per-hour demand → ceil staff slots with min/max bounds",
        is_stub=False,
        feature_names=["hourly_demand", "units_per_staff_hour",
                       "min_staff_per_open_hour", "max_staff",
                       "open_hour", "close_hour", "hourly_wage"],
        supported_explainers=["rule_based"],
        description="Hour-by-hour staffing schedule and labor cost estimate.",
    )

    def predict(self, input_data: StaffingOptimizerIn) -> StaffingOptimizerOut:
        oh, ch = input_data.open_hour, input_data.close_hour
        # Support overnight schedules where close < open by treating wrap-around
        if oh <= ch:
            open_hours = set(range(oh, ch + 1))
        else:
            open_hours = set(range(oh, 24)) | set(range(0, ch + 1))

        hourly_staff: list[int] = []
        for h, demand in enumerate(input_data.hourly_demand):
            if h not in open_hours:
                hourly_staff.append(0)
                continue
            need = math.ceil(demand / input_data.units_per_staff_hour)
            need = max(need, input_data.min_staff_per_open_hour)
            need = min(need, input_data.max_staff)
            hourly_staff.append(int(need))

        total_hours = float(sum(hourly_staff))
        labor_cost = round(total_hours * input_data.hourly_wage, 2)

        peak_h = max(range(24), key=lambda h: hourly_staff[h])
        peak_staff = hourly_staff[peak_h]

        return StaffingOptimizerOut(
            hourly_staff=hourly_staff,
            total_staff_hours=total_hours,
            estimated_labor_cost=labor_cost,
            peak_hour=peak_h,
            peak_hour_staff=peak_staff,
        )

    def explain(self, input_data: StaffingOptimizerIn) -> dict:
        return {
            "hourly_demand": 0.60,
            "units_per_staff_hour": 0.20,
            "min_max_constraints": 0.20,
        }
