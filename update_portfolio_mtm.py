import json
import urllib.request
import urllib.parse
from datetime import datetime

LEDGER_FILE = "portfolio_ledger.json"

with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
    ledger = json.load(f)

holdings = ledger.get('holdings', {})
cash_buffer = ledger.get('cash_buffer', 549.2)

print("Fetching real-time NSE market quotes...")
total_equity_val = 0.0
total_prev_equity_val = 0.0

stock_summary = []

for sym, info in holdings.items():
    shares = info.get('shares', 0)
    if shares <= 0:
        continue
    
    encoded = urllib.parse.quote(sym)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=1d&interval=5m"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    cmp = info.get('buy_price', 0.0)
    prev_close = cmp
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            meta = data['chart']['result'][0]['meta']
            c = meta.get('regularMarketPrice')
            p = meta.get('chartPreviousClose') or meta.get('previousClose')
            if c is not None:
                cmp = round(c, 2)
            if p is not None:
                prev_close = round(p, 2)
    except Exception as e:
        print(f"Notice fetching {sym}: {e}")

    cur_val = round(shares * cmp, 2)
    prev_val = round(shares * prev_close, 2)
    day_pnl = round(cur_val - prev_val, 2)
    day_pct = round(((cmp - prev_close) / prev_close) * 100.0, 2) if prev_close else 0.0
    
    buy_price = info.get('buy_price', cmp)
    total_cost = round(shares * buy_price, 2)
    unrealized_pnl = round(cur_val - total_cost, 2)
    unrealized_pct = round((unrealized_pnl / total_cost) * 100.0, 2) if total_cost > 0 else 0.0

    total_equity_val += cur_val
    total_prev_equity_val += prev_val

    # Update ledger record
    info['cmp'] = cmp
    info['prev_close'] = prev_close
    info['current_value'] = cur_val
    info['day_change_pct'] = day_pct
    info['day_pnl'] = day_pnl
    info['unrealized_pnl'] = unrealized_pnl
    info['unrealized_pnl_pct'] = unrealized_pct

    stock_summary.append({
        'symbol': sym.replace('.NS', ''),
        'name': info.get('name'),
        'sector': info.get('sector'),
        'shares': shares,
        'buy_price': buy_price,
        'cmp': cmp,
        'prev_close': prev_close,
        'cost': total_cost,
        'current_val': cur_val,
        'day_pnl': day_pnl,
        'day_pct': day_pct,
        'unrealized_pnl': unrealized_pnl,
        'unrealized_pct': unrealized_pct
    })

total_portfolio_val = round(total_equity_val + cash_buffer, 2)
initial_val = ledger.get('initial_portfolio_value', 100000.0)
overall_pnl = round(total_portfolio_val - initial_val, 2)
overall_pct = round((overall_pnl / initial_val) * 100.0, 2)

day_total_pnl = round(total_equity_val - total_prev_equity_val, 2)
prev_total_val = round(total_prev_equity_val + cash_buffer, 2)
day_total_pct = round((day_total_pnl / prev_total_val) * 100.0, 2)

now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

ledger['equity_value'] = round(total_equity_val, 2)
ledger['cash_buffer'] = round(cash_buffer, 2)
ledger['total_portfolio_value'] = total_portfolio_val
ledger['last_updated'] = now_str
ledger['day_pnl'] = day_total_pnl
ledger['day_pnl_pct'] = day_total_pct
ledger['overall_pnl'] = overall_pnl
ledger['overall_pnl_pct'] = overall_pct

with open(LEDGER_FILE, 'w', encoding='utf-8') as f:
    json.dump(ledger, f, indent=2)

print("\n" + "=" * 95)
print(f"      PORTFOLIO MARK-TO-MARKET VALUATION AUDIT ({now_str} IST)")
print("=" * 95)
print(f"Initial Base Capital:     Rs. {initial_val:>10,.2f}")
print(f"Current Equity Value:     Rs. {total_equity_val:>10,.2f}  ({(total_equity_val / total_portfolio_val)*100:.1f}%)")
print(f"Liquid Cash Buffer:       Rs. {cash_buffer:>10,.2f}  ({(cash_buffer / total_portfolio_val)*100:.1f}%)")
print(f"-----------------------------------------------------------------------------------------------")
print(f"TOTAL PORTFOLIO BALANCE:  Rs. {total_portfolio_val:>10,.2f}")
print(f"Today's Day Gain/Loss:    Rs. {day_total_pnl:>+10,.2f}  ({day_total_pct:+5.2f}%)")
print(f"Cumulative P&L (Unreal):  Rs. {overall_pnl:>+10,.2f}  ({overall_pct:+5.2f}%) vs Initial Capital")
print("=" * 95)

print(f"{'SYMBOL':<12} | {'SECTOR':<22} | {'SH':<3} | {'BUY':>8} | {'CMP':>8} | {'VAL (Rs)':>9} | {'DAY %':>6} | {'P&L (Rs)':>9} | {'P&L %':>6}")
print("-" * 95)
for s in stock_summary:
    print(f"{s['symbol']:<12} | {s['sector'][:22]:<22} | {s['shares']:>3} | {s['buy_price']:>8.1f} | {s['cmp']:>8.1f} | {s['current_val']:>9.2f} | {s['day_pct']:>+5.2f}% | {s['unrealized_pnl']:>+9.2f} | {s['unrealized_pct']:>+5.2f}%")
print("=" * 95)
