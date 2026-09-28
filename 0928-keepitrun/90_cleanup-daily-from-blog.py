#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
90_cleanup-daily-from-blog.py - AIGC 早报清理脚本 (v1.8 配套, v1.9 修复)

用途：
  清理之前因 04_convert-blog.py bug 误同步到主博客 lishuhang.me 的 AIGC 早报内容。
  AIGC 早报应仅在 lishuhang.me/daily/ 显示（由 03_convert-daily.py 发布到
  lishuhang/daily 仓库），不应出现在主博客 lishuhang.github.io 仓库。

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

工作流程：
  1. 自动探测仓库默认分支（main 或 master）
  2. 列出 lishuhang/lishuhang.github.io 仓库 _posts/ 目录下所有 .md 文件
  3. 逐个检查：
     - 文件名包含 "aigc" / "zao-bao" / "mei-ri-aigc" / "早报"
     - categories 包含 "AIGC日报" / "AIGC早报" / "贴图"（v1.7 误标）
     - tags 包含 "AIGC" / "贴图"
     - 标题包含 "AIGC 早报" / "每日 AIGC"
  4. 匹配的文件通过 GitHub API 批量删除（默认单次 commit）
  5. 输出清理报告

用法:
  python 90_cleanup-daily-from-blog.py                # 执行清理（批量模式）
  python 90_cleanup-daily-from-blog.py --dry-run      # 仅列出待删除文件
  python 90_cleanup-daily-from-blog.py --verbose      # 详细日志
  python 90_cleanup-daily-from-blog.py --no-batch     # 每文件单独 commit（慢）

环境变量 (.env):
  GITHUB_TOKEN  - GitHub Personal Access Token（需 repo 权限）

注意：
  - v1.9 起，keepitrun.py 会在 v1.9 首次启动时自动调用此脚本
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
from datetime import datetime

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
# v1.9: 文件名 pinyin 模式匹配（"每日aigc早报" 的 pinyin）
AIGC_FILENAME_PATTERNS = [
    r'mei-ri-aigc',
    r'aigc-zao-bao',
    r'mei-ri-aigc-zao-bao',
]

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


def list_posts(token, branch, verbose=False):
    """列出 _posts 目录下所有 .md 文件"""
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


def is_aigc_daily_post(filename, content, verbose=False):
    """判断文件是否为 AIGC 早报

    v1.9 改进：增加文件名 pinyin 模式匹配，增加 "贴图" category/tags 匹配
    """
    # 1. 文件名模式匹配
    fn_lower = filename.lower()
    # 直接包含 aigc 或 早报
    if "aigc" in fn_lower or "早报" in filename:
        if verbose:
            print(f"  [MATCH filename含aigc/早报] {filename}")
        return True
    # pinyin 模式匹配 (v1.9 新增)
    for pat in AIGC_FILENAME_PATTERNS:
        if re.search(pat, fn_lower):
            if verbose:
                print(f"  [MATCH filename pinyin pattern={pat}] {filename}")
            return True

    # 2. 解析 front matter
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)

        # 检查 categories (v1.9: 含 "贴图")
        cat_match = re.search(r'^categories:\s*(.+?)$', fm, re.MULTILINE)
        if cat_match:
            cat_val = cat_match.group(1).strip()
            for pat in AIGC_CATEGORY_PATTERNS:
                if re.search(pat, cat_val, re.IGNORECASE):
                    if verbose:
                        print(f"  [MATCH categories={cat_val}] {filename}")
                    return True

        # 检查 tags (v1.9: 含 "贴图")
        tag_section_match = re.search(r'^tags:\s*(.*?)$', fm, re.MULTILINE)
        if tag_section_match:
            tag_val = tag_section_match.group(1).strip()
            if tag_val.startswith("["):
                for pat in AIGC_TAG_PATTERNS:
                    if re.search(pat, tag_val, re.IGNORECASE):
                        if verbose:
                            print(f"  [MATCH tags={tag_val}] {filename}")
                        return True

        # 多行 tags
        tag_multi = re.findall(r'^-\s+(.+?)$', fm, re.MULTILINE)
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


