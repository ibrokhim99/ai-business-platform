"""For each model_id in the registry, build() must return a valid Pydantic input."""
import pytest
from pydantic import BaseModel

from app.ml.registry import get_registry
from app.services.profile_to_input import (
    ChatProfile,
    build,
    supported_model_ids,
)


def test_supported_ids_cover_registry():
    registry_ids = set(get_registry().all_ids())
    builder_ids = set(supported_model_ids())
    missing = registry_ids - builder_ids
    extra = builder_ids - registry_ids
    assert not missing, f"profile_to_input is missing builders for: {sorted(missing)}"
    assert not extra, f"profile_to_input has builders for unknown model_ids: {sorted(extra)}"


@pytest.mark.parametrize("model_id", sorted(supported_model_ids()))
def test_default_profile_builds_valid_input(model_id: str):
    profile = ChatProfile()
    result = build(model_id, profile)
    assert isinstance(result, BaseModel)


def test_unknown_model_id_raises():
    with pytest.raises(KeyError):
        build("M-X9", ChatProfile())


def test_partial_profile_uses_defaults():
    """LLM may have only filled some fields — defaults must produce valid inputs."""
    profile = ChatProfile(region_id="samarkand-01", mcc_code="5814", monthly_revenue_estimate=8_000)
    # Pick one model from each block to confirm defaults work post-override.
    for mid in ("M-A1", "M-B1", "M-C1", "M-D1", "M-E1", "M-F1", "M-G1", "M-H1", "M-I1", "M-J1"):
        result = build(mid, profile)
        assert isinstance(result, BaseModel)
