from app.services.llm_chat_service import (
    _augment_model_ids_for_advice,
    _default_model_ids_for_business_plan,
    _merge_input_resolutions,
)
from app.services.profile_resolver import InputResolution


def test_valid_deterministic_region_overrides_llm_unsupported_region():
    deterministic = InputResolution(
        fields={"region_id": "samarkand-01", "region_label": "Samarqand — Markaz"},
    )
    llm_resolution = InputResolution(
        fields={},
        unsupported_region="samarqand markazi",
    )

    merged = _merge_input_resolutions(deterministic, llm_resolution)

    assert merged.unsupported_region is None
    assert merged.fields["region_id"] == "samarkand-01"


def test_valid_deterministic_business_overrides_llm_unsupported_business():
    deterministic = InputResolution(
        fields={"mcc_code": "7011", "mcc_label": "Mehmonxona"},
    )
    llm_resolution = InputResolution(
        fields={},
        unsupported_business="mehmonxona biznesi",
    )

    merged = _merge_input_resolutions(deterministic, llm_resolution)

    assert merged.unsupported_business is None
    assert merged.fields["mcc_code"] == "7011"


def test_real_unsupported_scope_is_kept_when_no_deterministic_match_exists():
    deterministic = InputResolution(fields={})
    llm_resolution = InputResolution(
        fields={},
        unsupported_region="qashqadaryo markazi",
    )

    merged = _merge_input_resolutions(deterministic, llm_resolution)

    assert merged.unsupported_region == "qashqadaryo markazi"


def test_bank_product_prompt_adds_business_validation_models():
    selected = _augment_model_ids_for_advice(
        "Menga qaysi bank mahsuloti mosligini tavsiya qil",
        ["M-F5"],
    )

    assert selected[:8] == [
        "M-A5", "M-D1", "M-D3", "M-D5", "M-F1", "M-F2", "M-F3", "M-F5",
    ]


def test_non_product_prompt_keeps_selected_models():
    selected = _augment_model_ids_for_advice(
        "Toshkentda restoran bozori hajmini hisobla",
        ["M-A1"],
    )

    assert selected == ["M-A1"]


def test_business_plan_prompt_runs_validation_models_without_explicit_question():
    selected = _default_model_ids_for_business_plan(
        "Samarqand markazida mehmonxona ochmoqchiman. "
        "Oylik daromadim 18 mln so'm, boshlang'ich sarmoyam 220 mln so'm.",
        [],
    )

    assert selected == ["M-A5", "M-D1", "M-D3", "M-D5", "M-E4", "M-C1"]


def test_business_plan_prompt_keeps_existing_model_choice():
    selected = _default_model_ids_for_business_plan(
        "Samarqand markazida mehmonxona ochmoqchiman.",
        ["M-A1"],
    )

    assert selected == ["M-A1"]
