#!/usr/bin/env python3
"""storyboard-trilogy.md → v3：
1. 画面规格表新增 v3 黑底规范与 B站素材铁律
2. 第1集表格替换为实测时间码 v3 版
"""
import re

SRC = "/home/z/my-project/github-work/1105-canvas-test-videos/02-storyboards/storyboard-trilogy.md"
DST = "/home/z/my-project/github-work/1105-canvas-test-videos/02-storyboards/storyboard-trilogy.md"
TABLE = "/home/z/my-project/ep1-work/ep1_table_v3.md"

md = open(SRC, encoding="utf-8").read()

# ---- 1) 标题行与版本说明 ----
md = md.replace(
    "# 《AI视频画布横评》三集 · B站竖屏解说视频总分镜表",
    "# 《AI视频画布横评》三集 · B站竖屏解说视频总分镜表（v3 · 2026-11-06）",
)

md = md.replace(
    "> 本表经批准后即为投产依据；每集另附机读版 `timeline-epN.json`（TTS 对齐 / canvas 截帧 / ffmpeg 组装直接消费）。",
    "> 本表经批准后即为投产依据；每集另附机读版 `timeline-epN.json`（TTS 对齐 / canvas 截帧 / ffmpeg 组装直接消费）。\n"
    "> **v3（2026-11-06）修订**：① 全片改黑底暗色系（见规格表）；② 时间码全部改为配音实测对齐（whisper 词级时间戳 + 静音区间校准，第1集已实测，误差≤0.3s）；③ 外部数字证据一律网页截图裁切、作品类素材一律原片片段叠底（见素材铁律）；④ 第1集 S02/S03/S14/S23 重设计。",
)

# ---- 2) 画面规格表：黑底 + 色彩修订 ----
md = md.replace(
    "| 色彩/字体 | 品牌系：强调 #fc8166 / 深强调 #e55b46 / 正文 #312e2e / 次级 #6b6666 / 线 #e7e3e1；阿里普惠体 400/700/900（信息图资产自带 TTF，本地加载禁 CDN） |",
    "| **色彩/字体（v3 黑底版）** | **本类解说片一律黑底暗色系**（仅限此类片，不回传 yz-infographic 通用规范）：底 #131110（近黑暖灰）/面板 #1e1b19/线上 #2a2624；正文 #f2efec（白）/次级 #b5aea9；**强调色不变**：#fc8166 / #e55b46（橙高亮黑底直用，无需调整）；白字黑底不违反规范。阿里普惠体 400/700/900（信息图资产自带 TTF，本地加载禁 CDN） |\n"
    "| **信息图暗色化（v3）** | yz-infographic 产出的白底信息图进入本类视频前必须换肤：底→#131110、卡面→#1e1b19、文字→#f2efec/#b5aea9、描边→#3a3634、品牌橙高亮保留；数值条/哑铃/时间轴等图形元素底色同步压暗，白底截图素材改用深色描边卡片承托 |",
)

# ---- 3) 素材来源标记表：新增 B站素材铁律 ----
md = md.replace(
    "| 【外】 | 外部下载：B站免登录 720p 通路（skills/video-downloader）等；**失败重试≤1次，超时 5s 回退【canvas】** | 切片后入 `clips/`（≤99MB/段） |",
    "| 【外】 | 外部下载：B站免登录 720p 通路（skills/video-downloader）等；**失败重试≤1次，超时 5s 回退【canvas】** | 切片后入 `clips/`（≤99MB/段） |\n"
    "| 【外·B站】 | **B站素材铁律（v3）**：① 作品/影片类素材必须找原片片段做背景叠底（压暗 15~20%），不用 canvas 模拟；② 播放量/点赞/评论数等**外部数字证据一律网页截图+裁切**呈现（m.bilibili.com 移动页免验证码可截），禁止 canvas 手绘数字；③ 名人评价（如郭帆转发点赞）评论区不可达时用新闻报道段落截图留证；④ 下载通路：pagelist API 拿 cid → playurl html5 游客档（view API/视频页有 412/验证码墙，勿碰） | 页面截图入 `materials/bili/shots/`，片段入 `materials/bili/` |",
)

# ---- 4) 第1集表格替换 ----
new_table = open(TABLE, encoding="utf-8").read()
# 匹配第1集表格：从 "| 01 |" 到第2集标题前的最后一行表格
pat = re.compile(r"(\| 01 \| 00:00-00:07 \|.+\n)(.*?)(\n\n---\n\n### 第2集)", re.S)
m = pat.search(md)
if not m:
    # 兜底：找 | 01 | 开头到 ### 第2集 之间的表格区
    pat2 = re.compile(r"(\| 01 \|[^\n]+\n)((?:\| \d+ \|[^\n]+\n)+)", re.M)
    m2 = pat2.search(md)
    assert m2, "找不到第1集表格"
    md = md[:m2.start()] + new_table + md[m2.end():]
else:
    md = md[:m.start(1)] + new_table + m.group(3) + md[m.end():]

# ---- 5) 第1集时长口径说明更新 ----
md = md.replace(
    "**时长口径**：已按真实配音 740.36s 反推语速对齐（预计成片 12:20，43 个镜头）",
    "**时长口径（v3 实测）**：whisper 词级时间戳 + silencedetect 静音区间双校准，43 镜全部实测时间码（句首误差≤0.3s，总长 740.36s 与音轨精确吻合）；v2 字数权重估算全片漂移最大 ±27s，已废弃",
)

open(DST, "w", encoding="utf-8").write(md)
# 校验
assert "v3 黑底版" in md and "B站素材铁律" in md
n_rows = len(re.findall(r"^\| \d+ \| \d\d:\d\d-\d\d:\d\d \|", md, re.M))
print(f"v3 分镜表已写入: {DST}")
print(f"表格总行数(三集): {n_rows}")
print("黑底规范: ✓  B站铁律: ✓  第1集实测表: ✓")
