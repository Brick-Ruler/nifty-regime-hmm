"""
NIFTY 50 & INDIA VIX Pure-Python Data Ingestor
==============================================
Downloads daily price history from Yahoo Finance API directly using
standard Python libraries (no external C-extensions required).
"""

import urllib.request
import json
import csv
import math
from datetime import datetime

def fetch_ticker_data(symbol, range_str="10y"):
    """
    Fetches historical daily chart data for a ticker symbol from Yahoo Finance API.
    """
    # URL encode symbol (e.g. ^NSEI -> %5ENSEI)
    encoded_symbol = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_symbol}?range={range_str}&interval=1d"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            quotes = result['indicators']['quote'][0]
            
            records = {}
            for t, close, high, low, op in zip(timestamps, quotes['close'], quotes['high'], quotes['low'], quotes['open']):
                if close is not None and not math.isnan(close):
                    date_str = datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')
                    records[date_str] = {
                        'close': float(close),
                        'high': float(high) if high is not None else float(close),
                        'low': float(low) if low is not None else float(close),
                        'open': float(op) if op is not None else float(close)
                    }
            return records
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return {}

def build_dataset(output_csv="nifty_vix_clean.csv"):
    print("1. Fetching Nifty 50 (^NSEI)...")
    nifty_data = fetch_ticker_data("^NSEI", range_str="10y")
    
    print("2. Fetching India VIX (^INDIAVIX)...")
    vix_data = fetch_ticker_data("^INDIAVIX", range_str="10y")
    
    # Common dates where both Nifty and India VIX traded
    common_dates = sorted(list(set(nifty_data.keys()).intersection(set(vix_data.keys()))))
    print(f"-> Found {len(common_dates)} matching trading sessions.")
    
    rows = []
    prev_nifty_close = None
    prev_vix_close = None
    
    for date in common_dates:
        n_close = nifty_data[date]['close']
        v_close = vix_data[date]['close']
        
        if prev_nifty_close is not None and prev_vix_close is not None:
            # 1. Nifty Daily Return (%)
            nifty_ret = ((n_close - prev_nifty_close) / prev_nifty_close) * 100.0
            
            # 2. Nifty Daily Log Return
            nifty_log_ret = math.log(n_close / prev_nifty_close)
            
            # 3. India VIX Absolute Change (points)
            vix_change = v_close - prev_vix_close
            
            # 4. India VIX % Change
            vix_pct_change = ((v_close - prev_vix_close) / prev_vix_close) * 100.0
            
            rows.append({
                'date': date,
                'nifty_close': round(n_close, 2),
                'vix_close': round(v_close, 2),
                'nifty_ret': round(nifty_ret, 4),
                'nifty_log_ret': round(nifty_log_ret, 6),
                'vix_change': round(vix_change, 2),
                'vix_pct_change': round(vix_pct_change, 2)
            })
            
        prev_nifty_close = n_close
        prev_vix_close = v_close

    # Write to CSV
    if rows:
        fieldnames = ['date', 'nifty_close', 'vix_close', 'nifty_ret', 'nifty_log_ret', 'vix_change', 'vix_pct_change']
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            
        print(f"\nSuccessfully created {output_csv} with {len(rows)} records!")
        print(f"Date range: {rows[0]['date']} to {rows[-1]['date']}")
        print("\nFirst 3 records:")
        for r in rows[:3]:
            print(f"  {r['date']} | Nifty: {r['nifty_close']:8.2f} ({r['nifty_ret']:+6.2f}%) | VIX: {r['vix_close']:5.2f} ({r['vix_pct_change']:+6.2f}%)")
        print("...")
        print("Latest 3 records:")
        for r in rows[-3:]:
            print(f"  {r['date']} | Nifty: {r['nifty_close']:8.2f} ({r['nifty_ret']:+6.2f}%) | VIX: {r['vix_close']:5.2f} ({r['vix_pct_change']:+6.2f}%)")
    else:
        print("Error: No data rows collected.")

if __name__ == "__main__":
    build_dataset("C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/nifty_vix_clean.csv")