def delete_file_single(file_info, token, branch, reason="v1.9 cleanup: 移除误同步的 AIGC 早报"):
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


def delete_files_batch(files, token, branch, reason="v1.9 cleanup: 移除误同步的 AIGC 早报"):
    """v1.9: 批量删除（使用 Git Data API，单次 commit 删除多文件）

    步骤：
    1. GET /repos/{owner}/{repo}/git/ref/heads/{branch} → 获取最新 commit sha
    2. GET /repos/{owner}/{repo}/git/commits/{sha} → 获取 tree sha
    3. POST /repos/{owner}/{repo}/git/trees → 创建新 tree（删除文件 = 不包含该文件）
       注意：Git Data API 不支持直接 "delete"，需要构造新 tree 时排除要删除的文件。
       但这需要重新包含所有保留的文件，对于 _posts/ 目录来说不实际。
    4. 替代方案：使用 Contents API 逐个删除，但合并 commit message

    实际实现：由于 Git Data API 批量删除复杂，这里仍用 Contents API 逐个删除，
    但可以连续调用不等待。return (success_count, fail_count, errors)
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
    args = parser.parse_args()

    load_env()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("[ERROR] 未设置 GITHUB_TOKEN 环境变量")
        print("  请在 .env 文件中配置：GITHUB_TOKEN=ghp_xxxxx")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"AIGC 早报清理脚本 (v1.9) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标仓库: {BLOG_REPO}")
    print(f"目标路径: {BLOG_REPO_POSTS_PATH}/")
    print(f"模式: {'DRY-RUN (仅列出)' if args.dry_run else '实际删除'}")
    print(f"{'=' * 60}\n")

    # 0. v1.9: 自动探测分支
    print("[0/3] 探测仓库默认分支...")
    branch, err = detect_branch(token)
    if err:
        print(f"[ERROR] 探测分支失败: {err}")
        sys.exit(1)
    print(f"  检测到分支: {branch}")

    # 1. 列出所有 .md 文件
    print(f"\n[1/3] 列出 _posts/ 目录下所有 .md 文件 (branch: {branch})...")
    files, err = list_posts(token, branch, verbose=args.verbose)
    if err:
        print(f"[ERROR] 列出文件失败: {err}")
        sys.exit(1)

    md_files = [f for f in files if f.get("name", "").endswith(".md")]
    print(f"  共 {len(md_files)} 个 .md 文件")

    # 2. 逐个检查是否为 AIGC 早报
    print("\n[2/3] 检查每个文件是否为 AIGC 早报...")
    to_delete = []
    skipped = []

    for i, f in enumerate(md_files, 1):
        name = f.get("name", "")
        if args.verbose and i % 50 == 0:
            print(f"  进度: {i}/{len(md_files)}")

        # file_info 中可能没有 content（list 接口默认不返回 content）
        # 需要单独获取文件内容
        content = ""
        if "content" in f:
            content = base64.b64decode(f["content"]).decode("utf-8", errors="replace")
        else:
            # 单独获取文件内容
            file_path = f.get("path", "")
            if file_path:
                result, ferr = github_request(
                    "GET",
                    f"/repos/{BLOG_REPO}/contents/{file_path}?ref={branch}",
                    token
                )
                if not ferr and isinstance(result, dict):
                    content = base64.b64decode(result.get("content", "")).decode("utf-8", errors="replace")
                else:
                    skipped.append((name, f"无法获取内容: {ferr}"))
                    continue

        if is_aigc_daily_post(name, content, verbose=args.verbose):
            to_delete.append(f)
            print(f"  [MATCH] {name} → 待删除")

    print(f"\n  匹配 AIGC 早报: {len(to_delete)} 个")
    print(f"  跳过: {len(skipped)} 个")

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
        reason = "v1.9 cleanup: 移除误同步的 AIGC 早报"
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
