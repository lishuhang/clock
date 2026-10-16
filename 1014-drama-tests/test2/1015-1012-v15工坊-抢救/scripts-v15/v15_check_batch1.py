#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v15下篇 手册批量核查（第一批：声音段+主体库同步+表2细节+表3缺3家）"""
import subprocess, os, re

MANUAL = "/home/z/my-project/materials/step3/画布手册-1009-1800"

def rg(pattern, scope=None, maxc=4, ctx=0):
    path = os.path.join(MANUAL, scope) if scope else MANUAL
    cmd = ["rg", "-i", "--no-heading", "-n", "-C", str(ctx), "--max-count", str(maxc),
           "-g", "*.md", pattern, path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        return lines
    except Exception as e:
        return [f"ERR {e}"]

def show(title, patterns, scope=None, ctx=0, maxc=4):
    print(f"\n{'='*70}\n### {title}\n{'='*70}")
    found = False
    for p in patterns:
        hits = rg(p, scope=scope, ctx=ctx, maxc=maxc)
        if hits:
            found = True
            for h in hits[:6]:
                print(f"  [{p}] {h[:220]}")
    if not found:
        print("  ❌ 无命中")

show("A8. 人声/背景音分离（LibTV/纳逗/AniShort）", [r"人声", r"背景音", r"分离"], scope=None, maxc=3)
show("A9. ShotLab多轨混音", [r"混音", r"多轨"], scope="ShotLab")
show("A10. 小云雀角色音色改后全剧一键同步", [r"音色.{0,20}同步", r"一键同步", r"同步更新"], scope="小云雀")
show("A11. 纳逗人声修改后对口型", [r"对口型", r"口型"], scope="纳逗Pro")

# ============ B. 主体库改动同步（其他家） ============
show("B1. 主体改动后引用同步更新（各家）", [r"同步更新", r"自动更新", r"跟着.{0,6}(换|更新)", r"全部更新", r"联动更新", r"一处修改"], scope=None, maxc=3)

# ============ C. 表2用户改动相关 ============
show("C1. 纳逗宫格数量（10种vs十余种）", [r"宫格"], scope="纳逗Pro", maxc=8)
show("C2. ShotLab人像锁定算法/特征库", [r"锁定", r"特征库", r"合规"], scope="ShotLab")
show("C3. LibTV AutoLink/5-30秒音频生成音色", [r"AutoLink", r"自动连线", r"5-30", r"音频.{0,10}音色"], scope="LibTV")
show("C4. OiiOii角色设计师Agent/演员库", [r"角色设计师", r"演员库"], scope="OiiOii")
show("C5. Seko智能推荐参考图", [r"推荐", r"参考图"], scope="Seko", maxc=5)

# ============ D. 表3缺3家剧本能力 ============
show("D1. ShotLab剧本/分镜能力", [r"剧本", r"分镜", r"脚本"], scope="ShotLab", maxc=8)
show("D2. TapNow剧本/分镜能力", [r"剧本", r"分镜", r"脚本"], scope="TapNow", maxc=8)
show("D3. AniShort剧本/分镜能力", [r"剧本", r"分镜", r"脚本"], scope="Anishort", maxc=8)
