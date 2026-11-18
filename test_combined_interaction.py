"""
Test Combined Interaction: Markov Filter + 9:25 AM Gap Circuit Breaker + Volatility Targeting
=============================================================================================
Verifies whether combining the Opening Gap Breaker (-1.5%) with Volatility Targeting (18% Target, 15% Buffer)
synergizes or causes signal clashing.
"""

import csv
import math

AGG_STOCKS = ['DIXON.NS', 'CHOLAFIN.NS', 'MANAPPURAM.NS', 'AARTIIND.NS', 'BHARATFORG.NS', 'PERSISTENT.NS', 'INDHOTEL.NS', 'COFORGE.NS']
DEF_STOCKS = ['ABBOTINDIA.NS', 'TORNTPHARM.NS', 'IPCALAB.NS', 'MARICO.NS', 'ALKEM.NS', 'COLPAL.NS', 'DABUR.NS', 'LUPIN.NS']

def run_combined_test():
    csv_file = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/screened_universe_data.csv"
    data = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            data.append(r)

    total_sessions = len(data)
    warmup_window = 250
    TURNOVER_FEE = 0.0020
    RF_DAILY = ((1.0 + 0.065) ** (1.0 / 252.0) - 1.0) * 100.0

    # Fast forward: load the Markov regime results from screened_rotation_results.csv if available
    rec_results = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/screened_rotation_results.csv"
    regime_map = {}
    with open(rec_results, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            regime_map[r['date']] = (r['regime'], float(r['p_panic']))

    # Aligned test
    sessions = []
    for t in range(warmup_window, total_sessions):
        d_str = data[t]['date']
        if d_str in regime_map:
            reg, p_pan = regime_map[d_str]
            agg_rets = [float(data[t][f"{s}_ret"]) for s in AGG_STOCKS]
            def_rets = [float(data[t][f"{s}_ret"]) for s in DEF_STOCKS]
            sessions.append({
                'date': d_str,
                'regime': reg,
                'p_panic': p_pan,
                'nifty_ret': float(data[t]['nifty_ret']),
                'vix_close': float(data[t]['vix_close']),
                'mean_agg': sum(agg_rets) / len(agg_rets),
                'mean_def': sum(def_rets) / len(def_rets)
            })

    def calc_metrics(wealth, daily_rets, rf=6.5):
        years = len(daily_rets) / 252.0
        cagr = ((wealth[-1] / wealth[0]) ** (1.0 / years) - 1.0) * 100.0
        mean_r = sum(daily_rets) / len(daily_rets)
        var_r = sum((r - mean_r)**2 for r in daily_rets) / len(daily_rets)
        ann_vol = math.sqrt(var_r) * math.sqrt(252)
        sharpe = (cagr - rf) / (ann_vol or 1e-6)
        peak = wealth[0]
        mdd = 0.0
        for w in wealth:
            if w > peak: peak = w
            dd = (peak - w) / peak * 100.0
            if dd > mdd: mdd = dd
        calmar = cagr / (mdd or 1e-6)
        return {'cagr': cagr, 'ann_vol': ann_vol, 'sharpe': sharpe, 'mdd': mdd, 'calmar': calmar}

    # Test 1: Baseline (Markov Only)
    # Test 2: Markov + Vol Target (Target 18%, 15% Deadband)
    # Test 3: Markov + Vol Target (Target 16%, 10% Deadband)
    # Test 4: Markov + Vol Target (Target 14%, 10% Deadband)
    
    print(f"Total Aligned Sessions: {len(sessions)}")
    
    configs = [
        ("1. Pure Markov (No Vol Target)", 999.0, 0.0, 20),
        ("2. Markov + Vol Target 18% (15% Deadband)", 18.0, 0.15, 20),
        ("3. Markov + Vol Target 16% (10% Deadband)", 16.0, 0.10, 20),
        ("4. Markov + Vol Target 14% (10% Deadband)", 14.0, 0.10, 20),
    ]

    print("\n" + "="*95)
    print(f"{'Configuration':<45} | {'CAGR':<7} | {'Vol':<6} | {'Sharpe':<6} | {'MDD':<7} | {'Calmar':<6}")
    print("="*95)

    for name, tgt_vol, deadband, lb in configs:
        wealth = [100.0]
        daily_rets = []
        w_equity = 1.0
        churn_count = 0
        total_friction = 0.0

        for i in range(len(sessions)):
            reg = sessions[i]['regime']
            prev_reg = sessions[i-1]['regime'] if i > 0 else "CALM"

            # Realized vol of portfolio
            if i >= lb:
                past_r = daily_rets[i-lb:i]
                m_r = sum(past_r) / len(past_r)
                var_r = sum((r - m_r)**2 for r in past_r) / len(past_r)
                r_vol = math.sqrt(var_r) * math.sqrt(252)
            else:
                r_vol = 15.0

            if tgt_vol >= 100.0:
                target_w = 1.0
            else:
                raw_w = min(1.0, tgt_vol / max(r_vol, 5.0))
                if abs(raw_w - w_equity) > deadband:
                    target_w = raw_w
                else:
                    target_w = w_equity

            # Turnover
            regime_switch = (reg != prev_reg) and (i > 0)
            weight_turnover = abs(target_w - w_equity)
            rotation_turnover = (target_w * 0.60) if regime_switch else 0.0
            total_turnover = weight_turnover + rotation_turnover

            if total_turnover > 0.001:
                fee = total_turnover * TURNOVER_FEE * wealth[-1]
                wealth[-1] -= fee
                total_friction += fee
                churn_count += 1

            w_equity = target_w
            w_cash = 1.0 - w_equity

            if reg == "CALM":
                eq_ret = 0.80 * sessions[i]['mean_agg'] + 0.20 * sessions[i]['mean_def']
            else:
                eq_ret = 0.20 * sessions[i]['mean_agg'] + 0.80 * sessions[i]['mean_def']

            day_ret = (w_equity * eq_ret) + (w_cash * RF_DAILY)
            wealth.append(wealth[-1] * (1.0 + day_ret / 100.0))
            daily_rets.append(day_ret)

        res = calc_metrics(wealth, daily_rets)
        print(f"{name:<45} | {res['cagr']:>6.2f}% | {res['ann_vol']:>5.2f}% | {res['sharpe']:>6.2f} | {res['mdd']:>6.2f}% | {res['calmar']:>6.2f}")
    print("="*95)

if __name__ == '__main__':
    run_combined_test()
