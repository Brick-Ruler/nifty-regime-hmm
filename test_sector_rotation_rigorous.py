"""
Quantitative Audit: Does Sector Rotation Add Value in a Concentrated Mid/Small Cap Strategy?
=============================================================================================
Evaluating:
1. Baseline: Fixed Cross-Sector Neutrality (8 Distinct Sectors, 12.5% each)
2. Model A: Dynamic Sector Tilt (Overweight Top Momentum Sectors, Underweight Laggards)
3. Model B: Top-5 Sector Concentration (Eliminating bottom lagging sectors entirely)
"""

import sys, csv, math
sys.path.append('C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm')
import backtest_unbiased_dynamic_selection as bt

csv_file = 'C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/historical_broad_universe_48.csv'
with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

dates = [r['date'] for r in rows]
T = len(rows)
all_symbols = [col for col in reader.fieldnames if col not in ['date', 'nifty_close', 'vix_close']]

# Parse prices
prices = {s: [] for s in all_symbols}
nifty_prices = []
last_nifty = 10000.0
last_prices = {s: 100.0 for s in all_symbols}

for r in rows:
    n_val = r.get('nifty_close', '')
    if n_val and n_val != 'None': last_nifty = float(n_val)
    nifty_prices.append(last_nifty)
    for s in all_symbols:
        val = r.get(s, '')
        if val and val != 'None': last_prices[s] = float(val)
        prices[s].append(last_prices[s])

lookback = 252
rebalance_freq = 126 # Semi-annual
friction_rate = 15 / 10000.0 # 15 bps

# Sectors
SECTOR_MAP = bt.SECTOR_MAP

