"""
vidsync title processor
========================
按各平台字数限制截断标题。
"""
from __future__ import annotations


# 各平台标题字数上限
TITLE_LIMITS = {
    "bilibili":        80,   # 推荐 ≤25
    "douyin":          55,   # 含 #话题
    "xiaohongshu":     20,
    "kuaishou":        20,
    "wechat_channels": 30,
    "baijiahao":       30,
    "qq_shizi":        30,
    "tencent_video":   50,
    "weibo":           30,   # 且 ≥6 字
    "huxiu":           60,
    "kr36":            40,
    "ximalaya":        30,
    "alipay":          30,
}


def truncate_title(title: str, platform_id: str, hashtag_chars: int = 0) -> str:
    """
    按平台截断标题。

    Args:
        title: 原标题
        platform_id: 平台 ID
        hashtag_chars: 标题中要预留的话题字符数（如抖音 #话题 占用）

    Returns:
        截断后的标题
    """
    limit = TITLE_LIMITS.get(platform_id, 80)
    available = limit - hashtag_chars
    if available < 1:
        available = 1
    if len(title) <= available:
        return title
    return title[:available]


def get_short_title(long_title: str, short_title: str = "", max_chars: int = 12) -> str:
    """优先用短标题；如短标题为空，从长标题截断。"""
    if short_title and len(short_title) <= max_chars:
        return short_title
    return (short_title or long_title)[:max_chars]


def weibo_validate_title(title: str) -> str:
    """微博标题特殊处理：≥6 字。"""
    if len(title) < 6:
        # 不足 6 字，补长
        return title + "　" * (6 - len(title))  # 用全角空格补
    return title[:30]
