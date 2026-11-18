"""
The Full-Glory Production Backtest & Vulnerability Audit
========================================================
Integrates all 5 quantitative pillars simultaneously:
1. Macro Regime Filter (Hamilton 2-State Markov HMM with Hysteresis)
2. Overnight Circuit Breaker (09:25 AM NIFTY Opening Gap Check)
3. Semi-Annual Sector Rotation (Option B: Top-5 Leading Macro Sectors)
4. Dynamic Asymmetric 8-to-16 Stock Expansion (Halving Variance in Panic)
5. Volatility Targeting Overlay (18.0% Annualized Target with 15% Deadband & Liquid Cash 6.5% Yield)
6. Realistic Execution: 15 bps (0.15%) Friction on all portfolio turnover

Evaluates out-of-sample data (2019-2026, 1719 trading days) to identify pitfalls, whipsaw rates,
cash drag, and required optimizations.
"""

import urllib.request
import urllib.parse
import json
import csv
import math
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. CANDIDATE SECTOR TAXONOMY (48 Stocks across 10 Macro Sectors)
# -----------------------------------------------------------------------------
SECTOR_MAP = {
    'CUMMINSIND.NS': 'Capital Goods', 'VOLTAS.NS': 'Capital Goods', 'THERMAX.NS': 'Capital Goods', 'POLYCAB.NS': 'Capital Goods',
    'ASTRAL.NS': 'Building Materials', 'KAJARIACER.NS': 'Building Materials',
    'AIAENG.NS': 'Heavy Industrials', 'BHARATFORG.NS': 'Heavy Industrials',
    'BALKRISIND.NS': 'Auto Ancillary', 'APOLLOTYRE.NS': 'Auto Ancillary', 'TIINDIA.NS': 'Auto Ancillary',
    'DEEPAKNTR.NS': 'Specialty Chemicals', 'AARTIIND.NS': 'Specialty Chemicals', 'TATACHEM.NS': 'Specialty Chemicals',
    'PIIND.NS': 'Agri Nutrients', 'COROMANDEL.NS': 'Agri Nutrients',
    'TRENT.NS': 'Retail & Fashion', 'BATAINDIA.NS': 'Retail & Fashion',
    'INDHOTEL.NS': 'Hospitality', 'CROMPTON.NS': 'Consumer Electricals',
    'PERSISTENT.NS': 'Digital IT', 'COFORGE.NS': 'Digital IT', 'LTTS.NS': 'Digital IT', 'MPHASIS.NS': 'Digital IT', 'KPITTECH.NS': 'Digital IT',
    'CHOLAFIN.NS': 'Financials/NBFC', 'FEDERALBNK.NS': 'Financials/NBFC', 'MUTHOOTFIN.NS': 'Financials/NBFC', 'MANAPPURAM.NS': 'Financials/NBFC', 'AUBANK.NS': 'Financials/NBFC',
    'DIXON.NS': 'EMS/Electronics', 'AMBER.NS': 'EMS/Electronics',
    'TORNTPHARM.NS': 'Pharma Healthcare', 'ALKEM.NS': 'Pharma Healthcare', 'IPCALAB.NS': 'Pharma Healthcare', 'LUPIN.NS': 'Pharma Healthcare', 'GLENMARK.NS': 'Pharma Healthcare', 'GLAXO.NS': 'Pharma Healthcare',
    'MARICO.NS': 'Consumer Staples', 'COLPAL.NS': 'Consumer Staples', 'DABUR.NS': 'Consumer Staples', 'EMAMILTD.NS': 'Consumer Staples', 'RADICO.NS': 'Consumer Staples', 'GODREJCP.NS': 'Consumer Staples',
    'IGL.NS': 'Gas & Utilities', 'MGL.NS': 'Gas & Utilities', 'PETRONET.NS': 'Gas & Utilities', 'KANSAINER.NS': 'MNC Coatings'
}

