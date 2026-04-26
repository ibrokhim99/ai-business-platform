'use client';

import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend, ReferenceLine,
} from 'recharts';
import { CheckCircle2, AlertTriangle, AlertCircle, Loader2, ArrowRight, Sparkles, Shield, TrendingUp, Wallet } from 'lucide-react';
import { useTheme } from '@/lib/theme';
import { fmtMoney, fmtPct } from '@/lib/chat/format';
import type { RecommendationCard, Verdict, Binding } from '@/lib/chat/recommendation';

const VERDICT_LABEL: Record<Verdict, string> = {
  'APPROVE':     'TASDIQLASH',
  'RIGHT-SIZE':  'HAJMINI MOSLASH',
  'RESTRUCTURE': 'QAYTA TUZISH',
  'DECLINE':     'RAD ETISH',
};

const VERDICT_TONE: Record<Verdict, { wrap: string; fg: string; Icon: typeof CheckCircle2 }> = {
  'APPROVE':     { wrap: 'bg-emerald-500/10 border-emerald-500/30', fg: 'text-emerald-600 dark:text-emerald-400', Icon: CheckCircle2 },
  'RIGHT-SIZE':  { wrap: 'bg-accent/10 border-accent/30',           fg: 'text-accent',                            Icon: Sparkles },
  'RESTRUCTURE': { wrap: 'bg-amber-500/10 border-amber-500/30',     fg: 'text-amber-600 dark:text-amber-400',     Icon: AlertTriangle },
  'DECLINE':     { wrap: 'bg-rose-500/10 border-rose-500/30',       fg: 'text-rose-600 dark:text-rose-400',       Icon: AlertCircle },
};

const BINDING_LABEL: Record<Binding, string> = {
  requested:     'sizning soʻrovingiz',
  affordability: 'naqd pul oqimi imkoniyati',
  policy:        'bank siyosati chegarasi',
};

const TERM_LABEL = (n: number) => {
  if (n === 12) return '12 oy (1 yil)';
  if (n === 24) return '24 oy (2 yil)';
  if (n === 36) return '36 oy (3 yil)';
  return `${n} oy`;
};

