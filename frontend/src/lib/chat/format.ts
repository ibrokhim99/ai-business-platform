export const fmtMoney = (n: number): string => {
  if (!isFinite(n)) return '—';
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(1)}k`;
  return `$${Math.round(n).toLocaleString()}`;
};

export const fmtPct = (n: number, digits = 1): string => {
  if (!isFinite(n)) return '—';
  // Heuristic: |n| ≤ 1 → fraction (0.05 = 5%); otherwise already a percentage value.
  // Using Math.abs preserves sign for negative numbers like -3.57%.
  return `${(Math.abs(n) > 1 ? n : n * 100).toFixed(digits)}%`;
};

export const fmtNum = (n: number): string => {
  if (!isFinite(n)) return '—';
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}k`;
  return `${Math.round(n)}`;
};

export const clamp = (v: number, lo: number, hi: number): number =>
  Math.min(Math.max(v, lo), hi);