def run_simulation(mode='BASELINE'):
    port_val = 100000.0
    history = [port_val]
    daily_rets = []
    current_stocks = []
    current_weights = {}
    last_rebal = 0
    total_friction = 0.0

    hmm = bt.RollingHMM()
    current_regime = 'CALM'

    for t in range(lookback, T):
        # 1. Rebalance check
        if (t == lookback) or ((t - last_rebal) >= rebalance_freq):
            sub_nifty = nifty_prices[t-lookback:t]
            sub_prices = {s: prices[s][t-lookback:t] for s in all_symbols}

            # Calculate sector 6M momentum (trailing 126 days within lookback)
            sector_returns = {}
            for s in all_symbols:
                sec = SECTOR_MAP.get(s, 'Other')
                p_old = sub_prices[s][-126]
                p_new = sub_prices[s][-1]
                ret = ((p_new - p_old) / p_old) * 100.0 if p_old > 0 else 0.0
                if sec not in sector_returns:
                    sector_returns[sec] = []
                sector_returns[sec].append(ret)

            sec_mean_mom = {sec: sum(rets)/len(rets) for sec, rets in sector_returns.items()}
            sorted_sectors = sorted(sec_mean_mom.keys(), key=lambda sec: sec_mean_mom[sec], reverse=True)

            # Screen individual stocks using point-in-time factors
            new_agg, new_def = bt.screen_point_in_time(sub_prices, sub_nifty, lookback_window=lookback)

            if mode == 'BASELINE':
                # 8 distinct sectors, exactly 12.5% each
                current_stocks = new_agg
                current_weights = {s: 1.0 / len(new_agg) for s in new_agg}

            elif mode == 'SECTOR_TILT':
                # Rank the 8 selected stocks by their sector's 6M momentum
                # Top 2 sectors: 17.5% each (35% total)
                # Next 4 sectors: 12.5% each (50% total)
                # Bottom 2 sectors: 7.5% each (15% total)
                sorted_by_sec = sorted(new_agg, key=lambda s: sec_mean_mom.get(SECTOR_MAP.get(s, ''), 0.0), reverse=True)
                current_stocks = sorted_by_sec
                weights = [0.175, 0.175, 0.125, 0.125, 0.125, 0.125, 0.075, 0.075]
                current_weights = {s: w for s, w in zip(sorted_by_sec, weights)}

            elif mode == 'SECTOR_CONCENTRATED':
                # Pick ONLY from top 5 sectors, completely banning lagging sectors
                # Allow up to 2 stocks per top sector
                top_5_sectors = set(sorted_sectors[:5])
                # Filter candidates in top 5 sectors
                cands_in_top = []
                for s in all_symbols:
                    if SECTOR_MAP.get(s, '') in top_5_sectors:
                        # compute simple risk-adj mom
                        p = sub_prices[s]
                        rets = [((p[k] - p[k-1])/p[k-1])*100 for k in range(1, len(p))]
                        m = sum(rets)/len(rets)
                        sd = math.sqrt(sum((r-m)**2 for r in rets)/len(rets))
                        cands_in_top.append((s, m/max(sd, 1e-4), SECTOR_MAP.get(s, '')))
                cands_in_top.sort(key=lambda x: x[1], reverse=True)
                selected = []
                sec_counts = {}
                for s, sc, sec in cands_in_top:
                    if sec_counts.get(sec, 0) < 2:
                        selected.append(s)
                        sec_counts[sec] = sec_counts.get(sec, 0) + 1
                    if len(selected) == 8: break
                current_stocks = selected
                current_weights = {s: 1.0 / len(selected) for s in selected}

            last_rebal = t
            # Turnover friction
            port_val -= port_val * 0.30 * friction_rate
            total_friction += port_val * 0.30 * friction_rate

        # 2. Daily Markov check
        prev_ret = ((nifty_prices[t-1] - nifty_prices[t-2]) / nifty_prices[t-2]) * 100.0 if t >= 2 else 0.0
        p_panic = hmm.get_online_panic_prob(prev_ret)
        if current_regime == 'CALM' and p_panic > 0.65:
            current_regime = 'PANIC'
        elif current_regime == 'PANIC' and p_panic <= 0.40:
            current_regime = 'CALM'

        # 3. Vol targeting
        if len(daily_rets) >= 20:
            rolling_20 = daily_rets[-20:]
            std_20 = math.sqrt(sum((r - (sum(rolling_20)/20))**2 for r in rolling_20) / 20)
            real_vol = std_20 * math.sqrt(252)
            w_eq = min(1.0, 18.0 / real_vol) if real_vol > 18.0 else 1.0
        else:
            w_eq = 1.0

        # Day return
        day_rets = []
        for s in current_stocks:
            p0 = prices[s][t-1]
            p1 = prices[s][t]
            r = ((p1 - p0) / p0) * 100.0 if p0 > 0 else 0.0
            w = current_weights.get(s, 1.0/len(current_stocks))
            day_rets.append(r * w)
        
        equity_day_ret = sum(day_rets)
        total_day_ret = (w_eq * equity_day_ret) + ((1.0 - w_eq) * (0.065 / 252.0) * 100.0)
        daily_rets.append(total_day_ret)
        port_val *= (1.0 + total_day_ret / 100.0)
        history.append(port_val)

    # Metrics
    years = (T - lookback) / 252.0
    cagr = ((port_val / 100000.0) ** (1.0 / years) - 1.0) * 100.0
    m = sum(daily_rets)/len(daily_rets)
    vol = math.sqrt(sum((r-m)**2 for r in daily_rets)/len(daily_rets)) * math.sqrt(252)
    sharpe = (cagr - 6.5) / max(vol, 1e-4)

    neg_rets = [r for r in daily_rets if r < 0]
    down_vol = math.sqrt(sum(r**2 for r in neg_rets)/len(daily_rets)) * math.sqrt(252)
    sortino = (cagr - 6.5) / max(down_vol, 1e-4)

    peak = history[0]
    max_dd = 0.0
    for v in history:
        if v > peak: peak = v
        dd = (v - peak) / peak
        if dd < max_dd: max_dd = dd

    calmar = cagr / max(abs(max_dd * 100.0), 1e-4)
    return {
        'mode': mode,
        'ending_val': port_val,
        'cagr': cagr,
        'vol': vol,
        'sharpe': sharpe,
        'sortino': sortino,
        'max_dd': max_dd * 100.0,
        'calmar': calmar,
        'friction': total_friction
    }

print("=" * 80)
print("SECTOR ROTATION AUDIT: RIGOROUS QUANTITATIVE COMPARISON (1,719 TRADING DAYS)")
print("=" * 80)
m_base = run_simulation('BASELINE')
m_tilt = run_simulation('SECTOR_TILT')
m_conc = run_simulation('SECTOR_CONCENTRATED')

print(f"{'Strategy Model':<35} | {'CAGR (%)':<9} | {'Vol (%)':<8} | {'Sharpe':<7} | {'Sortino':<8} | {'Max DD (%)':<11} | {'Calmar':<7}")
print("-" * 90)
for res in [m_base, m_tilt, m_conc]:
    print(f"{res['mode']:<35} | {res['cagr']:>8.2f}% | {res['vol']:>7.2f}% | {res['sharpe']:>7.2f} | {res['sortino']:>8.2f} | {res['max_dd']:>10.2f}% | {res['calmar']:>7.2f}")
print("=" * 90)