export function RecommendationBlock({ rec }: { rec: RecommendationCard }) {
  if (!rec.ready) return <RecommendationSkeleton rec={rec} />;

  const v = rec.verdict;
  const tone = VERDICT_TONE[v];
  const Icon = tone.Icon;

  return (
    <div className="rounded-2xl border border-line bg-elev overflow-hidden fade-in shadow-card">
      {/* Header */}
      <div className="px-4 md:px-5 py-4 border-b border-line bg-gradient-to-br from-accent-soft via-transparent to-transparent">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-wider text-muted">Tavsiya</div>
            <div
              className="mt-1 text-base md:text-lg font-semibold text-fg md"
              dangerouslySetInnerHTML={{ __html: renderInline(rec.narrative) }}
            />
            <div className="mt-1.5 text-[12px] text-muted">
              Cheklov: <span className="text-fg font-medium">{BINDING_LABEL[rec.binding]}</span>
            </div>
          </div>
          <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold ${tone.wrap} ${tone.fg}`}>
            <Icon className="w-3.5 h-3.5" />
            {VERDICT_LABEL[v]}
          </div>
        </div>

        {/* Headline KPIs */}
        <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2.5">
          <KpiTile label="Kredit"     value={fmtMoney(rec.recommended.loan)}              tone="neutral" />
          <KpiTile label="Muddat"     value={TERM_LABEL(rec.recommended.termMonths)}      tone="neutral" />
          <KpiTile label="Oylik toʻlov" value={fmtMoney(rec.recommended.monthlyPayment)} tone="neutral" />
          <KpiTile
            label="Qoplash"
            value={`${rec.recommended.coverage.toFixed(2)}×`}
            tone={rec.recommended.coverage >= 1.5 ? 'pos' : rec.recommended.coverage >= 1.0 ? 'neutral' : 'neg'}
          />
        </div>
      </div>

      {/* Requested vs Recommended comparison */}
      {rec.requested.loan > 0 && rec.recommended.loan > 0 && (
        <div className="px-4 md:px-5 py-4 border-b border-line">
          <div className="text-[11px] uppercase tracking-wider text-muted mb-3">Soʻralgan vs Tavsiya qilingan</div>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-3 items-stretch">
            <ScenarioCard title="Siz soʻradingiz" muted scenario={rec.requested} />
            <div className="hidden md:flex items-center justify-center text-muted">
              <ArrowRight className="w-5 h-5" />
            </div>
            <ScenarioCard title="Biz tavsiya qilamiz" highlighted scenario={rec.recommended} />
          </div>
          {rec.requested.loan !== rec.recommended.loan && (
            <div className="mt-3 text-[12px] text-muted">
              Farqi: <span className="text-fg font-medium">{fmtMoney(rec.requested.loan - rec.recommended.loan)}</span>
              {' '}kichikroq · Oylik toʻlov{' '}
              <span className="text-fg font-medium">{fmtMoney(rec.requested.monthlyPayment - rec.recommended.monthlyPayment)}</span>
              {' '}past · Umumiy foiz{' '}
              <span className="text-fg font-medium">{fmtMoney(rec.requested.totalInterest - rec.recommended.totalInterest)}</span>
              {' '}tejaladi
            </div>
          )}
        </div>
      )}

      {/* Repayment vs Cash Flow chart */}
      {rec.overlay.length > 0 && (
        <div className="px-4 md:px-5 py-4 border-b border-line">
          <div className="text-[11px] uppercase tracking-wider text-muted mb-2">
            Qaytarish va Pul Oqimi (kelajakdagi traektoriya)
          </div>
          <OverlayChart
            data={rec.overlay}
            breakeven={rec.borrowerRisk.breakevenMonth}
            loanRepaid={rec.loanRepaidMonth}
          />
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted">
            <span><span className="inline-block w-3 h-0.5 bg-emerald-500 align-middle mr-1" /> Biznesning kümulyativ pul oqimi</span>
            <span><span className="inline-block w-3 h-0.5 bg-accent align-middle mr-1" /> Kümulyativ kredit qaytarish</span>
            <span><span className="inline-block w-3 h-0.5 bg-amber-500 align-middle mr-1" /> Tenglik nuqtasi (M{rec.borrowerRisk.breakevenMonth})</span>
            <span><span className="inline-block w-3 h-0.5 bg-violet-500 align-middle mr-1" /> Kredit yopilgan (M{rec.loanRepaidMonth})</span>
          </div>
        </div>
      )}

      {/* Dual risk */}
      <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-line border-b border-line">
        <RiskColumn
          icon={<TrendingUp className="w-4 h-4 text-accent" />}
          title="SIZ UCHUN RISK (qarz oluvchi)"
          rows={[
            { label: 'Defolt riski', value: fmtPct(rec.borrowerRisk.pd, 1), tone: rec.borrowerRisk.pd < 0.18 ? 'pos' : rec.borrowerRisk.pd < 0.30 ? 'neutral' : 'neg', hint: 'taxminiy' },
            { label: 'Toʻlovni qoplash', value: `${rec.borrowerRisk.coverage.toFixed(2)}×`, tone: rec.borrowerRisk.coverage >= 1.5 ? 'pos' : rec.borrowerRisk.coverage >= 1.0 ? 'neutral' : 'neg' },
            { label: 'Tenglik oyi', value: `M${rec.borrowerRisk.breakevenMonth}`, tone: 'neutral' },
            {
              label: 'Qaytarish vaqti',
              value: rec.borrowerRisk.monthsAheadOfBreakeven > 0
                ? `Tenglikdan ${rec.borrowerRisk.monthsAheadOfBreakeven} oy oldin`
                : rec.borrowerRisk.monthsAheadOfBreakeven < 0
                  ? `Tenglikdan ${Math.abs(rec.borrowerRisk.monthsAheadOfBreakeven)} oy keyin`
                  : 'Tenglik bilan bir vaqtda',
              tone: rec.borrowerRisk.monthsAheadOfBreakeven >= 0 ? 'pos' : 'neg',
            },
          ]}
        />
        <RiskColumn
          icon={<Shield className="w-4 h-4 text-accent" />}
          title="BANK UCHUN RISK"
          rows={[
            { label: 'Kutilayotgan zarar', value: fmtMoney(rec.bankRisk.expectedLoss), tone: rec.bankRisk.expectedLoss < rec.recommended.loan * 0.05 ? 'pos' : 'neg' },
            { label: 'LGD (yoʻqotish ulushi)', value: fmtPct(rec.bankRisk.lgd, 0), tone: 'neutral' },
            { label: 'Garov qoplash', value: fmtPct(rec.bankRisk.collateralCoverage, 0), tone: rec.bankRisk.collateralCoverage >= 0.5 ? 'pos' : 'neutral' },
            { label: 'Holat', value: rec.bankRisk.unsecured ? 'taʻminlanmagan' : 'taʻminlangan (diskont qoʻllanildi)', tone: rec.bankRisk.unsecured ? 'neg' : 'pos' },
          ]}
        />
      </div>

      {/* Stress test */}
      <div className="px-4 md:px-5 py-3 flex items-start gap-3">
        <Wallet className={`w-4 h-4 mt-0.5 ${rec.stress.marginal ? 'text-amber-500' : 'text-emerald-500'}`} />
        <div className="text-[13px] text-fg flex-1">
          <span className="font-medium">Stress sinovi:</span> daromad −{rec.stress.revenueDropPct}% boʻlsa,{' '}
          qoplash <span className="font-semibold">{rec.stress.stressCoverage.toFixed(2)}×</span>gacha tushadi
          {rec.stress.marginal
            ? <span className="text-amber-600 dark:text-amber-400"> · zaif chegara, ehtiyotkor boʻling</span>
            : <span className="text-emerald-600 dark:text-emerald-400"> · barqaror</span>
          }
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────
function KpiTile({ label, value, tone }: { label: string; value: string; tone?: 'pos' | 'neg' | 'neutral' }) {
  const valueClass = tone === 'pos' ? 'text-emerald-500' : tone === 'neg' ? 'text-rose-500' : 'text-fg';
  return (
    <div className="rounded-xl border border-line bg-elev px-3 py-2.5">
      <div className="text-[10.5px] uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-1 text-lg md:text-xl font-semibold leading-tight ${valueClass}`}>{value}</div>
    </div>
  );
}

