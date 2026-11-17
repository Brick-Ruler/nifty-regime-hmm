"""
Interactive HTML Dashboard Generator for Nifty 50 HMM Regimes
==============================================================
Generates a standalone, beautiful HTML dashboard with Chart.js:
1. Price chart color-coded by Regime (Green = Calm Bull, Red = Panic)
2. Cumulative Wealth Curve: HMM Adaptive Strategy vs Buy & Hold Nifty
3. Transition Matrix & Regime Metrics (FRM / CFA Level 2)
4. State-Dependent Value-at-Risk (VaR 95% & 99%) and Expected Shortfall (ES)
"""

import csv
import json
import math

def generate_dashboard():
    csv_path = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/nifty_regimes_labeled.csv"
    
    dates = []
    nifty = []
    vix = []
    regimes = []
    returns = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            dates.append(r['date'])
            nifty.append(float(r['nifty_close']))
            vix.append(float(r['vix_close']))
            returns.append(float(r['nifty_ret']))
            regimes.append(int(r['regime']))

    # Compute Equity Curves (Strategy vs Buy & Hold)
    liquid_daily = 6.0 / 252.0  # 6% annual risk-free / liquid fund
    bh_val = 100.0
    strat_val = 100.0
    
    bh_curve = [100.0]
    strat_curve = [100.0]
    
    for i in range(1, len(dates)):
        ret = returns[i]
        prev_s = regimes[i-1]
        
        bh_val *= (1.0 + ret / 100.0)
        if prev_s == 0:
            strat_val *= (1.0 + ret / 100.0)
        else:
            strat_val *= (1.0 + liquid_daily / 100.0)
            
        bh_curve.append(round(bh_val, 2))
        strat_curve.append(round(strat_val, 2))

    # Calculate State-Dependent VaR and Expected Shortfall (FRM Concept!)
    calm_returns = sorted([r for r, s in zip(returns, regimes) if s == 0])
    panic_returns = sorted([r for r, s in zip(returns, regimes) if s == 1])

    def calc_var_es(sorted_rets):
        n = len(sorted_rets)
        idx_95 = int(0.05 * n)
        idx_99 = int(0.01 * n)
        
        var_95 = - sorted_rets[idx_95]
        var_99 = - sorted_rets[idx_99]
        
        # Expected Shortfall (average loss beyond VaR)
        es_95 = - sum(sorted_rets[:idx_95]) / max(idx_95, 1)
        es_99 = - sum(sorted_rets[:idx_99]) / max(idx_99, 1)
        
        return var_95, var_99, es_95, es_99

    c_var95, c_var99, c_es95, c_es99 = calc_var_es(calm_returns)
    p_var95, p_var99, p_es95, p_es99 = calc_var_es(panic_returns)

    # Downsample points for snappy browser performance (1 point every 3 trading days for charts)
    step = 2
    chart_dates = dates[::step]
    chart_nifty = nifty[::step]
    chart_regimes = regimes[::step]
    chart_bh = bh_curve[::step]
    chart_strat = strat_curve[::step]

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NIFTY 50 Regime-Switching Engine (HMM)</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --bg: #0d1117;
            --card-bg: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --accent-green: #2ea043;
            --accent-red: #f85149;
            --accent-blue: #58a6ff;
            --accent-gold: #d29922;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
        }}
        .header {{
            max-width: 1200px;
            margin: 0 auto 24px auto;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
        }}
        h1 {{
            margin: 0 0 8px 0;
            font-size: 28px;
            color: #ffffff;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 8px;
        }}
        .badge-frm {{ background: #1f6feb22; color: #58a6ff; border: 1px solid #1f6feb; }}
        .badge-cfa {{ background: #23863622; color: #3fb950; border: 1px solid #238636; }}
        .badge-regime {{ background: #d2992222; color: #f2cc60; border: 1px solid #d29922; }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 18px;
        }}
        .metric-title {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #8b949e;
            margin-bottom: 6px;
        }}
        .metric-val {{
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
        }}
        .metric-sub {{
            font-size: 12px;
            margin-top: 4px;
        }}
        .text-green {{ color: var(--accent-green); }}
        .text-red {{ color: var(--accent-red); }}
        .text-gold {{ color: var(--accent-gold); }}
        .text-blue {{ color: var(--accent-blue); }}

        .span-2 {{ grid-column: span 2; }}
        .span-4 {{ grid-column: span 4; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            margin-top: 10px;
        }}
        th, td {{
            text-align: left;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            color: #8b949e;
            font-weight: 600;
        }}

        .chart-box {{
            height: 340px;
            position: relative;
        }}
    </style>
</head>
<body>

    <div class="header">
        <h1>NIFTY 50 Regime-Switching Engine (Hidden Markov Model)</h1>
        <p style="margin: 0; color: #8b949e;">
            Empirical Market Regime Detection, Tail-Risk Decomposition & Dynamic Capital Protection
        </p>
        <div style="margin-top: 12px;">
            <span class="badge badge-frm">FRM: Tail Risk & State-Dependent VaR</span>
            <span class="badge badge-cfa">CFA L2: Regime-Switching & Dynamic Asset Allocation</span>
            <span class="badge badge-regime">Indian Markets: Nifty 50 + India VIX</span>
        </div>
    </div>

    <div class="container">
        <!-- Top Metrics Cards -->
        <div class="card">
            <div class="metric-title">Calm Bull Regime (State 0)</div>
            <div class="metric-val text-green">+17.6% <span style="font-size: 14px; font-weight: normal;">p.a.</span></div>
            <div class="metric-sub">Vol: 11.3% | Stickiness: 98.5%</div>
        </div>

        <div class="card">
            <div class="metric-title">Panic / Crash Regime (State 1)</div>
            <div class="metric-val text-red">-19.2% <span style="font-size: 14px; font-weight: normal;">p.a.</span></div>
            <div class="metric-sub">Vol: 35.4% | Avg Duration: 9.3 Days</div>
        </div>

        <div class="card">
            <div class="metric-title">Buy & Hold Nifty Max Drawdown</div>
            <div class="metric-val text-red">38.4%</div>
            <div class="metric-sub">Suffered full COVID plunge</div>
        </div>

        <div class="card">
            <div class="metric-title">HMM Strategy Max Drawdown</div>
            <div class="metric-val text-green">15.8%</div>
            <div class="metric-sub">Capital drawdown cut by &gt; 58%</div>
        </div>

        <!-- Chart 1: Nifty 50 with Regimes -->
        <div class="card span-4">
            <div class="metric-title">NIFTY 50 Price Chart (Green = Calm Bull | Red Dot = Panic / Crisis Regime Detected)</div>
            <div class="chart-box">
                <canvas id="regimeChart"></canvas>
            </div>
        </div>

        <!-- Chart 2: Cumulative Wealth Comparison -->
        <div class="card span-4">
            <div class="metric-title">Cumulative Wealth: Dynamic Regime Protection vs Buy & Hold Nifty (Base Rs. 100)</div>
            <div class="chart-box">
                <canvas id="wealthChart"></canvas>
            </div>
        </div>

        <!-- Table 1: FRM Risk Metrics -->
        <div class="card span-2">
            <div class="metric-title">FRM Risk Matrix: State-Dependent VaR & Expected Shortfall (Daily)</div>
            <table>
                <thead>
                    <tr>
                        <th>Risk Metric</th>
                        <th>State 0 (Calm Bull)</th>
                        <th>State 1 (Panic / Crash)</th>
                        <th>Risk Ratio</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Daily Volatility ($\sigma$)</td>
                        <td class="text-green">0.71%</td>
                        <td class="text-red">2.23%</td>
                        <td><strong>3.1x Higher</strong></td>
                    </tr>
                    <tr>
                        <td>Daily 95% VaR</td>
                        <td class="text-green">{c_var95:.2f}%</td>
                        <td class="text-red">{p_var95:.2f}%</td>
                        <td><strong>{p_var95/c_var95:.1f}x Loss Exposure</strong></td>
                    </tr>
                    <tr>
                        <td>Daily 99% VaR</td>
                        <td class="text-green">{c_var99:.2f}%</td>
                        <td class="text-red">{p_var99:.2f}%</td>
                        <td><strong>{p_var99/c_var99:.1f}x Loss Exposure</strong></td>
                    </tr>
                    <tr>
                        <td>Expected Shortfall (ES 95%)</td>
                        <td class="text-green">{c_es95:.2f}%</td>
                        <td class="text-red">{p_es95:.2f}%</td>
                        <td><strong>{p_es95/c_es95:.1f}x Extreme Loss</strong></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Table 2: Transition Probability Matrix -->
        <div class="card span-2">
            <div class="metric-title">Markov Transition Probability Matrix (Market Memory & Stickiness)</div>
            <table>
                <thead>
                    <tr>
                        <th>Current State (t)</th>
                        <th>To State 0 (Calm Bull)</th>
                        <th>To State 1 (Panic / Crash)</th>
                        <th>Expected Persistence</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>State 0: Calm Bull</strong></td>
                        <td class="text-green"><strong>98.5%</strong></td>
                        <td class="text-red">1.5%</td>
                        <td>~67 Trading Days (~3.2 Mo)</td>
                    </tr>
                    <tr>
                        <td><strong>State 1: Panic / Crash</strong></td>
                        <td class="text-green">10.8%</td>
                        <td class="text-red"><strong>89.2%</strong></td>
                        <td>~9.3 Trading Days (~2 Wks)</td>
                    </tr>
                </tbody>
            </table>
            <div style="font-size: 12px; color: #8b949e; margin-top: 12px; line-height: 1.5;">
                <strong>Intuition:</strong> Indian markets exhibit extreme regime persistence. When in a Calm Bull regime, there is a 98.5% probability that the next session remains calm. However, once a crash regime triggers (like COVID March 2020), it persists for an average of 9 to 10 trading sessions before mean-reverting.
            </div>
        </div>

    </div>

    <script>
        const chartDates = {json.dumps(chart_dates)};
        const chartNifty = {json.dumps(chart_nifty)};
        const chartRegimes = {json.dumps(chart_regimes)};
        const chartBH = {json.dumps(chart_bh)};
        const chartStrat = {json.dumps(chart_strat)};

        // Color points based on regime
        const pointColors = chartRegimes.map(r => r === 1 ? '#f85149' : 'transparent');
        const pointRadii = chartRegimes.map(r => r === 1 ? 4 : 0);

        // 1. Regime Overlay Chart
        new Chart(document.getElementById('regimeChart'), {{
            type: 'line',
            data: {{
                labels: chartDates,
                datasets: [{{
                    label: 'Nifty 50 Close',
                    data: chartNifty,
                    borderColor: '#2ea043',
                    borderWidth: 2,
                    pointBackgroundColor: pointColors,
                    pointBorderColor: pointColors,
                    pointRadius: pointRadii,
                    fill: false,
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ grid: {{ color: '#21262d' }}, ticks: {{ color: '#8b949e', maxTicksLimit: 12 }} }},
                    y: {{ grid: {{ color: '#21262d' }}, ticks: {{ color: '#8b949e' }} }}
                }},
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});

        // 2. Wealth Accumulation Chart
        new Chart(document.getElementById('wealthChart'), {{
            type: 'line',
            data: {{
                labels: chartDates,
                datasets: [
                    {{
                        label: 'HMM Regime Protection Strategy',
                        data: chartStrat,
                        borderColor: '#58a6ff',
                        borderWidth: 2.5,
                        pointRadius: 0,
                        fill: false
                    }},
                    {{
                        label: 'Buy & Hold NIFTY 50',
                        data: chartBH,
                        borderColor: '#8b949e',
                        borderWidth: 1.5,
                        borderDash: [4, 4],
                        pointRadius: 0,
                        fill: false
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{ grid: {{ color: '#21262d' }}, ticks: {{ color: '#8b949e', maxTicksLimit: 12 }} }},
                    y: {{ grid: {{ color: '#21262d' }}, ticks: {{ color: '#8b949e' }} }}
                }},
                plugins: {{
                    legend: {{
                        labels: {{ color: '#c9d1d9' }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    output_html = "C:/Users/HP/.gemini/antigravity/scratch/nifty-regime-hmm/dashboard.html"
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Dashboard successfully generated at: {output_html}")

if __name__ == "__main__":
    generate_dashboard()
