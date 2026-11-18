"""
Zerodha Kite Connect Session Setup Tool
Interactive utility to generate and store your daily Kite Connect access token.
Zero trading permissions are used — only market quote reading.
"""
import os
import json
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(BASE_DIR, "kite_session.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")

def setup_kite_session():
    print("=" * 70)
    print("       ZERODHA KITE CONNECT L1 LIVE FEED SETUP (READ-ONLY)       ")
    print("=" * 70)
    
    api_key = os.environ.get("KITE_API_KEY")
    api_secret = os.environ.get("KITE_API_SECRET")

    # Check local .env if available
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        if k == "KITE_API_KEY" and not api_key:
                            api_key = v.strip()
                        elif k == "KITE_API_SECRET" and not api_secret:
                            api_secret = v.strip()
        except Exception:
            pass

    if not api_key:
        api_key = input("Enter your Zerodha Kite API Key: ").strip()
    if not api_secret:
        api_secret = input("Enter your Zerodha Kite API Secret: ").strip()

    if not api_key or not api_secret:
        print("[ERROR] Both API Key and API Secret are required.")
        return

    from kiteconnect import KiteConnect
    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()

    print("\n[STEP 1] Please authorize your session by opening this URL:")
    print("-" * 70)
    print(login_url)
    print("-" * 70)

    try:
        webbrowser.open(login_url)
    except Exception:
        pass

    print("\n[STEP 2] After logging in, you will be redirected to your registered redirect URL.")
    print("Example: https://127.0.0.1/?request_token=XXXXXX&action=login&status=success")
    request_token = input("\nEnter the 'request_token' from that URL: ").strip()

    # Extract request_token if user pasted entire URL
    if "request_token=" in request_token:
        request_token = request_token.split("request_token=")[1].split("&")[0].strip()

    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        print("\n[SUCCESS] Zerodha Kite Connect session generated successfully!")
        print(f"User ID: {data.get('user_id')} | User Name: {data.get('user_name')}")

        # Save session to local kite_session.json (strictly gitignored)
        session_data = {
            "api_key": api_key,
            "api_secret": api_secret,
            "access_token": access_token,
            "user_id": data.get("user_id"),
            "user_name": data.get("user_name"),
            "login_time": data.get("login_time")
        }
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)

        print(f"[INFO] Saved session credentials to {SESSION_FILE} (protected by .gitignore).")
        print("\nTesting quote fetch right now...")
        from zerodha_feed import fetch_kite_quotes
        quotes = fetch_kite_quotes()
        if quotes:
            print(f"[VERIFIED] Successfully pulled live quotes for {len(quotes.get('stocks', {}))} stocks directly from NSE!")

    except Exception as e:
        print(f"\n[ERROR] Failed to generate session: {e}")

if __name__ == "__main__":
    setup_kite_session()