function ScenarioCard({
  title, scenario, muted, highlighted,
}: {
  title: string;
  scenario: { loan: number; termMonths: number; monthlyPayment: number; totalInterest: number; coverage: number; pd: number };
  muted?: boolean;
  highlighted?: boolean;
}) {
  const wrap = highlighted
    ? 'border-accent/40 bg-accent-soft'
    : muted
      ? 'border-line bg-panel/40'
      : 'border-line bg-elev';
  return (
    <div className={`rounded-xl border ${wrap} p-3.5`}>
      <div className="flex items-center justify-between mb-2">
        <div className={`text-[11px] uppercase tracking-wider ${highlighted ? 'text-accent' : 'text-muted'}`}>{title}</div>
        {highlighted && <Sparkles className="w-3.5 h-3.5 text-accent" />}
      </div>
      <div className={`text-xl font-semibold ${highlighted ? 'text-accent' : 'text-fg'}`}>
        {fmtMoney(scenario.loan)}
      </div>
      <div className="text-[11px] text-muted mb-2">
        {TERM_LABEL(scenario.termMonths)}
      </div>
      <div className="space-y-0.5 text-[12px]">
        <Row label="Oylik toʻlov" value={fmtMoney(scenario.monthlyPayment)} />
        <Row label="Qoplash" value={`${scenario.coverage.toFixed(2)}×`} tone={scenario.coverage >= 1.5 ? 'pos' : scenario.coverage >= 1.0 ? 'neutral' : 'neg'} />
        <Row label="Defolt riski" value={fmtPct(scenario.pd, 1)} tone={scenario.pd < 0.18 ? 'pos' : scenario.pd < 0.30 ? 'neutral' : 'neg'} />
        <Row label="Umumiy foiz" value={fmtMoney(scenario.totalInterest)} />
      </div>
    </div>
  );
}

function Row({ label, value, tone }: { label: string; value: string; tone?: 'pos' | 'neg' | 'neutral' }) {
  const valueClass = tone === 'pos' ? 'text-emerald-500' : tone === 'neg' ? 'text-rose-500' : 'text-fg';
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-muted">{label}</span>
      <span className={`font-medium ${valueClass}`}>{value}</span>
    </div>
  );
}

