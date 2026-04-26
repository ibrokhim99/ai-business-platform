"""
LlmChatService — orchestrates qwen2.5 (via Ollama) + the 55 ML models.

Per user turn:
1. Decision call (non-streaming, with tools) — model emits ask_followup,
   update_profile, run_models, or any combination.
2. If run_models was chosen, execute selected models in parallel via
   PredictionService.predict (concurrency capped). Stream tool_call_start /
   tool_result events as they happen.
3. Synthesis call (streaming) — model writes a Uzbek answer that references
   the actual numerical results. Stream text deltas as they arrive.

Returns an async iterator of ChatEvent objects; the API layer encodes them as
Server-Sent Events.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Literal

from app.config import settings
from app.core.logging import get_logger
from app.ml.registry import ModelRegistry
from app.services.block_data import dataset_catalog, dataset_scope_counts, lookup_blocks_for_models
from app.services.llm_prompts import ALL_TOOLS, build_system_prompt
from app.services.ollama_client import OllamaClient, OllamaError
from app.services.openai_client import get_openai_client
from app.services.prediction_service import PredictionService
from app.services.profile_to_input import ChatProfile, build as build_input
from app.services.profile_resolver import (
    InputResolution,
    apply_profile_fields,
    normalize_profile_fields,
    resolve_profile_from_text,
)

log = get_logger()


# ── Event protocol ────────────────────────────────────────────────────────────

EventType = Literal[
    "profile_patch",
    "tool_call_start",
    "tool_result",
    "text",
    "done",
    "error",
]


@dataclass
class ChatEvent:
    type: EventType
    data: dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        return f"event: {self.type}\ndata: {json.dumps(self.data, ensure_ascii=False, default=str)}\n\n"


@dataclass
class ChatTurn:
    role: Literal["user", "assistant"]
    content: str


# ── Service ───────────────────────────────────────────────────────────────────


def _block_for(model_id: str) -> str:
    # "M-A1" -> "A"
    return model_id.split("-", 1)[1][0] if "-" in model_id else ""


class LlmChatService:
    def __init__(
        self,
        registry: ModelRegistry,
        ollama: OllamaClient,
        prediction_service: PredictionService,
    ):
        self._registry = registry
        self._ollama = ollama
        self._predictions = prediction_service

    async def stream_reply(
        self,
        *,
        user_message: str,
        history: list[ChatTurn],
        profile: ChatProfile,
        request_id: str | None = None,
        user_id: str | None = None,
        user_role: str | None = None,
    ) -> AsyncIterator[ChatEvent]:
        request_id = request_id or str(uuid.uuid4())
        started_at = time.perf_counter()

        resolution = await self._resolve_user_input(user_message)
        if resolution.has_unsupported_input:
            yield ChatEvent("text", {"delta": self._unsupported_input_message(resolution)})
            yield ChatEvent(
                "done",
                {
                    "chosen_models": [],
                    "total_latency_ms": int((time.perf_counter() - started_at) * 1000),
                    "reason": "no_evidence",
                },
            )
            return
        if resolution.fields:
            explicit_patch = apply_profile_fields(profile, resolution.fields)
            yield ChatEvent("profile_patch", {"fields": explicit_patch})

        # ── Build messages ────────────────────────────────────────────────────
        system_prompt = build_system_prompt(self._registry, profile)
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for turn in history[-settings.chat_max_history_turns:]:
            messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": user_message})

        # ── Decision call ─────────────────────────────────────────────────────
        try:
            decision = await self._ollama.chat(messages, tools=ALL_TOOLS)
        except OllamaError as e:
            yield ChatEvent("error", {"message": f"Ollama unavailable: {e}"})
            return
        except Exception as e:  # pragma: no cover
            log.error("ollama_decision_error", error=repr(e), error_type=type(e).__name__, exc_info=True)
            yield ChatEvent("error", {"message": f"LLM decision call failed: {type(e).__name__}: {e}"})
            return

        decision_msg: dict[str, Any] = (decision or {}).get("message") or {}
        tool_calls: list[dict[str, Any]] = decision_msg.get("tool_calls") or []
        free_text: str = (decision_msg.get("content") or "").strip()

        # Dispatch tools — order: profile_patch, ask_followup, run_models
        chosen_model_ids: list[str] = []
        run_reasoning: str = ""
        followup_text: str | None = None
        followup_fields: list[str] = []

        for call in tool_calls:
            fn = (call.get("function") or {})
            name = fn.get("name")
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            args = args or {}

            if name == "update_profile":
                fields = args.get("fields") or {}
                if isinstance(fields, dict) and fields:
                    # The deterministic extractor is based on the latest user
                    # turn and wins over tool-call guesses, especially for
                    # amounts like "200 million so'm" that some LLMs compress
                    # to 200_000.
                    fields = {**fields, **resolution.fields}
                    fields = apply_profile_fields(profile, fields)
                    yield ChatEvent("profile_patch", {"fields": fields})
            elif name == "ask_followup":
                followup_text = (args.get("question_uz") or "").strip() or followup_text
                followup_fields = args.get("fields_needed") or []
            elif name == "run_models":
                ids = args.get("model_ids") or []
                if isinstance(ids, list):
                    chosen_model_ids = [str(x) for x in ids if isinstance(x, str)]
                run_reasoning = (args.get("reasoning_uz") or "").strip()

        chosen_model_ids = self._sanitize_model_ids(chosen_model_ids)

        # ── Branch: ask_followup wins if no models were also chosen ──────────
        if followup_text and not chosen_model_ids:
            yield ChatEvent("text", {"delta": followup_text})
            yield ChatEvent(
                "done",
                {
                    "chosen_models": [],
                    "total_latency_ms": int((time.perf_counter() - started_at) * 1000),
                    "reason": "ask_followup",
                },
            )
            return

        # ── Branch: no tool calls — return whatever free text the model wrote ─
        if not chosen_model_ids:
            text = free_text or "Kechirasiz, savolingizni tushuna olmadim. Iltimos, qaytadan aniq qilib yozing."
            yield ChatEvent("text", {"delta": text})
            yield ChatEvent(
                "done",
                {
                    "chosen_models": [],
                    "total_latency_ms": int((time.perf_counter() - started_at) * 1000),
                    "reason": "no_tools",
                },
            )
            return

        data_issue = self._profile_data_issue(profile)
        if data_issue:
            yield ChatEvent("text", {"delta": data_issue})
            yield ChatEvent(
                "done",
                {
                    "chosen_models": chosen_model_ids,
                    "total_latency_ms": int((time.perf_counter() - started_at) * 1000),
                    "reason": "no_evidence",
                },
            )
            return

        # ── Branch: run_models — execute then synthesize ──────────────────────
        results: list[dict[str, Any]] = []
        sem = asyncio.Semaphore(max(1, settings.chat_model_concurrency))

        async def run_one(mid: str) -> dict[str, Any]:
            meta = None
            try:
                meta = self._registry.get(mid).metadata
            except Exception:
                meta = None
            title = meta.name if meta else mid
            block = meta.block if meta else _block_for(mid)

            await emit_q.put(ChatEvent("tool_call_start", {"model_id": mid, "title": title, "block": block}))

            t0 = time.perf_counter()
            try:
                async with sem:
                    input_obj = build_input(mid, profile)
                    pred = await self._predictions.predict(
                        mid, input_obj, include_explanation=False,
                        request_id=f"{request_id}:{mid}", user_id=user_id, user_role=user_role,
                    )
                latency_ms = int((time.perf_counter() - t0) * 1000)
                payload = {
                    "model_id": mid,
                    "prediction": pred.prediction if isinstance(pred.prediction, dict) else {"value": pred.prediction},
                    "latency_ms": pred.latency_ms or latency_ms,
                    "is_stub": bool(pred.is_stub),
                }
                await emit_q.put(ChatEvent("tool_result", payload))
                return payload
            except Exception as e:
                log.warning("chat_model_error", model_id=mid, error=str(e))
                payload = {
                    "model_id": mid,
                    "prediction": None,
                    "latency_ms": int((time.perf_counter() - t0) * 1000),
                    "is_stub": False,
                    "error": str(e)[:200],
                }
                await emit_q.put(ChatEvent("tool_result", payload))
                return payload

        emit_q: asyncio.Queue[ChatEvent | None] = asyncio.Queue()

        async def runner() -> list[dict[str, Any]]:
            r = await asyncio.gather(*(run_one(mid) for mid in chosen_model_ids))
            await emit_q.put(None)  # sentinel
            return r

        runner_task = asyncio.create_task(runner())
        while True:
            ev = await emit_q.get()
            if ev is None:
                break
            yield ev
        results = await runner_task

        # ── Synthesis call (streaming) ────────────────────────────────────────
        # Pull real CSV-grounded context for the blocks whose models ran, so
        # the LLM cites actual data (e.g. "47 similar restaurants in Tashkent
        # averaged $X in revenue") instead of guessing from model output alone.
        data_context = self._build_data_context(chosen_model_ids, profile)

        # If we have zero matched rows in any chosen block, the synthesis would
        # have nothing real to cite — refuse to answer rather than hallucinate.
        # The frontend uses the `no_evidence` reason on the done event to hide
        # the report/recommendation/data-sources blocks too, so the user only
        # sees the refusal message instead of cards full of junk numbers.
        if not data_context:
            yield ChatEvent("text", {"delta": (
                "Bizda hozircha tanlangan hudud va soha bo'yicha yetarli tarixiy "
                "ma'lumot yo'q. Ma'lumotlar bazasida mos yozuvlar topilmadi, shuning "
                "uchun aniq tahlil va tavsiya bera olmaymiz. Iltimos, boshqa hudud "
                "yoki sohani sinab ko'ring."
            )})
            yield ChatEvent(
                "done",
                {
                    "chosen_models": chosen_model_ids,
                    "total_latency_ms": int((time.perf_counter() - started_at) * 1000),
                    "reason": "no_evidence",
                },
            )
            return

        synth_messages = list(messages)
        if run_reasoning:
            synth_messages.append({"role": "assistant", "content": f"[Tanlangan modellar sababi: {run_reasoning}]"})
        synth_messages.append({
            "role": "tool",
            "content": json.dumps({"model_results": results}, ensure_ascii=False, default=str),
        })
        if data_context:
            synth_messages.append({
                "role": "tool",
                "content": json.dumps({"dataset_evidence": data_context}, ensure_ascii=False, default=str),
            })
        synth_messages.append({
            "role": "user",
            "content": (
                "Yuqoridagi model natijalari va `dataset_evidence` (haqiqiy tarixiy "
                "ma'lumotlar) asosida foydalanuvchining savoliga to'liq O'zbek tilida "
                "javob bering. dataset_evidence ichidagi haqiqiy raqamlarni keltiring "
                "(masalan: \"shu hududda 47 ta o'xshash biznes mavjud, o'rtacha daromad X\"). "
                "MUHIM: faqat model_results va dataset_evidence ichidagi raqamlarni "
                "ishlating — boshqa raqamlar, foizlar yoki statistikani O'YLAB TOPMANG. "
                "M-D1 `survival_probability_2y` — hayotiylik/yashab qolish ehtimoli; "
                "uni ROI deb atamang. M-D3 `roi_pct` — ROI; M-D3 `payback_months` "
                "— investitsiya qaytish muddati. Agar M-D1 va M-D3 ikkalasi ishlagan "
                "bo'lsa, moliyaviy bo'limda ikkalasini alohida yozing. "
                "Agar biror ma'lumot yo'q bo'lsa, \"bu ma'lumot mavjud emas\" deb yozing. "
                "Faqat tabiiy matn yozing — JSON, kod yoki tool chaqiruvini ishlatmang. "
                "Bitta amaliy tavsiya bering."
            ),
        })

        try:
            full_text = ""
            async for chunk in self._ollama.chat_stream(synth_messages):
                msg = (chunk or {}).get("message") or {}
                delta = msg.get("content") or ""
                if delta:
                    full_text += delta
                    yield ChatEvent("text", {"delta": delta})
                if chunk.get("done"):
                    break
            if not full_text.strip():
                yield ChatEvent("text", {"delta": "(Modellar ishladi, lekin LLM matn qaytarmadi.)"})
        except OllamaError as e:
            yield ChatEvent("error", {"message": f"Synthesis failed: {e}"})

        yield ChatEvent(
            "done",
            {
                "chosen_models": chosen_model_ids,
                "total_latency_ms": int((time.perf_counter() - started_at) * 1000),
                "reason": "run_models",
            },
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _resolve_user_input(self, user_message: str) -> InputResolution:
        """Extract region/business from the latest user turn before tool choice.

        Deterministic aliases provide a safe local fallback. When an OpenAI API
        key is configured, a small JSON extraction call handles arbitrary user
        wording and tells us when the requested scope is outside the CSV data.
        """
        deterministic = resolve_profile_from_text(user_message)
        if not settings.openai_api_key:
            return deterministic

        try:
            llm_resolution = await self._extract_input_with_openai(user_message)
        except Exception as e:
            log.warning("input_resolution_llm_failed", error=str(e)[:200])
            return deterministic

        if llm_resolution is None:
            return deterministic
        if llm_resolution.has_unsupported_input:
            return llm_resolution
        fields = {**deterministic.fields, **llm_resolution.fields}
        return InputResolution(fields=normalize_profile_fields(fields))

    async def _extract_input_with_openai(self, user_message: str) -> InputResolution | None:
        catalog = dataset_catalog()
        regions = ", ".join(catalog["regions"])
        mcc_codes = ", ".join(catalog["mcc_codes"])
        messages = [
            {
                "role": "system",
                "content": (
                    "You extract the latest intended business analysis scope from a user message. "
                    "Ignore pasted previous answers, tables, evidence rows, and stale profile text. "
                    "Corrections like 'I asked about...', 'not this hotel', or 'hotel emas' override older text. "
                    "Return JSON only."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Supported dataset region_id values: "
                    f"{regions}.\n"
                    "Supported dataset MCC values and meanings: "
                    "5047=medical equipment, 5411=grocery, 5511=auto dealer, "
                    "5621=womens clothing, 5651=clothing, 5712=furniture, "
                    "5734=electronics, 5812=restaurant/cafe, 5814=fast food, "
                    "5912=pharmacy, 5940=sports/bicycle, 5999=retail, "
                    "7011=hotel, 7372=software.\n"
                    f"Supported MCC code list: {mcc_codes}.\n"
                    "JSON schema: "
                    '{"region_id": string|null, "unsupported_region": string|null, '
                    '"mcc_code": string|null, "unsupported_business": string|null}.\n'
                    "If the user asks for a region not in the supported list, set unsupported_region. "
                    "If the user asks for a business that is not semantically one of the supported MCC categories, "
                    "set unsupported_business. Do not map a different business just to make it fit.\n"
                    f"User message:\n{user_message}"
                ),
            },
        ]
        client = get_openai_client()
        resp = await client.chat(messages, format="json", options={"temperature": 0})
        content = ((resp.get("message") or {}).get("content") or "").strip()
        if not content:
            return None
        payload = json.loads(content)
        if not isinstance(payload, dict):
            return None

        fields: dict[str, Any] = {}
        region_id = payload.get("region_id")
        mcc_code = payload.get("mcc_code")
        if isinstance(region_id, str) and region_id in catalog["regions"]:
            fields["region_id"] = region_id
        if isinstance(mcc_code, str) and mcc_code in catalog["mcc_codes"]:
            fields["mcc_code"] = mcc_code

        unsupported_region = payload.get("unsupported_region")
        unsupported_business = payload.get("unsupported_business")
        return InputResolution(
            fields=normalize_profile_fields(fields),
            unsupported_region=unsupported_region if isinstance(unsupported_region, str) and unsupported_region else None,
            unsupported_business=unsupported_business if isinstance(unsupported_business, str) and unsupported_business else None,
        )

    def _unsupported_input_message(self, resolution: InputResolution) -> str:
        parts: list[str] = []
        if resolution.unsupported_region:
            parts.append(f"hudud: {resolution.unsupported_region}")
        if resolution.unsupported_business:
            parts.append(f"soha: {resolution.unsupported_business}")
        scope = ", ".join(parts) or "tanlangan so'rov"
        return (
            f"Bizda hozircha {scope} bo'yicha dataset mavjud emas. "
            "Shuning uchun bu so'rov uchun model tahlili va tavsiya bermaymiz. "
            "Iltimos, datasetda mavjud hudud yoki biznes turini tanlang."
        )

    def _profile_data_issue(self, profile: ChatProfile) -> str | None:
        region_id = getattr(profile, "region_id", "") or ""
        mcc_code = getattr(profile, "mcc_code", "") or ""
        missing: list[str] = []
        if not region_id:
            missing.append("hudud")
        if not mcc_code:
            missing.append("biznes turi")
        if missing:
            return (
                f"Model tahlili uchun {', '.join(missing)} kerak. "
                "Iltimos, qaysi hudud va qaysi biznes turini tahlil qilishni aniq yozing."
            )

        catalog = dataset_catalog()
        region_label = getattr(profile, "region_label", None) or region_id
        mcc_label = getattr(profile, "mcc_label", None) or mcc_code
        if region_id not in catalog["regions"]:
            return (
                f"Bizda hozircha {region_label} bo'yicha dataset mavjud emas. "
                "Shuning uchun model tahlili va tavsiya bermaymiz."
            )
        if mcc_code not in catalog["mcc_codes"]:
            return (
                f"Bizda hozircha {mcc_label} bo'yicha dataset mavjud emas. "
                "Shuning uchun model tahlili va tavsiya bermaymiz."
            )

        counts = dataset_scope_counts(region_id=region_id, mcc_code=mcc_code)
        if not any(counts.values()):
            return (
                f"Bizda hozircha {region_label} hududida {mcc_label} bo'yicha "
                "yetarli tarixiy dataset mavjud emas. Shuning uchun bu so'rov "
                "uchun model tahlili va tavsiya bermaymiz."
            )
        return None

    def _build_data_context(self, model_ids: list[str], profile: ChatProfile) -> dict[str, Any] | None:
        """Return per-block data evidence the LLM should cite during synthesis.

        Only includes blocks for which we have at least one matched row.
        Capped at a small payload — the LLM doesn't need 1000 rows; it needs
        the stats and a few representative samples.
        """
        try:
            region_id = getattr(profile, "region_id", None)
            mcc_code = getattr(profile, "mcc_code", None)
            lookups = lookup_blocks_for_models(
                model_ids, region_id=region_id, mcc_code=mcc_code, limit=3,
            )
        except Exception as e:
            log.warning("data_context_failed", error=str(e))
            return None
        if not lookups:
            return None
        out: dict[str, Any] = {}
        for block, bl in lookups.items():
            # Skip blocks with no rows OR no rows matching the user's profile —
            # feeding empty stats/samples to the LLM invites hallucinated numbers.
            if bl.total_examined == 0 or bl.matched_count == 0:
                continue
            out[block] = {
                "matched_count": bl.matched_count,
                "total_examined": bl.total_examined,
                "stats": bl.stats,
                "sample_rows": bl.sample_rows,
                "source": bl.source,
            }
        return out or None

    def _sanitize_model_ids(self, ids: list[str]) -> list[str]:
        valid = set(self._registry.all_ids())
        out: list[str] = []
        seen: set[str] = set()
        for mid in ids:
            if mid in valid and mid not in seen:
                out.append(mid)
                seen.add(mid)
                if len(out) >= settings.chat_max_models_per_call:
                    break
        return out
