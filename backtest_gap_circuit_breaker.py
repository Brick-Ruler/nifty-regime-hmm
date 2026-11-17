"""
Overnight Gap Circuit Breaker Optimization Engine
=================================================
Tests whether executing an emergency derisking at Market Open (9:25 AM)
improves or harms portfolio performance during overnight market shocks.

Simulates 4 Thresholds:
- Strategy 0: Baseline (EOD 3:15 PM only, no morning gap triggers)
- Strategy 1: Sensitive Breaker (Nifty Gap <= -1.0%)
- Strategy 2: Optimal Breaker   (Nifty Gap <= -1.5%)
- Strategy 3: Extreme Breaker   (Nifty Gap <= -2.0%)

Evaluates:
- CAGR (Annualized Return)
- Maximum Drawdown (MDD)
- Sharpe Ratio
- Whipsaw Rate (Days morning panic was bought up into an intraday rally)
- Friction Cost of Panic Exits
"""

import urllib.request
import urllib.parse
import json
import csv
import math
from datetime import datetime

AGG_STOCKS = ['DIXON.NS', 'CHOLAFIN.NS', 'MANAPPURAM.NS', 'AARTIIND.NS', 'BHARATFORG.NS', 'PERSISTENT.NS', 'INDHOTEL.NS', 'COFORGE.NS']
DEF_STOCKS = ['ABBOTINDIA.NS', 'TORNTPHARM.NS', 'IPCALAB.NS', 'MARICO.NS', 'ALKEM.NS', 'COLPAL.NS', 'DABUR.NS', 'LUPIN.NS']
ALL_TICKERS = ['^NSEI', '^INDIAVIX'] + AGG_STOCKS + DEF_STOCKS

def fetch_open_close(symbol, range_str="8y"):
    encoded = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range={range_str}&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = data['chart']['result'][0]
            quotes = result['indicators']['quote'][0]
            timestamps = result['timestamp']
            
            records = {}
            for t, o, c in zip(timestamps, quotes['open'], quotes['close']):
                if o is not None and c is not None and not math.isnan(o) and not math.isnan(c):
                    d_str = datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')
                    records[d_str] = {'open': float(o), 'close': float(c)}
            return records
    except Exception as e:
        return {}

