import urllib.request
import json
from datetime import datetime, timezone

url = 'https://api.github.com/repos/Brick-Ruler/nifty-regime-hmm/actions/runs?per_page=20'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f"Total runs: {data.get('total_count')}")
        for r in data.get('workflow_runs', []):
            created_utc = r['created_at']
            # convert to IST
            dt = datetime.fromisoformat(created_utc.replace('Z', '+00:00'))
            ist_time = dt.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            print(f"{created_utc} ({r['id']}) | Event: {r['event']} | Name: {r['name']}")
except Exception as e:
    print(f"Error: {e}")
