#!/usr/bin/env python3
"""
微信公众号AIGC早报 - 自动抓取与GitHub发布脚本

功能：
1. 从微信专辑遍历抓取文章
2. 自动生成Markdown和下载封面图
3. 直接推送到 GitHub 仓库（图片目标由 daily 的 _config.yml 按日期决定，文章→daily repo）
4. 智能检测已有最新日期，只抓取缺失的
5. 覆盖前自动备份已有文件，需用户确认
6. 上传后验证文件已在仓库中
7. 完整对比专辑与仓库差异（album:diff）

用法：
  python convert_daily_2.py                    # 自动检测并抓取缺失文章
  python convert_daily_2.py album:20260103     # 抓取指定日期起至最新
  python convert_daily_2.py album:20260103:20260201  # 抓取指定日期范围
  python convert_daily_2.py album:20260103:20260103  # 单抓某一天
  python convert_daily_2.py album:all          # 抓取专辑全部文章
  python convert_daily_2.py album:diff         # 对比专辑与仓库差异

GitHub Token 设置：
  方式一（推荐）: 在脚本同目录创建 .env 文件，写入：
      GITHUB_TOKEN=ghp_xxxxxxxxxxxx
  方式二: 设置环境变量：
      export GITHUB_TOKEN=ghp_xxxxxxxxxxxx

  Token 申请步骤：
  1. 访问 https://github.com/settings/tokens
  2. 点击 "Generate new token (classic)"
  3. 填写 Note（如 "daily-publisher"）
  4. 勾选 repo 权限（完整仓库读写）
  5. 点击 Generate token，复制生成的 ghp_ 开头字符串
  6. 保存到 .env 文件或环境变量中

  注意：Token 只在创建时显示一次，请妥善保存！
"""

import os
import re
import sys
import json
import time
import base64
import logging
import requests
from datetime import datetime
from html import unescape as html_unescape

from bs4 import BeautifulSoup

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

# ═══════════════════════════════════════════════════════════════
# 常量与配置
# ═══════════════════════════════════════════════════════════════

GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
GITHUB_API_BASE = "https://api.github.com"

DAILY_REPO = {"owner": "lishuhang", "repo": "daily", "branch": "main"}

GITHUB_IMAGE_BASE_URL = (
    f""  # v1.11: empty prefix, paths are /YYYY/MM/...
)

DEFAULT_ALBUM_BIZ = "MjM5Mjg1ODIxMQ=="
DEFAULT_ALBUM_ID = "3793362825901522949"
ALBUM_API_URL = "https://mp.weixin.qq.com/mp/appmsgalbum"
ALBUM_PAGE_SIZE = 20

# 自动模式：最多检查专辑前几页（每页20篇）
AUTO_MAX_PAGES = 3


# ═══════════════════════════════════════════════════════════════
# 日志
# ═══════════════════════════════════════════════════════════════

def setup_logging(output_dir):
    """创建带时间戳的日志文件，同时输出到控制台"""
    log_name = f"daily_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_name)
    logger = logging.getLogger("convert_daily_2")
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


# ═══════════════════════════════════════════════════════════════
# GitHub Token
# ═══════════════════════════════════════════════════════════════

def get_github_token():
    """从环境变量或.env文件获取GitHub Token，未找到则返回空字符串"""
    # 1. 环境变量
    token = os.environ.get(GITHUB_TOKEN_ENV, "")
    if token:
        return token

    # 2. .env 文件（当前目录 → 脚本所在目录）
    for search_dir in (os.getcwd(), os.path.dirname(os.path.abspath(__file__))):
        env_path = os.path.join(search_dir, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{GITHUB_TOKEN_ENV}="):
                        token = line[len(GITHUB_TOKEN_ENV) + 1:].strip().strip('"').strip("'")
                        if token:
                            return token
    return ""


def print_token_help():
    """打印Token获取帮助信息"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║            GitHub Token 未设置，无法上传文件                  ║
╚══════════════════════════════════════════════════════════════╝

  获取 Token 步骤：
  1. 访问 https://github.com/settings/tokens
  2. 点击 "Generate new token (classic)"
  3. Note 填写: daily-publisher
  4. 勾选 repo 权限（完整仓库读写控制）
  5. 点击 Generate token
  6. 复制 ghp_ 开头的字符串

  设置 Token 方式（二选一）：

  方式一（推荐）- 创建 .env 文件：
    在脚本同目录创建 .env 文件，写入：
    GITHUB_TOKEN=ghp_你的token

  方式二 - 环境变量：
    Windows:  set GITHUB_TOKEN=ghp_你的token
    Linux/Mac: export GITHUB_TOKEN=ghp_你的token
""")


# ═══════════════════════════════════════════════════════════════
# GitHub API
# ═══════════════════════════════════════════════════════════════

