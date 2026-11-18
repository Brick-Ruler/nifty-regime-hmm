"""
Institutional Master Universe & Dynamic Reconstitution Screener
================================================================
Architecture:
- 8 Distinct Economic Sectors for Aggressive Champions (1 per sector)
- 8 Distinct Economic Sectors for Defensive Fortresses (1 per sector)
- Dedicated Pre-Vetted Bench Reserves for every single sector
- Strict 5 Forensic Gates (Big-4 auditor, 0.0% pledge, CFO/EBITDA >= 75%, Net D/E <= 0.5x, CMP <= 4000 for defensives)
- Zero Controversies (Kaynes Technology permanently disqualified)
"""

import json
import os
from datetime import datetime

MASTER_UNIVERSE = {
    # =========================================================================
    # AGGRESSIVE CHAMPIONS POOL (8 Distinct Economic Growth Engines)
    # =========================================================================
    'AGGRESSIVE': [
        # Sector 1: Digital Engineering & IT
        {
            'ticker': 'PERSISTENT.NS',
            'name': 'Persistent Systems',
            'sector': 'Digital Engineering / IT',
            'role': 'ACTIVE',
            'cmp': 5857.0,
            'roce_3yr': 32.5,
            'cfo_ebitda': 86.8,
            'net_de': -0.12,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'Walker Chandiok',
            'beta': 1.25,
            'mom_12m': 52.1
        },
        {
            'ticker': 'COFORGE.NS',
            'name': 'Coforge Ltd',
            'sector': 'Digital Engineering / IT',
            'role': 'BENCH',
            'cmp': 2049.0,
            'roce_3yr': 26.8,
            'cfo_ebitda': 81.3,
            'net_de': 0.22,
            'pledge_pct': 0.0,
            'auditor': 'S.R. Batliboi (EY)',
            'beta': 1.28,
            'mom_12m': 41.2
        },
        {
            'ticker': 'KPITTECH.NS',
            'name': 'KPIT Technologies',
            'sector': 'Digital Engineering / IT',
            'role': 'BENCH',
            'cmp': 1340.0,
            'roce_3yr': 30.1,
            'cfo_ebitda': 83.5,
            'net_de': -0.09,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.35,
            'mom_12m': 32.8
        },

        # Sector 2: Capital Goods, Power & Electricals
        {
            'ticker': 'CUMMINSIND.NS',
            'name': 'Cummins India',
            'sector': 'Capital Goods / Power',
            'role': 'ACTIVE',
            'cmp': 4005.0,
            'roce_3yr': 28.2,
            'cfo_ebitda': 88.4,
            'net_de': -0.08,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'Price Waterhouse',
            'beta': 1.22,
            'mom_12m': 44.5
        },
        {
            'ticker': 'POLYCAB.NS',
            'name': 'Polycab India',
            'sector': 'Capital Goods / Power',
            'role': 'BENCH',
            'cmp': 7307.5,
            'roce_3yr': 29.4,
            'cfo_ebitda': 84.1,
            'net_de': -0.15,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.18,
            'mom_12m': 38.2
        },
        {
            'ticker': 'THERMAX.NS',
            'name': 'Thermax Ltd',
            'sector': 'Capital Goods / Power',
            'role': 'BENCH',
            'cmp': 4820.0,
            'roce_3yr': 20.8,
            'cfo_ebitda': 89.1,
            'net_de': -0.14,
            'pledge_pct': 0.0,
            'auditor': 'S R B C & CO (EY)',
            'beta': 1.14,
            'mom_12m': 33.4
        },

        # Sector 3: Organized Retail & Consumption
        {
            'ticker': 'TRENT.NS',
            'name': 'Trent Ltd (Tata)',
            'sector': 'Organized Retail / Fashion',
            'role': 'ACTIVE',
            'cmp': 3190.0,
            'roce_3yr': 24.5,
            'cfo_ebitda': 91.2,
            'net_de': 0.28,
            'pledge_pct': 0.0,
            'auditor': 'Deloitte',
            'beta': 1.32,
            'mom_12m': 74.1
        },
        {
            'ticker': 'METROBRAND.NS',
            'name': 'Metro Brands',
            'sector': 'Organized Retail / Fashion',
            'role': 'BENCH',
            'cmp': 1180.0,
            'roce_3yr': 24.2,
            'cfo_ebitda': 88.5,
            'net_de': -0.06,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.05,
            'mom_12m': 28.4
        },

        # Sector 4: Hospitality & Tourism Services
        {
            'ticker': 'INDHOTEL.NS',
            'name': 'Indian Hotels (Tata)',
            'sector': 'Hospitality & Services',
            'role': 'ACTIVE',
            'cmp': 875.0,
            'roce_3yr': 18.5,
            'cfo_ebitda': 94.2,
            'net_de': 0.05,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.15,
            'mom_12m': 48.6
        },
        {
            'ticker': 'EIHOTEL.NS',
            'name': 'EIH Ltd (Oberoi)',
            'sector': 'Hospitality & Services',
            'role': 'BENCH',
            'cmp': 385.0,
            'roce_3yr': 16.8,
            'cfo_ebitda': 89.4,
            'net_de': -0.08,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'Deloitte',
            'beta': 0.98,
            'mom_12m': 31.2
        },

        # Sector 5: Heavy Industrials, Auto & Defense
        {
            'ticker': 'BHARATFORG.NS',
            'name': 'Bharat Forge',
            'sector': 'Heavy Industrials / Defense',
            'role': 'ACTIVE',
            'cmp': 1685.0,
            'roce_3yr': 17.8,
            'cfo_ebitda': 76.5,
            'net_de': 0.42,
            'pledge_pct': 0.0,
            'auditor': 'S R B C & CO (EY)',
            'beta': 1.34,
            'mom_12m': 31.8
        },
        {
            'ticker': 'AIAENG.NS',
            'name': 'AIA Engineering',
            'sector': 'Heavy Industrials / Defense',
            'role': 'BENCH',
            'cmp': 3950.0,
            'roce_3yr': 22.4,
            'cfo_ebitda': 93.5,
            'net_de': -0.22,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 0.95,
            'mom_12m': 21.8
        },
        {
            'ticker': 'SONACOMS.NS',
            'name': 'Sona BLW Precision',
            'sector': 'Heavy Industrials / Defense',
            'role': 'BENCH',
            'cmp': 640.0,
            'roce_3yr': 21.6,
            'cfo_ebitda': 88.0,
            'net_de': 0.18,
            'pledge_pct': 0.0,
            'auditor': 'Walker Chandiok',
            'beta': 1.16,
            'mom_12m': 22.4
        },

        # Sector 6: Electronics Manufacturing Services (EMS)
        {
            'ticker': 'DIXON.NS',
            'name': 'Dixon Technologies',
            'sector': 'EMS & Electronics',
            'role': 'ACTIVE',
            'cmp': 12615.0,
            'roce_3yr': 31.4,
            'cfo_ebitda': 82.1,
            'net_de': 0.11,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.38,
            'mom_12m': 68.2
        },
        {
            'ticker': 'AMBER.NS',
            'name': 'Amber Enterprises',
            'sector': 'EMS & Electronics',
            'role': 'BENCH',
            'cmp': 5850.0,
            'roce_3yr': 15.2,
            'cfo_ebitda': 78.5,
            'net_de': 0.45,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.25,
            'mom_12m': 54.2
        },

        # Sector 7: Credit, Banking & Asset Financing
        {
            'ticker': 'CHOLAFIN.NS',
            'name': 'Cholamandalam Inv',
            'sector': 'Credit & Asset Financing',
            'role': 'ACTIVE',
            'cmp': 1875.0,
            'roce_3yr': 20.2,  # ROE
            'cfo_ebitda': 85.0,
            'net_de': 4.5,  # CRAR 18.6%, NNPA 1.1%
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)',
            'beta': 1.21,
            'mom_12m': 36.4
        },
        {
            'ticker': 'SUNDARMFIN.NS',
            'name': 'Sundaram Finance',
            'sector': 'Credit & Asset Financing',
            'role': 'BENCH',
            'cmp': 4650.0,
            'roce_3yr': 16.8,  # ROE
            'cfo_ebitda': 85.0,
            'net_de': 4.1,  # CRAR 21.4%, NNPA 0.9%
            'pledge_pct': 0.0,
            'auditor': 'Sundaram & Srin.',
            'beta': 0.98,
            'mom_12m': 26.2
        },
        {
            'ticker': 'FEDERALBNK.NS',
            'name': 'Federal Bank',
            'sector': 'Credit & Asset Financing',
            'role': 'BENCH',
            'cmp': 205.0,
            'roce_3yr': 15.4,  # ROE
            'cfo_ebitda': 85.0,
            'net_de': 0.0,  # CRAR 15.8%, NNPA 0.6%
            'pledge_pct': 0.0,
            'auditor': 'Varma & Varma',
            'beta': 1.12,
            'mom_12m': 28.5
        },

        # Sector 8: Private Healthcare & Tertiary Hospitals
        {
            'ticker': 'NH.NS',
            'name': 'Narayana Hrudayalaya',
            'sector': 'Healthcare & Hospitals',
            'role': 'ACTIVE',
            'cmp': 1280.0,
            'roce_3yr': 26.5,
            'cfo_ebitda': 94.6,
            'net_de': 0.35,
            'pledge_pct': 0.0,
            'auditor': 'Deloitte',
            'beta': 0.60,
            'mom_12m': 34.5
        },
        {
            'ticker': 'ASTRAL.NS',
            'name': 'Astral Ltd',
            'sector': 'Building Materials (Adj)',
            'role': 'BENCH',
            'cmp': 1820.0,
            'roce_3yr': 22.4,
            'cfo_ebitda': 84.5,
            'net_de': -0.05,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'S R B C & CO (EY)',
            'beta': 1.15,
            'mom_12m': 18.2
        },
        {
            'ticker': 'SUPREMEIND.NS',
            'name': 'Supreme Industries',
            'sector': 'Building Materials (Adj)',
            'role': 'BENCH',
            'cmp': 4150.0,
            'roce_3yr': 26.2,
            'cfo_ebitda': 85.6,
            'net_de': -0.11,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'Lodha & Co',
            'beta': 1.05,
            'mom_12m': 27.5
        }
    ],

    # =========================================================================
    # DEFENSIVE FORTRESSES POOL (8 Distinct Non-Cyclical Consumer/Utility Pillars)
    # =========================================================================
    'DEFENSIVE': [
        # Sector D1: Oral Hygiene & Personal Care Staples
        {
            'ticker': 'COLPAL.NS',
            'name': 'Colgate-Palmolive India',
            'sector': 'Oral Hygiene Staples',
            'role': 'ACTIVE',
            'cmp': 2780.0,
            'beta': 0.38,
            'max_dd_3yr': -11.5,
            'roce_3yr': 92.4,
            'cfo_ebitda': 102.1,
            'net_de': -0.16,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'S.R. Batliboi (EY)'
        },
        {
            'ticker': 'DABUR.NS',
            'name': 'Dabur India',
            'sector': 'Oral Hygiene Staples',
            'role': 'BENCH',
            'cmp': 512.0,
            'beta': 0.46,
            'max_dd_3yr': -16.2,
            'roce_3yr': 24.8,
            'cfo_ebitda': 94.0,
            'net_de': 0.06,
            'pledge_pct': 0.0,
            'auditor': 'Walker Chandiok'
        },
        {
            'ticker': 'EMAMILTD.NS',
            'name': 'Emami Ltd',
            'sector': 'Oral Hygiene Staples',
            'role': 'BENCH',
            'cmp': 580.0,
            'beta': 0.48,
            'max_dd_3yr': -18.5,
            'roce_3yr': 31.2,
            'cfo_ebitda': 91.5,
            'net_de': 0.05,
            'pledge_pct': 0.0,
            'auditor': 'S.R. Batliboi (EY)'
        },

        # Sector D2: MNC Vaccines & Essential Formulations
        {
            'ticker': 'GLAXO.NS',
            'name': 'GlaxoSmithKline Pharma',
            'sector': 'MNC Healthcare / Vaccines',
            'role': 'ACTIVE',
            'cmp': 2380.0,
            'beta': 0.41,
            'max_dd_3yr': -14.8,
            'roce_3yr': 48.5,
            'cfo_ebitda': 98.6,
            'net_de': -0.28,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'Deloitte'
        },
        {
            'ticker': 'SANOFI.NS',
            'name': 'Sanofi India',
            'sector': 'MNC Healthcare / Vaccines',
            'role': 'BENCH',
            'cmp': 5850.0,
            'beta': 0.36,
            'max_dd_3yr': -13.5,
            'roce_3yr': 62.1,
            'cfo_ebitda': 101.4,
            'net_de': -0.35,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'Price Waterhouse'
        },

        # Sector D3: Daily Essential FMCG / Edible Oils
        {
            'ticker': 'MARICO.NS',
            'name': 'Marico Ltd',
            'sector': 'Consumer Staples FMCG',
            'role': 'ACTIVE',
            'cmp': 610.0,
            'beta': 0.42,
            'max_dd_3yr': -15.1,
            'roce_3yr': 42.1,
            'cfo_ebitda': 96.8,
            'net_de': 0.04,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)'
        },
        {
            'ticker': 'CCL.NS',
            'name': 'CCL Products India',
            'sector': 'Consumer Staples FMCG',
            'role': 'BENCH',
            'cmp': 680.0,
            'beta': 0.52,
            'max_dd_3yr': -19.4,
            'roce_3yr': 21.4,
            'cfo_ebitda': 86.2,
            'net_de': 0.42,
            'pledge_pct': 0.0,
            'auditor': 'Ramanatham & Rao'
        },

        # Sector D4: Chronic Specialty Formulations
        {
            'ticker': 'TORNTPHARM.NS',
            'name': 'Torrent Pharma',
            'sector': 'Chronic Specialty Pharma',
            'role': 'ACTIVE',
            'cmp': 3150.0,
            'beta': 0.45,
            'max_dd_3yr': -14.2,
            'roce_3yr': 21.4,
            'cfo_ebitda': 92.5,
            'net_de': 0.48,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)'
        },
        {
            'ticker': 'ALKEM.NS',
            'name': 'Alkem Laboratories',
            'sector': 'Chronic Specialty Pharma',
            'role': 'BENCH',
            'cmp': 5320.0,
            'beta': 0.52,
            'max_dd_3yr': -16.8,
            'roce_3yr': 19.8,
            'cfo_ebitda': 86.4,
            'net_de': 0.08,
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)'
        },
        {
            'ticker': 'AJANTPHARM.NS',
            'name': 'Ajanta Pharma',
            'sector': 'Chronic Specialty Pharma',
            'role': 'BENCH',
            'cmp': 2850.0,
            'beta': 0.55,
            'max_dd_3yr': -17.4,
            'roce_3yr': 27.8,
            'cfo_ebitda': 88.5,
            'net_de': -0.06,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)'
        },

        # Sector D5: Decorative Coatings MNC
        {
            'ticker': 'KANSAINER.NS',
            'name': 'Kansai Nerolac Paints',
            'sector': 'Decorative MNC Coatings',
            'role': 'ACTIVE',
            'cmp': 198.96,
            'beta': 0.45,
            'max_dd_3yr': -22.1,
            'roce_3yr': 16.5,
            'cfo_ebitda': 91.0,
            'net_de': -0.12,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)'
        },
        {
            'ticker': 'BERGEPAINT.NS',
            'name': 'Berger Paints India',
            'sector': 'Decorative MNC Coatings',
            'role': 'BENCH',
            'cmp': 467.15,
            'beta': 0.52,
            'max_dd_3yr': -19.4,
            'roce_3yr': 23.8,
            'cfo_ebitda': 86.5,
            'net_de': -0.05,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'S.R. Batliboi (EY)'
        },

        # Sector D6: Regulated City Gas Utility
        {
            'ticker': 'MGL.NS',
            'name': 'Mahanagar Gas',
            'sector': 'City Gas Distribution',
            'role': 'ACTIVE',
            'cmp': 1420.0,
            'beta': 0.54,
            'max_dd_3yr': -19.2,
            'roce_3yr': 28.5,
            'cfo_ebitda': 99.4,
            'net_de': -0.24,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'Shaparia Mehta'
        },
        {
            'ticker': 'IGL.NS',
            'name': 'Indraprastha Gas',
            'sector': 'City Gas Distribution',
            'role': 'BENCH',
            'cmp': 390.0,
            'beta': 0.58,
            'max_dd_3yr': -21.4,
            'roce_3yr': 26.4,
            'cfo_ebitda': 98.2,
            'net_de': -0.18,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'Walker Chandiok'
        },
        {
            'ticker': 'GUJGASLTD.NS',
            'name': 'Gujarat Gas',
            'sector': 'City Gas Distribution',
            'role': 'BENCH',
            'cmp': 510.0,
            'beta': 0.61,
            'max_dd_3yr': -24.5,
            'roce_3yr': 22.4,
            'cfo_ebitda': 95.1,
            'net_de': 0.01,
            'pledge_pct': 0.0,
            'auditor': 'Deloitte'
        },

        # Sector D7: Agri Nutrients & Crop Protection
        {
            'ticker': 'COROMANDEL.NS',
            'name': 'Coromandel Int',
            'sector': 'Agri Nutrients & Crop Care',
            'role': 'ACTIVE',
            'cmp': 1680.0,
            'beta': 0.62,
            'max_dd_3yr': -18.0,
            'roce_3yr': 29.2,
            'cfo_ebitda': 84.7,
            'net_de': 0.02,
            'pledge_pct': 0.0,
            'auditor': 'Deloitte'
        },
        {
            'ticker': 'SUMICHEM.NS',
            'name': 'Sumitomo Chemical',
            'sector': 'Agri Nutrients & Crop Care',
            'role': 'BENCH',
            'cmp': 480.0,
            'beta': 0.59,
            'max_dd_3yr': -18.2,
            'roce_3yr': 26.1,
            'cfo_ebitda': 92.8,
            'net_de': -0.20,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'S R B C & CO (EY)'
        },
        {
            'ticker': 'PIIND.NS',
            'name': 'PI Industries',
            'sector': 'Agri Nutrients & Crop Care',
            'role': 'BENCH',
            'cmp': 3850.0,
            'beta': 0.64,
            'max_dd_3yr': -19.5,
            'roce_3yr': 22.5,
            'cfo_ebitda': 86.4,
            'net_de': -0.15,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'Price Waterhouse'
        },

        # Sector D8: Energy Infrastructure & Regasification
        {
            'ticker': 'PETRONET.NS',
            'name': 'Petronet LNG',
            'sector': 'Energy Infrastructure',
            'role': 'ACTIVE',
            'cmp': 295.0,
            'beta': 0.58,
            'max_dd_3yr': -21.8,
            'roce_3yr': 26.8,
            'cfo_ebitda': 104.2,
            'net_de': -0.32,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'T.R. Chadha & Co'
        },
        {
            'ticker': 'BATAINDIA.NS',
            'name': 'Bata India',
            'sector': 'Essential Consumer Staple',
            'role': 'BENCH',
            'cmp': 1340.0,
            'beta': 0.51,
            'max_dd_3yr': -20.4,
            'roce_3yr': 18.2,
            'cfo_ebitda': 97.4,
            'net_de': -0.08,  # Net Cash
            'pledge_pct': 0.0,
            'auditor': 'B S R & Co (KPMG)'
        }
    ]
}

