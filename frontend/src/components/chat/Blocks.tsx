'use client';

import {
  ResponsiveContainer,
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from 'recharts';
import { CheckCircle2, AlertTriangle, Info, FileText } from 'lucide-react';
import { useTheme } from '@/lib/theme';
import type { Block } from '@/lib/chat/types';
import { ReportBlock } from './ReportBlock';
import { RecommendationBlock } from './RecommendationBlock';
import { DataSourcesBlock } from './DataSourcesBlock';

const PALETTE = ['#6366f1', '#06b6d4', '#8b5cf6', '#f59e0b', '#ef4444', '#10b981', '#ec4899'];

function useChartColors() {
  const { effective } = useTheme();
  const isDark = effective === 'dark';
  return {
    grid: isDark ? '#27272a' : '#e4e4e7',
    axis: isDark ? '#a1a1aa' : '#71717a',
    tipBg: isDark ? '#0a0a0c' : '#ffffff',
    tipBorder: isDark ? '#2a2a2e' : '#e4e4e7',
    legend: isDark ? '#a1a1aa' : '#52525b',
  };
}

function ChartBlock({ b }: { b: Extract<Block, { kind: 'chart' }> }) {
  const c = useChartColors();
  const colors = b.series.map((s, i) => s.color ?? PALETTE[i % PALETTE.length]);
  const tipStyle = { background: c.tipBg, border: `1px solid ${c.tipBorder}`, borderRadius: 8, fontSize: 12, color: 'inherit' };

  return (
    <div className="rounded-2xl border border-line bg-elev p-4 fade-in">
      {b.title && <div className="text-sm font-medium text-fg mb-3">{b.title}</div>}
      <div className="h-[260px] w-full">
        <ResponsiveContainer>
          {b.chartType === 'line' ? (
            <LineChart data={b.data} margin={{ top: 6, right: 12, left: -10, bottom: 0 }}>
              <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
              <XAxis dataKey={b.xKey} stroke={c.axis} fontSize={11} />
              <YAxis stroke={c.axis} fontSize={11} />
              <Tooltip contentStyle={tipStyle} />
              <Legend wrapperStyle={{ fontSize: 11, color: c.legend }} />
              {b.series.map((s, i) => (
                <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={colors[i]} strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          ) : b.chartType === 'area' ? (
            <AreaChart data={b.data} margin={{ top: 6, right: 12, left: -10, bottom: 0 }}>
              <defs>
                {b.series.map((s, i) => (
                  <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={colors[i]} stopOpacity={0.5} />
                    <stop offset="100%" stopColor={colors[i]} stopOpacity={0.05} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
              <XAxis dataKey={b.xKey} stroke={c.axis} fontSize={11} />
              <YAxis stroke={c.axis} fontSize={11} />
              <Tooltip contentStyle={tipStyle} />
              <Legend wrapperStyle={{ fontSize: 11, color: c.legend }} />
              {b.series.map((s, i) => (
                <Area key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={colors[i]} fill={`url(#grad-${s.key})`} strokeWidth={2} />
              ))}
            </AreaChart>
          ) : b.chartType === 'bar' ? (
            <BarChart data={b.data} margin={{ top: 6, right: 12, left: -10, bottom: 0 }}>
              <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
              <XAxis dataKey={b.xKey} stroke={c.axis} fontSize={11} />
              <YAxis stroke={c.axis} fontSize={11} />
              <Tooltip contentStyle={tipStyle} />
              <Legend wrapperStyle={{ fontSize: 11, color: c.legend }} />
              {b.series.map((s, i) => (
                <Bar key={s.key} dataKey={s.key} name={s.label} fill={colors[i]} radius={[6, 6, 0, 0]} />
              ))}
            </BarChart>
          ) : (
            <PieChart>
              <Pie data={b.data} dataKey={b.series[0].key} nameKey={b.xKey} outerRadius={90} innerRadius={50} paddingAngle={2}>
                {b.data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
              </Pie>
              <Tooltip contentStyle={tipStyle} />
              <Legend wrapperStyle={{ fontSize: 11, color: c.legend }} />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function KpiBlock({ b }: { b: Extract<Block, { kind: 'kpi' }> }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 fade-in">
      {b.items.map((it, i) => (
        <div key={i} className="rounded-2xl border border-line bg-elev p-3.5">
          <div className="text-[11px] uppercase tracking-wider text-subtle">{it.label}</div>
          <div
            className={`mt-1.5 text-xl font-semibold ${
              it.tone === 'pos' ? 'text-emerald-500' : it.tone === 'neg' ? 'text-rose-500' : 'text-fg'
            }`}
          >
            {it.value}
          </div>
          {it.hint && <div className="text-[11px] text-muted mt-0.5">{it.hint}</div>}
        </div>
      ))}
    </div>
  );
}

function TableBlock({ b }: { b: Extract<Block, { kind: 'table' }> }) {
  return (
    <div className="rounded-2xl border border-line bg-elev overflow-hidden fade-in">
      {b.title && <div className="px-4 pt-3 pb-2 text-sm font-medium text-fg">{b.title}</div>}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-y border-line bg-panel">
              {b.columns.map((c) => (
                <th key={c} className="text-left px-4 py-2 text-[11px] uppercase tracking-wider text-muted font-medium">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {b.rows.map((row, ri) => (
              <tr key={ri} className="border-b border-line last:border-b-0 hover:bg-panel/60">
                {row.map((cell, ci) => (
                  <td key={ci} className="px-4 py-2.5 text-fg">{String(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CalloutBlock({ b }: { b: Extract<Block, { kind: 'callout' }> }) {
  const styles = {
    info:    { wrap: 'border-sky-300/40 bg-sky-50 dark:border-sky-700/40 dark:bg-sky-950/30',     fg: 'text-sky-700 dark:text-sky-300',    Icon: Info },
    warn:    { wrap: 'border-amber-300/40 bg-amber-50 dark:border-amber-700/40 dark:bg-amber-950/30', fg: 'text-amber-700 dark:text-amber-300',  Icon: AlertTriangle },
    success: { wrap: 'border-emerald-300/40 bg-emerald-50 dark:border-emerald-700/40 dark:bg-emerald-950/30', fg: 'text-emerald-700 dark:text-emerald-300', Icon: CheckCircle2 },
  }[b.tone];
  const Icon = styles.Icon;
  return (
    <div className={`rounded-2xl border ${styles.wrap} px-4 py-3 flex gap-3 fade-in`}>
      <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${styles.fg}`} />
      <div className="text-sm">
        <div className={`font-medium ${styles.fg}`}>{b.title}</div>
        {b.body && <div className="text-fg/80 mt-0.5">{b.body}</div>}
      </div>
    </div>
  );
}

function SuggestionsBlock({ b, onPick }: { b: Extract<Block, { kind: 'suggestions' }>; onPick: (s: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2 fade-in">
      {b.chips.map((c) => (
        <button
          key={c}
          onClick={() => onPick(c)}
          className="text-xs px-3 py-1.5 rounded-full border border-line bg-elev hover:bg-panel hover:border-line-strong text-fg transition"
        >
          {c}
        </button>
      ))}
    </div>
  );
}

function ProgressBlock({ b }: { b: Extract<Block, { kind: 'progress' }> }) {
  const pct = Math.max(0, Math.min(100, b.pct));
  const color = b.tone === 'pos' ? 'bg-emerald-500' : b.tone === 'neg' ? 'bg-rose-500' : 'bg-accent';
  return (
    <div className="rounded-2xl border border-line bg-elev p-3.5 fade-in">
      <div className="flex justify-between text-xs mb-2">
        <span className="text-muted">{b.label}</span>
        <span className="text-fg font-medium">{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-panel rounded-full overflow-hidden">
        <div className={`h-full ${color} transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function FileAttachedBlock({ b }: { b: Extract<Block, { kind: 'file-attached' }> }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-line bg-elev px-3.5 py-3 fade-in">
      <div className="w-10 h-10 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
        <FileText className="w-5 h-5 text-accent" />
      </div>
      <div className="min-w-0">
        <div className="text-sm font-medium text-fg truncate">{b.name}</div>
        <div className="text-xs text-muted">
          {b.rows ?? '?'} qator · {b.cols ?? '?'} ustun
        </div>
      </div>
    </div>
  );
}

export function BlockRenderer({ block, onSuggestionPick }: { block: Block; onSuggestionPick: (s: string) => void }) {
  switch (block.kind) {
    case 'kpi':           return <KpiBlock b={block} />;
    case 'chart':         return <ChartBlock b={block} />;
    case 'table':         return <TableBlock b={block} />;
    case 'callout':       return <CalloutBlock b={block} />;
    case 'suggestions':   return <SuggestionsBlock b={block} onPick={onSuggestionPick} />;
    case 'progress':      return <ProgressBlock b={block} />;
    case 'file-attached': return <FileAttachedBlock b={block} />;
    case 'report':        return <ReportBlock profile={block.profile} results={block.results} />;
    case 'recommendation': return <RecommendationBlock rec={block.rec} />;
    case 'data-sources':  return (
      <DataSourcesBlock
        profile={block.profile}
        rows={block.rows}
        summary={block.summary}
        totalExamined={block.totalExamined}
        sources={block.sources}
        modelsUsed={block.modelsUsed}
        perBlock={block.perBlock}
      />
    );
  }
}