class GitHubAPI:
    """GitHub REST API v3 封装（Contents API）"""

    def __init__(self, token, logger=None):
        self.token = token
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "convert-daily-2",
        })

    def _log(self, level, msg):
        if self.logger:
            getattr(self.logger, level)(msg)

    def _request(self, method, url, **kwargs):
        """发送请求，处理常见错误"""
        full_url = f"{GITHUB_API_BASE}{url}"
        for attempt in range(3):
            try:
                resp = self.session.request(method, full_url, timeout=30, **kwargs)
                if resp.status_code == 403:
                    remaining = resp.headers.get("X-RateLimit-Remaining", "?")
                    if remaining == "0":
                        reset_ts = int(resp.headers.get("X-RateLimit-Reset", "0"))
                        wait = max(reset_ts - int(time.time()), 0) + 1
                        self._log("warning",
                                  f"API速率限制，等待 {wait} 秒...")
                        time.sleep(min(wait, 60))
                        continue
                return resp
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    self._log("warning", f"请求失败，重试: {e}")
                    time.sleep(2)
                else:
                    raise
        return resp

    # ─── 读取 ─────────────────────────────────────────────

    def get_file_info(self, owner, repo, path, branch=None):
        """获取文件元数据（含 content, sha），不存在返回 None"""
        params = {"ref": branch} if branch else {}
        resp = self._request("GET",
                             f"/repos/{owner}/{repo}/contents/{path}",
                             params=params)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                return None  # 路径是目录不是文件
            return data
        if resp.status_code == 404:
            return None
        raise Exception(
            f"GitHub API 错误: GET {path} → {resp.status_code} "
            f"{resp.text[:200]}"
        )

    def list_dir(self, owner, repo, path, branch=None):
        """列出目录内容，返回条目列表"""
        params = {"ref": branch} if branch else {}
        resp = self._request("GET",
                             f"/repos/{owner}/{repo}/contents/{path}",
                             params=params)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return []
        raise Exception(
            f"GitHub API 错误: LIST {path} → {resp.status_code} "
            f"{resp.text[:200]}"
        )

    def download_file_bytes(self, owner, repo, path, branch=None):
        """下载文件内容为bytes，不存在返回None"""
        info = self.get_file_info(owner, repo, path, branch=branch)
        if info is None:
            return None
        # 小文件：直接从 content 字段解码
        if "content" in info:
            return base64.b64decode(info["content"])
        # 大文件：用 download_url
        dl_url = info.get("download_url")
        if dl_url:
            resp = requests.get(dl_url, timeout=30)
            if resp.status_code == 200:
                return resp.content
        return None

    # ─── 写入 ─────────────────────────────────────────────

    def upload_file(self, owner, repo, path, content_bytes, message,
                    branch=None, sha=None):
        """创建或更新文件。sha非空时为更新已有文件。"""
        content_b64 = base64.b64encode(content_bytes).decode("ascii")
        data = {"message": message, "content": content_b64}
        if branch:
            data["branch"] = branch
        if sha:
            data["sha"] = sha
        resp = self._request("PUT",
                             f"/repos/{owner}/{repo}/contents/{path}",
                             json=data)
        if resp.status_code in (200, 201):
            self._log("debug", f"上传成功: {path}")
            return resp.json()
        raise Exception(
            f"GitHub 上传失败: PUT {path} → {resp.status_code} "
            f"{resp.text[:300]}"
        )

    # ─── 便捷方法 ──────────────────────────────────────────

    def file_exists(self, owner, repo, path, branch=None):
        """检查文件是否存在，返回 (exists, sha_or_empty)"""
        info = self.get_file_info(owner, repo, path, branch=branch)
        if info and info.get("type") == "file":
            return True, info.get("sha", "")
        return False, ""


# ═══════════════════════════════════════════════════════════════
# 专辑 API
# ═══════════════════════════════════════════════════════════════

