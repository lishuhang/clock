# -*- coding: utf-8 -*-
"""打包 keepitrun-v1.29.zip（14 成员、正斜杠路径、确定性顺序）并执行凭据扫描。"""
import hashlib
import os
import re
import sys
import zipfile

PKG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work-v129")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "keepitrun-v1.29.zip")

MEMBERS = [
    ".env.example",
    "01_getrss.py",
    "02_combine-gemini.py",
    "03_convert-daily.py",
    "04_convert-blog.py",
    "05_photos-update.py",
    "90_cleanup-daily-from-blog.py",
    "91_compress-images.py",
    "92_model-process.py",
    "image_routing.py",
    "keepitrun.py",
    "keywords.json",
    "readme.md",
    "rss_feeds.json",
]

# 凭据模式：真实 token 形态（占位符 ghp_xxxxx / your_github_token_here 应豁免）
CREDS_PATTERNS = [
    (r"ghp_[A-Za-z0-9]{20,}", "GitHub PAT 形态"),
    (r"gh_[A-Za-z0-9]{20,}", "GitHub fine-grained 形态"),
    (r"cfat_[A-Za-z0-9_\-]{20,}", "Cloudflare token 形态"),
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI 形态 key"),
    (r"AIzaSy[A-Za-z0-9_\-]{30,}", "Google API key 形态"),
    (r"(?i)(api[_-]?key|secret|password|cookie)\s*[:=]\s*['\"]?[A-Za-z0-9+/]{24,}", "疑似实值凭据赋值"),
]
PLACEHOLDER_OK = re.compile(r"ghp_xxxxx|your_github_token_here|ghp_\*+|\*{3,}")


def main():
    # 成员清点：必须恰为 14 项，不多不少
    actual = sorted(f for f in os.listdir(PKG) if not f.startswith("__pycache__") and f != "__pycache__")
    actual = [f for f in actual if os.path.isfile(os.path.join(PKG, f))]
    if sorted(MEMBERS) != actual:
        print("成员清单不符!")
        print("期望:", sorted(MEMBERS))
        print("实际:", actual)
        return 1
    print(f"[PASS] 成员清点: {len(MEMBERS)} 项，与 §5.3 打包清单一致")

    # 打包：正斜杠、固定顺序、去多余属性
    if os.path.exists(OUT):
        os.remove(OUT)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in MEMBERS:
            src = os.path.join(PKG, name)
            with open(src, "rb") as fh:
                data = fh.read()
            info = zipfile.ZipInfo(name.replace(os.sep, "/"))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)
    print(f"[PASS] 打包完成: {os.path.abspath(OUT)}")

    # 复核：成员数 / 路径分隔符 / 禁入项
    with zipfile.ZipFile(OUT) as zf:
        names = zf.namelist()
        assert len(names) == 14, names
        assert all("\\" not in n for n in names), "存在反斜杠路径"
        forbidden = [n for n in names if n == ".env" or n.endswith((".log", ".pyc", ".tmp"))
                     or "memory" in n or "task_completion" in n or n.startswith(("logs/", "tmp/", "scripts/"))]
        assert not forbidden, f"禁入项: {forbidden}"
        print("[PASS] 包内复核: 14 成员 / 正斜杠 / 无 .env·日志·缓存·记忆文件·测试脚本")
        # 凭据扫描（内容级）
        hits = []
        for name in names:
            text = zf.read(name).decode("utf-8", errors="replace")
            for pat, label in CREDS_PATTERNS:
                for mm in re.finditer(pat, text):
                    seg = text[max(0, mm.start()-20):mm.end()+20]
                    if PLACEHOLDER_OK.search(seg) or "xxxxx" in mm.group(0):
                        label += "（占位示例串，豁免）"
                    hits.append((name, label, mm.group(0)[:14] + "…"))
        if hits:
            for name, label, frag in hits:
                print(f"  [HIT] {name}: {label}: {frag}")
        else:
            print("[PASS] 包内凭据扫描: 零命中")

    size = os.path.getsize(OUT)
    sha = hashlib.sha256(open(OUT, "rb").read()).hexdigest().upper()
    print(f"\nkeepitrun-v1.29.zip  {size:,} bytes")
    print(f"SHA-256: {sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
