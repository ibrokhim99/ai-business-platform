"""
System-prompt builder and tool schemas for the chat LLM (qwen2.5 via Ollama).

The system prompt embeds:
- A compact catalog of all 55 ML models from the live ModelRegistry
- The current ChatProfile snapshot
- Behavioral rules (Uzbek replies, when to ask follow-ups, when to run models)

Tool schemas use OpenAI-style function calling, which Ollama forwards verbatim
to the model.
"""
from __future__ import annotations

import json
from typing import Any

from app.ml.registry import ModelRegistry
from app.services.profile_to_input import ChatProfile

# ── Tool definitions ───────────────────────────────────────────────────────────

ASK_FOLLOWUP_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "ask_followup",
        "description": (
            "Foydalanuvchidan biznes haqida aniqlovchi savol so'rang. "
            "Faqat profilda muhim ma'lumot (region_id, mcc_code, monthly_revenue_estimate, "
            "initial_investment) yetishmaganda ishlating. Bir vaqtda faqat bitta savol bering."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question_uz": {
                    "type": "string",
                    "description": "O'zbek tilidagi aniq, qisqa savol",
                },
                "fields_needed": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Qaysi profil maydonlari kerakligi (e.g. ['mcc_code'])",
                },
            },
            "required": ["question_uz"],
        },
    },
}

UPDATE_PROFILE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "update_profile",
        "description": (
            "Foydalanuvchi yangi qiymat aytganida (masalan, oylik daromadi yoki "
            "boshlang'ich investitsiya), uni profilga yozing. Maydon nomlari "
            "ChatProfile bilan bir xil bo'lishi kerak."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "object",
                    "description": (
                        "Yangilanadigan profil maydonlari, masalan "
                        "{\"monthly_revenue_estimate\": 50000, \"mcc_code\": \"5812\"}"
                    ),
                },
            },
            "required": ["fields"],
        },
    },
}

RUN_MODELS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "run_models",
        "description": (
            "55 ta ML modelidan foydalanuvchi savoliga eng mos bo'lganlarini tanlang "
            "(1 dan 10 tagacha). Faqat zarur modellarni tanlang — hammasini ishga "
            "tushirmang. Modellar ishga tushgandan keyin natijalar avtomatik kelishadi."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "model_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tanlangan model ID'lar (masalan ['M-A1', 'M-B1'])",
                    "maxItems": 10,
                    "minItems": 1,
                },
                "reasoning_uz": {
                    "type": "string",
                    "description": "Nega bu modellar tanlangani — qisqa izoh",
                },
            },
            "required": ["model_ids"],
        },
    },
}

ALL_TOOLS: list[dict[str, Any]] = [ASK_FOLLOWUP_TOOL, UPDATE_PROFILE_TOOL, RUN_MODELS_TOOL]


# ── System prompt builder ──────────────────────────────────────────────────────

_BLOCK_LABELS_UZ = {
    "A": "Bozor tahlili",
    "B": "Prognozlash",
    "C": "Joylashuv",
    "D": "Moliyaviy",
    "E": "Raqobat",
    "F": "Kredit",
    "G": "Mijoz / Ijtimoiy",
    "H": "Marketing",
    "I": "Operatsiyalar",
    "J": "Firibgarlik / AML",
}


def _model_catalog_table(registry: ModelRegistry) -> str:
    rows = ["| ID | Blok | Nomi | Tavsif |", "|----|------|------|--------|"]
    for meta in sorted(registry.list_all(), key=lambda m: m.model_id):
        block_label = _BLOCK_LABELS_UZ.get(meta.block, meta.block)
        desc = (meta.description or meta.name).replace("|", "/").replace("\n", " ")
        if len(desc) > 110:
            desc = desc[:107] + "..."
        rows.append(f"| {meta.model_id} | {meta.block} · {block_label} | {meta.name} | {desc} |")
    return "\n".join(rows)


def _profile_snapshot(profile: ChatProfile) -> str:
    keys = [
        "region_id", "region_label", "mcc_code", "mcc_label", "niche",
        "population", "avg_income",
        "monthly_revenue_estimate", "monthly_fixed_costs", "monthly_rent",
        "initial_investment", "business_age_months",
        "lat", "lon", "radius_m",
        "requested_loan_amount", "loan_term_months",
    ]
    snap = {k: getattr(profile, k) for k in keys}
    return json.dumps(snap, ensure_ascii=False, indent=2)


