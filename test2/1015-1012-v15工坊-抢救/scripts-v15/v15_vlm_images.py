#!/usr/bin/env python3
"""v15下篇: VLM识别下篇docx内嵌图 image1/2/3/4/5/18/19 归属平台与功能"""
import asyncio, base64, os
from zai_web_dev_sdk import ZaiClient

BASE = "/home/z/my-project/materials/下篇-1015/media/media"
IMAGES = {
    "image1-IMG273-需图注": {
        "p": f"{BASE}/image1.png",
        "q": "这是某AI视频/漫剧画布工作台产品的界面截图（10家候选：小云雀、纳逗Pro、ShotLab、万兴剧厂、Seko、TapNow、LibTV、巨日禄、OiiOii、AniShort）。请仔细读图：1)界面上任何位置出现的品牌名/logo/水印/产品名是什么？2)这是什么功能界面（尽量具体，例如分镜规划/走位编排/3D白模/主体库/广告剧向导等）？3)界面里有哪些可辨识的控件、文字标签（逐条列出原文）？请如实回答，看不清就说看不清。",
    },
    "image2-IMG267-现为TapNow主体库": {
        "p": f"{BASE}/image2.png",
        "q": "这张截图按图注说法是「在TapNow画布新建主体」。请核实：1)界面上的品牌名/logo/水印是什么？是否是TapNow？2)是否显示「新建主体」「主体库」等操作？3)列出界面主要文字标签原文。看不清就说看不清。",
    },
    "image3-IMG279-谁家的主体库": {
        "p": f"{BASE}/image3.png",
        "q": "这张截图按原文是某家的「主体库」界面（10家候选：小云雀、纳逗Pro、ShotLab、万兴剧厂、Seko、TapNow、LibTV、巨日禄、OiiOii、AniShort）。请核实：1)界面上的品牌名/logo/水印/产品名是什么？2)是不是主体库/资产库界面？3)列出界面主要文字标签与可见条目原文。看不清就说看不清。",
    },
    "image4-IMG270-需图注": {
        "p": f"{BASE}/image4.png",
        "q": "这是某AI视频/漫剧画布工作台产品的界面截图（10家候选：小云雀、纳逗Pro、ShotLab、万兴剧厂、Seko、TapNow、LibTV、巨日禄、OiiOii、AniShort）。请仔细读图：1)品牌名/logo/水印/产品名是什么？2)这是什么功能界面（例如剧本创作/分镜表/参数面板等）？3)列出界面主要文字标签原文。看不清就说看不清。",
    },
    "image5-IMG271-是否纳逗": {
        "p": f"{BASE}/image5.png",
        "q": "这张截图可能来自某产品教程（10家候选：小云雀、纳逗Pro、ShotLab、万兴剧厂、Seko、TapNow、LibTV、巨日禄、OiiOii、AniShort）。请核实：1)品牌名/logo/水印/产品名是什么？是否纳逗Pro？2)界面展示什么功能（例如分镜参数/剧本/宫格设定图等）？3)列出界面主要文字标签原文。看不清就说看不清。",
    },
    "image18-IMG277-现为巨日禄项目管理": {
        "p": f"{BASE}/image18.png",
        "q": "这张截图按图注说法是「巨日禄的项目管理界面」。请核实：1)界面上的品牌名/logo/水印是什么？是否巨日禄？2)是否是项目管理/任务管理类界面？3)列出界面主要文字标签与可见栏目原文。看不清就说看不清。",
    },
    "image19-IMG280-谁家的广告剧向导": {
        "p": f"{BASE}/image19.png",
        "q": "这张截图按原文是某家的「广告剧生成向导」（候选：万兴剧厂、小云雀、OiiOii等）。请核实：1)界面上的品牌名/logo/水印/产品名是什么？2)是否是广告剧/商品信息→剧情方案→成片之类的向导界面？3)列出界面主要文字标签原文（例如商品、方案、剧情等）。看不清就说看不清。",
    },
}

async def main():
    client = ZaiClient()
    for name, cfg in IMAGES.items():
        with open(cfg["p"], "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        res = await client.chat.completions.create(
            model="glm-4.6v",
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": cfg["q"]}]}],
        )
        print(f"\n===== {name} =====")
        print(res.choices[0].message.content)

asyncio.run(main())
