#!/usr/bin/env python3
"""Test 1secmail API in detail — it's a pure GET API, no auth needed.
Also test if its domains pass squido validation.
Then test the guerrillamail API in detail."""
import json
import re
import time
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

def fetch(url, headers=None, method="GET", body=None, timeout=15):
    h = {"User-Agent": UA, "Accept": "application/json"}
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

# ============ 1secmail — but it returned 403 earlier, retry ============
print("="*60)
print("1secmail API test")
print("="*60)

# 1secmail API uses simple GET
for endpoint in [
    "https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=5",
    "https://www.1secmail.com/api/v1/?action=getDomainList",
    "https://www.1secmail.com/api/v1/?action=getMessages&username=test&domain=1secmail.com",
]:
    s, h, b = fetch(endpoint)
    print(f"  {endpoint}")
    print(f"    status={s}, body={b[:200].decode(errors='replace')}")
    print()

# ============ internal.temp-mail.io — full flow test ============
print("="*60)
print("internal.temp-mail.io — full flow test (create, list)")
print("="*60)

# Create 10 mailboxes rapidly
mailboxes = []
for i in range(10):
    s, h, b = fetch("https://api.internal.temp-mail.io/api/v3/email/new", method="POST", body={})
    if s == 200:
        j = json.loads(b)
        mailboxes.append({"email": j["email"], "token": j["token"]})
        print(f"  [{i}] {j['email']}")
    elif s == 429:
        print(f"  [{i}] rate limited!")
        break
    else:
        print(f"  [{i}] status={s}")
    # NO delay — test true rate
print(f"\n  Total created: {len(mailboxes)}/10")

# Check each mailbox's messages
print("\n  Listing messages for each:")
for m in mailboxes[:3]:
    s, h, b = fetch(f"https://api.internal.temp-mail.io/api/v3/email/{m['email']}/messages")
    print(f"    {m['email']}: status={s}, body={b[:200].decode(errors='replace')}")
    time.sleep(0.2)

# Test the temp-mail.io domains against squido
print("\n  Testing temp-mail.io domains against squido:")
test_domains = set()
for m in mailboxes:
    d = m["email"].split("@")[1]
    test_domains.add(d)
print(f"    Unique domains from 10 mailboxes: {sorted(test_domains)}")

for d in sorted(test_domains):
    test_email = f"probe{int(time.time())%100000}@{d}"
    s, h, b = fetch("https://squido.ai/api/auth/send-email-otp",
                   method="POST", body={"email": test_email})
    err = "?"
    try:
        j = json.loads(b)
        err = j.get("error", j.get("success", "?"))
    except Exception:
        pass
    print(f"    {d:30s} → status={s}, err={err}")
    time.sleep(0.3)

# ============ tempmail.lol — already tested, expand ============
print("\n" + "="*60)
print("tempmail.lol — domains test")
print("="*60)
domains_seen = set()
for i in range(5):
    s, h, b = fetch("https://api.tempmail.lol/v2/inbox/create", method="POST")
    if s == 201:
        j = json.loads(b)
        # Could be list or dict
        if isinstance(j, list):
            for item in j:
                addr = item.get("address", "")
                if "@" in addr:
                    domains_seen.add(addr.split("@")[1])
        elif "address" in j:
            addr = j["address"]
            if "@" in addr:
                domains_seen.add(addr.split("@")[1])
    time.sleep(0.5)

print(f"  Unique domains: {sorted(domains_seen)}")

# Test these against squido
print("\n  Testing tempmail.lol domains against squido:")
for d in sorted(domains_seen):
    test_email = f"probe{int(time.time())%100000}@{d}"
    s, h, b = fetch("https://squido.ai/api/auth/send-email-otp",
                   method="POST", body={"email": test_email})
    err = "?"
    try:
        j = json.loads(b)
        err = j.get("error", j.get("success", "?"))
    except Exception:
        pass
    print(f"    {d:35s} → status={s}, err={err}")
    time.sleep(0.3)

# ============ mail.tm — how many domains are there? ============
print("\n" + "="*60)
print("mail.tm — all available domains")
print("="*60)
s, h, b = fetch("https://api.mail.tm/domains?page=1",
               headers={"Accept": "application/ld+json"})
print(f"  status={s}")
try:
    j = json.loads(b)
    if "hydra:member" in j:
        for d in j["hydra:member"]:
            print(f"    {d['domain']}  active={d.get('isActive')}  private={d.get('isPrivate')}")
    elif isinstance(j, list):
        for d in j:
            print(f"    {d['domain']}  active={d.get('isActive')}")
except Exception as e:
    print(f"  parse err: {e}")

# Test mail.tm domain rotation - if 2/minute limit, can we use multiple domains?
print("\n  Test: create 5 mailboxes across different mail.tm domains (if any):")
time.sleep(60)  # wait for rate limit to reset
mailtm_domains_test = []
s, h, b = fetch("https://api.mail.tm/domains?page=1",
               headers={"Accept": "application/ld+json"})
if s == 200:
    j = json.loads(b)
    if "hydra:member" in j:
        for d in j["hydra:member"]:
            mailtm_domains_test.append(d["domain"])

print(f"    Available domains: {mailtm_domains_test}")

# Try to create one mailbox per domain
for d in mailtm_domains_test[:3]:
    username = f"probe{int(time.time())%100000}"
    s2, h2, b2 = fetch("https://api.mail.tm/accounts", method="POST",
                      body={"address": f"{username}@{d}", "password": "Test12345!"},
                      headers={"Accept": "application/ld+json"})
    print(f"    {d}: status={s2}")
    if s2 == 429:
        print(f"      rate limited, sleeping 60s")
        time.sleep(60)
    time.sleep(0.3)
