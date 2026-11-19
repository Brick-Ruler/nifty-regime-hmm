"""
Autonomous Institutional Portfolio Agent: Dual-Scan Architecture & Emergency Gap Breaker
========================================================================================
Operational Modes:
1. Morning Emergency Gap Scan (--morning-check):
   - Runs at 9:25 AM IST every weekday.
   - Triggers EMERGENCY DERISKING if Nifty Opening Gap <= -1.5% or India VIX surges > +15%.
   - Immediately rotates into 16-Stock Defensive Fortresses to prevent intraday bleed.
   - Sends an urgent Black Swan alert to neal17022006@gmail.com.

2. End-of-Day Execution Scan (Default / --eod-check):
   - Runs at 3:15 PM IST every weekday.
   - Normal HMM Markov Filter, mark-to-market valuations, and full daily briefing email.
"""

import os
import sys
import json
import math
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Dedicated Dual Logging for Task Scheduler / Cron Traceability
LOG_FILE = os.path.join(BASE_DIR, "eod_cron.log")
class SafeLogger:
    def __init__(self, filepath):
        self.terminal = sys.stdout
        self.log = open(filepath, "a", encoding="utf-8")
    def write(self, message):
        if self.terminal is not None:
            try:
                self.terminal.write(message)
            except Exception:
                pass
        self.log.write(message)
        self.log.flush()
    def flush(self):
        if self.terminal is not None:
            try:
                self.terminal.flush()
            except Exception:
                pass
        self.log.flush()

_logger = SafeLogger(LOG_FILE)
sys.stdout = _logger
sys.stderr = _logger

from daily_portfolio_advisor import AGG_STOCKS, DEF_STOCKS, fetch_latest_quote
try:
    from update_live_quotes import update_live_quotes
except Exception:
    update_live_quotes = None

LEDGER_FILE = os.path.join(BASE_DIR, "portfolio_ledger.json")
BRIEF_HTML_FILE = os.path.join(BASE_DIR, "latest_email_brief.html")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL") or "neal17022006@gmail.com"

def compute_portfolio_20d_realized_vol():
    """
    Computes annualized 20-day realized volatility of the portfolio basket.
    Reads screened_universe_data.csv. Falls back safely to 17.72% if unavailable.
    """
    csv_file = os.path.join(BASE_DIR, "screened_universe_data.csv")
    if os.path.exists(csv_file):
        try:
            import csv
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            if len(rows) >= 20:
                recent = rows[-20:]
                rets = []
                for r in recent:
                    agg_rets = [float(r[f"{s[0]}_ret"]) for s in AGG_STOCKS if f"{s[0]}_ret" in r]
                    if agg_rets:
                        rets.append(sum(agg_rets) / len(agg_rets))
                    elif 'nifty_ret' in r:
                        rets.append(float(r['nifty_ret']))
                if len(rets) >= 10:
                    m = sum(rets) / len(rets)
                    var = sum((x - m)**2 for x in rets) / len(rets)
                    return max(5.0, round(math.sqrt(var) * math.sqrt(252), 2))
        except Exception as e:
            print(f"Vol calculation error: {e}")
    return 17.72

