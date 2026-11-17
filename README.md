# NIFTY 50 Regime-Switching Quantitative Engine & Mid/Small Cap Rotation Portfolio

**An institutional-grade, bias-free quantitative asset allocation framework for the Indian equity markets.**

Designed by bridging **Financial Risk Manager (FRM)** principles (state-dependent volatility, tail-risk Expected Shortfall, Hamilton filtering) and **Chartered Financial Analyst (CFA Level 2)** concepts (multi-factor asset allocation, Elton-Gruber optimal diversification, empirical CAPM beta).

---

## 1. Academic & Quantitative Grounding

1. **Hamilton, James D. (1989)**: *"A New Approach to the Economic Analysis of Nonstationary Time Series."* *Econometrica*, 57(2), 357–384.  
   * Foundation for Markov regime-switching models and the real-time forward filter $\alpha_t$.
2. **Ang, Andrew & Bekaert, Geert (2002)**: *"International Asset Allocation with Regime Shifts."* *Review of Financial Studies*, 15(4), 1137–1187.  
   * Proves that correlation and covariance matrices are non-stationary; diversification collapses during market crashes unless portfolios dynamically adapt to latent regimes.
3. **Kritzman, Mark; Page, Sebastien; & Turkington, David (2012)**: *"Regime Shifts: Implications for Dynamic Asset Allocation."* *Financial Analysts Journal*, 68(3), 22–39.  
   * Practical implementation of regime filters for dynamic multi-asset allocation.
4. **López de Prado, Marcos (2018)**: *"Advances in Financial Machine Learning."* John Wiley & Sons.  
   * Protocols for eliminating lookahead bias, walk-forward validation, and accounting for transaction friction.
5. **Elton, Edwin J. & Gruber, Martin J. (1977)**: *"Risk Reduction and Portfolio Size: An Analytical Solution."* *Journal of Business*, 50(4), 415–437.  
   * Mathematical proof of the optimal portfolio diversification curve (16 to 20 stocks eliminate ~90% of unsystematic risk).

---

## 2. Elimination of Prevalent Backtest Biases

| Bias | How Naive Models Cheat | How Our Engine Solves It |
| :--- | :--- | :--- |
| **Lookahead Bias** | Smoothing parameters over the entire 10-year dataset using future data. | **Strict Walk-Forward Expanding Window**: Parameters at Day $t$ use only past history up to $t-1$. Signals use Hamilton's real-time forward filter ($\alpha_t$). |
| **Selection / Cherry-Picking Bias** | Manually picking known past multi-bagger stocks. | **Algorithmic Factor Screener**: Scanned 45 liquid stocks across 10 sectors on NSE to select the purest mathematical proxies for Beta and Capture ratios. |
| **Friction & Slippage Neglect** | Assuming zero cost of trading. | **Real-World Indian Market Drag**: Deducts 0.20% (20 bps) on every rupee of portfolio turnover (covering STT, exchange fees, brokerage, GST, and bid-ask slippage). |
| **Churn / Whipsaw Drag** | Flipping daily on market noise. | **Hysteresis Conviction Bands**: Requires $P(\text{Panic}) > 0.65$ to shift defensive, and $P(\text{Panic}) \le 0.40$ to return to growth. Total switches capped at ~7/year. |
| **Vendor Glitches** | Blindly trusting unadjusted data. | Automated bad-tick scanner corrected the Yahoo Finance NSE decimal glitch (Dec 2019). |

---

## 3. The 16 Algoritmically Screened Stocks

Selected from a 45-stock candidate pool on NSE:

### A. Top 8 Aggressive Champions (80% in Calm, 20% in Panic)
*Average Upside Capture: 1.28 | Average Beta: 1.21*
* **DIXON TECH** (`DIXON.NS`): Beta 1.31, Upside Capture 1.37 (EMS / Electronics)
* **CHOLAMANDALAM** (`CHOLAFIN.NS`): Beta 1.29, Upside Capture 1.33 (High-Beta NBFC)
* **MANAPPURAM** (`MANAPPURAM.NS`): Beta 1.26, Upside Capture 1.33 (Gold Loan NBFC)
* **AARTI INDUSTRIES** (`AARTIIND.NS`): Beta 1.30, Upside Capture 1.22 (Specialty Chemicals)
* **BHARAT FORGE** (`BHARATFORG.NS`): Beta 1.17, Upside Capture 1.24 (Industrial Forging)
* **PERSISTENT SYSTEMS** (`PERSISTENT.NS`): Beta 1.10, Upside Capture 1.32 (Midcap IT)
* **INDIAN HOTELS** (`INDHOTEL.NS`): Beta 1.17, Upside Capture 1.18 (Hospitality)
* **COFORGE** (`COFORGE.NS`): Beta 1.10, Upside Capture 1.18 (Digital IT)

