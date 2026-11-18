"""
Comprehensive Volatility Targeting Backtest & Parameter Clashing Analysis
========================================================================
Rigorous testing of target volatility overlays on the 16-Stock Screened Markov Portfolio.
- Dataset: 2018-2026 (Warmup: Nov 2018 - Nov 2019; OOS: Nov 2019 - Nov 2026, 1703 trading sessions)
- Friction: 20 bps (0.20%) on all equity turnover
- Cash yield: 6.50% p.a. (risk-free liquid rate)
- Benchmark: Nifty 50 Buy & Hold and Unhedged 100% Equity Screened Markov Strategy
"""

import csv
import math
import numpy as np

AGG_STOCKS = [
    'DIXON.NS', 'CHOLAFIN.NS', 'MANAPPURAM.NS', 'AARTIIND.NS',
    'BHARATFORG.NS', 'PERSISTENT.NS', 'INDHOTEL.NS', 'COFORGE.NS'
]

DEF_STOCKS = [
    'ABBOTINDIA.NS', 'TORNTPHARM.NS', 'IPCALAB.NS', 'MARICO.NS',
    'ALKEM.NS', 'COLPAL.NS', 'DABUR.NS', 'LUPIN.NS'
]

class WalkForwardHMM:
    def __init__(self):
        self.mu = [0.08, -0.22]
        self.sigma = [0.65, 2.05]
        self.A = [
            [0.96, 0.04],
            [0.12, 0.88]
        ]
        self.pi = [0.85, 0.15]

    def gaussian_pdf(self, x, state):
        mu = self.mu[state]
        sig = max(self.sigma[state], 1e-4)
        diff = x - mu
        exponent = - (diff * diff) / (2.0 * sig * sig)
        if exponent < -500:
            return 1e-100
        return (1.0 / (sig * math.sqrt(2.0 * math.pi))) * math.exp(exponent)

    def train_on_history(self, history, max_iter=25):
        T = len(history)
        if T < 80:
            return
        mean_all = sum(history) / T
        var_all = sum((x - mean_all)**2 for x in history) / T
        std_all = math.sqrt(max(var_all, 1e-4))

        self.mu = [mean_all + 0.04, mean_all - 0.22]
        self.sigma = [std_all * 0.70, std_all * 1.85]

        for it in range(max_iter):
            alpha = []
            c = []
            a0 = [self.pi[i] * self.gaussian_pdf(history[0], i) for i in range(2)]
            c0 = sum(a0) or 1e-12
            alpha.append([a / c0 for a in a0])
            c.append(c0)

            for t in range(1, T):
                at = []
                for j in range(2):
                    prob_prev = alpha[t-1][0] * self.A[0][j] + alpha[t-1][1] * self.A[1][j]
                    emit = self.gaussian_pdf(history[t], j)
                    at.append(prob_prev * emit)
                ct = sum(at) or 1e-12
                alpha.append([a / ct for a in at])
                c.append(ct)

            beta = [[0.0, 0.0] for _ in range(T)]
            beta[T-1] = [1.0, 1.0]
            for t in range(T-2, -1, -1):
                for i in range(2):
                    beta[t][i] = (
                        self.A[i][0] * self.gaussian_pdf(history[t+1], 0) * beta[t+1][0] +
                        self.A[i][1] * self.gaussian_pdf(history[t+1], 1) * beta[t+1][1]
                    ) / c[t+1]

            gamma = []
            for t in range(T):
                denom = alpha[t][0] * beta[t][0] + alpha[t][1] * beta[t][1] or 1e-12
                gamma.append([
                    (alpha[t][0] * beta[t][0]) / denom,
                    (alpha[t][1] * beta[t][1]) / denom
                ])

            xi_sum = [[0.0, 0.0], [0.0, 0.0]]
            for t in range(T-1):
                denom = sum(
                    alpha[t][i] * self.A[i][j] * self.gaussian_pdf(history[t+1], j) * beta[t+1][j]
                    for i in range(2) for j in range(2)
                ) or 1e-12
                for i in range(2):
                    for j in range(2):
                        val = (alpha[t][i] * self.A[i][j] * self.gaussian_pdf(history[t+1], j) * beta[t+1][j]) / denom
                        xi_sum[i][j] += val

            self.pi = [gamma[0][0], gamma[0][1]]
            for i in range(2):
                g_sum_i = sum(gamma[t][i] for t in range(T-1)) or 1e-12
                self.A[i][0] = xi_sum[i][0] / g_sum_i
                self.A[i][1] = xi_sum[i][1] / g_sum_i
                row_sum = self.A[i][0] + self.A[i][1] or 1e-12
                self.A[i][0] /= row_sum
                self.A[i][1] /= row_sum

            for i in range(2):
                g_sum = sum(gamma[t][i] for t in range(T)) or 1e-12
                self.mu[i] = sum(gamma[t][i] * history[t] for t in range(T)) / g_sum
                var_i = sum(gamma[t][i] * ((history[t] - self.mu[i]) ** 2) for t in range(T)) / g_sum
                self.sigma[i] = math.sqrt(max(var_i, 1e-6))

            if self.sigma[0] > self.sigma[1]:
                self.mu[0], self.mu[1] = self.mu[1], self.mu[0]
                self.sigma[0], self.sigma[1] = self.sigma[1], self.sigma[0]
                self.A = [
                    [self.A[1][1], self.A[1][0]],
                    [self.A[0][1], self.A[0][0]]
                ]
                self.pi = [self.pi[1], self.pi[0]]

    def compute_forward_filtered_prob(self, prev_filtered_prob, current_obs):
        p0_prior = prev_filtered_prob[0] * self.A[0][0] + prev_filtered_prob[1] * self.A[1][0]
        p1_prior = prev_filtered_prob[0] * self.A[0][1] + prev_filtered_prob[1] * self.A[1][1]
        lik0 = self.gaussian_pdf(current_obs, 0)
        lik1 = self.gaussian_pdf(current_obs, 1)
        unnorm0 = p0_prior * lik0
        unnorm1 = p1_prior * lik1
        total = unnorm0 + unnorm1 or 1e-12
        return [unnorm0 / total, unnorm1 / total]


