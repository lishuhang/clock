#!/usr/bin/env python3
"""Deep-dive on the 3 services that have working APIs:
- guerrillamail
- tempmail.lol
- internal.temp-mail.io

Plus retest mail.tm with proper Accept header (was 406 due to format).
For each: actually create a mailbox, list messages, test domain against squido.
"""
import json
import re
import time
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, headers=None, method="GET", body=None, timeout=20):
    h = {"User-Agent": UA, "Accept": "application/ld+json,application/json"}
    if headers:
        h.update(headers)
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        else:
            data = body.encode()
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return 0, {}, str(e).encode()

results = {}

# ============ 1. mail.tm (retry with proper Accept header) ============
print("\n" + "="*60)
print("1. mail.tm")
print("="*60)
base = "https://api.mail.tm"
# Get domains first
s, h, b = fetch(base + "/domains?page=1")
print(f"GET /domains: status={s}")
print(f"  body: {b[:400].decode(errors='replace')}")
mailtm_domains = []
try:
    j = json.loads(b)
    if "hydra:member" in j:
        for d in j["hydra:member"]:
            mailtm_domains.append(d["domain"])
    elif isinstance(j, list):
        for d in j:
            mailtm_domains.append(d["domain"])
except Exception as e:
    print(f"  parse err: {e}")
print(f"  Available domains: {mailtm_domains}")

if mailtm_domains:
    # Try to create account
    username = f"probe{int(time.time())%1000000}"
    email = f"{username}@{mailtm_domains[0]}"
    password = "ProbePass123!"
    print(f"\nCreating mailbox: {email}")
    s, h, b = fetch(base + "/accounts", method="POST",
                   body={"address": email, "password": password})
    print(f"POST /accounts: status={s}")
    print(f"  body: {b[:400].decode(errors='replace')}")
    if s in (200, 201):
        # Get auth token
        s2, h2, b2 = fetch(base + "/token", method="POST",
                          body={"address": email, "password": password})
        print(f"POST /token: status={s2}")
        print(f"  body: {b2[:300].decode(errors='replace')}")
        try:
            tok = json.loads(b2).get("token")
            if tok:
                # List messages
                s3, h3, b3 = fetch(base + "/messages?page=1",
                                  headers={"Authorization": f"Bearer {tok}"})
                print(f"GET /messages: status={s3}")
                print(f"  body: {b3[:200].decode(errors='replace')}")
        except Exception as e:
            print(f"  token err: {e}")

    results["mail.tm"] = {
        "domains": mailtm_domains,
        "create_email": email,
        "create_status": s,
    }

# ============ 2. guerrillamail ============
print("\n" + "="*60)
print("2. guerrillamail")
print("="*60)
base = "https://api.guerrillamail.com/ajax.php"
# Get email address
s, h, b = fetch(base + "?f=get_email_address&lang=en")
print(f"GET get_email_address: status={s}")
print(f"  body: {b[:400].decode(errors='replace')}")
gm_email = None
gm_sid = None
try:
    j = json.loads(b)
    gm_email = j.get("email_addr")
    gm_sid = j.get("sid_token")
    print(f"  email: {gm_email}")
    print(f"  sid: {gm_sid}")
except Exception:
    pass

# Check available domains
s, h, b = fetch(base + "?f=get_email_list&offset=0&sid_token=" + (gm_sid or ""))
print(f"GET get_email_list: status={s}, body={b[:200].decode(errors='replace')}")

# Set email user (to control the username)
if gm_sid:
    custom_user = f"probe{int(time.time())%1000000}"
    s, h, b = fetch(base + f"?f=set_email_user&email_user={custom_user}&sid_token={gm_sid}&lang=en")
    print(f"\nSet custom user '{custom_user}': status={s}")
    print(f"  body: {b[:300].decode(errors='replace')}")

results["guerrillamail"] = {
    "email": gm_email,
    "sid": gm_sid,
    "domains_tested": True,
}

