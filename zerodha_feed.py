"""
Zerodha Kite Connect Market Data Feed Module
Fetches institutional Level-1 real-time quotes directly from the National Stock Exchange of India (NSE).
Supports seamless fallback to Yahoo Finance if Kite credentials or daily access token are absent.
"""
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(BASE_DIR, "kite_session.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")

SYMBOL_MAP_TO_KITE = {
    '^NSEI': 'NSE:NIFTY 50',
    '^INDIAVIX': 'NSE:INDIA VIX',
    'DIXON.NS': 'NSE:DIXON',
    'CHOLAFIN.NS': 'NSE:CHOLAFIN',
    'MANAPPURAM.NS': 'NSE:MANAPPURAM',
    'AARTIIND.NS': 'NSE:AARTIIND',
    'BHARATFORG.NS': 'NSE:BHARATFORG',
    'PERSISTENT.NS': 'NSE:PERSISTENT',
    'INDHOTEL.NS': 'NSE:INDHOTEL',
    'COFORGE.NS': 'NSE:COFORGE',
    'ABBOTINDIA.NS': 'NSE:ABBOTINDIA',
    'TORNTPHARM.NS': 'NSE:TORNTPHARM',
    'IPCALAB.NS': 'NSE:IPCALAB',
    'MARICO.NS': 'NSE:MARICO',
    'ALKEM.NS': 'NSE:ALKEM',
    'COLPAL.NS': 'NSE:COLPAL',
    'DABUR.NS': 'NSE:DABUR',
    'LUPIN.NS': 'NSE:LUPIN'
}

def load_credentials():
    """Load Kite API Key and Access Token from env or session file."""
    api_key = os.environ.get("KITE_API_KEY")
    access_token = os.environ.get("KITE_ACCESS_TOKEN")

    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        if k == "KITE_API_KEY" and not api_key:
                            api_key = v.strip()
                        elif k == "KITE_ACCESS_TOKEN" and not access_token:
                            access_token = v.strip()
        except Exception:
            pass

    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not api_key:
                    api_key = data.get("api_key")
                if not access_token:
                    access_token = data.get("access_token")
        except Exception:
            pass

    return api_key, access_token

def fetch_kite_quotes():
    """
    Fetches real-time Level-1 quotes from Zerodha Kite Connect.
    Returns dictionary structured for live_quotes.json, or None if unavailable.
    """
    api_key, access_token = load_credentials()
    if not api_key or not access_token:
        return None

    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)

        kite_symbols = list(SYMBOL_MAP_TO_KITE.values())
        raw_quotes = kite.quote(kite_symbols)

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        quotes = {
            'timestamp': now_str,
            'source': 'ZERODHA_KITE_CONNECT_L1',
            'stocks': {}
        }

        # Invert map for quick lookup
        reverse_map = {v: k for k, v in SYMBOL_MAP_TO_KITE.items()}

        for kite_sym, q in raw_quotes.items():
            native_sym = reverse_map.get(kite_sym)
            if not native_sym:
                continue

            cmp = q.get('last_price', 0.0)
            ohlc = q.get('ohlc', {})
            prev = ohlc.get('close') or cmp
            chg = ((cmp - prev) / prev) * 100.0 if prev > 0 else 0.0

            quote_obj = {
                'cmp': round(cmp, 2),
                'prev_close': round(prev, 2),
                'change_pct': round(chg, 2)
            }

            if native_sym == '^NSEI':
                quotes['nifty'] = quote_obj
            elif native_sym == '^INDIAVIX':
                quotes['vix'] = quote_obj
            else:
                quotes['stocks'][native_sym] = quote_obj

        print(f"[ZERODHA] Successfully fetched {len(raw_quotes)} instruments via Zerodha Kite Connect at {now_str}!")
        return quotes

    except Exception as e:
        print(f"[ZERODHA WARNING] Kite Connect quote fetch encountered: {e}")
        return None
