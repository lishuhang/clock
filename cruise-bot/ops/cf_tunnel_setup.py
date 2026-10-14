#!/usr/bin/env python3
"""cruise-bot iMessage 通路：Cloudflare Tunnel 预配置（幂等，可重跑）
- 建命名隧道 cruise-imsg（远程托管配置 config_src=cloudflare）
- ingress: imsg.lishuhang.com -> http://localhost:1234 (BlueBubbles 默认端口)
- DNS: CNAME imsg.lishuhang.com -> <tunnel-id>.cfargotunnel.com (proxied)
- token 写入 scripts/.imsg_tunnel.json (chmod 600)，stdout 不回显 token
"""
import json, os, sys, urllib.request

BASE = "https://api.cloudflare.com/client/v4"
ENV = {}
with open(os.path.expanduser("~/my-project/scripts/.cruise_secrets.env")) as f:
    for line in f:
        line = line.strip()
        if line.startswith("export "):
            k, _, v = line[7:].partition("=")
            ENV[k] = v.strip().strip("'\"")
TOK, ACC = ENV["CF_TOKEN"], ENV["CF_ACC"]
ZONE = "56bc9dd890c165ae59b1a3747b65cd05"  # lishuhang.com
HOST, PORT, NAME = "imsg.lishuhang.com", 1234, "cruise-imsg"

def api(method, path, body=None):
    import subprocess
    cmd = ["curl", "-s", "-m", "30", "-X", method, BASE + path,
           "-H", f"authorization: Bearer {TOK}", "-H", "content-type: application/json"]
    if body is not None:
        cmd += ["-d", json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=40).stdout
    d = json.loads(out)
    if not d.get("success"):
        sys.exit(f"API FAIL {method} {path}: {json.dumps(d.get('errors'))[:400]}")
    return d["result"]

# 1. 隧道（幂等：先列）
tunnels = api("GET", f"/accounts/{ACC}/cfd_tunnel?is_deleted=false&per_page=50")
t = next((x for x in tunnels if x["name"] == NAME), None)
if t:
    print(f"tunnel exists: {t['id']} status={t['status']}")
else:
    t = api("POST", f"/accounts/{ACC}/cfd_tunnel", {"name": NAME, "config_src": "cloudflare"})
    print(f"tunnel created: {t['id']}")

tid = t["id"]

# 2. 远程托管 ingress
api("PUT", f"/accounts/{ACC}/cfd_tunnel/{tid}/configurations", {"config": {
    "ingress": [
        {"hostname": HOST, "service": f"http://localhost:{PORT}"},
        {"service": "http_status:404"},
    ]}})
print(f"ingress set: {HOST} -> localhost:{PORT}")

# 3. DNS CNAME（幂等：查再建）
recs = api("GET", f"/zones/{ZONE}/dns_records?type=CNAME&name={HOST}")
if recs:
    print(f"dns exists: {HOST} -> {recs[0]['content']}")
    if recs[0]["content"] != f"{tid}.cfargotunnel.com":
        api("PUT", f"/zones/{ZONE}/dns_records/{recs[0]['id']}", {
            "type": "CNAME", "name": HOST, "content": f"{tid}.cfargotunnel.com", "proxied": True})
        print("dns updated to current tunnel")
else:
    api("POST", f"/zones/{ZONE}/dns_records", {
        "type": "CNAME", "name": HOST, "content": f"{tid}.cfargotunnel.com", "proxied": True})
    print(f"dns created: {HOST} -> {tid}.cfargotunnel.com")

# 4. token 落盘（不回显）
token = api("GET", f"/accounts/{ACC}/cfd_tunnel/{tid}/token")
out = os.path.expanduser("~/my-project/scripts/.imsg_tunnel.json")
with open(out, "w") as f:
    json.dump({"tunnel_id": tid, "host": HOST, "name": NAME, "token": token}, f)
os.chmod(out, 0o600)
print(f"token saved -> {out} (len={len(token)})")
print(f"MAC 一条命令: sudo cloudflared service install <token>")
print(f"BB_BASE 将为: https://{HOST}")
