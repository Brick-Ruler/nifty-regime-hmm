"""
Live Quote Fetcher for NIFTY Dynamic Tracker
Fetches live NSE prices for NIFTY 50, India VIX, and all portfolio stocks.
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
    'DIXON.NS', 'CHOLAFIN.NS', 'MANAPPURAM.NS', 'AARTIIND.NS',
    'BHARATFORG.NS', 'PERSISTENT.NS', 'INDHOTEL.NS', 'COFORGE.NS',
    'ABBOTINDIA.NS', 'TORNTPHARM.NS', 'IPCALAB.NS', 'MARICO.NS',
    'ALKEM.NS', 'COLPAL.NS', 'DABUR.NS', 'LUPIN.NS'
]

def fetch_symbol_meta(symbol):
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
        print(f"Error fetching {symbol}: {e}")
    return None

def update_live_quotes():
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    quotes = {
        'timestamp': now_str,
        'stocks': {}
    }
    
    for s in SYMBOLS:
        res = fetch_symbol_meta(s)
        if res:
            if s == '^NSEI':
                quotes['nifty'] = res
            elif s == '^INDIAVIX':
                quotes['vix'] = res
            else:
                quotes['stocks'][s] = res

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(quotes, f, indent=2)
    print(f"Successfully updated live_quotes.json at {now_str} with {len(quotes['stocks'])} stocks!")
    return quotes

if __name__ == '__main__':
    update_live_quotes()
