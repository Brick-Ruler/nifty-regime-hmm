"""
Mid & Small Cap Universe Data Ingestion Engine
==============================================
Downloads daily price history for 16 curated Mid & Small Cap leaders:
- 8 Aggressive Growth Stocks (High-beta, industrials, discretionaries, cyclicals)
- 8 Defensive Quality Stocks (Low-beta, pharma, FMCG staples, city gas utilities)
plus Nifty 50 Index (^NSEI) and India VIX (^INDIAVIX) as regime signals.
"""

import urllib.request
import urllib.parse
import json
import csv
import math
from datetime import datetime

AGGRESSIVE_STOCKS = [
    'VOLTAS.NS', 'BHARATFORG.NS', 'CUMMINSIND.NS', 'ASTRAL.NS',
    'DIXON.NS', 'INDHOTEL.NS', 'CHOLAFIN.NS', 'FEDERALBNK.NS'
]

DEFENSIVE_STOCKS = [
    'TORNTPHARM.NS', 'ALKEM.NS', 'IPCALAB.NS', 'COROMANDEL.NS',
    'MARICO.NS', 'EMAMILTD.NS', 'IGL.NS', 'MGL.NS'
]

ALL_TICKERS = ['^NSEI', '^INDIAVIX'] + AGGRESSIVE_STOCKS + DEFENSIVE_STOCKS

def fetch_ticker_data(symbol, range_str="8y"):
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
        print(f"Error fetching {symbol}: {e}")
        return {}

def build_universe(output_file="mid_small_universe.csv"):
    print(f"Downloading 16 Mid/Small Cap stocks + Signals ({len(ALL_TICKERS)} total instruments)...")
    ticker_data = {}
    for ticker in ALL_TICKERS:
        print(f"  Fetching {ticker}...")
        ticker_data[ticker] = fetch_ticker_data(ticker)

    # Intersect all available dates
    common_dates = None
    for ticker in ALL_TICKERS:
        dates_set = set(ticker_data[ticker].keys())
        if common_dates is None:
            common_dates = dates_set
        else:
            common_dates = common_dates.intersection(dates_set)

    common_dates = sorted(list(common_dates))
    print(f"Found {len(common_dates)} common trading dates across all 18 instruments.")

    rows = []
    prev_prices = {}
    for d in common_dates:
        curr_prices = {t: ticker_data[t][d] for t in ALL_TICKERS}
        
        row = {'date': d}
        if prev_prices:
            # Signal returns
            row['nifty_ret'] = round(((curr_prices['^NSEI'] - prev_prices['^NSEI']) / prev_prices['^NSEI']) * 100.0, 4)
            row['vix_change'] = round(curr_prices['^INDIAVIX'] - prev_prices['^INDIAVIX'], 2)
            row['nifty_close'] = round(curr_prices['^NSEI'], 2)
            row['vix_close'] = round(curr_prices['^INDIAVIX'], 2)

            # Stock returns
            for t in AGGRESSIVE_STOCKS + DEFENSIVE_STOCKS:
                ret = ((curr_prices[t] - prev_prices[t]) / prev_prices[t]) * 100.0
                row[f"{t}_ret"] = round(ret, 4)
                row[f"{t}_close"] = round(curr_prices[t], 2)
                
            rows.append(row)
            
        prev_prices = curr_prices

    # Write to CSV
    if rows:
        fieldnames = list(rows[0].keys())
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            
        print(f"\nSaved universe dataset to {output_file} ({len(rows)} trading days from {rows[0]['date']} to {rows[-1]['date']})")

if __name__ == "__main__":
    build_universe("C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/mid_small_universe.csv")
