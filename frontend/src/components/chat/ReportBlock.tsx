'use client';

import { useMemo, useState } from 'react';
import { ChevronDown, CheckCircle2, AlertCircle, Loader2, Circle } from 'lucide-react';
import { BLOCK_META, type BlockId } from '@/lib/chat/models';
import type { ModelResult } from '@/lib/chat/runner';

interface Props {
  profile: { region_label: string; mcc_label: string };
  results: ModelResult[];
}

const BLOCK_ORDER: BlockId[] = ['A', 'B', 'C', 'D', 'E', 'F', 'G'];

export function ReportBlock({ profile, results }: Props) {
  const summary = useMemo(() => {
    const total = results.length;
    const done = results.filter((r) => r.status === 'done').length;
    const running = results.filter((r) => r.status === 'running').length;
    const errored = results.filter((r) => r.status === 'error').length;
    const stub = results.filter((r) => r.isStub).length;
    return { total, done, running, errored, stub, pct: total ? (done / total) * 100 : 0 };
  }, [results]);

  const grouped = useMemo(() => {
    const m: Record<BlockId, ModelResult[]> = { A: [], B: [], C: [], D: [], E: [], F: [], G: [], H: [], I: [], J: [] };
    for (const r of results) m[r.block].push(r);
    return m;
  }, [results]);

  return (
    <div className="rounded-2xl border border-line bg-elev overflow-hidden fade-in">
      {/* Report header */}
      <div className="px-4 md:px-5 py-4 border-b border-line bg-gradient-to-r from-accent-soft via-transparent to-transparent">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-muted">Toʻliq tahlil</div>
            <div className="text-base md:text-lg font-semibold text-fg mt-0.5">
              {profile.mcc_label} <span className="text-muted">·</span> {profile.region_label}
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted">
            <span className="inline-flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> {summary.done}/{summary.total}</span>
            {summary.running > 0 && (
              <span className="inline-flex items-center gap-1"><Loader2 className="w-3.5 h-3.5 animate-spin text-accent" /> {summary.running}</span>
            )}
            {summary.errored > 0 && (
              <span className="inline-flex items-center gap-1"><AlertCircle className="w-3.5 h-3.5 text-rose-500" /> {summary.errored}</span>
            )}
            {summary.stub > 0 && summary.done > 0 && (
              <span className="text-subtle">· {summary.stub} ta sintetik</span>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-3 h-1.5 w-full bg-panel rounded-full overflow-hidden">
          <div
            className="h-full bg-accent transition-all duration-500"
            style={{ width: `${summary.pct}%` }}
          />
        </div>
      </div>

      {/* Sections */}
      <div className="divide-y divide-line">
        {BLOCK_ORDER.map((id) => (
          <Section key={id} block={id} items={grouped[id]} />
        ))}
      </div>
    </div>
  );
}

function Section({ block, items }: { block: BlockId; items: ModelResult[] }) {
  const [open, setOpen] = useState(true);
  const meta = BLOCK_META[block];
  const done = items.filter((i) => i.status === 'done').length;
  const errored = items.filter((i) => i.status === 'error').length;
  const accent = meta.color.split(' ').find((c) => c.startsWith('text-')) ?? 'text-accent';

  return (
    <div className="bg-elev">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 px-4 md:px-5 py-3 hover:bg-panel transition"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${meta.color} grid place-items-center font-bold text-sm shrink-0`}>
            {block}
          </div>
          <div className="min-w-0 text-left">
            <div className="text-sm font-semibold text-fg truncate">{meta.title}</div>
            <div className="text-[11px] text-muted truncate">{meta.subtitle}</div>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted shrink-0">
          <span className={accent}>{done}</span>
          <span>/</span>
          <span>{items.length}</span>
          {errored > 0 && <span className="text-rose-500">· {errored} xato</span>}
          <ChevronDown className={`w-4 h-4 text-muted transition ${open ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {open && (
        <div className="px-3 md:px-5 pb-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {items.map((r) => <ModelCard key={r.modelId} r={r} />)}
        </div>
      )}
    </div>
  );
}

function ModelCard({ r }: { r: ModelResult }) {
  const tone = r.headline?.tone;
  const valueClass =
    tone === 'pos' ? 'text-emerald-500' :
    tone === 'neg' ? 'text-rose-500' : 'text-fg';

  return (
    <div className="rounded-xl border border-line bg-panel/40 p-3 hover:border-line-strong transition relative overflow-hidden">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider text-subtle">{r.modelId}</div>
          <div className="text-[12.5px] font-medium text-fg truncate" title={r.title}>{r.title}</div>
        </div>
        <StatusDot status={r.status} />
      </div>

      {r.status === 'done' && r.headline ? (
        <>
          <div className="text-[10px] text-muted">{r.headline.label}</div>
          <div className={`text-[18px] font-semibold leading-tight ${valueClass}`}>{r.headline.value}</div>
          {r.spark && <Sparkline spark={r.spark} />}
          {(r.isStub || r.latencyMs) && (
            <div className="mt-2 flex items-center gap-2 text-[10px] text-subtle">
              {r.isStub && <span className="px-1.5 py-0.5 rounded bg-elev2 text-muted">sintetik</span>}
              {r.latencyMs !== undefined && <span>{r.latencyMs}ms</span>}
            </div>
          )}
        </>
      ) : r.status === 'error' ? (
        <div className="text-[12px] text-rose-500 mt-1">{r.error ?? 'Xato'}</div>
      ) : r.status === 'running' ? (
        <div className="space-y-1.5 mt-1">
          <div className="h-2.5 w-1/2 bg-elev2 rounded animate-pulse" />
          <div className="h-4 w-3/4 bg-elev2 rounded animate-pulse" />
        </div>
      ) : (
        <div className="space-y-1.5 mt-1 opacity-50">
          <div className="h-2.5 w-1/2 bg-elev2 rounded" />
          <div className="h-4 w-3/4 bg-elev2 rounded" />
        </div>
      )}
    </div>
  );
}

function StatusDot({ status }: { status: ModelResult['status'] }) {
  if (status === 'done') return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />;
  if (status === 'error') return <AlertCircle className="w-3.5 h-3.5 text-rose-500 shrink-0" />;
  if (status === 'running') return <Loader2 className="w-3.5 h-3.5 text-accent animate-spin shrink-0" />;
  return <Circle className="w-3.5 h-3.5 text-subtle shrink-0" />;
}

function Sparkline({ spark }: { spark: NonNullable<ModelResult['spark']> }) {
  const W = 100, H = 28;
  const vals = spark.values.length ? spark.values : [0];
  const max = Math.max(...vals, 1);
  const min = Math.min(...vals, 0);
  const range = max - min || 1;
  const norm = (v: number) => H - ((v - min) / range) * H;

  if (spark.type === 'gauge') {
    const pct = Math.max(0, Math.min(100, spark.pct ?? 0));
    return (
      <div className="mt-2 h-1.5 w-full bg-elev2 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-700 ${pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-accent' : 'bg-rose-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    );
  }

  if (spark.type === 'bar') {
    const bw = W / vals.length;
    return (
      <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full h-7" preserveAspectRatio="none">
        {vals.map((v, i) => (
          <rect
            key={i}
            x={i * bw + 1}
            y={norm(v)}
            width={bw - 2}
            height={Math.max(1, H - norm(v))}
            className="fill-accent/70"
          />
        ))}
      </svg>
    );
  }

  // line
  const points = vals.map((v, i) => `${(i / Math.max(1, vals.length - 1)) * W},${norm(v)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full h-7" preserveAspectRatio="none">
      <polyline points={points} className="stroke-accent" strokeWidth="1.5" fill="none" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