def run_gap_optimization():
    print("Fetching Open and Close prices for all 18 symbols...")
    raw = {}
    for s in ALL_TICKERS:
        raw[s] = fetch_open_close(s)

    common_dates = None
    for s in ALL_TICKERS:
        s_dates = set(raw[s].keys())
        common_dates = s_dates if common_dates is None else common_dates.intersection(s_dates)
    common_dates = sorted(list(common_dates))
    print(f"Aligned {len(common_dates)} trading days across all instruments.")

    # Calculate returns:
    # 1. Overnight gap for Nifty: (Nifty_Open_t - Nifty_Close_{t-1}) / Nifty_Close_{t-1}
    # 2. Stock returns: Close-to-Close and Open-to-Close
    sessions = []
    for i in range(1, len(common_dates)):
        prev_d, curr_d = common_dates[i-1], common_dates[i]
        n_prev_c = raw['^NSEI'][prev_d]['close']
        n_curr_o = raw['^NSEI'][curr_d]['open']
        n_curr_c = raw['^NSEI'][curr_d]['close']
        
        n_gap = ((n_curr_o - n_prev_c) / n_prev_c) * 100.0
        n_day_ret = ((n_curr_c - n_prev_c) / n_prev_c) * 100.0
        n_intraday = ((n_curr_c - n_curr_o) / n_curr_o) * 100.0

        agg_c2c = [((raw[s][curr_d]['close'] - raw[s][prev_d]['close']) / raw[s][prev_d]['close']) * 100.0 for s in AGG_STOCKS]
        def_c2c = [((raw[s][curr_d]['close'] - raw[s][prev_d]['close']) / raw[s][prev_d]['close']) * 100.0 for s in DEF_STOCKS]
        
        # Open to Close returns (for trades executed at open)
        agg_o2c = [((raw[s][curr_d]['close'] - raw[s][curr_d]['open']) / raw[s][curr_d]['open']) * 100.0 for s in AGG_STOCKS]
        def_o2c = [((raw[s][curr_d]['close'] - raw[s][curr_d]['open']) / raw[s][curr_d]['open']) * 100.0 for s in DEF_STOCKS]

        # Close to Open (Gap loss suffered overnight)
        agg_gap = [((raw[s][curr_d]['open'] - raw[s][prev_d]['close']) / raw[s][prev_d]['close']) * 100.0 for s in AGG_STOCKS]

        sessions.append({
            'date': curr_d,
            'n_gap': n_gap,
            'n_day_ret': n_day_ret,
            'n_intraday': n_intraday,
            'agg_c2c': sum(agg_c2c)/8.0,
            'def_c2c': sum(def_c2c)/8.0,
            'agg_o2c': sum(agg_o2c)/8.0,
            'def_o2c': sum(def_o2c)/8.0,
            'agg_gap': sum(agg_gap)/8.0
        })

    # Test out-of-sample window (last 1700 sessions)
    test_sessions = sessions[250:]
    thresholds = [-999.0, -1.0, -1.5, -2.0]  # -999 means baseline (never trigger gap breaker)
    names = ["Baseline (EOD 3:15 PM Only)", "Sensitive Breaker (-1.0% Gap)", "Optimal Breaker (-1.5% Gap)", "Extreme Shock Breaker (-2.0% Gap)"]

    print("\n" + "="*95)
    print("      OVERNIGHT GAP CIRCUIT BREAKER OPTIMIZATION (OUT-OF-SAMPLE: 2019 - 2026)")
    print("="*95)

    for thresh, name in zip(thresholds, names):
        wealth = 100.0
        wealth_hist = [100.0]
        ret_hist = []
        gap_triggers = 0
        whipsaw_count = 0  # Days where gap was red but market closed green

        # Simulated HMM state tracking (assuming Bull baseline, triggering defense on gap)
        for s in test_sessions:
            gap = s['n_gap']
            day_ret = 0.0

            if gap <= thresh:  # EMERGENCY GAP TRIGGER AT 9:25 AM!
                gap_triggers += 1
                # 1. Suffered overnight gap loss on Aggressive stocks
                overnight_loss = s['agg_gap']
                # 2. Rebalanced at Open into Defensive Fortresses (paying 0.20% friction)
                # 3. Earned Defensive intraday return from Open to Close
                intraday_gain = s['def_o2c']
                # Net daily return: (1 + gap_loss) * (1 + intraday_gain) - 1 - fee
                net_r = ((1.0 + overnight_loss/100.0) * (1.0 + intraday_gain/100.0) - 1.0) * 100.0 - 0.20
                day_ret = net_r

                # Check if this was a whipsaw (Nifty rallied intraday from open to close)
                if s['n_intraday'] > 0.5:
                    whipsaw_count += 1
            else:
                # Normal Day (holding the 8 Aggressive Champions close-to-close)
                day_ret = s['agg_c2c']

            wealth *= (1.0 + day_ret / 100.0)
            wealth_hist.append(wealth)
            ret_hist.append(day_ret)

        years = len(test_sessions) / 252.0
        cagr = ((wealth / 100.0) ** (1.0 / years) - 1.0) * 100.0
        mean_r = sum(ret_hist) / len(ret_hist)
        var_r = sum((x - mean_r)**2 for x in ret_hist) / len(ret_hist)
        ann_vol = math.sqrt(var_r) * math.sqrt(252)
        sharpe = (cagr - 6.5) / ann_vol if ann_vol > 0 else 0.0

        peak = wealth_hist[0]
        mdd = 0.0
        for w in wealth_hist:
            if w > peak: peak = w
            dd = (peak - w) / peak
            if dd > mdd: mdd = dd
        mdd *= 100.0

        print(f"\n-> {name.upper()}:")
        print(f"   • CAGR: {cagr:.2f}% | Volatility: {ann_vol:.2f}% | Sharpe: {sharpe:.2f} | Max Drawdown: {mdd:.2f}%")
        print(f"   • Emergency Triggers: {gap_triggers} times | Whipsaws (Rallied after Gap): {whipsaw_count} times")
        print(f"   • Total Out-of-Sample Return: +{wealth - 100.0:,.1f}%")

if __name__ == "__main__":
    run_gap_optimization()
