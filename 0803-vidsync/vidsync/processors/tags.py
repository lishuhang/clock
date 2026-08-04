"""
vidsync tag normalizer
======================
按各平台格式归一化标签。

格式：
- plain: 无 # 前缀（B站、虎嗅、36氪）
- single_hash: #话题（抖音、小红书、视频号、百家号）
- double_hash: #话题#（微博、QQ空间）

数量上限：
- B站: 10
- 抖音: 5 话题（中央网信办 2025 新规 6 类必选）
- 小红书: 10
- 快手: 不限
- 视频号: 10
- 百家号: 不限
- 企鹅号: 不限
- 腾讯视频: 不限
- 微博: 不限
- 虎嗅: 无标签
- 36氪: 5
- 喜马拉雅: 不限
"""
from __future__ import annotations


TAG_LIMITS = {
    "bilibili":        10,
    "douyin":          5,
    "xiaohongshu":     10,
    "kuaishou":        20,
    "wechat_channels": 10,
    "baijiahao":       10,
    "qq_shizi":        10,
    "tencent_video":   10,
    "weibo":           10,
    "huxiu":           0,   # 无标签
    "kr36":            5,
    "ximalaya":        10,
    "alipay":          10,
}

TAG_FORMATS = {
    "bilibili":        "plain",
    "douyin":          "single_hash",
    "xiaohongshu":     "single_hash",
    "kuaishou":        "single_hash",
    "wechat_channels": "double_hash",
    "baijiahao":       "single_hash",
    "qq_shizi":        "plain",
    "tencent_video":   "plain",
    "weibo":           "double_hash",
    "huxiu":           "plain",
    "kr36":            "plain",
    "ximalaya":        "plain",
    "alipay":          "single_hash",
}


def normalize_tags(tags: list[str], platform_id: str) -> list[str]:
    """
    按平台格式归一化标签。

    Args:
        tags: 原始标签列表
        platform_id: 平台 ID

    Returns:
        归一化后的标签列表（已截断到数量上限）
    """
    limit = TAG_LIMITS.get(platform_id, 10)
    fmt = TAG_FORMATS.get(platform_id, "plain")

    if limit == 0:
        return []

    # 去重保序
    seen = set()
    unique = []
    for t in tags:
        t = t.strip().lstrip("#").rstrip("#").strip()
        if t and t not in seen:
            seen.add(t)
            unique.append(t)

    truncated = unique[:limit]

    # 按格式加 #
    if fmt == "plain":
        return truncated
    elif fmt == "single_hash":
        return [f"#{t}" for t in truncated]
    elif fmt == "double_hash":
        return [f"#{t}#" for t in truncated]
    return truncated


def tags_to_str(tags: list[str], platform_id: str, separator: str = " ") -> str:
    """把标签列表拼成字符串。"""
    normalized = normalize_tags(tags, platform_id)
    return separator.join(normalized)


def tags_for_input(tags: list[str], platform_id: str) -> list[str]:
    """归一化后的标签列表，用于逐个输入到表单。"""
    return normalize_tags(tags, platform_id)
