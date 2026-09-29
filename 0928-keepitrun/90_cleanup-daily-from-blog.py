#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
90_cleanup-daily-from-blog.py - AIGC 早报清理脚本 (v2.0 快速扫描)

用途：
  清理之前因 04_convert-blog.py bug 误同步到主博客 lishuhang.me 的 AIGC 早报内容。
  AIGC 早报应仅在 lishuhang.me/daily/ 显示（由 03_convert-daily.py 发布到
  lishuhang/daily 仓库），不应出现在主博客 lishuhang.github.io 仓库。

v2.0 重构 (2026-09-29) — 冷启动性能重建:
  0928 生产日志显示 v1.9 每日首次启动三连 1800 秒超时（合计拖慢冷启动约 90 分钟），
  且自 v1.9 上线以来从未完成过一次完整扫描（task_completion.json 无 cleanup 记录）。
  根因与处置：
  - 根因 1：对 _posts 每个文件逐个调用 Contents API 拉全文（每文件 1 次 API 调用），
    _posts 实际有 1458 个 .md，按每文件约 0.5 秒需要 12 分钟以上，且远超 GitHub API
    限速可承受量，在 1800 秒时限内永远无法完成。
  - 根因 2：旧分页列表依赖 Contents API 的 per_page 参数，但该接口对目录列表忽略
    per_page（每页实际返回 1000 条），导致 1458 个文件被重复计数成 20000 个，
    且第 1000 名之后的文件从未被检查过。
  - 处置 1：改用 Git Trees API（1 次调用）获取真实文件清单与 blob sha。
  - 处置 2：文件内容改经 raw.githubusercontent.com CDN 并行拉取（默认 16 线程，
    不占用 GitHub API 限速配额）。
  - 处置 3：新增增量缓存 cleanup_scan_memory.json（path → sha → 判定结果）：
    内容未变化的文件不再重新拉取，首次全量扫描约 1 分钟，之后每次运行只检查
    新增/变更文件（秒级）。
  - 处置 4：--time-budget（默认 900 秒）内未完成时保存进度并以退出码 2 结束，
    由外层调度按失败重试；重试与次日运行均从缓存断点续扫，不会从头重来。
  - 判定语义修正：v1.9 对文件名含 "aigc"/"早报" 的文件不经内容确认即判待删除，
    会误删正经 AIGC 主题文章（如 2024-03-22-aigc-shi-dai-de-di-yi.md）。
    v2.0 判定 = front matter 内容匹配（categories/tags/title 模式与 v1.9 相同）
    或 无歧义拼音组合文件名（mei-ri-aigc*/aigc-zao-bao*）；
    裸 "aigc"/"早报" 文件名仅记为候选输出，不单独构成删除依据。
    （03_convert-daily.py 生成的早报文件名是 YYYY-MM-DD-daily.md，v1.9 的拼音
    文件名模式本就匹配不到真实泄漏文件——内容匹配才是唯一可靠判据。）

v1.9 修复 (2026-07-03):
  - 修复分支检测 bug：v1.8 硬编码 BLOG_REPO_BRANCH = "master"，但
    lishuhang.github.io 仓库默认分支是 "main"，导致 v1.8 的清理脚本
    404 失败。v1.9 改为自动探测分支（先试 main，再试 master）。
  - 改进匹配逻辑：除 categories/tags/title 外，还检查文件名 pinyin 模式
    (mei-ri-aigc-zao-bao / aigc-zao-bao)。
  - 添加 "贴图" category 匹配（v1.7 bug 将 AIGC 早报误标为 "贴图"）。
  - 添加 --batch 参数：批量删除模式（使用 Git Data API 单次 commit
    删除多个文件，减少 GitHub API 调用）。
  - keepitrun.py v1.9 会在首次启动时自动调用此脚本。