# -----------------------------------------------------------------------------
# 2. HAMILTON MARKOV REGIME ENGINE (Expanding Window, Zero Lookahead)
# -----------------------------------------------------------------------------
class RollingHMM:
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
        for _ in range(12):
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

    def get_online_panic_prob(self, ret):
        p0 = self.pi[0] * self.pdf(ret, 0)
        p1 = self.pi[1] * self.pdf(ret, 1)
        tot = p0 + p1 or 1e-12
        return p1 / tot


# -----------------------------------------------------------------------------
# 3. POINT-IN-TIME OPTION B SECTOR ROTATION & SELECTION
# -----------------------------------------------------------------------------
def screen_option_b_sectors(sub_prices, sub_nifty, lookback=252):
    """
    Ranks sectors by 6M momentum (trailing 126 days).
    Selects top 5 leading sectors:
    - Top 3 sectors: 2 stocks each (6 stocks)
    - Next 2 sectors: 1 stock each (2 stocks)
    Total = Exactly 8 Aggressive Champions
    Also selects 8 Defensive Fortresses from non-cyclical sectors.
    """
    all_syms = list(sub_prices.keys())

    # Sector 6M momentum
    sector_returns = {}
    for s in all_syms:
        sec = SECTOR_MAP.get(s, 'Other')
        p_old = sub_prices[s][-126] if len(sub_prices[s]) >= 126 else sub_prices[s][0]
        p_new = sub_prices[s][-1]
        ret = ((p_new - p_old) / p_old) * 100.0 if p_old > 0 else 0.0
        if sec not in sector_returns:
            sector_returns[sec] = []
        sector_returns[sec].append(ret)

    sec_mean_mom = {sec: sum(rets)/len(rets) for sec, rets in sector_returns.items()}
    sorted_sectors = sorted(sec_mean_mom.keys(), key=lambda sec: sec_mean_mom[sec], reverse=True)
    top5_sectors = sorted_sectors[:5]

    # Individual stock factor scores
    nifty_rets = [((sub_nifty[k] - sub_nifty[k-1])/sub_nifty[k-1])*100.0 for k in range(1, len(sub_nifty))]
    n_mean = sum(nifty_rets)/len(nifty_rets)
    n_var = sum((r - n_mean)**2 for r in nifty_rets)/len(nifty_rets)

    stock_scores = {}
    for s in all_syms:
        p = sub_prices[s]
        s_rets = [((p[k] - p[k-1])/p[k-1])*100.0 for k in range(1, len(p))]
        m = sum(s_rets)/len(s_rets)
        var = sum((r - m)**2 for r in s_rets)/len(s_rets)
        sd = math.sqrt(max(var, 1e-4))
        cov = sum((s_rets[k]-m)*(nifty_rets[k]-n_mean) for k in range(len(s_rets)))/len(s_rets)
        beta = cov / max(n_var, 1e-4)

        # Risk-adjusted momentum
        ram = m / max(sd, 1e-4)

        # Drawdown
        peak = p[0]
        max_dd = 0.0
        for px in p:
            if px > peak: peak = px
            dd = (px - peak)/peak
            if dd < max_dd: max_dd = dd

        stock_scores[s] = {
            'ram': ram,
            'beta': beta,
            'max_dd': max_dd,
            'sector': SECTOR_MAP.get(s, 'Other')
        }

    # Select 8 Aggressives from Top 5 Sectors
    selected_agg = []
    for rank, sec in enumerate(top5_sectors, 1):
        target_count = 2 if rank <= 3 else 1
        sec_cands = [s for s, sc in stock_scores.items() if sc['sector'] == sec]
        sec_cands.sort(key=lambda s: stock_scores[s]['ram'], reverse=True)
        selected_agg.extend(sec_cands[:target_count])

    # Select 8 Defensive Fortresses from non-cyclical sectors
    def_sectors = ['Pharma Healthcare', 'Consumer Staples', 'Gas & Utilities', 'MNC Coatings', 'Building Materials', 'Specialty Chemicals']
    def_cands = [s for s, sc in stock_scores.items() if sc['sector'] in def_sectors and s not in selected_agg]
    # Rank defensives by lowest beta + mildest drawdown
    def_cands.sort(key=lambda s: (stock_scores[s]['beta'] * 0.6) + (abs(stock_scores[s]['max_dd']) * 0.4))

    selected_def = []
    used_def_sec = set()
    for s in def_cands:
        sec = stock_scores[s]['sector']
        if sec not in used_def_sec:
            selected_def.append(s)
            used_def_sec.add(sec)
        if len(selected_def) == 8:
            break
    if len(selected_def) < 8:
        for s in def_cands:
            if s not in selected_def:
                selected_def.append(s)
                if len(selected_def) == 8: break

    return selected_agg, selected_def, top5_sectors


