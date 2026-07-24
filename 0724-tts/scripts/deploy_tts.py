#!/usr/bin/env python3
"""Deploy TTS Voice Lab worker to Cloudflare Workers.
Usage: python3 deploy_tts.py [path/to/worker.js]
       python3 deploy_tts.py   (defaults to latest v2.19)
"""
import urllib.request, ssl, os, json, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SECRETS_PATH = '/home/z/my-project/.secrets'
DEFAULT_WORKER = os.path.join(SCRIPT_DIR, '..', 'tts-voice-lab-v2.19.js')
WORKER_NAME = 'tts-voice-lab'

# Read secrets
secrets = {}
secrets_file = os.environ.get('SECRETS_PATH', SECRETS_PATH)
if os.path.exists(secrets_file):
    with open(secrets_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                secrets[k.strip()] = v.strip()

CF_API_TOKEN = os.environ.get('CLOUDFLARE_API_TOKEN', '') or secrets.get('CLOUDFLARE_TOKEN', '')
ACCOUNT_ID = os.environ.get('CLOUDFLARE_ACCOUNT_ID', '') or secrets.get('CLOUDFLARE_ACCOUNT_ID', '')
WORKER_FILE = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WORKER

if not CF_API_TOKEN or not ACCOUNT_ID:
    print('ERROR: Missing CLOUDFLARE_TOKEN and/or CLOUDFLARE_ACCOUNT_ID')
    print(f'  Set them in {secrets_file} or as environment variables')
    print(f'  Format: CLOUDFLARE_TOKEN=your_api_token')
    print(f'          CLOUDFLARE_ACCOUNT_ID=your_account_id')
    sys.exit(1)

print(f'Deploying {WORKER_FILE}')
print(f'  -> worker "{WORKER_NAME}"')
print(f'  -> account {ACCOUNT_ID}')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def cf_request(method, path, body=None, content_type='application/json'):
    url = f'https://api.cloudflare.com/client/v4{path}'
    headers = {'Authorization': f'Bearer {CF_API_TOKEN}', 'Content-Type': content_type}
    data = body.encode('utf8') if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
            return r.status, r.read().decode('utf8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf8')

with open(WORKER_FILE, 'r', encoding='utf8') as f:
    worker_code = f.read()
print(f'Worker code: {len(worker_code)} bytes')

boundary = '----cf-deploy-' + os.urandom(8).hex()
metadata = json.dumps({"main_module": "worker.js", "compatibility_date": "2024-01-01"})
body_parts = []
body_parts.append(f'--{boundary}\r\n'.encode())
body_parts.append(b'Content-Disposition: form-data; name="metadata"\r\n')
body_parts.append(b'Content-Type: application/json\r\n\r\n')
body_parts.append(metadata.encode() + b'\r\n')
body_parts.append(f'--{boundary}\r\n'.encode())
body_parts.append(b'Content-Disposition: form-data; name="worker.js"; filename="worker.js"\r\n')
body_parts.append(b'Content-Type: application/javascript+module\r\n\r\n')
body_parts.append(worker_code.encode('utf8') + b'\r\n')
body_parts.append(f'--{boundary}--\r\n'.encode())
body = b''.join(body_parts)

status, resp = cf_request('PUT', f'/accounts/{ACCOUNT_ID}/workers/scripts/{WORKER_NAME}',
                          body=body, content_type=f'multipart/form-data; boundary={boundary}')
print(f'Upload: HTTP {status}')
if status != 200:
    print(f'Failed: {resp[:1000]}')
    sys.exit(1)
try:
    r = json.loads(resp)
    if r.get('success'):
        print(f'Success: deployed {r["result"].get("id")}')
    else:
        print(f'CF reported failure: {r}')
except Exception as e:
    print(f'Parse error: {e}')

status2, resp2 = cf_request('POST', f'/accounts/{ACCOUNT_ID}/workers/scripts/{WORKER_NAME}/subdomain',
                            body=json.dumps({"enabled": True}))
print(f'Subdomain enable: HTTP {status2}')
if status2 == 200:
    print(f'Live at: https://{WORKER_NAME}.lishuhang.workers.dev')
