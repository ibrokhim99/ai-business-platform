"""ReportService — orchestrates multi-model composite reports."""
from __future__ import annotations

import asyncio

from app.services.prediction_service import PredictionService
from app.schemas.block_d import ViabilityCheckIn, CashFlowSimIn
from app.schemas.block_e import ChurnPredictionIn
from app.schemas.block_f import CreditRiskIn, LoanSizingIn, DTIPredictorIn


class ReportService:
    def __init__(self, prediction_service: PredictionService):
        self._ps = prediction_service

    async def business_viability_report(self, payload: dict, request_id: str) -> dict:
        """Aggregates M-D1 + M-D5 + M-E2 + M-F1."""
        tasks = {
            "viability": self._ps.predict("M-D1", ViabilityCheckIn(**payload), request_id=request_id),
            "cashflow": self._ps.predict("M-D5", CashFlowSimIn(**payload), request_id=request_id),
            "churn": self._ps.predict("M-E2", ChurnPredictionIn(**payload), request_id=request_id),
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return {
            key: (r.model_dump() if not isinstance(r, Exception) else {"error": str(r)})
            for key, r in zip(tasks.keys(), results)
        }

    async def credit_decision_report(self, payload: dict, request_id: str) -> dict:
        """Aggregates M-F1 + M-F2 + M-F3."""
        tasks = {
            "credit_risk": self._ps.predict("M-F1", CreditRiskIn(**payload), request_id=request_id),
            "loan_sizing": self._ps.predict("M-F2", LoanSizingIn(**payload), request_id=request_id),
            "dti": self._ps.predict("M-F3", DTIPredictorIn(**payload), request_id=request_id),
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        return {
            key: (r.model_dump() if not isinstance(r, Exception) else {"error": str(r)})
            for key, r in zip(tasks.keys(), results)
        }
