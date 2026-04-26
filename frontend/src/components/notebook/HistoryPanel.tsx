'use client';

import { useState } from 'react';
import { Plus, MoreVertical, Trash2, X, MessageSquare, History, Pencil, Check } from 'lucide-react';
import type { Conversation } from '@/lib/chat/types';

interface Props {
  onClose: () => void;
  // Lifted state from NotebookLayout's useConversations() — keeps a single
  // store instance so this panel and the chat stay in sync.
  items: Conversation[];
  activeId: string | null;
  hydrated: boolean;
  setActiveId: (id: string | null) => void;
  newConversation: () => Conversation;
  removeConversation: (id: string) => void;
  renameConversation: (id: string, title: string) => void;
  clearAll: () => void;
}

function firstUserPrompt(c: Conversation): string {
  const firstUser = c.messages.find((m) => m.role === 'user' && m.text);
  return firstUser?.text?.trim() || c.title || 'Yangi suhbat';
}

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const min = Math.floor(diff / 60_000);
  if (min < 1) return 'hozir';
  if (min < 60) return `${min} daq oldin`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} soat oldin`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day} kun oldin`;
  return new Date(ts).toLocaleDateString('uz-UZ', { day: 'numeric', month: 'short' });
}

export function HistoryPanel({
  onClose,
  items, activeId, hydrated,
  setActiveId, newConversation, removeConversation, renameConversation, clearAll,
}: Props) {
  // Newest first; conversations with messages bubble above empty drafts.
  const sorted = [...items].sort((a, b) => {
    const aHas = a.messages.length > 0 ? 1 : 0;
    const bHas = b.messages.length > 0 ? 1 : 0;
    if (aHas !== bHas) return bHas - aHas;
    return b.updatedAt - a.updatedAt;
  });

  return (
    <aside className="h-full flex flex-col bg-panel border-r border-line">
      <div className="flex items-center justify-between px-4 h-14 border-b border-line">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-muted" />
          <h2 className="text-sm font-semibold text-fg">Suhbatlar tarixi</h2>
          {items.length > 0 && (
            <span className="text-[11px] text-muted bg-elev2 px-1.5 py-0.5 rounded-full">{items.length}</span>
          )}
        </div>
        <button onClick={onClose} className="md:hidden p-1.5 rounded-lg hover:bg-elev2 text-muted" aria-label="Yopish">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="px-3 pt-3">
        <button
          onClick={() => newConversation()}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border border-line bg-elev hover:bg-elev2 text-sm font-medium text-fg transition shadow-soft"
        >
          <Plus className="w-4 h-4" /> Yangi suhbat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 mt-3 pb-3">
        {!hydrated ? (
          <div className="px-3 py-8 text-center text-xs text-muted">Yuklanmoqda…</div>
        ) : sorted.length === 0 ? (
          <div className="px-4 py-12 text-center">
            <MessageSquare className="w-6 h-6 text-subtle mx-auto mb-2" />
            <p className="text-xs text-muted">Hozircha tarix yoʻq. Birinchi savolingizni yozing.</p>
          </div>
        ) : (
          sorted.map((c) => (
            <HistoryRow
              key={c.id}
              conv={c}
              active={c.id === activeId}
              onSelect={() => setActiveId(c.id)}
              onRemove={() => removeConversation(c.id)}
              onRename={(t) => renameConversation(c.id, t)}
            />
          ))
        )}
      </div>

      {items.length > 0 && (
        <div className="border-t border-line px-3 py-2.5">
          <button
            onClick={() => {
              if (window.confirm('Barcha suhbatlar tarixini oʻchirishni xohlaysizmi?')) clearAll();
            }}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs text-muted hover:bg-elev2 hover:text-rose-500 transition"
          >
            <Trash2 className="w-3.5 h-3.5" /> Tarixni tozalash
          </button>
        </div>
      )}
    </aside>
  );
}

function HistoryRow({
  conv, active, onSelect, onRemove, onRename,
}: {
  conv: Conversation;
  active: boolean;
  onSelect: () => void;
  onRemove: () => void;
  onRename: (title: string) => void;
}) {
  const [menu, setMenu] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const prompt = firstUserPrompt(conv);
  const msgCount = conv.messages.length;

  function commit() {
    const next = draft.trim();
    if (next && next !== conv.title) onRename(next);
    setEditing(false);
  }

  return (
    <div
      className={`group flex items-start gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition ${
        active ? 'bg-accent-soft' : 'hover:bg-elev2'
      }`}
      onClick={() => !editing && onSelect()}
    >
      <div className={`w-7 h-7 rounded-md grid place-items-center flex-shrink-0 mt-0.5 ${
        active ? 'bg-accent/15 text-accent' : 'bg-elev2 text-muted'
      }`}>
        <MessageSquare className="w-3.5 h-3.5" />
      </div>

      <div className="flex-1 min-w-0">
        {editing ? (
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') commit();
                if (e.key === 'Escape') setEditing(false);
              }}
              onBlur={commit}
              className="flex-1 text-sm bg-elev border border-line rounded px-1.5 py-0.5 text-fg focus:outline-none focus:border-accent"
            />
            <button onClick={commit} className="p-0.5 rounded hover:bg-elev2 text-accent">
              <Check className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <>
            <div className={`text-sm truncate ${active ? 'text-fg font-medium' : 'text-fg/90'}`}>
              {prompt}
            </div>
            <div className="text-[11px] text-muted truncate">
              {msgCount > 0 ? `${Math.ceil(msgCount / 2)} ta savol · ${relativeTime(conv.updatedAt)}` : 'Boʻsh suhbat'}
            </div>
          </>
        )}
      </div>

      <div className="relative" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => setMenu((v) => !v)}
          className="p-1 rounded hover:bg-elev2 text-muted opacity-0 group-hover:opacity-100 transition"
          aria-label="Suhbat amallari"
        >
          <MoreVertical className="w-3.5 h-3.5" />
        </button>
        {menu && (
          <>
            <div className="fixed inset-0 z-[60]" onClick={() => setMenu(false)} />
            <div className="absolute right-0 top-full mt-1 z-[70] min-w-[160px] rounded-lg border border-line bg-elev shadow-pop py-1">
              <button
                onClick={() => {
                  setDraft(conv.title);
                  setEditing(true);
                  setMenu(false);
                }}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-fg hover:bg-panel"
              >
                <Pencil className="w-3.5 h-3.5" /> Nomini oʻzgartirish
              </button>
              <button
                onClick={() => { onRemove(); setMenu(false); }}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-rose-500 hover:bg-panel"
              >
                <Trash2 className="w-3.5 h-3.5" /> Oʻchirish
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