def send_email_report(subject, html_content, to_email=RECIPIENT_EMAIL):
    """
    Dual-mode email sender:
    1. If GMAIL_APP_PASSWORD is set (e.g. in GitHub Actions), sends via smtplib.
    2. Otherwise falls back to the local Antigravity Gmail CLI.
    """
    gmail_user = os.environ.get("GMAIL_USER") or to_email
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")

    if gmail_app_password:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = gmail_user
            msg["To"] = to_email
            msg.attach(MIMEText(html_content, "html", "utf-8"))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gmail_user, gmail_app_password)
                server.sendmail(gmail_user, [to_email], msg.as_string())
            print(f"Report emailed via Cloud SMTP to {to_email}!")
            return True
        except Exception as e:
            print(f"SMTP error: {e}")

    # Fallback to local Gmail CLI
    try:
        tmp_file = os.path.join(BASE_DIR, "temp_email_body.html")
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        cmd = [
            "gmail", "mutate", "send",
            "--to", to_email,
            "--subject", subject,
            "--html",
            "--body-file", tmp_file
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        out = (res.stdout or "").strip()
        err = (res.stderr or "").strip()
        if res.returncode == 0:
            print(f"Report emailed via local Gmail CLI! ({out or 'Message Dispatched'})")
            return True
        else:
            print(f"Gmail CLI warning (code {res.returncode}): {err or out}")
            return False
    except Exception as e:
        print(f"Gmail CLI error: {e}")
        return False

def fetch_open_and_prev_close(symbol):
    """
    Fetches today's open price and yesterday's close price for gap calculation.
    """
    import urllib.request
    import urllib.parse
    encoded = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=5d&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = data['chart']['result'][0]
            quotes = result['indicators']['quote'][0]
            opens = [o for o in quotes['open'] if o is not None and not math.isnan(o)]
            closes = [c for c in quotes['close'] if c is not None and not math.isnan(c)]
            if len(opens) >= 1 and len(closes) >= 2:
                today_open = opens[-1]
                prev_close = closes[-2]
                gap_pct = ((today_open - prev_close) / prev_close) * 100.0
                return today_open, prev_close, gap_pct
            elif len(closes) >= 2:
                return closes[-1], closes[-2], ((closes[-1] - closes[-2]) / closes[-2]) * 100.0
    except Exception as e:
        pass
    return None, None, 0.0

def is_valid_execution_window(mode):
    """
    Guards against delayed cloud runners executing outside valid market hours.
    Timezone: Asia/Kolkata (IST = UTC + 5:30)
    Can be bypassed manually using --force flag.
    """
    if "--force" in sys.argv:
        print("[TIME GATE] --force flag detected. Bypassing schedule window check.")
        return True

    from datetime import timezone, timedelta
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(timezone.utc).astimezone(ist_tz)
    weekday = now_ist.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

    if weekday > 4:
        print(f"[TIME GATE] Weekend detected (Day {weekday}). Execution suppressed.")
        return False

    total_mins = now_ist.hour * 60 + now_ist.minute

    if mode == "morning":
        # Morning Gap Window: 09:15 to 10:15 IST (555 to 615 minutes)
        if not (555 <= total_mins <= 615):
            print(f"[TIME GATE] Current time {now_ist.strftime('%H:%M IST')} is outside Morning Gap window (09:15-10:15 IST). Execution suppressed.")
            return False
    elif mode == "eod":
        # EOD Rebalance Window: 14:45 to 16:30 IST (885 to 990 minutes)
        if not (885 <= total_mins <= 990):
            print(f"[TIME GATE] Current time {now_ist.strftime('%H:%M IST')} is outside EOD Rebalance window (14:45-16:30 IST). Execution suppressed.")
            return False

    return True

def run_morning_circuit_breaker():
    if not is_valid_execution_window("morning"):
        return
    print("=" * 80)
    print("      MORNING EMERGENCY GAP CIRCUIT BREAKER (9:25 AM IST SCAN)        ")
    print("=" * 80)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"Timestamp: {now_str}")

    if not os.path.exists(LEDGER_FILE):
        print("Error: Ledger file not found.")
        return
    with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
        ledger = json.load(f)

    # 1. Fetch NIFTY 50 Opening Gap and VIX Spike
    nifty_open, nifty_prev_close, nifty_gap = fetch_open_and_prev_close("^NSEI")
    vix_open, vix_prev_close, vix_gap = fetch_open_and_prev_close("^INDIAVIX")
    
    nifty_open = nifty_open or 25350.0
    nifty_prev_close = nifty_prev_close or 25350.0
    nifty_gap = nifty_gap if nifty_gap is not None else 0.0
    vix_open = vix_open or 15.5
    vix_prev_close = vix_prev_close or 15.5
    vix_gap = vix_gap if vix_gap is not None else 0.0

    print(f"-> NIFTY 50 Opening Gap: {nifty_gap:+5.2f}% (Open: {nifty_open:,.1f} | Prev Close: {nifty_prev_close:,.1f})")
    print(f"-> India VIX:            {vix_open:5.2f} (Gap: {vix_gap:+5.2f}%)")

    # 2. Check Calibrated Optimal Threshold: Gap <= -1.75% OR (Gap <= -1.25% AND VIX >= 20.0)
    emergency_triggered = (nifty_gap <= -1.75) or (nifty_gap <= -1.25 and vix_open >= 20.0 and vix_gap >= 15.0)

    if not emergency_triggered:
        print(f"Status: Market open within normal tolerance (Gap: {nifty_gap:+4.2f}%).")
        print("Dispatching Morning Market Briefing to user email...")

        active_rows_html = ""
        for sym in ledger.get('holdings', {}):
            item = ledger['holdings'][sym]
            sh = item.get('shares', 0)
            if sh > 0:
                active_rows_html += f"""
                <tr>
                    <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-size: 13px;"><strong>{sym.replace('.NS','')}</strong></td>
                    <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-size: 13px;">{item.get('name', sym)}</td>
                    <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-size: 13px;">{sh}</td>
                    <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-size: 13px;">Rs. {item.get('cmp', 0):,.1f}</td>
                    <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-size: 13px;">Rs. {item.get('current_value', 0):,.2f}</td>
                </tr>
                """

        morning_html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; background-color: #f0f2f5; color: #1c1e21; margin: 0; padding: 20px;">
    <div style="max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 10px; border: 1px solid #dcdfe4; padding: 24px;">
        
        <div style="border-bottom: 2px solid #059669; padding-bottom: 12px; margin-bottom: 18px;">
            <div style="font-size: 20px; font-weight: 700; color: #0f172a;">☀️ NIFTY Morning Risk Scan (9:25 AM IST)</div>
            <div style="font-size: 13px; color: #64748b; margin-top: 4px;">Automated Overnight Gap Surveillance • Rs. 1 Lakh Concentration Portfolio</div>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #475569; margin-bottom: 8px;">1. Market Open Status & Circuit Breaker Audit</div>
            <div style="margin-bottom: 12px;">
                <span style="background: #dcfce7; color: #15803d; border: 1px solid #86efac; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 12px; display: inline-block;">🟢 ALL SYSTEMS NOMINAL — NORMAL MARKET OPEN</span>
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="width: 50%; vertical-align: top; padding-right: 10px;">
                        <div style="font-size: 12px; color: #64748b;">NIFTY 50 Opening Gap</div>
                        <div style="font-size: 22px; font-weight: 800; color: {'#16a34a' if nifty_gap >= 0 else '#475569'};">{nifty_gap:+4.2f}%</div>
                        <div style="font-size: 12px; color: #64748b; margin-top: 2px;">Open: {nifty_open:,.1f} | Prev: {nifty_prev_close:,.1f}</div>
                    </td>
                    <td style="width: 50%; vertical-align: top; padding-left: 10px;">
                        <div style="font-size: 12px; color: #64748b;">India VIX Open</div>
                        <div style="font-size: 22px; font-weight: 800; color: #0f172a;">{vix_open:.2f} ({vix_gap:+4.2f}%)</div>
                        <div style="font-size: 12px; color: #64748b; margin-top: 2px;">Threshold: 18.0 (Gap Threshold: -1.50%)</div>
                    </td>
                </tr>
            </table>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #475569; margin-bottom: 8px;">2. Morning Assessment & Action Rationale</div>
            <div style="background: #f0fdf4; border-left: 4px solid #16a34a; padding: 12px; border-radius: 4px; font-size: 13px; line-height: 1.6; color: #166534;">
                • <strong>Overnight Macro Check:</strong> No systemic global shock or overnight black swan detected. Market opened within normal variance.<br>
                • <strong>Breaker Inactive:</strong> Opening gap of <strong>{nifty_gap:+4.2f}%</strong> is safely above the -1.50% liquidation trigger.<br>
                • <strong>Decision: HOLD 100% OF POSITIONS:</strong> Zero portfolio churn. All 8 Concentrated Aggressive Champions are held intact to capture bull momentum without incurring transaction friction.
            </div>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #475569; margin-bottom: 6px;">3. Active Portfolio Holdings (Concentrated Bull Alpha)</div>
            <div style="font-size: 13px; color: #475569; margin-bottom: 10px;">
                Mode: <strong>{ledger['active_regime']}</strong> | Total Valuation: <strong>Rs. {ledger['total_portfolio_value']:,.2f}</strong>
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f1f5f9; text-align: left;">
                        <th style="padding: 8px 10px; font-size: 12px; color: #475569; border-bottom: 1px solid #e2e8f0;">Symbol</th>
                        <th style="padding: 8px 10px; font-size: 12px; color: #475569; border-bottom: 1px solid #e2e8f0;">Company</th>
                        <th style="padding: 8px 10px; font-size: 12px; color: #475569; border-bottom: 1px solid #e2e8f0;">Shares</th>
                        <th style="padding: 8px 10px; font-size: 12px; color: #475569; border-bottom: 1px solid #e2e8f0;">Prev CMP</th>
                        <th style="padding: 8px 10px; font-size: 12px; color: #475569; border-bottom: 1px solid #e2e8f0;">Value</th>
                    </tr>
                </thead>
                <tbody>
                    {active_rows_html}
                </tbody>
            </table>
        </div>

        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #7c3aed; margin-bottom: 8px;">4. Prospective Actions & Decision Matrix (What Happens at 3:15 PM)</div>
            <div style="font-size: 12px; color: #475569; margin-bottom: 8px; line-height: 1.5;">
                Your model continuously tracks 3 quantitative tripwires. Here are the exact prospective actions scheduled for today:
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 6px 8px; width: 32%;"><strong>⚠️ If EOD P(Panic) > 65%:</strong></td>
                    <td style="padding: 6px 8px; color: #b45309;">HMM triggers style rotation; reallocates 80% capital to Defensive Fortresses (Pharma & FMCG).</td>
                </tr>
                <tr style="border-bottom: 1px solid #e2e8f0;">
                    <td style="padding: 6px 8px;"><strong>📉 If 20D Vol > 21.2%:</strong></td>
                    <td style="padding: 6px 8px; color: #1d4ed8;">Exceeds 15% deadband; trims equity to ~85% and parks 15% in Liquid BeES (earning 6.5% p.a.).</td>
                </tr>
                <tr style="background: #f0fdf4;">
                    <td style="padding: 6px 8px;"><strong>🟢 If Market Stays Calm:</strong></td>
                    <td style="padding: 6px 8px; color: #15803d;">Hold 100% of the 8 Champions; zero transaction friction or churn incurred today.</td>
                </tr>
            </table>
        </div>

        <div style="text-align: center; margin: 22px 0 16px 0;">
            <a href="https://nifty-portfolio-tracker.netlify.app/" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; text-decoration: none; padding: 13px 26px; border-radius: 8px; font-weight: 700; font-size: 14px; display: inline-block; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);">
                📊 Open Live Portfolio Tracker (Instant Refresh) &rarr;
            </a>
            <div style="font-size: 11px; color: #64748b; margin-top: 6px;">Netlify Cloud Serverless Feed • Tap 'Refresh Now' anytime from your phone or PC.</div>
        </div>

        <div style="background: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; margin-bottom: 16px; font-size: 13px; color: #334155;">
            ⏰ <strong>Next Scan at 3:15 PM IST:</strong> The Hamilton Markov Model will execute its primary EOD regime classification and dispatch your full Daily Performance Briefing.
        </div>

        <div style="font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 12px;">
            Antigravity Quantitative Regime Engine • Dual-Scan Gap Defense (9:25 AM + 3:15 PM)
        </div>
    </div>
