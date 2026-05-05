import { fmtMoney, fmtPct } from './format';
import type { BusinessProfile } from './profile';
import type { ModelResult } from './runner';
import type { AlternativeBusiness, Block, EvidenceSummary } from './types';

interface AlternativeEvidence {
  summary: EvidenceSummary;
  alternatives: AlternativeBusiness[];
}

function getPrediction(results: ModelResult[], modelId: string): Record<string, unknown> | undefined {
  return results.find((r) => r.modelId === modelId)?.prediction;
}

function successRate(summary: EvidenceSummary): number {
  const total = summary.succeeded + summary.struggling + summary.failed;
  return total > 0 ? summary.succeeded / total : 0;
}

export function shouldSuggestAlternativeBusinesses(
  results: ModelResult[],
  evidence: AlternativeEvidence,
): boolean {
  if (!evidence.alternatives.length) return false;

  const d1 = getPrediction(results, 'M-D1') ?? {};
  const d3 = getPrediction(results, 'M-D3') ?? {};
  const a5 = getPrediction(results, 'M-A5') ?? {};

  const viabilityVerdict = String(d1.verdict ?? '');
  const survivalProb = Number(d1.survival_probability_2y ?? 1);
  const roiVerdict = String(d3.verdict ?? '');
  const roiPct = Number(d3.roi_pct ?? 0);
  const opportunityRank = String(a5.rank ?? '');
  const success = successRate(evidence.summary);

  return (
    opportunityRank === 'poor'
    || viabilityVerdict === 'high_risk'
    || survivalProb < 0.5
    || roiVerdict === 'unprofitable'
    || roiPct < 0
    || success < 0.45
    || evidence.summary.failed > evidence.summary.succeeded
  );
}

export function buildAlternativeBusinessBlocks(
  profile: BusinessProfile,
  results: ModelResult[],
  evidence: AlternativeEvidence,
): Block[] {
  if (!shouldSuggestAlternativeBusinesses(results, evidence)) return [];

  const success = successRate(evidence.summary);
  const businessLabel = profile.mcc_label || profile.mcc_code || 'Tanlangan biznes';
  const regionLabel = profile.region_label || profile.region_id || 'shu hudud';
  const top = evidence.alternatives.slice(0, 3);
  const weakLocalHistory = success < 0.45 || evidence.summary.failed > evidence.summary.succeeded;
  const body = weakLocalHistory
    ? `${businessLabel} uchun datasetdagi muvaffaqiyat ulushi ${fmtPct(success, 0)}. Shu hududda tarixan yaxshiroq ishlagan bizneslar quyida keltirilgan.`
    : `${businessLabel} bo'yicha hisob-kitob xavf ko'rsatdi. Shu hududda dataset bo'yicha yaxshiroq ishlagan bizneslar quyida keltirilgan.`;

  return [
    {
      kind: 'callout',
      tone: 'warn',
      title: `${businessLabel} ${regionLabel} hududida zaif ko'rinadi`,
      body,
    },
    {
      kind: 'table',
      title: 'Hududdagi muvaffaqiyatli muqobil bizneslar',
      columns: ['Biznes', 'MCC', 'Muvaffaqiyat', 'Oylik daromad', 'Sof oqim', 'Oʻsish'],
      rows: top.map((alt) => [
        alt.niche_label,
        alt.mcc_code,
        `${fmtPct(alt.success_rate, 0)} · n=${alt.support_count}`,
        fmtMoney(alt.monthly_revenue),
        fmtMoney(alt.monthly_net_cash_flow),
        fmtPct(alt.growth_rate_pct, 1),
      ]),
    },
    {
      kind: 'suggestions',
      chips: top.map((alt) => `${regionLabel}da ${alt.niche_label} biznesini tahlil qil`),
    },
  ];
}
