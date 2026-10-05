#!/usr/bin/env python3
"""
微信公众号文章 → Markdown + GitHub 自动发布脚本 v3.2 (主站 lishuhang.me)

v3.2 变更 (2026-07-03, keepitrun v1.9)：
  - 修复部分微信文章正文无法提取的 bug
    · 原因：部分微信文章正文在 <section> 标签内而非 <p> 标签，
      且标题用 <section> 而非 <h2>/<h3>，导致 convert_short_article
      的 <p> 遍历找不到内容，detect_article_type 也因 heading_count=0
      误判为短文
    · 表现：发布到主博客的文章只有 front matter 和图片，正文缺失
      （如 2026-06-25-zhong-guo-ban-mythos-bi-de.md 仅 14 行）
    · 修复：convert_short_article 在 <p> 提取结果过少时，回退从
      叶 <section> 提取文本；convert_long_article 新增 section 标签
      到 find_all 列表，处理叶 section 的文本
    · 跳过含"想跟作者进一步讨论本文"的 section（尾部推广）

v3.3 变更 (2026-07-24, keepitrun v1.16)：
  - fetch_wechat_html() 增强：微信反爬越来越严格（返回"环境异常"验证页）
  - 新增 z-ai page_reader 回退策略：当 requests 直接抓取失败时，调用 z-ai CLI
    的 page_reader 功能（基于云端浏览器，能绕过反爬验证）
  - _fetch_via_zai_page_reader() 辅助函数：通过 subprocess 调用 z-ai CLI
  - 抓取策略：requests 重试 3 次 → z-ai page_reader 回退 → 提示用户手动保存 HTML
  - 注意：z-ai CLI 需要单独安装（不在 keepitrun 包内），未安装时自动跳过此回退

v3.2 变更 (2026-07-24, keepitrun v1.15)：
  - 新增防御性检查：即使 ALBUMS 列表正确排除了 daily 专辑，仍按标题模式二次过滤
  - _is_daily_report_title(): 匹配 "每日\s*AIGC\s*早报" (大小写不敏感，兼容各种空格)
  - _is_daily_report_slug(): 匹配 "mei-ri-aigc-zao-bao" slug 前缀
  - 检查点1: collect_album_urls() — 在合集遍历时跳过 daily 文章
  - 检查点2: process_article() — 在文章处理时再次跳过 (防止 CLI/文件直接传入 daily URL)
  - 背景: 2026-07-05 的 restore commit f2a7f5b 误把 35 篇已删除的 daily 文章重新
    加回 blog repo (原由 86c8974 于 2026-07-03 删除)。此次防御性检查确保即使
    未来发生类似误操作，脚本也不会主动抓取 daily 内容到主博客。

v3.1 变更 (2026-07-02, keepitrun v1.8)：
  - 修复误纳 AIGC 早报合集的 bug：原 ALBUMS 列表中 album_id=3793362825901522949
    的 "贴图" 条目实际是 AIGC 早报专辑（与 03_convert-daily.py 的 DEFAULT_ALBUM_ID
    相同），导致 AIGC 早报被同步到主博客 lishuhang.me
  - 移除该条目；现支持 7 个合集分类（如有真实"贴图"合集需另配 album_id）
  - AIGC 早报仅在 lishuhang.me/daily/ 发布，由 03_convert-daily.py 处理

v3.0 变更 (2026-06-11)：
  - 移除公众平台后台Cookie登录方式（微信已关闭外部浏览器访问权限）
  - 改用微信公众号合集(Album) API获取文章列表，无需Cookie即可访问
  - 支持7个合集分类：新闻实验室、随笔、航通社的朋友们、AI、科技、历史、传媒
  - 文章类别(categories)和标签(tags)根据合集来源自动分配
  - 日志统一输出到 logs/ 目录，兼容 keepitrun 日志体系

功能：
1. 自动识别文章格式：长文(blog) / 短篇(short)
2. 从URL直接抓取微信文章（或读取同目录TXT/MD/HTML中的URL）
3. 从微信合集(Album)遍历抓取文章列表（无需Cookie）
4. 正确转换HTML→Markdown（保留粗体/斜体/链接/列表/引用，无重复）
5. 下载原始最大尺寸图片（1:1大图优先，非og:image裁剪版）
6. 自动推送到 GitHub：
   - 文章 → lishuhang/lishuhang.github.io  _posts/
   - 配图 → 按主站 _config.yml 的 image_prefixes 和文章日期选择仓库/分支
7. 覆盖保护：已有文件先备份为 _bak；批量模式下支持 a(ll) 全部覆盖
8. 合集来源自动分配 Jekyll categories 和 tags，并自动追加 featured 标签（v1.28）
9. v1.28: URL 级已同步记忆（blog_sync_memory.json）：同步过一次的文章
   永远不再抓取处理，配合调度器 30 天窗口封顶实现纯增量同步

用法：
  python 04_convert-blog.py <url>                          # 抓取指定URL
  python 04_convert-blog.py <url1> <url2> ...              # 批量抓取
  python 04_convert-blog.py                                # 读取同目录txt/md/html中的URL
  python 04_convert-blog.py album:20260101                 # 从合集抓取20260101至今的文章
  python 04_convert-blog.py album:20260101:20260201         # 指定日期范围
  python 04_convert-blog.py album:all                       # 抓取全部合集的所有文章
  python 04_convert-blog.py album:diff                      # 对比合集与仓库差异

参数说明：
  album:YYYYMMDD           从指定日期至今的所有文章（遍历全部合集）
  album:YYYYMMDD:YYYYMMDD  指定日期范围内的文章
  album:all                抓取全部合集的所有文章
  album:diff               对比合集文章与GitHub仓库差异

合集说明：
  脚本内置了7个微信合集配置，分为两大类：
  贴图类：新闻实验室
  文章类：随笔、航通社的朋友们、AI、科技、历史、传媒
  每个合集对应一个 categories 和 tags，自动写入 Markdown front matter。
  注：公众号改版后每篇文章只能归于一个合集，不会重复。

环境变量：
  GITHUB_TOKEN  — GitHub Personal Access Token（需 repo 权限）
  支持从同目录 .env 文件自动加载（格式：GITHUB_TOKEN=ghp_xxxxx）

获取 GitHub Token：
  1. 访问 https://github.com/settings/tokens
  2. Generate new token (classic)
  3. 勾选 repo 权限
  4. 设置环境变量：export GITHUB_TOKEN=ghp_xxxxx
     或在脚本同目录创建 .env 文件：GITHUB_TOKEN=ghp_xxxxx
"""

import re
import os
import sys
import glob
import json
import base64
import html as html_mod
import logging
import time
import random
import unicodedata
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup, Comment
from pypinyin import lazy_pinyin

from image_routing import ImageRouteError, join_repo_path, load_upload_route

# ================= Windows 编码修复 =================
# Windows 默认控制台编码为 cp1252，无法输出 emoji 等超出 Latin-1 范围的字符
# 在所有 print()/logging 输出之前，强制将 stdout/stderr 切换为 UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
# ====================================================

# ─── .env 文件加载 ──────────────────────────────────────────