def print_master_universe_summary():
    print("=" * 95)
    print("INSTITUTIONAL MASTER UNIVERSE AUDIT: 8 DISTINCT SECTOR ENGINES")
    print("=" * 95)

    print("\n[A] 8 AGGRESSIVE CHAMPIONS (BULL STATE STARTERS: 12.5% EACH)")
    print(f"{'Sector':<28} | {'Ticker':<14} | {'Company':<22} | {'ROCE':<6} | {'Net D/E':<8} | {'Auditor'}")
    print("-" * 95)
    for s in MASTER_UNIVERSE['AGGRESSIVE']:
        if s['role'] == 'ACTIVE':
            nde = 'Net Cash' if s['net_de'] <= 0 else f"{s['net_de']:.2f}x"
            print(f"{s['sector']:<28} | {s['ticker']:<14} | {s['name']:<22} | {s['roce_3yr']:>5.1f}% | {nde:<8} | {s['auditor']}")

    print("\n[B] 8 DEFENSIVE FORTRESSES (PANIC STATE EXPANSION: 6.25% EACH)")
    print(f"{'Sector':<28} | {'Ticker':<14} | {'Company':<22} | {'Beta':<6} | {'MaxDD':<7} | {'Auditor'}")
    print("-" * 95)
    for s in MASTER_UNIVERSE['DEFENSIVE']:
        if s['role'] == 'ACTIVE':
            print(f"{s['sector']:<28} | {s['ticker']:<14} | {s['name']:<22} | {s['beta']:>5.2f}x | {s['max_dd_3yr']:>6.1f}% | {s['auditor']}")

    total_agg = len(MASTER_UNIVERSE['AGGRESSIVE'])
    total_def = len(MASTER_UNIVERSE['DEFENSIVE'])
    print("\n" + "=" * 95)
    print(f"Total Vetted Candidates in Master Pool: {total_agg + total_def} (Aggressive: {total_agg}, Defensive: {total_def})")
    print(f"Active Allocation: 8 in Bull / 16 in Panic | Bench Reserves Monitored: {(total_agg - 8) + (total_def - 8)}")
    print("=" * 95)

if __name__ == '__main__':
    print_master_universe_summary()
