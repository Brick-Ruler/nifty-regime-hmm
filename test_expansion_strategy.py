import csv
import math

csv_file = 'C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/mid_small_universe.csv'
with open(csv_file, 'r', encoding='utf-8') as f:
    data = list(csv.DictReader(f))

warmup = 250
T = len(data)

agg_syms = ['VOLTAS.NS', 'BHARATFORG.NS', 'CUMMINSIND.NS', 'ASTRAL.NS', 'DIXON.NS', 'INDHOTEL.NS', 'CHOLAFIN.NS', 'FEDERALBNK.NS']
def_syms = ['TORNTPHARM.NS', 'ALKEM.NS', 'IPCALAB.NS', 'COROMANDEL.NS', 'MARICO.NS', 'EMAMILTD.NS', 'IGL.NS', 'MGL.NS']

class HMM:
    def __init__(self):
        self.mu = [0.08, -0.22]
        self.sigma = [0.65, 2.05]
        self.A = [[0.96, 0.04], [0.12, 0.88]]
        self.pi = [0.85, 0.15]
    def pdf(self, x, s):
        m, sig = self.mu[s], max(self.sigma[s], 1e-4)
        diff = x - m
        exp_val = - (diff * diff) / (2.0 * sig * sig)
        if exp_val < -500: return 1e-100
        return (1.0 / (sig * math.sqrt(2.0 * math.pi))) * math.exp(exp_val)
    def train(self, history):
        N = len(history)
        if N < 80: return
        m = sum(history) / N
        v = sum((x - m)**2 for x in history) / N
        s = math.sqrt(max(v, 1e-4))
        self.mu = [m + 0.04, m - 0.22]
        self.sigma = [s * 0.70, s * 1.85]
        for it in range(15):
            alpha, c = [], []
            a0 = [self.pi[i] * self.pdf(history[0], i) for i in range(2)]
            c0 = sum(a0) or 1e-12
            alpha.append([a / c0 for a in a0])
            c.append(c0)
            for t in range(1, N):
                at = []
                for j in range(2):
                    p_prev = alpha[t-1][0] * self.A[0][j] + alpha[t-1][1] * self.A[1][j]
                    at.append(p_prev * self.pdf(history[t], j))
                ct = sum(at) or 1e-12
                alpha.append([a / ct for a in at])
                c.append(ct)
            beta = [[0.0, 0.0] for _ in range(N)]
            beta[N-1] = [1.0, 1.0]
            for t in range(N-2, -1, -1):
                for i in range(2):
                    beta[t][i] = (self.A[i][0] * self.pdf(history[t+1], 0) * beta[t+1][0] + self.A[i][1] * self.pdf(history[t+1], 1) * beta[t+1][1]) / c[t+1]
            gamma = [[(alpha[t][i] * beta[t][i]) / (sum(alpha[t][k] * beta[t][k] for k in range(2)) or 1e-12) for i in range(2)] for t in range(N)]
            xi_sum = [[0.0, 0.0], [0.0, 0.0]]
            for t in range(N-1):
                d = sum(alpha[t][i] * self.A[i][j] * self.pdf(history[t+1], j) * beta[t+1][j] for i in range(2) for j in range(2)) or 1e-12
                for i in range(2):
                    for j in range(2):
                        xi_sum[i][j] += (alpha[t][i] * self.A[i][j] * self.pdf(history[t+1], j) * beta[t+1][j]) / d
            self.pi = [gamma[0][0], gamma[0][1]]
            for i in range(2):
                g_sum_i = sum(gamma[t][i] for t in range(N-1)) or 1e-12
                self.A[i][0] = xi_sum[i][0] / g_sum_i
                self.A[i][1] = xi_sum[i][1] / g_sum_i
                r_sum = self.A[i][0] + self.A[i][1] or 1e-12
                self.A[i][0] /= r_sum
                self.A[i][1] /= r_sum
            for i in range(2):
                g_sum = sum(gamma[t][i] for t in range(N)) or 1e-12
                self.mu[i] = sum(gamma[t][i] * history[t] for t in range(N)) / g_sum
                var_i = sum(gamma[t][i] * ((history[t] - self.mu[i]) ** 2) for t in range(N)) / g_sum
                self.sigma[i] = math.sqrt(max(var_i, 1e-6))
            if self.sigma[0] > self.sigma[1]:
                self.mu[0], self.mu[1] = self.mu[1], self.mu[0]
                self.sigma[0], self.sigma[1] = self.sigma[1], self.sigma[0]
                self.A = [[self.A[1][1], self.A[1][0]], [self.A[0][0], self.A[0][1]]]
                self.pi = [self.pi[1], self.pi[0]]

    def fwd(self, prev_p, obs):
        p0 = prev_p[0] * self.A[0][0] + prev_p[1] * self.A[1][0]
        p1 = prev_p[0] * self.A[0][1] + prev_p[1] * self.A[1][1]
        u0, u1 = p0 * self.pdf(obs, 0), p1 * self.pdf(obs, 1)
        tot = u0 + u1 or 1e-12
        return [u0 / tot, u1 / tot]

