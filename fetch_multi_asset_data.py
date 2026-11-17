"""
Multi-Asset Real-World Indian Market Data Ingestion
===================================================
Fetches daily prices for:
1. Signal Assets:
   - Nifty 50 Index (^NSEI)
   - India VIX (^INDIAVIX)
2. Execution / Tradeable Assets:
   - NIFTYBEES.NS (Nifty 50 ETF)
   - GOLDBEES.NS (Gold ETF)
"""

import urllib.request
import urllib.parse
import json
import csv
import math
from datetime import datetime

def fetch_ticker(symbol, range_str="10y"):
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
            for t, c, o in zip(timestamps, quotes['close'], quotes['open']):
                if c is not None and not math.isnan(c):
                    d_str = datetime.utcfromtimestamp(t).strftime('%Y-%m-%d')
                    records[d_str] = {
                        'close': float(c),
                        'open': float(o) if o is not None and not math.isnan(o) else float(c)
                    }
            return records
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return {}

def build_multi_asset_dataset(output_path="multi_asset_data.csv"):
    print("Fetching historical quotes for real tradeable universe...")
    nifty = fetch_ticker("^NSEI")
    vix = fetch_ticker("^INDIAVIX")
    niftybees = fetch_ticker("NIFTYBEES.NS")
    goldbees = fetch_ticker("GOLDBEES.NS")
    
    # Common intersection of trading dates
    common_dates = sorted(list(
        set(nifty.keys()) & set(vix.keys()) & set(niftybees.keys()) & set(goldbees.keys())
    ))
    print(f"Found {len(common_dates)} fully aligned trading sessions across all 4 assets.")
    
    rows = []
    prev_nifty = None
    prev_vix = None
    prev_niftybees = None
    prev_goldbees = None
    
    for d in common_dates:
        nc = nifty[d]['close']
        vc = vix[d]['close']
        nb_c = niftybees[d]['close']
        nb_o = niftybees[d]['open']
        gb_c = goldbees[d]['close']
        gb_o = goldbees[d]['open']
        
        if prev_nifty is not None:
            # Daily returns
            nifty_ret = ((nc - prev_nifty) / prev_nifty) * 100.0
            vix_change = vc - prev_vix
            vix_pct = ((vc - prev_vix) / prev_vix) * 100.0
            niftybees_ret = ((nb_c - prev_niftybees) / prev_niftybees) * 100.0
            goldbees_ret = ((gb_c - prev_goldbees) / prev_goldbees) * 100.0
            
            rows.append({
                'date': d,
                'nifty_close': round(nc, 2),
                'vix_close': round(vc, 2),
                'nifty_ret': round(nifty_ret, 4),
                'vix_change': round(vix_change, 2),
                'vix_pct': round(vix_pct, 2),
                'niftybees_close': round(nb_c, 2),
                'niftybees_open': round(nb_o, 2),
                'niftybees_ret': round(niftybees_ret, 4),
                'goldbees_close': round(gb_c, 2),
                'goldbees_open': round(gb_o, 2),
                'goldbees_ret': round(goldbees_ret, 4),
            })
            
        prev_nifty = nc
        prev_vix = vc
        prev_niftybees = nb_c
        prev_goldbees = gb_c

    fieldnames = [
        'date', 'nifty_close', 'vix_close', 'nifty_ret', 'vix_change', 'vix_pct',
        'niftybees_close', 'niftybees_open', 'niftybees_ret',
        'goldbees_close', 'goldbees_open', 'goldbees_ret'
    ]
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Saved dataset to {output_path} ({len(rows)} records from {rows[0]['date']} to {rows[-1]['date']})")

if __name__ == "__main__":
    build_multi_asset_dataset("C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/multi_asset_data.csv")
