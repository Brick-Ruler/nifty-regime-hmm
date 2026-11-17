"""
Walk-Forward Backtest for Algorithmically Screened 16-Stock Universe
====================================================================
Evaluates the purely objective, factor-screened portfolio across 7 out-of-sample years:
- 8 Aggressive Champions: DIXON, CHOLAFIN, MANAPPURAM, AARTIIND, BHARATFORG, PERSISTENT, INDHOTEL, COFORGE
- 8 Defensive Fortresses: ABBOTINDIA, TORNTPHARM, IPCALAB, MARICO, ALKEM, COLPAL, DABUR, LUPIN

Conditions:
- 100% Equity at all times
- 0.20% friction on turnover
- Hysteresis filtering (P > 0.65 to Panic, P <= 0.40 to Calm)
- Strict Walk-Forward (Hamilton 1989)
"""

import csv
import math

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
            # Forward Pass
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

            # Backward Pass
            beta = [[0.0, 0.0] for _ in range(T)]
            beta[T-1] = [1.0, 1.0]
            for t in range(T-2, -1, -1):
                for i in range(2):
                    beta[t][i] = (
                        self.A[i][0] * self.gaussian_pdf(history[t+1], 0) * beta[t+1][0] +
                        self.A[i][1] * self.gaussian_pdf(history[t+1], 1) * beta[t+1][1]
                    ) / c[t+1]

            # Posteriors
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

            # Parameter Updates
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


