'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { TopBar } from './TopBar';
import { HistoryPanel } from './HistoryPanel';
import { ChatPanel } from './ChatPanel';
import { useConversations } from '@/lib/chat/store';
import { useProfile, getProfileSnapshot } from '@/lib/chat/profile';
import { streamAnswer, toBackendHistory, type ModelResult } from '@/lib/chat/brain';
import { buildRecommendation, REQUIRED_MODEL_IDS } from '@/lib/chat/recommendation';
import { buildAlternativeBusinessBlocks } from '@/lib/chat/alternatives';
import type { AlternativeBusiness, Block, BlockEvidence, EvidenceRow, EvidenceSummary, Message } from '@/lib/chat/types';
import type { CsvSummary } from '@/lib/chat/csv';
import { fetchEvidence } from '@/lib/api';

const EXPLICIT_LOAN_REQUEST_RE =
  /(?:kredit|qarz|loan).{0,40}\d|\d.{0,40}(?:kredit|qarz|loan)/i;

function asksForLoanSizing(text: string): boolean {
  return EXPLICIT_LOAN_REQUEST_RE.test(text);
}

export function NotebookLayout() {
  const conversations = useConversations();
  const {
    active, ensureActive, addMessage, updateMessage,
    newConversation, renameConversation, hydrated, newMessageId,
  } = conversations;
  const { profile, updateProfile } = useProfile();

  const [leftOpen, setLeftOpen] = useState(true);
  const [pending, setPending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const md = window.matchMedia('(min-width: 768px)').matches;
    setLeftOpen(md);
  }, []);

  const send = useCallback(async (text: string, attachment?: CsvSummary) => {
    const conv = ensureActive();
    const controller = new AbortController();
    abortRef.current?.abort();
    abortRef.current = controller;
    setPending(true);

    const userMsg: Message = {
      id: newMessageId(),
      role: 'user',
      text: attachment ? (text || `Analyze ${attachment.name}`) : text,
      createdAt: Date.now(),
      blocks: attachment
        ? [{ kind: 'file-attached', name: attachment.name, sizeBytes: 0, rows: attachment.rows, cols: attachment.cols }]
        : undefined,
    };
    addMessage(conv.id, userMsg);

    const assistantId = newMessageId();
    addMessage(conv.id, { id: assistantId, role: 'assistant', createdAt: Date.now(), pending: true });

    // Live state we accumulate from SSE events. We re-render the assistant
    // message after each event so the user sees streaming progress.
    const results = new Map<string, ModelResult>();
    let textBuf = '';
    let started = false;
    let streamDone = false;
    // When the backend signals reason="no_evidence" on done, we suppress the
    // recommendation/report/data-sources cards entirely — those would be
    // garbage numbers from models that ran against an empty/unmatched profile.
    // Only the refusal text streamed by the backend is shown.
    let noEvidence = false;
    let evidence: {
      rows: EvidenceRow[];
      summary: EvidenceSummary;
      totalExamined: number;
      sources: string[];
      modelsUsed?: string[];
      perBlock?: BlockEvidence[];
      alternatives?: AlternativeBusiness[];
    } | null = null;

    const composeBlocks = (): Block[] => {
      if (noEvidence) return [];
      // Read the LIVE profile here — the LLM may have emitted profile_patch
      // mid-stream, so the closure-captured `profile` is stale by now.
      const live = getProfileSnapshot();
      const ordered = Array.from(results.values());
      const blocks: Block[] = [];
      if (ordered.length) {
        // The recommendation card is a loan-sizing/repayment card, not a bank
        // product card. Product-advice prompts may run credit models for
        // validation, but should not show "So'ralgan vs Tavsiya qilingan"
        // unless the user actually gave a loan amount.
        const anyRequiredPicked = ordered.some((r) =>
          (REQUIRED_MODEL_IDS as readonly string[]).includes(r.modelId),
        );
        if (anyRequiredPicked && asksForLoanSizing(userMsg.text ?? '')) {
          const rec = buildRecommendation(live, ordered, streamDone);
          blocks.push({ kind: 'recommendation', rec });
        }
        blocks.push({
          kind: 'report',
          profile: { region_label: live.region_label, mcc_label: live.mcc_label },
          results: ordered,
        });
        if (evidence) {
          blocks.push(...buildAlternativeBusinessBlocks(live, ordered, {
            summary: evidence.summary,
            alternatives: evidence.alternatives ?? [],
          }));
          blocks.push({
            kind: 'data-sources',
            profile: { region_label: live.region_label, mcc_label: live.mcc_label },
            rows: evidence.rows,
            summary: evidence.summary,
            totalExamined: evidence.totalExamined,
            sources: evidence.sources,
            modelsUsed: evidence.modelsUsed,
            perBlock: evidence.perBlock,
          });
        }
      }
      return blocks;
    };

    const flush = () => {
      updateMessage(conv.id, assistantId, {
        pending: false,
        text: textBuf || undefined,
        blocks: composeBlocks(),
      });
    };

    // History excludes the just-added pending assistant turn.
    const priorMessages = (conv.messages ?? []).concat(userMsg);
    const history = toBackendHistory(
      priorMessages.map((m) => ({ role: m.role, text: m.text })),
    );

    try {
      await streamAnswer(text || (attachment ? `Analyze ${attachment.name}` : ''), history, profile, {
        signal: controller.signal,
        onProfilePatch: (patch) => {
          updateProfile(patch);
        },
        onToolCallStart: (e) => {
          if (!started) { started = true; flush(); }
          results.set(e.modelId, {
            modelId: e.modelId, block: e.block, title: e.title, status: 'running',
          });
          flush();
        },
        onToolResult: (r) => {
          results.set(r.modelId, r);
          flush();
        },
        onTextDelta: (d) => {
          textBuf += d;
          flush();
        },
        onDone: (e) => {
          streamDone = true;
          if (e.reason === 'no_evidence') {
            noEvidence = true;
            flush();
            return;
          }
          flush();
          // Fetch the audit-trail evidence and re-flush once it lands.
          // The chat already streamed in; this is a non-blocking enrichment.
          if (results.size > 0 && !controller.signal.aborted) {
            // Read the LIVE profile — the LLM may have patched it during the
            // stream (e.g. user said "kiyim do'koni" → mcc_code=5651). Without
            // this, evidence would be filtered to the stale starting profile.
            const live = getProfileSnapshot();
            fetchEvidence({
              region_id: live.region_id,
              mcc_code: live.mcc_code,
              monthly_revenue: live.monthly_revenue_estimate,
              initial_investment: live.initial_investment,
              limit: 10,
              // Restrict per-block evidence to the blocks of models the LLM
              // actually chose, so we only show data that was relevant.
              model_ids: e.chosenModels,
            })
              .then((res) => {
                if (controller.signal.aborted) return;
                evidence = {
                  rows: res.rows as unknown as EvidenceRow[],
                  summary: res.summary,
                  totalExamined: res.total_examined,
                  sources: res.sources,
                  modelsUsed: e.chosenModels,
                  perBlock: res.blocks,
                  alternatives: res.alternatives as AlternativeBusiness[],
                };
                flush();
              })
              .catch(() => {
                // Evidence is supplementary — silently skip on failure.
              });
          }
        },
        onError: (msg) => {
          updateMessage(conv.id, assistantId, {
            pending: false,
            text: textBuf || undefined,
            blocks: composeBlocks(),
            error: msg,
          });
        },
      });
    } catch (err) {
      if ((err as { name?: string })?.name !== 'AbortError') {
        updateMessage(conv.id, assistantId, {
          pending: false,
          error: err instanceof Error ? err.message : 'Xatolik yuz berdi.',
        });
      }
    } finally {
      setPending(false);
    }
  }, [profile, addMessage, ensureActive, newMessageId, updateMessage, updateProfile]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setPending(false);
  }, []);

  if (!hydrated) {
    return (
      <div className="h-screen w-full grid place-items-center bg-canvas">
        <div className="w-6 h-6 border-2 border-line border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  const messages = active?.messages ?? [];
  const title = active?.title ?? 'Yangi bloknot';

  return (
    <div className="h-screen w-full flex flex-col bg-canvas">
      <TopBar
        title={title}
        onTitleChange={(t) => active && renameConversation(active.id, t)}
        onNew={() => newConversation()}
        toggleLeft={() => setLeftOpen((v) => !v)}
        leftOpen={leftOpen}
      />

      <div className="flex-1 flex min-h-0 relative">
        <div
          className={`transition-all duration-200 ease-out ${leftOpen ? 'md:w-[300px]' : 'md:w-0'}
            ${leftOpen ? 'fixed md:static inset-y-14 left-0 z-30 w-[280px]' : 'hidden md:block'}
            md:overflow-hidden`}
        >
          {leftOpen && (
            <HistoryPanel
              onClose={() => setLeftOpen(false)}
              items={conversations.items}
              activeId={conversations.activeId}
              hydrated={conversations.hydrated}
              setActiveId={conversations.setActiveId}
              newConversation={conversations.newConversation}
              removeConversation={conversations.removeConversation}
              renameConversation={conversations.renameConversation}
              clearAll={conversations.clearAll}
            />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <ChatPanel
            messages={messages}
            pending={pending}
            onSend={send}
            onStop={stop}
            onSuggestionPick={(s) => send(s)}
          />
        </div>

        {leftOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/40 md:hidden"
            onClick={() => setLeftOpen(false)}
          />
        )}
      </div>
    </div>
  );
}
