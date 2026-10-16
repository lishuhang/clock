#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v15下篇 手册批量核查（第二批：表4团队协作细节+剧本3家细读+声音段补充+表1小云雀新增）"""
import subprocess, os

MANUAL = "/home/z/my-project/materials/step3/画布手册-1009-1800"

def rg(pattern, scope=None, maxc=4, ctx=1):
    path = os.path.join(MANUAL, scope) if scope else MANUAL
    cmd = ["rg", "-i", "--no-heading", "-n", "-C", str(ctx), "--max-count", str(maxc),
           "-g", "*.md", pattern, path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return [l for l in r.stdout.splitlines() if l.strip()]
    except Exception as e:
        return [f"ERR {e}"]

def show(title, patterns, scope=None, ctx=1, maxc=4, show_n=6):
    print(f"\n{'='*70}\n### {title}\n{'='*70}")
    found = False
    for p in patterns:
        hits = rg(p, scope=scope, ctx=ctx, maxc=maxc)
        if hits:
            found = True
            for h in hits[:show_n]:
                print(f"  [{p}] {h[:240]}")
    if not found:
        print("  ❌ 无命中")

# ===== E. 表4 团队协作各家细节 =====
show("E1. TapNow 席位/3角色/SSO/团队", [r"SSO", r"席位", r"3 ?个?角色", r"团队"], scope="TapNow/TapNowCreative OS.md", maxc=6)
show("E2. TapNow 积分/额度（无限/周期/固定）", [r"积分", r"额度", r"无限", r"周期", r"固定"], scope="TapNow/TapNowCreative OS.md", maxc=8)
show("E3. TapNow 成员用量/看板", [r"用量", r"看板", r"使用量"], scope="TapNow/TapNowCreative OS.md", maxc=5)
show("E4. 纳逗Pro 团队/100人/三维看板/跨团队克隆/配额", [r"团队", r"100 ?人", r"三维", r"克隆", r"配额", r"CLI|命令行"], scope="纳逗Pro", maxc=8)
show("E5. ShotLab 协作/5人/画布共享/团队", [r"协作", r"5 ?人", r"共享", r"团队", r"协作者"], scope="ShotLab", maxc=8)
show("E6. 巨日禄 团队/二级账户/子团队/独立核算/CLI", [r"团队", r"二级", r"子团队", r"独立核算", r"CLI|命令行", r"项目管理"], scope="巨日禄", maxc=10)
show("E7. OiiOii 子账号/小组/限额", [r"子账号", r"小组", r"限额", r"团队"], scope="OiiOii", maxc=8)
show("E8. Seko 团队/多人/协作/CLI", [r"团队", r"多人", r"协作", r"CLI|命令行", r"席位"], scope="Seko", maxc=8)
show("E9. 万兴 团队/协作/多人/同屏/看板", [r"团队", r"协作", r"多人", r"同屏", r"看板", r"子账号|成员"], scope="万兴剧厂", maxc=10)
show("E10. 万兴 CLI/MCP", [r"CLI", r"MCP"], scope="万兴剧厂", maxc=6)

# ===== F. 剧本3家细读 =====
show("F1. ShotLab 分镜脚本节点（5.2.6）原文", [r"分镜脚本节点"], scope="ShotLab", maxc=3, ctx=6)
show("F2. TapNow Brainstorm 剧本（细读）", [r"Brainstorm|头脑风暴"], scope="TapNow/用 Brainstorm 找方向.md", maxc=3, ctx=3)
show("F3. AniShort 剧本相关功能", [r"剧本|脚本|情节|分段"], scope="Anishort/优化情节、智能分段、一键生成提示词.md", maxc=8)

# ===== G. 声音段补充 =====
show("G1. 小云雀 S2.5 音频/声音默认", [r"音频", r"声音", r"台词.{0,10}(有|无|不)"], scope="小云雀/小云雀 Seedance 2.5 使用手册.md", maxc=8)
show("G2. 巨日禄 声音/配音/BGM", [r"配音", r"BGM", r"音乐", r"声音", r"音频"], scope="巨日禄", maxc=8)
show("G3. AniShort 人声/背景分离/重配音", [r"人声", r"分离", r"背景", r"重配音"], scope="Anishort", maxc=8)
show("G4. 纳逗 声音分离细节", [r"声音分离"], scope="纳逗Pro", maxc=3, ctx=3)

# ===== H. 表1小云雀专业影视类新增（素模/白模/动作库/机位运镜库/帧级时间轴/轨迹WASD） =====
show("H1. 小云雀 素模/白模/动作库/机位运镜库", [r"素模", r"白模", r"动作库", r"运镜库|机位库", r"帧级", r"WASD", r"轨迹"], scope="小云雀", maxc=10)
