"""
Data Ingestion for Algorithmically Selected 16-Stock Universe
============================================================
Pulls daily price histories for:
- 8 Aggressive Champions: DIXON, CHOLAFIN, MANAPPURAM, AARTIIND, BHARATFORG, PERSISTENT, INDHOTEL, COFORGE
- 8 Defensive Fortresses: ABBOTINDIA, TORNTPHARM, IPCALAB, MARICO, ALKEM, COLPAL, DABUR, LUPIN
- Signals: ^NSEI, ^INDIAVIX
"""

import urllib.request
import urllib.parse
import json
import csv
import math
from datetime import datetime

AGG_STOCKS = [
    'DIXON.NS', 'CHOLAFIN.NS', 'MANAPPURAM.NS', 'AARTIIND.NS',
    'BHARATFORG.NS', 'PERSISTENT.NS', 'INDHOTEL.NS', 'COFORGE.NS'
]

DEF_STOCKS = [
    'ABBOTINDIA.NS', 'TORNTPHARM.NS', 'IPCALAB.NS', 'MARICO.NS',
    'ALKEM.NS', 'COLPAL.NS', 'DABUR.NS', 'LUPIN.NS'
]

ALL_SYMBOLS = ['^NSEI', '^INDIAVIX'] + AGG_STOCKS + DEF_STOCKS

def fetch_ticker_closes(symbol, range_str="8y"):
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

def build_dataset(output_file="screened_universe_data.csv"):
    print("Fetching historical price histories for algorithmically screened stocks...")
    price_data = {}
    for s in ALL_SYMBOLS:
        print(f"  Downloading {s}...")
        price_data[s] = fetch_ticker_closes(s)

    # Intersection of dates
    common_dates = None
    for s in ALL_SYMBOLS:
        s_dates = set(price_data[s].keys())
        if common_dates is None:
            common_dates = s_dates
        else:
            common_dates = common_dates.intersection(s_dates)

    common_dates = sorted(list(common_dates))
    print(f"Found {len(common_dates)} common trading dates across all 18 instruments.")

    rows = []
    prev_prices = {}
    for d in common_dates:
        curr_prices = {s: price_data[s][d] for s in ALL_SYMBOLS}
        row = {'date': d}
        if prev_prices:
            # Signal returns
            row['nifty_ret'] = round(((curr_prices['^NSEI'] - prev_prices['^NSEI']) / prev_prices['^NSEI']) * 100.0, 4)
            row['vix_change'] = round(curr_prices['^INDIAVIX'] - prev_prices['^INDIAVIX'], 2)
            row['nifty_close'] = round(curr_prices['^NSEI'], 2)
            row['vix_close'] = round(curr_prices['^INDIAVIX'], 2)

            for s in AGG_STOCKS + DEF_STOCKS:
                r = ((curr_prices[s] - prev_prices[s]) / prev_prices[s]) * 100.0
                row[f"{s}_ret"] = round(r, 4)
                row[f"{s}_close"] = round(curr_prices[s], 2)
                
            rows.append(row)
        prev_prices = curr_prices

    if rows:
        fieldnames = list(rows[0].keys())
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Successfully saved {len(rows)} aligned records to {output_file} ({rows[0]['date']} to {rows[-1]['date']})")

if __name__ == "__main__":
    build_dataset("C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/screened_universe_data.csv")
