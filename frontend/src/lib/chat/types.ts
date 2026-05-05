import type { ModelResult } from './runner';
import type { RecommendationCard } from './recommendation';

export type Role = 'user' | 'assistant';

export interface EvidenceRow {
  region_id: string;
  mcc_code: string;
  niche: string;
  niche_label: string;
  lat?: number;
  lon?: number;
  radius_m?: number;
  monthly_revenue: number;
  initial_investment: number;
  monthly_net_cash_flow: number;
  growth_rate_pct: number;
  competitor_count: number;
  gross_margin_pct: number;
  outcome: 'succeeded' | 'struggling' | 'failed';
  similarity: number;
}

export interface EvidenceSummary {
  succeeded: number;
  struggling: number;
  failed: number;
  median_revenue: number;
  median_growth_pct: number;
}

export interface AlternativeBusiness {
  region_id: string;
  mcc_code: string;
  niche: string;
  niche_label: string;
  monthly_revenue: number;
  initial_investment: number;
  monthly_net_cash_flow: number;
  growth_rate_pct: number;
  competitor_count: number;
  gross_margin_pct: number;
  success_rate: number;
  support_count: number;
  rationale: string;
}

export interface BusinessMapMarker {
  id: string;
  region_id: string;
  mcc_code: string;
  niche_label: string;
  lat: number;
  lon: number;
  radius_m: number;
  monthly_revenue: number;
  monthly_net_cash_flow: number;
  growth_rate_pct: number;
  competitor_count: number;
  outcome: EvidenceRow['outcome'];
}

/** Per-block dataset evidence — what real CSV rows informed the answer. */
export interface BlockEvidence {
  block: string;
  matched_count: number;
  total_examined: number;
  stats: Record<string, number>;
  sample_rows: Array<Record<string, unknown>>;
  source: string;
}

export type Block =
  | { kind: 'kpi'; items: Array<{ label: string; value: string; hint?: string; tone?: 'pos' | 'neg' | 'neutral' }> }
  | { kind: 'chart'; chartType: 'line' | 'bar' | 'area' | 'pie'; title?: string; data: Array<Record<string, number | string>>; xKey: string; series: Array<{ key: string; label: string; color?: string }>; }
  | { kind: 'table'; title?: string; columns: string[]; rows: Array<Array<string | number>>; }
  | { kind: 'callout'; tone: 'info' | 'warn' | 'success'; title: string; body?: string }
  | { kind: 'suggestions'; chips: string[] }
  | { kind: 'progress'; label: string; pct: number; tone?: 'pos' | 'neg' | 'neutral' }
  | { kind: 'file-attached'; name: string; sizeBytes: number; rows?: number; cols?: number }
  | { kind: 'report'; profile: { region_label: string; mcc_label: string }; results: ModelResult[] }
  | { kind: 'recommendation'; rec: RecommendationCard }
  | {
      kind: 'business-map';
      title: string;
      profile: { region_label: string; mcc_label: string };
      center: { lat: number; lon: number };
      radius_m: number;
      markers: BusinessMapMarker[];
    }
  | {
      kind: 'data-sources';
      profile: { region_label: string; mcc_label: string };
      rows: EvidenceRow[];
      summary: EvidenceSummary;
      totalExamined: number;
      sources: string[];
      modelsUsed?: string[];
      perBlock?: BlockEvidence[];
    };

export interface Message {
  id: string;
  role: Role;
  text?: string;
  blocks?: Block[];
  createdAt: number;
  pending?: boolean;
  error?: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
}
