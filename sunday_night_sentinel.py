"""
NIFTY Sunday Night Macro & Black-Swan Pre-Flagging Sentinel (09:30 PM IST Sunday)
=================================================================================
Monitors global macro futures at the Sunday night market open (US Equity Futures,
Crude Oil, CBOE VIX, Gold, USD/INR) to detect broad weekend systemic shocks
BEFORE the Indian market opens on Monday at 09:15 AM IST.

Writes `weekend_sentinel` state into `portfolio_ledger.json` so:
1. Monday 08:50 AM Pre-Market Radar highlights any elevated weekend macro risk.
2. Monday 09:20 AM Black-Swan Morning Breaker can pre-arm defensive rotation
   if a CRITICAL_BLACK_SWAN is confirmed by a NIFTY gap-down.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

LOG_FILE = os.path.join(BASE_DIR, "sunday_cron.log")
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

from auto_portfolio_agent import send_email_report

LEDGER_FILE = os.path.join(BASE_DIR, "portfolio_ledger.json")
SUNDAY_HTML_FILE = os.path.join(BASE_DIR, "latest_sunday_brief.html")

MACRO_FUTURES = {
    "S&P 500 Futures": "ES=F",
    "Nasdaq 100 Futures": "NQ=F",
    "Crude Oil (WTI/Macro)": "CL=F",
    "US CBOE VIX": "^VIX",
    "Gold (Safe Haven)": "GC=F",
    "USD / INR": "INR=X"
}

def is_valid_sunday_window():
    if "--force" in sys.argv or "--cloud" in sys.argv:
        print("[TIME GATE] --force/--cloud flag detected. Bypassing Sunday window check.")
        return True
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(timezone.utc).astimezone(ist_tz)
    # 6 = Sunday
    if now_ist.weekday() != 6:
        print(f"[TIME GATE] Non-Sunday detected (Day {now_ist.weekday()}). Sunday sentinel suppressed.")
        return False
    total_mins = now_ist.hour * 60 + now_ist.minute
    # Window: 20:30 to 23:00 IST (1230 to 1380 mins)
    if not (1230 <= total_mins <= 1380):
        print(f"[TIME GATE] Current time {now_ist.strftime('%H:%M IST')} outside Sunday window (20:30-23:00 IST).")
        return False
    return True

def fetch_macro_snapshot():
    snapshot = {}
    for label, sym in MACRO_FUTURES.items():
        try:
            encoded = urllib.parse.quote(sym)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=5d&interval=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                meta = data["chart"]["result"][0]["meta"]
                cmp = meta.get("regularMarketPrice")
                prev = meta.get("chartPreviousClose") or meta.get("previousClose")
                chg = ((cmp - prev) / prev) * 100.0 if (cmp is not None and prev) else 0.0
                snapshot[label] = {
                    "symbol": sym,
                    "price": round(float(cmp), 2) if cmp is not None else "N/A",
                    "chg_pct": round(float(chg), 2)
                }
        except Exception as e:
            print(f"[WARN] Failed fetching {sym}: {e}")
            snapshot[label] = {"symbol": sym, "price": "N/A", "chg_pct": 0.0}
    return snapshot

def classify_weekend_risk(snapshot):
    sp = snapshot.get("S&P 500 Futures", {}).get("chg_pct", 0.0)
    nq = snapshot.get("Nasdaq 100 Futures", {}).get("chg_pct", 0.0)
    oil = snapshot.get("Crude Oil (WTI/Macro)", {}).get("chg_pct", 0.0)
    vix_lvl = snapshot.get("US CBOE VIX", {}).get("price", 15.0)
    vix_chg = snapshot.get("US CBOE VIX", {}).get("chg_pct", 0.0)
    vix_num = float(vix_lvl) if isinstance(vix_lvl, (int, float)) else 15.0

    reasons = []
    if sp <= -2.0:
        reasons.append(f"S&P 500 Futures plunged {sp:+.2f}% (<= -2.0% threshold)")
    if nq <= -2.5:
        reasons.append(f"Nasdaq 100 Futures plunged {nq:+.2f}% (<= -2.5% threshold)")
    if oil >= 6.0:
        reasons.append(f"Crude Oil spiked {oil:+.2f}% (>= +6.0% energy shock)")
    if vix_num >= 28.0 or vix_chg >= 20.0:
        reasons.append(f"US CBOE VIX surged to {vix_num:.2f} ({vix_chg:+.2f}%)")

    if reasons:
        return "CRITICAL_BLACK_SWAN", "PRE_ARM_DEFENSE_AT_OPEN", reasons

    caution_reasons = []
    if sp <= -1.0:
        caution_reasons.append(f"S&P 500 Futures soft at {sp:+.2f}%")
    if nq <= -1.25:
        caution_reasons.append(f"Nasdaq 100 Futures soft at {nq:+.2f}%")
    if oil >= 3.5:
        caution_reasons.append(f"Crude Oil elevated at {oil:+.2f}%")

    if caution_reasons:
        return "ELEVATED_CAUTION", "MONITOR_MONDAY_OPEN", caution_reasons

    return "NOMINAL", "HOLD_CALM_BULL", ["Global weekend futures & macro indicators within normal variance."]

def run_sunday_sentinel():
    if not is_valid_sunday_window():
        return

    ist_tz = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(timezone.utc).astimezone(ist_tz)
    now_str = now_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    today_display = now_ist.strftime("%d %b %Y")

    print("=" * 80)
    print("  NIFTY SUNDAY NIGHT MACRO & BLACK-SWAN PRE-FLAGGING SENTINEL (09:30 PM IST)")
    print("=" * 80)
    print(f"Timestamp: {now_str}")

    snapshot = fetch_macro_snapshot()
    risk_flag, directive, reasons = classify_weekend_risk(snapshot)
    print(f"Weekend Risk Classification: {risk_flag} | Directive: {directive}")
    for r in reasons:
        print(f" -> {r}")

    if not os.path.exists(LEDGER_FILE):
        print("Error: portfolio_ledger.json not found.")
        return

    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        ledger = json.load(f)

    ledger["weekend_sentinel"] = {
        "timestamp": now_str,
        "risk_flag": risk_flag,
        "action_directive": directive,
        "reasons": reasons,
        "macro_snapshot": snapshot
    }

    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)

    # Styling by risk flag
    if risk_flag == "CRITICAL_BLACK_SWAN":
        badge_bg, badge_fg, border_col = "#fee2e2", "#b91c1c", "#dc2626"
        headline = "🚨 CRITICAL WEEKEND MACRO SHOCK DETECTED"
    elif risk_flag == "ELEVATED_CAUTION":
        badge_bg, badge_fg, border_col = "#fef3c7", "#b45309", "#d97706"
        headline = "⚠️ ELEVATED WEEKEND MACRO CAUTION"
    else:
        badge_bg, badge_fg, border_col = "#dcfce7", "#15803d", "#10b981"
        headline = "🟢 WEEKEND MACRO NOMINAL — NO SYSTEMIC SHOCK"

    cards_html = ""
    for label, val in snapshot.items():
        chg = val["chg_pct"]
        chg_col = "#16a34a" if chg >= 0 else "#dc2626"
        cards_html += f"""
        <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:6px;padding:10px;text-align:center;">
            <div style="font-size:11px;color:#64748b;font-weight:600;">{label}</div>
            <div style="font-size:15px;font-weight:800;color:#0f172a;margin-top:3px;">{val['price']}</div>
            <div style="font-size:12px;font-weight:700;color:{chg_col};margin-top:2px;">{chg:+.2f}%</div>
        </div>
        """

    reasons_html = "".join([f"<li style='margin-bottom:4px;'>{r}</li>" for r in reasons])
    nav = ledger.get("total_account_nav", 100000.0)
    eq_pnl = ledger.get("equity_pnl", 0.0)
    eq_pnl_pct = ledger.get("equity_pnl_pct", 0.0)

    email_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; background:#0f172a; color:#1e293b; margin:0; padding:20px; }}
  .container {{ max-width:640px; margin:0 auto; background:#ffffff; border-radius:12px; border:1px solid #cbd5e1; padding:24px; }}
  .grid-3 {{ display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; margin-top:10px; }}
  .btn-link {{ background:linear-gradient(135deg,#4f46e5 0%,#3730a3 100%); color:#ffffff !important; text-decoration:none; padding:12px 24px; border-radius:8px; font-weight:700; font-size:13px; display:inline-block; }}
</style>
</head>
<body>
  <div class="container">
    <div style="border-bottom:2px solid {border_col};padding-bottom:12px;margin-bottom:16px;">
      <div style="font-size:19px;font-weight:800;color:#0f172a;">🌙 Sunday Night Macro & Black-Swan Radar</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px;">{today_display} • 09:30 PM IST • Pre-Monday Risk Handoff</div>
    </div>

    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-bottom:14px;">
      <div style="margin-bottom:8px;">
        <span style="background:{badge_bg};color:{badge_fg};padding:4px 10px;border-radius:10px;font-size:12px;font-weight:800;display:inline-block;">{headline}</span>
      </div>
      <div style="font-size:13px;color:#334155;">
        <strong>Model Handoff Directive:</strong> <code>{directive}</code>
        <ul style="margin:8px 0 0 0;padding-left:18px;font-size:12px;line-height:1.5;">{reasons_html}</ul>
      </div>
    </div>

    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-bottom:14px;">
      <div style="font-size:11px;font-weight:800;text-transform:uppercase;color:#475569;">Global Weekend Futures & Macro Snapshot</div>
      <div class="grid-3">{cards_html}</div>
    </div>

    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-bottom:16px;font-size:12px;color:#334155;">
      <strong>Monday Execution Protocol (Path A — Pure EOD HMM):</strong><br>
      • <strong>08:50 AM IST:</strong> Read-only Pre-Market Radar surfaces this weekend flag alongside live Asian cues &amp; corporate filings.<br>
      • <strong>03:15 PM IST:</strong> Single unified Hamilton Markov Regime evaluation executes on confirmed closing liquidity (zero morning whipsaw churn).<br>
      • <strong>Current Portfolio NAV:</strong> Rs. {nav:,.2f} (Pure Equity P&amp;L: {eq_pnl:+,.2f} / {eq_pnl_pct:+.2f}%)
    </div>

    <div style="text-align:center;margin:18px 0 10px 0;">
      <a href="https://nifty-portfolio-tracker.netlify.app/" target="_blank" class="btn-link">🌐 Open Live Netlify Dashboard &rarr;</a>
    </div>

    <div style="font-size:11px;color:#94a3b8;text-align:center;border-top:1px solid #e2e8f0;padding-top:10px;">
      Antigravity Quantitative Strategy Engine • Weekend Macro Surveillance
    </div>
  </div>
</body>
</html>"""

    with open(SUNDAY_HTML_FILE, "w", encoding="utf-8") as f:
        f.write(email_html)

    subj_prefix = "🚨 ALERT" if risk_flag == "CRITICAL_BLACK_SWAN" else ("⚠️ CAUTION" if risk_flag == "ELEVATED_CAUTION" else "🌙 Nominal")
    subject = f"{subj_prefix}: NIFTY Sunday Night Macro Radar ({today_display})"
    send_email_report(subject, email_html)
    print(f"[SUCCESS] Sunday Night Sentinel completed ({risk_flag}).")

if __name__ == "__main__":
    run_sunday_sentinel()
