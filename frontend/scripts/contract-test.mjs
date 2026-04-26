#!/usr/bin/env node
/**
 * Runtime contract test — actually invokes each model's formatHeadline and
 * buildSpark against a captured backend response and flags any that return
 * empty / zero / NaN values. This catches contract drift that static analysis
 * cannot (ternary fallbacks, computed fields, etc.).
 *
 * Usage:
 *   1. Backend running on localhost:8000.
 *   2. node scripts/contract-test.mjs
 *
 * Prints a table per-model with status: ok / suspicious / broken.
 */

import { execSync } from 'node:child_process';
import { writeFileSync, readFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');

const BASE = 'http://localhost:8000/api/v1';
const PROFILE = {
  region_id: 'tashkent-01',
  region_label: 'Toshkent',
  population: 320000,
  avg_income: 720,
  mcc_code: '5812',
  mcc_label: 'Restoran',
  niche: 'food',
  lat: 41.3111,
  lon: 69.2797,
  radius_m: 500,
  walk_minutes: 10,
  facade_direction_deg: 180,
  monthly_revenue_estimate: 15000,
  monthly_fixed_costs: 6000,
  monthly_rent: 1800,
  initial_investment: 50000,
  business_age_months: 0,
  owner_experience_years: 3,
  owner_credit_history_score: 680,
  collateral_value: 25000,
  cogs_pct: 40,
  avg_transaction_value: 15,
  monthly_transactions: 1000,
  customer_acquisition_cost: 5,
  monthly_churn_rate_pct: 5,
  gross_margin_pct: 60,
  discount_rate_annual_pct: 12,
  horizon_months: 24,
  growth_rate_monthly_pct: 2,
  requested_loan_amount: 30000,
  loan_term_months: 36,
  interest_rate_annual_pct: 18,
  existing_debt_monthly: 0,
};

async function login() {
  const r = await fetch(`${BASE}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin@bank.uz', password: 'admin123' }),
  });
  const j = await r.json();
  return j.access_token;
}

async function callBackend(token, endpoint, body) {
  const r = await fetch(`${BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`HTTP ${r.status}: ${txt.slice(0, 200)}`);
  }
  const j = await r.json();
  return j.prediction ?? j;
}

function evalHeadline(result) {
  // A headline is "broken" if value is empty or matches obvious zero/empty patterns.
  if (!result || typeof result !== 'object') return 'broken';
  const v = String(result.value ?? '').trim();
  if (!v || v === '—' || v === 'undefined' || v === 'null' || v === 'NaN') return 'broken';
  // Specific zero patterns we want to flag:
  //   "0/100", "0%", "$0", "0", "0 oy", "M0"
  if (/^(0\s*\/\s*100|0\s*%|\$\s*0|0|0(\.0+)?\s*(oy|kun|month)|M0)$/i.test(v)) return 'suspicious';
  // Money zero: "0 so'm", "0 USD", "0$" etc.
  if (/^[^\d]*0([.,]0+)?[^\d]*$/.test(v)) return 'suspicious';
  return 'ok';
}

function evalSpark(spark) {
  if (!spark) return 'no-spark';
  if (!Array.isArray(spark.values) || spark.values.length === 0) return 'broken';
  const sum = spark.values.reduce((a, b) => Number(a) + Number(b), 0);
  if (!isFinite(sum) || sum === 0) return 'suspicious';
  return 'ok';
}

async function main() {
  // Compile models.ts to JS so we can import it.
  // Simplest: use tsc to emit a .mjs version, or use a bundle via esbuild.
  // We'll use esbuild via npx (already installed for Next.js).
  console.log('Bundling models.ts ...');
  const outFile = resolve(ROOT, '.contract-test/models.mjs');
  mkdirSync(resolve(ROOT, '.contract-test'), { recursive: true });
  // Replace external-only imports (format helpers, types) with inline shims.
  const src = readFileSync(resolve(ROOT, 'src/lib/chat/models.ts'), 'utf8');
  const stub = `
const fmtMoney = (v) => v === 0 ? '$0' : '$' + Number(v).toLocaleString('en');
const fmtPct = (n, d = 1) => {
  if (!isFinite(n)) return '—';
  return ((Math.abs(n) > 1 ? n : n * 100).toFixed(d)) + '%';
};
const fmtNum = (v) => Number(v).toLocaleString('en');
${src
  .replace(/import type \{[^}]+\} from [^;]+;/g, '')
  .replace(/import \{[^}]*fmt[^}]*\} from [^;]+;/g, '')}
  `;
  // Strip TS type annotations crudely via esbuild.
  writeFileSync(resolve(ROOT, '.contract-test/models.input.ts'), stub);
  execSync(
    `npx --yes esbuild --bundle --format=esm --platform=node --external:* --target=es2022 --outfile=${outFile} .contract-test/models.input.ts`,
    { cwd: ROOT, stdio: 'inherit' }
  );
  const mod = await import(outFile);
  const ALL = mod.ALL_MODELS;
  console.log(`Loaded ${ALL.length} models from models.ts\n`);

  const token = await login();
  const results = [];

  for (const m of ALL) {
    const input = m.buildInput(PROFILE);
    let pred;
    try {
      pred = await callBackend(token, m.endpoint, input);
    } catch (err) {
      results.push({ id: m.modelId, status: 'http_error', headline: '—', spark: '—', hStatus: 'http_error', sStatus: 'http_error', err: String(err).slice(0, 120) });
      continue;
    }
    let h, s;
    try { h = m.formatHeadline(pred); } catch (err) { h = { label: 'err', value: 'EXCEPTION: ' + String(err).slice(0, 80) }; }
    try { s = m.buildSpark ? m.buildSpark(pred) : null; } catch (err) { s = null; }
    const hStatus = evalHeadline(h);
    const sStatus = evalSpark(s);
    const overall = hStatus === 'ok' ? sStatus === 'ok' || sStatus === 'no-spark' ? 'ok' : sStatus : hStatus;
    results.push({
      id: m.modelId, status: overall,
      headline: `${h.label} = ${h.value}`,
      spark: s ? `${s.type}[${s.values.length}]` : '—',
      hStatus, sStatus,
      pred_keys: Object.keys(pred ?? {}).slice(0, 8).join(','),
    });
  }

  // Print
  for (const r of results) {
    const mark = r.status === 'ok' ? '✓' : (r.status === 'suspicious' ? '⚠' : '✗');
    console.log(`  ${mark} ${r.id.padEnd(6)} headline=${r.hStatus.padEnd(11)} spark=${r.sStatus.padEnd(11)}  "${r.headline}"  spark=${r.spark}`);
  }
  const broken = results.filter((r) => r.status === 'broken');
  const suspicious = results.filter((r) => r.status === 'suspicious');
  const httpErr = results.filter((r) => r.status === 'http_error');
  console.log();
  console.log(`summary: ok=${results.length - broken.length - suspicious.length - httpErr.length}, suspicious=${suspicious.length}, broken=${broken.length}, http_error=${httpErr.length}`);

  if (broken.length || httpErr.length) process.exit(1);
}

main().catch((err) => { console.error(err); process.exit(2); });
