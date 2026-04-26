'use client';

import { useState } from 'react';
import { ChevronDown, LogOut, PenSquare, Share2, Settings, PanelLeft } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { ThemeToggle } from './ThemeToggle';

interface Props {
  title: string;
  onTitleChange?: (t: string) => void;
  onNew: () => void;
  toggleLeft: () => void;
  leftOpen: boolean;
}

export function TopBar({ title, onTitleChange, onNew, toggleLeft, leftOpen }: Props) {
  const { user, logout } = useAuth();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title);
  const [accountOpen, setAccountOpen] = useState(false);

  function commit() {
    setEditing(false);
    if (draft.trim() && draft !== title) onTitleChange?.(draft.trim());
  }

  return (
    <header className="flex items-center justify-between px-3 md:px-4 h-14 border-b border-line bg-canvas/95 backdrop-blur sticky top-0 z-50">
      <div className="flex items-center gap-2 min-w-0">
        <button
          onClick={toggleLeft}
          className={`p-2 rounded-lg hover:bg-elev2 transition ${leftOpen ? 'text-fg' : 'text-muted'}`}
          aria-label="Manbalarni ko'rsatish"
          title="Manbalar paneli"
        >
          <PanelLeft className="w-[18px] h-[18px]" />
        </button>

        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-400 to-violet-600 grid place-items-center shrink-0 shadow-soft">
            <span className="text-white font-bold text-xs tracking-tight">B</span>
          </div>
          {editing ? (
            <input
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={commit}
              onKeyDown={(e) => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') { setDraft(title); setEditing(false); } }}
              className="bg-transparent text-sm font-medium text-fg outline-none border-b border-accent w-[260px] max-w-[60vw]"
            />
          ) : (
            <button
              onClick={() => { setDraft(title); setEditing(true); }}
              className="text-sm font-medium text-fg hover:text-accent truncate max-w-[40vw] md:max-w-[50vw] text-left"
              title="Bloknotni qayta nomlash"
            >
              {title}
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={onNew}
          className="hidden md:inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-fg hover:bg-elev2 transition"
        >
          <PenSquare className="w-4 h-4" /> Yangi
        </button>
        <button className="hidden md:inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-fg hover:bg-elev2 transition">
          <Share2 className="w-4 h-4" /> Ulashish
        </button>
        <button className="p-2 rounded-lg hover:bg-elev2 text-muted hover:text-fg transition" aria-label="Sozlamalar">
          <Settings className="w-[18px] h-[18px]" />
        </button>

        <ThemeToggle />

        <div className="relative ml-1">
          <button
            onClick={() => setAccountOpen((v) => !v)}
            className="flex items-center gap-1.5 pl-1.5 pr-2 py-1 rounded-full hover:bg-elev2 transition"
          >
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-violet-700 text-white text-xs font-semibold grid place-items-center">
              {(user?.email ?? 'M')[0].toUpperCase()}
            </div>
            <ChevronDown className={`w-3.5 h-3.5 text-muted transition ${accountOpen ? 'rotate-180' : ''}`} />
          </button>
          {accountOpen && (
            <>
              <div className="fixed inset-0 z-[60]" onClick={() => setAccountOpen(false)} />
              <div className="absolute right-0 top-full mt-1 z-[70] min-w-[220px] rounded-xl border border-line bg-elev shadow-pop py-1">
                <div className="px-3 py-2 border-b border-line">
                  <div className="text-sm text-fg truncate">{user?.email ?? 'Mehmon'}</div>
                  <div className="text-[11px] text-muted capitalize">{user?.role ?? 'tashrif buyuruvchi'}</div>
                </div>
                <button
                  onClick={() => { logout(); setAccountOpen(false); }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-fg hover:bg-panel"
                >
                  <LogOut className="w-4 h-4" /> Chiqish
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
