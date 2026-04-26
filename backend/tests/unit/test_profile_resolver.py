from app.services.profile_resolver import (
    apply_profile_fields,
    infer_profile_patch_from_text,
    normalize_profile_fields,
    resolve_profile_from_text,
)
from app.services.profile_to_input import ChatProfile


def test_infer_beauty_salon_over_hotel_words():
    fields = infer_profile_patch_from_text("Samarqandda buty salon uchun tahlil qil")

    assert fields["region_id"] == "samarkand-01"
    assert fields["region_label"] == "Samarqand — Markaz"
    assert fields["mcc_code"] == "7230"
    assert fields["mcc_label"] == "Goʻzallik saloni"
    assert fields["niche"] == "beauty"


def test_apply_profile_fields_overwrites_stale_hotel_profile():
    profile = ChatProfile(
        region_id="samarkand-01",
        mcc_code="7011",
        mcc_label="Mehmonxona",
        niche="hotel",
    )

    fields = apply_profile_fields(profile, {"mcc_code": "7230"})

    assert fields["mcc_label"] == "Goʻzallik saloni"
    assert profile.mcc_code == "7230"
    assert profile.mcc_label == "Goʻzallik saloni"
    assert profile.niche == "beauty"


def test_infer_restaurant_typo_overwrites_stale_hotel_profile():
    profile = ChatProfile(
        region_id="samarkand-01",
        mcc_code="7011",
        mcc_label="Mehmonxona",
        niche="hotel",
    )

    fields = infer_profile_patch_from_text("Samarqandda restauran biznesini bahola")
    apply_profile_fields(profile, fields)

    assert fields["region_id"] == "samarkand-01"
    assert fields["mcc_code"] == "5812"
    assert fields["mcc_label"] == "Restoran / Ovqatlanish"
    assert profile.mcc_code == "5812"
    assert profile.mcc_label == "Restoran / Ovqatlanish"
    assert profile.niche == "food"


def test_last_business_mention_wins_when_user_pastes_stale_hotel_answer():
    text = """
    Toʻliq tahlil
    Mehmonxona · Samarqand — Markaz
    Bu javob qaysi ma'lumotlarga asoslangan?
    Mehmonxona samarkand-01
    I asked about restauran in Samarqand, not this hotel response.
    """

    fields = infer_profile_patch_from_text(text)

    assert fields["region_id"] == "samarkand-01"
    assert fields["mcc_code"] == "5812"
    assert fields["mcc_label"] == "Restoran / Ovqatlanish"


def test_negated_hotel_does_not_override_restaurant_correction():
    fields = infer_profile_patch_from_text(
        "Mehmonxona javobi chiqdi. Samarqand markazida restauran ochmoqchiman, hotel emas."
    )

    assert fields["region_id"] == "samarkand-01"
    assert fields["mcc_code"] == "5812"
    assert fields["mcc_label"] == "Restoran / Ovqatlanish"


def test_unsupported_region_is_detected_instead_of_using_stale_region():
    resolution = resolve_profile_from_text("Qashqadaryo markazida mehmonxona ochmoqchiman")

    assert resolution.unsupported_region == "Qashqadaryo / Qarshi"
    assert resolution.fields["mcc_code"] == "7011"
    assert "region_id" not in resolution.fields


def test_supported_dataset_regions_include_nukus():
    fields = infer_profile_patch_from_text("Nukusda dorixona ochish kerak")

    assert fields["region_id"] == "nukus-01"
    assert fields["region_label"] == "Nukus — Markaz"
    assert fields["mcc_code"] == "5912"


def test_electronics_maps_to_dataset_mcc():
    fields = infer_profile_patch_from_text("Toshkentda elektronika do'koni uchun tahlil")

    assert fields["region_id"] == "tashkent-01"
    assert fields["mcc_code"] == "5734"
    assert fields["mcc_label"] == "Elektronika"


def test_unsupported_business_is_detected():
    resolution = resolve_profile_from_text("Samarqandda stomatologiya klinikasi ochmoqchiman")

    assert resolution.fields["region_id"] == "samarkand-01"
    assert resolution.unsupported_business == "Nomaʼlum biznes"


def test_money_amounts_with_million_override_stale_profile_values():
    fields = infer_profile_patch_from_text(
        "Samarqand markazida mehmonhona ochmoqchiman. "
        "Kredit — 200 million so'm, oylik daromad taxminan 20 million. "
        "Biznesim muvaffaqiyatli bo'ladimi? ROI"
    )

    assert fields["region_id"] == "samarkand-01"
    assert fields["mcc_code"] == "7011"
    assert fields["requested_loan_amount"] == 200_000_000
    assert fields["initial_investment"] == 200_000_000
    assert fields["monthly_revenue_estimate"] == 20_000_000


def test_normalize_region_adds_dependent_fields():
    fields = normalize_profile_fields({"region_id": "samarkand-01"})

    assert fields["region_label"] == "Samarqand — Markaz"
    assert fields["population"] == 530_000
    assert fields["lat"] == 39.6542
    assert fields["lon"] == 66.9597
