'use client';

import { useEffect, useRef, useState, KeyboardEvent } from 'react';
import { Paperclip, Send, Square, X } from 'lucide-react';
import type { CsvSummary } from '@/lib/chat/csv';
import { readCsvFile } from '@/lib/chat/csv';

interface Props {
  onSend: (text: string, attachment?: CsvSummary) => void;
  pending: boolean;
  onStop?: () => void;
  placeholder?: string;
}

export function Composer({ onSend, pending, onStop, placeholder }: Props) {
  const [text, setText] = useState('');
  const [attachment, setAttachment] = useState<CsvSummary | null>(null);
  const [parsing, setParsing] = useState(false);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(220, el.scrollHeight) + 'px';
  }, [text]);

  function send() {
    const t = text.trim();
    if (!t && !attachment) return;
    if (pending) return;
    onSend(t || `Analyze ${attachment?.name}`, attachment ?? undefined);
    setText('');
    setAttachment(null);
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    setParsing(true);
    try {
      const summary = await readCsvFile(f);
      setAttachment(summary);
    } catch {
      // ignore
    } finally {
      setParsing(false);
    }
  }

  return (
    <div className="w-full">
      <div className="rounded-3xl border border-line bg-elev focus-within:border-line-strong transition shadow-soft">
        {attachment && (
          <div className="px-4 pt-3 flex">
            <div className="inline-flex items-center gap-2 rounded-lg border border-line bg-panel pl-2 pr-1 py-1.5 text-xs text-fg">
              <span className="w-5 h-5 rounded bg-accent/10 text-accent grid place-items-center text-[10px] font-bold">CSV</span>
              <span className="truncate max-w-[200px]">{attachment.name}</span>
              <span className="text-muted">· {attachment.rows}×{attachment.cols}</span>
              <button
                onClick={() => setAttachment(null)}
                className="p-1 rounded hover:bg-elev2 text-muted"
                aria-label="Birikmani olib tashlash"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          </div>
        )}

        <textarea
          ref={taRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          placeholder={placeholder ?? 'Istalgan narsani soʻrang — bozor hajmi, prognoz, kredit riski, joylashuv…'}
          className="w-full bg-transparent text-fg placeholder:text-subtle px-4 pt-3.5 pb-2 outline-none text-[15px] leading-relaxed [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        />

        <div className="flex items-center justify-between px-2 pb-2">
          <div className="flex items-center gap-1">
            <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden" onChange={onFile} />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={parsing}
              className="p-2 rounded-full hover:bg-elev2 text-muted transition disabled:opacity-50"
              aria-label="CSV biriktirish"
              title="CSV biriktirish"
            >
              <Paperclip className="w-[18px] h-[18px]" />
            </button>
          </div>

          {pending ? (
            <button
              onClick={onStop}
              className="p-2 rounded-full bg-fg text-canvas hover:opacity-90 transition"
              aria-label="Toʻxtatish"
            >
              <Square className="w-4 h-4" fill="currentColor" />
            </button>
          ) : (
            <button
              onClick={send}
              disabled={!text.trim() && !attachment}
              className="p-2 rounded-full bg-accent text-accent-fg hover:opacity-90 transition disabled:bg-elev2 disabled:text-subtle disabled:cursor-not-allowed"
              aria-label="Yuborish"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
      <div className="text-center text-[11px] text-subtle mt-2">
        BizIQ tahliliy taxminlarni ishlab chiqaradi. Muhim qarorlarni asl maʻlumotlar bilan tasdiqlang.
      </div>
    </div>
  );
}
