'use client';

import { useState } from 'react';
import { Database, ChevronDown, CheckCircle2, AlertTriangle, XCircle, FileText } from 'lucide-react';
import type { BlockEvidence, EvidenceRow, EvidenceSummary } from '@/lib/chat/types';
import { fmtMoney, fmtPct } from '@/lib/chat/format';

interface Props {
  profile: { region_label: string; mcc_label: string };
  rows: EvidenceRow[];
  summary: EvidenceSummary;
  totalExamined: number;
  sources: string[];
  modelsUsed?: string[];
  perBlock?: BlockEvidence[];
}

const BLOCK_TITLES: Record<string, string> = {
  A: 'Bozor tahlili',
  B: 'Prognozlash',
  C: 'Joylashuv',
  D: 'Moliyaviy',
  E: 'Raqobat',
  F: 'Kredit',
  G: 'Mijoz / Sotsial',
  H: 'Marketing',
  I: 'Operatsiyalar',
  J: 'Firibgarlik',
};

function formatStatValue(key: string, val: number): string {
  if (Math.abs(val) >= 1_000_000) return `${(val / 1_000_000).toFixed(2)}M`;
  if (Math.abs(val) >= 1_000) return val.toLocaleString('en', { maximumFractionDigits: 0 });
  if (key.endsWith('_pct') || key.includes('rate') || key === 'service_level') return `${val.toFixed(1)}%`;
  if (Math.abs(val) < 1 && val !== 0) return val.toFixed(3);
  return val.toFixed(1);
}

