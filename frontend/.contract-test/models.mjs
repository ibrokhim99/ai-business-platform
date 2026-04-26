// .contract-test/models.input.ts
var fmtMoney = (v) => v === 0 ? "$0" : "$" + Number(v).toLocaleString("en");
var fmtPct = (n, d = 1) => {
  if (!isFinite(n)) return "\u2014";
  return (Math.abs(n) > 1 ? n : n * 100).toFixed(d) + "%";
};
var fmtNum = (v) => Number(v).toLocaleString("en");
var BLOCK_META = {
  A: { title: "Bozor tahlili", subtitle: "Hajm, bo\u02BBshliq, to\u02BByinganlik, sektor", color: "from-indigo-500/15 to-transparent text-indigo-500" },
  B: { title: "Prognozlash", subtitle: "Talab, mavsumiylik, tendensiyalar", color: "from-cyan-500/15 to-transparent text-cyan-500" },
  C: { title: "Joylashuv", subtitle: "Baho, tirbandlik, jonlilik", color: "from-violet-500/15 to-transparent text-violet-500" },
  D: { title: "Moliyaviy", subtitle: "Hayotiylik, ROI, pul oqimi", color: "from-amber-500/15 to-transparent text-amber-500" },
  E: { title: "Raqobat", subtitle: "Raqobatchilar, ketish, qoidaviy", color: "from-fuchsia-500/15 to-transparent text-fuchsia-500" },
  F: { title: "Kredit", subtitle: "Risk, hajm, DTI, NPL", color: "from-rose-500/15 to-transparent text-rose-500" },
  G: { title: "Mijoz", subtitle: "Profil, xatti-harakat, brend", color: "from-emerald-500/15 to-transparent text-emerald-500" },
  H: { title: "Marketing", subtitle: "CAC, LTV, kanallar, narx, promo", color: "from-pink-500/15 to-transparent text-pink-500" },
  I: { title: "Operatsiyalar", subtitle: "Inventar, ta\u02BBminotchi, xodim, marshrut", color: "from-teal-500/15 to-transparent text-teal-500" },
  J: { title: "Firibgarlik", subtitle: "Tranzaksiya, AML, identifikatsiya", color: "from-red-500/15 to-transparent text-red-500" }
};
var seasonal12 = [0.92, 0.95, 1.02, 1.07, 1.1, 1.05, 1, 0.97, 1.03, 1.08, 1.15, 1.2];
var competitorsFor = (pop) => Math.max(3, Math.round(pop / 6e3));
var A = [
  {
    modelId: "M-A1",
    block: "A",
    title: "Bozor hajmi",
    endpoint: "/market-analysis/market-sizing",
    buildInput: (p) => ({ region_id: p.region_id, mcc_code: p.mcc_code, population: p.population, avg_income: p.avg_income }),
    fallback: (p) => {
      const tam = p.population * p.avg_income * 0.6;
      return { tam_uzs: tam, sam_uzs: tam * 0.42, som_uzs: tam * 0.42 * 0.18 };
    },
    formatHeadline: (r) => ({ label: "TAM (umumiy bozor)", value: fmtMoney(Number(r.tam ?? r.tam_uzs ?? r.total_addressable_market ?? 0)), tone: "neutral" }),
    buildSpark: (r) => {
      const tam = Number(r.tam ?? r.tam_uzs ?? 0);
      const sam = Number(r.sam ?? r.sam_uzs ?? 0);
      const som = Number(r.som ?? r.som_uzs ?? 0);
      return { type: "bar", values: [tam, sam, som].map((v) => v / 1e6) };
    }
  },
  {
    modelId: "M-A2",
    block: "A",
    title: "Bo\u02BBshliq tahlili",
    endpoint: "/market-analysis/gap-analysis",
    buildInput: (p) => ({ region_id: p.region_id, mcc_code: p.mcc_code, normative_density: 1.5, actual_count: Math.max(1, Math.round(p.population / 5e3)), population: p.population }),
    fallback: (p) => {
      const norm = 1.5;
      const actual = Math.max(1, Math.round(p.population / 5e3));
      const ratio = actual / (p.population / 1e4 * norm);
      return { density_actual: actual, density_normative: norm, gap_ratio: ratio, opportunity_score: Math.max(0, 100 - ratio * 60) };
    },
    formatHeadline: (r) => {
      const opp = Number(r.opportunity_score ?? r.gap_pct ?? 0);
      return { label: "Imkoniyat", value: `${Math.round(opp)}/100`, tone: opp >= 60 ? "pos" : opp >= 40 ? "neutral" : "neg" };
    },
    buildSpark: (r) => {
      const v = Number(r.opportunity_score ?? r.gap_pct ?? 0);
      return { type: "gauge", values: [v], pct: v };
    }
  },
  {
    modelId: "M-A3",
    block: "A",
    title: "To\u02BByinganlik indeksi",
    endpoint: "/market-analysis/saturation-index",
    buildInput: (p) => ({ region_id: p.region_id, mcc_code: p.mcc_code, competitor_count: competitorsFor(p.population), population: p.population, avg_revenue_per_outlet: p.monthly_revenue_estimate * 12 }),
    fallback: (p) => ({ saturation_index: Math.min(95, competitorsFor(p.population) / (p.population / 1e4) * 30) }),
    formatHeadline: (r) => {
      const v = Number(r.saturation_index ?? 0);
      return { label: "To\u02BByinganlik", value: `${v.toFixed(0)}%`, tone: v < 60 ? "pos" : v < 80 ? "neutral" : "neg" };
    },
    buildSpark: (r) => ({ type: "gauge", values: [Number(r.saturation_index ?? 0)], pct: Number(r.saturation_index ?? 0) })
  },
  {
    modelId: "M-A4",
    block: "A",
    title: "Hamyon ulushi",
    endpoint: "/market-analysis/wallet-share",
    buildInput: (p) => ({ region_id: p.region_id, mcc_code: p.mcc_code, population: p.population, avg_monthly_spend: p.avg_income * 0.6, competitor_count: competitorsFor(p.population) }),
    fallback: (p) => ({ achievable_share_pct: 100 / (competitorsFor(p.population) + 2) }),
    formatHeadline: (r) => ({ label: "Erishish ulushi", value: fmtPct(Number(r.wallet_share_pct ?? r.achievable_share_pct ?? 0)), tone: "neutral" })
  },
  {
    modelId: "M-A5",
    block: "A",
    title: "Sektor imkoniyati",
    endpoint: "/market-analysis/niche-opportunity",
    buildInput: (p) => ({ region_id: p.region_id, mcc_code: p.mcc_code, population: p.population, avg_income: p.avg_income, competitor_count: competitorsFor(p.population), growth_rate_pct: 8 }),
    fallback: (p) => ({ niche_score: 40 + p.population / 1e4 % 50 }),
    formatHeadline: (r) => {
      const v = Number(r.niche_score ?? r.opportunity_score ?? 0);
      return { label: "Sektor bahosi", value: `${Math.round(v)}/100`, tone: v >= 60 ? "pos" : v >= 40 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-A6",
    block: "A",
    title: "Sohalararo sinergiya",
    endpoint: "/market-analysis/cross-niche",
    buildInput: (p) => ({ new_mcc_code: p.mcc_code, location_lat: p.lat, location_lon: p.lon, radius_m: p.radius_m, adjacent_mcc_codes: ["5814", "5411", "5999"].filter((m) => m !== p.mcc_code) }),
    fallback: () => ({ synergy_score: 55 + Math.random() * 30 }),
    formatHeadline: (r) => {
      const synergy = r.synergy_score !== void 0 ? Number(r.synergy_score) : 100 * (1 - Number(r.cannibalization_risk ?? 0));
      return { label: "Sinergiya", value: `${Math.round(synergy)}/100`, tone: synergy >= 60 ? "pos" : "neutral" };
    }
  }
];
var B = [
  {
    modelId: "M-B1",
    block: "B",
    title: "Talab prognozi",
    endpoint: "/forecasting/demand-forecast",
    buildInput: (p) => ({ region_id: p.region_id, mcc_code: p.mcc_code, horizon_months: p.horizon_months, base_monthly_revenue: p.monthly_revenue_estimate }),
    fallback: (p) => {
      const series = Array.from({ length: 12 }, (_, i) => Math.round(p.monthly_revenue_estimate * Math.pow(1.03, i) * seasonal12[i % 12]));
      return { monthly_forecast: series, total_revenue: series.reduce((a, b) => a + b, 0) };
    },
    formatHeadline: (r) => {
      const forecast = r.forecast ?? [];
      const total = r.total_revenue !== void 0 ? Number(r.total_revenue) : forecast.reduce((s, x) => s + Number(x.predicted ?? 0), 0);
      return { label: "12-oylik daromad", value: fmtMoney(total), tone: "pos" };
    },
    buildSpark: (r) => {
      const forecast = r.forecast ?? [];
      const values = forecast.length ? forecast.map((x) => Number(x.predicted ?? 0)) : r.monthly_forecast ?? [];
      return { type: "line", values };
    }
  },
  {
    modelId: "M-B2",
    block: "B",
    title: "Mavsumiylik",
    endpoint: "/forecasting/seasonality",
    buildInput: (p) => ({ mcc_code: p.mcc_code, region_id: p.region_id, year: (/* @__PURE__ */ new Date()).getFullYear() }),
    fallback: () => ({ seasonality_index: seasonal12.map((s) => s * 100), peak_month: 12, low_month: 1 }),
    formatHeadline: (r) => {
      const peak = r.peak_months?.[0] ?? r.peak_month ?? 12;
      return { label: "Cho\u02BBqqi oyi", value: `M${peak}`, tone: "neutral" };
    },
    buildSpark: (r) => {
      const idx = r.monthly_indices?.map((v) => v * 100) ?? r.seasonality_index ?? seasonal12.map((s) => s * 100);
      return { type: "bar", values: idx };
    }
  },
  {
    modelId: "M-B3",
    block: "B",
    title: "Aholi dinamikasi",
    endpoint: "/forecasting/population-dynamics",
    buildInput: (p) => ({ region_id: p.region_id, horizon_years: 5 }),
    fallback: (p) => {
      const series = Array.from({ length: 5 }, (_, i) => Math.round(p.population * Math.pow(1.018, i + 1)));
      return { yearly_population: series, growth_rate_pct: 1.8 };
    },
    formatHeadline: (r) => {
      const proj = r.projections;
      let growth = Number(r.growth_rate_pct ?? 0);
      if (proj && proj.length >= 2) {
        const first = proj[0].population, last = proj[proj.length - 1].population;
        growth = (Math.pow(last / first, 1 / (proj.length - 1)) - 1) * 100;
      }
      return { label: "5-yillik o\u02BBsish", value: fmtPct(growth), tone: "pos" };
    },
    buildSpark: (r) => {
      const proj = r.projections;
      const series = proj?.map((p) => p.population) ?? r.yearly_population ?? [];
      return { type: "line", values: series };
    }
  },
  {
    modelId: "M-B4",
    block: "B",
    title: "Daromad tendensiyasi",
    endpoint: "/forecasting/income-trend",
    buildInput: (p) => ({ region_id: p.region_id, horizon_months: p.horizon_months, current_avg_income: p.avg_income }),
    fallback: (p) => {
      const series = Array.from({ length: 12 }, (_, i) => Math.round(p.avg_income * Math.pow(1.005, i)));
      return { monthly_income: series, projected_growth_pct: 6.2 };
    },
    formatHeadline: (r) => {
      const forecast = r.forecast;
      let growth = Number(r.projected_growth_pct ?? 0);
      if (forecast && forecast.length >= 2) {
        const first = Number(forecast[0].avg_income ?? 0);
        const last = Number(forecast[forecast.length - 1].avg_income ?? 0);
        growth = first > 0 ? (last - first) / first * 100 : 0;
      }
      return { label: "Daromad o\u02BBsishi", value: fmtPct(growth), tone: "pos" };
    },
    buildSpark: (r) => {
      const forecast = r.forecast;
      const series = forecast?.map((x) => Number(x.avg_income ?? 0)) ?? (r.monthly_income ?? []);
      return { type: "line", values: series };
    }
  },
  {
    modelId: "M-B5",
    block: "B",
    title: "MCC tendensiyasi",
    endpoint: "/forecasting/mcc-trend",
    buildInput: (p) => ({ mcc_code: p.mcc_code, region_id: p.region_id, lookback_months: 24 }),
    fallback: () => ({ trend_direction: "rising", momentum_score: 72 }),
    formatHeadline: (r) => {
      const raw = Number(r.momentum_score ?? 0);
      const v = raw <= 1 ? raw * 100 : raw;
      return { label: "Sur\u02BCat", value: `${Math.round(v)}/100`, tone: v >= 50 ? "pos" : "neutral" };
    }
  },
  {
    modelId: "M-B6",
    block: "B",
    title: "Biznes ro\u02BByxatlari",
    endpoint: "/forecasting/business-registration",
    buildInput: (p) => ({ region_id: p.region_id, mcc_code: p.mcc_code, horizon_months: p.horizon_months }),
    fallback: (p) => ({ projected_new_registrations: Math.round(p.population / 5e3) }),
    formatHeadline: (r) => {
      const forecast = r.forecast;
      const total = forecast ? forecast.reduce((s, x) => s + Number(x.new_registrations ?? 0), 0) : Number(r.projected_new_registrations ?? 0);
      return { label: "Yangi kiruvchilar (yil)", value: fmtNum(total), tone: "neutral" };
    }
  }
];
var C = [
  {
    modelId: "M-C1",
    block: "C",
    title: "Joylashuv bahosi",
    endpoint: "/location/score",
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, mcc_code: p.mcc_code, radius_m: p.radius_m }),
    fallback: () => ({ score: 72, breakdown: { foot_traffic: 78, competition: 56, visibility: 84, income: 68 } }),
    formatHeadline: (r) => {
      const v = Number(r.score ?? r.total_score ?? 0);
      return { label: "Umumiy", value: `${Math.round(v)}/100`, tone: v >= 70 ? "pos" : v >= 50 ? "neutral" : "neg" };
    },
    buildSpark: (r) => ({ type: "gauge", values: [Number(r.score ?? 0)], pct: Number(r.score ?? 0) })
  },
  {
    modelId: "M-C2",
    block: "C",
    title: "Tirbandlik bahosi",
    endpoint: "/location/traffic-scoring",
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, radius_m: p.radius_m }),
    fallback: () => ({ daily_footfall: 4200, weekend_uplift_pct: 32 }),
    formatHeadline: (r) => {
      const v = Number(r.daily_foot_traffic ?? r.daily_footfall ?? 0);
      return { label: "Kunlik tashriflar", value: fmtNum(v), tone: "pos" };
    },
    buildSpark: (r) => {
      const profile = r.hourly_profile;
      if (profile?.length) {
        const peak = Number(r.daily_foot_traffic ?? 0);
        return { type: "line", values: profile.map((p) => Math.round(p * peak / 24)) };
      }
      const base = Number(r.daily_foot_traffic ?? r.daily_footfall ?? 4200);
      return { type: "bar", values: Array.from({ length: 7 }, (_, i) => base * (i === 5 || i === 6 ? 1.3 : 1)) };
    }
  },
  {
    modelId: "M-C3",
    block: "C",
    title: "Izoxron talab",
    endpoint: "/location/isochrone-demand",
    // Backend expects walk_minutes as a list of isochrone radii (e.g. [5, 10, 15]).
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, walk_minutes: [p.walk_minutes], mcc_code: p.mcc_code }),
    fallback: (p) => ({ reachable_population: Math.round(p.population * 0.04), demand_index: 68 }),
    formatHeadline: (r) => ({ label: "Erishish mumkin", value: fmtNum(Number(r.total_addressable_population ?? r.reachable_population ?? 0)), tone: "neutral" })
  },
  {
    modelId: "M-C4",
    block: "C",
    title: "Ko\u02BBcha jonliligi",
    endpoint: "/location/street-vitality",
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, radius_m: p.radius_m }),
    fallback: () => ({ vitality_score: 75 }),
    formatHeadline: (r) => {
      const v = Number(r.vitality_index ?? r.vitality_score ?? 0);
      return { label: "Jonlilik", value: `${Math.round(v)}/100`, tone: v >= 60 ? "pos" : v >= 40 ? "neutral" : "neg" };
    },
    buildSpark: (r) => {
      const v = Number(r.vitality_index ?? r.vitality_score ?? 0);
      return { type: "gauge", values: [v], pct: v };
    }
  },
  {
    modelId: "M-C5",
    block: "C",
    title: "Yirik ob\u02BBekt ta\u02BBsiri",
    endpoint: "/location/anchor-effect",
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, radius_m: p.radius_m }),
    fallback: () => ({ anchor_uplift_pct: 18 }),
    formatHeadline: (r) => ({ label: "Yirik ob\u02BBektlar ko\u02BBtarishi", value: fmtPct(Number(r.anchor_boost_pct ?? r.anchor_uplift_pct ?? 0)), tone: "pos" })
  },
  {
    modelId: "M-C6",
    block: "C",
    title: "Ko\u02BBrinishlik bahosi",
    endpoint: "/location/visibility-score",
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, facade_direction_deg: p.facade_direction_deg }),
    fallback: () => ({ visibility_score: 84 }),
    formatHeadline: (r) => ({ label: "Ko\u02BBrinishlik", value: `${Math.round(Number(r.visibility_score ?? 0))}/100`, tone: "pos" }),
    buildSpark: (r) => ({ type: "gauge", values: [Number(r.visibility_score ?? 0)], pct: Number(r.visibility_score ?? 0) })
  }
];
var D = [
  {
    modelId: "M-D1",
    block: "D",
    title: "Hayotiylik tekshiruvi",
    endpoint: "/financial/viability-check",
    buildInput: (p) => ({ mcc_code: p.mcc_code, region_id: p.region_id, monthly_revenue_estimate: p.monthly_revenue_estimate, monthly_fixed_costs: p.monthly_fixed_costs, initial_investment: p.initial_investment, monthly_rent: p.monthly_rent }),
    fallback: (p) => {
      const net = p.monthly_revenue_estimate - p.monthly_fixed_costs - p.monthly_rent;
      return { viability_score: net > 0 ? 78 : 32, monthly_net_cashflow: net };
    },
    formatHeadline: (r) => {
      const score = r.viability_score !== void 0 ? Number(r.viability_score) : 100 * Number(r.survival_probability_2y ?? 0);
      return { label: "Hayotiylik", value: `${Math.round(score)}/100`, tone: score >= 70 ? "pos" : score >= 50 ? "neutral" : "neg" };
    },
    buildSpark: (r) => {
      const score = r.viability_score !== void 0 ? Number(r.viability_score) : 100 * Number(r.survival_probability_2y ?? 0);
      return { type: "gauge", values: [score], pct: score };
    }
  },
  {
    modelId: "M-D2",
    block: "D",
    title: "Birlik iqtisodi",
    endpoint: "/financial/unit-economics",
    buildInput: (p) => ({ mcc_code: p.mcc_code, avg_transaction_value: p.avg_transaction_value, monthly_transactions: p.monthly_transactions, customer_acquisition_cost: p.customer_acquisition_cost, monthly_churn_rate_pct: p.monthly_churn_rate_pct, gross_margin_pct: p.gross_margin_pct }),
    fallback: (p) => {
      const ltv = p.avg_transaction_value * 12 * (p.gross_margin_pct / 100) / Math.max(0.01, p.monthly_churn_rate_pct / 100);
      return { ltv_to_cac_ratio: ltv / Math.max(1, p.customer_acquisition_cost) };
    },
    formatHeadline: (r) => {
      const v = Number(r.ltv_cac_ratio ?? r.ltv_to_cac_ratio ?? 0);
      return { label: "LTV / CAC", value: `${v.toFixed(1)}\xD7`, tone: v >= 3 ? "pos" : v >= 1 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-D3",
    block: "D",
    title: "ROI hisoblagich",
    endpoint: "/financial/roi-estimator",
    buildInput: (p) => ({ initial_investment: p.initial_investment, monthly_net_cash_flow: Math.max(100, p.monthly_revenue_estimate - p.monthly_fixed_costs - p.monthly_rent), discount_rate_annual_pct: p.discount_rate_annual_pct, horizon_years: Math.max(1, Math.round(p.horizon_months / 12)) }),
    fallback: (p) => {
      const net = Math.max(100, p.monthly_revenue_estimate - p.monthly_fixed_costs - p.monthly_rent);
      return { payback_months: p.initial_investment / net, npv: net * 24 - p.initial_investment, irr_pct: 28 };
    },
    formatHeadline: (r) => ({ label: "Qaytarish", value: `${Number(r.payback_months ?? 0).toFixed(1)} oy`, tone: Number(r.payback_months ?? 99) < 18 ? "pos" : "neg" })
  },
  {
    modelId: "M-D4",
    block: "D",
    title: "Ijara yuki",
    endpoint: "/financial/rental-burden",
    buildInput: (p) => ({ mcc_code: p.mcc_code, monthly_revenue_estimate: p.monthly_revenue_estimate, monthly_rent: p.monthly_rent }),
    fallback: (p) => ({ rent_to_revenue_pct: p.monthly_rent / Math.max(1, p.monthly_revenue_estimate) * 100 }),
    formatHeadline: (r) => {
      const v = Number(r.rent_to_revenue_pct ?? 0);
      return { label: "Ijara yuki", value: fmtPct(v, 1), tone: v < 15 ? "pos" : v < 25 ? "neutral" : "neg" };
    },
    buildSpark: (r) => ({ type: "gauge", values: [Number(r.rent_to_revenue_pct ?? 0)], pct: Math.min(100, Number(r.rent_to_revenue_pct ?? 0) * 3) })
  },
  {
    modelId: "M-D5",
    block: "D",
    title: "Pul oqimi simulyatori",
    endpoint: "/financial/cash-flow-simulator",
    buildInput: (p) => ({ mcc_code: p.mcc_code, region_id: p.region_id, initial_investment: p.initial_investment, monthly_revenue_base: p.monthly_revenue_estimate, monthly_fixed_costs: p.monthly_fixed_costs, cogs_pct: p.cogs_pct, growth_rate_monthly_pct: p.growth_rate_monthly_pct, horizon_months: p.horizon_months }),
    fallback: (p) => {
      let cum = -p.initial_investment;
      const series = Array.from({ length: 24 }, (_, i) => {
        const net = p.monthly_revenue_estimate * Math.pow(1.02, i / 6) * (1 - p.cogs_pct / 100) - p.monthly_fixed_costs - p.monthly_rent;
        cum += net;
        return Math.round(cum);
      });
      return { cumulative_cashflow: series, breakeven_month: series.findIndex((v) => v > 0) + 1 };
    },
    formatHeadline: (r) => {
      const flows = r.monthly_cashflows;
      const explicit = r.break_even_month ?? r.breakeven_month;
      const breakeven = explicit !== void 0 && explicit !== null ? Number(explicit) : flows ? flows.findIndex((f) => Number(f.cumulative) > 0) + 1 : 0;
      return { label: "Tenglik", value: breakeven > 0 ? `M${breakeven}` : "\u2014", tone: breakeven > 0 && breakeven < 24 ? "pos" : "neg" };
    },
    buildSpark: (r) => {
      const flows = r.monthly_cashflows;
      const series = flows?.map((f) => Number(f.cumulative)) ?? (r.cumulative_cashflow ?? []);
      return { type: "line", values: series };
    }
  },
  {
    modelId: "M-D6",
    block: "D",
    title: "COGS va marja",
    endpoint: "/financial/cogs-margin",
    buildInput: (p) => ({ mcc_code: p.mcc_code, monthly_revenue: p.monthly_revenue_estimate, region_id: p.region_id }),
    fallback: (p) => ({ benchmark_cogs_pct: p.cogs_pct, your_cogs_pct: p.cogs_pct, gross_margin_pct: p.gross_margin_pct }),
    formatHeadline: (r) => ({ label: "Yalpi marja", value: fmtPct(Number(r.gross_margin_pct ?? 0)), tone: Number(r.gross_margin_pct ?? 0) >= 50 ? "pos" : "neutral" })
  }
];
var E = [
  {
    modelId: "M-E1",
    block: "E",
    title: "Raqobatchilar tahlili",
    endpoint: "/competition/competitor-intelligence",
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, mcc_code: p.mcc_code }),
    fallback: (p) => ({ competitor_count: competitorsFor(p.population), top_competitor_share_pct: 28 }),
    formatHeadline: (r) => {
      const c1km = r.competitors_1km?.length;
      const c = c1km ?? Number(r.competitor_count ?? 0);
      return { label: "Raqobatchilar", value: String(c), tone: c > 50 ? "neg" : "neutral" };
    }
  },
  {
    modelId: "M-E2",
    block: "E",
    title: "Mijoz ketishi prognozi",
    endpoint: "/competition/churn-prediction",
    buildInput: (p) => ({ mcc_code: p.mcc_code, region_id: p.region_id, monthly_revenue: p.monthly_revenue_estimate, initial_investment: p.initial_investment, owner_experience_years: p.owner_experience_years, location_score: 70, competition_count: competitorsFor(p.population) }),
    fallback: () => ({ year_1_survival_pct: 78, churn_probability: 0.22 }),
    formatHeadline: (r) => {
      let v = Number(r.year_1_survival_pct ?? 0);
      if (!v && r.closure_probability_2y !== void 0) {
        const closure2y = Number(r.closure_probability_2y);
        v = 100 * Math.sqrt(1 - closure2y);
      }
      return { label: "1-yil omon qolish", value: fmtPct(v, 0), tone: v >= 80 ? "pos" : v >= 60 ? "neutral" : "neg" };
    },
    buildSpark: (r) => {
      let v = Number(r.year_1_survival_pct ?? 0);
      if (!v && r.closure_probability_2y !== void 0) {
        v = 100 * Math.sqrt(1 - Number(r.closure_probability_2y));
      }
      return { type: "gauge", values: [v], pct: v };
    }
  },
  {
    modelId: "M-E3",
    block: "E",
    title: "Qoidaviy risk",
    endpoint: "/competition/regulatory-risk",
    buildInput: (p) => ({ mcc_code: p.mcc_code, region_id: p.region_id, business_age_months: p.business_age_months }),
    fallback: () => ({ risk_score: 28, risk_level: "low" }),
    formatHeadline: (r) => {
      const v = Number(r.risk_score ?? 0);
      return { label: "Qoidaviy risk", value: `${Math.round(v)}/100`, tone: v < 30 ? "pos" : v < 60 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-E4",
    block: "E",
    title: "Kirish to\u02BBsig\u02BBi",
    endpoint: "/competition/entry-barrier",
    buildInput: (p) => ({ mcc_code: p.mcc_code, region_id: p.region_id, initial_investment: p.initial_investment }),
    fallback: () => ({ barrier_score: 52 }),
    formatHeadline: (r) => {
      const v = Number(r.barrier_index ?? r.barrier_score ?? 0);
      return { label: "To\u02BBsiq", value: `${Math.round(v)}/100`, tone: "neutral" };
    }
  },
  {
    modelId: "M-E5",
    block: "E",
    title: "Narx bosimi",
    endpoint: "/competition/price-pressure",
    buildInput: (p) => ({ mcc_code: p.mcc_code, region_id: p.region_id, target_price: p.avg_transaction_value, competitor_avg_price: p.avg_transaction_value * 1.1 }),
    fallback: () => ({ pressure_index: 38 }),
    formatHeadline: (r) => {
      const raw = Number(r.price_pressure_score ?? r.pressure_index ?? 0);
      const v = raw <= 1 ? raw * 100 : raw;
      return { label: "Bosim", value: `${Math.round(v)}/100`, tone: v < 40 ? "pos" : v < 70 ? "neutral" : "neg" };
    }
  }
];
var F = [
  {
    modelId: "M-F1",
    block: "F",
    title: "Kredit risk bahosi",
    endpoint: "/credit/risk-score",
    buildInput: (p) => ({ customer_id: "live-" + Date.now(), mcc_code: p.mcc_code, region_id: p.region_id, lat: p.lat, lon: p.lon, monthly_revenue_estimate: p.monthly_revenue_estimate, requested_loan_amount: p.requested_loan_amount, business_age_months: p.business_age_months, owner_credit_history_score: p.owner_credit_history_score, collateral_value: p.collateral_value }),
    fallback: (p) => {
      const pd = Math.max(0.02, Math.min(0.45, (820 - p.owner_credit_history_score) / 800));
      return { pd, score: Math.round(100 - pd * 100), recommendation: pd < 0.18 ? "approve" : "review" };
    },
    formatHeadline: (r) => {
      const credit = Number(r.credit_score ?? 0);
      const v = r.score !== void 0 ? Number(r.score) : Math.round(credit / 10);
      return { label: "Risk bahosi", value: `${v}/100`, tone: v >= 75 ? "pos" : v >= 60 ? "neutral" : "neg" };
    },
    buildSpark: (r) => {
      const credit = Number(r.credit_score ?? 0);
      const v = r.score !== void 0 ? Number(r.score) : credit / 10;
      return { type: "gauge", values: [v], pct: v };
    }
  },
  {
    modelId: "M-F2",
    block: "F",
    title: "Kredit hajmi",
    endpoint: "/credit/loan-sizing",
    buildInput: (p) => ({ monthly_net_cashflow: Math.max(100, p.monthly_revenue_estimate - p.monthly_fixed_costs - p.monthly_rent), monthly_revenue: p.monthly_revenue_estimate, existing_debt_monthly: p.existing_debt_monthly, loan_term_months: p.loan_term_months, interest_rate_annual_pct: p.interest_rate_annual_pct }),
    fallback: (p) => {
      const net = Math.max(100, p.monthly_revenue_estimate - p.monthly_fixed_costs - p.monthly_rent);
      return { max_loan: net * 24 * 0.6 };
    },
    formatHeadline: (r) => {
      const v = Number(r.recommended_loan ?? r.max_loan ?? 0);
      return { label: "Maks. kredit", value: fmtMoney(v), tone: "pos" };
    }
  },
  {
    modelId: "M-F3",
    block: "F",
    title: "DTI prognozi",
    endpoint: "/credit/dti-predictor",
    buildInput: (p) => ({ mcc_code: p.mcc_code, region_id: p.region_id, initial_monthly_revenue: p.monthly_revenue_estimate, proposed_loan_amount: p.requested_loan_amount, loan_term_months: p.loan_term_months, interest_rate_annual_pct: p.interest_rate_annual_pct }),
    fallback: (p) => {
      const monthly_payment = p.requested_loan_amount * (p.interest_rate_annual_pct / 1200) / (1 - Math.pow(1 + p.interest_rate_annual_pct / 1200, -p.loan_term_months));
      return { dti_ratio: monthly_payment / Math.max(100, p.monthly_revenue_estimate * 0.5) };
    },
    formatHeadline: (r) => {
      const v = Number(r.dti_at_12m ?? r.dti_ratio ?? 0);
      return { label: "DTI", value: fmtPct(v), tone: v < 0.4 ? "pos" : v < 0.55 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-F4",
    block: "F",
    title: "NPL ogohlantirish",
    endpoint: "/credit/npl-warning",
    buildInput: (p) => ({ customer_id: "live-" + Date.now(), loan_id: "loan-" + Date.now(), months_since_disbursement: 6, payment_delays_count: 0, revenue_trend_3m_pct: p.growth_rate_monthly_pct * 3, current_dti: 0.35, location_score: 70 }),
    fallback: () => ({ early_warning_score: 22, alert: false }),
    formatHeadline: (r) => {
      const v = r.early_warning_score !== void 0 ? Number(r.early_warning_score) : Number(r.npl_probability ?? 0) * 100;
      return { label: "NPL ogohlantirish", value: `${Math.round(v)}/100`, tone: v < 30 ? "pos" : v < 60 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-F5",
    block: "F",
    title: "Mahsulot tavsiyasi",
    endpoint: "/credit/product-recommender",
    buildInput: (p) => ({ customer_id: "live-" + Date.now(), mcc_code: p.mcc_code, monthly_revenue: p.monthly_revenue_estimate, business_age_months: p.business_age_months, existing_products: [], credit_score: p.owner_credit_history_score }),
    fallback: () => ({ top_product: "Working capital line", fit_score: 86 }),
    formatHeadline: (r) => {
      const recs = r.recommendations;
      const top = recs?.[0]?.product ?? recs?.[0]?.product_name ?? r.top_product ?? r.recommended_product;
      return { label: "Eng mos mahsulot", value: String(top ?? "Aylanma kapital"), tone: "pos" };
    }
  }
];
var G = [
  {
    modelId: "M-G1",
    block: "G",
    title: "Mijoz profili",
    endpoint: "/social/customer-profiler",
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, radius_m: p.radius_m, mcc_code: p.mcc_code }),
    fallback: () => ({ dominant_segment: "Young professionals", dominant_share_pct: 32 }),
    formatHeadline: (r) => {
      const segs = r.segments;
      const top = segs && segs.length ? segs.reduce((a, b) => b.share_pct > a.share_pct ? b : a) : null;
      return { label: "Asosiy segment", value: String(top?.label ?? r.dominant_segment ?? "Aralash"), tone: "pos" };
    }
  },
  {
    modelId: "M-G2",
    block: "G",
    title: "Kunlik aholi",
    endpoint: "/social/day-population",
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, radius_m: p.radius_m, hour_of_day: 14, day_of_week: 3 }),
    fallback: (p) => {
      const hours = Array.from({ length: 24 }, (_, h) => Math.round(800 + 1200 * Math.exp(-Math.pow(h - 13, 2) / 25)));
      return { hourly_population: hours, peak_population: Math.max(...hours), reachable: Math.round(p.population * 0.06) };
    },
    formatHeadline: (r) => {
      const hours = r.hourly_profile ?? r.hourly_population;
      const peak = r.peak_population !== void 0 ? Number(r.peak_population) : hours ? Math.max(...hours) : Number(r.total_population ?? 0);
      return { label: "Cho\u02BBqqi / soat", value: fmtNum(peak), tone: "pos" };
    },
    buildSpark: (r) => {
      const hours = r.hourly_profile ?? r.hourly_population ?? [];
      return { type: "line", values: hours };
    }
  },
  {
    modelId: "M-G3",
    block: "G",
    title: "Xatti-harakat klassifikatori",
    endpoint: "/social/behavior-classifier",
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, radius_m: p.radius_m, mcc_code: p.mcc_code }),
    fallback: () => ({ dominant_behavior: "Convenience-driven", confidence_pct: 78 }),
    formatHeadline: (r) => {
      const types = r.consumer_types;
      const top = types && types.length ? types.reduce((a, b) => b.share_pct > a.share_pct ? b : a) : null;
      return { label: "Xatti-harakat", value: String(top?.type ?? r.dominant_behavior ?? "Aralash"), tone: "neutral" };
    }
  },
  {
    modelId: "M-G4",
    block: "G",
    title: "Brend muvofiqligi",
    endpoint: "/social/brand-affinity",
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, radius_m: p.radius_m, mcc_code: p.mcc_code }),
    fallback: () => ({ premium_affinity_pct: 42 }),
    formatHeadline: (r) => {
      const v = Number(r.chain_preference_pct ?? r.premium_affinity_pct ?? 0);
      return { label: "Brend og\u02BBirligi", value: fmtPct(v), tone: "neutral" };
    },
    buildSpark: (r) => {
      const v = Number(r.chain_preference_pct ?? r.premium_affinity_pct ?? 0);
      return { type: "gauge", values: [v], pct: v };
    }
  },
  {
    modelId: "M-G5",
    block: "G",
    title: "Sarflash quvvati",
    endpoint: "/social/spending-power",
    buildInput: (p) => ({ lat: p.lat, lon: p.lon, radius_m: p.radius_m }),
    fallback: (p) => ({ avg_disposable_income: p.avg_income * 0.45 }),
    formatHeadline: (r) => {
      const v = Number(r.avg_monthly_spend_per_capita ?? r.avg_disposable_income ?? 0);
      return { label: "Sarflash / kishi", value: fmtMoney(v), tone: "pos" };
    }
  }
];
var H = [
  {
    modelId: "M-H1",
    block: "H",
    title: "Mijoz olish narxi (CAC)",
    endpoint: "/marketing/cac-predictor",
    buildInput: (p) => ({ channel: "paid_search", region_id: p.region_id, monthly_budget: Math.max(500, p.monthly_revenue_estimate * 0.1), industry_mcc: p.mcc_code, target_segment: "consumer", historical_cac: p.customer_acquisition_cost, competition_intensity: 0.5 }),
    fallback: (p) => ({ predicted_cac: p.customer_acquisition_cost * 1.2, expected_acquisitions: 100, channel_efficiency: "good" }),
    formatHeadline: (r) => ({ label: "Bashorat CAC", value: fmtMoney(Number(r.predicted_cac ?? 0)), tone: Number(r.predicted_cac ?? 0) < 20 ? "pos" : "neutral" })
  },
  {
    modelId: "M-H2",
    block: "H",
    title: "LTV / CAC nisbati",
    endpoint: "/marketing/ltv-cac-ratio",
    buildInput: (p) => ({ arpu_monthly: Math.max(1, p.avg_transaction_value * (p.monthly_transactions / Math.max(1, p.monthly_transactions))), gross_margin_pct: p.gross_margin_pct / 100, monthly_churn_rate: Math.max(5e-3, p.monthly_churn_rate_pct / 100), discount_rate_annual: p.discount_rate_annual_pct / 100, cac: Math.max(1, p.customer_acquisition_cost) }),
    fallback: (p) => {
      const arpu = p.avg_transaction_value;
      const ltv = arpu * (p.gross_margin_pct / 100) / Math.max(5e-3, p.monthly_churn_rate_pct / 100);
      return { ltv, ltv_cac_ratio: ltv / Math.max(1, p.customer_acquisition_cost), payback_months: Math.max(1, p.customer_acquisition_cost / Math.max(1, arpu * p.gross_margin_pct / 100)), verdict: "healthy" };
    },
    formatHeadline: (r) => {
      const v = Number(r.ltv_cac_ratio ?? 0);
      return { label: "LTV / CAC", value: `${v.toFixed(1)}\xD7`, tone: v >= 3 ? "pos" : v >= 1 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-H3",
    block: "H",
    title: "Kanal atributsiyasi",
    endpoint: "/marketing/channel-attribution",
    buildInput: (p) => ({ journey_id: "live-" + Date.now(), touchpoints: ["social", "paid_search", "email", "organic"], conversion_value: Math.max(10, p.avg_transaction_value) }),
    fallback: () => ({ primary_driver: "paid_search", weights: { paid_search: 0.4, social: 0.25, email: 0.2, organic: 0.15 } }),
    formatHeadline: (r) => ({ label: "Asosiy kanal", value: String(r.primary_driver ?? "paid_search"), tone: "pos" })
  },
  {
    modelId: "M-H4",
    block: "H",
    title: "Promo ko\u02BBtarilishi",
    endpoint: "/marketing/promo-uplift",
    buildInput: (p) => ({ customer_id: "live-" + Date.now(), promo_type: "discount", promo_value: Math.max(1, p.avg_transaction_value * 0.15), customer_recency_days: 30, customer_frequency_30d: 4, customer_monetary_30d: p.avg_transaction_value * 4, historical_response_rate: 0.12 }),
    fallback: () => ({ uplift_probability: 0.18, target_decision: "target", segment: "persuadable", expected_incremental_revenue: 250 }),
    formatHeadline: (r) => ({ label: "Promo qaror", value: String(r.target_decision ?? "target"), tone: "pos" })
  },
  {
    modelId: "M-H5",
    block: "H",
    title: "Optimal narx",
    endpoint: "/marketing/optimal-pricing",
    buildInput: (p) => ({ product_id: "live-" + Date.now(), current_price: Math.max(1, p.avg_transaction_value), current_units_sold: Math.max(1, p.monthly_transactions), unit_cost: p.avg_transaction_value * (p.cogs_pct / 100), elasticity_estimate: -1.5 }),
    fallback: (p) => ({ optimal_price: p.avg_transaction_value * 1.08, expected_revenue: p.avg_transaction_value * p.monthly_transactions * 1.05, revenue_lift_pct: 5, confidence: "medium" }),
    formatHeadline: (r) => ({ label: "Optimal narx", value: fmtMoney(Number(r.optimal_price ?? 0)), tone: "pos" })
  },
  {
    modelId: "M-H6",
    block: "H",
    title: "Lookalike auditoriya",
    endpoint: "/marketing/lookalike-audience",
    buildInput: () => ({
      seed_customer_features: { age: 32, monthly_spend: 450, frequency: 8 },
      candidate_pool: Array.from({ length: 12 }, (_, i) => ({ customer_id: `cand-${i}`, age: 28 + i, monthly_spend: 300 + i * 30, frequency: 3 + i % 6 })),
      top_k: 5
    }),
    fallback: () => ({ avg_similarity: 0.78, matches: [] }),
    formatHeadline: (r) => ({ label: "O\u02BBrtacha o\u02BBxshashlik", value: fmtPct(Number(r.avg_similarity ?? 0)), tone: "pos" })
  }
];
var I = [
  {
    modelId: "M-I1",
    block: "I",
    title: "Inventar optimizatsiyasi",
    endpoint: "/operations/inventory-optimizer",
    buildInput: (p) => ({ sku_id: "live-" + Date.now(), annual_demand: Math.max(50, p.monthly_transactions * 12), unit_cost: Math.max(1, p.avg_transaction_value * (p.cogs_pct / 100)), ordering_cost: 50, holding_cost_pct: 0.2, lead_time_days: 14, demand_std_daily: Math.max(0, p.monthly_transactions / 30 * 0.2), service_level: 0.95 }),
    fallback: (p) => ({ economic_order_quantity: Math.max(10, Math.round(p.monthly_transactions * 0.5)), reorder_point: Math.round(p.monthly_transactions / 30 * 14), total_annual_cost: p.monthly_transactions * 12 * p.avg_transaction_value * (p.cogs_pct / 100) }),
    formatHeadline: (r) => ({ label: "EOQ", value: fmtNum(Number(r.economic_order_quantity ?? 0)), tone: "pos" })
  },
  {
    modelId: "M-I2",
    block: "I",
    title: "Stockout xavfi",
    endpoint: "/operations/stockout-risk",
    buildInput: (p) => ({ sku_id: "live-" + Date.now(), on_hand_units: Math.max(1, Math.round(p.monthly_transactions / 30 * 14)), on_order_units: 0, daily_demand_mean: Math.max(0.1, p.monthly_transactions / 30), daily_demand_std: Math.max(0.05, p.monthly_transactions / 30 * 0.2), lead_time_days_mean: 14, lead_time_days_std: 2, horizon_days: 30 }),
    fallback: () => ({ stockout_probability: 0.08, days_of_cover: 18, risk_level: "low", recommended_action: "monitor" }),
    formatHeadline: (r) => {
      const v = Number(r.stockout_probability ?? 0);
      return { label: "Stockout", value: fmtPct(v), tone: v < 0.1 ? "pos" : v < 0.25 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-I3",
    block: "I",
    title: "Ta\u02BBminotchi riski",
    endpoint: "/operations/supplier-risk",
    buildInput: () => ({ supplier_id: "live-" + Date.now(), months_active: 24, on_time_delivery_rate: 0.92, quality_defect_rate: 0.02, payment_terms_days: 30, payment_delay_avg_days: 3, revenue_concentration_pct: 0.15, single_source_flag: false, geopolitical_risk: 0.3 }),
    fallback: () => ({ risk_score: 280, risk_band: "low", primary_risk_factor: "payment_delay" }),
    formatHeadline: (r) => {
      const v = Number(r.risk_score ?? 0);
      return { label: "Ta\u02BBminotchi xavfi", value: `${Math.round(v)}/1000`, tone: v < 300 ? "pos" : v < 600 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-I4",
    block: "I",
    title: "Xodim grafigi",
    endpoint: "/operations/staffing-optimizer",
    buildInput: (p) => {
      const peak = p.monthly_transactions / 30;
      const hourly = Array.from({ length: 24 }, (_, h) => Math.max(0, Math.round(peak * (h >= 8 && h <= 22 ? Math.exp(-Math.pow(h - 13, 2) / 18) * 4 : 0))));
      return { location_id: "live-" + Date.now(), hourly_demand: hourly, units_per_staff_hour: 10, min_staff_per_open_hour: 1, max_staff: 20, hourly_wage: 5, open_hour: 8, close_hour: 22 };
    },
    fallback: () => ({ total_staff_hours: 60, estimated_labor_cost: 300, peak_hour: 13, peak_hour_staff: 4 }),
    formatHeadline: (r) => ({ label: "Cho\u02BBqqi smena", value: `${r.peak_hour_staff ?? 4} kishi @ ${r.peak_hour ?? 13}:00`, tone: "pos" })
  },
  {
    modelId: "M-I5",
    block: "I",
    title: "Yetkazib berish marshruti",
    endpoint: "/operations/delivery-routing",
    buildInput: (p) => ({
      depot_lat: p.lat,
      depot_lon: p.lon,
      stops: Array.from({ length: 6 }, (_, i) => ({ stop_id: `stop-${i}`, lat: p.lat + (Math.random() - 0.5) * 0.05, lon: p.lon + (Math.random() - 0.5) * 0.05, demand: 1 + Math.random() * 3 })),
      vehicle_capacity: 100,
      n_vehicles: 2
    }),
    fallback: () => ({ total_distance_km: 28.4, n_vehicles_used: 2, routes: [] }),
    formatHeadline: (r) => ({ label: "Umumiy masofa", value: `${Number(r.total_distance_km ?? 0).toFixed(1)} km`, tone: "pos" })
  }
];
var J = [
  {
    modelId: "M-J1",
    block: "J",
    title: "Tranzaksiya anomaliyasi",
    endpoint: "/fraud/transaction-anomaly",
    buildInput: (p) => ({ customer_id: "live-" + Date.now(), transaction_id: "tx-" + Date.now(), amount: Math.max(1, p.avg_transaction_value), mcc_code: p.mcc_code, txn_count_last_24h: 3, txn_count_last_7d: 18, avg_amount_last_30d: p.avg_transaction_value, distinct_merchants_last_24h: 2, is_foreign: false, is_cnp: false, hour_of_day: 14 }),
    fallback: () => ({ anomaly_score: 0.12, is_anomaly: false, risk_level: "low", recommended_action: "allow" }),
    formatHeadline: (r) => {
      const v = Number(r.anomaly_score ?? 0);
      return { label: "Anomaliya", value: `${(v * 100).toFixed(0)}/100`, tone: v < 0.3 ? "pos" : v < 0.6 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-J2",
    block: "J",
    title: "Sotuvchi firibgarlik bahosi",
    endpoint: "/fraud/merchant-fraud",
    buildInput: (p) => ({ merchant_id: "live-" + Date.now(), mcc_code: p.mcc_code, months_active: Math.max(0, p.business_age_months), chargeback_rate_30d: 5e-3, refund_rate_30d: 0.02, avg_ticket_size: Math.max(1, p.avg_transaction_value), txn_velocity_per_day: Math.max(0, p.monthly_transactions / 30), pct_cnp_transactions: 0.1, pct_foreign_cards: 0.02, prior_complaints_count: 0 }),
    fallback: () => ({ fraud_score: 180, fraud_probability: 0.05, risk_band: "low", decision: "monitor" }),
    formatHeadline: (r) => {
      const v = Number(r.fraud_score ?? 0);
      return { label: "Sotuvchi xavfi", value: `${Math.round(v)}/1000`, tone: v < 300 ? "pos" : v < 600 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-J3",
    block: "J",
    title: "AML naqsh",
    endpoint: "/fraud/aml-pattern",
    buildInput: () => ({ customer_id: "live-" + Date.now(), cash_deposits_last_7d: 2, cash_amount_last_7d: 4500, structuring_threshold: 1e4, near_threshold_deposits_30d: 0, rapid_in_out_count_30d: 0, distinct_counterparties_30d: 6, cross_border_count_30d: 0, high_risk_jurisdiction_count: 0 }),
    fallback: () => ({ suspicion_score: 0.1, typology: "none", sar_recommended: false, confidence: 0.85 }),
    formatHeadline: (r) => {
      const v = Number(r.suspicion_score ?? 0);
      return { label: "AML shubha", value: `${(v * 100).toFixed(0)}/100`, tone: v < 0.3 ? "pos" : v < 0.6 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-J4",
    block: "J",
    title: "Sintetik shaxs aniqlash",
    endpoint: "/fraud/synthetic-identity",
    buildInput: (p) => ({ applicant_id: "live-" + Date.now(), credit_file_age_months: Math.max(0, p.owner_experience_years * 12), credit_inquiries_last_6m: 1, address_changes_last_24m: 0, ssn_age_norm: 0.95, phone_tenure_months: 36, email_tenure_months: 48, distinct_names_at_address: 1, employer_verifiable: true }),
    fallback: () => ({ synthetic_probability: 0.04, is_synthetic: false, confidence_band: "high" }),
    formatHeadline: (r) => {
      const v = Number(r.synthetic_probability ?? 0);
      return { label: "Sintetik shaxs", value: fmtPct(v), tone: v < 0.1 ? "pos" : v < 0.3 ? "neutral" : "neg" };
    }
  },
  {
    modelId: "M-J5",
    block: "J",
    title: "Ariza firibgarligi",
    endpoint: "/fraud/application-fraud",
    buildInput: (p) => ({ application_id: "live-" + Date.now(), applications_last_24h: 1, applications_last_30d: 1, device_seen_count_30d: 1, ip_seen_count_30d: 1, declared_income: Math.max(100, p.avg_income * 12), bureau_income_estimate: Math.max(100, p.avg_income * 12 * 0.95), document_quality_score: 0.92, velocity_score: 0.1, geolocation_mismatch: false }),
    fallback: () => ({ fraud_probability: 0.06, decision: "approve", risk_score: 120, income_discrepancy_pct: 5 }),
    formatHeadline: (r) => ({ label: "Ariza qarori", value: String(r.decision ?? "approve"), tone: r.decision === "approve" ? "pos" : r.decision === "review" ? "neutral" : "neg" })
  }
];
var ALL_MODELS = [...A, ...B, ...C, ...D, ...E, ...F, ...G, ...H, ...I, ...J];
export {
  ALL_MODELS,
  BLOCK_META
};
