"""
Initialize 1-Share Portfolio Ledger
===================================
Sets up the starting portfolio with exactly 1 share of each of the 16 stocks.
"""

import os
import sys
import json

# Add current directory to path
sys.path.append("C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm")
from daily_portfolio_advisor import AGG_STOCKS, DEF_STOCKS, fetch_latest_quote

def initialize_ledger():
    holdings = {}
    total_val = 0.0

    print("Fetching current live prices for 1-share portfolio initialization...")
    for sym, name, sec in AGG_STOCKS:
        price, _ = fetch_latest_quote(sym)
        price = price if price is not None else 1000.0
        holdings[sym] = {
            'name': name,
            'basket': 'AGGRESSIVE',
            'sector': sec,
            'shares': 1,
            'buy_price': round(price, 2),
            'cmp': round(price, 2),
            'current_value': round(price, 2)
        }
        total_val += price
        print(f"  {sym:<14} (1 share @ Rs. {price:,.2f})")

    for sym, name, sec in DEF_STOCKS:
        price, _ = fetch_latest_quote(sym)
        price = price if price is not None else 1000.0
        holdings[sym] = {
            'name': name,
            'basket': 'DEFENSIVE',
            'sector': sec,
            'shares': 1,
            'buy_price': round(price, 2),
            'cmp': round(price, 2),
            'current_value': round(price, 2)
        }
        total_val += price
        print(f"  {sym:<14} (1 share @ Rs. {price:,.2f})")

    ledger = {
        'initialized_at': '2026-11-17 22:15:00',
        'portfolio_mode': 'PAPER_TRADING_LIVE_TRACKING',
        'active_regime': 'AGGRESSIVE GROWTH',
        'cash_buffer': 5000.0,
        'equity_value': round(total_val, 2),
        'total_portfolio_value': round(total_val + 5000.0, 2),
        'holdings': holdings,
        'trade_log': []
    }

    out_file = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/portfolio_ledger.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(ledger, f, indent=2)

    print("\n" + "="*70)
    print(f"Portfolio ledger successfully created at: {out_file}")
    print(f"Total Invested in 16 Shares: Rs. {total_val:,.2f}")
    print(f"Cash Buffer:                 Rs.  5,000.00")
    print(f"Total Portfolio Value:       Rs. {total_val + 5000.0:,.2f}")
    print("="*70)

if __name__ == "__main__":
    initialize_ledger()