def fetch_album_page(session, begin_msgid="", begin_itemidx="",
                     count=ALBUM_PAGE_SIZE, is_reverse=0,
                     biz=DEFAULT_ALBUM_BIZ, album_id=DEFAULT_ALBUM_ID):
    """抓取专辑一页文章列表（JSON API）。

    返回: (article_list, continue_flag)
    """
    params = {
        "action": "getalbum",
        "__biz": biz,
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
            f"__biz={biz}&action=getalbum&album_id={album_id}"
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


def collect_album_urls(logger, since_date=None, until_date=None,
                       max_pages=None):
    """从专辑遍历文章URL，可选按日期范围过滤。

    参数:
      since_date: 起始日期 (datetime)，None=不限
      until_date: 截止日期 (datetime)，None=不限
      max_pages:  最多遍历几页，None=不限
    返回:
      [{'url': ..., 'title': ..., 'date': 'YYYY-MM-DD'}, ...]
      最新在前
    """
    session = requests.Session()
    all_articles = []
    begin_msgid = ""
    begin_itemidx = ""
    page = 0

    logger.info(f"开始遍历专辑")
    if since_date:
        logger.info(f"  起始日期: {since_date.strftime('%Y-%m-%d')}")
    if until_date:
        logger.info(f"  截止日期: {until_date.strftime('%Y-%m-%d')}")

    while True:
        page += 1
        if max_pages and page > max_pages:
            logger.info(f"已达到最大页数限制 ({max_pages})")
            break

        articles, cf = fetch_album_page(
            session, begin_msgid=begin_msgid,
            begin_itemidx=begin_itemidx, is_reverse=0
        )

        if not articles:
            logger.info(f"第{page}页无文章，遍历结束")
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

            url = html_unescape(a.get("url", ""))
            if url.startswith("http://"):
                url = "https://" + url[7:]
            url = url.split("#")[0]

            title = a.get("title", "")
            all_articles.append({
                "url": url,
                "title": title,
                "date": article_date.strftime("%Y-%m-%d"),
            })

        logger.debug(
            f"  第{page}页: 获取{len(articles)}条，"
            f"累计{len(all_articles)}条，continue_flag={cf}"
        )

        if stop:
            logger.info(f"已到达起始日期边界")
            break
        if cf != "1":
            logger.info(f"已遍历全部专辑 ({page}页)")
            break

        begin_msgid = articles[-1].get("msgid", "")
        begin_itemidx = articles[-1].get("itemidx", "")
        time.sleep(0.3)

    logger.info(f"专辑遍历完成: 共 {len(all_articles)} 篇文章")
    return all_articles


def collect_album_all_dates(logger):
    """遍历整个专辑，返回所有日期的集合 {'YYYY-MM-DD', ...}"""
    articles = collect_album_urls(logger, max_pages=None)
    return {a["date"] for a in articles}


# ═══════════════════════════════════════════════════════════════
# 内容处理（复用自 03_convert-daily.py）
# ═══════════════════════════════════════════════════════════════

def fetch_wechat_html(url, logger, session=None):
    """通过requests抓取微信文章HTML，返回原始HTML字符串或None"""
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
    for attempt in range(3):
        try:
            resp = s.get(url, timeout=30)
            resp.raise_for_status()
            text = resp.text
            if "og:title" in text:
                return text
            logger.debug(
                f"第{attempt+1}次请求未获正文 (长度={len(text)})，重试...")
            time.sleep(1)
        except Exception as e:
            logger.error(f"抓取失败 {url}: {e}")
            return None
    logger.warning(f"多次重试仍无法获取正文: {url}")
    return None


def extract_first_image_url(html_content):
    """从HTML的JS数据中提取正文第一张图片的原始URL（1:1大图）"""
    m = re.search(
        r"window\.picture_page_info_list\s*=\s*\[\s*\{[^}]*?"
        r"cdn_url\s*:\s*'(https?://[^']+)'",
        html_content,
    )
    if m:
        return m.group(1)
    m = re.search(
        r"picture_page_info_list\s*:\s*\[\s*\{[^}]*?"
        r"cdn_url\s*:\s*JsDecode\('(https?://[^']+)'\)",
        html_content,
    )
    if m:
        return m.group(1)
    return None


def get_image_format_from_url(url):
    """从微信CDN图片URL路径判断原始图片格式"""
    if "mmbiz_png" in url:
        return "png"
    if "mmbiz_gif" in url:
        return "gif"
    return "jpg"


def sanitize_image_url(url):
    """清理微信CDN图片URL中不必要的参数"""
    url = re.sub(r"[&?]tp=webp", "", url)
    url = re.sub(r"[&?]usePicPrefetch=\d*", "", url)
    url = re.sub(r"[&?]wxfrom=\d*", "", url)
    return url


def convert_content(raw_content):
    """将og:description原始内容转为Markdown列表"""
    import html as html_mod
    decoded = raw_content.replace(r"\x0a", "\n").replace("\x0a", "\n")
    decoded = decoded.replace(r"\x26", "&").replace("\x26", "&")
    decoded = html_mod.unescape(decoded)

    items, current = [], []
    for line in decoded.split("\n"):
        line = line.strip()
        if line.startswith("-") or line.startswith("\u2022"):
            if current:
                items.append("- " + " ".join(current))
                current = []
            line = line[1:].strip()
        if line:
            current.append(line)
    if current:
        items.append("- " + " ".join(current))
    return "\n\n".join(items)


def extract_date_from_title(title):
    """从标题中提取日期"""
    m = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", title or "")
    if m:
        y, mo, d = m.groups()
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    return None


def download_image_bytes(url, referer="https://mp.weixin.qq.com/"):
    """下载图片，返回bytes或None"""
    headers = {
        "Referer": referer,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        ),
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.content
        return None
    except Exception:
        return None


def compress_image_file(filepath, logger=None):
    """v1.13: 压缩并转换图片（与 04_convert-blog.py 一致，内置工具 + Pillow）

    使用内置 oxipng.exe（piczip/ 目录）+ Pillow（JPEG/GIF 压缩）。
    无需安装任何系统级工具。

    规则（IE6 兼容，仅 jpg/png/gif）:
      - 不透明 PNG → 转为 JPG
      - 透明 PNG → 保留 PNG，oxipng 压缩
      - 动图 GIF → 保留 GIF，Pillow 压缩
      - 静态 GIF → 转为 PNG
      - JPEG → Pillow 压缩 (quality=88, progressive)
      - WebP/AVIF → 按透明度转为 JPG 或 PNG

    返回: (new_filepath, saved_bytes)
    """
    import shutil
    if not os.path.exists(filepath):
        return (filepath, 0)

    # v1.13: 内置工具路径
    _piczip_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "piczip")
    def _get_tool(name):
        local = os.path.join(_piczip_dir, name + (".exe" if sys.platform == "win32" else ""))
        if os.path.isfile(local):
            return local
        return shutil.which(name)

    size_before = os.path.getsize(filepath)
    ext = filepath.rsplit('.', 1)[-1].lower() if '.' in filepath else ''
    base = filepath.rsplit('.', 1)[0] if '.' in filepath else filepath
    new_path = filepath

    def _detect_transparency(fp):
        try:
            from PIL import Image
            img = Image.open(fp)
            has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
            if not has_alpha: return False
            if img.mode == 'P': img = img.convert('RGBA')
            if img.mode == 'RGBA':
                return img.getchannel('A').getextrema()[0] < 255
            return True
        except Exception:
            return False

    def _is_animated(fp):
        try:
            from PIL import Image
            img = Image.open(fp)
            return getattr(img, 'is_animated', False) or getattr(img, 'n_frames', 1) > 1
        except Exception:
            return True

    def _compress_jpeg(fp):
        try:
            from PIL import Image
            img = Image.open(fp)
            if img.mode != 'RGB': img = img.convert('RGB')
            tmp = fp + '.tmp.jpg'
            img.save(tmp, 'JPEG', quality=88, optimize=True, progressive=True)
            if os.path.getsize(tmp) < os.path.getsize(fp):
                os.replace(tmp, fp)
            else:
                os.remove(tmp)
        except Exception:
            pass

    def _compress_gif(fp):
        try:
            from PIL import Image
            img = Image.open(fp)
            tmp = fp + '.tmp.gif'
            save_kwargs = {'optimize': True}
            if getattr(img, 'is_animated', False):
                save_kwargs['save_all'] = True
                save_kwargs['loop'] = getattr(img, 'loop', 0)
                save_kwargs['disposal'] = getattr(img, 'disposal', 2)
            img.save(tmp, 'GIF', **save_kwargs)
            if os.path.getsize(tmp) < os.path.getsize(fp):
                os.replace(tmp, fp)
            else:
                os.remove(tmp)
        except Exception:
            pass

    try:
        # WebP/AVIF → JPG or PNG
        if ext in ('webp', 'avif'):
            is_t = _detect_transparency(filepath)
            new_ext = 'png' if is_t else 'jpg'
            new_path = base + '.' + new_ext
            try:
                from PIL import Image
                img = Image.open(filepath)
                if is_t:
                    img.save(new_path, 'PNG', optimize=True)
                else:
                    img.convert('RGB').save(new_path, 'JPEG', quality=88, optimize=True, progressive=True)
                os.remove(filepath)
                ext = new_ext
            except Exception:
                new_path = filepath

        # PNG
        if ext == 'png':
            if not _detect_transparency(new_path):
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
                oxipng = _get_tool('oxipng')
                if oxipng:
                    subprocess.run([oxipng, '-o', '4', '--strip', 'safe', '--force', new_path], capture_output=True, timeout=120)

        # Static GIF → PNG
        if ext == 'gif' and not _is_animated(new_path):
            png_path = base + '.png'
            try:
                from PIL import Image
                img = Image.open(new_path)
                img.save(png_path, 'PNG', optimize=True)
                os.remove(new_path)
                new_path = png_path
                ext = 'png'
                if not _detect_transparency(new_path):
                    jpg_path = base + '.jpg'
                    img.convert('RGB').save(jpg_path, 'JPEG', quality=88, optimize=True, progressive=True)
                    os.remove(new_path)
                    new_path = jpg_path
                    ext = 'jpg'
                else:
                    oxipng = _get_tool('oxipng')
                    if oxipng:
                        subprocess.run([oxipng, '-o', '4', '--strip', 'safe', '--force', new_path], capture_output=True, timeout=120)
            except Exception:
                pass
        elif ext == 'gif':
            _compress_gif(new_path)

        # JPEG
        if ext in ('jpg', 'jpeg'):
            _compress_jpeg(new_path)

    except Exception as e:
        if logger:
            logger.debug(f'压缩/转换失败 {filepath}: {e}')

    size_after = os.path.getsize(new_path) if os.path.exists(new_path) else size_before
    return (new_path, max(0, size_before - size_after))