def _load_dotenv():
    """从脚本同目录的 .env 文件加载环境变量（不覆盖已有值）。

    支持格式：
    - KEY=VALUE
    - KEY="VALUE"  或  KEY='VALUE'
    - # 开头的注释行
    - 空行
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # 去掉引号
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                # 不覆盖已有环境变量
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass


_load_dotenv()

# ─── 配置 ────────────────────────────────────────────────────

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_POSTS = "lishuhang/lishuhang.github.io"   # 文章仓库
POSTS_PATH = "_posts"                            # 文章在仓库中的路径

# v1.25: 移除 piczip/ 内置 exe；压缩全部由 Pillow 完成（见 _optimize_png_with_pillow 等）
GITHUB_IMAGE_BASE = ""   # v2.0: 相对路径，由 _config.yml + image_prefix.rb 插件在构建时解析为完整 URL

# 长文/短篇自动识别阈值
LONG_ARTICLE_MIN_CHARS = 800   # js_content 文本长度 >= 此值 → 长文
LONG_ARTICLE_MIN_HEADINGS = 2  # h2/h3 数量 >= 此值 → 长文

# 微信合集(Album) API 配置
ALBUM_BIZ = "MjM5Mjg1ODIxMQ=="  # 公众号 __biz 参数
ALBUM_API_URL = "https://mp.weixin.qq.com/mp/appmsgalbum"
ALBUM_PAGE_SIZE = 20  # 合集API每页请求数量

# 合集配置：name=合集名称, album_id=合集ID, categories=Jekyll分类, tags=Jekyll标签
# v1.8 修复: 移除原 "贴图" 条目 (album_id=3793362825901522949)
#   该 album_id 实际是 AIGC 早报专辑 (与 03_convert-daily.py 的 DEFAULT_ALBUM_ID 完全相同)，
#   之前误纳导致 AIGC 早报被同步到主博客 lishuhang.me。
#   AIGC 早报应仅在 lishuhang.me/daily/ 发布 (由 03_convert-daily.py 处理)。
#   如有真实的"贴图"合集，需另配正确的 album_id 后重新添加。
# 贴图类合集
ALBUMS = [
    {"name": "新闻实验室", "album_id": "3902494251036180488",
     "categories": "新闻实验室", "tags": "新闻"},
    # 文章类合集
    {"name": "随笔", "album_id": "2615905303213441024",
     "categories": "随笔", "tags": "随笔"},
    {"name": "航通社的朋友们", "album_id": "3477575130983596037",
     "categories": "航通社", "tags": "航通社"},
    {"name": "AI", "album_id": "1525375142552518658",
     "categories": "AI", "tags": "AI"},
    {"name": "科技", "album_id": "1584782882340978691",
     "categories": "科技", "tags": "科技"},
    {"name": "历史", "album_id": "1903521189994545155",
     "categories": "历史", "tags": "历史"},
    {"name": "传媒", "album_id": "2046079811625844737",
     "categories": "传媒", "tags": "传媒"},
]

# 自动模式：最多检查每个合集前几页（每页20篇）
AUTO_MAX_PAGES = 3

# v1.28: 已同步文章记忆（URL → 同步时间戳）。
# 目的：合集增量同步只需「找出最近新增、尚未同步的文章」，同步过一次的 URL
# 永远不再抓取处理（不随合集变大而遍历历史全量；换新电脑时仓库本身即真相源，
# 仅最近窗口内的文章会做一次存在性确认）。文件为运行时状态，不入库不打包。
BLOG_SYNC_MEMORY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "blog_sync_memory.json"
)


def _build_tags_with_featured(tags):
    """v1.28: 每篇同步文章自动追加 featured 标签（首页大图滚动区域数据源）。

    tags 可为单个标签或逗号分隔多标签；已含 featured 时去重，避免重复。
    """
    tag_items = [t.strip() for t in str(tags).split(",") if t.strip()]
    if "featured" not in tag_items:
        tag_items.append("featured")
    return ",".join(tag_items)


def load_sync_memory(logger=None):
    """v1.28: 读取已同步文章记忆；文件缺失或损坏时返回空记忆（首次运行为冷启动）。"""
    try:
        with open(BLOG_SYNC_MEMORY_PATH, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    memory = {}
    for key, ts in raw.items():
        if isinstance(key, str) and isinstance(ts, (int, float)):
            memory[key] = ts
    return memory


def save_sync_memory(memory, logger=None):
    """v1.28: 原子写入记忆文件；写入失败仅警告，不阻断主流程。"""
    try:
        tmp_path = BLOG_SYNC_MEMORY_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(memory, fh, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp_path, BLOG_SYNC_MEMORY_PATH)
    except OSError as exc:
        if logger:
            logger.warning(f"同步记忆文件写入失败（不影响本次发布）: {exc}")


def mark_article_synced(memory, url, logger=None):
    """v1.28: 记录一个 URL 为已同步（含「仓库已存在」与「本次上传成功」两种情形）。"""
    if not url:
        return
    memory[url] = time.time()
    save_sync_memory(memory, logger=logger)


# ─── 日志 ────────────────────────────────────────────────────

def setup_logging(output_dir=None):
    """创建带时间戳的日志文件，同时输出到控制台。
    
    日志文件统一存放在脚本同目录的 logs/ 子目录下，兼容 keepitrun 日志体系。
    """
    log_name = f"blog_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_name)
    logger = logging.getLogger("convert_blog")
    # 清除已有handler（防止重复）
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger, log_path


# ─── 工具函数 ────────────────────────────────────────────────

def slugify(title):
    """生成带拼音转换的文件名slug（取前6个词）"""
    title_pinyin = ' '.join(lazy_pinyin(title))
    slug = unicodedata.normalize('NFKD', title_pinyin)
    slug = re.sub(r'[^\w\s-]', '', slug).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    # 下划线（如标题中残留的 "_"）会污染 slug 开头/内部，统一转为连字符并去掉首尾，
    # 避免生成 "_xxx" 这类路径。公众号标题中的 "|" 等特殊字符已被上方正则移除。
    slug = slug.replace('_', '-').strip('-')
    return '-'.join(slug.split('-')[:6])


# ── v1.15 防御性检查：识别 daily AIGC 早报文章 ──
# daily 文章由 03_convert-daily.py 处理，绝不应出现在主博客。
# 标题模式: "每日 AIGC 早报" / "每日AIGC早报" / "每日 AIGC早报" / "每日aigc早报" 等
# slug 模式: mei-ri-aigc-zao-bao-* (由 slugify 生成)
_DAILY_TITLE_PATTERN = re.compile(
    r"每日\s*AIGC\s*早报", re.IGNORECASE)
_DAILY_SLUG_PATTERN = re.compile(r"^mei-ri-aigc-zao-bao")


def _is_daily_report_title(title):
    """检查文章标题是否为 daily AIGC 早报。"""
    if not title:
        return False
    return bool(_DAILY_TITLE_PATTERN.search(title))


def _is_daily_report_slug(slug):
    """检查文章 slug 是否为 daily AIGC 早报。"""
    if not slug:
        return False
    return bool(_DAILY_SLUG_PATTERN.match(slug))


def _read_file_text(filepath, logger=None):
    """尝试多种编码读取文件文本内容。"""
    for enc in ("utf-8-sig", "utf-8", "gbk", "latin-1"):
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    if logger:
        logger.warning(f"无法解码文件: {os.path.basename(filepath)}")
    return None


def _normalize_wx_url(url):
    """标准化微信文章URL：http→https，去除查询参数，去重。"""
    url = url.strip()
    # 处理JS转义的斜杠  \/ → /
    url = url.replace("\\/", "/")
    if url.startswith("http://"):
        url = "https://" + url[7:]
    elif not url.startswith("https://"):
        return None
    # 只保留 mp.weixin.qq.com/s/ 格式的文章链接
    if not re.match(r"https?://mp\.weixin\.qq\.com/s/", url):
        return None
    # 去除URL片段和多余查询参数
    url = url.split("#")[0]
    return url


def _extract_urls_from_text(text):
    """从纯文本中提取微信文章URL（一行一个URL的情况）。"""
    urls = []
    for line in text.splitlines():
        line = line.strip()
        line = html_mod.unescape(line)
        # 处理HTML实体和JS转义
        line = line.replace("\\/", "/")
        normalized = _normalize_wx_url(line)
        if normalized:
            urls.append(normalized)
    return urls


def _extract_urls_from_markdown(text):
    """从Markdown文本中提取微信文章URL。
    
    支持：
    - [标题](https://mp.weixin.qq.com/s/xxx) 链接格式
    - 纯文本URL
    """
    urls = []
    # 提取Markdown链接中的URL
    for m in re.finditer(r'\[(?:[^\]]*)\]\((https?://mp\.weixin\.qq\.com/s/[^\s\)]+)\)', text):
        url = _normalize_wx_url(m.group(1))
        if url:
            urls.append(url)
    # 也提取纯文本URL（不在链接格式中的）
    for m in re.finditer(r'(?<!\()(https?://mp\.weixin\.qq\.com/s/[^\s\)<"\'\]]+)', text):
        url = _normalize_wx_url(m.group(1))
        if url and url not in urls:
            urls.append(url)
    return urls


def _extract_urls_from_html_text(text):
    """从HTML文本（含内嵌JavaScript）中提取微信文章URL。
    
    支持：
    - <a href="https://mp.weixin.qq.com/s/xxx"> 链接
    - JavaScript JSON数据中的 content_url 字段
      (含多级转义: &quot; + backslash-slash 等)
    - HTML实体转义的URL
    """
    urls = []
    seen = set()

    # 第1步：HTML entity decode整个文本
    decoded = html_mod.unescape(text)

    # 第2步：反复替换JS转义斜杠，直到全部清理干净
    # 微信后台HTML可能有多层转义：\\/ → /, \\\/ → /, \\\\/ → / 等
    prev = None
    while prev != decoded:
        prev = decoded
        decoded = decoded.replace("\\/", "/")

    # 第3步：从<a>标签提取href
    for m in re.finditer(r'<a[^>]*?href=["\']([^"\'>]+)["\']', decoded, re.IGNORECASE):
        url = _normalize_wx_url(m.group(1))
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    # 第4步：提取所有 mp.weixin.qq.com/s/ 链接（清理转义后，格式统一）
    for m in re.finditer(
        r'(https?://mp\.weixin\.qq\.com/s/[^\s"\'<>,}\])]+)',
        decoded
    ):
        url = _normalize_wx_url(m.group(1))
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    return urls


def read_urls_from_files(directory, logger=None):
    """从目录内所有支持文件中提取微信文章URL。
    
    支持：
    - .txt  — 纯文本，一行一个URL
    - .md   — Markdown格式，提取链接 [text](url)
    - .html — HTML/JavaScript格式，提取<a>标签和JSON数据中的URL
    
    兼容 http/https、HTML实体转义、JS转义(escaped-slash)、UTF-8 BOM 和 GBK 编码。
    """
    all_urls = []
    seen = set()

    # 处理 .txt 文件
    for filepath in sorted(glob.glob(os.path.join(directory, "*.txt"))):
        text = _read_file_text(filepath, logger)
        if text is None:
            continue
        for url in _extract_urls_from_text(text):
            if url not in seen:
                seen.add(url)
                all_urls.append(url)
        if logger:
            logger.debug(f"从TXT中读取到URL: {os.path.basename(filepath)}")

    # 处理 .md 文件
    for filepath in sorted(glob.glob(os.path.join(directory, "*.md"))):
        text = _read_file_text(filepath, logger)
        if text is None:
            continue
        for url in _extract_urls_from_markdown(text):
            if url not in seen:
                seen.add(url)
                all_urls.append(url)
        if logger:
            logger.debug(f"从MD中读取到URL: {os.path.basename(filepath)}")

    # 处理 .html 文件（只提取URL，不作为文章HTML处理）
    for filepath in sorted(glob.glob(os.path.join(directory, "*.html"))):
        text = _read_file_text(filepath, logger)
        if text is None:
            continue
        for url in _extract_urls_from_html_text(text):
            if url not in seen:
                seen.add(url)
                all_urls.append(url)
        if logger:
            logger.debug(f"从HTML中读取到URL: {os.path.basename(filepath)}")

    if logger and all_urls:
        logger.info(f"从文件中共读取到 {len(all_urls)} 个微信文章URL")

    return all_urls


# ─── 网络抓取 ────────────────────────────────────────────────

def fetch_wechat_html(url, logger, session=None):
    """通过requests抓取微信文章HTML。使用Session维持Cookie。

    v1.16 增强 (2026-07-24):
    - 微信对服务器 IP 越来越严格，频繁返回"环境异常"验证页。
    - 当 requests 直接抓取失败时，回退到 z-ai page_reader（基于云端浏览器）。
    - z-ai page_reader 能绕过微信的反爬验证，返回真实文章 HTML。
    - 如果 z-ai 也失败，提示用户手动保存 HTML。
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    s = session or requests.Session()
    s.headers.update(headers)

    # ── 策略1: 直接 requests 抓取（最快，但可能被微信反爬拦截）──
    for attempt in range(3):
        try:
            resp = s.get(url, timeout=30)
            resp.raise_for_status()
            text = resp.text
            if "og:title" in text:
                return text
            logger.debug(f"第{attempt+1}次请求未获正文 (长度={len(text)})，重试...")
            time.sleep(2)
        except Exception as e:
            logger.error(f"抓取失败 {url}: {e}")
            break  # 直接进入回退策略

    logger.warning(f"直接抓取失败，尝试 z-ai page_reader 回退...")

    # ── 策略2: z-ai page_reader 回退（基于云端浏览器，能绕过反爬）──
    html = _fetch_via_zai_page_reader(url, logger)
    if html and "og:title" in html:
        logger.info("z-ai page_reader 抓取成功")
        return html

    logger.warning(f"多次重试仍无法获取正文: {url}")
    logger.warning("微信可能需要验证。请在浏览器中打开URL，Ctrl+S保存HTML后再处理。")
    return None


def _fetch_via_zai_page_reader(url, logger):
    """通过 z-ai page_reader CLI 抓取网页内容（回退策略）。

    z-ai page_reader 基于云端浏览器，能绕过微信的反爬验证。
    需要 z-ai CLI 已安装并配置。
    """
    import subprocess
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, prefix='zai_page_'
        ) as tmp:
            tmp_path = tmp.name

        result = subprocess.run(
            ['z-ai', 'function', '-n', 'page_reader',
             '-a', json.dumps({"url": url}), '-o', tmp_path],
            capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            logger.debug(f"z-ai page_reader 失败: {result.stderr[:200]}")
            return None

        with open(tmp_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        html = data.get('data', {}).get('html', '')
        os.unlink(tmp_path)
        return html if html else None

    except FileNotFoundError:
        logger.debug("z-ai CLI 未安装，跳过 page_reader 回退")
        return None
    except Exception as e:
        logger.debug(f"z-ai page_reader 异常: {e}")
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return None


# ─── 图片处理 ────────────────────────────────────────────────

def download_image(url, filepath, referer="https://mp.weixin.qq.com/"):
    """下载图片到指定路径"""
    headers = {
        "Referer": referer,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        ),
    }
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        resp = requests.get(url, headers=headers, stream=True, timeout=30)
        if resp.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            return True
        return False
    except Exception:
        return False


# ─── 图片压缩与格式转换 (v1.25：纯 Pillow，无外部 exe) ─────

def _detect_transparency(filepath):
    """检测图片是否有透明通道（需要 Pillow）"""
    try:
        from PIL import Image
        img = Image.open(filepath)
        has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
        if not has_alpha:
            return False
        if img.mode == 'P':
            img = img.convert('RGBA')
        if img.mode == 'RGBA':
            alpha = img.getchannel('A')
            return alpha.getextrema()[0] < 255
        return True
    except Exception:
        return False


def _is_animated_gif(filepath):
    """检测 GIF 是否为动图"""
    try:
        from PIL import Image
        img = Image.open(filepath)
        return getattr(img, 'is_animated', False) or getattr(img, 'n_frames', 1) > 1
    except Exception:
        return True  # 无法判断时保守处理为动图


def _compress_jpeg_with_pillow(filepath):
    """v1.13: 使用 Pillow 压缩 JPEG（无需外部工具）"""
    try:
        from PIL import Image
        img = Image.open(filepath)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        # 先保存到临时文件，如果更小则替换
        tmp = filepath + '.tmp.jpg'
        img.save(tmp, 'JPEG', quality=88, optimize=True, progressive=True)
        if os.path.getsize(tmp) < os.path.getsize(filepath):
            os.replace(tmp, filepath)
        else:
            os.remove(tmp)
    except Exception:
        pass


def _compress_gif_with_pillow(filepath):
    """v1.13: 使用 Pillow 压缩 GIF（无需外部工具）"""
    try:
        from PIL import Image
        img = Image.open(filepath)
        tmp = filepath + '.tmp.gif'
        # 保存时启用 optimize
        save_kwargs = {'optimize': True}
        if getattr(img, 'is_animated', False):
            save_kwargs['save_all'] = True
            save_kwargs['loop'] = getattr(img, 'loop', 0)
            save_kwargs['disposal'] = getattr(img, 'disposal', 2)
        img.save(tmp, 'GIF', **save_kwargs)
        if os.path.getsize(tmp) < os.path.getsize(filepath):
            os.replace(tmp, filepath)
        else:
            os.remove(tmp)
    except Exception:
        pass


def _optimize_png_with_pillow(filepath):
    """v1.25: Pillow 无损 PNG 优化（替代 oxipng）：仅在更小时替换，失败保留原文件。"""
    tmp = filepath + '.tmp.png'
    try:
        from PIL import Image
        with Image.open(filepath) as img:
            img.save(tmp, 'PNG', optimize=True)
        if os.path.getsize(tmp) < os.path.getsize(filepath):
            os.replace(tmp, filepath)
        else:
            os.remove(tmp)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)


def rewrite_converted_image_urls(content, cover_github_url, replacements):
    """将图片格式转换后的 URL 回写至已生成的正文和题图字段。"""
    for original_url, converted_url in replacements.items():
        content = content.replace(original_url, converted_url)
        if cover_github_url == original_url:
            cover_github_url = converted_url
    return content, cover_github_url


