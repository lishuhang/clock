#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RSS 抓取、链接规范化与关键词过滤；跨批次去重由 02 合并器完成。"""

import feedparser
from datetime import datetime, timedelta
import json
import logging
import os
import re
import socket
import ssl
import urllib.error
import requests
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

# ================= Windows 编码修复 =================
import sys
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
# ====================================================

GLOBAL_TIMEOUT = 60
ARTICLE_LINK_TIMEOUT = 15
socket.setdefaulttimeout(GLOBAL_TIMEOUT)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(SCRIPT_DIR, "tmp")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".log"
log_path = os.path.join(LOG_DIR, f"getrss_{log_name}")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# 保留既有行为：兼容部分 RSS 源的异常证书配置。
ssl._create_default_https_context = ssl._create_unverified_context

TRACKING_PARAM_NAMES = {
    "gclid", "dclid", "fbclid", "gbraid", "wbraid", "msclkid", "yclid",
    "igshid", "ref", "referrer", "ref_src", "source", "src", "campaign",
    "mkt_tok", "spm", "scid", "cmp", "ocid", "feature", "si", "mc_cid",
    "mc_eid", "trk", "tracking", "tracking_id", "from", "via", "output",
}
TRACKING_PARAM_PREFIXES = ("utm_", "mc_", "ga_", "_ga", "oly_", "pk_")
CONTENT_PARAM_PATTERN = re.compile(
    r"^(?:id|p|v|aid|cid|pid|sid|slug|article(?:_id)?|story(?:_id)?|post(?:_id)?|"
    r"video(?:_id)?|content(?:_id)?|item(?:_id)?|news(?:_id)?|episode(?:_id)?)$",
    re.IGNORECASE,
)
TECHMEME_CACHE = {}


def load_config(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.error("配置文件 %s 未找到", file_path)
        raise
    except json.JSONDecodeError as exc:
        logger.error("配置文件 %s 格式错误: %s", file_path, exc)
        raise


def _is_tracking_param(name):
    lowered = name.lower()
    return lowered in TRACKING_PARAM_NAMES or lowered.startswith(TRACKING_PARAM_PREFIXES)


def _is_content_identifier(name):
    """只保留可定位具体文章、视频或内容项的查询参数。"""
    return bool(CONTENT_PARAM_PATTERN.fullmatch(name.lower()))


def decode_google_redirect(url):
    """将 Google 的 /url 重定向链接解码为最终文章 URL。"""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host not in {"google.com", "www.google.com", "news.google.com"}:
        return url
    if parsed.path.rstrip("/") != "/url":
        return url

    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        if key.lower() in {"url", "u", "q"} and value.startswith(("http://", "https://")):
            logger.info("解析 Google 重定向链接为原始地址")
            return value
    return url


def strip_nonessential_url_parts(url):
    """移除片段与追踪参数，仅保留内容定位所需的查询参数。"""
    parsed = urlsplit(url)
    kept_params = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if _is_tracking_param(key):
            continue
        if _is_content_identifier(key):
            kept_params.append((key, value))

    hostname = (parsed.hostname or "").lower()
    netloc = hostname
    if parsed.port:
        default_port = (parsed.scheme == "https" and parsed.port == 443) or (
            parsed.scheme == "http" and parsed.port == 80
        )
        if not default_port:
            netloc = f"{hostname}:{parsed.port}"

    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, urlencode(kept_params, doseq=True), ""))


