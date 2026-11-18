import subprocess
import json

ids = ['1a1efe7973dcd21c', '1a1eef82baa8a022', '1a1eee6845afe211', '1a1eea4f5f039277', '1a1ee9ac023dab97']
for mid in ids:
    res = subprocess.run(['gmail', 'readonly', 'get', mid, '--json'], capture_output=True, text=True, shell=True)
    try:
        data = json.loads(res.stdout)
        headers = {h['name']: h['value'] for h in data.get('payload', {}).get('headers', [])}
        print(f"Date: {headers.get('Date')} | Subject: {headers.get('Subject')}")
    except Exception as e:
        print(mid, "error:", e)