def compress_and_convert_image(filepath, logger=None):
    """v1.25: 压缩并转换图片为合规格式

    使用纯 Pillow（v1.25 起不再依赖 piczip/oxipng.exe）。
    无需安装任何系统级工具。

    规则（IE6 兼容，仅 jpg/png/gif）:
      - 不透明 PNG → 转为 JPG（体积更小）
      - 透明 PNG → 保留 PNG，Pillow 无损优化
      - 动图 GIF → 保留 GIF，Pillow 压缩
      - 静态 GIF → 转为 PNG（再按 PNG 规则处理）
      - JPEG → Pillow 压缩 (quality=88, progressive)
      - WebP/AVIF → 按透明度转为 JPG 或 PNG

    返回: (new_filepath, saved_bytes)
    """
    if not os.path.exists(filepath):
        return (filepath, 0)

    size_before = os.path.getsize(filepath)
    ext = filepath.rsplit('.', 1)[-1].lower() if '.' in filepath else ''
    base = filepath.rsplit('.', 1)[0] if '.' in filepath else filepath
    new_path = filepath

    try:
        # WebP/AVIF → JPG or PNG
        if ext in ('webp', 'avif'):
            is_transparent = _detect_transparency(filepath)
            if is_transparent:
                new_path = base + '.png'
                try:
                    from PIL import Image
                    img = Image.open(filepath)
                    img.save(new_path, 'PNG', optimize=True)
                    os.remove(filepath)
                    ext = 'png'
                except Exception:
                    new_path = filepath
            else:
                new_path = base + '.jpg'
                try:
                    from PIL import Image
                    img = Image.open(filepath)
                    img.convert('RGB').save(new_path, 'JPEG', quality=88, optimize=True, progressive=True)
                    os.remove(filepath)
                    ext = 'jpg'
                except Exception:
                    new_path = filepath

        # PNG 处理
        if ext == 'png':
            is_transparent = _detect_transparency(new_path)
            if not is_transparent:
                # 不透明 PNG → JPG
                jpg_path = base + '.jpg'
                try:
                    from PIL import Image
                    img = Image.open(new_path)
                    img.convert('RGB').save(jpg_path, 'JPEG', quality=88, optimize=True, progressive=True)
                    os.remove(new_path)
                    new_path = jpg_path
                    ext = 'jpg'
                except Exception:
                    pass
            else:
                # 透明 PNG → Pillow 无损优化
                _optimize_png_with_pillow(new_path)

        # 静态 GIF → PNG
        if ext == 'gif' and not _is_animated_gif(new_path):
            png_path = base + '.png'
            try:
                from PIL import Image
                img = Image.open(new_path)
                img.save(png_path, 'PNG', optimize=True)
                os.remove(new_path)
                new_path = png_path
                ext = 'png'
                # 新 PNG 再按 PNG 规则处理
                if not _detect_transparency(new_path):
                    jpg_path = base + '.jpg'
                    img.convert('RGB').save(jpg_path, 'JPEG', quality=88, optimize=True, progressive=True)
                    os.remove(new_path)
                    new_path = jpg_path
                    ext = 'jpg'
                else:
                    _optimize_png_with_pillow(new_path)
            except Exception:
                pass
        elif ext == 'gif':
            # 动图 GIF → Pillow 压缩
            _compress_gif_with_pillow(new_path)

        # JPEG 压缩（Pillow）
        if ext in ('jpg', 'jpeg'):
            _compress_jpeg_with_pillow(new_path)

    except Exception as e:
        if logger:
            logger.debug(f'压缩/转换失败 {filepath}: {e}')

    size_after = os.path.getsize(new_path) if os.path.exists(new_path) else size_before
    saved = max(0, size_before - size_after)
    return (new_path, saved)


# 向后兼容别名
def compress_image_local(filepath, logger=None):
    """v1.13: 兼容旧调用，实际调用 compress_and_convert_image"""
    new_path, saved = compress_and_convert_image(filepath, logger)
    return (True, saved)


def get_image_format_from_url(url):
    """从微信CDN图片URL路径判断原始图片格式"""
    if "mmbiz_png" in url:
        return "png"
    if "mmbiz_gif" in url:
        return "gif"
    # 微信webp在CDN上仍是jpg格式
    return "jpg"


def sanitize_image_url(url):
    """清理微信CDN图片URL中不必要的参数"""
    url = re.sub(r"[&?]tp=webp", "", url)
    url = re.sub(r"[&?]usePicPrefetch=\d*", "", url)
    url = re.sub(r"[&?]wxfrom=\d*", "", url)
    return url


def extract_first_image_url(html_content, soup=None):
    """从HTML的JS数据中提取正文第一张图片的原始URL（1:1大图）
    
    优先级：
    1. picture_page_info_list 中的1:1大图（贴图页面专用）
    2. js_content 中第一个 <img data-src>（长文正文原图，非og:image裁剪版）
    """
    # 方法1: window.picture_page_info_list (纯字符串)
    m = re.search(
        r"window\.picture_page_info_list\s*=\s*\[\s*\{[^}]*?"
        r"cdn_url\s*:\s*'(https?://[^']+)'",
        html_content,
    )
    if m:
        return m.group(1)
    # 方法2: 内联JS picture_page_info_list (JsDecode)
    m = re.search(
        r"picture_page_info_list\s*:\s*\[\s*\{[^}]*?"
        r"cdn_url\s*:\s*JsDecode\('(https?://[^']+)'\)",
        html_content,
    )
    if m:
        return m.group(1)
    # 方法3: 从 js_content 中提取第一个 <img data-src>（长文正文原图）
    # og:image 是裁剪版封面，而正文中的 <img data-src> 才是原始大图
    if soup:
        content_div = soup.find("div", id="js_content")
        if not content_div:
            content_div = soup.find("div", class_="rich_media_content")
        if content_div:
            for img in content_div.find_all("img"):
                classes = img.get("class", [])
                if any(c in classes for c in ["wx_follow_avatar", "we-emoji"]):
                    continue
                img_url = img.get("data-src") or img.get("src", "")
                if not img_url:
                    continue
                if "wx.qlogo.cn" in img_url or "mmhead" in img_url:
                    continue
                if "we-emoji" in img_url:
                    continue
                return sanitize_image_url(img_url)
    return None


def extract_all_images_from_html(soup, html_content=None):
    """从HTML中提取所有正文图片URL（原始最大尺寸，跳过头像/emoji）。
    返回有序列表，每个元素为图片URL字符串。"""
    images = []
    seen_ids = set()

    # 优先：从 picture_page_info_list 提取所有原图（1:1大图）
    if html_content:
        # 方法1: window.picture_page_info_list
        pattern1 = r"window\.picture_page_info_list\s*=\s*(\[.*?\])\s*;"
        m = re.search(pattern1, html_content, re.DOTALL)
        if m:
            try:
                # 尝试解析JSON
                list_str = m.group(1)
                # 替换单引号为双引号
                list_str = list_str.replace("'", '"')
                pic_list = json.loads(list_str)
                for item in pic_list:
                    cdn_url = item.get("cdn_url", "")
                    if cdn_url and cdn_url not in seen_ids:
                        seen_ids.add(cdn_url)
                        images.append(cdn_url)
            except (json.JSONDecodeError, Exception):
                pass

        # 方法2: JsDecode 格式
        if not images:
            for m in re.finditer(
                r"cdn_url\s*:\s*JsDecode\('(https?://[^']+)'\)",
                html_content,
            ):
                url = m.group(1)
                if url not in seen_ids:
                    seen_ids.add(url)
                    images.append(url)

    # 回退：从 img 标签提取（data-src 优先于 src）
    if not images:
        content_div = soup.find("div", id="js_content")
        if not content_div:
            content_div = soup

        for img in content_div.find_all("img"):
            # 跳过头像/emoji
            classes = img.get("class", [])
            if any(c in classes for c in ["wx_follow_avatar", "we-emoji"]):
                continue

            img_url = img.get("data-src") or img.get("src", "")
            if not img_url:
                continue
            # 跳过头像URL
            if "wx.qlogo.cn" in img_url or "mmhead" in img_url:
                continue
            # 跳过小图标
            if "we-emoji" in img_url:
                continue

            if img_url not in seen_ids:
                seen_ids.add(img_url)
                images.append(img_url)

    return images


# ─── HTML → Markdown 核心转换 ─────────────────────────────────

def clean_soup(soup):
    """清理无关HTML元素"""
    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for div in soup.select(".emoji-panel, .fixed-footer, .ad-container, .rich_media_tool"):
        div.decompose()
    # 移除头像区域
    for avatar in soup.find_all(class_="wx_follow_avatar"):
        avatar.decompose()
    return soup


def extract_date(soup, html_content, fallback_name="", logger=None):
    """从HTML中提取发布日期

    优先级：
    0. 从正文中"文 / 书航 YYYY.MM.DD"格式的日期（文章内标注的日期最准确）
    1. 从 JavaScript 变量 createTime 提取
    2. 从 create_timestamp 提取
    3. 从 meta 标签提取
    4. 从文件名提取

    注意：微信后台的发布日期可能与文章内显示的日期不同，
    以文章正文中的日期为准（如"文 / 书航 2025.12.11"）。
    """
    # 0. 从正文提取"文 / 书航 YYYY.MM.DD"格式的日期（最高优先级）
    # 匹配多种变体：文 / 书航 2025.12.11 / 文/书航 2025.12.11 / 文 / 书航 2025.12.11
    # v1.28: 允许「书航」与日期之间无空格（文/书航2025.12.11），
    # 月份/日期允许一位数（2026.9.5）；分隔符支持 . 和 -
    # 转载稿（如公司稿件）公众号发布时间晚于实际首发，blog 日期以正文标注为准。
    m = re.search(
        r'文\s*/\s*书航\s*(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})',
        html_content,
    )
    if m:
        y, mo, d = m.groups()
        date_str = f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
        if logger:
            logger.info(f"日期来源: 正文标注「文 / 书航」→ {date_str}")
        return date_str

    # 1. 从 JavaScript 变量 createTime 提取
    for script_match in re.finditer(r"var\s+createTime\s*=\s*'(\d{4})-(\d{1,2})-(\d{1,2})", html_content):
        y, m, d = script_match.groups()
        date_str = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
        if logger:
            logger.debug(f"日期来源: JS createTime → {date_str}")
        return date_str

    # 2. 从 create_timestamp 提取
    m = re.search(r"create_timestamp[:\s]*['\"]?(\d{5,})", html_content)
    if m:
        ts = int(m.group(1))
        dt = datetime.fromtimestamp(ts)
        date_str = dt.strftime("%Y-%m-%d")
        if logger:
            logger.debug(f"日期来源: create_timestamp → {date_str}")
        return date_str

    # 3. 从 meta 标签提取
    for prop in ["article:published_time", "og:article:published_time"]:
        tag = soup.find("meta", property=prop)
        if tag and tag.get("content"):
            try:
                date_str = datetime.fromisoformat(tag["content"][:10]).strftime("%Y-%m-%d")
                if logger:
                    logger.debug(f"日期来源: meta {prop} → {date_str}")
                return date_str
            except ValueError:
                pass

    # 4. 从文件名提取
    m = re.search(r"(\d{4})[\.-](\d{1,2})[\.-](\d{1,2})", fallback_name)
    if m:
        y, mo, d = m.groups()
        date_str = f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
        if logger:
            logger.debug(f"日期来源: 文件名 → {date_str}")
        return date_str

    date_str = datetime.now().strftime("%Y-%m-%d")
    if logger:
        logger.warning(f"日期来源: 未找到，使用当前日期 → {date_str}")
    return date_str


def _is_tietu_page(html_content):
    """检测是否为贴图(IMG_SHARE_PAGE)页面。
    
    贴图页面的特征：
    - item_show_type = 8
    - 没有 js_content div
    - 有 share_content_page 结构
    - 内容通过 picture_page_info_list 和 og:description 提供
    """
    # 方法1: 检查 item_show_type
    m = re.search(r"item_show_type\s*[:=]\s*['\"]?8", html_content)
    if m:
        return True
    # 方法2: 检查页面类型标记
    if "share_content_page" in html_content and "IMG_SHARE_PAGE" in html_content:
        return True
    return False


