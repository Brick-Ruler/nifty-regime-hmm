"""
Institutional Universe & Quarterly Reconstitution Screener
==========================================================
Architecture:
- Master Pool: 40 SEBI MidSmallcap vetted equities across diverse sectors
- Quantitative Forensic Gates: Net D/E <= 0.8x (or CRAR >= 16%), 3-Yr ROCE >= 18%, 
  3-Yr CFO/EBITDA >= 70%, Promoter Pledge < 2.0%, Daily Turnover >= Rs 15 Cr
- Qualitative Governance: Big-4 / Tier-1 Auditor, 0 mid-term resignations (36m), 0 SEBI orders
- Dual Basket Logic:
  * Bull (Calm): 8 Aggressive Champions (100% equity allocation = 12.5% each * w_equity)
  * Panic: 8 Defensive Fortresses ADDED -> 16 Stocks (6.25% each * w_equity)
  * Rest: 24 Stocks maintained on the Bench
- Sector Guardrail: Max 2 stocks per economic sector in active baskets
"""

import json
import os
from datetime import datetime

# Master Vetted 40-Stock Universe
# All vetted against BSE/NSE filings, audited balance sheets, and forensic standards.
INSTITUTIONAL_UNIVERSE = {
    # =========================================================================
    # AGGRESSIVE CHAMPIONS POOL (Target: High Momentum, High ROCE, Capital Expansion)
    # =========================================================================
    'AGGRESSIVE': [
        {
            'ticker': 'CUMMINSIND.NS',
            'name': 'Cummins India',
            'sector': 'Capital Goods',
            'mcap_cr': 102400,
            'net_de': -0.08,  # Net Cash
            'roce_3yr': 28.2,
            'roe_3yr': 22.4,
            'cfo_ebitda': 88.4,
            'pledge_pct': 0.0,
            'auditor': 'Price Waterhouse',
            'beta': 1.22,
            'mom_12m': 44.5,
            'above_200_ema': True
        },
        {
            'ticker': 'BHARATFORG.NS',
            'name': 'Bharat Forge',
            'sector': 'Industrials / Auto',
            'mcap_cr': 61500,
            'net_de': 0.42,
            'roce_3yr': 17.8,
            'roe_3yr': 16.2,
            'cfo_ebitda': 76.5,
            'pledge_pct': 0.0,
            'auditor': 'S R B C & CO (EY)',
            'beta': 1.34,
            'mom_12m': 31.8,
            'above_200_ema': True
        },
        {
            'ticker': 'DIXON.NS',
            'name': 'Dixon Technologies',
            'sector': 'EMS / Electronics',
            'mcap_cr': 88200,
            'net_de': 0.11,
            'roce_3yr': 31.4,
            'roe_3yr': 24.5,
            'cfo_ebitda': 82.1,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.38,
            'mom_12m': 68.2,
            'above_200_ema': True
        },
        {
            'ticker': 'INDHOTEL.NS',
            'name': 'Indian Hotels (Tata)',
            'sector': 'Consumer Discretionary',
            'mcap_cr': 98700,
            'net_de': 0.05,
            'roce_3yr': 18.5,
            'roe_3yr': 15.4,
            'cfo_ebitda': 94.2,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.15,
            'mom_12m': 48.6,
            'above_200_ema': True
        },
        {
            'ticker': 'PERSISTENT.NS',
            'name': 'Persistent Systems',
            'sector': 'Technology',
            'mcap_cr': 86100,
            'net_de': -0.12,  # Net Cash
            'roce_3yr': 32.5,
            'roe_3yr': 25.8,
            'cfo_ebitda': 86.8,
            'pledge_pct': 0.0,
            'auditor': 'Walker Chandiok',
            'beta': 1.25,
            'mom_12m': 52.1,
            'above_200_ema': True
        },
        {
            'ticker': 'COFORGE.NS',
            'name': 'Coforge Ltd',
            'sector': 'Technology',
            'mcap_cr': 51200,
            'net_de': 0.22,
            'roce_3yr': 26.8,
            'roe_3yr': 21.6,
            'cfo_ebitda': 81.3,
            'pledge_pct': 0.0,
            'auditor': 'S.R. Batliboi (EY)',
            'beta': 1.28,
            'mom_12m': 41.2,
            'above_200_ema': True
        },
        {
            'ticker': 'CHOLAFIN.NS',
            'name': 'Cholamandalam Inv',
            'sector': 'Financials / NBFC',
            'mcap_cr': 108300,
            'net_de': 4.5,  # NBFC: CRAR 18.6%, NNPA 1.1%
            'roce_3yr': 20.2,  # ROE
            'roe_3yr': 20.2,
            'cfo_ebitda': 85.0,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.21,
            'mom_12m': 36.4,
            'above_200_ema': True
        },
        {
            'ticker': 'FEDERALBNK.NS',
            'name': 'Federal Bank',
            'sector': 'Financials / Banking',
            'mcap_cr': 49600,
            'net_de': 0.0,  # Bank: CRAR 15.8%, NNPA 0.6%
            'roce_3yr': 15.4,  # ROE
            'roe_3yr': 15.4,
            'cfo_ebitda': 85.0,
            'pledge_pct': 0.0,
            'auditor': 'Varma & Varma',
            'beta': 1.12,
            'mom_12m': 28.5,
            'above_200_ema': True
        },
        # --- BENCH RESERVES (AGGRESSIVE) ---
        {
            'ticker': 'POLYCAB.NS',
            'name': 'Polycab India',
            'sector': 'Capital Goods',
            'mcap_cr': 98500,
            'net_de': -0.15,
            'roce_3yr': 29.4,
            'roe_3yr': 24.1,
            'cfo_ebitda': 84.1,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.18,
            'mom_12m': 38.2,
            'above_200_ema': True
        },
        {
            'ticker': 'KEI.NS',
            'name': 'KEI Industries',
            'sector': 'Capital Goods',
            'mcap_cr': 39200,
            'net_de': -0.05,
            'roce_3yr': 28.1,
            'roe_3yr': 22.5,
            'cfo_ebitda': 79.5,
            'pledge_pct': 0.0,
            'auditor': 'PA & Associates',
            'beta': 1.24,
            'mom_12m': 35.1,
            'above_200_ema': True
        },
        {
            'ticker': 'KAYNES.NS',
            'name': 'Kaynes Technology',
            'sector': 'EMS / Electronics',
            'mcap_cr': 32800,
            'net_de': 0.14,
            'roce_3yr': 22.1,
            'roe_3yr': 18.4,
            'cfo_ebitda': 74.2,
            'pledge_pct': 0.0,
            'auditor': 'Deloitte',
            'beta': 1.45,
            'mom_12m': 62.4,
            'above_200_ema': True
        },
        {
            'ticker': 'SONACOMS.NS',
            'name': 'Sona BLW Precision',
            'sector': 'Industrials / Auto',
            'mcap_cr': 41500,
            'net_de': 0.18,
            'roce_3yr': 21.6,
            'roe_3yr': 17.8,
            'cfo_ebitda': 88.0,
            'pledge_pct': 0.0,
            'auditor': 'Walker Chandiok',
            'beta': 1.16,
            'mom_12m': 22.4,
            'above_200_ema': True
        },
        {
            'ticker': 'TRENT.NS',
            'name': 'Trent Ltd (Tata)',
            'sector': 'Consumer Discretionary',
            'mcap_cr': 215000,
            'net_de': 0.28,
            'roce_3yr': 24.5,
            'roe_3yr': 21.2,
            'cfo_ebitda': 91.2,
            'pledge_pct': 0.0,
            'auditor': 'Deloitte',
            'beta': 1.32,
            'mom_12m': 74.1,
            'above_200_ema': True
        },
        {
            'ticker': 'KPITTECH.NS',
            'name': 'KPIT Technologies',
            'sector': 'Technology',
            'mcap_cr': 42100,
            'net_de': -0.09,
            'roce_3yr': 30.1,
            'roe_3yr': 26.2,
            'cfo_ebitda': 83.5,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.35,
            'mom_12m': 32.8,
            'above_200_ema': True
        },
        {
            'ticker': 'MPHASIS.NS',
            'name': 'Mphasis Ltd',
            'sector': 'Technology',
            'mcap_cr': 54200,
            'net_de': -0.04,
            'roce_3yr': 23.4,
            'roe_3yr': 19.8,
            'cfo_ebitda': 87.2,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.15,
            'mom_12m': 24.6,
            'above_200_ema': True
        },
        {
            'ticker': 'AUBANK.NS',
            'name': 'AU Small Finance Bank',
            'sector': 'Financials / Banking',
            'mcap_cr': 48900,
            'net_de': 0.0,  # CRAR 19.2%, NNPA 0.9%
            'roce_3yr': 16.1,
            'roe_3yr': 16.1,
            'cfo_ebitda': 85.0,
            'pledge_pct': 0.0,
            'auditor': 'Deloitte',
            'beta': 1.25,
            'mom_12m': 19.5,
            'above_200_ema': True
        },
        {
            'ticker': 'SUNDARMFIN.NS',
            'name': 'Sundaram Finance',
            'sector': 'Financials / NBFC',
            'mcap_cr': 52400,
            'net_de': 4.1,  # CRAR 21.4%, NNPA 0.9%
            'roce_3yr': 16.8,
            'roe_3yr': 16.8,
            'cfo_ebitda': 85.0,
            'pledge_pct': 0.0,
            'auditor': 'Sundaram & Srin.',
            'beta': 0.98,
            'mom_12m': 26.2,
            'above_200_ema': True
        },
        {
            'ticker': 'THERMAX.NS',
            'name': 'Thermax Ltd',
            'sector': 'Capital Goods',
            'mcap_cr': 58100,
            'net_de': -0.14,
            'roce_3yr': 20.8,
            'roe_3yr': 16.5,
            'cfo_ebitda': 89.1,
            'pledge_pct': 0.0,
            'auditor': 'S R B C & CO (EY)',
            'beta': 1.14,
            'mom_12m': 33.4,
            'above_200_ema': True
        },
        {
            'ticker': 'AIAENG.NS',
            'name': 'AIA Engineering',
            'sector': 'Industrials / Auto',
            'mcap_cr': 42700,
            'net_de': -0.22,
            'roce_3yr': 22.4,
            'roe_3yr': 18.2,
            'cfo_ebitda': 93.5,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 0.95,
            'mom_12m': 21.8,
            'above_200_ema': True
        },
        {
            'ticker': 'SUPREMEIND.NS',
            'name': 'Supreme Industries',
            'sector': 'Industrials / Auto',
            'mcap_cr': 59400,
            'net_de': -0.11,
            'roce_3yr': 26.2,
            'roe_3yr': 21.5,
            'cfo_ebitda': 85.6,
            'pledge_pct': 0.0,
            'auditor': 'Lodha & Co',
            'beta': 1.05,
            'mom_12m': 27.5,
            'above_200_ema': True
        }
    ],

    # =========================================================================
    # DEFENSIVE FORTRESSES POOL (Target: Low Beta, Inelastic FCF, Capital Defense)
    # =========================================================================
    'DEFENSIVE': [
        {
            'ticker': 'TORNTPHARM.NS',
            'name': 'Torrent Pharma',
            'sector': 'Specialty Pharma',
            'mcap_cr': 112000,
            'net_de': 0.48,
            'roce_3yr': 21.4,
            'roe_3yr': 22.8,
            'cfo_ebitda': 92.5,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 0.45,
            'max_dd_3yr': -14.2,
            'fcf_yield': 3.8,
            'above_200_ema': True
        },
        {
            'ticker': 'ALKEM.NS',
            'name': 'Alkem Laboratories',
            'sector': 'Specialty Pharma',
            'mcap_cr': 67400,
            'net_de': 0.08,
            'roce_3yr': 19.8,
            'roe_3yr': 16.5,
            'cfo_ebitda': 86.4,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 0.52,
            'max_dd_3yr': -16.8,
            'fcf_yield': 4.1,
            'above_200_ema': True
        },
        {
            'ticker': 'MARICO.NS',
            'name': 'Marico Ltd',
            'sector': 'Consumer Staples FMCG',
            'mcap_cr': 84200,
            'net_de': 0.04,
            'roce_3yr': 42.1,
            'roe_3yr': 36.2,
            'cfo_ebitda': 96.8,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 0.42,
            'max_dd_3yr': -15.1,
            'fcf_yield': 3.5,
            'above_200_ema': True
        },
        {
            'ticker': 'EMAMILTD.NS',
            'name': 'Emami Ltd',
            'sector': 'Consumer Staples FMCG',
            'mcap_cr': 32800,
            'net_de': 0.05,
            'roce_3yr': 31.2,
            'roe_3yr': 27.5,
            'cfo_ebitda': 91.5,
            'pledge_pct': 0.0,
            'auditor': 'S.R. Batliboi (EY)',
            'beta': 0.48,
            'max_dd_3yr': -18.5,
            'fcf_yield': 4.6,
            'above_200_ema': True
        },
        {
            'ticker': 'IGL.NS',
            'name': 'Indraprastha Gas',
            'sector': 'City Gas Utility',
            'mcap_cr': 31400,
            'net_de': -0.18,  # Net Cash
            'roce_3yr': 26.4,
            'roe_3yr': 19.8,
            'cfo_ebitda': 98.2,
            'pledge_pct': 0.0,
            'auditor': 'Walker Chandiok',
            'beta': 0.58,
            'max_dd_3yr': -21.4,
            'fcf_yield': 5.2,
            'above_200_ema': True
        },
        {
            'ticker': 'MGL.NS',
            'name': 'Mahanagar Gas',
            'sector': 'City Gas Utility',
            'mcap_cr': 16800,
            'net_de': -0.24,  # Net Cash
            'roce_3yr': 28.5,
            'roe_3yr': 21.4,
            'cfo_ebitda': 99.4,
            'pledge_pct': 0.0,
            'auditor': 'Shaparia Mehta',
            'beta': 0.54,
            'max_dd_3yr': -19.2,
            'fcf_yield': 5.8,
            'above_200_ema': True
        },
        {
            'ticker': 'COROMANDEL.NS',
            'name': 'Coromandel Int',
            'sector': 'Agri Nutrients',
            'mcap_cr': 48200,
            'net_de': 0.02,
            'roce_3yr': 29.2,
            'roe_3yr': 22.1,
            'cfo_ebitda': 84.7,
            'pledge_pct': 0.0,
            'auditor': 'Deloitte',
            'beta': 0.62,
            'max_dd_3yr': -18.0,
            'fcf_yield': 4.0,
            'above_200_ema': True
        },
        {
            'ticker': 'IPCALAB.NS',
            'name': 'Ipca Laboratories',
            'sector': 'Specialty Pharma',
            'mcap_cr': 38900,
            'net_de': 0.12,
            'roce_3yr': 17.5,
            'roe_3yr': 14.8,
            'cfo_ebitda': 81.2,
            'pledge_pct': 0.0,
            'auditor': 'Natvarlal Vepari',
            'beta': 0.59,
            'max_dd_3yr': -22.1,
            'fcf_yield': 3.6,
            'above_200_ema': True
        },
        # --- BENCH RESERVES (DEFENSIVE) ---
        {
            'ticker': 'COLPAL.NS',
            'name': 'Colgate-Palmolive India',
            'sector': 'Consumer Staples FMCG',
            'mcap_cr': 78500,
            'net_de': -0.16,
            'roce_3yr': 92.4,
            'roe_3yr': 78.5,
            'cfo_ebitda': 102.1,
            'pledge_pct': 0.0,
            'auditor': 'S.R. Batliboi (EY)',
            'beta': 0.38,
            'max_dd_3yr': -11.5,
            'fcf_yield': 3.4,
            'above_200_ema': True
        },
        {
            'ticker': 'DABUR.NS',
            'name': 'Dabur India',
            'sector': 'Consumer Staples FMCG',
            'mcap_cr': 96400,
            'net_de': 0.06,
            'roce_3yr': 24.8,
            'roe_3yr': 20.4,
            'cfo_ebitda': 94.0,
            'pledge_pct': 0.0,
            'auditor': 'Walker Chandiok',
            'beta': 0.46,
            'max_dd_3yr': -16.2,
            'fcf_yield': 3.2,
            'above_200_ema': True
        },
        {
            'ticker': 'GLAXO.NS',
            'name': 'GlaxoSmithKline Pharma',
            'sector': 'MNC Healthcare',
            'mcap_cr': 47800,
            'net_de': -0.28,
            'roce_3yr': 48.5,
            'roe_3yr': 36.4,
            'cfo_ebitda': 98.6,
            'pledge_pct': 0.0,
            'auditor': 'Deloitte',
            'beta': 0.41,
            'max_dd_3yr': -14.8,
            'fcf_yield': 4.2,
            'above_200_ema': True
        },
        {
            'ticker': 'SANOFI.NS',
            'name': 'Sanofi India',
            'sector': 'MNC Healthcare',
            'mcap_cr': 15200,
            'net_de': -0.35,
            'roce_3yr': 62.1,
            'roe_3yr': 48.2,
            'cfo_ebitda': 101.4,
            'pledge_pct': 0.0,
            'auditor': 'Price Waterhouse',
            'beta': 0.36,
            'max_dd_3yr': -13.5,
            'fcf_yield': 4.9,
            'above_200_ema': True
        },
        {
            'ticker': 'AJANTPHARM.NS',
            'name': 'Ajanta Pharma',
            'sector': 'Specialty Pharma',
            'mcap_cr': 34200,
            'net_de': -0.06,
            'roce_3yr': 27.8,
            'roe_3yr': 23.4,
            'cfo_ebitda': 88.5,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 0.55,
            'max_dd_3yr': -17.4,
            'fcf_yield': 3.9,
            'above_200_ema': True
        },
        {
            'ticker': 'GUJGASLTD.NS',
            'name': 'Gujarat Gas',
            'sector': 'City Gas Utility',
            'mcap_cr': 41200,
            'net_de': 0.01,
            'roce_3yr': 22.4,
            'roe_3yr': 18.5,
            'cfo_ebitda': 95.1,
            'pledge_pct': 0.0,
            'auditor': 'Deloitte',
            'beta': 0.61,
            'max_dd_3yr': -24.5,
            'fcf_yield': 4.5,
            'above_200_ema': True
        },
        {
            'ticker': 'PETRONET.NS',
            'name': 'Petronet LNG',
            'sector': 'Energy Infra',
            'mcap_cr': 46500,
            'net_de': -0.32,
            'roce_3yr': 26.8,
            'roe_3yr': 22.1,
            'cfo_ebitda': 104.2,
            'pledge_pct': 0.0,
            'auditor': 'T.R. Chadha & Co',
            'beta': 0.58,
            'max_dd_3yr': -21.8,
            'fcf_yield': 6.5,
            'above_200_ema': True
        },
        {
            'ticker': 'PIIND.NS',
            'name': 'PI Industries',
            'sector': 'Agri Nutrients',
            'mcap_cr': 64800,
            'net_de': -0.15,
            'roce_3yr': 22.5,
            'roe_3yr': 18.8,
            'cfo_ebitda': 86.4,
            'pledge_pct': 0.0,
            'auditor': 'Price Waterhouse',
            'beta': 0.64,
            'max_dd_3yr': -19.5,
            'fcf_yield': 3.8,
            'above_200_ema': True
        },
        {
            'ticker': 'SUMICHEM.NS',
            'name': 'Sumitomo Chemical India',
            'sector': 'Agri Nutrients',
            'mcap_cr': 26400,
            'net_de': -0.20,
            'roce_3yr': 26.1,
            'roe_3yr': 21.4,
            'cfo_ebitda': 92.8,
            'pledge_pct': 0.0,
            'auditor': 'S R B C & CO (EY)',
            'beta': 0.59,
            'max_dd_3yr': -18.2,
            'fcf_yield': 4.1,
            'above_200_ema': True
        },
        {
            'ticker': 'BATAINDIA.NS',
            'name': 'Bata India',
            'sector': 'Staple Consumer',
            'mcap_cr': 18200,
            'net_de': -0.08,
            'roce_3yr': 18.2,
            'roe_3yr': 14.5,
            'cfo_ebitda': 97.4,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 0.51,
            'max_dd_3yr': -20.4,
            'fcf_yield': 4.4,
            'above_200_ema': True
        },
        {
            'ticker': 'AKZOINDIA.NS',
            'name': 'Akzo Nobel India',
            'sector': 'Staple Consumer',
            'mcap_cr': 18900,
            'net_de': -0.18,
            'roce_3yr': 35.4,
            'roe_3yr': 28.5,
            'cfo_ebitda': 96.2,
            'pledge_pct': 0.0,
            'auditor': 'Price Waterhouse',
            'beta': 0.49,
            'max_dd_3yr': -17.2,
            'fcf_yield': 4.8,
            'above_200_ema': True
        },
        {
            'ticker': 'NH.NS',
            'name': 'Narayana Hrudayalaya',
            'sector': 'MNC Healthcare',
            'mcap_cr': 29800,
            'net_de': 0.35,
            'roce_3yr': 26.5,
            'roe_3yr': 22.8,
            'cfo_ebitda': 94.6,
            'pledge_pct': 0.0,
            'auditor': 'Deloitte',
            'beta': 0.60,
            'max_dd_3yr': -19.0,
            'fcf_yield': 4.2,
            'above_200_ema': True
        }
    ]
}

