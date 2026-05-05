'use client';

import { useRef, useState } from 'react';
import { Plus, MoreVertical, Compass, Database, FileSpreadsheet, Briefcase, Trash2, X } from 'lucide-react';
import { useSources, type Source } from '@/lib/chat/sources';
import { readCsvFile } from '@/lib/chat/csv';

interface Props {
  onClose: () => void;
}

export function SourcesPanel({ onClose }: Props) {
  const { items, hydrated, toggle, remove, add, selected } = useSources();
  const [adding, setAdding] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const allChecked = items.length > 0 && items.every((s) => s.selected);

  function selectAll(checked: boolean) {
    items.forEach((s) => {
      if (s.selected !== checked) toggle(s.id);
    });
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    const summary = await readCsvFile(f);
    add({
      type: 'csv',
      name: summary.name,
      subtitle: `${summary.rows} qator · ${summary.cols} ustun`,
      rows: summary.rows,
      cols: summary.cols,
      selected: true,
      context: `CSV ${summary.name} — ${summary.rows} qator, ustunlar: ${summary.headers.join(', ')}.`,
    });
  }

  return (
    <aside className="h-full flex flex-col bg-panel border-r border-line">
      <div className="flex items-center justify-between px-4 h-14 border-b border-line">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-muted" />
          <h2 className="text-sm font-semibold text-fg">Manbalar</h2>
          {selected.length > 0 && (
            <span className="text-[11px] text-muted bg-elev2 px-1.5 py-0.5 rounded-full">{selected.length}</span>
          )}
        </div>
        <button onClick={onClose} className="md:hidden p-1.5 rounded-lg hover:bg-elev2 text-muted" aria-label="Yopish">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="px-3 pt-3 flex flex-col gap-2">
        <button
          onClick={() => setAdding(true)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border border-line bg-elev hover:bg-elev2 text-sm font-medium text-fg transition shadow-soft"
        >
          <Plus className="w-4 h-4" /> Manba qoʻshish
        </button>
        <button className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-muted hover:bg-elev2 transition">
          <Compass className="w-4 h-4" /> Manba topish
        </button>
      </div>

      {items.length > 0 && (
        <div className="px-4 mt-2 mb-1 flex items-center justify-between">
          <label className="flex items-center gap-2 text-xs text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={allChecked}
              onChange={(e) => selectAll(e.target.checked)}
              className="accent-accent w-3.5 h-3.5"
            />
            Hammasini tanlash
          </label>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {!hydrated ? (
          <div className="px-3 py-8 text-center text-xs text-muted">Yuklanmoqda…</div>
        ) : items.length === 0 ? (
          <div className="px-4 py-12 text-center">
            <Briefcase className="w-6 h-6 text-subtle mx-auto mb-2" />
            <p className="text-xs text-muted">Manbalar yoʻq. Profil qoʻshing yoki CSV yuklang.</p>
          </div>
        ) : (
          items.map((s) => (
            <SourceRow key={s.id} source={s} onToggle={() => toggle(s.id)} onRemove={() => remove(s.id)} />
          ))
        )}
      </div>

      <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden" onChange={onFile} />

      {adding && (
        <AddSourceDialog
          onClose={() => setAdding(false)}
          onPickProfile={(p) => { add(p); setAdding(false); }}
          onUpload={() => { setAdding(false); fileRef.current?.click(); }}
        />
      )}
    </aside>
  );
}

function SourceRow({ source, onToggle, onRemove }: { source: Source; onToggle: () => void; onRemove: () => void }) {
  const [menu, setMenu] = useState(false);
  const Icon = source.type === 'csv' ? FileSpreadsheet : Briefcase;
  return (
    <div className={`group flex items-center gap-2 px-2 py-2 rounded-lg ${source.selected ? 'bg-accent-soft' : 'hover:bg-elev2'} transition`}>
      <input
        type="checkbox"
        checked={source.selected}
        onChange={onToggle}
        className="accent-accent w-4 h-4 flex-shrink-0"
      />
      <div className={`w-7 h-7 rounded-md grid place-items-center flex-shrink-0 ${source.type === 'csv' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-violet-500/10 text-violet-500'}`}>
        <Icon className="w-3.5 h-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className={`text-sm truncate ${source.selected ? 'text-fg font-medium' : 'text-fg/90'}`}>{source.name}</div>
        {source.subtitle && <div className="text-[11px] text-muted truncate">{source.subtitle}</div>}
      </div>
      <div className="relative">
        <button
          onClick={() => setMenu((v) => !v)}
          className="p-1 rounded hover:bg-elev2 text-muted opacity-0 group-hover:opacity-100 transition"
          aria-label="Manba amallari"
        >
          <MoreVertical className="w-3.5 h-3.5" />
        </button>
        {menu && (
          <>
            <div className="fixed inset-0 z-[60]" onClick={() => setMenu(false)} />
            <div className="absolute right-0 top-full mt-1 z-[70] min-w-[140px] rounded-lg border border-line bg-elev shadow-pop py-1">
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

const PRESETS: Array<Omit<Source, 'id' | 'createdAt'>> = [
  { type: 'profile', name: 'Kafe — Toshkent',          subtitle: 'MCC 5812 · Yunusobod',  context: 'Kafe (MCC 5812), Toshkent (Yunusobod).',         region_id: 'tashkent-01',  mcc_code: '5812', monthly_revenue: 15_000, initial_investment: 50_000,  selected: true },
  { type: 'profile', name: 'Oziq-ovqat — Samarqand',   subtitle: 'MCC 5411',              context: 'Oziq-ovqat doʻkoni (MCC 5411), Samarqand.',      region_id: 'samarkand-01', mcc_code: '5411', monthly_revenue: 22_000, initial_investment: 80_000,  selected: true },
  { type: 'profile', name: 'Mehmonxona — Buxoro',      subtitle: 'MCC 7011',              context: 'Butik mehmonxona (MCC 7011), Buxoro.',           region_id: 'bukhara-01',   mcc_code: '7011', monthly_revenue: 18_000, initial_investment: 220_000, selected: true },
  { type: 'profile', name: 'Dorixona — Fargʻona',       subtitle: 'MCC 5912',              context: 'Dorixona (MCC 5912), Fargʻona.',                region_id: 'fergana-01',   mcc_code: '5912', monthly_revenue: 8_000,  initial_investment: 25_000,  selected: true },
  { type: 'profile', name: 'Tez ovqatlanish — Andijon', subtitle: 'MCC 5814',             context: 'Tez ovqat (MCC 5814), Andijon.',                 region_id: 'andijan-01',   mcc_code: '5814', monthly_revenue: 12_000, initial_investment: 40_000,  selected: true },
  { type: 'profile', name: 'Kiyim doʻkoni — Namangan',  subtitle: 'MCC 5651',             context: 'Oilaviy kiyim doʻkoni (MCC 5651), Namangan.',    region_id: 'namangan-01',  mcc_code: '5651', monthly_revenue: 10_000, initial_investment: 35_000,  selected: true },
];

function AddSourceDialog({
  onClose, onPickProfile, onUpload,
}: { onClose: () => void; onPickProfile: (s: Omit<Source, 'id' | 'createdAt'>) => void; onUpload: () => void }) {
  return (
    <div className="fixed inset-0 z-[100] grid place-items-center bg-black/40 backdrop-blur-sm fade-in" onClick={onClose}>
      <div
        className="w-[92vw] max-w-lg rounded-2xl bg-elev border border-line shadow-pop p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-fg">Manba qoʻshish</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-elev2 text-muted">
            <X className="w-4 h-4" />
          </button>
        </div>

        <button
          onClick={onUpload}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-xl border border-dashed border-line-strong hover:border-accent hover:bg-accent-soft text-left transition mb-4"
        >
          <FileSpreadsheet className="w-5 h-5 text-accent" />
          <div>
            <div className="text-sm font-medium text-fg">CSV yuklash</div>
            <div className="text-xs text-muted">Tahlil uchun maʻlumot faylini tashlang</div>
          </div>
        </button>

        <div className="text-[11px] uppercase tracking-wider text-muted mb-2">Yoki namuna profil tanlang</div>
        <div className="grid grid-cols-1 gap-1.5 max-h-[280px] overflow-y-auto pr-1">
          {PRESETS.map((p) => (
            <button
              key={p.name}
              onClick={() => onPickProfile(p)}
              className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-panel text-left transition"
            >
              <div className="w-7 h-7 rounded-md bg-violet-500/10 text-violet-500 grid place-items-center">
                <Briefcase className="w-3.5 h-3.5" />
              </div>
              <div className="flex-1">
                <div className="text-sm text-fg">{p.name}</div>
                <div className="text-[11px] text-muted">{p.subtitle}</div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
