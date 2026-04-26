# ML Modellar Katalogi

10 ta blokga taqsimlangan 55 ta ishlab chiqarish modeli. Barcha modellar uchun: `version=1.0.0`, `is_stub=false`.

> 🇬🇧 English versiyasi: [`ML_CATALOG.md`](ML_CATALOG.md)

---

## Blok A — Bozor tahlili va sig'imi

### M-A1 — Bozor hajmini baholash (TAM/SAM/SOM)
- **Algoritm**: `scipy.stats.norm` ishonch oraliqlari bilan Bayes uslubidagi pastdan-yuqoriga (bottom-up) tahlil
- **Kirish**: region_id, mcc_code, population, avg_income, niche
- **Chiqish**: tam, sam, som, confidence_interval [past, yuqori], methodology
- **Mantiq**: TAM = aholi × o'rtacha daromad × MCC kirib borish darajasi (5812→15%, 5411→12%, 5912→8%). SAM = TAM × 0,40, SOM = SAM × 0,25. CI log-normal taqsimotidan olinadi.
- **Tushuntirish**: population_weight, income_weight, penetration_rate

### M-A2 — GAP (Tafovut) tahlili
- **Algoritm**: Normativ zichlik hisoblash + `scipy.stats.poisson` statistik test
- **Kirish**: region_id, mcc_code, normative_density, actual_count, population
- **Chiqish**: normative_count, actual_count, gap, gap_pct, verdict (yetishmovchi/muvozanat/to'yingan)
- **Mantiq**: normative_count = aholi/10000 × normativ zichlik. gap = normativ − haqiqiy. Statistik ahamiyat uchun Poisson testi.
- **Tushuntirish**: normative_density_weight, population_scale_weight

### M-A3 — To'yinganlik indeksi
- **Algoritm**: Sigmoid bilan normallashtirilgan kompozit indeks
- **Kirish**: region_id, mcc_code, competitor_count, population, avg_revenue_per_outlet
- **Chiqish**: saturation_index (0–100), level (past/o'rta/yuqori/kritik), components (komponentlar) lug'ati
- **Mantiq**: outlet_density = raqobatchilar / (aholi/10000). Sigmoid normallashtirish. Daromad kontsentratsiyasi omili. Chegaralar: <25=past, <50=o'rta, <75=yuqori, ≥75=kritik.
- **Tushuntirish**: density_component, revenue_component

### M-A4 — Hamyon ulushini baholash (Wallet Share)
- **Algoritm**: Gravitatsion-tuzatilgan Herfindahl ulush modeli
- **Kirish**: region_id, mcc_code, population, avg_monthly_spend, competitor_count
- **Chiqish**: wallet_share_pct, estimated_monthly_revenue, ishonch (0–1)
- **Mantiq**: wallet_share = 1/(1 + raqobatchilar) × MCC_rate × gravity_adjustment. confidence = 0,95 − raqobatchilar × 0,05.
- **Tushuntirish**: competition_discount, mcc_affinity, gravity_factor

### M-A5 — Niche imkoniyatlar bahosi
- **Algoritm**: 500 sintetik namunada o'qitilgan XGBoost regressori
- **Kirish**: region_id, mcc_code, population, avg_income, competitor_count, growth_rate_pct
- **Chiqish**: opportunity_score (0–100), rank (a'lo/yaxshi/o'rta/yomon), top_factors lug'ati
- **Mantiq**: Xususiyatlar: [population_norm, income_norm, competitor_density, growth_rate]. XGBoost klass darajasida bir marta o'rgatiladi (seed=42). Gain asosidagi xususiyat ahamiyatlarini qaytaradi.
- **Tushuntirish**: barcha 4 xususiyat uchun XGBoost gain ahamiyatlari

### M-A6 — Niche-aro kannibalizatsiya
- **Algoritm**: MCC kategoriyalari grafi + haversin masofa bo'yicha pasayish
- **Kirish**: new_mcc_code, location_lat, location_lon, radius_m, adjacent_mcc_codes
- **Chiqish**: cannibalization_risk (0–1), affected_niches ro'yxati, net_revenue_impact_pct, tavsiya
- **Mantiq**: 40+ MCC kodlari guruhlarga taqsimlangan. Bir guruhdagi qo'shnilik = yuqori xavf, qo'shni guruh = o'rta, bog'liq emas = past. Har bir ta'sirlangan niche bo'yicha masofaga qarab pasayish qo'llaniladi.
- **Tushuntirish**: mcc_similarity_weight, distance_decay_weight, group_overlap_weight

---

## Blok B — Bashoratlash va talab

### M-B1 — Talabni bashoratlash
- **Algoritm**: Holt-Winters ExponentialSmoothing (additive trend + mavsumiy, davr=12)
- **Kirish**: region_id, mcc_code, horizon_months (1–36), base_monthly_revenue
- **Chiqish**: bashorat ro'yxati [{month, predicted, lower, upper}], trend, cagr_pct, model_used
- **Mantiq**: MCC-ga xos o'sish bilan 24 oylik sintetik tarix yaratiladi. `statsmodels.tsa.holtwinters.ExponentialSmoothing` o'rgatiladi. 90% bashorat oraliqlari.
- **Tushuntirish**: trend_weight, seasonal_weight, base_weight

### M-B2 — Mavsumiylik modeli
- **Algoritm**: O'zbekistonga xos kalendar voqealari bilan STL uslubidagi dekompozitsiya
- **Kirish**: mcc_code, region_id, year
- **Chiqish**: monthly_indices [12 ta float], peak_months, trough_months, voqealar ro'yxati
- **Mantiq**: Asosiy naqsh MCC kategoriyasiga qarab moslashtiriladi. Ramazon oyi har yil uchun hisoblanadi (2024–2030 jadvali). 7 ta voqea: Navro'z (Mart), Ramazon hayiti, Qurbon hayiti, to'y mavsumlari (May–Iyun, Sen–Okt), Yangi yil.
- **Tushuntirish**: base_seasonality, event_adjustments, mcc_modifier

### M-B3 — Aholi dinamikasi
- **Algoritm**: Kogort-komponent demografik model
- **Kirish**: region_id, horizon_years (1–20)
- **Chiqish**: prognozlar [{year, population, working_age_pct}], growth_rate_annual_pct, demographic_shift
- **Mantiq**: O'sish darajasi region_id hash dan olinadi → 1,5%–3,5% oralig'i. working_age_pct 65% dan boshlanadi, yiliga +0,15% (urbanizatsiya). 14 ta O'zbekiston viloyati.
- **Tushuntirish**: base_growth_rate, urbanisation_trend, regional_coefficient

### M-B4 — Daromad trendi prognozi
- **Algoritm**: `statsmodels.tsa.arima.ARIMA` orqali ARIMA(1,1,1)
- **Kirish**: region_id, horizon_months (3–36), current_avg_income
- **Chiqish**: bashorat [{month, avg_income, lower, upper}], real_growth_rate_pct, inflation_adjusted=true
- **Mantiq**: region_id bilan urug'lantirilgan sintetik daromad tarixiga ARIMA o'rgatiladi. Makro parametrlar qo'llaniladi: 12,8% nominal, 9,2% inflyatsiya → 3,6% real o'sish.
- **Tushuntirish**: trend_component, ar_coefficient, ma_coefficient

### M-B5 — MCC trend detektori
- **Algoritm**: `ruptures.Pelt` o'zgarish nuqtasini aniqlash (rbf yadrosi)
- **Kirish**: mcc_code, region_id, lookback_months (6–60)
- **Chiqish**: trend_direction (o'sayotgan/pasayayotgan/barqaror/o'zgaruvchan), changepoints [{date, type, magnitude}], momentum_score (-1 dan 1 gacha), forecast_3m_pct
- **Mantiq**: MCC-ga xos o'sish koeffitsientlari bilan sintetik daromad qatori yaratiladi. PELT o'zgarish nuqtasini aniqlash. Momentum = normallashtirilgan oxirgi nishab.
- **Tushuntirish**: momentum_score, changepoint_count, recent_slope

### M-B6 — Biznesni ro'yxatdan o'tkazish bashorati
- **Algoritm**: `statsmodels.tsa.ar_model.AutoReg(lags=3)` + XGBoost
- **Kirish**: region_id, mcc_code, horizon_months (3–24)
- **Chiqish**: bashorat [{month, new_registrations, cumulative}], annual_growth_pct, competition_intensity
- **Mantiq**: Poisson taqsimotli sintetik ro'yxat tarixiga AutoReg. MCC-ga xos asosiy stavkalar va o'sish ko'paytmalari. Raqobat intensivligi ro'yxat tezlanishidan kelib chiqadi.
- **Tushuntirish**: ar_coefficient, mcc_base_rate, region_multiplier

---

## Blok C — Joylashuvni baholash va qatnov

### M-C1 — Joylashuv balli
- **Algoritm**: 8 ta omilli og'irlikli kompozit indeks
- **Kirish**: lat, lon, mcc_code, radius_m
- **Chiqish**: ball (0–100), darajа (A/B/C/D/F), sub_scores lug'ati (8 kalit), tavsiya
- **Mantiq**: Quyi ballar: traffic, competition, vitality, anchor, visibility, isochrone, demographic, income. MCC-ga xos og'irliklar (restoranlar traffic/anchor ga ko'proq, do'konlar isochrone/demographic ga). Daraja: ≥90=A, ≥80=B, ≥70=C, ≥60=D, qolgan=F.
- **Tushuntirish**: har bir quyi ball bo'yicha og'irlik

### M-C2 — Qatnov baholash
- **Algoritm**: 2000 sintetik GPS+vaqt namunasida o'qitilgan `sklearn.GradientBoostingRegressor`
- **Kirish**: lat, lon, radius_m
- **Chiqish**: daily_foot_traffic, daily_auto_traffic, peak_hours, peak_days, hourly_profile [24 float], seasonal_factor
- **Mantiq**: Xususiyatlar: [lat_norm, lon_norm, hour/23, dow/6]. Klass darajasida bir marta o'rgatiladi (seed=0). Kunning barcha 24 soati uchun bashorat. M-C2 hech qachon Redis-da keshlanmaydi (har doim "live").
- **Tushuntirish**: GradientBoosting xususiyat ahamiyatlari

### M-C3 — Izoxron talab
- **Algoritm**: Doiraviy izoxron yaqinlashuvi + gravitatsion model
- **Kirish**: lat, lon, walk_minutes [ro'yxat], mcc_code
- **Chiqish**: zonalar [{minutes, area_sqkm, population, consumer_potential_usd}], total_addressable_population, total_consumer_potential_usd
- **Mantiq**: Yurish tezligi = 1,2 m/s. maydon = π × r². Aholi zichligi Toshkent markazidan masofaga ko'ra baholanadi. MCC-ga xos kunlik xarajat va kirib borish darajasi.
- **Tushuntirish**: area_weight, density_weight, penetration_weight

### M-C4 — Ko'cha jonliligi indeksi
- **Algoritm**: Spatial hash → zichlik darajasi tasnifi + POI bahosi
- **Kirish**: lat, lon, radius_m
- **Chiqish**: vitality_index (0–100), active_storefronts, vacant_storefronts, poi_count, dominant_categories
- **Mantiq**: Uchta zichlik darajasi (shahar markazi/atrof/qishloq) — POI zichligi, bo'sh do'konlar nisbati va kategoriyalar shularga moslashtiriladi. Daraja ichidagi o'zgarish uchun spatial hash.
- **Tushuntirish**: active_share_weight, poi_density_weight, vacancy_penalty

### M-C5 — Anchor (langar) effekti modeli
- **Algoritm**: Nyutonning gravitatsion modeli (G = massa / d²)
- **Kirish**: lat, lon, radius_m
- **Chiqish**: anchor_boost_pct, anchors [{name, type, distance_m, gravity_score}], dominant_anchor
- **Mantiq**: 12 ta sintetik langar turi (savdo markazlari, bozorlar, shifoxonalar, transport tugunlari, masjidlar, universitetlar). Haversin masofalar. anchor_boost = gravity hissalarining yig'indisi, 80% bilan cheklangan.
- **Tushuntirish**: gravity_mass_weight, distance_decay_power

### M-C6 — Ko'rinish balli
- **Algoritm**: Trigonometriyaga asoslangan geometrik tahlil
- **Kirish**: lat, lon, facade_direction_deg
- **Chiqish**: visibility_score (0–100), road_frontage_m, sidewalk_width_m, sight_lines lug'ati, to'siqlar ro'yxati
- **Mantiq**: Ko'cha frontoni va piyoda yo'lakcha eni lat/lon trigonometrik hash dan baholanadi. Har bir kompas yo'nalishi bo'yicha ko'rish chiziqlari fasad burchagini hisobga oladi. To'siqlar joylashuv darajasiga qarab tanlanadi.
- **Tushuntirish**: frontage_weight, sight_line_weight, direction_bonus

---

## Blok D — Moliyaviy maqbullik

### M-D1 — Maqbullik tekshiruvi
- **Algoritm**: Monte Carlo simulyatsiyasi (500 ta tirajlanish, 24 oy)
- **Kirish**: mcc_code, region_id, monthly_revenue_estimate, monthly_fixed_costs, initial_investment, monthly_rent
- **Chiqish**: survival_probability_2y (0–1), verdict (maqbul/o'rta/yuqori xavf), key_risks ro'yxati, monthly_break_even, months_to_break_even
- **Mantiq**: Har bir tirajda daromad (−20% dan +30% gacha) va xarajatlar (±15% σ) o'zgartiriladi. 12 oylik mavsumiy naqsh qo'llaniladi. MCC-ga xos boshlang'ich omon qolish koeffitsientlari (restoranlar −5%, dorixona +5%). Survival = 24-oyda kümulyativ foyda > 0 bo'lgan tirajlar ulushi. Takrorlash uchun seed kirishlardan olinadi.
- **Tushuntirish**: revenue_sensitivity, cost_volatility, mcc_risk_prior

### M-D2 — Birlik iqtisodiyoti (Unit Economics)
- **Algoritm**: Kogortlar bo'yicha LTV tahlili
- **Kirish**: mcc_code, avg_transaction_value, monthly_transactions, customer_acquisition_cost, monthly_churn_rate_pct, gross_margin_pct
- **Chiqish**: ltv, cac, ltv_cac_ratio, payback_months, net_margin_pct, unit_economics_grade
- **Mantiq**: LTV = (avg_transaction × monthly_txn × margin%) / churn_rate. Net margin uchun MCC-ga xos opex koeffitsientlari (restoranlar 70%, dasturiy ta'minot 45%). Daraja LTV/CAC bo'yicha: A ≥ 3, B ≥ 2, C ≥ 1, D ≥ 0,5, qolgan F.
- **Tushuntirish**: ltv_driver, churn_impact, margin_component

### M-D3 — ROI baholash
- **Algoritm**: DCF + aniq IRR uchun `scipy.optimize.brentq`
- **Kirish**: initial_investment, monthly_net_cash_flow, discount_rate_annual_pct, horizon_years
- **Chiqish**: npv, irr_pct, payback_months, roi_pct, verdict
- **Mantiq**: NPV = Σ(CF/(1+r)^t) − I. IRR brentq orqali oylik koeffitsient maydonida [1e-8, 5,0] qidiriladi. Qaytim davri kasr interpolyatsiyasi. Verdict: musbat NPV + IRR > diskont = "kuchli", musbat NPV = "maqbul", aks holda "zarar".
- **Tushuntirish**: npv_sensitivity, payback_efficiency, irr_vs_hurdle

### M-D4 — Ijara yuki modeli
- **Algoritm**: MCC-ga moslashtirilgan chegara modeli
- **Kirish**: mcc_code, monthly_revenue_estimate, monthly_rent
- **Chiqish**: rent_to_revenue_pct, safe_threshold_pct, critical_threshold_pct, status (xavfsiz/ogohlantirish/kritik), max_affordable_rent
- **Mantiq**: MCC-ga xos chegaralar: restoranlar safe=15%/critical=25%, do'konlar safe=10%/critical=18%, dasturiy ta'minot safe=25%/critical=40%. Status nisbat bo'yicha aniqlanadi.
- **Tushuntirish**: mcc_threshold_adjustment, revenue_base_weight

### M-D5 — Pul oqimi simulyatori
- **Algoritm**: Monte Carlo pul oqimi (500 simulyatsiya, P50 stsenariy)
- **Kirish**: mcc_code, region_id, initial_investment, monthly_revenue_base, monthly_fixed_costs, cogs_pct, growth_rate_monthly_pct, horizon_months
- **Chiqish**: monthly_cashflows [{month, revenue, costs, net_cashflow, cumulative}], total_net, cash_gap_months, break_even_month, final_balance
- **Mantiq**: 500 ta tiraj. Daromad = baza × (1+o'sish)^m × mavsumiylik × N(1, MCC_std). xarajatlar = qat'iy + cogs%×daromad. P50 stsenariy qaytariladi. cash_gap_months = kümulyativ < 0 bo'lgan oylar.
- **Tushuntirish**: growth_sensitivity, seasonality_impact, cogs_pressure

### M-D6 — COGS va marja baholash
- **Algoritm**: MCC etalon qidiruvi + viloyat va miqyos sozlamalari
- **Kirish**: mcc_code, monthly_revenue, region_id
- **Chiqish**: cogs_pct, gross_margin_pct, operating_margin_pct, net_margin_pct, benchmark_source, industry_comparison
- **Mantiq**: 20+ MCC etalon yozuvi. Toshkent viloyatida +5–8% xarajat indeksi. Daromad miqyosi effekti (oyiga $100k uchun +2,5% marja). industry_comparison etalon medianasiga qarama-qarshi.
- **Tushuntirish**: mcc_benchmark, region_cost_adjustment, scale_effect

---

## Blok E — Raqobat va xatarlar

### M-E1 — Raqobatchilar tahlili
- **Algoritm**: MD5 bilan urug'lantirilgan haversin spatial qidiruv
- **Kirish**: lat, lon, mcc_code, radius_300m, radius_1km
- **Chiqish**: competitors_300m ro'yxati, competitors_1km ro'yxati, total_count, avg_rating, market_leader, threat_level
- **Mantiq**: Raqobatchilar soni va joylari MD5(mcc_code + lat_yumalandi + lon_yumalandi) dan urug'lantiriladi. 300m ichida 0–3 raqobatchi, 1km ichida 0–8. threat_level: <2=past, <5=o'rta, <8=yuqori, ≥8=kritik.
- **Tushuntirish**: density_factor, proximity_weight, market_concentration

### M-E2 — Yopilish bashorati (Churn)
- **Algoritm**: XGBoost klassifikatori (1000 sintetik namuna) + Kaplan-Meier omon qolish egri chizig'i
- **Kirish**: mcc_code, region_id, monthly_revenue, initial_investment, owner_experience_years, location_score, competition_count
- **Chiqish**: closure_probability_2y (0–1), risk_level (past/o'rta/yuqori), top_risk_factors, survival_curve [{month, survival_probability}]
- **Mantiq**: Xususiyatlar: [revenue_to_investment_ratio, owner_experience_norm, location_score_norm, competition_density, mcc_risk_factor]. Survival curve `scipy.stats.expon.sf()` orqali.
- **Tushuntirish**: XGBoost xususiyat ahamiyatlari

### M-E3 — Tartibga solish xavfi balli
- **Algoritm**: MCC asosidagi qoidaviy klassifikator (17 kategoriya)
- **Kirish**: mcc_code, region_id, business_age_months
- **Chiqish**: risk_score (0–100), risk_level (past/o'rta/yuqori), applicable_regulations, inspection_frequency, common_violations
- **Mantiq**: MCC → tartibga solish kategoriyasi (oziq-ovqat xavfsizligi, farmatsevtika, moliyaviy va h.k.). Har bir kategoriya bazaviy xavfi. Yoshga ko'ra kamayish (har yiliga −1,5, max −15). Viloyat ko'paytmasi.
- **Tushuntirish**: regulatory_category_weight, age_reduction, region_multiplier

### M-E4 — Bozorga kirish to'sig'i indeksi
- **Algoritm**: 5 komponentli og'irlikli kompozit
- **Kirish**: mcc_code, region_id, initial_investment
- **Chiqish**: barrier_index (0–100), barrier_level (past/o'rta/yuqori/juda yuqori), components lug'ati, tavsiya
- **Mantiq**: Komponentlar: capital(40) + regulatory(30) + brand_loyalty(15) + economies_of_scale(10) + switching_costs(5). Har biri MCC-ga xos koeffitsientlar bilan og'irlanadi.
- **Tushuntirish**: har komponent bo'yicha og'irlik

### M-E5 — Narx bosimi modeli
- **Algoritm**: Hedonik narx + MCC-ga xos elastiklik
- **Kirish**: mcc_code, region_id, target_price, competitor_avg_price
- **Chiqish**: price_pressure_score (0–1), optimal_price_range [min, max], price_elasticity, recommended_price, margin_at_recommended
- **Mantiq**: Elastiklik diapazoni MCC bo'yicha −0,9 dan −2,5 gacha. Optimal oraliq: [raqobatchi×0,90, raqobatchi×1,10]. price_pressure = |target − competitor| / competitor.
- **Tushuntirish**: elasticity_coefficient, competitive_gap, region_price_index

---

## Blok F — Kredit va bank mahsulotlari

### M-F1 — Kredit xavfi balli
- **Algoritm**: 2000 sintetik namunada o'qitilgan LightGBM klassifikator
- **Kirish**: customer_id, mcc_code, region_id, lat, lon, monthly_revenue_estimate, requested_loan_amount, business_age_months, owner_credit_history_score, collateral_value
- **Chiqish**: credit_score (0–1000), risk_grade (AAA/AA/A/BBB/BB/B/CCC), default_probability (0–1), max_recommended_loan, decision (tasdiqlash/shartli/rad), conditions ro'yxati
- **Mantiq**: 6 ta xususiyat: [credit_hist_norm, revenue_coverage_ratio, age_norm, collateral_ratio, location_risk, mcc_risk]. LightGBM seed=42 bilan. Ball oraliqlari: ≥800=AAA/tasdiq, ≥700=AA, ≥600=A, ≥500=BBB/shartli, ≥400=BB, ≥300=B/rad, qolgan CCC.
- **Tushuntirish**: LightGBM xususiyat ahamiyatlari (gain)

### M-F2 — Kredit hajmi tavsiyachisi
- **Algoritm**: Standart annuitet formulasi + 43% DTI cheklovi
- **Kirish**: monthly_net_cashflow, monthly_revenue, existing_debt_monthly, loan_term_months, interest_rate_annual_pct
- **Chiqish**: recommended_loan, max_loan, monthly_payment, dti_ratio, affordability_verdict
- **Mantiq**: monthly_payment = L × r(1+r)^n / ((1+r)^n − 1). max_loan DTI=43% chegarasi orqali. recommended = min(max_loan, 2,5 × yillik daromad) × 0,80.
- **Tushuntirish**: dti_constraint_weight, cashflow_coverage_weight, term_factor

### M-F3 — DTI bashoratchisi
- **Algoritm**: MCC-ga xos daromad o'sishi proyeksiyasi + annuitet to'lov
- **Kirish**: mcc_code, region_id, initial_monthly_revenue, proposed_loan_amount, loan_term_months, interest_rate_annual_pct
- **Chiqish**: dti_at_6m, dti_at_12m, dti_at_24m, safe_threshold=0.43, risk_periods, trayektoriya
- **Mantiq**: MCC-ga xos oylik o'sish (0,7%–1,5%). Daromad 6/12/24 oyga proyeksiyalanadi. DTI = oylik to'lov / proyeksiyalangan daromad. trayektoriya: pasayuvchi DTI = yaxshilanmoqda, aks holda yomonlashmoqda.
- **Tushuntirish**: growth_rate_assumption, payment_to_revenue_ratio

### M-F4 — NPL erta ogohlantirish
- **Algoritm**: `sklearn.IsolationForest` + qoidaviy tuzatish qatlami
- **Kirish**: customer_id, loan_id, months_since_disbursement, payment_delays_count, revenue_trend_3m_pct, current_dti, location_score
- **Chiqish**: npl_probability (0–1), alert_level (yashil/sariq/to'q sariq/qizil), days_to_potential_default, recommended_actions, anomaly_flags
- **Mantiq**: IsolationForest 1000 ta sog'lom qarz namunasida o'rgatiladi. Qoidaviy tuzatishlar: har kechikish uchun +0,20, DTI > 0,6 bo'lsa +0,15, daromad trendi < −10% bo'lsa +0,10. Daraja: <0,20=yashil, <0,40=sariq, <0,65=to'q sariq, qolgan=qizil.
- **Tushuntirish**: anomaly_score, payment_delay_penalty, dti_risk_flag

### M-F5 — Bank mahsuloti tavsiyachisi
- **Algoritm**: Tarkib asosidagi kollaborativ filtrlash
- **Kirish**: customer_id, mcc_code, monthly_revenue, business_age_months, existing_products, credit_score
- **Chiqish**: recommendations [{product, type, score, rationale, amount_range}], primary_recommendation, cross_sell_opportunities
- **Mantiq**: 7 ta mahsulot: business_loan, overdraft, leasing, bank_guarantee, factoring, deposit, pos_terminal. Score = credit_score × revenue × age affinity × MCC_weight, normallashtirilgan. Mavjud mahsulotlar filtrlab tashlanadi. Top 3 qaytariladi.
- **Tushuntirish**: credit_score_weight, revenue_affinity, mcc_product_match

---

## Blok G — Ijtimoiy profil va auditoriya

### M-G1 — Mijoz segmenti profilchisi
- **Algoritm**: 1000 sintetik namunada o'rgatilgan K-means (k=4)
- **Kirish**: lat, lon, radius_m, mcc_code
- **Chiqish**: segments [{segment_id, label, share_pct, avg_age, avg_income, top_categories, visit_frequency}], dominant_segment, total_addressable_customers
- **Mantiq**: 4 segment: "Yosh shahar aholisi" (22–35, yuqori chastota), "Oilaviy xaridorlar" (30–45, o'rta), "Premium xaridorlar" (35–55, past chastota yuqori xarajat), "Iqtisodiy xaridorlar" (25–50, yuqori chastota past xarajat). Share_pct IDW masofalardan. total_addressable = π×(r/1000)² × 8000.
- **Tushuntirish**: cluster_distance_weights, mcc_segment_affinity

### M-G2 — Kunlik aholini baholash
- **Algoritm**: 24-soatlik ish kuni/dam olish kuni profillari bilan gravitatsion model
- **Kirish**: lat, lon, radius_m, hour_of_day (0–23), day_of_week (0–6)
- **Chiqish**: residents, workers, visitors, transit_passers, total_population, hourly_profile [24 int]
- **Mantiq**: base_population = π×(r/1000)² × 8000. residents=60%. Ishchilar 8–18 da ish kunlarida cho'qqiga chiqadi. Mehmonlar/o'tuvchilar soat va kunga qarab o'zgaradi. M-G2 hech qachon Redis-da keshlanmaydi (har doim "live").
- **Tushuntirish**: resident_base_weight, worker_profile_hour, visitor_day_multiplier

### M-G3 — Iste'molchi xulq-atvori klassifikatori
- **Algoritm**: 4 ta iste'molchi turi profili bilan MCC asosidagi qoidalar dvigatel
- **Kirish**: lat, lon, radius_m, mcc_code
- **Chiqish**: consumer_types [{type, share_pct, peak_hours, avg_spend, description}], dominant_type, marketing_insight
- **Mantiq**: MCC qidiruv jadvali: 5812→[ertalabki qahva tolasi, tushlik tolasi, kechki ovqatchilar], 5411→[ertalabki xaridorlar, kechki ovqatchilar], 5912→[sog'lom turmush tarafdorlari, keksalar]. Fallback profili.
- **Tushuntirish**: mcc_type_affinity, location_modifier

### M-G4 — Brend yaqinligi modeli
- **Algoritm**: O'zbek shahar markazlaridan haversin orqali shaharlik bali
- **Kirish**: lat, lon, radius_m, mcc_code
- **Chiqish**: chain_preference_pct (0–100), independent_preference_pct (0–100), top_chains, brand_loyalty_index (0–1), opportunity_type (chain/independent/aralash)
- **Mantiq**: chain_pct Toshkent, Samarqand, Namangan ga yaqinlikka qarab 20–80% oralig'ida. top_chains MCC bo'yicha (5812→["Dodo Pizza","Burger House","Coffee House"]). loyalty_index = chain_pct/100 × 0,80.
- **Tushuntirish**: urban_proximity_score, chain_density_index

### M-G5 — Xarid quvvati indeksi
- **Algoritm**: Inverse-Distance Weighting (IDW) spatial interpolyatsiya
- **Kirish**: lat, lon, radius_m
- **Chiqish**: spending_power_index (0–100), avg_monthly_spend_per_capita, quartile (Q1/Q2/Q3/Q4), heatmap_cells [{lat, lon, index}], category_breakdown lug'ati
- **Mantiq**: 5 ta shahar etalon nuqtasidan IDW. Radius ichida 5×5 heatmap to'ri yaratiladi. avg_monthly_spend = 150 + index × 5 (USD). Quartile indeks qiymatiga ko'ra.
- **Tushuntirish**: idw_weights, reference_point_distances

---

## Blok H — Marketing va mijoz jalb qilish

### M-H1 — CAC bashoratchisi
- **Algoritm**: 2000 namunada o'rgatilgan GradientBoostingRegressor (channel × region × MCC × budget)
- **Kirish**: channel, region_id, monthly_budget, industry_mcc, target_segment, historical_cac, competition_intensity
- **Chiqish**: predicted_cac, cac_range_low/high, expected_acquisitions, channel_efficiency, drivers
- **Mantiq**: Kanal/viloyat/MCC bazalari × byudjet miqyosi-iqtisodiyot termi × raqobat intensivligi. Agar `historical_cac > 0` bo'lsa, model chiqishi bilan 70/30 nisbatda aralashtiriladi (Bayesian shrinkage).
- **Tushuntirish**: GBR xususiyat ahamiyatlari og'irliklarga normallashtirilgan

### M-H2 — LTV / CAC nisbati
- **Algoritm**: Oylik diskontlash bilan yopiq shakldagi kontrakt LTV + qaytarish davri
- **Kirish**: arpu_monthly, gross_margin_pct, monthly_churn_rate, discount_rate_annual, cac
- **Chiqish**: ltv, ltv_cac_ratio, payback_months, verdict (barqaror emas/o'rta/sog'lom/a'lo), tavsiyalar
- **Mantiq**: `LTV = ARPU × marja / (churn + monthly_discount)`. Verdict chegaralari: <1, 1–3, 3–5, >5. Payback = `CAC / contribution`.
- **Tushuntirish**: ARPU, marja, churn, CAC og'irliklari

### M-H3 — Kanal atributsiyasi
- **Algoritm**: Shapley qiymati (≤7 noyob teginishlar uchun aniq, aks holda Monte Carlo)
- **Kirish**: journey_id, touchpoints (tartibli ro'yxat), conversion_value
- **Chiqish**: weights {kanal→ulush}, credit {kanal→$}, primary_driver, method
- **Mantiq**: Kooperativ-o'yin qiymat funktsiyasi `v(S) = 1 − ∏(1 − lift_ch)` kanallar to'plami ustida. Shapley = barcha tartiblar bo'yicha o'rtacha marjinal hissa.
- **Tushuntirish**: shapley_marginal_contribution

### M-H4 — Promo Uplift
- **Algoritm**: Ikki modelli uplift (alohida treated/control GBM klassifikatorlar), CATE = P(buy|T) − P(buy|C)
- **Kirish**: customer_id, promo_type, promo_value, RFM xususiyatlar (recency/frequency/monetary), historical_response_rate
- **Chiqish**: uplift_probability, treated/control javob ehtimolliklari, expected_incremental_revenue, target_decision, segment
- **Mantiq**: To'rt-kvadrant segmentatsiyasi: `persuadable` (uplift > 0,05), `sleeping_dog` (uplift < −0,05), `sure_thing` (ikkalasi ham ≥ 0,5), `lost_cause` (qolgan). Faqat `persuadable` segmenti targetlanadi; `sleeping_dog` bostiriladi.
- **Tushuntirish**: treated va control modellar bo'yicha o'rtacha xususiyat ahamiyatlari

### M-H5 — Optimal narx
- **Algoritm**: Log-log narx elastikligi → Lerner mark-up `p* = MC × ε / (ε + 1)` (`ε < −1` uchun)
- **Kirish**: product_id, current_price, current_units_sold, unit_cost, elasticity_estimate, ixtiyoriy price_floor/ceiling
- **Chiqish**: optimal_price, expected_units, expected_revenue, expected_margin, revenue_lift_pct, margin_lift_pct, ishonch
- **Mantiq**: O'zgarmas elastiklikli talab `Q(p) = Q0 × (p/p0)^ε`. Inelastik holat (ε ≥ −1) uchun +25% (ceiling bilan cheklangan). Floor/ceiling kuchga kiritiladi.
- **Tushuntirish**: elasticity, unit_cost, current_price og'irliklari

### M-H6 — Lookalike auditoriya
- **Algoritm**: Sonli xususiyat vektorlari ustida cosine-similarity k-NN
- **Kirish**: seed_customer_features (lug'at), candidate_pool (lug'atlar ro'yxati), top_k
- **Chiqish**: matches [{customer_id, similarity}], avg_similarity, seed_features_used
- **Mantiq**: Vektorlash uchun seed dagi sonli kalitlar kesishmasi ishlatiladi; standartlashtirilgan vektorlar ustida cosine sim; kamayish tartibida saralash; top_k.
- **Tushuntirish**: cosine_similarity (yagona xususiyat)

---

## Blok I — Operatsiyalar va ta'minot zanjiri

### M-I1 — Inventarizatsiya optimallashtiruvchi
- **Algoritm**: EOQ + (s, S) siyosati va normal-yaqinlashuvli xavfsiz zaxira
- **Kirish**: sku_id, annual_demand, unit_cost, ordering_cost, holding_cost_pct, lead_time_days, demand_std_daily, service_level
- **Chiqish**: economic_order_quantity, reorder_point, safety_stock, annual_orders, total_annual_cost, target_service_level
- **Mantiq**: `EOQ = sqrt(2DK/h)`; safety = `z(SL) × σ_LT`; reorder point = `μ_LT + safety`. Umumiy xarajat = ordering + holding + safety holding.
- **Tushuntirish**: annual_demand 0,40, ordering_cost 0,20, holding 0,20, lead_time 0,10, service_level 0,10

### M-I2 — Mahsulot tugashi xavfi (Stockout)
- **Algoritm**: Normal yaqinlashuvli talab × yetkazib berish vaqti dum ehtimolligi
- **Kirish**: sku_id, on_hand_units, on_order_units, kunlik talab o'rtacha/std, lead-time o'rtacha/std, horizon_days
- **Chiqish**: stockout_probability, expected_stockout_days, days_of_cover, risk_level, recommended_action
- **Mantiq**: (horizon + LT) bo'yicha kümulyativ talab ≈ Normal(μ×T, σ×√T). Stockout ehtimolligi = `1 − Φ((available − μ)/σ)`. Talab dispersiyasini va lead-time dispersiyasini birlashtiradi.
- **Tushuntirish**: available_inventory 0,40, demand_rate 0,30, demand_volatility 0,15, lead_time 0,15

### M-I3 — Yetkazib beruvchi xavfi balli
- **Algoritm**: Og'irlikli ko'p omilli qoidaviy hisoblagich
- **Kirish**: supplier_id, months_active, on_time_delivery_rate, quality_defect_rate, payment_delay_avg_days, revenue_concentration_pct, single_source_flag, geopolitical_risk
- **Chiqish**: risk_score (0–1000), risk_band, primary_risk_factor, contingency_actions
- **Mantiq**: Og'irliklar — delivery 0,22, quality 0,18, concentration 0,18, geopolitical 0,15, single_source 0,12, payment 0,10, tenure 0,05. Diapazon chegaralari: <250 past, <500 o'rta, <750 yuqori, ≥750 jiddiy.
- **Tushuntirish**: Har omil bo'yicha og'irlikli hissalar

### M-I4 — Xodimlar grafigi optimallashtiruvchisi
- **Algoritm**: Soatlik talab → ceil(staff slots), min/max chegaralar va ochilish/yopilish soatlari
- **Kirish**: location_id, hourly_demand (24 uzunlik), units_per_staff_hour, min/max staff, ochilish/yopilish soatlari, hourly_wage
- **Chiqish**: hourly_staff (24 uzunlik), total_staff_hours, estimated_labor_cost, peak_hour, peak_hour_staff
- **Mantiq**: Har bir ochiq soat uchun: `staff_h = clip(ceil(demand_h / units_per_staff_hour), min, max)`. Yopiq soatlar = 0. Tungi grafiklar wrap-around orqali qo'llab-quvvatlanadi.
- **Tushuntirish**: hourly_demand 0,60, units_per_staff_hour 0,20, min_max_constraints 0,20

### M-I5 — Yetkazib berish marshrutlash (VRP)
- **Algoritm**: Sig'im chegarasi bilan Clarke-Wright savings evristikasi (haversin masofasi)
- **Kirish**: depot_lat/lon, stops [{stop_id, lat, lon, demand}], vehicle_capacity, n_vehicles
- **Chiqish**: routes [{vehicle_id, stop_sequence, distance_km, load}], total_distance_km, n_vehicles_used, unrouted_stops
- **Mantiq**: Har bir to'xtash o'z borib-keluvchi marshruti sifatida boshlanadi; kattaroq tejash `s_ij = d(0,i) + d(0,j) − d(i,j)` bo'yicha sig'imni hisobga olib birlashtiriladi. Ortib qolgan to'xtashlar `unrouted` sifatida qaytariladi.
- **Tushuntirish**: stop_geography 0,50, vehicle_capacity 0,30, fleet_size 0,20

---

## Blok J — Firibgarlik, AML va shaxsni aniqlash

> **Keshlash:** Barcha Blok J modellari Redis bashorat keshini chetlab o'tadi (`_NO_CACHE`) — firibgarlik signallari har doim joriy holatni aks ettiradi.

### M-J1 — Tranzaksiya anomaliyasini aniqlash
- **Algoritm**: amount/velocity/MCC xususiyatlari ustida IsolationForest (3000 namuna) + qoida qatlami
- **Kirish**: customer_id, transaction_id, amount, mcc_code, velocity (24h/7d), avg_amount_30d, distinct_merchants_24h, is_foreign, is_cnp, hour_of_day
- **Chiqish**: anomaly_score (0–1), is_anomaly, risk_level (past/o'rta/yuqori/kritik), triggered_rules, recommended_action
- **Mantiq**: Sigmoid bilan moslashtirilgan IsolationForest balli (kalibratsiya: normal ~0,10, anomaliya ~0,55) + qoidaviy tuzatishlar (5× o'rtacha summa, >15 tranzaksiya 24 soat ichida, foreign+CNP, g'alati soatda katta summa).
- **Tushuntirish**: amount_zscore 0,30, velocity_24h 0,25, foreign_cnp 0,20, distinct_merchants 0,15, odd_hour 0,10

### M-J2 — Sotuvchi (merchant) firibgarlik balli
- **Algoritm**: Chargeback/velocity/tenure va MCC fraud-prior xususiyatlari ustida LightGBM (2000 namuna)
- **Kirish**: merchant_id, mcc_code, months_active, chargeback_rate_30d, refund_rate_30d, avg_ticket_size, txn_velocity_per_day, pct_cnp/foreign, prior_complaints_count
- **Chiqish**: fraud_score (0–1000), fraud_probability, risk_band (past/o'rta/yuqori/jiddiy), decision (kuzatuv/cheklov/to'xtatish), risk_factors
- **Mantiq**: GBM ehtimolligi → 0–1000 ball. Qaror: <0,50 kuzatuv, <0,75 cheklov, ≥0,75 to'xtatish. MCC priorlari qimor (0,70), raqamli tovarlar (0,60), telemarketingni (0,65) ko'taradi.
- **Tushuntirish**: LightGBM xususiyat ahamiyatlari normallashtirilgan

### M-J3 — AML shubhali namuna aniqlash
- **Algoritm**: Qoidaviy tipologiya hisoblagichi (FATF strukturalash/qatlamlash evristikasi)
- **Kirish**: customer_id, naqd depozit ko'rsatkichlari (count/amount/near-threshold), tez kirim-chiqim sikllari, distinct counterparties, cross-border + yuqori xavfli yurisdiksiya soni
- **Chiqish**: suspicion_score (0–1), typology (strukturalash/qatlamlash/integratsiya/yo'q), sar_recommended, triggered_typologies, ishonch
- **Mantiq**: Uchta mustaqil tipologiya ballari; eng ustun bo'lgani belgilangan tipologiyaga aylanadi. SAR `suspicion ≥ 0,55` bo'lsa tavsiya etiladi. Ishonch = eng yuqori ball − ikkinchisi + 0,5 (1 bilan cheklangan).
- **Tushuntirish**: structuring 0,40, layering 0,30, cross_border 0,20, high_risk_jurisdiction 0,10

### M-J4 — Sintetik shaxsni aniqlash
- **Algoritm**: Kredit-ingichkalik + shaxs-tenure xususiyatlari ustida XGBoost klassifikator (2000 namuna)
- **Kirish**: applicant_id, credit_file_age_months, credit_inquiries_last_6m, address_changes_24m, ssn_age_norm, telefon/email tenure, distinct_names_at_address, employer_verifiable
- **Chiqish**: synthetic_probability (0–1), is_synthetic, confidence_band (past/o'rta/yuqori), contributing_factors, verification_steps
- **Mantiq**: Ingichka kredit fayli + yuqori so'rov tezligi + shaxs hujjat yoshining ariza beruvchi yoshiga to'g'ri kelmasligi + manzil bo'yicha bo'lishish → sintetik. Tekshirish qadamlari diapazon bo'yicha "standart KYC" dan "shaxsiy uchrashuv"gacha eskalatsiya qilinadi.
- **Tushuntirish**: XGBoost xususiyat ahamiyatlari normallashtirilgan

### M-J5 — Ariza firibgarligini aniqlash
- **Algoritm**: Ariza-tezligi va shaxs-bo'lishuv xususiyatlari ustida GradientBoosting (2000 namuna)
- **Kirish**: application_id, applications_24h/30d, qurilma/IP shared count_30d, declared_income vs bureau_income_estimate, document_quality_score, velocity_score, geolocation_mismatch
- **Chiqish**: fraud_probability, decision (tasdiq/ko'rib chiqish/rad), fraud_indicators, income_discrepancy_pct, risk_score (0–1000)
- **Mantiq**: Qaror chegaralari: <0,30 tasdiq, <0,65 ko'rib chiqish, ≥0,65 rad. Daromad farqi = `(declared − bureau) / bureau`. Indikatorlar: tezlik portlashlari, qurilma bo'lishish, hujjat buzilishi, geo nomuvofiqlik.
- **Tushuntirish**: GBM xususiyat ahamiyatlari normallashtirilgan
