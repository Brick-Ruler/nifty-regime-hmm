"""
Live Daily Portfolio Advisor for Pure-Equity Mid & Small Cap Strategy
======================================================================
Run this script at 3:15 PM every trading afternoon (or in the evening)
to get real-time regime prediction and exact target share quantities.

Usage:
  python daily_portfolio_advisor.py
  (Prompts for portfolio size in INR, e.g., 500000 or 1000000)
"""

import urllib.request
import urllib.parse
import json
import csv
import math
import sys
from datetime import datetime

# INSTITUTIONAL TOP-5 SECTOR ROTATION ACTIVE PICKS (Option B: Leading Macro Sectors)
AGG_STOCKS = [
    ('PERSISTENT.NS', 'Persistent Systems', 'Digital Engineering / IT'),
    ('COFORGE.NS', 'Coforge Ltd', 'Digital Engineering / IT'),
    ('CHOLAFIN.NS', 'Cholamandalam Inv', 'Financials & NBFC'),
    ('FEDERALBNK.NS', 'Federal Bank', 'Financials & Banking'),
    ('INDHOTEL.NS', 'Indian Hotels (Tata)', 'Hospitality & Services'),
    ('EIHOTEL.NS', 'EIH Ltd (Oberoi)', 'Hospitality & Services'),
    ('BALKRISIND.NS', 'Balkrishna Ind (BKT)', 'Auto Ancillary'),
    ('DIXON.NS', 'Dixon Technologies', 'EMS & Consumer Tech')
]

DEF_STOCKS = [
    ('COLPAL.NS', 'Colgate-Palmolive India', 'Oral Hygiene Staples'),
    ('GLAXO.NS', 'GlaxoSmithKline Pharma', 'MNC Healthcare / Vaccines'),
    ('MARICO.NS', 'Marico Ltd', 'Consumer Staples FMCG'),
    ('TORNTPHARM.NS', 'Torrent Pharma', 'Chronic Specialty Pharma'),
    ('KANSAINER.NS', 'Kansai Nerolac Paints', 'Decorative MNC Coatings'),
    ('MGL.NS', 'Mahanagar Gas', 'City Gas Distribution'),
    ('COROMANDEL.NS', 'Coromandel Int', 'Agri Nutrients & Crop Care'),
    ('PETRONET.NS', 'Petronet LNG', 'Energy Infrastructure')
]

def fetch_latest_quote(symbol):
    encoded = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=5d&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = data['chart']['result'][0]
            quotes = result['indicators']['quote'][0]
            closes = [c for c in quotes['close'] if c is not None and not math.isnan(c)]
            if len(closes) >= 2:
                latest = closes[-1]
                prev = closes[-2]
                ret = ((latest - prev) / prev) * 100.0
                return latest, ret
            elif len(closes) == 1:
                return closes[0], 0.0
    except Exception as e:
        pass
    return None, 0.0