def extract_embedded_links(html_content):
    """从微信文章HTML中提取嵌入的其他文章链接。
    
    来源：
    - JsDecode('http://mp.weixin.qq.com/s?__biz=...') 格式
    - 这些链接对应文章中提到的《标题》引用
    """
    links = []  # (url, title_hint) 列表
    seen = set()

    # 提取 JsDecode 中的 mp.weixin.qq.com/s?__biz= 格式链接（多图文/嵌入链接）
    for m in re.finditer(
        r"JsDecode\('(https?://mp\.weixin\.qq\.com/s\?[^']+)'\)",
        html_content,
    ):
        url = m.group(1)
        # 解码转义
        url = url.replace("\\x26amp;", "&").replace("\\x26", "&")
        url = url.replace("\\/", "/")
        if url.startswith("http://"):
            url = "https://" + url[7:]
        # 去重（排除文章自身的URL）
        og_url_m = re.search(
            r'property="og:url"[^>]*content="([^"]+)"', html_content
        )
        if og_url_m and url == og_url_m.group(1):
            continue
        if url not in seen:
            seen.add(url)
            links.append(url)

    # 提取 JsDecode 中的 mp.weixin.qq.com/s/xxx 格式链接
    for m in re.finditer(
        r"JsDecode\('(https?://mp\.weixin\.qq\.com/s/[A-Za-z0-9_-]+)'\)",
        html_content,
    ):
        url = m.group(1)
        if url.startswith("http://"):
            url = "https://" + url[7:]
        og_url_m = re.search(
            r'property="og:url"[^>]*content="([^"]+)"', html_content
        )
        if og_url_m and url == og_url_m.group(1):
            continue
        if url not in seen:
            seen.add(url)
            links.append(url)

    return links


def detect_article_type(soup, html_content):
    """自动识别文章类型：'long'（长文）或 'short'（短篇）
    
    判断依据：
    - 贴图页面（item_show_type=8）→ 短篇
    - js_content 中 h2/h3 标题数量
    - js_content 中纯文本长度
    - 图片数量
    """
    # 优先检查贴图页面（这类页面没有js_content，需要特殊处理）
    if _is_tietu_page(html_content):
        return "short"

    content_div = soup.find("div", id="js_content")
    if not content_div:
        content_div = soup.find("div", class_="rich_media_content")
    if not content_div:
        return "short"

    # 统计标题
    headings = content_div.find_all(["h1", "h2", "h3"])
    heading_count = len(headings)

    # 统计纯文本长度
    text = content_div.get_text(strip=True)
    text_len = len(text)

    # 统计图片数量
    images = content_div.find_all("img")
    img_count = len([i for i in images
                     if not any(c in i.get("class", [])
                                for c in ["wx_follow_avatar", "we-emoji"])])

    # 长文判定：有足够标题 + 足够文字
    if heading_count >= LONG_ARTICLE_MIN_HEADINGS and text_len >= LONG_ARTICLE_MIN_CHARS:
        return "long"
    # 有标题但文字不多——如果标题>=2，很可能是长文（短篇通常无标题或只有1个）
    if heading_count >= LONG_ARTICLE_MIN_HEADINGS:
        return "long"
    # 短篇可能文字也不少但没有标题结构
    if text_len < LONG_ARTICLE_MIN_CHARS and img_count <= 3:
        return "short"

    return "short"


def _inline_to_md(element):
    """将内联HTML元素转换为Markdown文本（递归处理粗体/斜体/链接）
    
    注意：微信文章中可能存在嵌套的<a>标签（无效HTML），例如：
    <a href="url1"><a href="url2"><a href="url3">阅读原文</a></a></a>
    这种情况下，只使用最内层（文本最近）的<a>标签的href，
    避免生成嵌套的Markdown链接 [[text](url1)](url2)。
    """
    if element.name is None:
        # 纯文本节点
        return str(element)

    # 跳过图片（图片单独处理）
    if element.name == "img":
        return ""

    if element.name == "br":
        return "\n"

    # 递归处理子节点
    inner = "".join(_inline_to_md(child) for child in element.children)

    if element.name in ("strong", "b"):
        stripped = inner.strip()
        if stripped:
            return f"**{stripped}**"
        return inner
    if element.name in ("em", "i"):
        stripped = inner.strip()
        if stripped:
            return f"*{stripped}*"
        return inner
    if element.name == "a":
        href = element.get("href", "")
        # 清理微信跳转链接
        if href and "mp.weixin.qq.com" in href:
            href = html_mod.unescape(href)
        link_text = inner.strip()
        if href and link_text:
            # 检测嵌套链接：如果inner已经是Markdown链接格式[text](url)，
            # 说明子节点中已有<a>标签被转换。只保留内层链接，不嵌套。
            if re.match(r'^\[.*\]\(https?://.*\)$', link_text):
                return link_text
            return f"[{link_text}]({href})"
        return link_text
    if element.name == "code":
        return f"`{inner.strip()}`"

    return inner


def _is_cover_image(img_url, cover_image_url):
    """检查图片URL是否与题图相同（用于去重）。
    微信CDN URL可能有参数差异，比较核心路径部分。
    同时也通过图片ID（canonical identifier）进行去重，
    解决同一图片不同尺寸参数（如/640 vs /0）导致的误判。
    """
    if not cover_image_url or not img_url:
        return False
    # 精确匹配
    if img_url == cover_image_url:
        return True
    # 去掉参数后比较路径
    def _path(url):
        return url.split("?")[0].rstrip("/")
    if _path(img_url) == _path(cover_image_url):
        return True
    # 通过图片canonical ID比较（同一图片不同尺寸也视为相同）
    if _get_image_canonical_id(img_url) and _get_image_canonical_id(cover_image_url):
        if _get_image_canonical_id(img_url) == _get_image_canonical_id(cover_image_url):
            return True
    return False


def _get_image_canonical_id(url):
    """从微信CDN图片URL中提取canonical标识符，用于去重。
    
    微信CDN URL格式: https://mmbiz.qpic.cn/mmbiz_jpg/{hash1}/{hash2}/{size}?{params}
    其中 hash1+hash2 组合唯一标识一张图片，不同size只是缩放。
    
    返回 'hash1/hash2' 或 None（非微信CDN图片）。
    """
    m = re.match(
        r'https?://mmbiz\.qpic\.cn/(mmbiz_\w+)/([\w=]+)/([\w=]+)',
        url
    )
    if m:
        return f"{m.group(2)}/{m.group(3)}"
    # 其他CDN格式尝试
    m = re.match(
        r'https?://mmbiz\.qlogo\.cn/(mmbiz_\w+)/([\w=]+)/([\w=]+)',
        url
    )
    if m:
        return f"{m.group(2)}/{m.group(3)}"
    return None


def _add_image_element(img_tag, cover_image_url, images_to_download, lines,
                       seen_canonical_ids=None):
    """处理单个<img>标签，加入images_to_download列表和Markdown输出。
    
    seen_canonical_ids: 已见过的图片canonical ID集合，用于跨URL去重
    （同一图片可能以不同URL/尺寸出现多次）。
    """
    classes = img_tag.get("class", [])
    if any(c in classes for c in ["wx_follow_avatar", "we-emoji"]):
        return

    img_url = img_tag.get("data-src") or img_tag.get("src", "")
    if not img_url:
        return
    if "wx.qlogo.cn" in img_url or "mmhead" in img_url:
        return

    img_url = sanitize_image_url(img_url)

    # 跳过与题图相同的URL（避免重复）
    if _is_cover_image(img_url, cover_image_url):
        return

    # 通过canonical ID去重（同一图片不同尺寸参数）
    if seen_canonical_ids is not None:
        canon_id = _get_image_canonical_id(img_url)
        if canon_id and canon_id in seen_canonical_ids:
            return
        if canon_id:
            seen_canonical_ids.add(canon_id)

    if img_url not in images_to_download:
        images_to_download.append(img_url)

    lines.append(f"![]({{'IMG_URL'}}:{img_url})")


def _convert_blockquote_inner(blockquote, cover_image_url, seen_canonical_ids=None):
    """处理blockquote内部内容，返回Markdown行列表。"""
    parts = []
    for child in blockquote.children:
        if child.name in ("p", "section"):
            # 处理blockquote内的段落（保留内联格式）
            # blockquote内的图片也要处理
            for img in child.find_all("img"):
                _add_image_element(img, cover_image_url, [], parts,
                                   seen_canonical_ids=seen_canonical_ids)
            text = _inline_to_md(child).strip()
            if text:
                parts.append(text)
        elif child.name in ("ul", "ol"):
            for li in child.find_all("li", recursive=False):
                li_text = _inline_to_md(li).strip()
                if li_text:
                    parts.append(f"- {li_text}")
        elif child.name is None:
            text = str(child).strip()
            if text:
                parts.append(text)
    return parts


def convert_long_article(soup, html_content, post_date, slug, logger):
    """长文(blog)转换：完整HTML→Markdown，保留所有格式。
    
    修复旧脚本问题：
    - ✅ 粗体 → **text**
    - ✅ 斜体 → *text*
    - ✅ 链接 → [text](url)
    - ✅ 无序列表 → - item
    - ✅ blockquote不重复
    - ✅ 题图不与front matter重复
    - ✅ 深层section嵌套正确遍历
    
    策略：在 js_content 内按文档序收集所有"叶"内容元素
    （h1-h4, p, img, blockquote, ul, ol），跳过 section/div 包装层。
    当遇到 blockquote 时，整体处理并标记其后代为"已处理"，
    避免内容重复。
    """
    year, month, day = post_date.split("-")
    content_div = soup.find("div", id="js_content")
    if not content_div:
        content_div = soup.find("div", class_="rich_media_content")
    if not content_div:
        logger.warning("未找到文章正文div")
        return None, [], {}, ""

    # 获取题图URL（用于去重）
    # 优先使用正文第一张图（1:1大图），而非og:image裁剪版
    cover_url = extract_first_image_url(html_content, soup=soup)
    # 回退：从HTML原始内容提取 og:image
    if not cover_url:
        m = re.search(r'property="og:image"\s+content="([^"]+)"', html_content)
        if not m:
            m = re.search(r'content="([^"]+)"\s+property="og:image"', html_content)
        if m:
            cover_url = m.group(1)

    images_to_download = []  # 按出现顺序收集图片URL
    markdown_lines = []
    seen_canonical_ids = set()  # 用于跨URL去重（同一图片不同尺寸）

    # ── 步骤1：收集所有 blockquote 的后代 id，用于去重 ──
    blockquote_desc_ids = set()
    for bq in content_div.find_all("blockquote"):
        for desc in bq.descendants:
            blockquote_desc_ids.add(id(desc))

    # ── 步骤2：按文档序遍历所有内容元素 ──
    # v1.9 修复：新增 "section" 标签——部分微信文章正文在 section 内
    # 而非 p 内，且标题用 section 而非 h2/h3。
    all_elements = content_div.find_all(
        ["h1", "h2", "h3", "h4", "p", "img", "blockquote", "ul", "ol", "section"]
    )

    processed_ids = set()  # 已处理的元素id（防重复）
    processed_img_ids = set()  # 已处理的<img>元素id（防止p内img被重复处理）
    processed_section_ids = set()  # v1.9: 已处理的 section（防止嵌套 section 重复）

    for element in all_elements:
        eid = id(element)
        if eid in processed_ids:
            continue

        # 如果元素是 blockquote 的后代，跳过（由 blockquote 统一处理）
        if eid in blockquote_desc_ids and element.name != "blockquote":
            continue

        # ── 标题 ──
        if element.name in ("h1", "h2", "h3", "h4"):
            text = element.get_text(strip=True)
            if text:
                level = int(element.name[1])
                markdown_lines.append(f"{'#' * level} {text}")

        # ── 引用块 ──
        elif element.name == "blockquote":
            inner_lines = _convert_blockquote_inner(element, cover_url, seen_canonical_ids=seen_canonical_ids)
            for line in inner_lines:
                stripped = line.strip()
                if stripped:
                    markdown_lines.append(f"> {stripped}")
            # 标记 blockquote 所有后代为已处理
            for desc in element.descendants:
                processed_ids.add(id(desc))
                if desc.name == "img":
                    processed_img_ids.add(id(desc))
            processed_ids.add(eid)

        # ── 列表 ──
        elif element.name in ("ul", "ol"):
            for li in element.find_all("li", recursive=False):
                li_text = _inline_to_md(li).strip()
                if li_text:
                    markdown_lines.append(f"- {li_text}")

        # ── 段落 ──
        elif element.name == "p":
            # 段落中可能包含 <img>，先处理图片
            for img in element.find_all("img"):
                img_eid = id(img)
                if img_eid not in processed_img_ids:
                    _add_image_element(img, cover_url, images_to_download, markdown_lines,
                                       seen_canonical_ids=seen_canonical_ids)
                    processed_img_ids.add(img_eid)
            # 再处理内联文本（粗体/斜体/链接）
            p_text = _inline_to_md(element).strip()
            if p_text:
                markdown_lines.append(p_text)

        # ── 图片 ──
        elif element.name == "img":
            # 跳过已在段落内处理过的图片
            if eid not in processed_img_ids:
                _add_image_element(element, cover_url, images_to_download, markdown_lines,
                                   seen_canonical_ids=seen_canonical_ids)
                processed_img_ids.add(eid)

        # ── section (v1.9 新增) ──
        # 处理直接含文本的叶 section（无嵌套 section/p/img 等子内容元素）
        # 微信部分文章正文在 section 内而非 p 内，标题也用 section 而非 h2/h3
        elif element.name == "section":
            # 跳过嵌套 section 的父级（只处理叶 section）
            if element.find("section"):
                # 标记父级已处理，避免其文本被重复提取
                processed_section_ids.add(eid)
                continue
            # 跳过已被处理的 section
            if eid in processed_section_ids:
                continue
            # 跳过含图片的 section（图片由 img 处理）
            if element.find("img"):
                # 提取不含图片的文本
                p_text = _inline_to_md(element).strip()
                if p_text and len(p_text) > 2:
                    # 跳过尾部推广
                    if "想跟作者进一步讨论本文" not in p_text:
                        markdown_lines.append(p_text)
                processed_section_ids.add(eid)
                continue
            # 纯文本叶 section
            text = element.get_text(strip=True)
            if text and len(text) > 2:
                # 跳过尾部推广
                if "想跟作者进一步讨论本文" not in text:
                    markdown_lines.append(text)
            processed_section_ids.add(eid)

    # ── 步骤3：生成图片映射（分配编号） ──
    cover_img_url = cover_url  # 优先使用 picture_page_info_list 中的1:1大图

    image_mapping = {}  # 微信URL → GitHub URL

    # 题图 = 01
    cover_github_url = ""
    if cover_img_url:
        img_ext = get_image_format_from_url(cover_img_url)
        cover_github_url = f"{GITHUB_IMAGE_BASE}/{year}/{month}/{day}/{slug}/01.{img_ext}"
        image_mapping[cover_img_url] = cover_github_url

    # 其余图片从02开始编号
    img_idx = 2
    for img_url in images_to_download:
        if _is_cover_image(img_url, cover_img_url):
            # 题图已在正文中被跳过，不重复
            continue
        img_ext = get_image_format_from_url(img_url)
        github_url = f"{GITHUB_IMAGE_BASE}/{year}/{month}/{day}/{slug}/{img_idx:02d}.{img_ext}"
        image_mapping[img_url] = github_url
        img_idx += 1

    # ── 步骤4：替换图片占位符 ──
    content = "\n\n".join(markdown_lines)
    for wx_url, gh_url in image_mapping.items():
        content = content.replace(f"{{'IMG_URL'}}:{wx_url}", gh_url)

    # ── 步骤5：清理 ──
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = re.sub(r"以下文章来源于.*?\n\n", "", content, flags=re.DOTALL)
    # 清理"🔈想跟作者进一步讨论本文"及之后的所有内容
    # 这段之后通常是嵌套的阅读原文链接和二维码推广，全部删除
    content = re.sub(r"🔈想跟作者进一步讨论本文.*", "", content, flags=re.DOTALL)
    # 额外清理：如果🔊/🔈 emoji被html_mod.unescape破坏，也清理纯文本版本
    content = re.sub(r"想跟作者进一步讨论本文.*", "", content, flags=re.DOTALL)
    # 清理残留的嵌套Markdown链接（如 [[[[阅读原文](url)](url)](url)] ）
    content = _clean_nested_links(content)
    # 清理"详情请参考：[阅读原文](url)"后面可能的多余空行
    content = re.sub(r"详情请参考：\[阅读原文\]\(https?://mp\.weixin\.qq\.com.*?\)", "", content)

    return content.strip(), images_to_download, image_mapping, cover_github_url


