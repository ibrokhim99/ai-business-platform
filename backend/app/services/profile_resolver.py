"""Deterministic profile normalization for chat turns.

The LLM still decides which models to run, but explicit business/region words
from the user should not depend on the model remembering stale profile state.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.services.profile_to_input import ChatProfile


REGION_DEFAULTS: dict[str, dict[str, Any]] = {
    "tashkent-01": {"region_label": "Toshkent — Yunusobod", "population": 320_000, "avg_income": 720, "lat": 41.3611, "lon": 69.2867},
    "samarkand-01": {"region_label": "Samarqand — Markaz", "population": 530_000, "avg_income": 480, "lat": 39.6542, "lon": 66.9597},
    "bukhara-01": {"region_label": "Buxoro — Markaz", "population": 280_000, "avg_income": 460, "lat": 39.7747, "lon": 64.4286},
    "fergana-01": {"region_label": "Fargʻona — Markaz", "population": 320_000, "avg_income": 440, "lat": 40.3894, "lon": 71.7843},
    "andijan-01": {"region_label": "Andijon — Markaz", "population": 410_000, "avg_income": 450, "lat": 40.7821, "lon": 72.3442},
    "namangan-01": {"region_label": "Namangan — Markaz", "population": 470_000, "avg_income": 430, "lat": 40.9983, "lon": 71.6726},
    "jizzakh-01": {"region_label": "Jizzax", "population": 180_000, "avg_income": 410, "lat": 40.1158, "lon": 67.8422},
    "gulistan-01": {"region_label": "Guliston — Markaz", "population": 190_000, "avg_income": 420, "lat": 40.4897, "lon": 68.7842},
    "navoiy-01": {"region_label": "Navoiy — Markaz", "population": 160_000, "avg_income": 520, "lat": 40.0844, "lon": 65.3792},
    "nukus-01": {"region_label": "Nukus — Markaz", "population": 330_000, "avg_income": 410, "lat": 42.4619, "lon": 59.6166},
    "termez-01": {"region_label": "Termiz — Markaz", "population": 190_000, "avg_income": 400, "lat": 37.2242, "lon": 67.2783},
}

MCC_DEFAULTS: dict[str, dict[str, Any]] = {
    "5812": {"mcc_label": "Restoran / Ovqatlanish", "niche": "food", "avg_transaction_value": 15, "monthly_transactions": 1_000, "gross_margin_pct": 60},
    "5814": {"mcc_label": "Tez ovqatlanish", "niche": "food", "avg_transaction_value": 8, "monthly_transactions": 2_400, "gross_margin_pct": 55},
    "5411": {"mcc_label": "Oziq-ovqat doʻkoni", "niche": "grocery", "avg_transaction_value": 22, "monthly_transactions": 1_400, "gross_margin_pct": 28},
    "5651": {"mcc_label": "Oilaviy kiyim doʻkoni", "niche": "apparel", "avg_transaction_value": 38, "monthly_transactions": 420, "gross_margin_pct": 52},
    "5712": {"mcc_label": "Mebel doʻkoni", "niche": "furniture", "avg_transaction_value": 320, "monthly_transactions": 80, "gross_margin_pct": 42},
    "7011": {"mcc_label": "Mehmonxona", "niche": "hotel", "avg_transaction_value": 95, "monthly_transactions": 220, "gross_margin_pct": 65},
    "7230": {"mcc_label": "Goʻzallik saloni", "niche": "beauty", "avg_transaction_value": 18, "monthly_transactions": 540, "gross_margin_pct": 70},
    "7999": {"mcc_label": "Dam olish xizmatlari", "niche": "recreation", "avg_transaction_value": 25, "monthly_transactions": 600, "gross_margin_pct": 60},
    "5999": {"mcc_label": "Maxsus chakana savdo", "niche": "retail", "avg_transaction_value": 28, "monthly_transactions": 480, "gross_margin_pct": 48},
    "8011": {"mcc_label": "Tibbiy xizmatlar", "niche": "medical", "avg_transaction_value": 65, "monthly_transactions": 240, "gross_margin_pct": 55},
    "7542": {"mcc_label": "Avtomobil yuvish", "niche": "recreation", "avg_transaction_value": 6, "monthly_transactions": 2_500, "gross_margin_pct": 65},
    "5912": {"mcc_label": "Dorixona", "niche": "pharmacy", "avg_transaction_value": 18, "monthly_transactions": 1_200, "gross_margin_pct": 35},
    "5734": {"mcc_label": "Elektronika", "niche": "electronics", "avg_transaction_value": 220, "monthly_transactions": 130, "gross_margin_pct": 28},
    "5511": {"mcc_label": "Avtomobil savdosi", "niche": "auto_dealer", "avg_transaction_value": 6500, "monthly_transactions": 12, "gross_margin_pct": 18},
    "7372": {"mcc_label": "Dasturiy taʻminot", "niche": "software", "avg_transaction_value": 280, "monthly_transactions": 90, "gross_margin_pct": 78},
    "5940": {"mcc_label": "Velosiped / Sport", "niche": "sports", "avg_transaction_value": 95, "monthly_transactions": 180, "gross_margin_pct": 38},
    "5047": {"mcc_label": "Tibbiyot jihozlari", "niche": "medical_equipment", "avg_transaction_value": 320, "monthly_transactions": 110, "gross_margin_pct": 30},
    "5621": {"mcc_label": "Ayollar kiyim doʻkoni", "niche": "womens_clothing", "avg_transaction_value": 42, "monthly_transactions": 360, "gross_margin_pct": 54},
}

_REGION_ALIASES: list[tuple[str, str | None, str]] = [
    (r"\btoshkent\w*|\btashkent\w*|\byunusobod\w*", "tashkent-01", "Toshkent"),
    (r"\bsamarqand\w*|\bsamarkand\w*", "samarkand-01", "Samarqand"),
    (r"\bbuxoro\w*|\bbukhara\w*", "bukhara-01", "Buxoro"),
    (r"\bfarg[ʻ'`]ona\w*|\bfergana\w*", "fergana-01", "Fargʻona"),
    (r"\bandijon\w*|\bandijan\w*", "andijan-01", "Andijon"),
    (r"\bnamangan\w*", "namangan-01", "Namangan"),
    (r"\bjizzax\w*|\bjizzakh\w*", "jizzakh-01", "Jizzax"),
    (r"\bguliston\w*|\bgulistan\w*|\bsirdaryo\w*", "gulistan-01", "Guliston"),
    (r"\bnavoiy\w*|\bnavoi\w*", "navoiy-01", "Navoiy"),
    (r"\bnukus\w*|qoraqalpog[ʻ'`]?iston\w*|karakalpak\w*", "nukus-01", "Nukus"),
    (r"\btermiz\w*|\btermez\w*|\bsurxondaryo\w*|\bsurkhandarya\w*", "termez-01", "Termiz"),
    (r"\bqashqadaryo\w*|\bkashkadarya\w*|\bqarshi\w*", None, "Qashqadaryo / Qarshi"),
    (r"\bxorazm\w*|\burganch\w*|\bkhorezm\w*", None, "Xorazm / Urganch"),
    (r"\bqo[ʻ'`]?qon\w*|\bkokand\w*", None, "Qoʻqon"),
]

_MCC_ALIASES: list[tuple[str, str | None, str]] = [
    (r"\bbuty\s+salon\b|\bbeauty\s+salon\b|go[ʻ'`]?zallik\s+salon|go[ʻ'`]?zallik|salon", "7230", "Goʻzallik saloni"),
    (r"\bmehmonxona\b|\bmehmonhona\b|\bhotel\b", "7011", "Mehmonxona"),
    (r"tez\s+ovqat|fast\s*food", "5814", "Tez ovqatlanish"),
    (r"kafe|rest[ao]u?r[ao]n\w*", "5812", "Restoran / Ovqatlanish"),
    (r"oziq[-\s]?ovqat|grocery|market", "5411", "Oziq-ovqat doʻkoni"),
    (r"ayollar\s+kiyim|women'?s\s+clothing", "5621", "Ayollar kiyim doʻkoni"),
    (r"kiyim|clothing|apparel", "5651", "Oilaviy kiyim doʻkoni"),
    (r"mebel|furniture", "5712", "Mebel doʻkoni"),
    (r"dorixona|pharmacy", "5912", "Dorixona"),
    (r"elektronika|electronics|maishiy\s+texnika", "5734", "Elektronika"),
    (r"tibbiyot\s+jihoz|medical\s+equipment", "5047", "Tibbiyot jihozlari"),
    (r"dasturiy|software|saas", "7372", "Dasturiy taʻminot"),
    (r"avtomobil\s+savdo|auto\s+dealer", "5511", "Avtomobil savdosi"),
    (r"sport|velosiped|bicycle", "5940", "Velosiped / Sport"),
    (r"chakana|retail", "5999", "Maxsus chakana savdo"),
    (r"barber|sartarosh|spa|stomatolog|dental|maktab|bog[ʻ'`]?cha|qurilish|construction", None, "Nomaʼlum biznes"),
]


@dataclass(frozen=True)
class InputResolution:
    fields: dict[str, Any] = field(default_factory=dict)
    unsupported_region: str | None = None
    unsupported_business: str | None = None

    @property
    def has_unsupported_input(self) -> bool:
        return bool(self.unsupported_region or self.unsupported_business)


def _is_negated_match(text: str, match: re.Match[str]) -> bool:
    before = text[max(0, match.start() - 48):match.start()]
    after = text[match.end():match.end() + 24]
    return bool(
        re.search(r"\bnot\b(?:\s+\w+){0,3}\s*$", before)
        or re.search(r"^\s+(emas|yo['ʻ`]?q)\b", after)
    )


def _parse_amount(raw_number: str, raw_unit: str | None) -> float:
    cleaned = raw_number.replace(" ", "").replace("_", "").replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        return 0.0

    unit = (raw_unit or "").lower()
    if re.search(r"mlrd|milliard|billion", unit):
        value *= 1_000_000_000
    elif re.search(r"mln|million|million|mln\.?", unit):
        value *= 1_000_000
    elif re.search(r"\bk\b|ming|thousand", unit):
        value *= 1_000
    return value


def _infer_amount_fields(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    amount_re = re.compile(
        r"(?P<num>\d+(?:[\s_,.]\d+)?)\s*"
        r"(?P<unit>mlrd|milliard|billion|mln\.?|million|ming|thousand|k)?"
        r"(?:\s*(?:so['ʻ`]?m|sum|uzs|\$|usd))?",
        re.IGNORECASE,
    )

    for match in amount_re.finditer(text):
        amount = _parse_amount(match.group("num"), match.group("unit"))
        if amount <= 0:
            continue

        before = text[max(0, match.start() - 48):match.start()].lower()
        after = text[match.end():match.end() + 48].lower()
        context = f"{before} {after}"

        if re.search(r"kredit|loan|qarz", context):
            fields["requested_loan_amount"] = amount
            continue
        if re.search(r"oylik\s+daromad|daromad|revenue|tushum|savdo", context):
            fields["monthly_revenue_estimate"] = amount
            continue
        if re.search(r"sarmoya|invest|investment|boshlang[ʻ'`]?ich|kapital", context):
            fields["initial_investment"] = amount

    if (
        "requested_loan_amount" in fields
        and "initial_investment" not in fields
        and re.search(r"roi|ochmoq|ochish|start|boshlamoq|boshlash", text.lower())
    ):
        fields["initial_investment"] = fields["requested_loan_amount"]

    return fields


def normalize_profile_fields(fields: dict[str, Any]) -> dict[str, Any]:
    out = dict(fields)
    region_id = out.get("region_id")
    if isinstance(region_id, str) and region_id in REGION_DEFAULTS:
        out.update(REGION_DEFAULTS[region_id])
        out["region_id"] = region_id

    mcc_code = out.get("mcc_code")
    if isinstance(mcc_code, str) and mcc_code in MCC_DEFAULTS:
        out.update(MCC_DEFAULTS[mcc_code])
        out["mcc_code"] = mcc_code

    return out


def infer_profile_patch_from_text(text: str) -> dict[str, Any]:
    return resolve_profile_from_text(text).fields


def resolve_profile_from_text(text: str) -> InputResolution:
    lowered = text.lower()
    fields: dict[str, Any] = {}
    unsupported_region: str | None = None
    unsupported_business: str | None = None

    last_region: tuple[int, str | None, str] | None = None
    for pattern, region_id, label in _REGION_ALIASES:
        for match in re.finditer(pattern, lowered):
            if last_region is None or match.start() > last_region[0]:
                last_region = (match.start(), region_id, label)
    if last_region:
        if last_region[1]:
            fields["region_id"] = last_region[1]
        else:
            unsupported_region = last_region[2]

    last_mcc: tuple[int, str | None, str] | None = None
    for pattern, mcc_code, label in _MCC_ALIASES:
        for match in re.finditer(pattern, lowered):
            if _is_negated_match(lowered, match):
                continue
            if last_mcc is None or match.start() > last_mcc[0]:
                last_mcc = (match.start(), mcc_code, label)
    if last_mcc:
        if last_mcc[1]:
            fields["mcc_code"] = last_mcc[1]
        else:
            unsupported_business = last_mcc[2]

    fields.update(_infer_amount_fields(text))

    return InputResolution(
        fields=normalize_profile_fields(fields),
        unsupported_region=unsupported_region,
        unsupported_business=unsupported_business,
    )


def apply_profile_fields(profile: ChatProfile, fields: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_profile_fields(fields)
    for key, value in normalized.items():
        if hasattr(profile, key):
            setattr(profile, key, value)
    return normalized
