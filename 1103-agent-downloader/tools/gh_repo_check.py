#!/usr/bin/env python3
"""[A07] 批量查询候选仓库维护状态（stars / 最近推送 / 是否归档）"""
import json, urllib.request

tok = open('/home/z/my-project/.secrets/github_token').read().strip()
repos = [
    "yt-dlp/yt-dlp",
    "mikf/gallery-dl",
    "JoeanAmier/TikTokDownloader",
    "JoeanAmier/XHS-Downloader",
    "NanmiCoder/MediaCrawler",
    "ReaJason/xhs",
    "instaloader/instaloader",
    "btjawa/BiliTools",
    "nilaoda/BBDown",
    "SocialSisterYi/bilibili-API-collect",
    "dataabc/weibo-crawler",
    "zyipeng/video-downloader",
    "brainicism/bgutil-ytdlp-pot-provider",
    "yt-dlp/yt-dlp-get-pot",
    "junhoyeo/threads-api",
    "EvilDecoder/Douyin_TikTok_Download_API",
]
for r in repos:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{r}",
        headers={"Authorization": f"token {tok}", "User-Agent": "feasibility-research"},
    )
    try:
        d = json.load(urllib.request.urlopen(req, timeout=10))
        if "full_name" not in d:
            print(f"{r:44s} | NOT FOUND / {d.get('message','?')}")
            continue
        print(f"{d['full_name']:44s} | ★{d['stargazers_count']:<7} pushed:{d['pushed_at'][:10]} archived:{d['archived']}")
    except Exception as e:
        print(f"{r:44s} | ERROR {e}")