def convert_short_article(soup, html_content, post_date, slug, logger):
    """短篇(short)转换：提取正文+图片平铺。
    
    支持两种页面结构：
    1. 常规短文：有 js_content div，从中提取 <p> 文本和图片
    2. 贴图(IMG_SHARE_PAGE)：无 js_content，内容在 og:description 和
       picture_page_info_list 中，链接在 JsDecode 数据中
    
    输出格式：
    - 第一张图 = 题图（front matter image）
    - 正文文本（来自 <p> 标签或 og:description）
    - 嵌入链接（来自 JsDecode 数据，转为 [描述](URL) 格式）
    - 其余图片平铺在文字下方
    """
    year, month, day = post_date.split("-")
    content_div = soup.find("div", id="js_content")
    if not content_div:
        content_div = soup.find("div", class_="rich_media_content")

    is_tietu = _is_tietu_page(html_content)
    logger.info(f"短篇类型: {'贴图(IMG_SHARE_PAGE)' if is_tietu else '常规短文'}")

    images_to_download = []
    image_mapping = {}

    # 提取所有图片
    all_images = extract_all_images_from_html(soup, html_content)
    logger.info(f"短篇：找到 {len(all_images)} 张图片")

    # 去重：图片列表中可能有重复URL或同一图片不同尺寸
    seen_img_urls = set()
    seen_canonical_ids = set()
    deduped_images = []
    for img_url in all_images:
        clean_url = sanitize_image_url(img_url)
        if clean_url in seen_img_urls:
            continue
        # 通过canonical ID去重（同一图片不同尺寸参数）
        canon_id = _get_image_canonical_id(clean_url)
        if canon_id and canon_id in seen_canonical_ids:
            continue
        seen_img_urls.add(clean_url)
        if canon_id:
            seen_canonical_ids.add(canon_id)
        deduped_images.append(img_url)
    all_images = deduped_images

    # 分配图片编号和GitHub URL
    for idx, img_url in enumerate(all_images):
        img_url = sanitize_image_url(img_url)
        new_idx = idx + 1  # 从01开始
        img_ext = get_image_format_from_url(img_url)
        github_url = f"{GITHUB_IMAGE_BASE}/{year}/{month}/{day}/{slug}/{new_idx:02d}.{img_ext}"
        image_mapping[img_url] = github_url
        images_to_download.append(img_url)

    # 题图 = 第一张图
    cover_github_url = ""
    if all_images:
        first_url = sanitize_image_url(all_images[0])
        cover_github_url = image_mapping.get(first_url, "")

    # ── 提取正文文本 ──
    content = ""

    if is_tietu:
        # 贴图页面：正文从 og:description 提取
        # 注意：soup 可能已经被 clean_soup 清理过（meta标签被删除）
        # 所以优先从 html_content 原始文本中提取
        desc_content = ""
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            desc_content = og_desc["content"]
        else:
            # 从原始HTML中提取
            m = re.search(
                r'property="og:description"[^>]*content="([^"]+)"',
                html_content,
            )
            if not m:
                m = re.search(
                    r'content="([^"]+)"[^>]*property="og:description"',
                    html_content,
                )
            if m:
                desc_content = m.group(1)

        if desc_content:
            content = desc_content
            # 解码微信转义
            content = content.replace("\\x0a", "\n").replace(r"\x0a", "\n")
            content = content.replace("\\x26amp;", "&").replace(r"\x26amp;", "&")
            content = content.replace("\\x26nbsp;", " ").replace(r"\x26nbsp;", " ")
            content = content.replace("\\x26", "&").replace(r"\x26", "&")
            content = html_mod.unescape(content)
            # 清理尾部广告文字
            content = _clean_tail_promo(content)
    else:
        # 常规短文：从 js_content 提取
        if content_div:
            paragraphs = []
            seen_texts = set()  # 去重

            for element in content_div.find_all("p"):
                # 跳过仅含图片的p标签
                if element.find("img") and not element.get_text(strip=True):
                    continue
                text = _inline_to_md(element).strip()
                if text and len(text) > 2 and text not in seen_texts:
                    seen_texts.add(text)
                    paragraphs.append(text)

            # v1.9 修复：如果 <p> 提取的内容过少（< 100 字符），
            # 微信部分文章正文在 <section> 标签内而非 <p>，
            # 需要从 <section> 补充提取文本。
            # 典型场景：标题用 section 而非 h2/h3，段落也直接在 section 中。
            if sum(len(p) for p in paragraphs) < 100:
                section_paragraphs = []
                section_seen_texts = set()
                for section in content_div.find_all("section"):
                    # 跳过含嵌套 section 的（只取叶节点 section）
                    if section.find("section"):
                        continue
                    # 跳过仅含图片的 section
                    if section.find("img") and not section.get_text(strip=True):
                        continue
                    text = _inline_to_md(section).strip()
                    # 跳过尾部推广
                    if "想跟作者进一步讨论本文" in text:
                        continue
                    if text and len(text) > 2 and text not in section_seen_texts \
                       and text not in seen_texts:
                        section_seen_texts.add(text)
                        section_paragraphs.append(text)
                # 如果 section 提取到更多内容，用它替换
                if sum(len(p) for p in section_paragraphs) > \
                   sum(len(p) for p in paragraphs):
                    paragraphs = section_paragraphs

            if paragraphs:
                content = "\n\n".join(paragraphs)

        # 回退到 og:description
        if not content:
            desc_content = ""
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                desc_content = og_desc["content"]
            else:
                m = re.search(
                    r'property="og:description"[^>]*content="([^"]+)"',
                    html_content,
                )
                if m:
                    desc_content = m.group(1)
            if desc_content:
                content = desc_content
                content = content.replace(r"\x0a", "\n").replace("\x0a", "\n")
                content = content.replace(r"\x26", "&").replace("\x26", "&")
                content = html_mod.unescape(content)
                content = _clean_short_links(content)

    # ── 插入嵌入链接 ──
    # 提取文章中引用的其他微信文章链接
    embedded_links = extract_embedded_links(html_content)
    if embedded_links:
        content = _insert_embedded_links(content, embedded_links, logger)

    # ── 清理嵌套链接和尾部推广 ──
    content = _clean_nested_links(content)
    content = _clean_tail_promo(content)

    # ── 追加图片（从第2张开始平铺） ──
    additional_images = []
    for idx, img_url in enumerate(all_images):
        if idx == 0:
            continue  # 跳过题图
        img_url = sanitize_image_url(img_url)
        gh_url = image_mapping.get(img_url, "")
        if gh_url:
            additional_images.append(f"![配图{idx+1}]({gh_url})")

    if additional_images:
        content = content.rstrip() + "\n\n" + "\n\n".join(additional_images)

    return content.strip(), images_to_download, image_mapping, cover_github_url


def _clean_short_links(text):
    """清理短文中的HTML链接标签，转为Markdown格式"""
    # 将<a>标签转换为Markdown链接格式
    def replace_link(match):
        href = match.group(1)
        link_text = match.group(2)
        href = href.replace("&amp;", "&")
        return f"[{link_text}]({href})"

    text = re.sub(r'<a[^>]*?href=["\']([^"\'>]+)["\'][^>]*?>([^<]*?)</a>', replace_link, text)
    # 移除其他HTML标签
    text = re.sub(r"<[^>]+>", "", text)
    return text


def _clean_tail_promo(text):
    """清理文章尾部的推广文字（航通社读者群等）。
    
    贴图文章的 og:description 包含尾部推广文字，需要清理：
    - "想跟作者进一步讨论本文，欢迎您加入航通社的读者交流群！..."
    - "请添加入群小助理个人号..."
    """
    # 清理读者群推广
    text = re.sub(
        r"\n*想跟作者进一步讨论本文.*",
        "",
        text,
        flags=re.DOTALL,
    )
    # 清理"请添加入群小助理"行
    text = re.sub(
        r"\n*请添加入群小助理个人号.*",
        "",
        text,
        flags=re.DOTALL,
    )
    return text.strip()


def _clean_nested_links(text):
    """清理嵌套的Markdown链接格式。
    
    微信文章底部常有嵌套的<a>标签（无效HTML），_inline_to_md可能产生：
    [[[[[阅读原文](url1)](url2)](url3)](url4)](url5)
    
    策略：只保留最内层的 [text](url) 链接，去掉外层包裹。
    """
    # 反复清理外层包裹的 [...](url)，直到没有嵌套
    prev = None
    while prev != text:
        prev = text
        # 匹配: [ 已经是Markdown链接的内容 ](url)
        # 即 [\s*[text](inner_url)\s*](outer_url)
        text = re.sub(
            r'\[\s*(\[[^\]]*\]\([^)]*\))\s*\]\([^)]*\)',
            r'\1',
            text,
        )
    return text


