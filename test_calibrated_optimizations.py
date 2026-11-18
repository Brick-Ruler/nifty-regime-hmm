"""
Calibrated Optimization Audit
=============================
Tests proposed refinements:
1. Vol Target = 21.0% (calibrated for Mid & Small Caps vs 18.0% Large Cap default)
2. High-Conviction Opening Gap Trigger: Gap <= -1.75% OR (Gap <= -1.25% AND VIX >= 20.0)
3. Regime-Conditional Vol Target: Vol target only derisks equity when Markov State is PANIC or Downside Vol > 20%
"""

import urllib.request, json, csv, math
from datetime import datetime

csv_path = 'C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/historical_broad_universe_48.csv'
with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

dates = [r['date'] for r in rows]
T = len(rows)
all_symbols = [col for col in reader.fieldnames if col not in ['date', 'nifty_close', 'vix_close']]

# Fetch NIFTY open prices
url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=8y&interval=1d"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
nifty_opens_dict = {}
with urllib.request.urlopen(req, timeout=5) as resp:
    d = json.loads(resp.read().decode('utf-8'))
    res = d['chart']['result'][0]
    ts = res['timestamp']
    q = res['indicators']['quote'][0]
    for t_stamp, op, cl in zip(ts, q['open'], q['close']):
        dt_s = datetime.fromtimestamp(t_stamp).strftime('%Y-%m-%d')
        if op is not None: nifty_opens_dict[dt_s] = float(op)

prices = {s: [] for s in all_symbols}
nifty_closes, vix_closes, nifty_opens = [], [], []
last_nifty, last_vix = 10000.0, 15.0
last_prices = {s: 100.0 for s in all_symbols}

for r in rows:
    dt = r['date']
    n_val = r.get('nifty_close', '')
    if n_val and n_val != 'None': last_nifty = float(n_val)
    nifty_closes.append(last_nifty)
    v_val = r.get('vix_close', '')
    if v_val and v_val != 'None': last_vix = float(v_val)
    vix_closes.append(last_vix)
    nifty_opens.append(nifty_opens_dict.get(dt, last_nifty))
    for s in all_symbols:
        val = r.get(s, '')
        if val and val != 'None': last_prices[s] = float(val)
        prices[s].append(last_prices[s])

import backtest_full_glory_production as btf

