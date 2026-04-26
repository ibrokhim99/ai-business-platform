'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { BusinessProfile } from './profile';
import { profileFromContext, DEFAULT_PROFILE } from './profile';

export interface Source {
  id: string;
  type: 'profile' | 'csv';
  name: string;
  subtitle?: string;
  /** Free-text context that gets prepended to chat queries when this source is active. */
  context?: string;
  /** Structured profile data — partial overrides applied when computing the active profile. */
  profile?: Partial<BusinessProfile>;
  /** Identifiers used to derive a profile when `profile` is absent. */
  region_id?: string;
  mcc_code?: string;
  monthly_revenue?: number;
  initial_investment?: number;
  rows?: number;
  cols?: number;
  selected: boolean;
  createdAt: number;
}

const KEY = 'biziq_sources_v3_uz';

const SEED: Source[] = [
  {
    id: 'seed-kafe-toshkent', type: 'profile', selected: true,
    name: 'Kafe — Toshkent', subtitle: 'MCC 5812 · Yunusobod',
    context: 'Kafe (MCC 5812), Toshkent (Yunusobod). Oylik daromad ~$15k, $50k boshlangʻich sarmoya.',
    region_id: 'tashkent-01', mcc_code: '5812', monthly_revenue: 15_000, initial_investment: 50_000,
    createdAt: Date.now() - 86_400_000 * 4,
  },
  {
    id: 'seed-oziq-samarqand', type: 'profile', selected: false,
    name: 'Oziq-ovqat — Samarqand', subtitle: 'MCC 5411 · Markaz',
    context: 'Oziq-ovqat doʻkoni (MCC 5411), Samarqand markazi. Oylik daromad ~$22k.',
    region_id: 'samarkand-01', mcc_code: '5411', monthly_revenue: 22_000, initial_investment: 80_000,
    createdAt: Date.now() - 86_400_000 * 6,
  },
  {
    id: 'seed-mehmonxona-buxoro', type: 'profile', selected: false,
    name: 'Butik mehmonxona — Buxoro', subtitle: 'MCC 7011 · Eski shahar',
    context: 'Butik mehmonxona (MCC 7011), Buxoro. 12 ta xona, oylik daromad ~$18k.',
    region_id: 'bukhara-01', mcc_code: '7011', monthly_revenue: 18_000, initial_investment: 220_000,
    createdAt: Date.now() - 86_400_000 * 9,
  },
  {
    id: 'seed-salon-fargona', type: 'profile', selected: false,
    name: 'Goʻzallik saloni — Fargʻona', subtitle: 'MCC 7230 · Markaz',
    context: 'Goʻzallik saloni (MCC 7230), Fargʻona markazi. Oylik daromad ~$8k.',
    region_id: 'fergana-01', mcc_code: '7230', monthly_revenue: 8_000, initial_investment: 25_000,
    createdAt: Date.now() - 86_400_000 * 12,
  },
];

function load(): Source[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return SEED;
    const parsed = JSON.parse(raw) as Source[];
    return Array.isArray(parsed) && parsed.length ? parsed : SEED;
  } catch {
    return SEED;
  }
}

function save(items: Source[]) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(KEY, JSON.stringify(items));
}

const uid = () => Math.random().toString(36).slice(2, 9) + Date.now().toString(36).slice(-3);

export function useSources() {
  const [items, setItems] = useState<Source[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setItems(load());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) save(items);
  }, [items, hydrated]);

  const toggle = useCallback((id: string) => {
    setItems((prev) => prev.map((s) => (s.id === id ? { ...s, selected: !s.selected } : s)));
  }, []);

  const selectOnly = useCallback((id: string) => {
    setItems((prev) => prev.map((s) => ({ ...s, selected: s.id === id })));
  }, []);

  const remove = useCallback((id: string) => {
    setItems((prev) => prev.filter((s) => s.id !== id));
  }, []);

  const add = useCallback((src: Omit<Source, 'id' | 'createdAt'>) => {
    setItems((prev) => [{ ...src, id: uid(), createdAt: Date.now() }, ...prev]);
  }, []);

  /**
   * Merge LLM-extracted profile patches (e.g. user said "daromadim 50K") into
   * every selected source. The profile is recomputed from selected sources, so
   * the patch lives on the sources themselves to survive re-renders.
   */
  const updateProfile = useCallback((patch: Partial<BusinessProfile>) => {
    setItems((prev) => {
      const anySelected = prev.some((s) => s.selected);
      if (!anySelected) return prev;
      return prev.map((s) => {
        if (!s.selected) return s;
        const next: Source = { ...s, profile: { ...(s.profile ?? {}), ...patch } };
        if (typeof patch.region_id === 'string') next.region_id = patch.region_id;
        if (typeof patch.mcc_code === 'string') next.mcc_code = patch.mcc_code;
        if (typeof patch.monthly_revenue_estimate === 'number') next.monthly_revenue = patch.monthly_revenue_estimate;
        if (typeof patch.initial_investment === 'number') next.initial_investment = patch.initial_investment;
        return next;
      });
    });
  }, []);

  const selected = items.filter((s) => s.selected);
  const activeContext = selected.map((s) => s.context).filter(Boolean).join(' ');

  /** Build a complete BusinessProfile by merging all selected sources (last wins). */
  const profile: BusinessProfile = useMemo(() => {
    if (selected.length === 0) return DEFAULT_PROFILE;
    let p = profileFromContext({});
    for (const s of selected) {
      const next = profileFromContext({
        region_id: s.region_id,
        mcc_code: s.mcc_code,
        monthly_revenue: s.monthly_revenue,
        initial_investment: s.initial_investment,
      });
      p = { ...p, ...next, ...(s.profile ?? {}) };
    }
    return p;
  }, [selected]);

  return { items, selected, activeContext, profile, hydrated, toggle, selectOnly, remove, add, updateProfile };
}