def _insert_embedded_links(content, embedded_links, logger=None):
    """将嵌入的文章链接插入到正文中适当位置。
    
    策略：
    - 如果正文提到"点击下方嵌入链接阅读"，在对应位置插入链接
    - 如果正文提到"扫码阅读原文"或"识别图中二维码"，在对应位置插入链接
    - 如果正文中已有 [阅读原文](url) 格式（由 _inline_to_md 生成），
      不再重复替换，避免产生 [[阅读原文](url1)](url2) 嵌套
    - 否则，在正文末尾追加链接
    - 多个链接时，每个只替换一次，避免重复替换已生成的Markdown链接
    """
    if not embedded_links:
        return content

    # 跟踪已替换的关键词位置，避免同一个词被多个URL重复替换
    replaced_keywords = set()

    for url in embedded_links:
        # 生成链接描述
        link_text = "阅读原文"
        inserted = False

        # 尝试匹配正文中的提示文字（按优先级尝试）
        for keyword in ["点击下方嵌入链接阅读", "嵌入链接", "扫码阅读原文"]:
            if keyword in content and keyword not in replaced_keywords:
                # 先检查该关键词是否已在Markdown链接内（避免嵌套）
                # 简单检测：关键词前是否有 "](" 模式
                idx = content.find(keyword)
                if idx > 0:
                    before = content[:idx]
                    # 如果关键词已被包裹在 [xxx](url) 中，跳过
                    if re.search(r'\[[^\]]*$', before):
                        continue
                content = content.replace(
                    keyword,
                    f"[{keyword}]({url})",
                    1,  # 只替换第一个
                )
                replaced_keywords.add(keyword)
                inserted = True
                break

        if not inserted and "阅读原文" in content and "阅读原文" not in replaced_keywords:
            # 检查"阅读原文"是否已在Markdown链接中
            # 避免: [阅读原文](url1) 被替换为 [[阅读原文](url1)](url2)
            idx = content.find("阅读原文")
            if idx >= 0:
                before = content[:idx]
                after = content[idx + len("阅读原文"):]
                # 如果"阅读原文"后面紧跟 ]( ，说明已经是Markdown链接的一部分
                if after.lstrip().startswith("]("):
                    # 已经是链接，视为已处理，不再追加
                    replaced_keywords.add("阅读原文")
                    inserted = True
                # 如果"阅读原文"前面是 [ ，也说明已在链接中
                elif before.rstrip().endswith("["):
                    replaced_keywords.add("阅读原文")
                    inserted = True
                else:
                    content = content.replace(
                        "阅读原文",
                        f"[阅读原文]({url})",
                        1,
                    )
                    replaced_keywords.add("阅读原文")
                    inserted = True

        if not inserted:
            # 在正文末尾追加
            content = content.rstrip() + f"\n\n详情请参考：[{link_text}]({url})"

    if logger and embedded_links:
        logger.debug(f"插入了 {len(embedded_links)} 个嵌入链接")

    return content



# ─── 微信合集(Album) API ───────────────────────────────────

def fetch_album_page(session, album_id, begin_msgid="", begin_itemidx="",
                     count=ALBUM_PAGE_SIZE, is_reverse=0):
    """抓取合集一页文章列表（JSON API）。

    返回: (article_list, continue_flag)
    """
    params = {
        "action": "getalbum",
        "__biz": ALBUM_BIZ,
        "album_id": album_id,
        "count": count,
        "begin_msgid": begin_msgid,
        "begin_itemidx": begin_itemidx,
        "is_reverse": is_reverse,
        "f": "json",
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": (
            f"https://mp.weixin.qq.com/mp/appmsgalbum?"
            f"__biz={ALBUM_BIZ}&action=getalbum&album_id={album_id}"
        ),
        "X-Requested-With": "XMLHttpRequest",
    }
    try:
        resp = session.get(ALBUM_API_URL, params=params,
                           headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("base_resp", {}).get("ret") != 0:
            return [], "0"
        album_resp = data.get("getalbum_resp", {})
        articles = album_resp.get("article_list", [])
        if not isinstance(articles, list):
            articles = [articles] if articles else []
        continue_flag = album_resp.get("continue_flag", "0")
        return articles, continue_flag
    except Exception:
        return [], "0"


def collect_album_urls(logger, album_config, since_date=None, until_date=None,
                       max_pages=None):
    """从单个合集遍历文章URL，可选按日期范围过滤。

    参数:
      album_config: 合集配置 dict (name, album_id, categories, tags)
      since_date: 起始日期 (datetime)，None=不限
      until_date: 截止日期 (datetime)，None=不限
      max_pages:  最多遍历几页，None=不限
    返回:
      [{'url': ..., 'title': ..., 'date': 'YYYY-MM-DD',
        'categories': ..., 'tags': ...}, ...]
      最新在前
    """
    session = requests.Session()
    all_articles = []
    begin_msgid = ""
    begin_itemidx = ""
    page = 0
    album_name = album_config["name"]
    album_id = album_config["album_id"]

    logger.info(f"开始遍历合集 [{album_name}] (album_id={album_id})")
    if since_date:
        logger.info(f"  起始日期: {since_date.strftime('%Y-%m-%d')}")
    if until_date:
        logger.info(f"  截止日期: {until_date.strftime('%Y-%m-%d')}")

    while True:
        page += 1
        if max_pages and page > max_pages:
            logger.info(f"  [{album_name}] 已达到最大页数限制 ({max_pages})")
            break

        articles, cf = fetch_album_page(
            session, album_id, begin_msgid=begin_msgid,
            begin_itemidx=begin_itemidx, is_reverse=0
        )

        if not articles:
            logger.info(f"  [{album_name}] 第{page}页无文章，遍历结束")
            break

        stop = False
        for a in articles:
            create_time = int(a.get("create_time", 0))
            if create_time == 0:
                continue
            dt = datetime.fromtimestamp(create_time)
            article_date = dt.replace(hour=0, minute=0, second=0,
                                      microsecond=0)

            # 日期过滤
            if since_date and article_date < since_date:
                stop = True
                break
            if until_date and article_date > until_date:
                continue

            url = html_mod.unescape(a.get("url", ""))
            if url.startswith("http://"):
                url = "https://" + url[7:]
            url = url.split("#")[0]

            title = a.get("title", "")

            # ── v1.15 防御性检查：排除 daily AIGC 早报文章 ──
            # 即使 ALBUMS 列表正确排除了 daily 专辑 (album_id=3793362825901522949)，
            # 仍按标题模式二次过滤，防止任何 daily 内容混入主博客。
            # daily 文章标题模式："每日 AIGC 早报" / "每日AIGC早报" / "每日 AIGC早报" 等
            if _is_daily_report_title(title):
                logger.warning(
                    f"  [{album_name}] 跳过 daily 文章 (标题匹配): {title!r}")
                continue

            all_articles.append({
                "url": url,
                "title": title,
                "date": article_date.strftime("%Y-%m-%d"),
                "categories": album_config["categories"],
                "tags": album_config["tags"],
            })

        logger.debug(
            f"  [{album_name}] 第{page}页: 获取{len(articles)}条，"
            f"累计{len(all_articles)}条，continue_flag={cf}"
        )

        if stop:
            logger.info(f"  [{album_name}] 已到达起始日期边界")
            break
        if cf != "1":
            logger.info(f"  [{album_name}] 已遍历全部合集 ({page}页)")
            break

        begin_msgid = articles[-1].get("msgid", "")
        begin_itemidx = articles[-1].get("itemidx", "")
        time.sleep(0.3)

    logger.info(f"  [{album_name}] 遍历完成: 共 {len(all_articles)} 篇文章")
    return all_articles


def collect_all_album_urls(logger, since_date=None, until_date=None,
                           max_pages=None):
    """遍历全部7个合集，合并去重文章URL列表。

    参数:
      since_date: 起始日期 (datetime)，None=不限
      until_date: 截止日期 (datetime)，None=不限
      max_pages:  每个合集最多遍历几页，None=不限
    返回:
      [{'url': ..., 'title': ..., 'date': 'YYYY-MM-DD',
        'categories': ..., 'tags': ...}, ...]
    """
    all_articles = []
    seen_urls = set()

    logger.info(f"═══ 开始遍历全部 {len(ALBUMS)} 个合集 ═══")

    for album_config in ALBUMS:
        articles = collect_album_urls(
            logger, album_config, since_date=since_date,
            until_date=until_date, max_pages=max_pages
        )
        for a in articles:
            if a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                all_articles.append(a)
        # 合集间短暂延迟
        time.sleep(0.5)

    # 按日期降序排列（最新在前）
    all_articles.sort(key=lambda a: a["date"], reverse=True)

    logger.info(f"═══ 全部合集遍历完成: 共 {len(all_articles)} 篇不重复文章 ═══")
    return all_articles


# ─── GitHub API ──────────────────────────────────────────────

def github_api_request(method, url, logger, **kwargs):
    """发送GitHub API请求"""
    if not GITHUB_TOKEN:
        logger.error("未设置 GITHUB_TOKEN 环境变量")
        logger.error("获取方法：")
        logger.error("  1. 访问 https://github.com/settings/tokens")
        logger.error("  2. Generate new token (classic)")
        logger.error("  3. 勾选 repo 权限")
        logger.error("  4. export GITHUB_TOKEN=ghp_xxxxx")
        return None

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.request(method, f"https://api.github.com{url}",
                            headers=headers, timeout=30, **kwargs)
    if resp.status_code in (200, 201):
        return resp.json()
    elif resp.status_code == 409:
        # Conflict - need to get latest SHA
        logger.debug(f"GitHub API 409 conflict for {url}")
        return None
    else:
        logger.error(f"GitHub API 错误: {resp.status_code} {resp.text[:200]}")
        return None


def github_get_file_info(owner, repo, path, branch, logger):
    """读取指定分支中的文件元数据，供图床路由模块解析 _config.yml。"""
    suffix = f"?ref={branch}" if branch else ""
    return github_api_request(
        "GET", f"/repos/{owner}/{repo}/contents/{path}{suffix}", logger)


def get_image_upload_route(post_date, logger):
    """从主博客 _config.yml 读取并验证该文章月份的图片上传目标。"""
    route = load_upload_route(
        lambda owner, repo, path, branch=None: github_get_file_info(
            owner, repo, path, branch, logger),
        REPO_POSTS,
        "main",
        post_date,
    )
    logger.info(
        "图床路由: %s → %s@%s",
        route["date_key"], route["repository"], route["branch"],
    )
    return route


def github_file_exists(repo, path, logger, branch=None):
    """检查指定分支中是否存在文件，返回 (exists, sha) 或 (False, None)。"""
    suffix = f"?ref={branch}" if branch else ""
    result = github_api_request(
        "GET", f"/repos/{repo}/contents/{path}{suffix}", logger)
    if result and isinstance(result, dict) and "sha" in result:
        return True, result["sha"]
    return False, None


def github_download_file(repo, path, local_path, logger, branch=None):
    """从指定分支下载 GitHub 文件到本地。"""
    suffix = f"?ref={branch}" if branch else ""
    result = github_api_request(
        "GET", f"/repos/{repo}/contents/{path}{suffix}", logger)
    if result and isinstance(result, dict) and "content" in result:
        content = base64.b64decode(result["content"])
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(content)
        logger.info(f"已下载: {path} → {local_path}")
        return True
    return False


def github_upload_file(repo, path, local_path, message, logger, overwrite=False,
                       branch=None):
    """上传文件到GitHub仓库。
    
    如果文件已存在：
    - overwrite=False: 跳过
    - overwrite=True: 先备份旧版本到本地（_bak后缀），再覆盖
    """
    # 检查指定分支中是否已存在
    exists, sha = github_file_exists(repo, path, logger, branch=branch)

    if exists and not overwrite:
        logger.info(f"文件已存在（跳过）: {path}")
        return True

    if exists and overwrite:
        # 备份旧版本
        bak_local = local_path + "_bak"
        github_download_file(repo, path, bak_local, logger, branch=branch)
        logger.info(f"已备份旧版本: {bak_local}")

    # 读取文件内容
    with open(local_path, "rb") as f:
        file_content = base64.b64encode(f.read()).decode("utf-8")

    data = {
        "message": message,
        "content": file_content,
    }
    if sha:
        data["sha"] = sha
    if branch:
        data["branch"] = branch

    # 使用 PUT 上传
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.put(
        f"https://api.github.com/repos/{repo}/contents/{path}",
        headers=headers,
        json=data,
        timeout=30,
    )

    if resp.status_code in (200, 201):
        logger.info(f"✓ 上传成功: {path}")
        return True
    else:
        logger.error(f"✗ 上传失败: {path} — {resp.status_code} {resp.text[:200]}")
        return False


def github_list_dir(repo, dir_path, logger, branch=None):
    """列出GitHub仓库中指定目录下的文件。

    返回: [{name, path, sha, type}, ...] 列表，失败返回空列表。
    """
    suffix = f"?ref={branch}" if branch else ""
    result = github_api_request(
        "GET", f"/repos/{repo}/contents/{dir_path}{suffix}", logger)
    if result and isinstance(result, list):
        return [{"name": f.get("name", ""), "path": f.get("path", ""),
                 "sha": f.get("sha", ""), "type": f.get("type", "")}
                for f in result if isinstance(f, dict)]
    return []


def github_batch_commit(repo, file_ops, commit_message, logger, branch=None):
    """使用 Git Data API 一次性提交多个文件操作（增/删/改）。

    避免像逐文件 PUT 那样产生大量 commit，看起来像 DDoS。

    file_ops: 列表，每个元素为 dict:
      - {"mode": "add", "path": "a/b.jpg", "local_path": "/tmp/b.jpg"}  — 新增/覆盖
      - {"mode": "modify", "path": "a/b.jpg", "local_path": "/tmp/b.jpg", "sha": "xxx"}  — 修改（已知sha）
      - {"mode": "delete", "path": "a/b.jpg", "sha": "xxx"}  — 删除

    返回: True/False
    """
    if not file_ops:
        logger.info("无可提交的文件操作")
        return True

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    # 1. 获取目标分支的最新 commit SHA；未指定时保持旧版 master → main 回退。
    candidate_branches = [branch] if branch else ["master", "main"]
    resp = None
    for candidate in candidate_branches:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/git/ref/heads/{candidate}",
            headers=headers, timeout=30,
        )
        if resp.status_code == 200:
            break
    if resp.status_code != 200:
        logger.error(f"无法获取分支引用: {resp.status_code} {resp.text[:200]}")
        return False

    ref_data = resp.json()
    last_commit_sha = ref_data["object"]["sha"]
    branch_name = ref_data.get("ref", "refs/heads/master").split("/")[-1]

    # 2. 获取该 commit 的 tree SHA
    resp = requests.get(
        f"https://api.github.com/repos/{repo}/git/commits/{last_commit_sha}",
        headers=headers, timeout=30,
    )
    if resp.status_code != 200:
        logger.error(f"无法获取 commit: {resp.status_code}")
        return False
    commit_data = resp.json()
    base_tree_sha = commit_data["tree"]["sha"]

    # 3. 构建 tree entries（为每个文件创建 blob）
    tree_entries = []
    for op in file_ops:
        mode = op["mode"]
        path = op["path"]

        if mode in ("add", "modify"):
            # 读取本地文件，创建 blob
            local_path = op["local_path"]
            if not os.path.isfile(local_path):
                logger.warning(f"本地文件不存在，跳过: {local_path}")
                continue

            with open(local_path, "rb") as f:
                file_content = base64.b64encode(f.read()).decode("utf-8")

            # 创建 blob
            blob_resp = requests.post(
                f"https://api.github.com/repos/{repo}/git/blobs",
                headers=headers,
                json={"content": file_content, "encoding": "base64"},
                timeout=30,
            )
            if blob_resp.status_code not in (200, 201):
                logger.error(f"创建 blob 失败: {path} — {blob_resp.status_code}")
                continue
            blob_sha = blob_resp.json()["sha"]

            tree_entries.append({
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha,
            })

        elif mode == "delete":
            tree_entries.append({
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": None,  # None 表示删除
            })

    if not tree_entries:
        logger.warning("没有有效的文件操作可提交")
        return False

    # 4. 创建新 tree
    tree_resp = requests.post(
        f"https://api.github.com/repos/{repo}/git/trees",
        headers=headers,
        json={"base_tree": base_tree_sha, "tree": tree_entries},
        timeout=30,
    )
    if tree_resp.status_code not in (200, 201):
        logger.error(f"创建 tree 失败: {tree_resp.status_code} {tree_resp.text[:300]}")
        return False
    new_tree_sha = tree_resp.json()["sha"]

    # 5. 创建 commit
    commit_resp = requests.post(
        f"https://api.github.com/repos/{repo}/git/commits",
        headers=headers,
        json={
            "message": commit_message,
            "tree": new_tree_sha,
            "parents": [last_commit_sha],
        },
        timeout=30,
    )
    if commit_resp.status_code not in (200, 201):
        logger.error(f"创建 commit 失败: {commit_resp.status_code} {commit_resp.text[:300]}")
        return False
    new_commit_sha = commit_resp.json()["sha"]

    # 6. 更新分支引用
    update_resp = requests.patch(
        f"https://api.github.com/repos/{repo}/git/refs/heads/{branch_name}",
        headers=headers,
        json={"sha": new_commit_sha, "force": False},
        timeout=30,
    )
    if update_resp.status_code not in (200, 200):
        # 有些API返回200
        if update_resp.status_code not in (200, 201):
            logger.error(f"更新分支引用失败: {update_resp.status_code} {update_resp.text[:200]}")
            return False

    logger.info(f"✓ 批量提交成功: {commit_message} ({len(tree_entries)} 个文件操作)")
    return True


