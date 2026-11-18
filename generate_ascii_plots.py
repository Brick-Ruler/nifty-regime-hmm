"""
Generate Visual Plots and Terminal Charts for Randomly Sampled Periods
======================================================================
"""

import csv
import math

def generate_plots():
    csv_file = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/screened_universe_data.csv"
    data = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            data.append(r)

    warmup = 250
    total = len(data)
    FEE = 0.0020
    RF_DAILY = ((1.0 + 0.065) ** (1.0 / 252.0) - 1.0) * 100.0

    rec_results = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/screened_rotation_results.csv"
    regime_map = {}
    with open(rec_results, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            regime_map[r['date']] = (r['regime'], float(r['p_panic']))

    AGG_STOCKS = ['DIXON.NS', 'CHOLAFIN.NS', 'MANAPPURAM.NS', 'AARTIIND.NS', 'BHARATFORG.NS', 'PERSISTENT.NS', 'INDHOTEL.NS', 'COFORGE.NS']
    DEF_STOCKS = ['ABBOTINDIA.NS', 'TORNTPHARM.NS', 'IPCALAB.NS', 'MARICO.NS', 'ALKEM.NS', 'COLPAL.NS', 'DABUR.NS', 'LUPIN.NS']

    dates = []
    strat_daily_rets = []
    nifty_daily_rets = []
    current_w = 1.0

    for t in range(warmup, total):
        d_str = data[t]['date']
        if d_str not in regime_map:
            continue
        reg, p_pan = regime_map[d_str]

        if len(strat_daily_rets) >= 20:
            past_r = strat_daily_rets[-20:]
            m_r = sum(past_r) / len(past_r)
            var_r = sum((r - m_r)**2 for r in past_r) / len(past_r)
            r_vol = math.sqrt(var_r) * math.sqrt(252)
        else:
            r_vol = 15.0

        raw_w = min(1.0, 18.0 / max(r_vol, 5.0))
        if abs(raw_w - current_w) > 0.15:
            current_w = raw_w

        agg_rets = [float(data[t][f"{s}_ret"]) for s in AGG_STOCKS]
        def_rets = [float(data[t][f"{s}_ret"]) for s in DEF_STOCKS]
        if reg == "CALM":
            eq_ret = 0.80 * (sum(agg_rets)/8.0) + 0.20 * (sum(def_rets)/8.0)
        else:
            eq_ret = 0.20 * (sum(agg_rets)/8.0) + 0.80 * (sum(def_rets)/8.0)

        strat_ret = (current_w * eq_ret) + ((1.0 - current_w) * RF_DAILY)
        nifty_ret = float(data[t]['nifty_ret'])

        dates.append(d_str)
        strat_daily_rets.append(strat_ret)
        nifty_daily_rets.append(nifty_ret)

    # Let's define 4 contrasting market regimes to plot visually:
    # 1. COVID Crash & Recovery (2020-01 to 2022-01) - High Volatility & Rebound
    # 2. Russia-Ukraine & Rate Hike Bear Market (2021-11 to 2023-11) - Tough Sideways/Correction
    # 3. Post-Rate Hike Midcap Expansion (2022-06 to 2024-06) - Strong Steady Bull Market
    # 4. Recent Election Cycle & Consolidation (2023-06 to 2025-06) - Latest Modern Era

    eras = [
        ("Era 1: COVID Crash & Recovery (2020-2022)", "2020-01-01", "2022-01-01"),
        ("Era 2: Rate-Hike Bear & Adani Shock (2021-2023)", "2021-11-01", "2023-11-01"),
        ("Era 3: Post-Rate Hike Structural Expansion (2022-2024)", "2022-06-01", "2024-06-01"),
        ("Era 4: Election Cycle & Consolidation (2023-2025)", "2023-06-01", "2025-06-01")
    ]

    def render_sparkline(wealth_series, width=32):
        min_v = min(wealth_series)
        max_v = max(wealth_series)
        rng = max(max_v - min_v, 1e-6)
        chars = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█']
        
        # Downsample to width
        step = len(wealth_series) / width
        sampled = [wealth_series[int(i * step)] for i in range(width)]
        out = ""
        for v in sampled:
            idx = int((v - min_v) / rng * (len(chars) - 1))
            out += chars[min(len(chars)-1, max(0, idx))]
        return out

    print("\n" + "="*85)
    print("VISUAL PERFORMANCE COMPARISON ACROSS 4 DISTINCT MACRO ERAS")
    print("="*85)

    for name, s_d, e_d in eras:
        # Find indices
        s_idx = next(i for i, d in enumerate(dates) if d >= s_d)
        e_idx = next(i for i, d in enumerate(dates) if d >= e_d)
        
        s_sub = strat_daily_rets[s_idx:e_idx]
        n_sub = nifty_daily_rets[s_idx:e_idx]

        w_s, w_n = 100.0, 100.0
        ws_hist, wn_hist = [100.0], [100.0]
        for r_s, r_n in zip(s_sub, n_sub):
            w_s *= (1.0 + r_s/100.0)
            w_n *= (1.0 + r_n/100.0)
            ws_hist.append(w_s)
            wn_hist.append(w_n)

        cagr_s = ((w_s / 100.0) ** (1.0 / 2.0) - 1.0) * 100.0
        cagr_n = ((w_n / 100.0) ** (1.0 / 2.0) - 1.0) * 100.0
        alpha = cagr_s - cagr_n

        spark_s = render_sparkline(ws_hist)
        spark_n = render_sparkline(wn_hist)

        print(f"\n>>> {name} ({dates[s_idx]} -> {dates[e_idx]})")
        print(f"    Strategy (18% Vol Target): CAGR {cagr_s:>+6.2f}% | Final: ₹{w_s:,.1f} | Trend: [{spark_s}]")
        print(f"    Nifty 50 Benchmark:       CAGR {cagr_n:>+6.2f}% | Final: ₹{w_n:,.1f} | Trend: [{spark_n}]")
        print(f"    Net Alpha Delivered:       {alpha:>+6.2f}% p.a. Outperformance vs Nifty")

if __name__ == '__main__':
    generate_plots()