### B. Top 8 Defensive Fortresses (80% in Panic, 20% in Calm)
*Average Downside Capture: 0.47 | Average Beta: 0.51*
* **ABBOTT INDIA** (`ABBOTINDIA.NS`): Beta 0.38, Downside Capture 0.35 (MNC Healthcare)
* **TORRENT PHARMA** (`TORNTPHARM.NS`): Beta 0.46, Downside Capture 0.36 (Chronic Pharma)
* **IPCA LABS** (`IPCALAB.NS`): Beta 0.38, Downside Capture 0.27 (Formulations/API)
* **MARICO** (`MARICO.NS`): Beta 0.51, Downside Capture 0.42 (FMCG Staples)
* **ALKEM LABS** (`ALKEM.NS`): Beta 0.51, Downside Capture 0.50 (Anti-Infectives)
* **COLGATE-PALMOLIVE** (`COLPAL.NS`): Beta 0.54, Downside Capture 0.57 (Oral Hygiene)
* **DABUR INDIA** (`DABUR.NS`): Beta 0.61, Downside Capture 0.74 (Personal Care - lowest vol at 21.8%)
* **LUPIN** (`LUPIN.NS`): Beta 0.67, Downside Capture 0.62 (Respiratory Pharma)

---

## 4. Out-of-Sample Performance Summary (2019 – 2026)

*Net of 20 bps transaction friction on all rebalances across 1,703 trading days:*

| Metric | HMM Screened Rotation (16 Stocks) | Static Screened 16-Stock Basket | NIFTY 50 Benchmark |
| :--- | :---: | :---: | :---: |
| **Total Net Return** | **+639.9%** (7.4x Capital) | +352.9% | +110.8% |
| **CAGR (Annualized Return)** | **34.47%** | 25.05% | 11.67% |
| **Annualized Volatility** | 19.42% | 17.71% | 17.77% |
| **Maximum Drawdown (MDD)** | **26.13%** | 32.05% | 38.44% |
| **Sharpe Ratio ($R_f = 6.5\%$)** | **1.44** | 1.05 | 0.29 |
| **Calmar Ratio ($\text{CAGR} / \text{MDD}$)** | **1.32** | 0.78 | 0.30 |
| **Rebalance Switches** | **50 in 7 Years** (~7 / yr) | 0 | 0 |

---

## 5. Dual-Scan Daily Execution Architecture

To eliminate **overnight gap risk** and protect capital against black swan morning crashes, the agent operates two daily scans:

```
                            EVERY WEEKDAY (MON - FRI)
                                       │
        ┌──────────────────────────────┴──────────────────────────────┐
        ▼                                                             ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────────────┐
│     SCAN 1: 9:25 AM MORNING CHECK     │   │      SCAN 2: 3:15 PM EOD SCAN         │
│     (Emergency Black Swan Breaker)    │   │      (Normal Daily Regime Scan)       │
├───────────────────────────────────────┤   ├───────────────────────────────────────┤
│ • Checks 9:25 AM NIFTY Opening Gap    │   │ • Normal daily HMM Markov Filter      │
│ • If Gap <= -1.50%:                   │   │ • Checks conviction bands & momentum  │
│   -> EMERGENCY DERISKING TRIGGERED!   │   │ • Mark-to-market ledger update        │
│   -> Immediately rotates into 16      │   │ • Formats and emails daily executive  │
│      Defensive Fortresses             │   │   performance briefing                │
│   -> Sends urgent alert to your email │   │                                       │
│ • If Gap > -1.50%:                    │   │                                       │
│   -> Silent exit, zero action         │   │                                       │
└───────────────────────────────────────┘   └───────────────────────────────────────┘
```

Both scans are registered in **Windows Task Scheduler**:
1. `NiftyMorningCircuitBreaker` — Runs every weekday at **09:25 AM IST**.
2. `NiftyRegimeAdvisor` — Runs every weekday at **03:15 PM IST**.

---

## 6. Manual Execution Commands (For Testing)

```powershell
# Morning Circuit Breaker Check:
& "C:\Users\HP\AppData\Local\Python\pythoncore-3.12-64\python.exe" "C:\Users\HP\.gemini\antigravity\scratch\nifty-regime-hmm\auto_portfolio_agent.py" --morning-check

# Afternoon End-of-Day Scan & Briefing:
& "C:\Users\HP\AppData\Local\Python\pythoncore-3.12-64\python.exe" "C:\Users\HP\.gemini\antigravity\scratch\nifty-regime-hmm\auto_portfolio_agent.py"
```

---

## 6. Dashboards

Double-click to open in any web browser:
* [`dashboard_mid_small.html`](dashboard_mid_small.html): Pure-Equity 16-Stock Mid & Small Cap Rotation Dashboard.
* [`dashboard_production.html`](dashboard_production.html): Multi-Asset All-Weather Macro Portfolio Dashboard (Nifty, Gold, Cash).
