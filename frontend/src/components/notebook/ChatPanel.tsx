'use client';

import { forwardRef, useEffect, useRef } from 'react';
import { Sparkles, Bot } from 'lucide-react';
import { MessageBubble } from '@/components/chat/Message';
import { Composer } from '@/components/chat/Composer';
import type { Message } from '@/lib/chat/types';
import type { CsvSummary } from '@/lib/chat/csv';
import { useSources } from '@/lib/chat/sources';
import { ALL_MODELS } from '@/lib/chat/models';

interface Props {
  messages: Message[];
  pending: boolean;
  onSend: (text: string, attachment?: CsvSummary) => void;
  onStop: () => void;
  onSuggestionPick: (s: string) => void;
}

const STARTER_CHIPS = [
  `Faol manba uchun barcha ${ALL_MODELS.length} tahlilni ishga tushiring`,
  'Toshkent va Samarqandni solishtiring',
  'Daromad ±20% bilan qayta ishga tushiring',
  'Modellar katalogini koʻrsating',
];

export const ChatPanel = forwardRef<HTMLDivElement, Props>(function ChatPanel(
  { messages, pending, onSend, onStop, onSuggestionPick },
  ref,
) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastCount = useRef(0);
  const { selected } = useSources();

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    if (messages.length !== lastCount.current) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
      lastCount.current = messages.length;
    }
  }, [messages.length]);

  return (
    <section ref={ref} className="h-full flex flex-col bg-canvas min-w-0">
      <div className="flex items-center justify-between px-5 h-14 border-b border-line">
        <div className="flex items-center gap-2 text-sm">
          <Bot className="w-4 h-4 text-accent" />
          <span className="text-fg font-medium">Suhbat</span>
          <span className="text-muted text-xs">
            · {selected.length} ta manba tanlangan
          </span>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <EmptyChat onPick={onSuggestionPick} />
        ) : (
          <div className="max-w-3xl mx-auto py-6 md:py-10 px-4 md:px-6 space-y-6">
            {messages.map((m) => (
              <MessageBubble key={m.id} msg={m} onSuggestionPick={onSuggestionPick} />
            ))}
          </div>
        )}
      </div>

      <div className="px-3 md:px-6 pb-4 pt-2 bg-gradient-to-t from-canvas via-canvas to-transparent">
        <div className="max-w-3xl mx-auto">
          {messages.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2 justify-center">
              {STARTER_CHIPS.slice(0, 3).map((c) => (
                <button
                  key={c}
                  onClick={() => onSuggestionPick(c)}
                  className="text-[11px] px-2.5 py-1 rounded-full border border-line bg-elev hover:bg-panel text-muted hover:text-fg transition"
                >
                  {c}
                </button>
              ))}
            </div>
          )}
          <Composer onSend={onSend} pending={pending} onStop={onStop} />
        </div>
      </div>
    </section>
  );
});

function EmptyChat({ onPick }: { onPick: (s: string) => void }) {
  return (
    <div className="h-full grid place-items-center px-6 py-10">
      <div className="max-w-2xl w-full text-center fade-in">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-400 to-violet-600 mb-4 shadow-soft">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <h1 className="text-2xl md:text-3xl font-semibold text-fg tracking-tight">
          Biznesingiz haqida suhbat boshlang
        </h1>
        <p className="text-muted mt-2 text-sm">
          Chap tarafdan manbani tanlang, oʻng tarafda Studiya vositasini bosing yoki shu yerga savol yozing.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-8 text-left">
          {STARTER_CHIPS.map((c) => (
            <button
              key={c}
              onClick={() => onPick(c)}
              className="rounded-xl border border-line bg-elev hover:bg-panel hover:border-line-strong px-4 py-3 text-sm text-fg transition"
            >
              {c}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