def github_verify_file(repo, path, logger, branch=None):
    """验证指定分支中的文件是否已成功上传到 GitHub。"""
    exists, sha = github_file_exists(repo, path, logger, branch=branch)
    if exists:
        logger.info(f"✓ 验证通过: {path}")
        return True
    else:
        logger.warning(f"✗ 验证失败: {path}")
        return False


# ─── 核心处理流程 ────────────────────────────────────────────

def process_article(raw_html, output_dir, logger, source_url=None, source_path=None,
                    overwrite_all=False, categories="文章", tags="科技", non_interactive=False,
                    sync_memory=None):
    """
    核心处理流程：原始HTML → Markdown + 图片下载 + GitHub上传。

    自动识别长文/短篇，按不同规则转换。

    overwrite_all: 如果为True，所有已存在的文件都自动覆盖，不再询问。
                   函数返回时也会告知调用者是否选择了"全部覆盖"。
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    # 1. 提取元数据（在clean_soup之前，因为clean_soup会删除meta标签）
    meta = {}
    for tag in soup.find_all("meta", property=True):
        if "og:" in tag["property"]:
            meta[tag["property"]] = tag.get("content", "")

    title_raw = meta.get("og:title", "")
    title = html_mod.unescape(title_raw)
    if not title:
        html_title = soup.title.string.strip() if soup.title and soup.title.string else None
        title = html_title or "未命名文章"

    # ── v1.15 防御性检查：二次排除 daily AIGC 早报文章 ──
    # 即使上层 collect_album_urls 已过滤，这里再按标题模式挡一道，
    # 防止从文件/CLI 直接传入 daily URL 时漏网。
    if _is_daily_report_title(title):
        logger.warning(
            f"跳过 daily AIGC 早报文章 (防御性检查): {title!r} — "
            f"该文章应由 03_convert-daily.py 处理，不属于主博客")
        return None

    # 2. 提取日期（也在clean_soup之前，优先使用正文标注的日期）
    post_date = extract_date(soup, raw_html, fallback_name=source_path or "", logger=logger)
    year, month, day = post_date.split("-")

    # 3. 清理HTML（元数据已提取完毕，现在可以安全清理）
    soup = clean_soup(soup)

    # 4. 生成slug
    slug = slugify(title)

    # 5. 自动识别文章类型
    article_type = detect_article_type(soup, raw_html)
    logger.info(f"文章类型: {'长文(blog)' if article_type == 'long' else '短篇(short)'}")
    logger.info(f"标题: {title}")
    logger.info(f"日期: {post_date}")
    logger.info(f"Slug: {slug}")

    # 6. 转换内容
    if article_type == "long":
        result = convert_long_article(soup, raw_html, post_date, slug, logger)
    else:
        result = convert_short_article(soup, raw_html, post_date, slug, logger)

    if result is None or result[0] is None:
        logger.error("内容转换失败")
        return None

    content, images_to_download, image_mapping, cover_github_url = result

    # 7. 有图片需要上传时，先从主站 _config.yml 按文章月份解析图床。
    image_route = None
    image_repo = None
    image_branch = None
    if image_mapping and GITHUB_TOKEN:
        try:
            image_route = get_image_upload_route(post_date, logger)
        except ImageRouteError as e:
            logger.error(f"无法确定图片上传图床，终止发布以避免产生失效引用: {e}")
            return None
        image_repo = image_route["repository"]
        image_branch = image_route["branch"]

    # 8. 下载图片到本地
    local_img_dir = os.path.join(output_dir, "images", year, month, day, slug)
    os.makedirs(local_img_dir, exist_ok=True)

    # 收集所有需要上传的图片（题图 + 正文图片）
    all_image_urls = set()
    for wx_url, gh_url in image_mapping.items():
        all_image_urls.add(wx_url)

    downloaded_files = {}  # 本地文件路径 → GitHub仓库路径
    converted_url_replacements = {}  # 转换前公开 URL → 转换后公开 URL

    for wx_url in all_image_urls:
        gh_url = image_mapping[wx_url]
        img_ext = get_image_format_from_url(wx_url)
        # 从GitHub URL提取文件名
        gh_filename = gh_url.split("/")[-1]
        local_path = os.path.join(local_img_dir, gh_filename)

        dl_url = sanitize_image_url(wx_url)
        logger.info(f"下载图片 {gh_filename}...")
        if download_image(dl_url, local_path):
            logger.info(f"  ✓ 已保存: {local_path}")
            # v1.12: 上传前压缩并转换格式（不透明PNG→JPG, WebP→JPG/PNG, 静态GIF→PNG）
            new_local_path, saved = compress_and_convert_image(local_path, logger)
            if saved > 0:
                logger.info(f"  ✓ 压缩节省: {saved/1024:.1f}KB")
            # 格式转换后扩展名可能变化，更新 gh_filename 和 image_mapping
            new_gh_filename = os.path.basename(new_local_path)
            if new_gh_filename != gh_filename:
                logger.info(f"  ✓ 格式转换: {gh_filename} → {new_gh_filename}")
                gh_filename = new_gh_filename
                # 更新 image_mapping 中的 URL
                new_gh_url = gh_url.rsplit('.', 1)[0] + '.' + new_gh_filename.rsplit('.', 1)[-1]
                converted_url_replacements[gh_url] = new_gh_url
                image_mapping[wx_url] = new_gh_url
            # GitHub 仓库路径：由配置的 path_prefix 加相对图片路径组成。
            relative_img_path = f"{year}/{month}/{day}/{slug}/{gh_filename}"
            gh_repo_path = (
                join_repo_path(image_route, relative_img_path)
                if image_route else relative_img_path
            )
            downloaded_files[new_local_path] = gh_repo_path
        else:
            logger.warning(f"  ✗ 下载失败: {gh_filename}")

    if converted_url_replacements:
        content, cover_github_url = rewrite_converted_image_urls(
            content, cover_github_url, converted_url_replacements)
        logger.info(f"  ✓ 已回写 {len(converted_url_replacements)} 个转换后图片 URL 到文章内容")

    # 8. 生成Markdown文件
    # v1.28: featured 标签自动化（见 _build_tags_with_featured）
    tags_str = _build_tags_with_featured(tags)
    categories_str = categories

    front_matter = (
        f"---\n"
        f"layout: post\n"
        f'title: "{html_mod.escape(title)}"\n'
        f"date: {post_date}\n"
        f"categories: {categories_str}\n"
        f"tags: [{tags_str}]\n"
        f"image: {cover_github_url}\n"
        f"---\n\n"
    )

    md_name = f"{post_date}-{slug}.md"
    md_content = front_matter + content
    md_path = os.path.join(output_dir, md_name)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    logger.info(f"生成Markdown: {md_name}")

    # 9. 上传到GitHub（如果配置了Token）
    overwrite_this = overwrite_all  # 本次是否覆盖

    if GITHUB_TOKEN:
        # 上传文章到 lishuhang.github.io 仓库
        posts_repo_path = f"{POSTS_PATH}/{md_name}"

        # 检查文章是否已存在
        exists, sha = github_file_exists(REPO_POSTS, posts_repo_path, logger)
        if exists:
            logger.info(f"文章已存在于仓库: {posts_repo_path}")
            if non_interactive:
                overwrite_this = False
                logger.info("后台模式：文章已存在，跳过覆盖")
            elif not overwrite_all:
                answer = input(
                    f"文件 {md_name} 已存在，是否覆盖？(y/N/a[全部覆盖]): "
                ).strip().lower()
                if answer == "a":
                    overwrite_this = True
                    overwrite_all = True  # 后续所有文章都覆盖
                    logger.info("已选择「全部覆盖」模式，后续不再询问")
                elif answer == "y":
                    overwrite_this = True
                else:
                    overwrite_this = False
                    logger.info("跳过上传")
            else:
                overwrite_this = True

        upload_ok = None  # None=仓库已有且未覆盖
        if exists and overwrite_this:
            # 备份旧版本
            bak_path = md_path + "_bak"
            github_download_file(REPO_POSTS, posts_repo_path, bak_path, logger)
            upload_ok = github_upload_file(
                REPO_POSTS, posts_repo_path, md_path,
                f"Update: {md_name}", logger, overwrite=True
            )
        elif not exists:
            upload_ok = github_upload_file(
                REPO_POSTS, posts_repo_path, md_path,
                f"Add: {md_name}", logger
            )

        # v1.28: 同步记忆 —— 仓库已有或本次上传成功均记为已同步；
        # 上传失败不记录，保留下次增量运行重试的机会。
        if source_url and sync_memory is not None:
            if exists:
                mark_article_synced(sync_memory, source_url, logger)
                logger.info("已记入同步记忆（仓库已有此文章，不再重复同步）")
            elif upload_ok:
                mark_article_synced(sync_memory, source_url, logger)
                logger.info("已记入同步记忆（本次发布成功）")

        # ── 图片库：批量提交（每篇文章一次 commit） ──
        # 图片路径前缀由当前日期匹配的 _config.yml 规则决定。
        relative_img_dir = f"{year}/{month}/{day}/{slug}"
        img_dir_prefix = (
            join_repo_path(image_route, relative_img_dir)
            if image_route else relative_img_dir
        )

        # 收集需要执行的文件操作
        img_file_ops = []  # [{"mode": "add"/"modify"/"delete", ...}, ...]

        if overwrite_this and downloaded_files:
            # 覆盖模式：先查看图片库中该文章目录下已有的文件
            existing_imgs = github_list_dir(
                image_repo, img_dir_prefix, logger, branch=image_branch)
            existing_img_names = {f["name"] for f in existing_imgs if f["type"] == "file"}
            existing_img_map = {f["name"]: f for f in existing_imgs if f["type"] == "file"}

            # 备份旧图片到本地
            for old_img in existing_imgs:
                if old_img["type"] != "file":
                    continue
                bak_local = os.path.join(local_img_dir, old_img["name"] + "_bak")
                github_download_file(
                    image_repo, old_img["path"], bak_local, logger,
                    branch=image_branch)
                logger.info(f"已备份旧图片: {old_img['name']} → {bak_local}")

                # 删除旧图片（在同一 commit 中）
                img_file_ops.append({
                    "mode": "delete",
                    "path": old_img["path"],
                    "sha": old_img["sha"],
                })

            # 添加新图片
            for local_path, gh_repo_path in downloaded_files.items():
                img_file_ops.append({
                    "mode": "add",
                    "path": gh_repo_path,
                    "local_path": local_path,
                })

        elif downloaded_files:
            # 非覆盖模式：只上传不存在的图片
            existing_imgs = github_list_dir(
                image_repo, img_dir_prefix, logger, branch=image_branch)
            existing_img_names = {f["name"] for f in existing_imgs if f["type"] == "file"}

            for local_path, gh_repo_path in downloaded_files.items():
                img_filename = gh_repo_path.split("/")[-1]
                if img_filename in existing_img_names:
                    logger.info(f"图片已存在（跳过）: {gh_repo_path}")
                    continue
                img_file_ops.append({
                    "mode": "add",
                    "path": gh_repo_path,
                    "local_path": local_path,
                })

        # 批量提交图片
        if img_file_ops:
            img_commit_msg = f"{'Replace' if overwrite_this else 'Add'} images: {img_dir_prefix}"
            success = github_batch_commit(
                image_repo, img_file_ops, img_commit_msg, logger,
                branch=image_branch)
            if not success:
                # 回退到逐个上传
                logger.warning("批量提交失败，回退到逐个上传...")
                for op in img_file_ops:
                    if op["mode"] in ("add", "modify"):
                        github_upload_file(
                            image_repo, op["path"], op["local_path"],
                            f"Add image: {op['path']}", logger,
                            overwrite=op["mode"] == "modify",
                            branch=image_branch,
                        )

        # 验证上传
        logger.info("验证上传结果...")
        for local_path, gh_repo_path in downloaded_files.items():
            github_verify_file(
                image_repo, gh_repo_path, logger, branch=image_branch)
        github_verify_file(REPO_POSTS, posts_repo_path, logger)
    else:
        logger.info("未配置 GITHUB_TOKEN，跳过GitHub上传")
        logger.info("请手动上传：")
        logger.info("  图片 → 请按主站 _config.yml 的 image_prefixes 确认上传图床")
        logger.info(f"  文章 → https://github.com/{REPO_POSTS}/tree/main/{POSTS_PATH}")

    return md_path, overwrite_all


# ─── 入口 ──────────────────────────────────────────────────────

def parse_album_arg(arg):
    """解析 album 参数，返回 (mode, since_date, until_date)。

    mode: 'all' | 'diff' | 'range'
    """
    parts = arg.split(":")

    if len(parts) < 2 or parts[1] == "all":
        return "all", None, None

    if parts[1] == "diff":
        return "diff", None, None

    # 日期范围模式
    since_date = None
    until_date = None
    if len(parts) >= 2 and parts[1]:
        try:
            since_date = datetime.strptime(parts[1], "%Y%m%d")
        except ValueError:
            print(f"错误：日期格式无效 '{parts[1]}'，应为 YYYYMMDD",
                  file=sys.stderr)
            sys.exit(1)
    if len(parts) >= 3 and parts[2]:
        try:
            until_date = datetime.strptime(parts[2], "%Y%m%d")
        except ValueError:
            print(f"错误：日期格式无效 '{parts[2]}'，应为 YYYYMMDD",
                  file=sys.stderr)
            sys.exit(1)

    return "range", since_date, until_date


def main():
    # 解析命令行参数
    album_mode = None       # 'all' | 'diff' | 'range' | None
    album_since = None      # datetime
    album_until = None      # datetime

    cli_urls = []
    dir_args = []
    non_interactive = "--non-interactive" in sys.argv[1:]

    for arg in sys.argv[1:]:
        if arg == "--non-interactive":
            continue
        if arg.startswith("album:"):
            album_mode, album_since, album_until = parse_album_arg(arg)
        elif arg.startswith("http"):
            cli_urls.append(arg)
        else:
            dir_args.append(arg)

    # 工作目录
    if dir_args:
        d = dir_args[0]
        if not os.path.isdir(d):
            print(f"错误：{d} 不是有效目录", file=sys.stderr)
            sys.exit(1)
        output_dir = os.path.abspath(d)
    else:
        output_dir = os.getcwd()

    logger, log_path = setup_logging(output_dir)
    logger.info(f"工作目录: {output_dir}")
    logger.info(f"日志文件: {log_path}")

    if album_mode:
        desc = "全部合集"
        if album_since:
            desc = f"自 {album_since.strftime('%Y-%m-%d')}"
        if album_until:
            desc += f" 至 {album_until.strftime('%Y-%m-%d')}"
        logger.info(f"合集模式: {desc}")

    # 构建任务队列：URL列表 + 合集URL
    urls_with_meta = []  # [(url, categories, tags), ...]
    seen_urls = set(cli_urls)

    # 来源1：合集API（如果指定了album:参数）
    if album_mode:
        if album_mode == "diff":
            # 差异对比模式
            logger.info("═══ 差异对比模式 ═══")
            articles = collect_all_album_urls(logger, max_pages=None)
            album_dates = {a["date"] for a in articles}
            album_urls = {a["url"] for a in articles}
            logger.info(f"合集共有 {len(album_dates)} 个日期，{len(album_urls)} 篇文章")

            # 检查GitHub仓库已有文章
            repo_dates = set()
            if GITHUB_TOKEN:
                entries = github_list_dir(REPO_POSTS, POSTS_PATH, logger)
                for e in entries:
                    m = re.match(r"(\d{4}-\d{2}-\d{2})-", e.get("name", ""))
                    if m:
                        repo_dates.add(m.group(1))
            logger.info(f"仓库已有 {len(repo_dates)} 篇文章")

            missing = sorted(album_dates - repo_dates)
            print(f"\n{'='*60}")
            print(f"  合集文章数: {len(album_dates)}")
            print(f"  仓库文章数: {len(repo_dates)}")
            print(f"  缺失（合集有/仓库无）: {len(missing)} 篇")
            if missing:
                print(f"\n  缺失日期列表:")
                current_ym = ""
                for d in missing:
                    ym = d[:7]
                    if ym != current_ym:
                        current_ym = ym
                        print(f"\n    {ym}:")
                    print(f"      {d}")
            print(f"{'='*60}")

            if missing:
                try:
                    answer = input(
                        f"\n  是否抓取这 {len(missing)} 篇缺失文章？(y/n): "
                    ).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return
                if answer in ("y", "yes"):
                    # 只处理缺失日期的文章
                    for a in articles:
                        if a["date"] in missing and a["url"] not in seen_urls:
                            seen_urls.add(a["url"])
                            urls_with_meta.append(
                                (a["url"], a["categories"], a["tags"]))
            return

        elif album_mode == "all":
            articles = collect_all_album_urls(logger, max_pages=None)
        else:  # range
            articles = collect_all_album_urls(
                logger, since_date=album_since, until_date=album_until)

        for a in articles:
            if a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                urls_with_meta.append(
                    (a["url"], a["categories"], a["tags"]))

        if urls_with_meta:
            logger.info(f"从合集获取到 {len(urls_with_meta)} 个文章URL")
        else:
            logger.info("合集中没有符合条件的文章")

    # 来源2：命令行直接输入的URL
    for url in cli_urls:
        urls_with_meta.append((url, "文章", "科技"))  # 默认分类

    # 来源3：从同目录文件读取URL
    file_urls = read_urls_from_files(output_dir, logger)
    for url in file_urls:
        if url not in seen_urls:
            seen_urls.add(url)
            urls_with_meta.append((url, "文章", "科技"))  # 默认分类

    # 来源4：自动模式（无参数时，检查合集最新文章）
    if not cli_urls and not file_urls and album_mode is None:
        logger.info("═══ 自动模式：检查合集最新文章 ═══")
        articles = collect_all_album_urls(logger, max_pages=AUTO_MAX_PAGES)
        if not articles:
            logger.info("没有发现新文章")
            return
        logger.info(f"发现 {len(articles)} 篇文章")
        for a in articles:
            if a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                urls_with_meta.append(
                    (a["url"], a["categories"], a["tags"]))

    if not urls_with_meta:
        logger.error("没有可处理的URL")
        return

    logger.info(f"共 {len(urls_with_meta)} 个URL待处理")

    # ── 处理每篇文章 ──
    # v1.28: 增量同步 —— 载入已同步记忆，同步过的 URL 不再抓取处理；
    # 合集窗口由调度器 30 天封顶，历史文章永不重跑（新电脑冷启动亦然）。
    sync_memory = load_sync_memory(logger)
    if sync_memory:
        logger.info(f"已同步记忆: {len(sync_memory)} 篇（blog_sync_memory.json）")

    overwrite_all = False
    ok, fail, skip = 0, 0, 0

    for i, (url, categories, tags) in enumerate(urls_with_meta, 1):
        if url in sync_memory:
            logger.info(
                f"[{i}/{len(urls_with_meta)}] 已同步过（记忆命中，跳过）: {url[:80]}")
            skip += 1
            continue

        logger.info(f"[{i}/{len(urls_with_meta)}] {url[:80]}...")

        raw_html = fetch_wechat_html(url, logger)
        if not raw_html:
            logger.error("抓取HTML失败，跳过")
            fail += 1
            continue

        result = process_article(
            raw_html, output_dir, logger,
            source_url=url,
            overwrite_all=overwrite_all,
            categories=categories,
            tags=tags,
            non_interactive=non_interactive,
            sync_memory=sync_memory,
        )

        if result is not None:
            md_path, overwrite_all = result
            ok += 1
        else:
            skip += 1

        # 礼貌延迟
        if i < len(urls_with_meta):
            time.sleep(0.5)

    logger.info(f"═══ 完成: {ok} 成功, {skip} 跳过, {fail} 失败 ═══")
    logger.info(f"日志文件: {log_path}")


if __name__ == "__main__":
    main()
