"""
Algorithmic Factor Screener for Mid & Small Caps (NSE)
======================================================
Eliminates human selection bias and cherry-picking.

Methodology:
1. Candidate Pool: ~45 prominent, liquid Mid & Small Cap stocks across 10 sectors on NSE.
2. Benchmark: NIFTY 50 (^NSEI)
3. Factor Calculations:
   - Beta (β) = Cov(Stock, Market) / Var(Market)
   - Upside Capture Ratio = Mean(Stock Ret | Market > 0) / Mean(Market Ret | Market > 0)
   - Downside Capture Ratio = Mean(Stock Ret | Market < 0) / Mean(Market Ret | Market < 0)
   - Annualized Volatility (σ) = Std(Stock Ret) * sqrt(252)
4. Ranking:
   - Aggressive Rank: Highest Beta + Highest Upside Capture
   - Defensive Rank: Lowest Beta + Lowest Downside Capture + Lowest Volatility
5. Optimal Selection: Top 8 Aggressive Champions & Top 8 Defensive Fortresses
"""

import urllib.request
import urllib.parse
import json
import csv
import math
from datetime import datetime

CANDIDATE_POOL = [
    # Industrials & Capital Goods
    'CUMMINSIND.NS', 'VOLTAS.NS', 'BHARATFORG.NS', 'ASTRAL.NS', 'KEI.NS', 'THERMAX.NS',
    # Auto Ancillary
    'BALKRISIND.NS', 'APOLLOTYRE.NS', 'TIINDIA.NS',
    # Chemicals & Agri
    'DEEPAKNTR.NS', 'TATACHEM.NS', 'PIIND.NS', 'COROMANDEL.NS', 'AARTIIND.NS',
    # Consumer Discretionary & EMS
    'DIXON.NS', 'INDHOTEL.NS', 'KAJARIACER.NS', 'BATAINDIA.NS', 'CROMPTON.NS',
    # Midcap IT & Tech
    'PERSISTENT.NS', 'COFORGE.NS', 'LTTS.NS', 'MPHASIS.NS',
    # Midcap Financials & NBFCs
    'CHOLAFIN.NS', 'FEDERALBNK.NS', 'MUTHOOTFIN.NS', 'MANAPPURAM.NS', 'AUBANK.NS',
    # Pharma & Healthcare (Defensive candidates)
    'TORNTPHARM.NS', 'ALKEM.NS', 'IPCALAB.NS', 'LUPIN.NS', 'GLENMARK.NS', 'JBCHEPHARM.NS', 'ABBOTINDIA.NS',
    # FMCG & Consumer Staples (Defensive candidates)
    'MARICO.NS', 'EMAMILTD.NS', 'DABUR.NS', 'COLPAL.NS', 'RADICO.NS', 'JYOTHYLAB.NS', 'GODREJCP.NS',
    # City Gas & Utilities (Defensive candidates)
    'IGL.NS', 'MGL.NS', 'CESC.NS'
]

def fetch_ticker_closes(symbol, range_str="5y"):
    encoded = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range={range_str}&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            quotes = result['indicators']['quote'][0]
            
            records = {}
            for t, c in zip(timestamps, quotes['close']):
                if c is not None and not math.isnan(c):
                    d_str = datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')
                    records[d_str] = float(c)
            return records
    except Exception as e:
        return {}