def run_calibrated(target_vol=21.0, gap_threshold=-1.75, gap_vix_thresh=20.0, condition_on_panic=False):
    lookback = 252
    rebal_freq = 126
    friction_rate = 15.0 / 10000.0
    rf_daily = (0.065 / 252.0) * 100.0

    hmm = btf.RollingHMM()
    val = 100000.0
    hist = [val]
    rets = []
    current_agg, current_def = [], []
    last_rebal = 0
    current_regime = 'CALM'
    gap_triggers = 0
    whipsaws = 0
    derisk_sessions = 0
    total_friction = 0.0

    for t in range(lookback, T):
        n_prev = nifty_closes[t-1]
        n_open = nifty_opens[t]
        n_close = nifty_closes[t]
        vix_prev = vix_closes[t-1]
        opening_gap = ((n_open - n_prev) / n_prev) * 100.0
        nifty_day_ret = ((n_close - n_prev) / n_prev) * 100.0

        # Layer 1: Sector Rotation Rebal
        if (t == lookback) or ((t - last_rebal) >= rebal_freq):
            sub_nifty = nifty_closes[t-lookback:t]
            sub_prices = {s: prices[s][t-lookback:t] for s in all_symbols}
            new_agg, new_def, _ = btf.screen_option_b_sectors(sub_prices, sub_nifty, lookback=lookback)
            if current_agg:
                dropped = set(current_agg) - set(new_agg)
                turnover = len(dropped) / len(current_agg)
                fric = val * turnover * friction_rate * 2.0
                val -= fric
                total_friction += fric
            current_agg, current_def = new_agg, new_def
            last_rebal = t

        # Layer 2: Gap Breaker
        gap_triggered = False
        if opening_gap <= gap_threshold or (opening_gap <= (gap_threshold + 0.5) and vix_prev >= gap_vix_thresh):
            gap_triggered = True
            gap_triggers += 1
            if nifty_day_ret >= opening_gap:
                whipsaws += 1
            if current_regime == 'CALM':
                current_regime = 'PANIC'
                fric = val * 0.50 * friction_rate
                val -= fric
                total_friction += fric

        # Layer 3: EOD HMM
        if (t - lookback) % 63 == 0:
            hist_n = [((nifty_closes[k] - nifty_closes[k-1]) / nifty_closes[k-1]) * 100.0 for k in range(1, t)]
            hmm.train(hist_n[-500:])

        prev_day_ret = ((nifty_closes[t-1] - nifty_closes[t-2]) / nifty_closes[t-2]) * 100.0 if t >= 2 else 0.0
        p_panic = hmm.get_online_panic_prob(prev_day_ret)

        if current_regime == 'CALM' and p_panic > 0.65:
            current_regime = 'PANIC'
            fric = val * 0.50 * friction_rate
            val -= fric
            total_friction += fric
        elif current_regime == 'PANIC' and p_panic <= 0.40 and not gap_triggered:
            current_regime = 'CALM'
            fric = val * 0.50 * friction_rate
            val -= fric
            total_friction += fric

        # Layer 4: Vol Targeting
        if len(rets) >= 20:
            roll_20 = rets[-20:]
            mean_20 = sum(roll_20) / 20.0
            std_20 = math.sqrt(sum((r - mean_20)**2 for r in roll_20) / 20.0)
            realized_vol = std_20 * math.sqrt(252)

            upper_bound = target_vol * 1.15
            lower_bound = target_vol * 0.85

            should_derisk = (realized_vol > upper_bound)
            if condition_on_panic:
                should_derisk = should_derisk and (current_regime == 'PANIC')

            if should_derisk:
                w_eq = min(1.0, target_vol / realized_vol)
                derisk_sessions += 1
            else:
                w_eq = 1.0
        else:
            w_eq = 1.0

        w_cash = 1.0 - w_eq

        # Layer 5: Daily Returns
        active = (current_agg + current_def) if current_regime == 'PANIC' else current_agg
        s_rets = [((prices[s][t] - prices[s][t-1])/prices[s][t-1])*100.0 for s in active if prices[s][t-1] > 0]
        eq_ret = sum(s_rets)/len(s_rets) if s_rets else 0.0
        day_ret = (w_eq * eq_ret) + (w_cash * rf_daily)
        rets.append(day_ret)
        val *= (1.0 + day_ret / 100.0)
        hist.append(val)

    years = (T - lookback) / 252.0
    cagr = ((val / 100000.0) ** (1.0 / years) - 1.0) * 100.0
    m = sum(rets)/len(rets)
    vol = math.sqrt(sum((r-m)**2 for r in rets)/len(rets)) * math.sqrt(252)
    sharpe = (cagr - 6.5) / max(vol, 1e-4)
    neg = [r for r in rets if r < 0]
    d_vol = math.sqrt(sum(r**2 for r in neg)/len(rets)) * math.sqrt(252)
    sortino = (cagr - 6.5) / max(d_vol, 1e-4)

    peak = hist[0]
    max_dd = 0.0
    for v in hist:
        if v > peak: peak = v
        dd = (v - peak)/peak
        if dd < max_dd: max_dd = dd

    return {
        'target_vol': target_vol,
        'gap_thresh': gap_threshold,
        'cagr': cagr,
        'vol': vol,
        'sharpe': sharpe,
        'sortino': sortino,
        'max_dd': max_dd * 100.0,
        'calmar': cagr / max(abs(max_dd*100.0), 1e-4),
        'gap_triggers': gap_triggers,
        'whipsaws': whipsaws,
        'derisk_sessions': derisk_sessions,
        'friction': total_friction
    }

print("=" * 105)
print("PARAMETER SENSITIVITY & CALIBRATION MATRIX (1,719 TRADING DAYS)")
print("=" * 105)
cfg1 = run_calibrated(target_vol=18.0, gap_threshold=-1.50, gap_vix_thresh=18.0, condition_on_panic=False)
cfg2 = run_calibrated(target_vol=21.0, gap_threshold=-1.75, gap_vix_thresh=20.0, condition_on_panic=False)
cfg3 = run_calibrated(target_vol=21.0, gap_threshold=-1.75, gap_vix_thresh=20.0, condition_on_panic=True)
cfg4 = run_calibrated(target_vol=24.0, gap_threshold=-2.00, gap_vix_thresh=22.0, condition_on_panic=True)

print(f"{'Configuration':<40} | {'CAGR (%)':<9} | {'Vol (%)':<8} | {'Sharpe':<7} | {'Sortino':<8} | {'Max DD (%)':<11} | {'Calmar':<7} | {'Whipsaws':<9}")
print("-" * 115)
configs = [
    ("Current Base (Vol 18%, Gap -1.5%)", cfg1),
    ("Calibrated A (Vol 21%, Gap -1.75%)", cfg2),
    ("Calibrated B (Vol 21% in Panic Only)", cfg3),
    ("Growth Maximum (Vol 24%, Gap -2.0%)", cfg4)
]
for name, c in configs:
    print(f"{name:<40} | {c['cagr']:>8.2f}% | {c['vol']:>7.2f}% | {c['sharpe']:>7.2f} | {c['sortino']:>8.2f} | {c['max_dd']:>10.2f}% | {c['calmar']:>7.2f} | {c['whipsaws']:>3}/{c['gap_triggers']}")
print("=" * 115)
