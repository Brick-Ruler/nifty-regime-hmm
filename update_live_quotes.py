"""
Live Quote Fetcher for NIFTY Dynamic Tracker
Primary Engine: Zerodha Kite Connect L1 Real-Time Exchange Feed
Fallback Engine: Direct Yahoo Finance v8 Fast Chart API
"""
import urllib.request
import urllib.parse
import json
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "live_quotes.json")

SYMBOLS = [
    '^NSEI', '^INDIAVIX',
    # 8 Aggressive Champions
    'DIXON.NS', 'TRENT.NS', 'KAYNES.NS', 'PERSISTENT.NS',
    'CUMMINSIND.NS', 'COFORGE.NS', 'POLYCAB.NS', 'INDHOTEL.NS',
    # 8 Defensive Fortresses
    'COLPAL.NS', 'SANOFI.NS', 'GLAXO.NS', 'MARICO.NS',
    'TORNTPHARM.NS', 'AKZOINDIA.NS', 'ALKEM.NS', 'MGL.NS'
]

def fetch_symbol_meta_yahoo(symbol):
    encoded = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=1d&interval=5m"
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            meta = data['chart']['result'][0]['meta']
            cmp = meta.get('regularMarketPrice')
            prev = meta.get('chartPreviousClose') or meta.get('previousClose')
            if cmp is not None and prev is not None:
                chg = ((cmp - prev) / prev) * 100.0
                return {'cmp': round(cmp, 2), 'prev_close': round(prev, 2), 'change_pct': round(chg, 2)}
    except Exception as e:
        print(f"Error fetching {symbol} via Yahoo: {e}")
    return None

def update_live_quotes():
    # 1. Attempt Primary Zerodha Kite Connect Feed
    try:
        from zerodha_feed import fetch_kite_quotes
        kite_quotes = fetch_kite_quotes()
        if kite_quotes and len(kite_quotes.get('stocks', {})) > 0:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(kite_quotes, f, indent=2)
            print(f"[SUCCESS] Updated live_quotes.json via Zerodha Kite Connect ({len(kite_quotes['stocks'])} stocks)!")
            return kite_quotes
    except Exception as e:
        print(f"[NOTICE] Zerodha feed not active ({e}); falling back to standard feed.")

    # 2. Fallback to Yahoo Finance Feed
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    quotes = {
        'timestamp': now_str,
        'source': 'FALLBACK_EXCHANGE_FEED',
        'stocks': {}
    }
    
    for s in SYMBOLS:
        res = fetch_symbol_meta_yahoo(s)
        if res:
            if s == '^NSEI':
                quotes['nifty'] = res
            elif s == '^INDIAVIX':
                quotes['vix'] = res
            else:
                quotes['stocks'][s] = res

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(quotes, f, indent=2)
    print(f"[SUCCESS] Updated live_quotes.json via Fallback Feed at {now_str} with {len(quotes['stocks'])} stocks!")
    return quotes

if __name__ == '__main__':
    update_live_quotes()