function RiskColumn({
  icon, title, rows,
}: {
  icon: React.ReactNode;
  title: string;
  rows: Array<{ label: string; value: string; tone?: 'pos' | 'neg' | 'neutral'; hint?: string }>;
}) {
  return (
    <div className="px-4 md:px-5 py-4">
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <div className="text-[11px] uppercase tracking-wider text-muted font-semibold">{title}</div>
      </div>
      <div className="space-y-2">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between gap-2 text-[13px]">
            <span className="text-muted">{r.label}{r.hint && <span className="text-subtle text-[10px] ml-1">({r.hint})</span>}</span>
            <span className={`font-semibold ${r.tone === 'pos' ? 'text-emerald-500' : r.tone === 'neg' ? 'text-rose-500' : 'text-fg'}`}>{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function OverlayChart({
  data, breakeven, loanRepaid,
}: {
  data: Array<{ month: string; cashflow: number; repaid: number }>;
  breakeven: number;
  loanRepaid: number;
}) {
  const { effective } = useTheme();
  const isDark = effective === 'dark';
  const grid = isDark ? '#27272a' : '#e4e4e7';
  const axis = isDark ? '#a1a1aa' : '#71717a';
  const tipBg = isDark ? '#0a0a0c' : '#ffffff';
  const tipBorder = isDark ? '#2a2a2e' : '#e4e4e7';
  const legend = isDark ? '#a1a1aa' : '#52525b';

  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 6, right: 12, left: -10, bottom: 0 }}>
          <CartesianGrid stroke={grid} strokeDasharray="3 3" />
          <XAxis dataKey="month" stroke={axis} fontSize={11} />
          <YAxis stroke={axis} fontSize={11} tickFormatter={(v) => fmtMoney(v)} />
          <Tooltip
            contentStyle={{ background: tipBg, border: `1px solid ${tipBorder}`, borderRadius: 8, fontSize: 12 }}
            formatter={(v) => fmtMoney(Number(v ?? 0))}
          />
          <Legend wrapperStyle={{ display: 'none' }} />
          <ReferenceLine x={`M${breakeven}`} stroke="#f59e0b" strokeDasharray="4 4" />
          <ReferenceLine x={`M${loanRepaid}`} stroke="#8b5cf6" strokeDasharray="4 4" />
          <Line type="monotone" dataKey="cashflow" name="Pul oqimi" stroke="#10b981" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="repaid"   name="Qaytarish" stroke="#6366f1" strokeWidth={2} strokeDasharray="6 4" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Skeleton (shown while required models still running) ──────────────
function RecommendationSkeleton({ rec }: { rec: Extract<RecommendationCard, { ready: false }> }) {
  // Once the stream is done and not all required models ran, we know the
  // missing ones will never arrive — flip from "preparing…" to "not applicable".
  const finalized = rec.streamDone && rec.readyCount < rec.totalRequired;

  if (finalized) {
    return (
      <div className="rounded-2xl border border-line bg-elev overflow-hidden fade-in">
        <div className="px-4 md:px-5 py-4 bg-gradient-to-br from-amber-500/10 via-transparent to-transparent">
          <div className="text-[11px] uppercase tracking-wider text-muted">Tavsiya</div>
          <div className="mt-1 text-base font-semibold text-fg flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-500" />
            Bu soʻrov uchun kredit tavsiyasi tuzilmadi
          </div>
          <div className="mt-1.5 text-[12px] text-muted">
            Toʻliq kredit tavsiyasi uchun savolingizda kreditni soʻrang —
            zarur 6 ta modeldan {rec.readyCount} tasi ishladi
            {rec.missing.length > 0 && (
              <>, qolgan: <span className="text-fg">{rec.missing.join(', ')}</span></>
            )}.
          </div>
          {rec.errored.length > 0 && (
            <div className="mt-1.5 text-[12px] text-rose-500">
              Xatolik: {rec.errored.join(', ')}.
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-line bg-elev overflow-hidden fade-in">
      <div className="px-4 md:px-5 py-4 bg-gradient-to-br from-accent-soft via-transparent to-transparent">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-wider text-muted">Tavsiya</div>
            <div className="mt-1 text-base font-semibold text-fg flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-accent" />
              Tavsiya tayyorlanmoqda…
            </div>
            {rec.errored.length > 0 && (
              <div className="mt-1.5 text-[12px] text-rose-500">
                Xatolik: {rec.errored.join(', ')} — tavsiya cheklangan rejimda koʻrsatiladi.
              </div>
            )}
            <div className="mt-1.5 text-[12px] text-muted">
              {rec.readyCount} / {rec.totalRequired} ta kerakli model tayyor
            </div>
          </div>
          <div className="text-[11px] text-muted bg-elev2 px-2.5 py-1 rounded-full">
            {Math.round((rec.readyCount / rec.totalRequired) * 100)}%
          </div>
        </div>
        <div className="mt-3 h-1.5 bg-panel rounded-full overflow-hidden">
          <div
            className="h-full bg-accent transition-all duration-500"
            style={{ width: `${(rec.readyCount / rec.totalRequired) * 100}%` }}
          />
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 p-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl border border-line bg-panel/40 p-3 space-y-2">
            <div className="h-2.5 w-1/2 bg-elev2 rounded animate-pulse" />
            <div className="h-5 w-3/4 bg-elev2 rounded animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  );
}

// Tiny inline markdown for **bold** in the narrative
function renderInline(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}