# ═══════════════════════════════════════════════════════════════
# 工作流
# ═══════════════════════════════════════════════════════════════

class DailyWorkflow:
    """主工作流：抓取 → 处理 → 上传 → 验证"""

    def __init__(self, gh, logger, output_dir, non_interactive=False):
        self.gh = gh
        self.logger = logger
        self.output_dir = output_dir
        self.non_interactive = non_interactive
        self.overwrite_all = False  # 覆盖确认：all=不再询问
        self.wechat_session = requests.Session()
        self.image_route_cache = {}

    # ─── 仓库查询 ──────────────────────────────────────────

    def get_latest_post_date(self):
        """从daily仓库 _posts/ 获取最新文章日期，无文章返回None"""
        entries = self.gh.list_dir(
            DAILY_REPO["owner"], DAILY_REPO["repo"],
            "_posts", branch=DAILY_REPO["branch"]
        )
        dates = []
        for e in entries:
            m = re.match(r"(\d{4}-\d{2}-\d{2})-daily\.md", e.get("name", ""))
            if m:
                dates.append(m.group(1))
        if not dates:
            return None
        dates.sort(reverse=True)
        return dates[0]

    def get_all_post_dates(self):
        """从daily仓库获取所有文章日期，返回集合 {'YYYY-MM-DD', ...}"""
        entries = self.gh.list_dir(
            DAILY_REPO["owner"], DAILY_REPO["repo"],
            "_posts", branch=DAILY_REPO["branch"]
        )
        dates = set()
        for e in entries:
            m = re.match(r"(\d{4}-\d{2}-\d{2})-daily\.md", e.get("name", ""))
            if m:
                dates.add(m.group(1))
        return dates

    def get_image_route(self, post_date):
        """读取 daily 的 _config.yml，并按文章月份确定图片上传路由。"""
        date_key = post_date[:7]
        if date_key not in self.image_route_cache:
            route = load_upload_route(
                self.gh.get_file_info,
                f"{DAILY_REPO['owner']}/{DAILY_REPO['repo']}",
                DAILY_REPO["branch"],
                post_date,
            )
            self.image_route_cache[date_key] = route
            self.logger.info(
                "图床路由: %s → %s@%s",
                date_key, route["repository"], route["branch"],
            )
        return self.image_route_cache[date_key]

    # ─── 交互 ──────────────────────────────────────────────

    def ask_overwrite(self, repo_path):
        """询问用户是否覆盖已有文件；后台模式绝不等待输入且默认跳过。"""
        if self.overwrite_all:
            return "yes"
        if self.non_interactive:
            self.logger.info(f"后台模式：远程文件已存在，跳过覆盖: {repo_path}")
            return "no"
        while True:
            try:
                answer = input(
                    f"  ⚠ 文件已存在: {repo_path}\n"
                    f"  覆盖？(y/n/all): "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return "no"
            if answer in ("y", "yes"):
                return "yes"
            if answer in ("n", "no"):
                return "no"
            if answer == "all":
                self.overwrite_all = True
                return "yes"
            print("  请输入 y / n / all")

    # ─── 上传与备份 ─────────────────────────────────────────

    def upload_with_backup(self, owner, repo, path, content_bytes,
                           message, branch, local_backup_path=None):
        """上传文件到GitHub，如已存在则备份后确认覆盖。

        返回: True=成功, False=跳过
        """
        exists, sha = self.gh.file_exists(owner, repo, path, branch=branch)

        if exists:
            # 先决定是否覆盖。后台模式会直接跳过，避免无效下载和本地备份。
            answer = self.ask_overwrite(f"{owner}/{repo}/{path}")
            if answer == "no":
                self.logger.info(f"跳过覆盖: {path}")
                return False

            # 仅在明确覆盖时备份已有远程文件。
            if local_backup_path:
                existing_bytes = self.gh.download_file_bytes(
                    owner, repo, path, branch=branch)
                if existing_bytes:
                    os.makedirs(os.path.dirname(local_backup_path),
                                exist_ok=True)
                    with open(local_backup_path, "wb") as f:
                        f.write(existing_bytes)
                    self.logger.info(f"已备份旧版: {local_backup_path}")

        # 上传
        try:
            self.gh.upload_file(
                owner, repo, path, content_bytes,
                message=message, branch=branch, sha=sha if exists else None
            )
            self.logger.info(f"已上传: {path}")
            return True
        except Exception as e:
            self.logger.error(f"上传失败 {path}: {e}")
            return False

    def verify_file(self, owner, repo, path, branch):
        """验证文件是否已在仓库中"""
        exists, _ = self.gh.file_exists(owner, repo, path, branch=branch)
        if exists:
            self.logger.debug(f"验证通过: {path}")
            return True
        self.logger.warning(f"验证失败: {path} 未在仓库中找到")
        return False

    # ─── 核心处理 ──────────────────────────────────────────

    def process_and_upload(self, url):
        """处理单篇文章：抓取 → 生成MD/下载图 → 上传 → 验证。

        返回: True=成功, False=失败/跳过
        """
        import html as html_mod

        # 1. 抓取微信文章
        self.logger.info(f"抓取文章: {url[:80]}...")
        raw_html = fetch_wechat_html(url, self.logger,
                                     session=self.wechat_session)
        if not raw_html:
            self.logger.error("抓取文章HTML失败")
            return False

        # 2. 提取元数据
        soup = BeautifulSoup(raw_html, "html.parser")
        meta = {}
        for tag in soup.find_all("meta", property=True):
            if "og:" in tag["property"]:
                meta[tag["property"]] = tag.get("content", "")

        # 3. 提取日期
        title_raw = meta.get("og:title", "")
        post_date = extract_date_from_title(title_raw)
        if not post_date:
            self.logger.warning("无法提取日期，跳过")
            return False
        year, month, day = post_date.split("-")

        # 4. 提取封面图
        first_img = extract_first_image_url(raw_html)
        og_img = meta.get("og:image", "")

        img_bytes = None
        img_ext = "jpg"
        dl_url = ""

        if first_img:
            self.logger.info("使用正文原始题图（1:1大图）")
            dl_url = sanitize_image_url(first_img)
            img_ext = get_image_format_from_url(first_img)
        elif og_img:
            self.logger.info("回退使用 og:image（可能为裁剪版）")
            dl_url = sanitize_image_url(og_img)
            img_ext = get_image_format_from_url(og_img)
        else:
            self.logger.warning("未找到封面图URL")

        if dl_url:
            self.logger.info(f"下载封面图（{img_ext.upper()}）...")
            img_bytes = download_image_bytes(dl_url)

        # 5. 生成GitHub图片URL和Markdown
        image_url = (
            f"{GITHUB_IMAGE_BASE_URL}/{year}/{month}/"
            f"{month}{day}-d.{img_ext}"
        )

        if "og:description" not in meta:
            self.logger.warning("未找到 og:description，跳过")
            return False

        content = convert_content(meta["og:description"])
        title = html_mod.unescape(title_raw or f"每日 AIGC 早报：{post_date}")

        front_matter = (
            f"---\n"
            f"layout: post\n"
            f'title: "{title}"\n'
            f"date: {post_date}\n"
            f"categories: AIGC日报\n"
            f"tags: [AIGC]\n"
            f"image: {image_url}\n"
            f"---\n\n"
        )
        md_content = (front_matter + content).encode("utf-8")

        # 6. 本地保存
        img_dir = os.path.join(self.output_dir, "images", year, month)
        img_name = f"{month}{day}-d.{img_ext}"
        img_local = os.path.join(img_dir, img_name)
        if img_bytes:
            os.makedirs(img_dir, exist_ok=True)
            with open(img_local, "wb") as f:
                f.write(img_bytes)
            self.logger.info(f"本地保存图片: {img_local}")
            # v1.12: 上传前压缩并转换格式（不透明PNG→JPG, WebP→JPG/PNG, 静态GIF→PNG）
            try:
                new_img_local, saved = compress_image_file(img_local, self.logger)
                if saved > 0:
                    self.logger.info(f"压缩节省: {saved/1024:.1f}KB")
                # 格式转换后扩展名可能变化，更新 img_name 和 image_url
                new_img_name = os.path.basename(new_img_local)
                if new_img_name != img_name:
                    self.logger.info(f"格式转换: {img_name} → {new_img_name}")
                    img_name = new_img_name
                    img_ext = new_img_name.rsplit('.', 1)[-1]
                    # 更新 image_url 和 md_content 中的引用
                    image_url = (
                        f"{GITHUB_IMAGE_BASE_URL}/{year}/{month}/"
                        f"{month}{day}-d.{img_ext}"
                    )
                    front_matter = (
                        f"---\n"
                        f"layout: post\n"
                        f'title: "{title}"\n'
                        f"date: {post_date}\n"
                        f"categories: AIGC日报\n"
                        f"tags: [AIGC]\n"
                        f"image: {image_url}\n"
                        f"---\n\n"
                    )
                    md_content = (front_matter + content).encode("utf-8")
                # 重新读取压缩/转换后的 bytes
                with open(new_img_local, "rb") as f:
                    img_bytes = f.read()
                img_local = new_img_local
            except Exception as e:
                self.logger.debug(f"压缩失败: {e}")

        md_dir = os.path.join(self.output_dir, "_posts")
        md_name = f"{post_date}-daily.md"
        md_local = os.path.join(md_dir, md_name)
        os.makedirs(md_dir, exist_ok=True)
        with open(md_local, "w", encoding="utf-8") as f:
            f.write(md_content.decode("utf-8"))
        self.logger.info(f"本地保存Markdown: {md_local}")

        # 7. 上传图片。上传前必须读取 daily 的 _config.yml，按文章月份选图床。
        image_route = None
        img_ok = True
        if img_bytes:
            try:
                image_route = self.get_image_route(post_date)
            except ImageRouteError as e:
                self.logger.error(f"无法确定图片上传图床，终止发布以避免产生失效引用: {e}")
                return False

            img_owner, img_repo = image_route["repository"].split("/", 1)
            img_repo_path = join_repo_path(
                image_route, f"{year}/{month}/{img_name}")
            img_bak_local = os.path.join(
                img_dir, f"{month}{day}-d_bak.{img_ext}")
            img_ok = self.upload_with_backup(
                img_owner, img_repo,
                img_repo_path, img_bytes,
                message=f"上传封面图 {post_date}",
                branch=image_route["branch"],
                local_backup_path=img_bak_local,
            )
        else:
            self.logger.warning("无图片数据，跳过图片上传")

        # 8. 上传Markdown到 daily repo
        md_repo_path = f"_posts/{md_name}"
        md_bak_local = os.path.join(md_dir, f"{post_date}-daily_bak.md")
        md_ok = self.upload_with_backup(
            DAILY_REPO["owner"], DAILY_REPO["repo"],
            md_repo_path, md_content,
            message=f"发布早报 {post_date}",
            branch=DAILY_REPO["branch"],
            local_backup_path=md_bak_local,
        )

        # 9. 验证
        if md_ok:
            v1 = self.verify_file(
                DAILY_REPO["owner"], DAILY_REPO["repo"],
                md_repo_path, DAILY_REPO["branch"])
            if not v1:
                self.logger.warning(f"文章验证失败: {md_repo_path}")

        if img_ok and img_bytes and image_route:
            img_owner, img_repo = image_route["repository"].split("/", 1)
            v2 = self.verify_file(
                img_owner, img_repo, img_repo_path, image_route["branch"])
            if not v2:
                self.logger.warning(f"图片验证失败: {img_repo_path}")

        return md_ok

    # ─── 工作模式 ──────────────────────────────────────────

    def auto_fetch(self):
        """无参数模式：检测仓库最新日期，抓取专辑中更新的文章"""
        self.logger.info("═══ 自动模式 ═══")

        # 1. 获取仓库最新日期
        latest = self.get_latest_post_date()
        if latest:
            self.logger.info(f"仓库最新文章: {latest}")
        else:
            self.logger.info("仓库无文章，将抓取专辑全部内容")
            return self.fetch_all()

        # 2. 以远程 daily 仓库完整日期集合做差集判定。日期相同即视为已发布，
        # 避免首次启动或重试再次抓取同一篇文章并触发覆盖提示。
        known_dates = self.get_all_post_dates()
        since_date = datetime.strptime(latest, "%Y-%m-%d")
        candidates = collect_album_urls(
            self.logger, since_date=since_date,
            max_pages=AUTO_MAX_PAGES
        )
        articles = [item for item in candidates if item.get("date") not in known_dates]

        if not articles:
            self.logger.info("没有发现尚未发布到 daily 仓库的文章")
            return

        self.logger.info(f"发现 {len(articles)} 篇尚未发布的文章")
        self._process_articles(articles)

    def fetch_date_range(self, since_date, until_date=None):
        """抓取指定日期范围的文章并上传"""
        desc = f"自 {since_date.strftime('%Y-%m-%d')}"
        if until_date:
            desc += f" 至 {until_date.strftime('%Y-%m-%d')}"
        self.logger.info(f"═══ 日期范围模式: {desc} ═══")

        articles = collect_album_urls(
            self.logger, since_date=since_date, until_date=until_date
        )

        if not articles:
            self.logger.info("指定日期范围内没有文章")
            return

        self.logger.info(f"共 {len(articles)} 篇文章待处理")
        self._process_articles(articles)

    def fetch_all(self):
        """抓取专辑全部文章并上传"""
        self.logger.info("═══ 全量模式 ═══")

        # 确认
        try:
            answer = input(
                "  将抓取专辑全部文章（约450+篇），确认？(y/n): "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if answer not in ("y", "yes"):
            self.logger.info("已取消")
            return

        articles = collect_album_urls(self.logger, max_pages=None)
        if not articles:
            self.logger.info("专辑无文章")
            return

        self._process_articles(articles)

    def diff(self):
        """对比专辑与仓库差异，显示缺失的文章日期"""
        self.logger.info("═══ 差异对比模式 ═══")

        # 1. 获取仓库所有日期
        self.logger.info("获取仓库文章列表...")
        repo_dates = self.get_all_post_dates()
        self.logger.info(f"仓库已有 {len(repo_dates)} 篇文章")

        # 2. 遍历专辑获取所有日期
        self.logger.info("遍历专辑获取全部日期...")
        album_dates = collect_album_all_dates(self.logger)
        self.logger.info(f"专辑共有 {len(album_dates)} 个日期")

        # 3. 计算差异
        missing = sorted(album_dates - repo_dates)
        extra = sorted(repo_dates - album_dates)

        print(f"\n{'='*60}")
        print(f"  专辑文章数: {len(album_dates)}")
        print(f"  仓库文章数: {len(repo_dates)}")
        print(f"  缺失（专辑有/仓库无）: {len(missing)} 篇")
        print(f"  多余（仓库有/专辑无）: {len(extra)} 篇")

        if missing:
            print(f"\n  缺失日期列表:")
            # 按年月分组显示
            current_ym = ""
            for d in missing:
                ym = d[:7]
                if ym != current_ym:
                    current_ym = ym
                    print(f"\n    {ym}:")
                print(f"      {d}")

        if extra:
            print(f"\n  多余日期（仓库有但专辑无）:")
            for d in extra[:20]:
                print(f"      {d}")
            if len(extra) > 20:
                print(f"      ... 共 {len(extra)} 篇")

        print(f"{'='*60}")

        # 4. 询问是否抓取缺失的
        if missing:
            try:
                answer = input(
                    f"\n  是否抓取这 {len(missing)} 篇缺失文章？(y/n): "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if answer in ("y", "yes"):
                self._fetch_missing(missing)

    def _fetch_missing(self, missing_dates):
        """抓取指定日期列表的文章"""
        # 将日期列表转为范围，避免全量遍历
        # 策略：遍历专辑，只处理缺失日期的文章
        self.logger.info(f"开始抓取 {len(missing_dates)} 篇缺失文章...")

        missing_set = set(missing_dates)
        session = requests.Session()
        all_articles = []
        begin_msgid = ""
        begin_itemidx = ""
        page = 0
        earliest_missing = min(missing_dates)

        while True:
            page += 1
            articles, cf = fetch_album_page(
                session, begin_msgid=begin_msgid,
                begin_itemidx=begin_itemidx, is_reverse=0
            )
            if not articles:
                break

            for a in articles:
                create_time = int(a.get("create_time", 0))
                if create_time == 0:
                    continue
                dt = datetime.fromtimestamp(create_time)
                article_date = dt.replace(hour=0, minute=0, second=0,
                                          microsecond=0)
                date_str = article_date.strftime("%Y-%m-%d")

                if date_str in missing_set:
                    url = html_unescape(a.get("url", ""))
                    if url.startswith("http://"):
                        url = "https://" + url[7:]
                    url = url.split("#")[0]
                    all_articles.append({
                        "url": url,
                        "title": a.get("title", ""),
                        "date": date_str,
                    })

            # 如果当前页最旧的文章日期已早于最早的缺失日期，停止
            last_time = int(articles[-1].get("create_time", 0))
            if last_time:
                last_dt = datetime.fromtimestamp(last_time).replace(
                    hour=0, minute=0, second=0, microsecond=0)
                if last_dt.strftime("%Y-%m-%d") < earliest_missing:
                    break

            if cf != "1":
                break
            begin_msgid = articles[-1].get("msgid", "")
            begin_itemidx = articles[-1].get("itemidx", "")
            time.sleep(0.3)

        if not all_articles:
            self.logger.info("未找到可抓取的文章")
            return

        self.logger.info(f"找到 {len(all_articles)} 篇缺失文章")
        self._process_articles(all_articles)

    def _process_articles(self, articles):
        """批量处理文章列表"""
        ok, fail, skip = 0, 0, 0
        total = len(articles)

        for i, a in enumerate(articles, 1):
            self.logger.info(f"[{i}/{total}] {a['date']} | {a['title']}")
            try:
                result = self.process_and_upload(a["url"])
                if result:
                    ok += 1
                else:
                    skip += 1
            except Exception as e:
                self.logger.error(f"处理失败: {e}")
                fail += 1

            # 礼貌延迟
            if i < total:
                time.sleep(0.5)

        self.logger.info(
            f"═══ 完成: {ok} 成功, {skip} 跳过, {fail} 失败 ═══"
        )


# ═══════════════════════════════════════════════════════════════
# 参数解析
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    # 解析参数
    album_mode = None
    since_date = None
    until_date = None
    non_interactive = "--non-interactive" in sys.argv[1:]

    for a in sys.argv[1:]:
        if a == "--non-interactive":
            continue
        if a.startswith("album"):
            album_mode, since_date, until_date = parse_album_arg(a)
        elif a.startswith("http"):
            # 兼容：直接传URL
            pass

    # 获取 GitHub Token
    token = get_github_token()
    if not token:
        print_token_help()
        sys.exit(1)

    # 初始化
    output_dir = os.getcwd()
    logger, log_path = setup_logging(output_dir)
    logger.info(f"工作目录: {output_dir}")
    logger.info(f"日志文件: {log_path}")

    gh = GitHubAPI(token, logger)

    # 验证Token有效性
    try:
        resp = gh._request("GET", "/user")
        if resp.status_code == 200:
            username = resp.json().get("login", "?")
            logger.info(f"GitHub 认证成功: {username}")
        else:
            logger.error(f"GitHub 认证失败: {resp.status_code}")
            print_token_help()
            sys.exit(1)
    except Exception as e:
        logger.error(f"GitHub API 连接失败: {e}")
        sys.exit(1)

    # 创建工作流
    workflow = DailyWorkflow(gh, logger, output_dir, non_interactive=non_interactive)

    # 执行
    if album_mode == "diff":
        workflow.diff()
    elif album_mode == "all":
        workflow.fetch_all()
    elif album_mode == "range":
        workflow.fetch_date_range(since_date, until_date)
    else:
        # 无参数：自动模式
        workflow.auto_fetch()


if __name__ == "__main__":
    main()
