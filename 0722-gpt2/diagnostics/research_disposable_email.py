#!/usr/bin/env python3
"""Research 1: Disposable email services that have public APIs.

For each service, check:
- Has a public API (REST/JSON, no auth required)
- Allows programmatic mailbox creation
- Allows programmatic message retrieval
- Domain(s) not blocked by common anti-spam (we'll test against squido.ai separately)
- Rate limits (free tier)
- Reliability (uptime, age of service)

Compare to mail.tm which we already know works.
"""
import json
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

# Known disposable email services with public APIs
SERVICES = [
    # (name, api_base, mailbox_create_path, mailbox_list_path, notes)
    ("mail.tm", "https://api.mail.tm", "/accounts", "/messages", "Popular, free, REST API, well-documented"),
    ("mail.gw", "https://api.mail.gw", "/accounts", "/messages", "mail.tm fork, same API"),
    ("1secmail", "https://www.1secmail.com/api/v1", "?action=genRandomMailbox", "?action=getMessages", "Simple GET-only API, no auth"),
    ("guerrillamail", "https://api.guerrillamail.com/ajax.php", "?f=get_email_address", "?f=check_email", "Long-running service, has rate limit"),
    ("tempmail.lol", "https://api.tempmail.lol", "/v2/inbox/create", "/v2/inbox/<token>", "Has official API, requires token"),
    ("internal.temp-mail.io", "https://api.internal.temp-mail.io/api/v3", "/email/new", "/email/<addr>/messages", "REST API, no auth"),
    ("disposable-email.ml", "https://disposable-email.ml/api", "/v1/mailbox", "/v1/mailbox/<addr>", "Smaller service, may be down"),
    ("mailcatch.com", "https://mailcatch.com", "/en/disposable-mailbox", None, "Has REST but limited"),
    ("mohmal.com", "https://www.mohmal.com/en", None, None, "Web-only, no API"),
    ("tempinbox.com", "https://tempinbox.com", None, None, "Web-only"),
    ("maildrop.cc", "https://api.maildrop.cc/graphql", None, None, "GraphQL API, no auth"),
    ("ethereal.email", "https://ethereal.email", None, None, "Nodemailer test service, requires SMTP login"),
    ("yopmail.com", "https://yopmail.com", None, None, "Web-only, well-known"),
    ("mailinator.com", "https://www.mailinator.com", None, None, "Public inboxes but premium API"),
]

results = []

for name, base, create_path, list_path, notes in SERVICES:
    print(f"\n=== {name} ===")
    print(f"  URL: {base}")
    print(f"  Notes: {notes}")

    info = {"name": name, "base": base, "create_path": create_path,
            "list_path": list_path, "notes": notes}

    # Test 1: API root reachability
    s, h, b = fetch(base)
    info["root_status"] = s
    info["root_body_len"] = len(b)
    print(f"  Root: status={s}, len={len(b)}")

    # Test 2: try create mailbox
    if create_path and create_path.startswith("?"):
        # GET-style API (like 1secmail)
        url = base + create_path
        s, h, b = fetch(url)
        info["create_status"] = s
        info["create_response"] = b[:300].decode(errors="replace")
        print(f"  Create (GET): status={s}, body={b[:200].decode(errors='replace')}")
    elif create_path and create_path.startswith("/"):
        # POST-style API (like mail.tm)
        # Try simple POST with random username
        username = f"test{int(time.time())%100000}"
        url = base + create_path
        # mail.tm requires address+password
        s, h, b = fetch(url, method="POST",
                       body={"address": f"{username}@example.com", "password": "testpass123"})
        info["create_status"] = s
        info["create_response"] = b[:300].decode(errors="replace")
        print(f"  Create (POST): status={s}, body={b[:200].decode(errors='replace')}")

        # Also try /domains to see what domains are available
        s2, h2, b2 = fetch(base + "/domains?page=1")
        info["domains_status"] = s2
        info["domains_response"] = b2[:500].decode(errors="replace")
        print(f"  Domains: status={s2}, body={b2[:300].decode(errors='replace')}")
    else:
        info["create_status"] = "no_api"
        print(f"  Create: no API path defined")

    # Test 3: list messages (just probe the path)
    if list_path and "?" in list_path:
        # 1secmail-style
        url = base + list_path + "&username=test123&domain=1secmail.com"
        s, h, b = fetch(url)
        info["list_status"] = s
        print(f"  List (GET): status={s}, body={b[:200].decode(errors='replace')}")
    elif list_path and "<" in list_path:
        # placeholder-style
        url = base + list_path.replace("<addr>", "test@example.com").replace("<token>", "test")
        s, h, b = fetch(url)
        info["list_status"] = s
        print(f"  List (probe): status={s}")

    results.append(info)
    time.sleep(0.3)

# Save to file
with open("/home/z/my-project/download/disposable-email-services-research.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n\n=== SUMMARY ===")
print(f"{'Service':25s} {'Root':6s} {'Create':8s} {'Has API':10s}")
print("-" * 60)
for r in results:
    api = "YES" if r.get("create_status") not in (0, "no_api", None) and r.get("create_status", 0) in (200, 201) else "NO"
    print(f"{r['name']:25s} {str(r.get('root_status', '?')):6s} {str(r.get('create_status', '?')):8s} {api:10s}")