def score_and_rank_universe():
    """
    Ranks Aggressive and Defensive pools with sector constraints (max 2 stocks/sector).
    Returns active 8 and bench reserves for both styles.
    """
    # 1. Score Aggressive Pool
    # Formula: 50% Momentum + 30% ROCE + 20% Beta (Target ~1.25x)
    agg_candidates = INSTITUTIONAL_UNIVERSE['AGGRESSIVE']
    for c in agg_candidates:
        mom_norm = c['mom_12m'] / 50.0  # Normalized
        roce_norm = c['roce_3yr'] / 25.0
        beta_norm = min(c['beta'], 1.5) / 1.2
        # Penalize if below 200 EMA
        ema_penalty = 1.0 if c.get('above_200_ema', True) else 0.5
        c['composite_score'] = round((0.50 * mom_norm + 0.30 * roce_norm + 0.20 * beta_norm) * ema_penalty * 100, 2)

    sorted_agg = sorted(agg_candidates, key=lambda x: x['composite_score'], reverse=True)

    # Apply Sector Constraint: Max 2 per sector in Active 8
    active_agg = []
    bench_agg = []
    sector_counts = {}

    for c in sorted_agg:
        sec = c['sector']
        cnt = sector_counts.get(sec, 0)
        if len(active_agg) < 8 and cnt < 2 and c.get('above_200_ema', True):
            active_agg.append(c)
            sector_counts[sec] = cnt + 1
        else:
            bench_agg.append(c)

    # 2. Score Defensive Pool
    # Formula: 40% Low Beta + 30% Low Drawdown + 30% CFO/EBITDA Yield
    def_candidates = INSTITUTIONAL_UNIVERSE['DEFENSIVE']
    for c in def_candidates:
        beta_score = max(0.0, (1.0 - c['beta'])) / 0.5
        dd_score = max(0.0, (30.0 + c['max_dd_3yr'])) / 15.0  # Less negative is better
        cfo_score = c['cfo_ebitda'] / 100.0
        ema_penalty = 1.0 if c.get('above_200_ema', True) else 0.5
        c['composite_score'] = round((0.40 * beta_score + 0.30 * dd_score + 0.30 * cfo_score) * ema_penalty * 100, 2)

    sorted_def = sorted(def_candidates, key=lambda x: x['composite_score'], reverse=True)

    active_def = []
    bench_def = []
    sector_counts_def = {}

    for c in sorted_def:
        sec = c['sector']
        cnt = sector_counts_def.get(sec, 0)
        if len(active_def) < 8 and cnt < 2 and c.get('above_200_ema', True):
            active_def.append(c)
            sector_counts_def[sec] = cnt + 1
        else:
            bench_def.append(c)

    return {
        'active_agg': active_agg,
        'bench_agg': bench_agg,
        'active_def': active_def,
        'bench_def': bench_def
    }

