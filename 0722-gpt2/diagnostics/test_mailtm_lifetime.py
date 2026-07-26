"""Test mail.tm account lifecycle — does the JWT expire? When does the account get cleaned?"""
import json
import urllib.request
import urllib.error
import base64
import time

UA = "Mozilla/5.0 Chrome"

def req(url, method="GET", body=None, headers=None, accept="application/ld+json"):
    h = {"User-Agent": UA, "Accept": accept}
    if headers: h.update(headers)
    data = json.dumps(body).encode() if body is not None else None
    if data: h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

# Step 1: Create test account
username = f"pooltest{int(time.time())%100000}"
email = f"{username}@web-library.net"
password = "PoolTest123!"
print(f"Creating: {email}")
s, b = req("https://api.mail.tm/accounts", method="POST", body={"address": email, "password": password})
print(f"  create: status={s}")
account_id = json.loads(b).get("id") if s == 201 else None

# Step 2: Get JWT
s, b = req("https://api.mail.tm/token", method="POST", body={"address": email, "password": password})
jwt = json.loads(b).get("token")
print(f"  JWT: {jwt[:50]}...")

# Step 3: Decode JWT to check for exp field
payload_b64 = jwt.split(".")[1]
payload_b64 += "=" * (4 - len(payload_b64) % 4)
payload = json.loads(base64.urlsafe_b64decode(payload_b64))
print(f"\nJWT payload:")
print(json.dumps(payload, indent=2))
print(f"\nHas exp field: {'exp' in payload}")
print(f"iat (issued): {time.ctime(payload['iat'])}")
# If no exp field, JWT itself doesn't expire (server-side policy may still delete)

# Step 4: Check account info
s, b = req(f"https://api.mail.tm/accounts/{account_id}",
          headers={"Authorization": f"Bearer {jwt}"})
print(f"\nAccount info:")
print(json.dumps(json.loads(b), indent=2, ensure_ascii=False)[:600])