def run_factor_analysis():
    print(f"1. Fetching Nifty 50 benchmark (^NSEI)...")
    market_data = fetch_ticker_closes("^NSEI", range_str="5y")
    if not market_data:
        print("Failed to download Nifty 50.")
        return

    print(f"2. Fetching and analyzing {len(CANDIDATE_POOL)} candidate mid/small cap stocks...")
    stock_metrics = []

    # Get sorted market dates and compute daily market returns
    market_dates = sorted(list(market_data.keys()))
    market_rets = {}
    for i in range(1, len(market_dates)):
        prev_d, curr_d = market_dates[i-1], market_dates[i]
        m_ret = (market_data[curr_d] - market_data[prev_d]) / market_data[prev_d] * 100.0
        market_rets[curr_d] = m_ret

    m_up_days = [d for d, r in market_rets.items() if r > 0]
    m_down_days = [d for d, r in market_rets.items() if r < 0]
    
    m_ret_list = [market_rets[d] for d in market_dates[1:]]
    mean_m = sum(m_ret_list) / len(m_ret_list)
    var_m = sum((r - mean_m)**2 for r in m_ret_list) / len(m_ret_list)
    mean_m_up = sum(market_rets[d] for d in m_up_days) / len(m_up_days)
    mean_m_down = sum(market_rets[d] for d in m_down_days) / len(m_down_days)

    for ticker in CANDIDATE_POOL:
        s_data = fetch_ticker_closes(ticker, range_str="5y")
        if len(s_data) < 700:  # Require at least ~3 years of trading history
            continue

        # Common trading days
        common_d = sorted(list(set(market_dates[1:]).intersection(set(s_data.keys()))))
        if len(common_d) < 700:
            continue

        s_rets = {}
        for i in range(1, len(common_d)):
            prev_d, curr_d = common_d[i-1], common_d[i]
            s_ret = (s_data[curr_d] - s_data[prev_d]) / s_data[prev_d] * 100.0
            s_rets[curr_d] = s_ret

        # Filter down to common returns
        aligned_s = [s_rets[d] for d in common_d[1:]]
        aligned_m = [market_rets[d] for d in common_d[1:]]
        N = len(aligned_s)

        # 1. Volatility
        mean_s = sum(aligned_s) / N
        var_s = sum((r - mean_s)**2 for r in aligned_s) / N
        ann_vol = math.sqrt(var_s) * math.sqrt(252)

        # 2. Beta to Nifty
        cov_sm = sum((s - mean_s) * (m - mean_m) for s, m in zip(aligned_s, aligned_m)) / N
        beta = cov_sm / var_m if var_m > 0 else 1.0

        # 3. Upside & Downside Capture
        up_s = [s_rets[d] for d in common_d[1:] if market_rets[d] > 0]
        down_s = [s_rets[d] for d in common_d[1:] if market_rets[d] < 0]

        mean_s_up = sum(up_s) / len(up_s) if up_s else 0.0
        mean_s_down = sum(down_s) / len(down_s) if down_s else 0.0

        up_capture = (mean_s_up / mean_m_up) if mean_m_up > 0 else 1.0
        down_capture = (mean_s_down / mean_m_down) if mean_m_down < 0 else 1.0

        # Scores:
        # Aggressive Score: Wants high beta + high upside capture
        agg_score = (beta * 0.6) + (up_capture * 0.4)
        
        # Defensive Score: Wants low beta + low downside capture + low volatility
        # Normalized so higher = better defensive quality
        def_score = (2.0 - beta) * 0.4 + (2.0 - down_capture) * 0.4 + (40.0 - ann_vol) * 0.02

        stock_metrics.append({
            'ticker': ticker,
            'beta': round(beta, 2),
            'ann_vol': round(ann_vol, 2),
            'up_capture': round(up_capture, 2),
            'down_capture': round(down_capture, 2),
            'agg_score': round(agg_score, 3),
            'def_score': round(def_score, 3)
        })

    # Sort and rank
    agg_ranked = sorted(stock_metrics, key=lambda x: x['agg_score'], reverse=True)
    def_ranked = sorted(stock_metrics, key=lambda x: x['def_score'], reverse=True)

    print("\n" + "="*85)
    print("      TOP 10 AGGRESSIVE GROWTH CANDIDATES (Ranked by Beta & Upside Capture)")
    print("="*85)
    print(f"{'Rank':<5} | {'Ticker':<15} | {'Beta (β)':<10} | {'Upside Capture':<15} | {'Ann. Volatility':<16} | {'Agg Score':<10}")
    print("-" * 85)
    for i, s in enumerate(agg_ranked[:10], 1):
        print(f"{i:<5} | {s['ticker']:<15} | {s['beta']:<10} | {s['up_capture']:<15} | {s['ann_vol']:<16}% | {s['agg_score']:<10}")

    print("\n" + "="*85)
    print("      TOP 10 DEFENSIVE QUALITY CANDIDATES (Ranked by Low Beta & Low Downside)")
    print("="*85)
    print(f"{'Rank':<5} | {'Ticker':<15} | {'Beta (β)':<10} | {'Downside Capture':<16} | {'Ann. Volatility':<16} | {'Def Score':<10}")
    print("-" * 85)
    for i, s in enumerate(def_ranked[:10], 1):
        print(f"{i:<5} | {s['ticker']:<15} | {s['beta']:<10} | {s['down_capture']:<16} | {s['ann_vol']:<16}% | {s['def_score']:<10}")

    # Save ranking table to CSV
    csv_out = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/factor_screener_results.csv"
    with open(csv_out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['ticker', 'beta', 'ann_vol', 'up_capture', 'down_capture', 'agg_score', 'def_score'])
        writer.writeheader()
        writer.writerows(stock_metrics)
    print(f"\nFull factor audit table saved to {csv_out}")

if __name__ == "__main__":
    run_factor_analysis()