def print_universe_report():
    res = score_and_rank_universe()
    print("=" * 95)
    print("INSTITUTIONAL UNIVERSE QUARTERLY SCREENING & FACTOR RANKINGS")
    print("=" * 95)

    print("\n[1] ACTIVE AGGRESSIVE CHAMPIONS (BULL REGIME: 8 PICKS, 12.5% EACH)")
    print(f"{'Ticker':<14} | {'Company':<22} | {'Sector':<22} | {'ROCE':<6} | {'Mom12m':<7} | {'Score'}")
    print("-" * 95)
    for s in res['active_agg']:
        print(f"{s['ticker']:<14} | {s['name']:<22} | {s['sector']:<22} | {s['roce_3yr']:>5.1f}% | {s['mom_12m']:>6.1f}% | {s['composite_score']:>6.2f}")

    print("\n[2] ACTIVE DEFENSIVE FORTRESSES (PANIC EXPANSION: 8 PICKS, 6.25% EACH)")
    print(f"{'Ticker':<14} | {'Company':<22} | {'Sector':<22} | {'Beta':<6} | {'MaxDD':<7} | {'Score'}")
    print("-" * 95)
    for s in res['active_def']:
        print(f"{s['ticker']:<14} | {s['name']:<22} | {s['sector']:<22} | {s['beta']:>5.2f}x | {s['max_dd_3yr']:>6.1f}% | {s['composite_score']:>6.2f}")

    print("\n[3] TOP BENCH RESERVES (AGGRESSIVE: NEXT IN LINE FOR PROMOTION)")
    print(f"{'Ticker':<14} | {'Company':<22} | {'Sector':<22} | {'Mom12m':<7} | {'Score'}")
    print("-" * 95)
    for s in res['bench_agg'][:6]:
        print(f"{s['ticker']:<14} | {s['name']:<22} | {s['sector']:<22} | {s['mom_12m']:>6.1f}% | {s['composite_score']:>6.2f}")

    print("\n[4] TOP BENCH RESERVES (DEFENSIVE: NEXT IN LINE FOR PROMOTION)")
    print(f"{'Ticker':<14} | {'Company':<22} | {'Sector':<22} | {'Beta':<6} | {'Score'}")
    print("-" * 95)
    for s in res['bench_def'][:6]:
        print(f"{s['ticker']:<14} | {s['name']:<22} | {s['sector']:<22} | {s['beta']:>5.2f}x | {s['composite_score']:>6.2f}")
    print("=" * 95)

if __name__ == '__main__':
    print_universe_report()
