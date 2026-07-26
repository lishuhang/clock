"""Test user-provided squido cookies directly against squido API.
Verifies that the __Secure-better-auth.session_token cookie works.
Usage: paste user's cookie value into SESSION_TOKEN variable below."""
import json
import urllib.request
import urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

# Replace with user's session_token value (URL-encoded form, as in cookies.txt)
SESSION_TOKEN = "PASTE_USER_TOKEN_HERE"
COOKIE = f"__Secure-better-auth.session_token={SESSION_TOKEN}"

def req(url, method="GET", body=None):
    h = {"User-Agent": UA, "Accept": "application/json", "Cookie": COOKIE,
         "Origin": "https://squido.ai", "Referer": "https://squido.ai/ai-image-generator"}
    data = json.dumps(body).encode() if body is not None else None
    if data: h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

print("=== get-user-info ===")
s, b = req("https://squido.ai/api/get-user-info", method="POST", body={})
print(f"status={s}, body={b[:500].decode(errors='replace')}")

print("\n=== generate image test ===")
gen_body = {
    "prompt": "a tiny red dot on white background",
    "fileUrls": [], "model": "gpt-image-2", "resolution": "1K", "ratio": "1:1",
    "remove_watermark": False, "generationMode": "text-to-image", "web_search": True, "files": []
}
s, b = req("https://squido.ai/api/generate/image", method="POST", body=gen_body)
print(f"status={s}, body={b[:500].decode(errors='replace')}")
