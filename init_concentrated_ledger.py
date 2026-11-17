"""
Initialize Rs. 1,00,000 Concentrated Bull Portfolio Ledger
===========================================================
Capital: Rs. 1,00,000
Active Regime: CALM BULL -> 100% Concentrated in the 8 Aggressive Champions (12.5% each)
"""

import os
import sys
import json

sys.path.append("C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm")
from daily_portfolio_advisor import AGG_STOCKS, DEF_STOCKS, fetch_latest_quote

def initialize_1lakh_ledger():
    total_capital = 100000.0
    target_per_stock = total_capital / len(AGG_STOCKS)  # Rs. 12,500 each

    print(f"Initializing Rs. 1 Lakh Concentrated Bull Portfolio across 8 Aggressive Champions...")
    print(f"Target allocation per stock: Rs. {target_per_stock:,.2f} (12.5%)\n")

    holdings = {}
    spent_equity = 0.0

    print(f"{'Ticker':<14} | {'Name':<22} | {'CMP (Rs)':<10} | {'Shares':<8} | {'Total Cost (Rs)':<15}")
    print("-" * 80)

    for sym, name, sec in AGG_STOCKS:
        price, _ = fetch_latest_quote(sym)
        price = price if price is not None else 1000.0
        shares = max(1, round(target_per_stock / price))
        cost = shares * price
        spent_equity += cost
        holdings[sym] = {
            'name': name,
            'basket': 'AGGRESSIVE',
            'sector': sec,
            'shares': shares,
            'buy_price': round(price, 2),
            'cmp': round(price, 2),
            'current_value': round(cost, 2)
        }
        print(f"{sym:<14} | {name:<22} | Rs.{price:>8.1f} | {shares:>6} | Rs.{cost:>12,.2f}")

    # Defensives currently hold 0 shares in Bull mode
    for sym, name, sec in DEF_STOCKS:
        price, _ = fetch_latest_quote(sym)
        price = price if price is not None else 1000.0
        holdings[sym] = {
            'name': name,
            'basket': 'DEFENSIVE',
            'sector': sec,
            'shares': 0,
            'buy_price': round(price, 2),
            'cmp': round(price, 2),
            'current_value': 0.0
        }

    cash_remaining = total_capital - spent_equity

    ledger = {
        'initialized_at': '2026-11-17 22:35:00',
        'portfolio_mode': 'DYNAMIC_CONCENTRATION_PAPER_TRADING',
        'strategy_name': 'HMM Dynamic Concentration (8 in Bull / 16 in Panic)',
        'initial_portfolio_value': total_capital,
        'initial_nifty_close': 25387.40,
        'peak_portfolio_value': total_capital,
        'active_regime': 'AGGRESSIVE GROWTH',
        'cash_buffer': round(cash_remaining, 2),
        'equity_value': round(spent_equity, 2),
        'total_portfolio_value': round(spent_equity + cash_remaining, 2),
        'cumulative_friction_paid': 0.0,
        'holdings': holdings,
        'trade_log': [{
            'date': '2026-11-17 22:35',
            'action': 'PORTFOLIO_INIT',
            'note': 'Initial allocation of Rs. 1 Lakh into 8 Aggressive Champions (12.5% each)'
        }],
        'history': [{
            'date': '2026-11-17',
            'value': round(spent_equity + cash_remaining, 2),
            'nifty_close': 25387.40,
            'regime': 'AGGRESSIVE GROWTH'
        }]
    }

    out_file = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/portfolio_ledger.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(ledger, f, indent=2)

    print("-" * 80)
    print(f"Total Equity Invested: Rs. {spent_equity:,.2f}")
    print(f"Cash Buffer:           Rs. {cash_remaining:,.2f}")
    print(f"Total Portfolio Value: Rs. {spent_equity + cash_remaining:,.2f}")
    print(f"Ledger saved to {out_file}")

if __name__ == "__main__":
    initialize_1lakh_ledger()