function PerBlockSection({ b }: { b: BlockEvidence }) {
  const [open, setOpen] = useState(false);
  const statEntries = Object.entries(b.stats);
  return (
    <div className="rounded-lg border border-line bg-panel/30 fade-in">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 px-3 py-2 text-left hover:bg-panel/60 transition rounded-lg"
        aria-expanded={open}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="inline-flex w-6 h-6 rounded bg-accent/10 border border-accent/20 items-center justify-center text-[11px] font-semibold text-accent flex-shrink-0">
            {b.block}
          </span>
          <div className="min-w-0">
            <div className="text-sm font-medium text-fg truncate">{BLOCK_TITLES[b.block] ?? b.block}</div>
            <div className="text-[11px] text-muted truncate">
              {b.matched_count.toLocaleString()} / {b.total_examined.toLocaleString()} mos qator · <code>{b.source}</code>
            </div>
          </div>
        </div>
        <ChevronDown className={`w-4 h-4 text-muted flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="border-t border-line px-3 py-3 space-y-3">
          {statEntries.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {statEntries.slice(0, 9).map(([k, v]) => (
                <div key={k} className="rounded border border-line bg-elev px-2 py-1.5 text-[11px]">
                  <div className="text-muted truncate">{k}</div>
                  <div className="text-fg font-medium tabular-nums">{formatStatValue(k, v)}</div>
                </div>
              ))}
            </div>
          )}
          {b.sample_rows.length > 0 && (
            <div className="overflow-x-auto rounded border border-line">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="bg-panel border-b border-line">
                    {Object.keys(b.sample_rows[0]).slice(0, 8).map((k) => (
                      <th key={k} className="text-left px-2 py-1.5 text-[10px] uppercase tracking-wider text-muted font-medium">{k}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {b.sample_rows.slice(0, 5).map((row, i) => (
                    <tr key={i} className="border-b border-line last:border-b-0 hover:bg-panel/40">
                      {Object.keys(b.sample_rows[0]).slice(0, 8).map((k) => (
                        <td key={k} className="px-2 py-1.5 text-fg truncate max-w-[160px]">
                          {String(row[k] ?? '—')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const OUTCOME_META: Record<EvidenceRow['outcome'], { label: string; cls: string; Icon: typeof CheckCircle2 }> = {
  succeeded:  { label: 'Muvaffaqiyatli', cls: 'text-emerald-500',  Icon: CheckCircle2  },
  struggling: { label: 'Qiyin holatda',  cls: 'text-amber-500',    Icon: AlertTriangle },
  failed:     { label: 'Muvaffaqiyatsiz',cls: 'text-rose-500',     Icon: XCircle       },
};

export function DataSourcesBlock({ profile, rows, summary, totalExamined, sources, modelsUsed, perBlock }: Props) {
  const [open, setOpen] = useState(false);

  const totalClassified = summary.succeeded + summary.struggling + summary.failed;
  const successPct = totalClassified ? Math.round((summary.succeeded / totalClassified) * 100) : 0;

  return (
    <div className="rounded-2xl border border-line bg-elev fade-in">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-panel/60 transition rounded-2xl"
        aria-expanded={open}
      >
        <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center flex-shrink-0">
          <Database className="w-4 h-4 text-accent" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-fg">
            Bu javob qaysi maʻlumotlarga asoslangan?
          </div>
          <div className="text-xs text-muted mt-0.5">
            {totalExamined.toLocaleString()} ta oʻxshash biznes koʻrib chiqildi · {successPct}% muvaffaqiyatli
          </div>
        </div>
        <ChevronDown className={`w-4 h-4 text-muted transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="border-t border-line px-4 py-3 space-y-3">
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-3 py-2">
              <div className="flex items-center gap-1.5 text-emerald-500 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" /> Muvaffaqiyatli
              </div>
              <div className="text-fg text-base font-semibold mt-1">{summary.succeeded}</div>
            </div>
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2">
              <div className="flex items-center gap-1.5 text-amber-500 font-medium">
                <AlertTriangle className="w-3.5 h-3.5" /> Qiyin holatda
              </div>
              <div className="text-fg text-base font-semibold mt-1">{summary.struggling}</div>
            </div>
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/5 px-3 py-2">
              <div className="flex items-center gap-1.5 text-rose-500 font-medium">
                <XCircle className="w-3.5 h-3.5" /> Muvaffaqiyatsiz
              </div>
              <div className="text-fg text-base font-semibold mt-1">{summary.failed}</div>
            </div>
          </div>

          <div className="text-xs text-muted">
            <span className="font-medium text-fg">{profile.mcc_label}</span> · {profile.region_label} —
            mediana daromad <span className="text-fg">{fmtMoney(summary.median_revenue)}</span>,
            oʻrtacha oʻsish <span className="text-fg">{fmtPct(summary.median_growth_pct, 1)}</span>.
          </div>

          {rows.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-line">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-panel border-b border-line">
                    <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted font-medium">Soha</th>
                    <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted font-medium">Hudud</th>
                    <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider text-muted font-medium">Oylik daromad</th>
                    <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider text-muted font-medium">Sof oqim</th>
                    <th className="text-right px-3 py-2 text-[10px] uppercase tracking-wider text-muted font-medium">Oʻsish</th>
                    <th className="text-left px-3 py-2 text-[10px] uppercase tracking-wider text-muted font-medium">Natija</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => {
                    const meta = OUTCOME_META[r.outcome];
                    const Icon = meta.Icon;
                    return (
                      <tr key={i} className="border-b border-line last:border-b-0 hover:bg-panel/40">
                        <td className="px-3 py-2 text-fg">{r.niche_label}</td>
                        <td className="px-3 py-2 text-muted">{r.region_id}</td>
                        <td className="px-3 py-2 text-right text-fg tabular-nums">{fmtMoney(r.monthly_revenue)}</td>
                        <td className={`px-3 py-2 text-right tabular-nums ${r.monthly_net_cash_flow >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                          {fmtMoney(r.monthly_net_cash_flow)}
                        </td>
                        <td className={`px-3 py-2 text-right tabular-nums ${r.growth_rate_pct >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                          {fmtPct(r.growth_rate_pct, 1)}
                        </td>
                        <td className={`px-3 py-2 ${meta.cls}`}>
                          <span className="inline-flex items-center gap-1">
                            <Icon className="w-3 h-3" /> {meta.label}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {modelsUsed && modelsUsed.length > 0 && (
            <div className="text-[11px] text-muted">
              <span className="font-medium text-fg">{modelsUsed.length} ta ML model</span> ushbu maʻlumotlardan foydalandi:{' '}
              {modelsUsed.slice(0, 8).join(', ')}{modelsUsed.length > 8 ? `, +${modelsUsed.length - 8}` : ''}
            </div>
          )}

          {perBlock && perBlock.length > 0 && (
            <div className="space-y-2 pt-1">
              <div className="text-[11px] font-medium text-fg flex items-center gap-1.5">
                <FileText className="w-3 h-3" />
                Ishlatilgan dataset qatorlari (har bir blok uchun)
              </div>
              <div className="space-y-1.5">
                {perBlock.map((b) => <PerBlockSection key={b.block} b={b} />)}
              </div>
            </div>
          )}

          {sources.length > 0 && (
            <div className="text-[11px] text-muted">
              <div>Manba:</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {sources.map((s) => (
                  <code key={s} className="px-1.5 py-0.5 rounded bg-panel border border-line text-[10px]">
                    {s}
                  </code>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