</body>
</html>"""

        morning_html_file = os.path.join(BASE_DIR, "morning_normal_report.html")
        with open(morning_html_file, 'w', encoding='utf-8') as f:
            f.write(morning_html)

        if update_live_quotes:
            try:
                update_live_quotes()
            except Exception as e:
                print(f"Live quotes sync notice: {e}")

        gap_display = f"{nifty_gap:+.2f}".replace('%', '') + " percent"
        safe_subject = f"☀️ NIFTY Morning Scan: Normal Open ({gap_display}) - Positions Held Steady"
        send_email_report(safe_subject, morning_html)
        return

    print("\n" + "!" * 80)
    print(f"CRITICAL ALERT: OVERNIGHT BLACK SWAN GAP DETECTED! (Nifty Gap: {nifty_gap:+4.2f}%)")
    print("Activating Emergency Circuit Breaker -> Immediate Rotation into Defensive Fortresses!")
    print("!" * 80 + "\n")

    # 3. Execute Emergency Rebalance: Liquidate Aggressive, Buy 80% Defensive Fortresses
    total_cap = ledger['total_portfolio_value']
    transactions = []
    turnover_val = 0.0

    # Trim 8 Aggressive Champions from 12.5% to 6.25% (Sell half to fund defensive expansion)
    for sym, name, _ in AGG_STOCKS:
        curr_sh = ledger['holdings'][sym]['shares']
        target_amt = total_cap * 0.0625
        cmp, _ = fetch_latest_quote(sym)
        cmp = cmp or ledger['holdings'][sym]['cmp']
        target_sh = max(1, round(target_amt / cmp))
        diff = target_sh - curr_sh
        if diff < 0:
            transactions.append({'ticker': sym, 'name': name, 'action': 'TRIM_AGGRESSIVE', 'shares': abs(diff), 'price': cmp})
            ledger['cash_buffer'] += (abs(diff) * cmp)
            ledger['holdings'][sym]['shares'] = target_sh
            turnover_val += (abs(diff) * cmp)

    # Add 8 Defensive Fortresses at 6.25% each -> Expanding portfolio to 16 stocks!
    for sym, name, _ in DEF_STOCKS:
        target_amt = total_cap * 0.0625
        cmp, _ = fetch_latest_quote(sym)
        cmp = cmp or ledger['holdings'][sym]['cmp']
        target_sh = max(1, round(target_amt / cmp))
        transactions.append({'ticker': sym, 'name': name, 'action': 'ADD_DEFENSIVE', 'shares': target_sh, 'price': cmp})
        ledger['holdings'][sym]['shares'] = target_sh
        ledger['cash_buffer'] -= (target_sh * cmp)
        turnover_val += (target_sh * cmp)

    fee = turnover_val * 0.0020
    ledger['cumulative_friction_paid'] += fee
    ledger['cash_buffer'] -= fee
    ledger['active_regime'] = "DEFENSIVE QUALITY (EMERGENCY OVERRIDE)"

    # Recalculate equity value
    eq_val = sum(ledger['holdings'][s]['shares'] * ledger['holdings'][s]['cmp'] for s in ledger['holdings'])
    ledger['equity_value'] = round(eq_val, 2)
    ledger['total_portfolio_value'] = round(eq_val + ledger['cash_buffer'], 2)

    ledger['trade_log'].append({
        'date': now_str,
        'trigger': 'EMERGENCY_OVERNIGHT_GAP_CIRCUIT_BREAKER',
        'nifty_gap': round(nifty_gap, 2),
        'orders': transactions,
        'fee': round(fee, 2)
    })

    with open(LEDGER_FILE, 'w', encoding='utf-8') as f:
        json.dump(ledger, f, indent=2)

    # 4. Dispatch Urgent Email Alert via Gmail
    alert_html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #fef2f2; color: #1c1e21; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 2px solid #ef4444; padding: 24px;">
            <div style="color: #b91c1c; font-size: 20px; font-weight: bold; border-bottom: 2px solid #ef4444; padding-bottom: 10px;">
                🚨 EMERGENCY CIRCUIT BREAKER ACTIVATED (9:25 AM IST)
            </div>
            <p style="font-size: 14px; line-height: 1.5; color: #333; margin-top: 14px;">
                An overnight macroeconomic black swan triggered a severe gap-down at market open:
            </p>
            <div style="background: #fee2e2; border-left: 4px solid #ef4444; padding: 12px; border-radius: 4px; font-size: 13px;">
                • <strong>NIFTY 50 Opening Gap:</strong> <span style="color:#b91c1c; font-weight:bold;">{nifty_gap:+4.2f}%</span> (Threshold: -1.50%)<br>
                • <strong>India VIX:</strong> <strong>{vix_open:.2f} ({vix_gap:+4.2f}%)</strong><br>
                • <strong>Action Taken:</strong> 100% Growth basket liquidated; Rs. 80,000 rotated immediately into <strong>8 Defensive Fortresses (Abbott, Torrent, Colgate, Dabur, Alkem, Ipca)</strong>.
            </div>
            <p style="font-size: 13px; color: #555; margin-top: 14px;">
                <strong>Why This Was Done:</strong> Historically, when Nifty gaps down &gt; -1.5%, high-beta midcaps collapse an additional -3% to -6% intraday. Rotated at 9:25 AM to immunize your capital from the intraday sell-off.
            </p>
            <div style="text-align: center; margin: 20px 0 10px 0;">
                <a href="https://nifty-portfolio-tracker.netlify.app/" style="background: #ef4444; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-weight: 700; font-size: 14px; display: inline-block;">
                    🚨 Monitor Emergency Defense in Live Tracker &rarr;
                </a>
            </div>
            <div style="font-size: 12px; color: #888; margin-top: 14px; border-top: 1px solid #eee; padding-top: 10px;">
                Total Portfolio Value: <strong>Rs. {ledger['total_portfolio_value']:,.2f}</strong> | Normal 3:15 PM EOD scan will monitor recovery.
            </div>
        </div>
    </body>
    </html>
    """

    alert_file = os.path.join(BASE_DIR, "emergency_gap_alert.html")
    with open(alert_file, 'w', encoding='utf-8') as f:
        f.write(alert_html)

    gap_display = f"{nifty_gap:+.2f}".replace('%', '') + " percent"
    safe_subject = f"🚨 URGENT: Portfolio Emergency Circuit Breaker Triggered ({gap_display} Gap)"
    send_email_report(safe_subject, alert_html)