# ============ 3. tempmail.lol ============
print("\n" + "="*60)
print("3. tempmail.lol")
print("="*60)
base = "https://api.tempmail.lol"
# Create inbox
s, h, b = fetch(base + "/v2/inbox/create", method="POST")
print(f"POST /v2/inbox/create: status={s}")
print(f"  body: {b[:500].decode(errors='replace')}")
tml_address = None
tml_token = None
try:
    j = json.loads(b)
    if isinstance(j, list) and j:
        tml_address = j[0].get("address")
        tml_token = j[0].get("token")
    elif "address" in j:
        tml_address = j.get("address")
        tml_token = j.get("token")
    print(f"  address: {tml_address}")
    print(f"  token: {tml_token}")
except Exception as e:
    print(f"  parse err: {e}")

# Check inbox
if tml_token:
    s, h, b = fetch(base + f"/v2/inbox/{tml_token}")
    print(f"GET /v2/inbox/{{token}}: status={s}")
    print(f"  body: {b[:300].decode(errors='replace')}")

results["tempmail.lol"] = {
    "address": tml_address,
    "token": tml_token,
}

# ============ 4. internal.temp-mail.io ============
print("\n" + "="*60)
print("4. internal.temp-mail.io")
print("="*60)
base = "https://api.internal.temp-mail.io/api/v3"
# Create new email
s, h, b = fetch(base + "/email/new", method="POST", body={})
print(f"POST /email/new: status={s}")
print(f"  body: {b[:500].decode(errors='replace')}")
tmio_email = None
try:
    j = json.loads(b)
    tmio_email = j.get("email")
    print(f"  email: {tmio_email}")
except Exception:
    pass

# List messages
if tmio_email:
    s, h, b = fetch(base + f"/email/{tmio_email}/messages")
    print(f"GET /email/{{addr}}/messages: status={s}")
    print(f"  body: {b[:200].decode(errors='replace')}")

results["internal.temp-mail.io"] = {
    "email": tmio_email,
}

# ============ 5. Test each domain against squido.ai's email validator ============
print("\n" + "="*60)
print("5. Test disposable email domains against squido.ai's send-email-otp endpoint")
print("="*60)
# Collect all candidate emails from all services
candidates = []
if mailtm_domains:
    for d in mailtm_domains[:3]:
        candidates.append(("mail.tm:"+d, f"probe{int(time.time())%100000}@{d}"))
if gm_email:
    candidates.append(("guerrillamail", gm_email))
    # Also try the @guerrillamailblock.com and @grr.la variants
    for d in ["guerrillamail.com", "guerrillamailblock.com", "grr.la", "sharklasers.com"]:
        candidates.append(("guerrillamail:"+d, f"probe{int(time.time())%100000}@{d}"))
if tml_address:
    candidates.append(("tempmail.lol", tml_address))
if tmio_email:
    candidates.append(("internal.temp-mail.io", tmio_email))

# Also test some well-known disposable domains directly to see if squido blocks them
for d in ["1secmail.com", "1secmail.net", "1secmail.org", "wwjmp.com",
         "esiix.com", "kzcc.com", "icznn.com",
         "yopmail.com", "mailinator.com", "tempmail.com",
         "discard.email", "fakeinbox.com", "10minutemail.com",
         "temp-mail.org", "dispostable.com", "maildrop.cc",
         "mintemail.com", "getnada.com", "moakt.com"]:
    candidates.append(("known:"+d, f"probe{int(time.time())%100000}@{d}"))

squido_results = []
for label, email in candidates:
    s, h, b = fetch("https://squido.ai/api/auth/send-email-otp", method="POST", body={"email": email})
    body_str = b[:200].decode(errors="replace").replace("\n", " ")
    # Extract the error or success
    err = "?"
    try:
        j = json.loads(b)
        err = j.get("error", j.get("success", "?"))
    except Exception:
        pass
    squido_results.append({"label": label, "email": email, "status": s, "error": err})
    print(f"  {label:35s} {email[:40]:40s} status={s} err={err}")
    time.sleep(0.5)

results["squido_email_test"] = squido_results

# Save
with open("/home/z/my-project/download/disposable-email-deep-research.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n\n=== Summary: which disposable email services work end-to-end on squido? ===")
working = [r for r in squido_results if r["error"] != "Invalid email address" and r["status"] == 200]
print(f"Services that pass squido's email validation ({len(working)}/{len(squido_results)}):")
for w in working:
    print(f"  {w['label']:35s}  {w['email']}")
