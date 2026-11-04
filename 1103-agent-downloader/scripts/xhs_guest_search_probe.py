#!/usr/bin/env python3
"""小红书游客搜索探针: RedCrack 纯Python签名, 免登录免JS (mankezhou/RedCrack MIT)
预期: 搜索可能 -104 未登录无权限 (skill 文档已预警), 需实测确认
"""
import asyncio, json, sys, os
os.chdir("/tmp/RedCrack")  # config.py 用相对路径读 ini, 必须 cwd=RedCrack
sys.path.insert(0, "/tmp/RedCrack")
from request.web.xhs_session import create_xhs_session

async def main():
    kw = sys.argv[1] if len(sys.argv) > 1 else "万智牌"
    out = {"steps": []}
    try:
        xhs = await create_xhs_session(proxy=None)
        out["steps"].append("guest_session_created")
        print("[OK] guest session created")
        res = await xhs.apis.note.search_notes(kw)
        txt = await res.text()
        try:
            j = json.loads(txt)
            code = j.get("code")
            success = j.get("success")
            print(f"[{'OK' if success else 'FAIL'}] search_notes({kw}): success={success} code={code}")
            items = (j.get("data") or {}).get("items") or []
            print(f"items={len(items)}")
            if items:
                for it in items[:8]:
                    n = it.get("note_card", {}) or it
                    print(json.dumps({
                        "note_id": it.get("id") or n.get("note_id"),
                        "title": n.get("display_title", "")[:30],
                        "type": n.get("type"),
                        "xsec_token": (it.get("xsec_token") or "")[:20] + "...",
                        "user": (n.get("user") or {}).get("nickname", ""),
                        "liked": (n.get("interact_info") or {}).get("liked_count", ""),
                    }, ensure_ascii=False))
            out["search_raw_head"] = txt[:800]
        except Exception:
            print(f"[FAIL] non-json: {txt[:300]}")
            out["search_raw_head"] = txt[:800]
        await xhs.close_session()
    except Exception as e:
        print(f"[FAIL] EXC {type(e).__name__}: {e}")
        out["steps"].append(f"EXC {type(e).__name__}: {e}")
    with open("/home/z/my-project/logs/xhs_guest_search.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("RESULT=/home/z/my-project/logs/xhs_guest_search.json")

asyncio.run(main())
