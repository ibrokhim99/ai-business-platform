'use client';

import { Sun, Moon, Monitor } from 'lucide-react';
import { useState } from 'react';
import { useTheme, type ThemeMode } from '@/lib/theme';

const OPTIONS: Array<{ value: ThemeMode; label: string; Icon: typeof Sun }> = [
  { value: 'light',  label: 'Yorugʻ',  Icon: Sun },
  { value: 'dark',   label: 'Qorongʻi', Icon: Moon },
  { value: 'system', label: 'Tizim',    Icon: Monitor },
];

export function ThemeToggle() {
  const { mode, effective, setMode } = useTheme();
  const [open, setOpen] = useState(false);
  const Active = effective === 'dark' ? Moon : Sun;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="p-2 rounded-lg hover:bg-elev2 text-muted hover:text-fg transition focus-ring"
        aria-label="Mavzu"
        title="Mavzu"
      >
        <Active className="w-[18px] h-[18px]" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-[60]" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-[70] min-w-[160px] rounded-xl border border-line bg-elev shadow-pop py-1">
            {OPTIONS.map((o) => {
              const Icon = o.Icon;
              return (
                <button
                  key={o.value}
                  onClick={() => { setMode(o.value); setOpen(false); }}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-fg hover:bg-panel ${
                    mode === o.value ? 'bg-accent-soft text-accent' : ''
                  }`}
                >
                  <Icon className="w-4 h-4" /> {o.label}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

export function QuickThemeToggle() {
  const { toggle, effective } = useTheme();
  const Icon = effective === 'dark' ? Sun : Moon;
  return (
    <button
      onClick={toggle}
      className="p-2 rounded-lg hover:bg-elev2 text-muted hover:text-fg transition focus-ring"
      aria-label="Mavzuni almashtirish"
      title={`${effective === 'dark' ? 'Yorugʻ' : 'Qorongʻi'} rejimga oʻtish`}
    >
      <Icon className="w-[18px] h-[18px]" />
    </button>
  );
}