工作流程 (v2.0):
  1. 自动探测仓库默认分支（查询 default_branch，失败则 main → master 探测）
  2. Git Trees API 一次列出 _posts/ 下所有 .md 文件（失败时回退 Contents 分页）
  3. 对照本地缓存按 sha 增量检查：
     - sha 未变：直接复用缓存判定（match / nomatch）
     - sha 未知或内容有变：经 raw CDN 并行拉取全文后按内容判定
  4. 匹配的文件通过 GitHub API 批量删除（默认单批连续调用）
  5. 输出清理报告；未在时间预算内完成时缓存断点并以退出码 2 结束

用法:
  python 90_cleanup-daily-from-blog.py                # 执行清理（批量模式）
  python 90_cleanup-daily-from-blog.py --dry-run      # 仅列出待删除文件
  python 90_cleanup-daily-from-blog.py --verbose      # 详细日志
  python 90_cleanup-daily-from-blog.py --refresh      # 忽略缓存强制全量重扫
  python 90_cleanup-daily-from-blog.py --no-batch     # 每文件单独 commit（慢）
  python 90_cleanup-daily-from-blog.py --time-budget 600 --workers 8

退出码:
  0 = 扫描完成（无论是否有匹配）
  1 = 致命错误（认证失败、列目录失败等）
  2 = 时间预算内未完成全部内容检查（进度已缓存，可续扫）

环境变量 (.env):
  GITHUB_TOKEN  - GitHub Personal Access Token（需 repo 权限）

注意：
  - keepitrun.py 在每日首次启动时自动调用（--dry-run 预览通过后才执行实际删除）
  - 也可手动运行，支持 --dry-run 预览
  - 只清理 lishuhang.github.io 仓库，不影响 lishuhang/daily 仓库