def run_simulation(mode='expansion_16'):
    hmm = HMM()
    init_hist = [float(d['nifty_ret']) for d in data[:warmup]]
    hmm.train(init_hist)
    prob = [0.90, 0.10]
    regime = 'CALM'
    w_equity = 1.0
    wealth = [100.0]
    daily_rets = []
    total_fee = 0.0
    switches = 0
    TARGET_VOL = 18.0
    DEADBAND = 0.15
    FEE = 0.0020
    RF = ((1.0 + 0.065)**(1/252) - 1.0) * 100

    for t in range(warmup, T):
        if (t - warmup) % 21 == 0 and t > warmup:
            hmm.train([float(d['nifty_ret']) for d in data[:t]])
        n_ret = float(data[t]['nifty_ret'])
        prob = hmm.fwd(prob, n_ret)
        p_panic = prob[1]
        prev_r = regime
        if regime == 'CALM' and p_panic > 0.65:
            regime = 'PANIC'
        elif regime == 'PANIC' and p_panic <= 0.40:
            regime = 'CALM'

        # Vol target
        if len(daily_rets) >= 20:
            past = daily_rets[-20:]
            m = sum(past) / len(past)
            v = sum((r - m)**2 for r in past) / len(past)
            r_vol = math.sqrt(v) * math.sqrt(252)
        else:
            r_vol = 16.0

        raw_w = min(1.0, TARGET_VOL / max(r_vol, 5.0))
        target_w = raw_w if abs(raw_w - w_equity) > DEADBAND else w_equity

        reg_switched = (regime != prev_r)
        if reg_switched: switches += 1

        if mode == 'expansion_16':
            # Calm: 100% Aggressive (8 stocks)
            # Panic: 50% Aggressive + 50% Defensive (16 stocks total)
            # Switch turnover is only 50% of portfolio reallocated!
            turnover_regime = 0.50 * target_w if reg_switched else 0.0
        else:
            # Full 80/20 rotation: 60% turnover
            turnover_regime = 0.60 * target_w if reg_switched else 0.0

        turnover = abs(target_w - w_equity) + turnover_regime
        if turnover > 0.001:
            fee = turnover * FEE * wealth[-1]
            wealth[-1] -= fee
            total_fee += fee

        w_equity = target_w
        w_cash = 1.0 - w_equity

        agg_r = sum(float(data[t][f'{s}_ret']) for s in agg_syms) / len(agg_syms)
        def_r = sum(float(data[t][f'{s}_ret']) for s in def_syms) / len(def_syms)

        if mode == 'expansion_16':
            if regime == 'CALM':
                eq_ret = agg_r  # 8 aggressive picks (100% of equity)
            else:
                eq_ret = 0.50 * agg_r + 0.50 * def_r  # 8 aggressive + 8 defensive = 16 picks!
        else:
            if regime == 'CALM':
                eq_ret = 0.80 * agg_r + 0.20 * def_r
            else:
                eq_ret = 0.20 * agg_r + 0.80 * def_r

        day_ret = (w_equity * eq_ret) + (w_cash * RF)
        wealth.append(wealth[-1] * (1.0 + day_ret / 100.0))
        daily_rets.append(day_ret)

    yrs = len(daily_rets) / 252.0
    cagr = ((wealth[-1] / wealth[0]) ** (1.0 / yrs) - 1.0) * 100.0
    m_r = sum(daily_rets) / len(daily_rets)
    vol = math.sqrt(sum((r - m_r)**2 for r in daily_rets) / len(daily_rets)) * math.sqrt(252)
    sharpe = (cagr - 6.5) / (vol or 1e-6)
    peak = wealth[0]
    mdd = 0.0
    for w in wealth:
        if w > peak: peak = w
        dd = (peak - w) / peak * 100.0
        if dd > mdd: mdd = dd

    return {
        'mode': mode,
        'cagr': cagr,
        'vol': vol,
        'sharpe': sharpe,
        'mdd': mdd,
        'calmar': cagr / mdd,
        'switches': switches,
        'total_fee': total_fee,
        'final_wealth': wealth[-1]
    }

m1 = run_simulation('expansion_16')
m2 = run_simulation('rotation_80_20')

print("="*80)
print(f"{'Strategy Architecture':<42} | {'CAGR':<7} | {'Vol':<6} | {'Sharpe':<6} | {'MDD':<7} | {'Friction'}")
print("-"*80)
print(f"{'User: 8 Agg (Bull) -> 16 Agg+Def (Panic)':<42} | {m1['cagr']:>6.2f}% | {m1['vol']:>5.2f}% | {m1['sharpe']:>6.2f} | {m1['mdd']:>6.2f}% | Rs. {m1['total_fee']:>5.2f}")
print(f"{'Prior: 80/20 Agg <-> 20/80 Def Rotation':<42} | {m2['cagr']:>6.2f}% | {m2['vol']:>5.2f}% | {m2['sharpe']:>6.2f} | {m2['mdd']:>6.2f}% | Rs. {m2['total_fee']:>5.2f}")
print("="*80)
