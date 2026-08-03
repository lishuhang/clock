"""
vidsync cookie parser
======================
解析 Netscape cookies.txt 格式（Get cookies.txt locally 扩展导出格式），
转成 Playwright BrowserContext.add_cookies() 接受的格式。

Netscape 格式：
  # 注释行
  <domain>\t<flag>\t<path>\t<secure>\t<expiration>\t<name>\t<value>

例如：
  .bilibili.com	TRUE	/	TRUE	1801271338	SESSDATA	f3d6e9af%2C...
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


@dataclass
class Cookie:
    """单条 cookie，对应 Playwright add_cookies 的字典。"""
    name: str
    value: str
    domain: str
    path: str
    expires: float
    secure: bool
    http_only: bool = False
    same_site: str = "Lax"

    def to_playwright(self) -> dict:
        """转成 Playwright add_cookies 接受的 dict。"""
        # Playwright 要求 domain 必须以点开头或不含点（精确主机）
        # same_site 必须是 "Strict" | "Lax" | "None"
        return {
            "name": self.name,
            "value": self.value,
            "domain": self.domain,
            "path": self.path or "/",
            "expires": self.expires if self.expires > 0 else -1,
            "secure": bool(self.secure),
            "httpOnly": bool(self.http_only),
            "sameSite": self.same_site,
        }


def parse_netscape_cookies(text: str) -> list[Cookie]:
    """
    解析 Netscape cookies.txt 文本，返回 Cookie 列表。

    Args:
        text: cookies.txt 文件内容

    Returns:
        list[Cookie]
    """
    cookies: list[Cookie] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            # 部分扩展导出时空格分隔
            parts = line.split()
            if len(parts) < 7:
                logger.warning("cookie line %d skipped (expected 7 fields, got %d): %s",
                               lineno, len(parts), line[:80])
                continue
        domain, flag, path, secure, expiration, name, value = parts[:7]
        try:
            cookies.append(Cookie(
                name=name,
                value=value,
                domain=domain,
                path=path or "/",
                expires=float(expiration) if expiration else -1,
                secure=(secure.upper() == "TRUE"),
                http_only=False,
                same_site="Lax",
            ))
        except Exception as e:
            logger.warning("cookie line %d parse error: %s", lineno, e)
    return cookies


def load_cookies_file(path: str | Path) -> list[Cookie]:
    """从文件加载 cookies。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"cookies file not found: {p}")
    text = p.read_text(encoding="utf-8", errors="replace")
    cookies = parse_netscape_cookies(text)
    logger.info("loaded %d cookies from %s", len(cookies), p.name)
    return cookies


def filter_expired(cookies: Iterable[Cookie], now: float | None = None) -> list[Cookie]:
    """过滤掉已过期的 cookies（expires != 0 且 < now）。"""
    if now is None:
        now = time.time()
    out = []
    for c in cookies:
        if c.expires == 0:
            out.append(c)  # session cookie
        elif c.expires > now:
            out.append(c)
        else:
            logger.debug("expired cookie dropped: %s (expired %d sec ago)",
                         c.name, int(now - c.expires))
    return out


def filter_by_domain(cookies: Iterable[Cookie], domain: str) -> list[Cookie]:
    """筛选属于某域名的 cookies（含子域）。"""
    out = []
    d = domain.lower().lstrip(".")
    for c in cookies:
        cd = c.domain.lower().lstrip(".")
        if cd == d or cd.endswith("." + d) or d.endswith("." + cd):
            out.append(c)
    return out


def discover_cookies_dir(cookies_dir: str | Path) -> dict[str, list[Cookie]]:
    """
    扫描 cookies 目录，返回 {platform_domain: [Cookie, ...]}。

    支持的文件命名：
      - member.bilibili.com_cookies.txt
      - bilibili.com_cookies.txt
      - bilibili_cookies.txt
    """
    p = Path(cookies_dir)
    if not p.exists():
        logger.warning("cookies dir does not exist: %s", p)
        return {}
    result: dict[str, list[Cookie]] = {}
    for f in sorted(p.glob("*.txt")):
        text = f.read_text(encoding="utf-8", errors="replace")
        cookies = parse_netscape_cookies(text)
        if not cookies:
            continue
        # 推断平台域名：优先取第一个 cookie 的 domain
        primary_domain = cookies[0].domain.lstrip(".")
        # 如果文件名里有更具体的域名，用文件名
        stem = f.stem  # e.g. member.bilibili.com_cookies
        if stem.endswith("_cookies"):
            stem = stem[:-len("_cookies")]
        if "." in stem:
            primary_domain = stem
        result[primary_domain] = cookies
        logger.info("discovered cookies for %s (%d entries, file=%s)",
                    primary_domain, len(cookies), f.name)
    return result


# 平台域名 → 平台 ID 映射
PLATFORM_DOMAIN_MAP = {
    "bilibili": ["bilibili.com", "member.bilibili.com"],
    "douyin": ["douyin.com", "creator.douyin.com"],
    "xiaohongshu": ["xiaohongshu.com", "creator.xiaohongshu.com"],
    "kuaishou": ["kuaishou.com", "cp.kuaishou.com"],
    "wechat_channels": ["weixin.qq.com", "channels.weixin.qq.com"],
    "baijiahao": ["baidu.com", "baijiahao.baidu.com"],
    "qq_shizi": ["qq.com", "shizi.qq.com"],
    "tencent_video": ["v.qq.com", "mp.v.qq.com"],
    "weibo": ["weibo.com", "s.weibo.com"],
    "huxiu": ["huxiu.com", "www.huxiu.com"],
    "kr36": ["36kr.com", "misopen.36kr.com"],
    "alipay": ["alipay.com", "c.alipay.com"],
}


def map_cookies_to_platforms(cookies_map: dict[str, list[Cookie]]) -> dict[str, list[Cookie]]:
    """
    把扫描到的 cookies 按平台 ID 归类。
    返回 {platform_id: [Cookie, ...]}
    """
    result: dict[str, list[Cookie]] = {}
    for platform_id, domains in PLATFORM_DOMAIN_MAP.items():
        for domain in domains:
            # 精确匹配
            if domain in cookies_map:
                result[platform_id] = cookies_map[domain]
                break
            # 前缀匹配（如 member.bilibili.com 匹配 bilibili.com）
            for k in cookies_map:
                if k.endswith(domain) or domain.endswith(k):
                    if platform_id not in result:
                        result[platform_id] = cookies_map[k]
                    break
    return result


if __name__ == "__main__":
    # 自测：扫描 /home/z/my-project/cookies-extracted
    import sys
    cookies_dir = sys.argv[1] if len(sys.argv) > 1 else "/home/z/my-project/cookies-extracted"
    logging.basicConfig(level=logging.INFO)
    raw = discover_cookies_dir(cookies_dir)
    print(f"Discovered {len(raw)} cookie files:")
    for k, v in raw.items():
        valid = filter_expired(v)
        print(f"  {k}: {len(v)} total / {len(valid)} valid")
    print()
    mapped = map_cookies_to_platforms(raw)
    print(f"Mapped to {len(mapped)} platforms:")
    for pid, cookies in mapped.items():
        valid = filter_expired(cookies)
        print(f"  {pid}: {len(valid)} valid cookies")
