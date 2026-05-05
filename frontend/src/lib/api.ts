const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const TOKEN_KEY = 'ai_platform_token';
const USER_KEY = 'ai_platform_user';

export function getToken(): string | null {
  return null;
}

export function isAuthenticated(): boolean {
  return true;
}

export function logout(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredUser(): { email: string; role: string } | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

async function apiFetch(path: string, options?: RequestInit): Promise<Response> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> || {}),
  };
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  return response;
}

export async function login(email: string, password: string): Promise<{ email: string; role: string }> {
  const user = { email, role: 'admin' };
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}

export async function predict<T = unknown>(
  endpoint: string,
  body: Record<string, unknown>,
  explain = false
): Promise<T> {
  const query = explain ? '?explain=true' : '';
  const response = await apiFetch(`${endpoint}${query}`, {
    method: 'POST',
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Soʻrov bajarilmadi' }));
    if (response.status === 401) {
      throw new Error('API ruxsat soʻrovini rad etdi.');
    }
    throw new Error(err.detail || `Soʻrov xatosi: ${response.status}`);
  }

  return response.json();
}

export async function fetchEvidence(body: {
  region_id?: string;
  mcc_code?: string;
  monthly_revenue?: number;
  initial_investment?: number;
  limit?: number;
  model_ids?: string[];
}): Promise<{
  rows: Array<Record<string, unknown>>;
  summary: { succeeded: number; struggling: number; failed: number; median_revenue: number; median_growth_pct: number };
  total_examined: number;
  sources: string[];
  blocks: Array<{
    block: string;
    matched_count: number;
    total_examined: number;
    stats: Record<string, number>;
    sample_rows: Array<Record<string, unknown>>;
    source: string;
  }>;
  alternatives: Array<{
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
  }>;
}> {
  const response = await apiFetch('/evidence/similar-businesses', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Evidence request failed: ${response.status}`);
  return response.json();
}