"""

import os
import sys
import re
import json
import time
import argparse
import requests
import base64
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

# ================= Windows 编码修复 =================
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stdout.detach())

# ================= 配置 =================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 主博客仓库（AIGC 早报误同步到这里）
BLOG_REPO = "lishuhang/lishuhang.github.io"
BLOG_REPO_POSTS_PATH = "_posts"
# v1.9: 不再硬编码分支，运行时自动探测
# v2.0: raw 内容 CDN 基址
RAW_BASE = f"https://raw.githubusercontent.com/{BLOG_REPO}"

# 增量缓存（path → sha → 判定），与 rss_issue_memory.json 同为运行时状态
SCAN_MEMORY_PATH = os.path.join(SCRIPT_DIR, "cleanup_scan_memory.json")
SCAN_MEMORY_VERSION = 2

# 匹配 AIGC 早报的判断关键词
AIGC_CATEGORY_PATTERNS = [
    r'AIGC日报',
    r'AIGC\s*早报',
    r'贴图',  # v1.7 bug: AIGC 早报被误标为 "贴图" category
]
AIGC_TAG_PATTERNS = [
    r'\bAIGC\b',
    r'贴图',
]
AIGC_TITLE_PATTERNS = [
    r'AIGC\s*早报',
    r'每日\s*AIGC',
]
# 无歧义拼音组合文件名模式（命中即判定，无需内容确认）
# 注意：裸 "aigc" 不是无歧义模式（会误伤正经 AIGC 主题文章），不在此列
AIGC_FILENAME_PATTERNS = [
    r'mei-ri-aigc',
    r'aigc-zao-bao',
    r'mei-ri-aigc-zao-bao',
]
# 03_convert-daily.py 生成的早报文件名样式（调度时优先检查这类文件）
DAILY_FILENAME_RE = re.compile(r'^\d{4}-\d{2}-\d{2}-daily(_bak)?\.md$', re.IGNORECASE)

GITHUB_API_BASE = "https://api.github.com"


def load_env():
    """加载同目录 .env 文件"""
    env_path = os.path.join(SCRIPT_DIR, ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except OSError:
        pass


def github_request(method, path, token, json_body=None, return_raw=False):
    """发送 GitHub API 请求"""
    url = f"{GITHUB_API_BASE}{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        resp = requests.request(
            method, url, headers=headers,
            json=json_body, timeout=30
        )
        if resp.status_code in (200, 201):
            if return_raw:
                return resp.content, None
            try:
                return resp.json(), None
            except ValueError:
                return None, f"非 JSON 响应: {resp.text[:200]}"
        elif resp.status_code == 404:
            return None, "not found"
        elif resp.status_code == 401:
            return None, "认证失败 (401)：检查 GITHUB_TOKEN 是否有效"
        elif resp.status_code == 403:
            return None, f"权限不足或触发限流 (403): {resp.text[:200]}"
        else:
            return None, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except requests.RequestException as e:
        return None, str(e)


def detect_branch(token):
    """v1.9: 自动探测仓库默认分支

    先查仓库信息获取 default_branch，失败则尝试 main → master 顺序探测。
    返回: (branch_name, error_message)
    """
    # 方法 1: 查询仓库信息
    result, err = github_request("GET", f"/repos/{BLOG_REPO}", token)
    if not err and isinstance(result, dict):
        db = result.get("default_branch", "")
        if db:
            return db, None

    # 方法 2: 尝试 main 分支
    result, err = github_request(
        "GET",
        f"/repos/{BLOG_REPO}/contents/{BLOG_REPO_POSTS_PATH}?ref=main&per_page=1",
        token
    )
    if not err:
        return "main", None

    # 方法 3: 尝试 master 分支
    result, err = github_request(
        "GET",
        f"/repos/{BLOG_REPO}/contents/{BLOG_REPO_POSTS_PATH}?ref=master&per_page=1",
        token
    )
    if not err:
        return "master", None

    return None, f"无法探测分支（main 和 master 均失败）: {err}"


def list_posts_trees(token, branch):
    """v2.0: 用 Git Trees API 一次列出 _posts/ 下所有 .md 文件

    返回与旧 list_posts 相同形状的条目（name/path/sha，无 content）。
    优点：1 次 API 调用、无分页截断、无重复计数。
    """
    path = f"/repos/{BLOG_REPO}/git/trees/{branch}?recursive=1"
    result, err = github_request("GET", path, token)
    if err:
        return None, err
    if not isinstance(result, dict):
        return None, f"意外的响应类型: {type(result)}"

    prefix = BLOG_REPO_POSTS_PATH + "/"
    truncated = bool(result.get("truncated"))
    files = []
    for item in result.get("tree", []):
        p = item.get("path", "")
        if item.get("type") == "blob" and p.startswith(prefix) and p.endswith(".md"):
            files.append({
                "name": p.rsplit("/", 1)[-1],
                "path": p,
                "sha": item.get("sha", ""),
            })
    if truncated:
        # 仓库极大导致树被截断时不能保证清单完整，明确报错并回退
        return None, f"git trees 响应被截断（truncated=true），{len(files)} 个文件不完整"
    return files, None


def list_posts(token, branch, verbose=False):
    """v1.9 旧流程（回退用）：Contents API 分页列出 _posts 目录

    注意：该接口对目录列表忽略 per_page（每页实际返回最多 1000 条），超过
    1000 个文件的目录只能看到字典序前 1000 个，仅作为 trees API 失败时的回退。
    """
    all_files = []
    page = 1
    while True:
        path = f"/repos/{BLOG_REPO}/contents/{BLOG_REPO_POSTS_PATH}?ref={branch}&per_page=100&page={page}"
        result, err = github_request("GET", path, token)
        if err:
            if "not found" in err:
                return [], None
            return None, err
        if not isinstance(result, list):
            return None, f"意外的响应类型: {type(result)}"
        all_files.extend(result)
        if len(result) < 100:
            break
        page += 1
        if page > 20:
            break
    if verbose:
        print(f"[INFO] _posts/ 目录共找到 {len(all_files)} 个文件 (branch: {branch})")
    return all_files, None


# ═══════════════════════════════════════════════════════════════
# v2.0: 增量扫描缓存
# ═══════════════════════════════════════════════════════════════

_cache_lock = threading.Lock()


def load_scan_memory():
    """加载增量扫描缓存；损坏或版本不符时返回空缓存"""
    if not os.path.isfile(SCAN_MEMORY_PATH):
        return {}
    try:
        with open(SCAN_MEMORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or data.get("version") != SCAN_MEMORY_VERSION:
            return {}
        entries = data.get("entries")
        if not isinstance(entries, dict):
            return {}
        return entries
    except (json.JSONDecodeError, OSError):
        return {}


def save_scan_memory(entries):
    """原子保存增量扫描缓存（写临时文件后替换）"""
    payload = {
        "version": SCAN_MEMORY_VERSION,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "entries": entries,
    }
    tmp_path = SCAN_MEMORY_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        os.replace(tmp_path, SCAN_MEMORY_PATH)
        return True
    except OSError as e:
        print(f"[WARN] 缓存写入失败（不影响本次结果）: {e}")
        try:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False


def update_cache_entry(entries, path, sha, verdict):
    """线程安全地更新单个缓存条目"""
    with _cache_lock:
        entries[path] = {
            "sha": sha,
            "verdict": verdict,
            "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def fetch_raw_content(session, repo_path, branch, token):
    """v2.0: 经 raw.githubusercontent.com CDN 拉取文件全文

    不占用 GitHub API 限速配额；429 时指数退避重试。
    返回: (content_text, error_message)
    """
    url = f"{RAW_BASE}/{branch}/{quote(repo_path)}"
    headers = {"Authorization": f"token {token}"} if token else {}
    delay = 1.0
    for attempt in range(3):
        try:
            resp = session.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                return resp.text, None
            if resp.status_code == 429:
                time.sleep(delay)
                delay *= 2
                continue
            if resp.status_code == 404:
                return None, "not found"
            return None, f"HTTP {resp.status_code}"
        except requests.RequestException as e:
            if attempt == 2:
                return None, str(e)[:120]
            time.sleep(delay)
            delay *= 2
    return None, "HTTP 429 (重试后仍限流)"


# ═══════════════════════════════════════════════════════════════
# 判定逻辑
# ═══════════════════════════════════════════════════════════════

def is_aigc_daily_post(filename, content, verbose=False):
    """判断文件是否为 AIGC 早报 (v2.0 语义)

    1. 无歧义拼音组合文件名（mei-ri-aigc* / aigc-zao-bao*）→ 直接判定
    2. front matter 内容匹配（categories/tags/title，模式与 v1.9 完全相同）
    注意：裸 "aigc"/"早报" 文件名不再单独构成判定（会误删正经 AIGC 主题文章），
    此类文件与其他文件一样走内容判据。
    """
    # 1. 文件名 pinyin 组合模式匹配（无歧义）
    fn_lower = filename.lower()
    for pat in AIGC_FILENAME_PATTERNS:
        if re.search(pat, fn_lower):
            if verbose:
                print(f"  [MATCH filename pinyin pattern={pat}] {filename}")
            return True

    # 2. 解析 front matter
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)

        # 检查 categories (含 "贴图")
        cat_match = re.search(r'^categories:\s*(.+?)$', fm, re.MULTILINE)
        if cat_match:
            cat_val = cat_match.group(1).strip()
            for pat in AIGC_CATEGORY_PATTERNS:
                if re.search(pat, cat_val, re.IGNORECASE):
                    if verbose:
                        print(f"  [MATCH categories={cat_val}] {filename}")
                    return True

        # 检查 tags (含 "贴图")
        tag_section_match = re.search(r'^tags:\s*(.*?)$', fm, re.MULTILINE)
        if tag_section_match:
            tag_val = tag_section_match.group(1).strip()
            if tag_val.startswith("["):
                for pat in AIGC_TAG_PATTERNS:
                    if re.search(pat, tag_val, re.IGNORECASE):
                        if verbose:
                            print(f"  [MATCH tags={tag_val}] {filename}")
                        return True

        # 多行 tags（v2.0 修复：允许 YAML 标准缩进列表；v1.9 的 ^- 只匹配顶格，
        # 对缩进的 "- 贴图" 永远不命中，等于死代码）
        tag_multi = re.findall(r'^\s*-\s+(.+?)$', fm, re.MULTILINE)
        for tag in tag_multi:
            for pat in AIGC_TAG_PATTERNS:
                if re.search(pat, tag, re.IGNORECASE):
                    if verbose:
                        print(f"  [MATCH tags item={tag}] {filename}")
                    return True

    # 3. 标题检查
    title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1)
        for pat in AIGC_TITLE_PATTERNS:
            if re.search(pat, title, re.IGNORECASE):
                if verbose:
                    print(f"  [MATCH title={title}] {filename}")
                return True

    return False


def weak_filename_candidate(filename):
    """v2.0: 文件名疑似候选（仅用于透明化输出，不构成删除判定）

    v1.9 曾把这类文件名直接判为待删除，存在误删正经 AIGC 主题文章的风险。
    """
    fn_lower = filename.lower()
    return "aigc" in fn_lower or "早报" in filename


def delete_file_single(file_info, token, branch, reason="v2.0 cleanup: 移除误同步的 AIGC 早报"):
    """单文件删除（每个文件单独 commit）"""
    path = file_info.get("path", "")
    sha = file_info.get("sha", "")
    if not path or not sha:
        return False, "缺少 path 或 sha"

    body = {
        "message": f"cleanup: {reason} - {os.path.basename(path)}",
        "sha": sha,
        "branch": branch,
    }
    _, err = github_request("DELETE", f"/repos/{BLOG_REPO}/contents/{path}", token, json_body=body)
    if err:
        return False, err
    return True, ""


def delete_files_batch(files, token, branch, reason="v2.0 cleanup: 移除误同步的 AIGC 早报"):
    """批量删除（Contents API 逐个删除，连续调用）

    Git Data API 构造整树删除对 _posts/ 目录不实际，沿用 v1.9 的方案。
    """
    success_count = 0
    fail_count = 0
    errors = []

    for i, f in enumerate(files, 1):
        name = f.get("name", "")
        ok, err = delete_file_single(f, token, branch, reason)
        if ok:
            success_count += 1
            print(f"      [{i}/{len(files)}] [OK] {name}")
        else:
            fail_count += 1
            errors.append((name, err))
            print(f"      [{i}/{len(files)}] [FAIL] {name}: {err}")
        # 短暂延迟避免限流
        time.sleep(0.5)

    return success_count, fail_count, errors


# ═══════════════════════════════════════════════════════════════
# v2.0: 增量内容扫描
# ═══════════════════════════════════════════════════════════════

def scan_contents(md_files, branch, token, cache, workers=16, time_budget=900.0,
                  verbose=False, refresh=False):
    """按 sha 增量检查每个文件的内容并给出判定

    返回 dict:
      verdicts   {path: bool}  全部文件的最终判定（仅包含已确定者）
      fetched    本次实际拉取数
      cache_hits 缓存命中数
      errors     拉取失败数
      incomplete 是否因时间预算未完成
    """
    now_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    verdicts = {}
    need_fetch = []

    for f in md_files:
        p = f.get("path", "")
        entry = cache.get(p)
        if (not refresh) and entry and entry.get("sha") == f.get("sha") \
                and entry.get("verdict") in ("match", "nomatch"):
            verdicts[p] = (entry["verdict"] == "match")
        else:
            need_fetch.append(f)

    # 疑似早报文件名（YYYY-MM-DD-daily.md）优先检查：即使预算中断也先查最可能的
    need_fetch.sort(key=lambda f: 0 if DAILY_FILENAME_RE.match(f.get("name", "")) else 1)

    stats = {"fetched": 0, "cache_hits": len(md_files) - len(need_fetch), "errors": 0}
    incomplete = False
    deadline = time.monotonic() + max(1.0, float(time_budget))

    if need_fetch:
        print(f"  需拉取内容检查: {len(need_fetch)} 个（缓存命中 {stats['cache_hits']} 个）")
        session = requests.Session()
        processed = 0
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {
                pool.submit(fetch_raw_content, session, f.get("path", ""), branch, token): f
                for f in need_fetch
            }
            for fut in as_completed(futures):
                f = futures[fut]
                p = f.get("path", "")
                name = f.get("name", "")
                try:
                    content, ferr = fut.result()
                except Exception as e:  # 防御：任何线程异常都不应中断整体扫描
                    content, ferr = None, str(e)[:120]

                if ferr == "not found":
                    # 列表里有但 CDN 拉不到：按无内容处理，交给文件名/缓存判定，
                    # 不缓存为 error，避免永久卡死
                    verdict = is_aigc_daily_post(name, "", verbose=verbose)
                    update_cache_entry(cache, p, f.get("sha", ""),
                                       "match" if verdict else "nomatch")
                    verdicts[p] = verdict
                elif ferr:
                    stats["errors"] += 1
                    update_cache_entry(cache, p, f.get("sha", ""), "error")
                    if verbose:
                        print(f"  [WARN] 拉取失败 {name}: {ferr}")
                else:
                    verdict = is_aigc_daily_post(name, content or "", verbose=verbose)
                    update_cache_entry(cache, p, f.get("sha", ""),
                                       "match" if verdict else "nomatch")
                    verdicts[p] = verdict

                stats["fetched"] += 1
                processed += 1
                if processed % 250 == 0:
                    print(f"  进度: {processed}/{len(need_fetch)} 已检查 "
                          f"（累计缓存 {len(cache)} 条，@{now_stamp} 起）")
                    save_scan_memory(cache)

                # 时间预算保护：超限即保存断点退出（退出码 2），续扫交给下次运行
                if time.monotonic() > deadline:
                    incomplete = True
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
        if processed % 250 != 0:
            print(f"  进度: {processed}/{len(need_fetch)} 已检查完成")

    return {
        "verdicts": verdicts,
        "fetched": stats["fetched"],
        "cache_hits": stats["cache_hits"],
        "errors": stats["errors"],
        "incomplete": incomplete,
    }


def main():
    parser = argparse.ArgumentParser(
        description="清理主博客 lishuhang.github.io 中误同步的 AIGC 早报内容"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅列出待删除文件，不实际删除"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="详细日志"
    )
    parser.add_argument(
        "--no-batch", action="store_true",
        help="每个文件单独 commit（兼容性更好但更慢）"
    )
    parser.add_argument(
        "--refresh", action="store_true",
        help="忽略增量缓存，强制全量重扫"
    )
    parser.add_argument(
        "--workers", type=int, default=16,
        help="raw CDN 并行拉取线程数（默认 16）"
    )
    parser.add_argument(
        "--time-budget", type=float, default=900.0,
        help="内容扫描时间预算秒数，超时保存断点并以退出码 2 结束（默认 900）"
    )
    args = parser.parse_args()

    load_env()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("[ERROR] 未设置 GITHUB_TOKEN 环境变量")
        print("  请在 .env 文件中配置：GITHUB_TOKEN=ghp_xxxxx")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"AIGC 早报清理脚本 (v2.0 快速扫描) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标仓库: {BLOG_REPO}")
    print(f"目标路径: {BLOG_REPO_POSTS_PATH}/")
    print(f"模式: {'DRY-RUN (仅列出)' if args.dry_run else '实际删除'}")
    print(f"{'=' * 60}\n")

    # 0. 自动探测分支
    print("[0/3] 探测仓库默认分支...")
    branch, err = detect_branch(token)
    if err:
        print(f"[ERROR] 探测分支失败: {err}")
        sys.exit(1)
    print(f"  检测到分支: {branch}")

    # 1. 列出所有 .md 文件（trees API 一次拿全量，失败回退旧分页）
    print(f"\n[1/3] 列出 _posts/ 目录下所有 .md 文件 (branch: {branch})...")
    files, err = list_posts_trees(token, branch)
    listing_source = "git trees API"
    if err:
        print(f"  [WARN] trees API 失败（{err}），回退 Contents 分页列表（可能不完整）")
        files, err = list_posts(token, branch, verbose=args.verbose)
        listing_source = "contents 分页（回退，可能不完整）"
        if err:
            print(f"[ERROR] 列出文件失败: {err}")
            sys.exit(1)
    print(f"  共 {len(files)} 个 .md 文件（来源: {listing_source}）")

    md_files = [f for f in files if f.get("name", "").endswith(".md")]

    # 2. 按 sha 增量检查内容
    print(f"\n[2/3] 增量检查文件内容是否为 AIGC 早报...")
    cache = {} if args.refresh else load_scan_memory()

    # 清理已不存在文件的缓存条目
    if cache:
        alive_paths = {f.get("path", "") for f in md_files}
        stale = [p for p in cache if p not in alive_paths]
        for p in stale:
            cache.pop(p, None)
        if stale:
            print(f"  缓存修剪: 移除 {len(stale)} 个已不存在文件的条目")

    result = scan_contents(
        md_files, branch, token, cache,
        workers=args.workers, time_budget=args.time_budget,
        verbose=args.verbose, refresh=args.refresh,
    )
    save_scan_memory(cache)

    to_delete = []
    skipped = []
    weak_candidates = []
    for f in md_files:
        name = f.get("name", "")
        p = f.get("path", "")
        verdict = result["verdicts"].get(p)
        if verdict is None:
            skipped.append((name, "未检查（预算中断或拉取失败，下次续扫）"))
            continue
        if verdict:
            to_delete.append(f)
            print(f"  [MATCH] {name} → 待删除")
        elif weak_filename_candidate(name):
            weak_candidates.append(name)

    print(f"\n  匹配 AIGC 早报: {len(to_delete)} 个")
    print(f"  跳过: {len(skipped)} 个")
    print(f"  扫描统计: 共 {len(md_files)} 个，缓存命中 {result['cache_hits']}，"
          f"本次拉取 {result['fetched']}，失败 {result['errors']}")
    if weak_candidates:
        print(f"  [提示] {len(weak_candidates)} 个文件名含 aigc/早报 但内容不匹配，"
              f"按 v2.0 语义不删除（v1.9 会误删）:")
        for name in weak_candidates[:10]:
            print(f"    - {name}")
        if len(weak_candidates) > 10:
            print(f"    ... 等共 {len(weak_candidates)} 个")

    if result["incomplete"]:
        print(f"\n[WARN] 时间预算 {args.time_budget:.0f} 秒内未完成全部内容检查")
        print(f"[WARN] 进度已缓存至 {os.path.basename(SCAN_MEMORY_PATH)}，"
              f"下次运行将从断点续扫（疑似早报文件名已优先检查）")
        sys.exit(2)

    if not to_delete:
        print("\n[OK] 没有需要清理的 AIGC 早报文件")
        sys.exit(0)

    # 3. 删除文件
    print(f"\n[3/3] {'列出待删除文件' if args.dry_run else '删除文件'}...")
    if args.dry_run:
        for i, f in enumerate(to_delete, 1):
            print(f"  [{i}/{len(to_delete)}] [DRY-RUN] 将删除: {f.get('path', '')}")
        success_count = len(to_delete)
        fail_count = 0
    else:
        reason = "v2.0 cleanup: 移除误同步的 AIGC 早报"
        success_count, fail_count, _ = delete_files_batch(
            to_delete, token, branch, reason=reason
        )

    # 汇总
    print(f"\n{'=' * 60}")
    print(f"清理完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"成功: {success_count} / 失败: {fail_count}")
    if args.dry_run:
        print("(DRY-RUN 模式，未实际删除)")
    else:
        print(f"已从 {BLOG_REPO} 的 {BLOG_REPO_POSTS_PATH}/ 移除 AIGC 早报内容")
        print(f"AIGC 早报今后仅在 lishuhang.me/daily/ 显示")
    print(f"{'=' * 60}\n")

    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
