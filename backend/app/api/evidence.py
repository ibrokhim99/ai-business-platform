"""
/evidence — data transparency endpoints.

Lets the chat UI surface the synthetic dataset rows that backed a prediction
so the user can audit the answer instead of taking it on faith.
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.evidence_service import get_evidence_service

router = APIRouter(prefix="/evidence", tags=["Evidence — data transparency"])


class SimilarBusinessesIn(BaseModel):
    region_id: str | None = None
    mcc_code: str | None = None
    monthly_revenue: float | None = Field(default=None, ge=0)
    initial_investment: float | None = Field(default=None, ge=0)
    limit: int = Field(default=10, ge=1, le=50)
    # Optional: restrict per-block evidence to the blocks whose models were run.
    # Pass model_ids (e.g. ["M-A1","M-D5"]) and we'll resolve to {"A","D"}.
    model_ids: list[str] | None = None


def _blocks_from_model_ids(model_ids: list[str] | None) -> list[str] | None:
    if not model_ids:
        return None
    out: set[str] = set()
    for mid in model_ids:
        if "-" in mid and len(mid) >= 3:
            out.add(mid.split("-", 1)[1][:1].upper())
    return sorted(out) if out else None


@router.post("/similar-businesses")
async def similar_businesses(body: SimilarBusinessesIn):
    """Return synthetic businesses comparable to the user's profile.

    Each row carries an `outcome` (succeeded / struggling / failed) so the chat
    can show the user how comparable businesses fared — the evidence behind
    the prediction. Optionally narrows per-block evidence to the blocks
    associated with the provided model IDs.
    """
    target_blocks = _blocks_from_model_ids(body.model_ids)
    result = get_evidence_service().find_similar(
        region_id=body.region_id,
        mcc_code=body.mcc_code,
        monthly_revenue=body.monthly_revenue,
        initial_investment=body.initial_investment,
        limit=body.limit,
        blocks=target_blocks,
    )
    return {
        "rows": [asdict(r) for r in result.rows],
        "summary": asdict(result.summary),
        "total_examined": result.total_examined,
        "sources": result.sources,
        "blocks": [asdict(b) for b in result.blocks],
    }
