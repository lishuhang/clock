#!/usr/bin/env python3
"""v15下篇: VLM识别真机取证截图 r2/r3系列 + 01c：万兴宣传视频页(多光标/看板/子账号)、Seko订阅、TapNow企业版、AniShort充值、LibTV VIP、巨日禄项目页"""
import asyncio, base64, os
from zai_web_dev_sdk import ZaiClient

BASE = "/home/z/my-project/evidence/v15-team-check"
IMAGES = {
    "r2-reelmate-path-mcp-cli-万兴宣传": {
        "p": f"{BASE}/r2-reelmate-path-mcp-cli.png",
        "q": "这是万兴剧厂(reelmate.cn)相关页面截图（可能来自官方宣传视频页面）。请仔细读图：1)页面标题/品牌名是什么？2)页面上提到哪些功能（特别找：多光标同屏/多人协作/团队看板/用量管理/子账号管理/MCP/CLI/团队管理）？3)逐条列出页面可见文字原文。看不清就说看不清。",
    },
    "r2-reelmate-path-member-万兴成员": {
        "p": f"{BASE}/r2-reelmate-path-member.png",
        "q": "这是万兴剧厂(reelmate.cn)相关页面截图。请仔细读图：1)页面标题/板块名是什么？2)是否提到成员管理/子账号/席位/团队？3)逐条列出页面可见文字原文。",
    },
    "r2-reelmate-path-subscription-万兴订阅": {
        "p": f"{BASE}/r2-reelmate-path-subscription.png",
        "q": "这是万兴剧厂(reelmate.cn)相关页面截图。请仔细读图：1)页面标题/板块名是什么？2)是否提到订阅/会员/团队版档位？3)逐条列出页面可见文字原文。",
    },
    "r2-seko-sub-Seko订阅": {
        "p": f"{BASE}/r2-seko-sub.png",
        "q": "这是Seko(seko.sensetime.com,商汤)订阅/会员页截图。请仔细读图：1)确认品牌名；2)列出个人版与团队版所有档位名；3)【重点】逐条列出团队/企业相关功能原文（席位、积分、管理、看板、多人协作等）；4)个人订阅档位的功能点也列出（如3D、Agent、宫格等）。看不清就说看不清。",
    },
    "r2-tapnow-enterprise-TapNow企业版": {
        "p": f"{BASE}/r2-tapnow-enterprise.png",
        "q": "这是TapNow(tapnow.ai)企业版/pricing页截图。请仔细读图：1)确认品牌名；2)列出档位名；3)【重点】逐条列出团队/企业功能原文（席位、SSO、用量管控、看板、MCP、CLI、模板定制等）；4)有没有多人同屏/多光标、CLI、MCP字样？",
    },
    "r2-anishort-recharge-AniShort充值": {
        "p": f"{BASE}/r2-anishort-recharge.png",
        "q": "这是AniShort(anishort.ai)充值/订阅页截图。请仔细读图：1)确认品牌名；2)列出个人与团队档位名；3)【重点】逐条列出功能原文（席位、团队积分管控、并发、CLI、多人协同、3D导演台、智能分镜、宫格、全能视频Agent、多模态主体库、720度全景等）；4)特别注意：有没有'标准版/进阶版/高级版/豪华版/至尊版'这样的个人档位名？",
    },
    "r2-libtv-vip-LibTV会员": {
        "p": f"{BASE}/r2-libtv-vip.png",
        "q": "这是LibTV(liblib.tv)会员/VIP页截图。请仔细读图：1)确认品牌名；2)列出个人与团队档位名；3)【重点】逐条列出功能原文（多人画布协作、席位、积分、看板、CLI、Plugin等）；4)特别注意：个人订阅档位名是不是'标准版/进阶版/高级版/豪华版/至尊版'？功能里有没有'全能视频Agent/3D导演台/智能分镜(Kling3.0/O3)/9/4/25宫格/宫格切分/镜头聚焦/多模态主体库/720度全景'这些词？",
    },
    "r3-jurilu-project-巨日禄项目": {
        "p": f"{BASE}/r3-jurilu-project.png",
        "q": "这是巨日禄(video.jurilu.com)项目管理相关页面截图。请仔细读图：1)确认品牌名；2)这是什么界面（项目管理/任务/看板）？3)逐条列出可见文字（栏目名、按钮、数据项）；4)有没有多人协作/成员/席位/数据看板类功能？",
    },
    "r3-reelmate-team-万兴团队页": {
        "p": f"{BASE}/r3-reelmate-team.png",
        "q": "这是万兴剧厂(reelmate.cn)团队/团队管理页截图。请仔细读图：1)确认品牌名；2)这是什么界面？3)逐条列出可见文字（成员管理、席位、子账号、用量、看板等）；4)有没有多光标同屏、协作、权限等字样？",
    },
}

async def main():
    client = ZaiClient()
    for name, cfg in IMAGES.items():
        with open(cfg["p"], "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        try:
            res = await client.chat.completions.create(
                model="glm-4.6v",
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": cfg["q"]}]}],
            )
            print(f"\n===== {name} =====")
            print(res.choices[0].message.content)
        except Exception as e:
            print(f"\n===== {name} ===== ERROR: {e}")

asyncio.run(main())