def calc_perf_metrics(wealth, daily_rets, rf=6.5):
    years = len(daily_rets) / 252.0
    cagr = ((wealth[-1] / wealth[0]) ** (1.0 / years) - 1.0) * 100.0
    mean_r = sum(daily_rets) / len(daily_rets)
    var_r = sum((r - mean_r)**2 for r in daily_rets) / len(daily_rets)
    ann_vol = math.sqrt(var_r) * math.sqrt(252)
    sharpe = (cagr - rf) / (ann_vol or 1e-6)

    # Max Drawdown
    peak = wealth[0]
    mdd = 0.0
    for w in wealth:
        if w > peak:
            peak = w
        dd = (peak - w) / peak * 100.0
        if dd > mdd:
            mdd = dd
    calmar = cagr / (mdd or 1e-6)
    return {
        'cagr': cagr,
        'ann_vol': ann_vol,
        'sharpe': sharpe,
        'mdd': mdd,
        'calmar': calmar,
        'final_wealth': wealth[-1]
    }


def run_volatility_targeting_experiment():
    csv_file = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/screened_universe_data.csv"
    data = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            data.append(r)

    total_sessions = len(data)
    warmup_window = 250
    TURNOVER_FEE = 0.0020  # 20 bps
    RF_DAILY = ((1.0 + 0.065) ** (1.0 / 252.0) - 1.0) * 100.0  # ~0.025% daily

    # 1. Precompute walk-forward Markov regime & probabilities for all out-of-sample sessions
    hmm = WalkForwardHMM()
    warmup_obs = [float(d['nifty_ret']) for d in data[:warmup_window]]
    hmm.train_on_history(warmup_obs, max_iter=30)

    regimes = []
    p_panics = []
    curr_regime = "CALM"
    curr_prob = [0.90, 0.10]

    for t in range(warmup_window, total_sessions):
        if (t - warmup_window) % 21 == 0 and t > warmup_window:
            history_t = [float(d['nifty_ret']) for d in data[:t]]
            hmm.train_on_history(history_t, max_iter=15)

        today_obs = float(data[t]['nifty_ret'])
        curr_prob = hmm.compute_forward_filtered_prob(curr_prob, today_obs)
        p_panic = curr_prob[1]

        if curr_regime == "CALM" and p_panic > 0.65:
            curr_regime = "PANIC"
        elif curr_regime == "PANIC" and p_panic <= 0.40:
            curr_regime = "CALM"

        regimes.append(curr_regime)
        p_panics.append(p_panic)

    oos_len = total_sessions - warmup_window
    print(f"OOS Evaluation Sessions: {oos_len} (from {data[warmup_window]['date']} to {data[-1]['date']})")

    # Precalculate daily asset returns
    # Equity basket return depends on regime:
    # Calm: 80% Champions, 20% Fortresses
    # Panic: 20% Champions, 80% Fortresses
    calm_basket_rets = []
    panic_basket_rets = []
    vix_values = []
    nifty_rets = []

    for t in range(warmup_window, total_sessions):
        agg_rets = [float(data[t][f"{s}_ret"]) for s in AGG_STOCKS]
        def_rets = [float(data[t][f"{s}_ret"]) for s in DEF_STOCKS]
        mean_agg = sum(agg_rets) / len(agg_rets)
        mean_def = sum(def_rets) / len(def_rets)
        
        calm_basket_rets.append(0.80 * mean_agg + 0.20 * mean_def)
        panic_basket_rets.append(0.20 * mean_agg + 0.80 * mean_def)
        vix_values.append(float(data[t]['vix_close']))
        nifty_rets.append(float(data[t]['nifty_ret']))

    # Baseline 1: Nifty 50 Buy & Hold
    nifty_wealth = [100.0]
    for r in nifty_rets:
        nifty_wealth.append(nifty_wealth[-1] * (1.0 + r / 100.0))
    nifty_metrics = calc_perf_metrics(nifty_wealth, nifty_rets)

    # Strategy Simulation Engine
    def simulate_strategy(name, sizing_func, lookback=20):
        """
        sizing_func(t, prev_w_equity, realized_vol_ann, current_vix, regime) -> target_w_equity
        """
        wealth = [100.0]
        daily_rets = []
        turnover_paid_total = 0.0
        turnover_count = 0
        w_equity = 1.0  # start 100% equity

        # To avoid lookahead bias, realized vol at day t must be calculated strictly from t-1 backwards
        for i in range(oos_len):
            regime = regimes[i]
            prev_regime = regimes[i-1] if i > 0 else "CALM"
            current_vix = vix_values[i-1] if i > 0 else vix_values[0]

            # Calculate realized vol of the portfolio over lookback sessions
            if i >= lookback:
                # historical portfolio returns of last 'lookback' days
                past_r = daily_rets[i-lookback:i]
                m_r = sum(past_r) / len(past_r)
                var_r = sum((r - m_r)**2 for r in past_r) / len(past_r)
                realized_vol_ann = math.sqrt(var_r) * math.sqrt(252)
            else:
                realized_vol_ann = 15.0  # prior assumption

            # Determine target equity weight for session i
            target_w = sizing_func(i, w_equity, realized_vol_ann, current_vix, regime)
            target_w = max(0.0, min(1.0, target_w))  # no leverage, no shorting

            # Equity style rotation friction:
            # If regime changed from CALM to PANIC or vice-versa, 60% of equity basket is rotated
            regime_switched = (regime != prev_regime) and (i > 0)
            
            # Rebalancing turnover:
            # 1. Delta between current equity weight and target equity weight
            weight_turnover = abs(target_w - w_equity)
            # 2. If regime changed, the remaining equity portion rotates 60%
            rotation_turnover = (target_w * 0.60) if regime_switched else 0.0
            
            total_session_turnover = weight_turnover + rotation_turnover
            if total_session_turnover > 0.001:
                fee = total_session_turnover * TURNOVER_FEE * wealth[-1]
                turnover_paid_total += fee
                turnover_count += 1
                curr_w = wealth[-1] - fee
            else:
                curr_w = wealth[-1]

            w_equity = target_w
            w_cash = 1.0 - w_equity

            # Session return
            equity_ret = calm_basket_rets[i] if regime == "CALM" else panic_basket_rets[i]
            cash_ret = RF_DAILY
            session_ret = (w_equity * equity_ret) + (w_cash * cash_ret)

            curr_w *= (1.0 + session_ret / 100.0)
            wealth.append(curr_w)
            daily_rets.append(session_ret)

        metrics = calc_perf_metrics(wealth, daily_rets)
        metrics['turnover_cost'] = turnover_paid_total
        metrics['turnover_count'] = turnover_count
        return metrics

    # Define Strategies:
    strategies = {}

    # 1. Baseline: 100% Equity Markov (No Vol Target)
    def size_baseline(i, prev_w, r_vol, vix, reg):
        return 1.0
    strategies['1. Baseline 100% Equity (Markov only)'] = simulate_strategy('Baseline', size_baseline)

    # 2. Continuous Vol Target (Target Vol = 15%, No Deadband - Daily Micro-Churn)
    def size_continuous_15_no_deadband(i, prev_w, r_vol, vix, reg):
        target_vol = 15.0
        # Continuous sizing formula: target_vol / realized_vol
        return min(1.0, target_vol / max(r_vol, 5.0))
    strategies['2. Continuous Vol Target (15% Target, No Buffer - Daily Rebal)'] = simulate_strategy(
        'Continuous_NoBuffer', size_continuous_15_no_deadband
    )

    # 3. Continuous Vol Target (Target Vol = 12%, No Deadband)
    def size_continuous_12_no_deadband(i, prev_w, r_vol, vix, reg):
        target_vol = 12.0
        return min(1.0, target_vol / max(r_vol, 5.0))
    strategies['3. Continuous Vol Target (12% Target, No Buffer - Daily Rebal)'] = simulate_strategy(
        'Continuous_12_NoBuffer', size_continuous_12_no_deadband
    )

    # 4. Continuous Vol Target with 10% Deadband (Target Vol = 15%)
    def size_continuous_15_buffer10(i, prev_w, r_vol, vix, reg):
        target_vol = 15.0
        raw_w = min(1.0, target_vol / max(r_vol, 5.0))
        # Deadband rule: only change weight if drift > 10%
        if abs(raw_w - prev_w) > 0.10:
            return raw_w
        return prev_w
    strategies['4. Continuous Vol Target (15% Target, 10% Deadband Buffer)'] = simulate_strategy(
        'Continuous_15_Buffer10', size_continuous_15_buffer10
    )

    # 5. Discrete 3-Tier Vol Target (Based on Realized Volatility)
    def size_discrete_rvol(i, prev_w, r_vol, vix, reg):
        # Tiered rules:
        # Vol <= 14%: 100% Equity
        # 14% < Vol <= 18%: 80% Equity + 20% Cash
        # Vol > 18%: 60% Equity + 40% Cash
        if r_vol <= 14.0:
            desired_w = 1.0
        elif r_vol <= 18.0:
            desired_w = 0.80
        else:
            desired_w = 0.60
        # Require 3 consecutive days or buffer? Let's test standard buffer
        return desired_w
    strategies['5. Discrete 3-Tier Realized Vol (100% / 80% / 60%)'] = simulate_strategy(
        'Discrete_RVol', size_discrete_rvol
    )

    # 6. Discrete 3-Tier VIX-Based (Based on India VIX)
    def size_discrete_vix(i, prev_w, r_vol, vix, reg):
        # VIX <= 15: 100% Equity
        # 15 < VIX <= 20: 80% Equity + 20% Cash
        # VIX > 20: 60% Equity + 40% Cash
        # With hysteresis on VIX to avoid ping-pong:
        # Drop equity when VIX crosses 16, restore only when VIX drops below 14.
        if vix <= 14.0:
            return 1.0
        elif vix > 20.0:
            return 0.60
        elif vix > 16.0 and prev_w == 1.0:
            return 0.80
        elif vix <= 15.0 and prev_w == 0.80:
            return 1.0
        elif vix <= 18.0 and prev_w == 0.60:
            return 0.80
        return prev_w
    strategies['6. Discrete 3-Tier VIX with Hysteresis (100% / 80% / 60%)'] = simulate_strategy(
        'Discrete_VIX_Hysteresis', size_discrete_vix
    )

    # 7. Asymmetric Vol Target: Vol target active ONLY in Calm regime (Let Fortresses handle Panic)
    def size_asymmetric_calm_only(i, prev_w, r_vol, vix, reg):
        # In Panic regime: 100% in Defensive Fortresses (Beta is already ~0.45, cash drag hurts recovery)
        if reg == "PANIC":
            return 1.0
        # In Calm regime: if VIX > 16, hold 20% cash buffer
        if vix > 16.0:
            return 0.80
        elif vix <= 14.0:
            return 1.0
        return prev_w
    strategies['7. Asymmetric Architecture (Calm Vol Target, 100% Fortresses in Panic)'] = simulate_strategy(
        'Asymmetric', size_asymmetric_calm_only
    )

    # Print Results Table
    print("\n" + "="*115)
    print(f"{'Strategy Architecture':<55} | {'CAGR':<7} | {'Vol':<6} | {'Sharpe':<6} | {'MDD':<7} | {'Calmar':<6} | {'Turnover Churn':<14}")
    print("="*115)
    print(f"{'Nifty 50 Buy & Hold':<55} | {nifty_metrics['cagr']:>6.2f}% | {nifty_metrics['ann_vol']:>5.2f}% | {nifty_metrics['sharpe']:>6.2f} | {nifty_metrics['mdd']:>6.2f}% | {nifty_metrics['calmar']:>6.2f} | {'N/A':>14}")
    print("-"*115)

    for name, m in strategies.items():
        churn_str = f"{m['turnover_count']}x (-{m['turnover_cost']:.1f} pts)"
        print(f"{name:<55} | {m['cagr']:>6.2f}% | {m['ann_vol']:>5.2f}% | {m['sharpe']:>6.2f} | {m['mdd']:>6.2f}% | {m['calmar']:>6.2f} | {churn_str:>14}")
    print("="*115)

    # Parameter grid search for optimal parameters
    print("\n>>> Running Grid Search: Target Vol (10% - 20%) x Rebalance Buffer (0% - 15%) x Lookback (10d - 40d)...")
    grid_results = []
    for tgt in [10.0, 12.0, 14.0, 16.0, 18.0]:
        for buf in [0.0, 0.05, 0.10, 0.15]:
            for lb in [10, 20, 30]:
                def make_func(t_vol, b_band):
                    def fn(i, prev_w, r_vol, vix, reg):
                        raw_w = min(1.0, t_vol / max(r_vol, 5.0))
                        if abs(raw_w - prev_w) > b_band:
                            return raw_w
                        return prev_w
                    return fn
                res = simulate_strategy(f"Grid_{tgt}_{buf}_{lb}", make_func(tgt, buf), lookback=lb)
                grid_results.append({
                    'tgt': tgt,
                    'buf': buf,
                    'lb': lb,
                    'cagr': res['cagr'],
                    'vol': res['ann_vol'],
                    'sharpe': res['sharpe'],
                    'mdd': res['mdd'],
                    'calmar': res['calmar'],
                    'churn': res['turnover_count'],
                    'cost': res['turnover_cost']
                })

    # Sort grid by Sharpe and Calmar
    grid_by_sharpe = sorted(grid_results, key=lambda x: x['sharpe'], reverse=True)
    grid_by_calmar = sorted(grid_results, key=lambda x: x['calmar'], reverse=True)

    print("\n--- Top 5 Configurations by Sharpe Ratio ---")
    for r in grid_by_sharpe[:5]:
        print(f"Target: {r['tgt']}%, Buffer: {r['buf']*100:.0f}%, Lookback: {r['lb']}d -> CAGR: {r['cagr']:.2f}%, Vol: {r['vol']:.2f}%, Sharpe: {r['sharpe']:.2f}, MDD: {r['mdd']:.2f}%, Calmar: {r['calmar']:.2f}, Churn: {r['churn']} trades (Cost: -{r['cost']:.1f} pts)")

    print("\n--- Top 5 Configurations by Calmar Ratio (Drawdown Protection) ---")
    for r in grid_by_calmar[:5]:
        print(f"Target: {r['tgt']}%, Buffer: {r['buf']*100:.0f}%, Lookback: {r['lb']}d -> CAGR: {r['cagr']:.2f}%, Vol: {r['vol']:.2f}%, Sharpe: {r['sharpe']:.2f}, MDD: {r['mdd']:.2f}%, Calmar: {r['calmar']:.2f}, Churn: {r['churn']} trades (Cost: -{r['cost']:.1f} pts)")

    print("\n--- Zero Buffer (Naive Continuous Daily) vs 10% Buffer Comparison ---")
    for r in grid_results:
        if r['tgt'] in [14.0, 16.0] and r['lb'] == 20:
            print(f"Target: {r['tgt']}%, Buffer: {r['buf']*100:.0f}%, Lookback: 20d -> CAGR: {r['cagr']:.2f}%, Sharpe: {r['sharpe']:.2f}, MDD: {r['mdd']:.2f}%, Churn Trades: {r['churn']} (Friction Paid: -{r['cost']:.1f} pts)")

if __name__ == '__main__':
    run_volatility_targeting_experiment()