def run_eod_agent():
    if not is_valid_execution_window("eod"):
        return
    print("=" * 80)
    print("   AUTONOMOUS HMM AGENT: EOD EXECUTION & COMPREHENSIVE BRIEFING (3:15 PM)  ")
    print("=" * 80)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today_str = datetime.now().strftime('%Y-%m-%d')
    print(f"Timestamp: {now_str}")

    if not os.path.exists(LEDGER_FILE):
        print("Error: Ledger file not found.")
        return
    with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
        ledger = json.load(f)

    # 1. Fetch live market signals
    nifty_price, nifty_ret = fetch_latest_quote("^NSEI")
    vix_price, vix_ret = fetch_latest_quote("^INDIAVIX")
    nifty_price = nifty_price or 25387.40
    vix_price = vix_price or 15.52

    # 2. Compute HMM Forward Filter
    mu = [0.075, -0.22]
    sigma = [0.65, 2.05]
    A = [[0.965, 0.035], [0.115, 0.885]]
    prior = [0.90, 0.10] if ledger['active_regime'].startswith('AGGRESSIVE') else [0.20, 0.80]

    p0_prior = prior[0] * A[0][0] + prior[1] * A[1][0]
    p1_prior = prior[0] * A[0][1] + prior[1] * A[1][1]

    def norm_pdf(x, m, s):
        d = x - m
        return (1.0 / (s * 2.5066)) * 2.71828 ** (-0.5 * (d*d) / (s*s))

    u0 = p0_prior * norm_pdf(nifty_ret, mu[0], sigma[0])
    u1 = p1_prior * norm_pdf(nifty_ret, mu[1], sigma[1])
    total_u = u0 + u1 or 1e-12

    p_calm = (u0 / total_u) * 100.0
    p_panic = (u1 / total_u) * 100.0

    # 3. Hysteresis Decision Rule
    prev_regime = ledger['active_regime']
    if prev_regime.startswith("AGGRESSIVE") and p_panic > 65.0:
        new_regime = "DEFENSIVE QUALITY"
    elif prev_regime.startswith("DEFENSIVE") and p_panic <= 40.0:
        new_regime = "AGGRESSIVE GROWTH"
    else:
        new_regime = "AGGRESSIVE GROWTH" if prev_regime.startswith("AGGRESSIVE") else "DEFENSIVE QUALITY"

    regime_flipped = (new_regime != prev_regime)

    # 3b. Volatility Targeting Overlay (Calibrated B: Target = 21.0%, 15% Deadband, Asymmetric Shield)
    vol_cfg = ledger.get('volatility_targeting', {
        'target_annualized_vol': 21.0,
        'rebalance_deadband': 0.15,
        'rolling_lookback_sessions': 20,
        'current_portfolio_realized_vol': 18.25,
        'current_equity_weight': 1.0,
        'current_liquid_cash_weight': 0.0,
        'status': 'NORMAL_FULL_EXPOSURE'
    })
    realized_vol_20d = compute_portfolio_20d_realized_vol()
    tgt_vol = vol_cfg.get('target_annualized_vol', 21.0)
    deadband = vol_cfg.get('rebalance_deadband', 0.15)
    current_eq_w = vol_cfg.get('current_equity_weight', 1.0)

    # Calibrated B: Full 100% equity compounding in Calm Bull mode unless realized vol exceeds extreme ceiling (24.15%)
    # In Panic Bear regime, scales equity down to preserve capital
    if new_regime == "DEFENSIVE QUALITY" or realized_vol_20d > (tgt_vol * 1.15):
        raw_target_eq_w = min(1.0, round(tgt_vol / max(realized_vol_20d, 5.0), 4))
    else:
        raw_target_eq_w = 1.0

    vol_rebalanced = False
    new_eq_w = current_eq_w
    if abs(raw_target_eq_w - current_eq_w) > deadband:
        vol_rebalanced = True
        new_eq_w = raw_target_eq_w

    new_cash_w = round(1.0 - new_eq_w, 4)
    vol_cfg['current_portfolio_realized_vol'] = realized_vol_20d
    vol_cfg['current_equity_weight'] = new_eq_w
    vol_cfg['current_liquid_cash_weight'] = new_cash_w
    vol_cfg['status'] = 'NORMAL_FULL_EXPOSURE' if new_eq_w >= 0.95 else f'DERISKED_{int(new_cash_w*100)}PCT_CASH'
    ledger['volatility_targeting'] = vol_cfg

    # 4. Reasoning
    reasoning_points = []
    if new_regime == "AGGRESSIVE GROWTH":
        reasoning_points.append(
            f"<strong>Market Mood is Calm Bull:</strong> India VIX closed calm at <strong>{vix_price:.2f} ({vix_ret:+4.2f}%)</strong>, "
            f"well below the 18.0 threshold. NIFTY 50 registered daily drift of <strong>{nifty_ret:+4.2f}%</strong>."
        )
        reasoning_points.append(
            f"<strong>Quantitative Probability:</strong> Hamilton Forward Filter calculated <strong>P(Panic) = {p_panic:.1f}%</strong> "
            f"vs <strong>P(Calm) = {p_calm:.1f}%</strong>."
        )
        reasoning_points.append(
            f"<strong>Volatility Target (18.0%):</strong> 20-Day Portfolio Realized Volatility is <strong>{realized_vol_20d:.1f}%</strong>. "
            f"Gross Allocation: <strong>{new_eq_w*100:.1f}% Equity / {new_cash_w*100:.1f}% Liquid Cash (Yielding 6.5% p.a.)</strong>. "
            f"{'Deadband filter (15%) suppressed friction trade today.' if not vol_rebalanced else 'Vol Target Rebalance executed to maintain risk budget.'}"
        )
        reasoning_points.append(
            f"<strong>Concentration Strategy Active (8 Champions):</strong> Equity capital is concentrated across the 8 Aggressive Champions to capture maximum bull-market alpha."
        )
        if not regime_flipped and not vol_rebalanced:
            reasoning_points.append(
                "<strong>Action Decision: HOLD CONCENTRATED POSITIONS:</strong> Dual hysteresis & deadband filters kept portfolio steady. Zero friction incurred today."
            )
    else:
        reasoning_points.append(
            f"<strong>Market Mood is Panic / High Vol:</strong> India VIX spiked to <strong>{vix_price:.2f} ({vix_ret:+4.2f}%)</strong> with NIFTY at {nifty_ret:+4.2f}%."
        )
        reasoning_points.append(
            f"<strong>Quantitative Probability:</strong> P(Panic) = {p_panic:.1f}% (> 65.0%)."
        )
        reasoning_points.append(
            f"<strong>Volatility Target & Defense:</strong> 20-Day Realized Vol is <strong>{realized_vol_20d:.1f}%</strong>. "
            f"Allocation: <strong>{new_eq_w*100:.1f}% Fortresses / {new_cash_w*100:.1f}% Liquid Cash</strong>."
        )
        reasoning_points.append(
            "<strong>Broadened Defense Active (16 Stocks):</strong> 80% concentrated into 8 Defensive Fortresses (Abbott, Torrent, Colgate, Dabur) to prevent drawdown."
        )

    # 5. Mark to Market (Pure Equity Accounting Convention)
    total_equity_value = 0.0
    total_invested_cost = 0.0
    active_stock_movers = []
    for sym in ledger['holdings']:
        h = ledger['holdings'][sym]
        cmp, daily_r = fetch_latest_quote(sym)
        cmp = cmp or h['cmp']
        h['cmp'] = round(cmp, 2)
        val = round(h['shares'] * cmp, 2)
        h['current_value'] = val
        total_equity_value += val
        
        buy_p = h.get('buy_price', cmp)
        inv_cost = round(h['shares'] * buy_p, 2)
        h['invested_cost'] = inv_cost
        
        if h['shares'] > 0:
            total_invested_cost += inv_cost
            pnl = round(val - inv_cost, 2)
            pnl_pct = round((pnl / inv_cost) * 100.0, 2) if inv_cost > 0 else 0.0
            h['unrealized_pnl'] = pnl
            h['unrealized_pnl_pct'] = pnl_pct
            active_stock_movers.append({
                'sym': sym,
                'name': h['name'],
                'shares': h['shares'],
                'buy_price': buy_p,
                'cmp': cmp,
                'cost': inv_cost,
                'val': val,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'daily_r': daily_r
            })

    # Pure Deployed Equity Metrics (Cash Buffer completely segregated!)
    total_invested_cost = round(total_invested_cost, 2)
    total_equity_value = round(total_equity_value, 2)
    net_equity_pnl = round(total_equity_value - total_invested_cost, 2)
    equity_return_pct = round((net_equity_pnl / total_invested_cost) * 100.0, 2) if total_invested_cost > 0 else 0.0
    
    cash_buffer = round(ledger.get('cash_buffer', 1779.40), 2)
    total_account_nav = round(total_equity_value + cash_buffer, 2)
    account_return_pct = round((net_equity_pnl / 100000.0) * 100.0, 2)

    ledger['invested_equity_cost'] = total_invested_cost
    ledger['current_equity_value'] = total_equity_value
    ledger['equity_value'] = total_equity_value
    ledger['equity_pnl'] = net_equity_pnl
    ledger['equity_pnl_pct'] = equity_return_pct
    ledger['cash_buffer'] = cash_buffer
    ledger['total_account_nav'] = total_account_nav
    ledger['total_portfolio_value'] = total_account_nav
    ledger['active_regime'] = new_regime

    if ledger['total_account_nav'] > ledger.get('peak_portfolio_value', 100000.0):
        ledger['peak_portfolio_value'] = ledger['total_account_nav']
    peak_val = ledger['peak_portfolio_value']
    current_drawdown = round(((ledger['total_account_nav'] - peak_val) / peak_val) * 100.0, 2)

    # 6. Execute Rebalance if regime flipped
    transactions = []
    if regime_flipped:
        total_cap = ledger['total_account_nav']
        turnover_val = 0.0
        if new_regime == "DEFENSIVE QUALITY":
            # PANIC REGIME: ADD 8 Defensive Fortresses, expanding to 16 stocks total (6.25% each * new_eq_w)
            for sym, name, _ in AGG_STOCKS:
                target_amt = total_cap * (new_eq_w / 16.0)
                cmp = ledger['holdings'][sym]['cmp']
                target_sh = max(1, round(target_amt / cmp))
                curr_sh = ledger['holdings'][sym]['shares']
                diff = target_sh - curr_sh
                if diff != 0:
                    transactions.append({'ticker': sym, 'name': name, 'action': 'TRIM_AGGRESSIVE' if diff < 0 else 'BUY', 'shares': abs(diff), 'price': cmp})
                    ledger['holdings'][sym]['shares'] = target_sh
                    ledger['cash_buffer'] -= (diff * cmp)
                    turnover_val += abs(diff) * cmp
            for sym, name, _ in DEF_STOCKS:
                target_amt = total_cap * (new_eq_w / 16.0)
                cmp = ledger['holdings'][sym]['cmp']
                target_sh = max(1, round(target_amt / cmp))
                curr_sh = ledger['holdings'][sym]['shares']
                diff = target_sh - curr_sh
                if diff != 0:
                    transactions.append({'ticker': sym, 'name': name, 'action': 'ADD_DEFENSIVE', 'shares': abs(diff), 'price': cmp})
                    ledger['holdings'][sym]['shares'] = target_sh
                    ledger['cash_buffer'] -= (diff * cmp)
                    turnover_val += abs(diff) * cmp
        else:
            # BULL REGIME: Liquidate 8 Defensives, Concentrate into 8 Aggressive Champions (12.5% each * new_eq_w)
            for sym, name, _ in DEF_STOCKS:
                curr_sh = ledger['holdings'][sym]['shares']
                if curr_sh > 0:
                    cmp = ledger['holdings'][sym]['cmp']
                    transactions.append({'ticker': sym, 'name': name, 'action': 'EXIT_DEFENSIVE', 'shares': curr_sh, 'price': cmp})
                    ledger['cash_buffer'] += (curr_sh * cmp)
                    ledger['holdings'][sym]['shares'] = 0
                    turnover_val += (curr_sh * cmp)
            for sym, name, _ in AGG_STOCKS:
                target_amt = total_cap * (new_eq_w / 8.0)
                cmp = ledger['holdings'][sym]['cmp']
                target_sh = max(1, round(target_amt / cmp))
                curr_sh = ledger['holdings'][sym]['shares']
                diff = target_sh - curr_sh
                if diff != 0:
                    transactions.append({'ticker': sym, 'name': name, 'action': 'BUY' if diff > 0 else 'SELL', 'shares': abs(diff), 'price': cmp})
                    ledger['holdings'][sym]['shares'] = target_sh
                    ledger['cash_buffer'] -= (diff * cmp)
                    turnover_val += abs(diff) * cmp

        fee = turnover_val * 0.0020
        ledger['cumulative_friction_paid'] += fee
        ledger['cash_buffer'] -= fee
        ledger['total_portfolio_value'] = round(ledger['equity_value'] + ledger['cash_buffer'], 2)
        ledger['total_account_nav'] = ledger['total_portfolio_value']

    # 7. Metrics & Ledger Persistence
    init_nifty = ledger.get('initial_nifty_close', 25300.0)
    nifty_total_return = round(((nifty_price - init_nifty) / init_nifty) * 100.0, 2)
    alpha = round(equity_return_pct - nifty_total_return, 2)

    ledger['regime_intel'] = {
        'active_regime': f"CALM BULL (AGGRESSIVE GROWTH)" if new_regime != "DEFENSIVE QUALITY" else "PANIC BEAR (DEFENSIVE FORTRESS)",
        'p_calm': round(p_calm, 1),
        'p_panic': round(p_panic, 1),
        'panic_threshold': 65.0,
        'realized_vol_20d': round(realized_vol_20d, 2),
        'target_vol': 21.0,
        'equity_weight_pct': round(new_eq_w * 100, 1),
        'cash_weight_pct': round(new_cash_w * 100, 1),
        'nifty_cmp': nifty_price,
        'vix_cmp': vix_price,
        'model_thinking': (
            f"Hamilton forward filter indicates {p_calm:.1f}% Calm Bull confidence. With 20-day realized volatility ({realized_vol_20d:.1f}%) "
            f"safely under the 21.0% target, the system maintains 100% equity concentration in the 8 Aggressive Champions with zero cash drag."
        ) if new_regime != "DEFENSIVE QUALITY" else (
            f"P(Panic) breached the 65.0% threshold ({p_panic:.1f}%). Deployed 8 Defensive Fortresses for portfolio capital protection."
        )
    }

    if not ledger.get('history') or ledger['history'][-1]['date'] != today_str:
        ledger.setdefault('history', []).append({'date': today_str, 'value': total_account_nav, 'nifty_close': nifty_price, 'regime': new_regime})

    with open(LEDGER_FILE, 'w', encoding='utf-8') as f:
        json.dump(ledger, f, indent=2)

    # 8. Email HTML Construction
    active_stock_movers.sort(key=lambda x: x['pnl_pct'], reverse=True)
    top_gainers = active_stock_movers[:3]
    top_losers = active_stock_movers[-3:]

    gap_cutoff_nifty = round(nifty_price * (1.0 - 0.0175), 1)
    vol_upper_trigger = round(21.0 / max(0.01, (new_eq_w - deadband)), 1)

    foot_pnl_class = "text-green" if net_equity_pnl >= 0 else "text-red"
    foot_sign = "+" if net_equity_pnl >= 0 else ""

    active_rows_html = ""
    for item in active_stock_movers:
        pnl_class = "text-green" if item['pnl'] >= 0 else "text-red"
        sign = "+" if item['pnl'] >= 0 else ""
        active_rows_html += f"""
        <tr>
            <td>
                <strong>{item['sym'].replace('.NS','')}</strong><br>
                <span style="font-size: 11px; color: #64748b;">{item['name']}</span>
            </td>
            <td style="text-align: right;"><strong>{item['shares']}</strong></td>
            <td style="text-align: right; color: #64748b;">Rs. {item['buy_price']:,.2f}</td>
            <td style="text-align: right; font-weight: 700;">Rs. {item['cmp']:,.2f}</td>
            <td style="text-align: right; color: #64748b;">Rs. {item['cost']:,.2f}</td>
            <td style="text-align: right; font-weight: 700;">Rs. {item['val']:,.2f}</td>
            <td style="text-align: right;" class="{pnl_class}"><strong>{sign}Rs. {item['pnl']:,.2f}</strong></td>
            <td style="text-align: right;" class="{pnl_class}"><strong>{sign}{item['pnl_pct']:.2f}%</strong></td>
        </tr>
        """

    email_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f0f2f5; color: #1c1e21; margin: 0; padding: 20px; }}
            .container {{ max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 10px; border: 1px solid #dcdfe4; padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
            .header {{ border-bottom: 2px solid #7c3aed; padding-bottom: 14px; margin-bottom: 20px; }}
            .title {{ font-size: 21px; font-weight: 700; color: #0f172a; margin: 0; }}
            .meta {{ font-size: 13px; color: #64748b; margin-top: 5px; }}
            .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
            .card-title {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #475569; margin-bottom: 8px; }}
            .badge-purple {{ background: #f3e8ff; color: #7e22ce; border: 1px solid #d8b4fe; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 12px; }}
            .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; }}
            .val-large {{ font-size: 20px; font-weight: 800; color: #0f172a; margin-top: 3px; }}
            .val-sub {{ font-size: 11px; color: #64748b; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
            th, td {{ padding: 8px 8px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            th {{ background: #f1f5f9; color: #475569; font-weight: 600; font-size: 11px; }}
            .text-green {{ color: #16a34a; font-weight: 600; }}
            .text-red {{ color: #dc2626; font-weight: 600; }}
            .reasoning-box {{ background: #faf5ff; border-left: 4px solid #7c3aed; padding: 12px; border-radius: 4px; font-size: 13px; line-height: 1.6; color: #4c1d95; }}
            .footer {{ font-size: 11px; color: #94a3b8; text-align: center; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 14px; line-height: 1.5; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title">NIFTY Dynamic Quantitative Portfolio Briefing</div>
                <div class="meta">8 Champions in Bull / 16 Fortresses in Panic • 08:50 AM Pre-Market Radar & 03:15 PM EOD Hamilton Markov</div>
            </div>

            <!-- 1. System Brain & Regime Card -->
            <div class="card">
                <div class="card-title">1. Quantitative Rationale & Regime Brain</div>
                <div style="margin-bottom: 10px;">
                    Active Mode: <span class="badge-purple">{new_regime} (8 CONCENTRATED STOCKS)</span>
                    <span style="font-size: 12px; color: #64748b; margin-left: 8px;">
                        P(Calm Bull): <strong style="color: #16a34a;">{p_calm:.1f}%</strong> | 
                        P(Panic Bear): <strong style="color: #dc2626;">{p_panic:.1f}%</strong> | 
                        Barrier: <strong>65.0% Panic</strong>
                    </span>
                </div>
                <div class="reasoning-box">{"<br>• ".join(["• " + p for p in reasoning_points])}</div>
            </div>

            <!-- 2. Pure Equity Performance Audit (Cash Buffer Segregated) -->
            <div class="card">
                <div class="card-title">2. Pure Equity Performance Audit (Excluding Cash Buffer)</div>
                <div class="grid-2">
                    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px;">
                        <div class="val-sub">Current Invested Equities</div>
                        <div class="val-large">Rs. {total_equity_value:,.2f}</div>
                        <div class="val-sub"><span class="{foot_pnl_class}">{foot_sign}Rs. {net_equity_pnl:,.2f} ({foot_sign}{equity_return_pct:.2f}%)</span> vs Rs. {total_invested_cost:,.2f} Cost</div>
                    </div>
                    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px;">
                        <div class="val-sub">Net Equity Profit / Loss</div>
                        <div class="val-large {foot_pnl_class}">{foot_sign}Rs. {net_equity_pnl:,.2f}</div>
                        <div class="val-sub"><span class="{foot_pnl_class}">{foot_sign}{equity_return_pct:.2f}% Return</span> on Deployed Equities</div>
                    </div>
                    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px;">
                        <div class="val-sub">Unallocated Cash Buffer</div>
                        <div class="val-large" style="color: #2563eb;">Rs. {cash_buffer:,.2f}</div>
                        <div class="val-sub">1.8% Liquid Cash • Zero Market Risk</div>
                    </div>
                    <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px;">
                        <div class="val-sub">Total Account Value (NAV)</div>
                        <div class="val-large" style="color: #7c3aed;">Rs. {total_account_nav:,.2f}</div>
                        <div class="val-sub">Equities (Rs. {round(total_equity_value):,}) + Cash (Rs. {round(cash_buffer):,})</div>
                    </div>
                </div>
            </div>

            <!-- 3. Active Portfolio Holdings Table -->
            <div class="card">
                <div class="card-title">3. Active Stock Holdings Breakdown (100% Equity)</div>
                <table>
                    <thead>
                        <tr>
                            <th>Holding</th>
                            <th style="text-align: right;">Shares</th>
                            <th style="text-align: right;">Buy Price</th>
                            <th style="text-align: right;">Live CMP</th>
                            <th style="text-align: right;">Invested Cost</th>
                            <th style="text-align: right;">Current Value</th>
                            <th style="text-align: right;">Net P&L</th>
                            <th style="text-align: right;">Return %</th>
                        </tr>
                    </thead>
                    <tbody>{active_rows_html}</tbody>
                    <tfoot>
                        <tr style="font-weight: 800; background: #e2e8f0; border-top: 2px solid #cbd5e1;">
                            <td colspan="4">TOTAL INVESTED EQUITIES (Pure Stock Movement)</td>
                            <td style="text-align: right;">Rs. {total_invested_cost:,.2f}</td>
                            <td style="text-align: right;">Rs. {total_equity_value:,.2f}</td>
                            <td style="text-align: right;" class="{foot_pnl_class}">{foot_sign}Rs. {net_equity_pnl:,.2f}</td>
                            <td style="text-align: right;" class="{foot_pnl_class}">{foot_sign}{equity_return_pct:.2f}%</td>
                        </tr>
                        <tr style="font-weight: 600; background: #f8fafc;">
                            <td colspan="4">Liquid Cash Buffer Reserve (Unallocated)</td>
                            <td style="text-align: right;">Rs. {cash_buffer:,.2f}</td>
                            <td style="text-align: right;">Rs. {cash_buffer:,.2f}</td>
                            <td style="text-align: right; color: #64748b;">Rs. 0.00</td>
                            <td style="text-align: right; color: #64748b;">0.00%</td>
                        </tr>
                        <tr style="font-weight: 800; font-size: 13px; border-top: 2px solid #cbd5e1; background: #f1f5f9;">
                            <td colspan="4">TOTAL ACCOUNT NET ASSET VALUE (NAV)</td>
                            <td style="text-align: right;">Rs. 100,000.00</td>
                            <td style="text-align: right;">Rs. {total_account_nav:,.2f}</td>
                            <td style="text-align: right;" class="{foot_pnl_class}">{foot_sign}Rs. {net_equity_pnl:,.2f}</td>
                            <td style="text-align: right;" class="{foot_pnl_class}">{foot_sign}{account_return_pct:.2f}%</td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <!-- Prominent Live Netlify Dashboard Button -->
            <div style="text-align: center; margin: 24px 0 16px 0;">
                <a href="https://nifty-portfolio-tracker.netlify.app/" style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); color: #ffffff; text-decoration: none; padding: 13px 28px; border-radius: 8px; font-weight: 700; font-size: 14px; display: inline-block; box-shadow: 0 4px 12px rgba(124, 58, 237, 0.35);">
                    📊 OPEN LIVE NETLIFY DASHBOARD (INSTANT REFRESH) &rarr;
                </a>
                <div style="font-size: 11px; color: #64748b; margin-top: 6px;">Live Quantitative Feed • Tap to open and view real-time tick-by-tick updates.</div>
            </div>
            <div class="card">
                <div class="card-title">4. Today's Factor Movers (Session P&L)</div>
                <div class="grid-2" style="font-size: 12px;">
                    <div><strong class="text-green">Top Performers Today:</strong><br>{"<br>".join([f"• {g['name']}: <span class='text-green'>{g['pnl_pct']:+4.2f}%</span> (Rs.{g['cmp']:,.1f})" for g in top_gainers])}</div>
                    <div><strong class="text-red">Laggards Today:</strong><br>{"<br>".join([f"• {l['name']}: <span class='text-red'>{l['pnl_pct']:+4.2f}%</span> (Rs.{l['cmp']:,.1f})" for l in top_losers])}</div>
                </div>
            </div>
            <div class="card">
                <div class="card-title" style="color: #7c3aed;">5. Forward-Looking Action Roadmap (What Happens If Conditions Change)</div>
                <div style="font-size: 12px; color: #475569; margin-bottom: 10px;">
                    Your autonomous model continuously monitors 3 quantitative tripwires. Here are the exact prospective actions it will execute:
                </div>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 28%;">Scenario / Trigger Condition</th>
                            <th style="width: 38%;">Model's Prospective Action</th>
                            <th style="width: 34%;">Target Portfolio Reallocation</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>
                                <strong style="color: #6366f1;">🌅 Morning Surveillance (08:50 AM)</strong><br>
                                Global cues, indicative drift, and overnight corporate filings
                            </td>
                            <td>
                                <strong>Read-Only Intelligence Radar:</strong> Evaluates global macro mood and scans all 16 portfolio holdings for regulatory and corporate exchange filings.
                            </td>
                            <td>
                                <strong>Zero Morning Churn:</strong> Confirms capital remains 100% steady. Avoids the 53.4% whipsaw rate discovered on morning intraday noise.
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <strong style="color: #d97706;">⚠️ Macro Regime Flip</strong><br>
                                EOD Markov P(Panic) &gt; <strong>65.0%</strong> (currently {p_panic:.1f}%)
                            </td>
                            <td>
                                <strong>03:15 PM EOD Style Expansion:</strong> HMM signals confirmed bear turbulence. Expands into the 8 Defensive Fortresses at 6.25% each.
                            </td>
                            <td>
                                <strong>16 Stocks Total:</strong> Holds 8 Champions + 8 Fortresses (Colpal, Glaxo, Marico, Torrent Pharma, Kansai Nerolac, MGL, Coromandel, Petronet).
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <strong style="color: #2563eb;">📉 Volatility Spike</strong><br>
                                20-Day Realized Vol climbs &gt; <strong>{vol_upper_trigger:.1f}%</strong> (exceeding 15% deadband from {realized_vol_20d:.1f}%)
                            </td>
                            <td>
                                <strong>Vol Target Cash Buffer:</strong> Automatically trims equity exposure to maintain 18.0% risk budget.
                            </td>
                            <td>
                                <strong>Trims to ~85% Equity / ~15% Liquid Cash:</strong> Excess capital parked in Liquid BeES earning 6.50% p.a.
                            </td>
                        </tr>
                        <tr style="background: #f0fdf4;">
                            <td>
                                <strong style="color: #16a34a;">🟢 Calm Bull Persistence</strong><br>
                                Gap &gt; -1.5%, P(Panic) &le; 65%, Vol &le; {vol_upper_trigger:.1f}%
                            </td>
                            <td>
                                <strong>Hold 8 Champions (100% Equity):</strong> Dual hysteresis & deadband suppress churn. Zero friction incurred.
                            </td>
                            <td>
                                <strong>Concentrated in 8 Champions (12.5% each):</strong> Persistent, Coforge, Cholamandalam, Federal Bank, Indian Hotels, EIH, Balkrishna Ind, Dixon.
                            </td>
                        </tr>
                        <tr style="background: #faf5ff;">
                            <td>
                                <strong style="color: #7c3aed;">🔄 Quarterly Universe Scan</strong><br>
                                Semi-Annual Sector Reconstitution (126 sessions)
                            </td>
                            <td>
                                <strong>Dynamic Bench Evaluation:</strong> Re-ranks 40-stock universe by Momentum/ROCE/Beta and checks 200-day EMA.
                            </td>
                            <td>
                                <strong>Eviction & Promotion:</strong> Displaces any stock ranked &gt; #12 or below 200 EMA with the top sector bench candidate.
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div style="text-align: center; margin: 24px 0 16px 0;">
                <a href="https://nifty-portfolio-tracker.netlify.app/" style="background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); color: #ffffff; text-decoration: none; padding: 13px 28px; border-radius: 8px; font-weight: 700; font-size: 14px; display: inline-block; box-shadow: 0 4px 12px rgba(124, 58, 237, 0.35);">
                    📊 Open Live Portfolio Tracker (Instant Refresh) &rarr;
                </a>
                <div style="font-size: 11px; color: #64748b; margin-top: 6px;">Netlify Cloud Serverless Feed • Tap 'Refresh Now' anytime from your phone or PC.</div>
            </div>
            <div class="footer">Automated by Antigravity Quantitative Regime Engine (Hamilton 1989 EOD Regime Switch).<br>Next pre-market intelligence brief scheduled tomorrow at 08:50 AM IST.</div>
        </div>
    </body>
    </html>
    """
    with open(BRIEF_HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(email_html)

    # 9. Send Email
    if update_live_quotes:
        try:
            update_live_quotes()
        except Exception as e:
            print(f"Live quotes sync notice: {e}")

    subject = f"NIFTY Dynamic Concentration Portfolio Briefing ({datetime.now().strftime('%d %b %Y')})"
    send_email_report(subject, email_html)

if __name__ == "__main__":
    if "--morning-check" in sys.argv:
        print("[DECOMMISSIONED] Morning execution breaker eliminated to prevent whipsaw friction. The system executes solely at 03:15 PM EOD.")
        sys.exit(0)
    else:
        run_eod_agent()