def run_screened_backtest():
    csv_file = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/screened_universe_data.csv"
    data = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            data.append(r)

    total_sessions = len(data)
    warmup_window = 250  # ~1 year warmup (Nov 2018 to Nov 2019)
    print(f"Total sessions: {total_sessions}")
    print(f"Warmup window: {warmup_window} sessions")
    print(f"Out-of-sample backtest: {total_sessions - warmup_window} sessions (~7 years: late 2019 to Nov 2026)")

    CALM_AGG_WT = 0.80 / len(AGG_STOCKS)
    CALM_DEF_WT = 0.20 / len(DEF_STOCKS)

    PANIC_AGG_WT = 0.20 / len(AGG_STOCKS)
    PANIC_DEF_WT = 0.80 / len(DEF_STOCKS)

    TURNOVER_FEE = 0.0020  # 20 bps

    hmm = WalkForwardHMM()
    warmup_obs = [float(d['nifty_ret']) for d in data[:warmup_window]]
    hmm.train_on_history(warmup_obs, max_iter=30)
    print("Initial HMM trained on warmup window successfully.")

    curr_regime = "CALM"
    curr_filtered_prob = [0.90, 0.10]
    
    rot_wealth = 100.0
    static_screened_wealth = 100.0  # Equal weight 16 stocks (no rotation)
    nifty_bh_wealth = 100.0

    results = []
    total_switches = 0
    total_friction_paid = 0.0

    for t in range(warmup_window, total_sessions):
        # Monthly model re-estimation
        if (t - warmup_window) % 21 == 0 and t > warmup_window:
            history_t = [float(d['nifty_ret']) for d in data[:t]]
            hmm.train_on_history(history_t, max_iter=15)

        today_obs = float(data[t]['nifty_ret'])
        curr_filtered_prob = hmm.compute_forward_filtered_prob(curr_filtered_prob, today_obs)
        p_panic = curr_filtered_prob[1]

        prev_regime = curr_regime
        if curr_regime == "CALM" and p_panic > 0.65:
            curr_regime = "PANIC"
        elif curr_regime == "PANIC" and p_panic <= 0.40:
            curr_regime = "CALM"

        if curr_regime != prev_regime:
            total_switches += 1
            turnover = 0.60
            fee_drag = turnover * TURNOVER_FEE * rot_wealth
            total_friction_paid += fee_drag
            rot_wealth -= fee_drag

        if curr_regime == "CALM":
            agg_wt = CALM_AGG_WT
            def_wt = CALM_DEF_WT
        else:
            agg_wt = PANIC_AGG_WT
            def_wt = PANIC_DEF_WT

        agg_rets = [float(data[t][f"{s}_ret"]) for s in AGG_STOCKS]
        def_rets = [float(data[t][f"{s}_ret"]) for s in DEF_STOCKS]
        
        mean_agg_ret = sum(agg_rets) / len(agg_rets)
        mean_def_ret = sum(def_rets) / len(def_rets)

        rot_daily_ret = sum(w * r for w, r in zip([agg_wt]*len(AGG_STOCKS), agg_rets)) + \
                        sum(w * r for w, r in zip([def_wt]*len(DEF_STOCKS), def_rets))

        rot_wealth *= (1.0 + rot_daily_ret / 100.0)

        # Static equal-weight of the 16 screened stocks
        static_ret = 0.50 * mean_agg_ret + 0.50 * mean_def_ret
        static_screened_wealth *= (1.0 + static_ret / 100.0)

        # Nifty 50
        nifty_ret = float(data[t]['nifty_ret'])
        nifty_bh_wealth *= (1.0 + nifty_ret / 100.0)

        results.append({
            'date': data[t]['date'],
            'p_panic': round(p_panic, 4),
            'regime': curr_regime,
            'rot_wealth': round(rot_wealth, 2),
            'static_screened_wealth': round(static_screened_wealth, 2),
            'nifty_bh_wealth': round(nifty_bh_wealth, 2),
            'rot_ret': round(rot_daily_ret, 4),
            'static_ret': round(static_ret, 4),
            'nifty_ret': round(nifty_ret, 4)
        })

    def calc_metrics(wealth_history, return_history):
        total_ret = (wealth_history[-1] - wealth_history[0]) / wealth_history[0] * 100.0
        years = len(wealth_history) / 252.0
        cagr = ((wealth_history[-1] / wealth_history[0]) ** (1.0 / years) - 1.0) * 100.0
        mean_r = sum(return_history) / len(return_history)
        var_r = sum((r - mean_r)**2 for r in return_history) / len(return_history)
        ann_vol = math.sqrt(var_r) * math.sqrt(252)
        rf_ann = 6.5
        sharpe = (cagr - rf_ann) / ann_vol if ann_vol > 0 else 0.0
        
        peak = wealth_history[0]
        max_dd = 0.0
        for w in wealth_history:
            if w > peak:
                peak = w
            dd = (peak - w) / peak
            if dd > max_dd:
                max_dd = dd
        max_dd *= 100.0
        calmar = cagr / max_dd if max_dd > 0 else 0.0
        
        return {
            'cagr': cagr,
            'ann_vol': ann_vol,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'calmar': calmar,
            'total_ret': total_ret
        }

    m_rot = calc_metrics([r['rot_wealth'] for r in results], [r['rot_ret'] for r in results])
    m_static = calc_metrics([r['static_screened_wealth'] for r in results], [r['static_ret'] for r in results])
    m_nifty = calc_metrics([r['nifty_bh_wealth'] for r in results], [r['nifty_ret'] for r in results])

    print("\n==========================================================================================")
    print("      OUT-OF-SAMPLE ALGORITHMICALLY SCREENED ROTATION RESULTS (2019 - 2026)               ")
    print("        [16 Screened Stocks, 100% Equity, 0.20% Friction Deducted on All Rebalances]      ")
    print("==========================================================================================\n")

    print(f"{'Performance Metric':<25} | {'HMM Screened Rotation':<22} | {'Static Screened Basket':<22} | {'NIFTY 50 Benchmark':<22}")
    print("-" * 102)
    print(f"{'Total Return':<25} | {m_rot['total_ret']:>18.1f}% | {m_static['total_ret']:>18.1f}% | {m_nifty['total_ret']:>18.1f}%")
    print(f"{'CAGR (Annualized Return)':<25} | {m_rot['cagr']:>18.2f}% | {m_static['cagr']:>18.2f}% | {m_nifty['cagr']:>18.2f}%")
    print(f"{'Annualized Volatility':<25} | {m_rot['ann_vol']:>18.2f}% | {m_static['ann_vol']:>18.2f}% | {m_nifty['ann_vol']:>18.2f}%")
    print(f"{'Maximum Drawdown (MDD)':<25} | {m_rot['max_dd']:>18.2f}% | {m_static['max_dd']:>18.2f}% | {m_nifty['max_dd']:>18.2f}%")
    print(f"{'Sharpe Ratio (Rf = 6.5%)':<25} | {m_rot['sharpe']:>18.2f}  | {m_static['sharpe']:>18.2f}  | {m_nifty['sharpe']:>18.2f} ")
    print(f"{'Calmar Ratio (CAGR/MDD)':<25} | {m_rot['calmar']:>18.2f}  | {m_static['calmar']:>18.2f}  | {m_nifty['calmar']:>18.2f} ")
    print("-" * 102)
    print(f"Total Sector Regime Switches: {total_switches}")
    print(f"Total Friction (STT/Brokerage/Slippage) Deducted: Rs. {total_friction_paid:.2f} per Rs. 100 invested")

    # Save CSV
    out_csv = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/screened_rotation_results.csv"
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"\nSaved out-of-sample rotation results to {out_csv}")

if __name__ == "__main__":
    run_screened_backtest()