def resolve_techmeme_source_url(url):
    """提取 Techmeme 目标条目的原始报道 URL，失败时保留聚合页地址。"""
    if url in TECHMEME_CACHE:
        return TECHMEME_CACHE[url]

    parsed = urlsplit(url)
    anchor_name = parsed.fragment
    if not anchor_name:
        path_item = parsed.path.rstrip("/").rsplit("/", 1)[-1]
        if re.fullmatch(r"p\d+", path_item, re.IGNORECASE):
            anchor_name = path_item
    request_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
    try:
        response = requests.get(
            request_url,
            headers={"User-Agent": "curl/8.6.0", "Accept": "text/html,application/xhtml+xml"},
            timeout=ARTICLE_LINK_TIMEOUT,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        container = soup.find("a", attrs={"name": anchor_name}) if anchor_name else None
        candidate = container.find_next("a", class_="ourh") if container else soup.select_one("a.ourh")
        if candidate and candidate.get("href"):
            resolved = urljoin(request_url, candidate["href"])
            resolved_host = (urlsplit(resolved).hostname or "").lower()
            if resolved_host and not resolved_host.endswith("techmeme.com"):
                TECHMEME_CACHE[url] = resolved
                logger.info("Techmeme 条目已解析为原始文章链接: %s", resolved_host)
                return resolved
    except Exception as exc:
        logger.warning("Techmeme 原文链接解析失败，保留聚合页链接: %s", type(exc).__name__)

    TECHMEME_CACHE[url] = url
    return url


def extract_techmeme_source_from_summary(summary):
    """Extract the original article URL embedded in a Techmeme RSS item."""
    if not summary:
        return ""
    soup = BeautifulSoup(summary, "html.parser")
    for anchor in soup.find_all("a", href=True):
        candidate = anchor["href"].strip()
        parsed = urlsplit(candidate)
        host = (parsed.hostname or "").lower()
        if parsed.scheme in {"http", "https"} and host and not host.endswith("techmeme.com"):
            return candidate
    return ""


def normalize_article_url(url):
    """将聚合/重定向 URL 规范化为可复用的文章 URL。"""
    if not url:
        return ""

    decoded = decode_google_redirect(url.strip())
    host = (urlsplit(decoded).hostname or "").lower()
    if host.endswith("techmeme.com"):
        decoded = resolve_techmeme_source_url(decoded)
    return strip_nonessential_url_parts(decoded)


def fetch_rss_entries(feed_tuples):
    entries = []
    for feed in feed_tuples:
        feed_url = feed["url"]
        if feed_url.startswith("//"):
            logger.info("跳过已注释的 RSS 源: %s", feed_url)
            continue

        logger.info("正在获取 RSS 源: %s", feed_url)
        try:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0 Safari/537.36"
                )
            }
            rss_feed = feedparser.parse(feed_url, request_headers=headers)
            if rss_feed.bozo:
                logger.warning("RSS 源 %s 解析时出现问题: %s", feed_url, rss_feed.bozo_exception)
            if not rss_feed.entries:
                logger.warning("RSS 源 %s 没有返回条目", feed_url)
                continue

            logger.info("从 %s 获取到 %s 个条目", feed_url, len(rss_feed.entries))
            for entry in rss_feed.entries:
                if getattr(entry, "published_parsed", None) is not None:
                    entry_datetime = datetime(*entry.published_parsed[:6])
                elif getattr(entry, "updated_parsed", None) is not None:
                    entry_datetime = datetime(*entry.updated_parsed[:6])
                else:
                    entry_datetime = datetime.now()
                    logger.warning("条目 %r 没有时间信息，使用当前时间", entry.get("title", ""))

                if entry_datetime > datetime.now() - timedelta(days=1):
                    entry_link = entry.get("link", "")
                    if (urlsplit(entry_link).hostname or "").lower().endswith("techmeme.com"):
                        source_link = extract_techmeme_source_from_summary(entry.get("summary", ""))
                        if source_link:
                            entry_link = source_link
                            logger.info(
                                "从 Techmeme RSS 摘要提取原始文章链接: %s",
                                (urlsplit(source_link).hostname or "").lower(),
                            )
                    entries.append(
                        {
                            "title": entry.get("title", ""),
                            "link": entry_link,
                            "published": entry_datetime,
                        }
                    )
        except socket.timeout:
            logger.error("获取 RSS 源 %s 超时（超过 %s 秒），已跳过", feed_url, GLOBAL_TIMEOUT)
        except (urllib.error.URLError, ConnectionResetError, ssl.SSLError) as exc:
            logger.error("获取 RSS 源 %s 时发生网络错误: %s", feed_url, exc)
        except Exception as exc:
            logger.error("处理 RSS 源 %s 时发生未知错误: %s", feed_url, exc)

    logger.info("总共获取到 %s 个有效条目", len(entries))
    return entries


def filter_by_keywords(entries, keywords):
    if not keywords:
        logger.warning("没有提供关键词，返回所有条目")
        return entries

    filtered = []
    for entry in entries:
        title = entry.get("title", "").lower()
        if any(keyword.lower() in title for keyword in keywords):
            filtered.append(entry)
    logger.info("关键词过滤后剩余 %s 个条目", len(filtered))
    return filtered


def _display_title(raw_title):
    title = re.sub(r"<.*?>", "", raw_title or "")
    title = re.sub(r"人工智能|artificial intelligence", "AI", title, flags=re.I)
    return re.sub(r"（.*?）$", "", title).strip()


def process_entries(entries):
    """还原并规范化链接，保留全部候选供 02 跨批次统一去重。"""
    if not entries:
        logger.warning("没有条目需要处理")
        return []

    normalized_entries = []
    for entry in entries:
        title = _display_title(entry.get("title", ""))
        link = normalize_article_url(entry.get("link", ""))
        if not title or not link:
            continue
        candidate = {
            "title": title,
            "link": link,
            "published": entry.get("published", datetime.min),
        }
        normalized_entries.append(candidate)

    chinese_entries = sorted(
        (item for item in normalized_entries if re.search(r"[\u4e00-\u9fff]", item["title"])),
        key=lambda item: item["title"],
    )
    english_entries = sorted(
        (item for item in normalized_entries if not re.search(r"[\u4e00-\u9fff]", item["title"])),
        key=lambda item: item["title"],
    )
    result = chinese_entries + english_entries
    logger.info("规范化后得到 %s 个候选条目，交由 02 跨批次去重", len(result))
    return result


def to_markdown(entries):
    if not entries:
        return "暂无相关内容\n"
    return "\n".join(f"- [{entry['title']}]({entry['link']})" for entry in entries) + "\n"


def main():
    logger.info("开始执行 RSS 处理脚本")
    rss_config = load_config(os.path.join(SCRIPT_DIR, "rss_feeds.json"))
    keyword_config = load_config(os.path.join(SCRIPT_DIR, "keywords.json"))

    all_keywords = []
    for category in keyword_config["keywords"]:
        all_keywords.extend(keyword_config["keywords"][category])
    all_keywords = list(set(all_keywords))

    logger.info("加载了 %s 个 RSS 源", len(rss_config["feeds"]))
    logger.info("加载了 %s 个关键词", len(all_keywords))
    all_entries = fetch_rss_entries(rss_config["feeds"])
    filtered_entries = filter_by_keywords(all_entries, all_keywords)
    markdown_output = to_markdown(process_entries(filtered_entries))

    os.makedirs(TMP_DIR, exist_ok=True)
    output_file = os.path.join(TMP_DIR, f"rss_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md")
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(markdown_output)
    logger.info("处理完成，结果已保存到 %s", output_file)
    print(f"Processed Markdown saved to {output_file}")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as exc:
        logger.error("配置文件未找到: %s", exc)
        print(f"Config file not found: {exc}")
    except Exception as exc:
        logger.error("发生错误: %s", exc)
        print(f"An error occurred: {exc}")