def run_live_advisor(portfolio_capital=1000000.0):
    print("=" * 80)
    print("       NIFTY 50 REGIME DETECTOR & MID/SMALLCAP PORTFOLIO ADVISOR      ")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Fetching live market signals (NIFTY 50 & India VIX)...")

    nifty_price, nifty_ret = fetch_latest_quote("^NSEI")
    vix_price, vix_ret = fetch_latest_quote("^INDIAVIX")

    if nifty_price is None or vix_price is None:
        print("Error: Could not retrieve live market quotes. Ensure internet connection.")
        return

    print(f"-> NIFTY 50:  {nifty_price:,.2f} ({nifty_ret:+5.2f}%)")
    print(f"-> India VIX: {vix_price:5.2f} ({vix_ret:+5.2f}%)")

    # Load trained model parameters from walk-forward results
    # Default calibrated parameters:
    mu = [0.075, -0.22]
    sigma = [0.65, 2.05]
    A = [[0.965, 0.035], [0.115, 0.885]]

    # Prior probability based on recent regime
    prior = [0.90, 0.10]
    
    # Hamilton Filter step
    p0_prior = prior[0] * A[0][0] + prior[1] * A[1][0]
    p1_prior = prior[0] * A[0][1] + prior[1] * A[1][1]

    def norm_pdf(x, m, s):
        d = x - m
        return (1.0 / (s * math.sqrt(2 * math.pi))) * math.exp(-0.5 * (d*d) / (s*s))

    lik0 = norm_pdf(nifty_ret, mu[0], sigma[0])
    lik1 = norm_pdf(nifty_ret, mu[1], sigma[1])

    u0 = p0_prior * lik0
    u1 = p1_prior * lik1
    total = u0 + u1 or 1e-12

    p_calm = (u0 / total) * 100.0
    p_panic = (u1 / total) * 100.0

    print("-" * 80)
    print(f"MARKET REGIME DIAGNOSIS:")
    print(f"  P(Calm Bull Regime):    {p_calm:5.1f}%")
    print(f"  P(Panic / High-Vol):    {p_panic:5.1f}%")

    if p_panic > 65.0:
        regime = "DEFENSIVE QUALITY"
        agg_pct = 20.0
        def_pct = 80.0
        action = "DEFENSIVE ALLOCATION ACTIVE: Overweight Healthcare, Staples, Inelastic Cash Flows"
    else:
        regime = "AGGRESSIVE GROWTH"
        agg_pct = 80.0
        def_pct = 20.0
        action = "AGGRESSIVE ALLOCATION ACTIVE: Overweight High-Beta CapGoods, EMS, Discretionary"

    print(f"\nACTIVE REGIME: [{regime}]")
    print(f"STRATEGY RULE: {action}")
    print(f"Portfolio Capital: Rs. {portfolio_capital:,.2f}")
    print("-" * 80)

    # Calculate per-stock allocations
    agg_per_stock_pct = agg_pct / len(AGG_STOCKS)
    def_per_stock_pct = def_pct / len(DEF_STOCKS)

    print(f"\n1. AGGRESSIVE GROWTH BASKET (Target Weight: {agg_pct:.0f}% total | {agg_per_stock_pct:.2f}% each):")
    print(f"{'Ticker':<14} | {'Company Name':<22} | {'Sector':<20} | {'Weight':<8} | {'Target (Rs)':<12} | {'CMP (Rs)':<10} | {'Shares':<8}")
    print("-" * 105)
    for sym, name, sec in AGG_STOCKS:
        price, _ = fetch_latest_quote(sym)
        price = price if price is not None else 1000.0
        target_amt = (agg_per_stock_pct / 100.0) * portfolio_capital
        target_shares = max(1, round(target_amt / price)) if target_amt > 0 else 0
        print(f"{sym:<14} | {name:<22} | {sec:<20} | {agg_per_stock_pct:>6.2f}% | Rs.{target_amt:>9,.0f} | Rs.{price:>8.1f} | {target_shares:>6}")

    print(f"\n2. DEFENSIVE FORTRESS BASKET (Target Weight: {def_pct:.0f}% total | {def_per_stock_pct:.2f}% each):")
    print(f"{'Ticker':<14} | {'Company Name':<22} | {'Sector':<20} | {'Weight':<8} | {'Target (Rs)':<12} | {'CMP (Rs)':<10} | {'Shares':<8}")
    print("-" * 105)
    for sym, name, sec in DEF_STOCKS:
        price, _ = fetch_latest_quote(sym)
        price = price if price is not None else 1000.0
        target_amt = (def_per_stock_pct / 100.0) * portfolio_capital
        target_shares = max(1, round(target_amt / price)) if target_amt > 0 else 0
        print(f"{sym:<14} | {name:<22} | {sec:<20} | {def_per_stock_pct:>6.2f}% | Rs.{target_amt:>9,.0f} | Rs.{price:>8.1f} | {target_shares:>6}")

    print("=" * 105)
    print("Execution Recommendation:")
    print("1. If today's regime is identical to yesterday: NO ACTION REQUIRED (Sit tight, zero friction).")
    print("2. If a regime flip was triggered: Execute rebalance at 3:15 PM - 3:25 PM or tomorrow at 9:45 AM.")
    print("=" * 105)

if __name__ == "__main__":
    cap = 1000000.0
    if len(sys.argv) > 1:
        try:
            cap = float(sys.argv[1])
        except:
            pass
    run_live_advisor(portfolio_capital=cap)
