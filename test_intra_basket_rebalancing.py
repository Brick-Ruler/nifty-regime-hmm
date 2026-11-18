"""
Empirical Test: Daily vs Weekly vs Monthly vs Drift-Band Intra-Basket Rebalancing
=================================================================================
Tests whether rebalancing individual stock weights within the 8-stock basket 
adds alpha (rebalancing premium) or destroys return via friction and momentum truncation.
"""

import csv
import math

AGG_STOCKS = ['DIXON.NS', 'CHOLAFIN.NS', 'MANAPPURAM.NS', 'AARTIIND.NS', 'BHARATFORG.NS', 'PERSISTENT.NS', 'INDHOTEL.NS', 'COFORGE.NS']
DEF_STOCKS = ['ABBOTINDIA.NS', 'TORNTPHARM.NS', 'IPCALAB.NS', 'MARICO.NS', 'ALKEM.NS', 'COLPAL.NS', 'DABUR.NS', 'LUPIN.NS']

def test_intra_basket_rebalancing():
    csv_file = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/screened_universe_data.csv"
    data = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            data.append(r)

    warmup = 250
    total = len(data)
    FEE = 0.0020  # 20 bps

    # Load regime
    rec_results = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/screened_rotation_results.csv"
    regime_map = {}
    with open(rec_results, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            regime_map[r['date']] = r['regime']

    sessions = []
    for t in range(warmup, total):
        d = data[t]['date']
        if d in regime_map:
            sessions.append({
                'date': d,
                'regime': regime_map[d],
                'agg_rets': [float(data[t][f"{s}_ret"]) for s in AGG_STOCKS],
                'def_rets': [float(data[t][f"{s}_ret"]) for s in DEF_STOCKS]
            })

    def run_rebalance_strategy(rebal_mode):
        """
        rebal_mode:
        - 'NONE': Float weights, rebalance only on regime flip
        - 'DAILY': Reset to equal weight every single morning
        - 'WEEKLY': Reset to equal weight every 5 trading days
        - 'MONTHLY': Reset to equal weight every 21 trading days
        - 'BAND_3PCT': Rebalance only if any stock weight drifts beyond 12.5% +/- 3%
        """
        wealth = 100.0
        # Initialize weights: 8 agg stocks at 10% each (if 80/20) or 12.5% each
        agg_w = [0.10] * 8
        def_w = [0.025] * 8
        total_friction = 0.0
        trade_count = 0
        history = [100.0]
        daily_rets = []

        for i, sess in enumerate(sessions):
            reg = sess['regime']
            prev_reg = sessions[i-1]['regime'] if i > 0 else reg
            reg_flipped = (reg != prev_reg) and (i > 0)

            # Target weights for today
            target_agg_unit = 0.10 if reg == "CALM" else 0.025
            target_def_unit = 0.025 if reg == "CALM" else 0.10

            # Determine if we rebalance today
            do_rebalance = False
            if reg_flipped:
                do_rebalance = True
            elif rebal_mode == 'DAILY':
                do_rebalance = True
            elif rebal_mode == 'WEEKLY' and (i % 5 == 0):
                do_rebalance = True
            elif rebal_mode == 'MONTHLY' and (i % 21 == 0):
                do_rebalance = True
            elif rebal_mode == 'BAND_3PCT':
                # Check if any active stock drifted by > 3% from target
                if reg == "CALM":
                    if any(abs(w - target_agg_unit) > 0.03 for w in agg_w):
                        do_rebalance = True
                else:
                    if any(abs(w - target_def_unit) > 0.03 for w in def_w):
                        do_rebalance = True

            if do_rebalance:
                # Compute turnover
                turnover = sum(abs(w - target_agg_unit) for w in agg_w) + sum(abs(w - target_def_unit) for w in def_w)
                turnover /= 2.0  # one-way turnover
                fee = turnover * FEE * wealth
                wealth -= fee
                total_friction += fee
                trade_count += 1
                agg_w = [target_agg_unit] * 8
                def_w = [target_def_unit] * 8

            # EOD return of stocks
            day_ret = sum(w * (r / 100.0) for w, r in zip(agg_w, sess['agg_rets'])) + \
                      sum(w * (r / 100.0) for w, r in zip(def_w, sess['def_rets']))

            # Update weights based on price returns (drift)
            new_agg_vals = [w * (1.0 + r / 100.0) for w, r in zip(agg_w, sess['agg_rets'])]
            new_def_vals = [w * (1.0 + r / 100.0) for w, r in zip(def_w, sess['def_rets'])]
            total_end_val = sum(new_agg_vals) + sum(new_def_vals)

            agg_w = [v / total_end_val for v in new_agg_vals]
            def_w = [v / total_end_val for v in new_def_vals]

            wealth *= (1.0 + day_ret)
            history.append(wealth)
            daily_rets.append(day_ret * 100.0)

        years = len(sessions) / 252.0
        cagr = ((wealth / 100.0) ** (1.0 / years) - 1.0) * 100.0
        m_r = sum(daily_rets) / len(daily_rets)
        var_r = sum((r - m_r)**2 for r in daily_rets) / len(daily_rets)
        ann_vol = math.sqrt(var_r) * math.sqrt(252)
        sharpe = (cagr - 6.5) / (ann_vol or 1e-6)

        peak = history[0]
        mdd = 0.0
        for w in history:
            if w > peak: peak = w
            dd = (peak - w) / peak * 100.0
            if dd > mdd: mdd = dd

        return {
            'cagr': cagr,
            'vol': ann_vol,
            'sharpe': sharpe,
            'mdd': mdd,
            'turnover_trades': trade_count,
            'friction_paid': total_friction
        }

    print("\n" + "="*100)
    print(f"{'Intra-Basket Rebalancing Strategy':<45} | {'CAGR':<7} | {'Vol':<6} | {'Sharpe':<6} | {'MDD':<7} | {'Trades':<8} | {'Friction Cost'}")
    print("="*100)

    strategies = [
        ("1. Floating Weights (Rebalance Only on Regime Flip)", 'NONE'),
        ("2. Daily Rebalancing (Reset 12.5% Every Morning)", 'DAILY'),
        ("3. Weekly Rebalancing (Every Friday)", 'WEEKLY'),
        ("4. Monthly Rebalancing (Every 21 Trading Days)", 'MONTHLY'),
        ("5. Tolerance Band (+/- 3% Drift Threshold)", 'BAND_3PCT')
    ]

    for name, mode in strategies:
        res = run_rebalance_strategy(mode)
        print(f"{name:<45} | {res['cagr']:>6.2f}% | {res['vol']:>5.2f}% | {res['sharpe']:>6.2f} | {res['mdd']:>6.2f}% | {res['turnover_trades']:>6}x  | -{res['friction_paid']:>5.1f} pts")
    print("="*100)

if __name__ == '__main__':
    test_intra_basket_rebalancing()
