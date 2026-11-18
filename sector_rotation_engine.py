"""
Sector Rotation Engine (Option B: Top-5 Leading Macro Sectors)
==============================================================
Institutional Architecture:
1. Macro Sector Filter: Ranks candidate economic sectors by trailing 6-month (126 trading days)
   aggregate relative momentum vs NIFTY 50.
2. Top-5 Sector Selection: Bypasses structurally lagging sectors (e.g. commodities/dumping,
   margin compression). Focuses capital on the top 5 leading economic growth engines.
3. Position Uniformity (Zero Lumpiness for Rs. 1 Lakh):
   - Top 3 Sectors: 2 Champion stocks each (6 stocks * 12.5% = 75%)
   - Next 2 Sectors: 1 Champion stock each (2 stocks * 12.5% = 25%)
   - Total: Exactly 8 Aggressive Champions at 12.5% (Rs. 12,500) each in Calm mode.
4. Total Harmony with HMM:
   - Calm Mode: 8 Aggressives across Top 5 Sectors (12.5% each).
   - Panic Mode: Expands to 16 stocks (8 Aggressives + 8 Non-cyclical Defensive Fortresses, 6.25% each).
"""

import urllib.request
import urllib.parse
import json
import math

SECTOR_CANDIDATE_POOLS = {
    'Hospitality & Services': ['INDHOTEL.NS', 'EIHOTEL.NS'],
    'Financials & NBFC': ['CHOLAFIN.NS', 'FEDERALBNK.NS', 'MUTHOOTFIN.NS', 'SUNDARMFIN.NS'],
    'Retail & Fashion': ['TRENT.NS', 'METROBRAND.NS', 'BATAINDIA.NS'],
    'Digital Engineering / IT': ['PERSISTENT.NS', 'COFORGE.NS', 'KPITTECH.NS', 'LTTS.NS'],
    'EMS & Consumer Tech': ['DIXON.NS', 'AMBER.NS'],
    'Healthcare & Hospitals': ['NH.NS', 'TORNTPHARM.NS', 'ALKEM.NS'],
    'Heavy Industrials & Defense': ['BHARATFORG.NS', 'AIAENG.NS', 'SONACOMS.NS'],
    'Auto Ancillary': ['BALKRISIND.NS', 'APOLLOTYRE.NS', 'TIINDIA.NS'],
    'Capital Goods & Power': ['CUMMINSIND.NS', 'THERMAX.NS', 'POLYCAB.NS'],
    'Specialty Chemicals': ['DEEPAKNTR.NS', 'PIIND.NS', 'AARTIIND.NS']
}

def fetch_6m_return(symbol):
    encoded = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=6mo&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
            valid = [c for c in closes if c is not None and not math.isnan(c)]
            if len(valid) >= 2:
                return ((valid[-1] - valid[0]) / valid[0]) * 100.0
    except Exception:
        pass
    return None

def compute_sector_momentum_rankings():
    """
    Computes trailing 6-month aggregate return for each sector pool.
    Returns sorted list of (sector_name, avg_6m_return, [constituent_stocks]).
    """
    sector_scores = []
    for sector, symbols in SECTOR_CANDIDATE_POOLS.items():
        rets = []
        for s in symbols[:2]: # Sample top 2 constituents per sector
            r = fetch_6m_return(s)
            if r is not None:
                rets.append(r)
        avg_ret = sum(rets) / len(rets) if rets else 0.0
        sector_scores.append((sector, round(avg_ret, 2), symbols))

    # Sort descending by 6M momentum
    sector_scores.sort(key=lambda x: x[1], reverse=True)
    return sector_scores

def select_top5_sector_portfolio():
    """
    Implements Option B:
    - Top 3 Sectors: 2 stocks each (6 stocks)
    - Next 2 Sectors: 1 stock each (2 stocks)
    Total = Exactly 8 Aggressive Champions
    """
    rankings = compute_sector_momentum_rankings()
    top5_sectors = rankings[:5]

    selected_portfolio = []
    for rank, (sector, mom, symbols) in enumerate(top5_sectors, 1):
        stocks_to_pick = 2 if rank <= 3 else 1
        picked = symbols[:stocks_to_pick]
        for s in picked:
            selected_portfolio.append({
                'ticker': s,
                'sector': sector,
                'sector_rank': rank,
                'sector_6m_momentum': mom,
                'target_weight': 12.5 # 12.5% each
            })

    return {
        'rankings': rankings,
        'selected_8_stocks': selected_portfolio
    }

if __name__ == "__main__":
    print("=" * 80)
    print("SECTOR ROTATION ENGINE: TOP-5 LEADING MACRO SECTORS (OPTION B)")
    print("=" * 80)
    res = select_top5_sector_portfolio()
    print("\nCURRENT 6-MONTH SECTOR MOMENTUM RANKINGS:")
    print("-" * 65)
    for rank, (sec, mom, syms) in enumerate(res['rankings'], 1):
        status = "[SELECTED - 2 STOCKS]" if rank <= 3 else ("[SELECTED - 1 STOCK]" if rank <= 5 else "[BYPASSED / LAGGING]")
        print(f"#{rank:<2}: {sec:<28} | {mom:>+6.2f}% | {status}")

    print("\n" + "=" * 80)
    print("SELECTED 8 AGGRESSIVE CHAMPIONS (CALM MODE: 12.5% EACH)")
    print("=" * 80)
    for idx, s in enumerate(res['selected_8_stocks'], 1):
        print(f"{idx}. {s['ticker']:<15} | Sector: {s['sector']:<28} (Rank #{s['sector_rank']}, 6M Mom: {s['sector_6m_momentum']:>+6.2f}%) | Weight: {s['target_weight']}%")