# -----------------------------------------------------------------------------
# 4. FULL GLORY SIMULATION ENGINE
# -----------------------------------------------------------------------------
def run_full_glory_simulation():
    csv_path = 'C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/historical_broad_universe_48.csv'
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    dates = [r['date'] for r in rows]
    T = len(rows)
    all_symbols = [col for col in reader.fieldnames if col not in ['date', 'nifty_close', 'vix_close']]

    # Fetch NIFTY open prices for exact opening gap simulation
    print("Fetching historical NIFTY Open/Close data for 09:25 AM Circuit Breaker...")
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
            if op is not None:
                nifty_opens_dict[dt_s] = float(op)

    # Parse prices with forward fill
    prices = {s: [] for s in all_symbols}
    nifty_closes = []
    vix_closes = []
    nifty_opens = []

    last_nifty = 10000.0
    last_vix = 15.0
    last_prices = {s: 100.0 for s in all_symbols}

    for r in rows:
        dt = r['date']
        n_val = r.get('nifty_close', '')
        if n_val and n_val != 'None': last_nifty = float(n_val)
        nifty_closes.append(last_nifty)

        v_val = r.get('vix_close', '')
        if v_val and v_val != 'None': last_vix = float(v_val)
        vix_closes.append(last_vix)

        op_val = nifty_opens_dict.get(dt, last_nifty)
        nifty_opens.append(op_val)

        for s in all_symbols:
            val = r.get(s, '')
            if val and val != 'None': last_prices[s] = float(val)
            prices[s].append(last_prices[s])

    lookback = 252 # 1 year burn-in
    rebal_freq = 126 # Semi-annual (6 months)
    friction_rate = 15.0 / 10000.0 # 15 bps
    rf_daily = (0.065 / 252.0) * 100.0 # 6.5% p.a. Liquid Cash yield

    hmm = RollingHMM()

    # Model Portfolios:
    # 1. Full Glory (Option B + 8-to-16 + 09:25 AM Breaker + 03:15 PM HMM + Vol Target 18% + Frictions)
    val_full = 100000.0
    hist_full = [val_full]
    rets_full = []

    # 2. Strategy Without Morning Circuit Breaker (EOD Switch only)
    val_no_cb = 100000.0
    hist_no_cb = [val_no_cb]
    rets_no_cb = []

    # 3. Strategy Without Volatility Targeting (Always 100% Equity)
    val_no_vt = 100000.0
    hist_no_vt = [val_no_vt]
    rets_no_vt = []

    # 4. Pure Unhedged Momentum (8 Aggressives only, no defensives, no vol target)
    val_pure_mom = 100000.0
    hist_pure_mom = [val_pure_mom]
    rets_pure_mom = []

    # 5. Benchmark: NIFTY 50
    val_nifty = 100000.0
    hist_nifty = [val_nifty]
    rets_nifty = []

    current_agg = []
    current_def = []
    last_rebal = 0

    # Operational statistics & pitfall counters
    gap_breaker_triggers = 0
    whipsaw_gap_count = 0 # Breaker triggered, but NIFTY closed positive
    effective_gap_count = 0 # Breaker triggered, and saved losses as NIFTY closed deeper in red
    hmm_panic_switches = 0
    total_panic_days = 0
    vol_target_cuts_count = 0
    friction_paid_full = 0.0

    current_regime_full = 'CALM'
    current_regime_no_cb = 'CALM'

    print("=" * 95)
    print("RUNNING FULL-GLORY PRODUCTION BACKTEST (2019 - 2026: 1,719 TRADING DAYS)")
    print("=" * 95)

    for t in range(lookback, T):
        dt = dates[t]
        n_prev = nifty_closes[t-1]
        n_open = nifty_opens[t]
        n_close = nifty_closes[t]
        vix_prev = vix_closes[t-1]

        nifty_day_ret = ((n_close - n_prev) / n_prev) * 100.0
        rets_nifty.append(nifty_day_ret)
        val_nifty *= (1.0 + nifty_day_ret / 100.0)
        hist_nifty.append(val_nifty)

        # ---------------------------------------------------------------------
        # LAYER 1: SEMI-ANNUAL OPTION B SECTOR ROTATION RECONSTITUTION
        # ---------------------------------------------------------------------
        if (t == lookback) or ((t - last_rebal) >= rebal_freq):
            sub_nifty = nifty_closes[t-lookback:t]
            sub_prices = {s: prices[s][t-lookback:t] for s in all_symbols}

            new_agg, new_def, top5 = screen_option_b_sectors(sub_prices, sub_nifty, lookback=lookback)

            if current_agg:
                dropped = set(current_agg) - set(new_agg)
                turnover = len(dropped) / len(current_agg)
                fric = val_full * turnover * friction_rate * 2.0
                val_full -= fric
                friction_paid_full += fric

            current_agg = new_agg
            current_def = new_def
            last_rebal = t

        # ---------------------------------------------------------------------
        # LAYER 2: 09:25 AM OVERNIGHT OPENING GAP EMERGENCY CIRCUIT BREAKER
        # ---------------------------------------------------------------------
        opening_gap = ((n_open - n_prev) / n_prev) * 100.0
        gap_triggered = False

        # Threshold: Gap <= -1.50% OR (Gap <= -1.0% AND VIX >= 18)
        if opening_gap <= -1.50 or (opening_gap <= -1.0 and vix_prev >= 18.0):
            gap_triggered = True
            gap_breaker_triggers += 1
            if nifty_day_ret < opening_gap:
                effective_gap_count += 1 # Market fell further intraday -> Breaker was a lifesaver!
            else:
                whipsaw_gap_count += 1 # Market rebounded intraday

            if current_regime_full == 'CALM':
                current_regime_full = 'PANIC'
                # 50% portfolio turnover to expand into 8 defensives
                fric = val_full * 0.50 * friction_rate
                val_full -= fric
                friction_paid_full += fric

        # ---------------------------------------------------------------------
        # LAYER 3: 03:15 PM EOD HAMILTON MARKOV HMM REGIME SCAN
        # ---------------------------------------------------------------------
        if (t - lookback) % 63 == 0:
            hist_n = [((nifty_closes[k] - nifty_closes[k-1]) / nifty_closes[k-1]) * 100.0 for k in range(1, t)]
            hmm.train(hist_n[-500:])

        prev_day_ret = ((nifty_closes[t-1] - nifty_closes[t-2]) / nifty_closes[t-2]) * 100.0 if t >= 2 else 0.0
        p_panic = hmm.get_online_panic_prob(prev_day_ret)

        # Full Glory Regime State Update
        if current_regime_full == 'CALM' and p_panic > 0.65:
            current_regime_full = 'PANIC'
            hmm_panic_switches += 1
            fric = val_full * 0.50 * friction_rate
            val_full -= fric
            friction_paid_full += fric
        elif current_regime_full == 'PANIC' and p_panic <= 0.40 and not gap_triggered:
            current_regime_full = 'CALM'
            hmm_panic_switches += 1
            fric = val_full * 0.50 * friction_rate
            val_full -= fric
            friction_paid_full += fric

        if current_regime_full == 'PANIC':
            total_panic_days += 1

        # No-CB (EOD-only) regime update
        if current_regime_no_cb == 'CALM' and p_panic > 0.65:
            current_regime_no_cb = 'PANIC'
            val_no_cb -= val_no_cb * 0.50 * friction_rate
        elif current_regime_no_cb == 'PANIC' and p_panic <= 0.40:
            current_regime_no_cb = 'CALM'
            val_no_cb -= val_no_cb * 0.50 * friction_rate

        # ---------------------------------------------------------------------
        # LAYER 4: 20-DAY ROLLING VOLATILITY TARGETING (Target 18.0% Ann Vol)
        # ---------------------------------------------------------------------
        if len(rets_full) >= 20:
            roll_20 = rets_full[-20:]
            mean_20 = sum(roll_20) / 20.0
            std_20 = math.sqrt(sum((r - mean_20)**2 for r in roll_20) / 20.0)
            realized_vol = std_20 * math.sqrt(252)

            # Deadband buffer: [15.3%, 20.7%]
            if realized_vol > 20.7:
                w_eq = min(1.0, 18.0 / realized_vol)
                vol_target_cuts_count += 1
            elif realized_vol < 15.3:
                w_eq = 1.0
            else:
                w_eq = 1.0 # Within normal deadband
        else:
            w_eq = 1.0

        w_cash = 1.0 - w_eq

        # ---------------------------------------------------------------------
        # LAYER 5: DAILY ASSET RETURNS COMPUTATION
        # ---------------------------------------------------------------------
        # 1. Full Glory Return
        active_syms_full = (current_agg + current_def) if current_regime_full == 'PANIC' else current_agg
        agg_rets_today = []
        for s in active_syms_full:
            p0 = prices[s][t-1]
            p1 = prices[s][t]
            agg_rets_today.append(((p1 - p0) / p0) * 100.0 if p0 > 0 else 0.0)
        eq_ret_full = sum(agg_rets_today) / len(agg_rets_today) if agg_rets_today else 0.0
        day_ret_full = (w_eq * eq_ret_full) + (w_cash * rf_daily)
        rets_full.append(day_ret_full)
        val_full *= (1.0 + day_ret_full / 100.0)
        hist_full.append(val_full)

        # 2. No-CB Return (EOD only)
        active_syms_no_cb = (current_agg + current_def) if current_regime_no_cb == 'PANIC' else current_agg
        rets_no_cb_stocks = [((prices[s][t] - prices[s][t-1])/prices[s][t-1])*100.0 for s in active_syms_no_cb if prices[s][t-1] > 0]
        eq_ret_no_cb = sum(rets_no_cb_stocks)/len(rets_no_cb_stocks) if rets_no_cb_stocks else 0.0
        day_ret_no_cb = (w_eq * eq_ret_no_cb) + (w_cash * rf_daily)
        rets_no_cb.append(day_ret_no_cb)
        val_no_cb *= (1.0 + day_ret_no_cb / 100.0)
        hist_no_cb.append(val_no_cb)

        # 3. No-VT Return (100% Equity always, regime switch active)
        active_syms_no_vt = (current_agg + current_def) if current_regime_full == 'PANIC' else current_agg
        rets_no_vt_stocks = [((prices[s][t] - prices[s][t-1])/prices[s][t-1])*100.0 for s in active_syms_no_vt if prices[s][t-1] > 0]
        day_ret_no_vt = sum(rets_no_vt_stocks)/len(rets_no_vt_stocks) if rets_no_vt_stocks else 0.0
        rets_no_vt.append(day_ret_no_vt)
        val_no_vt *= (1.0 + day_ret_no_vt / 100.0)
        hist_no_vt.append(val_no_vt)

        # 4. Pure Momentum Return (8 Aggressives only, 100% equity always)
        pure_mom_stocks = [((prices[s][t] - prices[s][t-1])/prices[s][t-1])*100.0 for s in current_agg if prices[s][t-1] > 0]
        day_ret_pm = sum(pure_mom_stocks)/len(pure_mom_stocks) if pure_mom_stocks else 0.0
        rets_pure_mom.append(day_ret_pm)
        val_pure_mom *= (1.0 + day_ret_pm / 100.0)
        hist_pure_mom.append(val_pure_mom)

    # -------------------------------------------------------------------------
    # 5. METRICS AUDIT (CFA / FRM Rigor)
    # -------------------------------------------------------------------------
    years = (T - lookback) / 252.0

    def calc_m(vals, rets, name):
        cagr = ((vals[-1] / vals[0]) ** (1.0 / years) - 1.0) * 100.0
        m = sum(rets) / len(rets)
        vol = math.sqrt(sum((r - m)**2 for r in rets) / len(rets)) * math.sqrt(252)
        sharpe = (cagr - 6.5) / max(vol, 1e-4)
        neg_rets = [r for r in rets if r < 0]
        d_vol = math.sqrt(sum(r**2 for r in neg_rets) / len(rets)) * math.sqrt(252)
        sortino = (cagr - 6.5) / max(d_vol, 1e-4)

        peak = vals[0]
        max_dd = 0.0
        for v in vals:
            if v > peak: peak = v
            dd = (v - peak) / peak
            if dd < max_dd: max_dd = dd

        calmar = cagr / max(abs(max_dd * 100.0), 1e-4)
        return {
            'Name': name,
            'Ending Value': vals[-1],
            'CAGR': cagr,
            'Vol': vol,
            'Sharpe': sharpe,
            'Sortino': sortino,
            'MaxDD': max_dd * 100.0,
            'Calmar': calmar
        }

    m_full = calc_m(hist_full, rets_full, "Full Glory System (All 5 Pillars Active)")
    m_no_cb = calc_m(hist_no_cb, rets_no_cb, "Without 09:25 AM Circuit Breaker (EOD Only)")
    m_no_vt = calc_m(hist_no_vt, rets_no_vt, "Without Volatility Targeting (100% Equity)")
    m_pure_mom = calc_m(hist_pure_mom, rets_pure_mom, "Pure Momentum (Option B Only, No Armor)")
    m_nifty = calc_m(hist_nifty, rets_nifty, "NIFTY 50 Index (Passive Benchmark)")

    print("\n" + "=" * 100)
    print("FULL-GLORY PRODUCTION AUDIT SCORECARD (AFTER 15 BPS FRICTIONS)")
    print("=" * 100)
    print(f"{'Strategy Architecture':<45} | {'CAGR (%)':<9} | {'Vol (%)':<8} | {'Sharpe':<7} | {'Sortino':<8} | {'Max DD (%)':<11} | {'Calmar':<7}")
    print("-" * 100)
    for m in [m_full, m_no_cb, m_no_vt, m_pure_mom, m_nifty]:
        print(f"{m['Name']:<45} | {m['CAGR']:>8.2f}% | {m['Vol']:>7.2f}% | {m['Sharpe']:>7.2f} | {m['Sortino']:>8.2f} | {m['MaxDD']:>10.2f}% | {m['Calmar']:>7.2f}")
    print("=" * 100)

    print("\nOPERATIONAL METRICS & PITFALL DIAGNOSTICS:")
    print("-" * 65)
    print(f"Total Out-of-Sample Sessions:      {T - lookback} days (6.82 years)")
    print(f"Opening Gap Breaker Triggers:      {gap_breaker_triggers} days")
    print(f"  • Effective Crash Reductions:     {effective_gap_count} days (Market cratered further intraday)")
    print(f"  • Whipsaw Intraday Reversals:     {whipsaw_gap_count} days (Market rebounded intraday)")
    print(f"  • Breaker Accuracy Rate:          {(effective_gap_count / max(gap_breaker_triggers, 1)) * 100:.1f}%")
    print(f"Markov Regime Panic Sessions:      {total_panic_days} / {T - lookback} ({total_panic_days / (T - lookback) * 100:.1f}%)")
    print(f"Volatility Targeting Derisk Events: {vol_target_cuts_count} sessions with equity exposure < 100%")
    print(f"Total Turnover Friction Paid:      Rs. {friction_paid_full:,.2f} on Rs. 1 Lakh initial capital")

    return {
        'metrics': [m_full, m_no_cb, m_no_vt, m_pure_mom, m_nifty],
        'diagnostics': {
            'gap_triggers': gap_breaker_triggers,
            'effective_gaps': effective_gap_count,
            'whipsaw_gaps': whipsaw_gap_count,
            'panic_days': total_panic_days,
            'friction_paid': friction_paid_full
        }
    }

if __name__ == '__main__':
    run_full_glory_simulation()