def build_system_prompt(registry: ModelRegistry, profile: ChatProfile) -> str:
    catalog = _model_catalog_table(registry)
    snapshot = _profile_snapshot(profile)
    return f"""Siz BizIQ — O'zbekiston bank mijozlari uchun AI biznes maslahatchisisiz.
Sizning vazifangiz: foydalanuvchining biznes savollariga 55 ta ixtisoslashgan ML modeli yordamida aniq, raqamli javoblar berish.

QOIDALAR
1. **HAR DOIM O'ZBEK TILIDA** javob bering. Qisqa, aniq, professional uslub.
2. Foydalanuvchi salomlashsa yoki umumiy savol bersa — modellarsiz oddiy javob bering. `run_models` chaqirmang.
3. Agar profildagi muhim maydon yetishmasa yoki bo'sh bo'lsa (region_id="", mcc_code="", monthly_revenue_estimate=0, initial_investment=0) — `run_models` ni CHAQIRMANG. Avval `ask_followup` chaqiring va foydalanuvchidan aniq so'rang. Bo'sh qiymat = ma'lumot yo'q.
4. **MUHIM** — Foydalanuvchi xabarida JORIY PROFIL bilan ZIDDIYAT bo'lsa (boshqa biznes turi, boshqa hudud, yangi raqam), DARROV `update_profile` chaqiring va keyin tegishli modellarni ishga tushiring.
   Misollar:
   - Profilda `mcc_code: 7011 (Mehmonxona)`, foydalanuvchi "kiyim do'koni" deb yozdi → update_profile fields: {{"mcc_code": "5651", "mcc_label": "Oilaviy kiyim doʻkoni", "niche": "apparel"}}
   - Profilda `region_id: tashkent-01`, foydalanuvchi "Samarqandda" deb yozdi → update_profile fields: {{"region_id": "samarkand-01"}}
   - Foydalanuvchi "daromadim 50 mln so'm" dedi → update_profile fields: {{"monthly_revenue_estimate": 50000000}}
   MCC kodlari: kafe/restoran=5812, tez ovqat=5814, oziq-ovqat doʻkoni=5411, kiyim doʻkoni=5651, ayollar kiyimi=5621, mebel=5712, mehmonxona=7011, dorixona=5912, elektronika=5734, tibbiyot jihozlari=5047, sport/velosiped=5940, dasturiy taʻminot=7372, avtomobil savdosi=5511, chakana savdo=5999.
   Region kodlari: Toshkent=tashkent-01, Samarqand=samarkand-01, Buxoro=bukhara-01, Fargʻona=fergana-01, Andijon=andijan-01, Namangan=namangan-01, Jizzax=jizzakh-01, Guliston=gulistan-01, Navoiy=navoiy-01, Nukus=nukus-01, Termiz=termez-01.
5. Modellardan foydalanish uchun `run_models` ni chaqiring va FAQAT savolga to'g'ridan-to'g'ri tegishli 1-10 ta modelni tanlang. Hammasini ishga tushirmang.
6. Modellar tugagandan keyin natijalarni tabiiy o'zbek tilida sharhlang: asosiy raqamlarni ko'rsating, xulosa qiling, bitta amaliy tavsiya bering.
7. Hech qachon model natijalarini o'zingiz o'ylab topmang — har doim `run_models` orqali real natija oling.
8. **Foydalanuvchi xabari MUDDAT** — agar JORIY PROFIL eski yoki noto'g'ri bo'lsa, ishonchli emas. Foydalanuvchi yozgan biznes turi va hudud — muqaddam.

JORIY PROFIL
```json
{snapshot}
```

55 TA ML MODEL KATALOGI
{catalog}

JAVOB FORMATI (modellar ishlatilganda)
- 1 jumla — asosiy xulosa (asosiy raqam bilan)
- 2-4 ta nuqta — har bir ishlatilgan modelning eng muhim natijasi (raqam + nomi)
- 1 jumla — amaliy tavsiya
"""
