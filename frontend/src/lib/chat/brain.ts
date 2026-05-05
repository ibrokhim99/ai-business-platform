import type { BusinessProfile } from './profile';
import type { ModelDef, BlockId, Spark } from './models';
import { ALL_MODELS } from './models';
import { initialResults, type ModelResult } from './runner';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface ChatHistoryTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface StreamCallbacks {
  /** LLM extracted new profile fields (e.g. user said "daromadim 50K"). */
  onProfilePatch?: (patch: Partial<BusinessProfile>) => void;
  /** A model started executing. UI marks the card as running. */
  onToolCallStart?: (e: { modelId: string; title: string; block: BlockId }) => void;
  /** A model finished. UI flips the card to done with formatted headline + spark. */
  onToolResult?: (e: ModelResult) => void;
  /** Token chunk for the assistant message. */
  onTextDelta?: (delta: string) => void;
  /** Stream finished cleanly. */
  onDone?: (e: { chosenModels: string[]; totalLatencyMs: number; reason?: string }) => void;
  /** Stream errored. Surfaces the message to the UI. */
  onError?: (msg: string) => void;
  signal?: AbortSignal;
}

const MODEL_BY_ID: Record<string, ModelDef | undefined> = Object.fromEntries(
  ALL_MODELS.map((m) => [m.modelId, m]),
);

/**
 * Stream a chat reply from the backend LLM-driven /chat/stream endpoint.
 * Parses Server-Sent Events and dispatches into the provided callbacks.
 */
export async function streamAnswer(
  message: string,
  history: ChatHistoryTurn[],
  profile: BusinessProfile,
  cb: StreamCallbacks,
): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };

  const resp = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, history, profile }),
    signal: cb.signal,
  });

  if (resp.status === 401) {
    cb.onError?.('API ruxsat soʻrovini rad etdi.');
    return;
  }
  if (!resp.ok || !resp.body) {
    let detail = `HTTP ${resp.status}`;
    try {
      const j = await resp.json();
      detail = j.detail ?? detail;
    } catch { /* ignore */ }
    cb.onError?.(detail);
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line.
      let nlIdx: number;
      while ((nlIdx = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, nlIdx);
        buffer = buffer.slice(nlIdx + 2);
        dispatchFrame(frame, cb);
      }
    }
  } catch (err) {
    if ((err as { name?: string })?.name === 'AbortError') return;
    cb.onError?.(err instanceof Error ? err.message : 'Stream error');
  }
}

function dispatchFrame(frame: string, cb: StreamCallbacks) {
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
  }
  if (!dataLines.length) return;
  let data: Record<string, unknown> = {};
  try {
    data = JSON.parse(dataLines.join('\n'));
  } catch {
    return;
  }

  switch (event) {
    case 'profile_patch': {
      const fields = data.fields as Partial<BusinessProfile> | undefined;
      if (fields && typeof fields === 'object') cb.onProfilePatch?.(fields);
      break;
    }
    case 'tool_call_start': {
      cb.onToolCallStart?.({
        modelId: String(data.model_id ?? ''),
        title: String(data.title ?? data.model_id ?? ''),
        block: (data.block as BlockId) ?? 'A',
      });
      break;
    }
    case 'tool_result': {
      const modelId = String(data.model_id ?? '');
      const meta = MODEL_BY_ID[modelId];
      const pred = (data.prediction as Record<string, unknown> | null) ?? undefined;
      const errMsg = data.error ? String(data.error) : undefined;
      let headline: ModelResult['headline'];
      let spark: Spark | undefined;
      if (meta && pred) {
        try { headline = meta.formatHeadline(pred); } catch { /* leave undefined */ }
        try { spark = meta.buildSpark?.(pred); } catch { /* leave undefined */ }
      }
      const result: ModelResult = {
        modelId,
        block: meta?.block ?? 'A',
        title: meta?.title ?? modelId,
        status: errMsg ? 'error' : 'done',
        isStub: Boolean(data.is_stub),
        latencyMs: typeof data.latency_ms === 'number' ? data.latency_ms : undefined,
        headline,
        spark,
        prediction: pred,
        error: errMsg,
      };
      cb.onToolResult?.(result);
      break;
    }
    case 'text': {
      const delta = String(data.delta ?? '');
      if (delta) cb.onTextDelta?.(delta);
      break;
    }
    case 'done': {
      cb.onDone?.({
        chosenModels: Array.isArray(data.chosen_models) ? (data.chosen_models as string[]) : [],
        totalLatencyMs: typeof data.total_latency_ms === 'number' ? data.total_latency_ms : 0,
        reason: typeof data.reason === 'string' ? data.reason : undefined,
      });
      break;
    }
    case 'error': {
      cb.onError?.(String(data.message ?? 'Unknown error'));
      break;
    }
  }
}

/** Helper: derive the chat history slice we send to the backend. */
export function toBackendHistory(messages: Array<{ role: 'user' | 'assistant'; text?: string }>, maxTurns = 12): ChatHistoryTurn[] {
  return messages
    .filter((m) => typeof m.text === 'string' && m.text.trim().length > 0)
    .slice(-maxTurns)
    .map((m) => ({ role: m.role, content: m.text as string }));
}

// Re-export ModelResult so callers (NotebookLayout) can import it from one place.
export type { ModelResult } from './runner';
