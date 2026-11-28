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
    '^NSEI', '^INDIAVIX', 'MID150BEES.NS',
    # 8 Aggressive Champions (Option B Top-5 Sector Rotation)
    'PERSISTENT.NS', 'COFORGE.NS', 'CHOLAFIN.NS', 'FEDERALBNK.NS',
    'INDHOTEL.NS', 'EIHOTEL.NS', 'BALKRISIND.NS', 'DIXON.NS',
    # 8 Distinct Defensive Fortresses
    'COLPAL.NS', 'GLAXO.NS', 'MARICO.NS', 'TORNTPHARM.NS',
    'KANSAINER.NS', 'MGL.NS', 'COROMANDEL.NS', 'PETRONET.NS'
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

def fetch_open_price_yahoo(symbol):
    """Fetches today's actual market open price (falling back to regularMarketPrice)."""
    encoded = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=1d&interval=5m"
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = data['chart']['result'][0]
            opens = [o for o in result['indicators']['quote'][0].get('open', []) if o is not None]
            if opens:
                return round(float(opens[0]), 2)
            cmp = result['meta'].get('regularMarketPrice')
            if cmp is not None:
                return round(float(cmp), 2)
    except Exception as e:
        print(f"Error fetching open price for {symbol}: {e}")
    return None

def process_pending_cash_deployment(ledger_path=None):
    """
    Executes queued cash deployment orders at the next trading day's opening price
    (>= execute_on_or_after at >= 09:15 IST) and reconciles all ledger totals.
    """
    from datetime import timezone, timedelta
    lpath = ledger_path or os.path.join(BASE_DIR, "portfolio_ledger.json")
    if not os.path.exists(lpath):
        return False
    with open(lpath, 'r', encoding='utf-8') as f:
        ledger = json.load(f)

    pending = ledger.get('pending_cash_deployment')
    if not pending or pending.get('status') != 'PENDING_NEXT_OPEN':
        return False

    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(timezone.utc).astimezone(ist_tz)
    today_ist = now_ist.strftime('%Y-%m-%d')
    exec_after = pending.get('execute_on_or_after', '2026-11-30')

    if now_ist.weekday() > 4 or today_ist < exec_after:
        return False
    if (now_ist.hour * 60 + now_ist.minute) < 555:  # Before 09:15 IST
        return False

    executed_orders = []
    total_buy = 0.0
    cash_avail = float(ledger.get('cash_buffer', 0.0))

    for order in pending.get('orders', []):
        sym = order['symbol']
        req_sh = int(order['shares'])
        h = ledger.get('holdings', {}).get(sym)
        if not h or req_sh <= 0:
            continue
        open_p = fetch_open_price_yahoo(sym) or float(h.get('cmp', 0.0))
        if open_p <= 0:
            continue
        affordable_sh = min(req_sh, int((cash_avail - total_buy) // (open_p * 1.0015)))
        if affordable_sh <= 0:
            continue

        order_val = round(affordable_sh * open_p, 2)
        old_sh = int(h.get('shares', 0))
        old_cost = float(h.get('invested_cost', old_sh * float(h.get('buy_price', open_p))))
        new_sh = old_sh + affordable_sh
        new_cost = round(old_cost + order_val, 2)
        new_avg_buy = round(new_cost / new_sh, 2)

        h['shares'] = new_sh
        h['buy_price'] = new_avg_buy
        h['invested_cost'] = new_cost
        h['cmp'] = open_p
        h['current_value'] = round(new_sh * open_p, 2)
        h['unrealized_pnl'] = round(h['current_value'] - new_cost, 2)
        h['unrealized_pnl_pct'] = round((h['unrealized_pnl'] / new_cost) * 100.0, 2) if new_cost > 0 else 0.0

        total_buy += order_val
        executed_orders.append({'ticker': sym, 'action': 'BUY_OPEN_SWEEP', 'shares': affordable_sh, 'price': open_p, 'value': order_val})

    if not executed_orders:
        return False

    fee = round(total_buy * 0.001, 2)  # 10 bps delivery STT/stamp duty
    ledger['cash_buffer'] = round(cash_avail - total_buy - fee, 2)
    ledger['cumulative_friction_paid'] = round(float(ledger.get('cumulative_friction_paid', 0.0)) + fee, 2)

    eq_val = sum(float(v.get('current_value', 0.0)) for v in ledger['holdings'].values() if v.get('shares', 0) > 0)
    cost_val = sum(float(v.get('invested_cost', 0.0)) for v in ledger['holdings'].values() if v.get('shares', 0) > 0)
    ledger['equity_value'] = round(eq_val, 2)
    ledger['current_equity_value'] = round(eq_val, 2)
    ledger['invested_equity_cost'] = round(cost_val, 2)
    ledger['equity_pnl'] = round(eq_val - cost_val, 2)
    ledger['equity_pnl_pct'] = round((ledger['equity_pnl'] / cost_val) * 100.0, 2) if cost_val > 0 else 0.0
    ledger['total_account_nav'] = round(eq_val + ledger['cash_buffer'], 2)
    ledger['total_portfolio_value'] = ledger['total_account_nav']

    now_str = now_ist.strftime('%Y-%m-%d %H:%M')
    ledger.setdefault('trade_log', []).append({
        'date': now_str,
        'action': 'CASH_DEPLOYMENT_COMBO_A',
        'orders': executed_orders,
        'fee': fee,
        'remaining_cash': ledger['cash_buffer']
    })
    pending['status'] = 'EXECUTED'
    pending['executed_at'] = now_str
    pending['fills'] = executed_orders

    with open(lpath, 'w', encoding='utf-8') as f:
        json.dump(ledger, f, indent=2)
    print(f"[CASH SWEEP EXECUTED] Deployed Rs. {total_buy:,.2f} (Fee Rs. {fee:.2f}); remaining cash Rs. {ledger['cash_buffer']:.2f}.")
    return True

def update_live_quotes():
    try:
        process_pending_cash_deployment()
    except Exception as e:
        print(f"[WARN] Pending cash deployment check: {e}")
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
            elif s == 'MID150BEES.NS':
                quotes['midcap150'] = res
            else:
                quotes['stocks'][s] = res

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(quotes, f, indent=2)
    print(f"[SUCCESS] Updated live_quotes.json via Fallback Feed at {now_str} with {len(quotes['stocks'])} stocks!")
    return quotes

if __name__ == '__main__':
    update_live_quotes()
