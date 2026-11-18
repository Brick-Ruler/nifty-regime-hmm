import urllib.request
import json

url = 'https://api.github.com/repos/Brick-Ruler/nifty-regime-hmm/actions/runs?per_page=5'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f"Total runs: {data.get('total_count')}")
        for r in data.get('workflow_runs', []):
            print(f"ID: {r['id']} | Event: {r['event']} | Status: {r['status']} | Conclusion: {r['conclusion']} | Name: {r['name']}")
except Exception as e:
    print(f"Error checking GitHub Actions: {e}")
