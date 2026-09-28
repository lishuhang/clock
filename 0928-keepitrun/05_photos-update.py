#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05_photos-update.py — 按 lishuhang/photos _config.yml 同步图片库到 Photos 网站

v1.21：每个待同步月份先读取 photos 的 image_prefixes，再选择对应图片仓库、分支与公开 URL；不再固定为单一图床。

v1.4 修复 (2026-06-12):
  - 添加 Windows 控制台 UTF-8 编码修复，解决 emoji 输出导致的 UnicodeEncodeError
  - 在所有 print() 调用前强制 stdout/stderr 编码为 UTF-8

用法：
    python 05_photos-update.py                          # 自动检测模式
    python 05_photos-update.py date:202312,202504       # 强制更新指定月份
    python 05_photos-update.py date:201608              # 强制更新单个月份

自动检测模式逻辑：
    1. 检查 lishuhang/photos 仓库 data/ 目录中最新的 JSON 月份
    2. 从该月（含）检查至当前月份；每月均按 _config.yml 选择图片仓库
    3. 如有新内容，生成/更新对应月份的 JSON 并推送到 lishuhang/photos

指定月份模式逻辑：
    无条件按 _config.yml 重新检查指定月份对应的图片仓库，并在内容变化时更新 JSON

环境变量：
    GITHUB_TOKEN — 在 .env 文件中配置，需要对 lishuhang/photos 及配置指定图片仓库有读取权限
"""

import os
import sys
import re
import json
import base64
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import requests

from image_routing import ImageRouteError, load_upload_route, public_image_base_url

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

# ─── 配置 ─────────────────────────────────────────────
PHOTOS_REPO = "lishuhang/photos"  # 照片网站仓库，也是图床路由配置来源
PHOTOS_BRANCH = "main"
DATA_PATH = "data"                # JSON 存放路径（相对于仓库根目录）
API_BASE = "https://api.github.com"

# ─── 加载 .env ──────────────────────────────────────────
def load_env():
    """从脚本同级 .env 文件加载环境变量"""
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

load_env()
TOKEN = os.environ.get("GITHUB_TOKEN", "")

if not TOKEN:
    print("错误: 未找到 GITHUB_TOKEN，请在 .env 文件中配置")
    sys.exit(1)

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "photos-update-script"
}


# ─── GitHub API 工具函数 ─────────────────────────────────

def api_get(url, params=None, allow_not_found=False):
    """发送 GET 请求到 GitHub API，带速率限制和认证错误处理"""
    resp = requests.get(url, headers=HEADERS, params=params)
    if allow_not_found and resp.status_code == 404:
        return []
    if resp.status_code == 401:
        print("\n❌ GitHub 认证失败 (401 Unauthorized)")
        print("  GITHUB_TOKEN 无效或已过期，请检查:")
        print("  1. 访问 https://github.com/settings/tokens 确认 Token 状态")
        print("  2. 检查 .env 文件中的 GITHUB_TOKEN 是否正确")
        print("  3. 确认 Token 有 repo 权限")
        sys.exit(1)
    if resp.status_code == 403:
        # 速率限制，等待后重试
        reset_time = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
        wait_seconds = max(reset_time - int(time.time()), 5) + 2
        print(f"  ⏳ API 速率限制，等待 {wait_seconds} 秒...")
        time.sleep(wait_seconds)
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code == 401:
            print("\n❌ GitHub 认证失败 (401 Unauthorized)")
            print("  请检查 .env 文件中的 GITHUB_TOKEN")
            sys.exit(1)
    resp.raise_for_status()
    return resp.json()


def api_put(url, data):
    """发送 PUT 请求到 GitHub API"""
    resp = requests.put(url, headers=HEADERS, json=data)
    if resp.status_code == 409:
        # Conflict - SHA 不匹配，需要重新获取
        return None
    resp.raise_for_status()
    return resp.json()


def list_dir(repo, path="", branch=None):
    """列出指定分支目录下的子目录名。"""
    url = f"{API_BASE}/repos/{repo}/contents/{path}"
    items = api_get(url, params={"ref": branch} if branch else None, allow_not_found=True)
    if isinstance(items, dict) and items.get("message"):
        return []
    return [item["name"] for item in items if item["type"] == "dir"]


def list_files(repo, path, branch=None):
    """列出指定分支目录下的文件名。"""
    url = f"{API_BASE}/repos/{repo}/contents/{path}"
    items = api_get(url, params={"ref": branch} if branch else None, allow_not_found=True)
    if isinstance(items, dict) and items.get("message"):
        return []
    return [item["name"] for item in items if item["type"] == "file"]


def get_file_info(repo, path, branch=None):
    """读取 Contents API 文件元数据；不存在时返回 None。"""
    url = f"{API_BASE}/repos/{repo}/contents/{path}"
    resp = requests.get(
        url, headers=HEADERS, params={"ref": branch} if branch else None,
        timeout=30,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def get_image_route(year, month):
    """从 photos _config.yml 读取当前月份应扫描和展示的图床。"""
    post_date = f"{year}-{month}-01"

    def _get(owner, repo, path, branch=None):
        return get_file_info(f"{owner}/{repo}", path, branch)

    return load_upload_route(_get, PHOTOS_REPO, PHOTOS_BRANCH, post_date)


def get_file_json(repo, path):
    """获取仓库中 JSON 文件的内容（解析为 dict），文件不存在时返回 (None, None)"""
    url = f"{API_BASE}/repos/{repo}/contents/{path}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 404:
        return None, None
    resp.raise_for_status()
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    sha = data["sha"]
    return json.loads(content), sha


def upload_file(repo, path, content_str, sha=None, message=""):
    """
    上传或更新仓库中的文件
    content_str: 文件内容字符串
    sha: 如果是更新已有文件，需要提供原文件的 SHA
    """
    url = f"{API_BASE}/repos/{repo}/contents/{path}"
    encoded_content = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

    data = {
        "message": message or f"Update {path}",
        "content": encoded_content,
    }
    if sha:
        data["sha"] = sha

    result = api_put(url, data)
    return result


# ─── 核心逻辑 ────────────────────────────────────────────

def get_photos_repo_latest_month():
    """
    获取 lishuhang/photos 仓库中 data/ 目录下的最新月份
    返回 "yyyymm" 格式字符串，如果没有则返回 None
    """
    url = f"{API_BASE}/repos/{PHOTOS_REPO}/contents/{DATA_PATH}"
    items = api_get(url)
    if isinstance(items, dict) and items.get("message"):
        return None

    json_files = [
        item["name"] for item in items
        if item["type"] == "file" and item["name"].endswith(".json")
    ]
    if not json_files:
        return None

    # 提取 yyyymm 部分并排序
    months = []
    for f in json_files:
        match = re.match(r"^(\d{6})\.json$", f)
        if match:
            months.append(match.group(1))

    return max(months) if months else None


def scan_month_from_img(year, month, image_route):
    """扫描配置为该月份图床的所有图片文件，按日期分组返回。"""
    image_repo = image_route["repository"]
    image_branch = image_route["branch"]
    path = f"{year}/{month}"
    days = list_dir(image_repo, path, branch=image_branch)
    if not days:
        return None

    # 过滤有效的日期目录
    days = sorted([d for d in days if re.match(r"^\d{2}$", d)])

    if not days:
        return None

    photos = {}
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    for day in days:
        day_path = f"{path}/{day}"
        files = list_files(image_repo, day_path, branch=image_branch)
        # 过滤图片文件
        image_files = sorted([
            f for f in files
            if Path(f).suffix.lower() in image_extensions
        ])
        if image_files:
            photos[day] = image_files

    return photos if photos else None


def generate_json(year, month, photos, image_route):
    """生成与 photos 页面兼容、且明确记录图床来源的月度 JSON。"""
    json_data = {
        "user_id": image_route["repository"].split("/", 1)[0],
        "year": year,
        "month": month,
        "base_url": public_image_base_url(image_route),
        "source_repository": image_route["repository"],
        "source_branch": image_route["branch"],
        "photos": photos,
    }
    return json_data


def update_month_json(year, month):
    """
    检查并更新指定月份的 JSON 文件
    返回 True 如果有更新，False 如果无需更新
    """
    yyyymm = f"{year}{month}"
    json_filename = f"{yyyymm}.json"
    json_path = f"{DATA_PATH}/{json_filename}"

    print(f"\n{'='*60}")
    print(f"📅 检查 {year}-{month}")

    # 1. 读取 photos 配置，并扫描该月份对应的图片仓库。
    try:
        image_route = get_image_route(year, month)
    except ImageRouteError as e:
        print(f"  ❌ 无法从 {PHOTOS_REPO}/_config.yml 确定图床：{e}")
        return False

    print(
        f"  🔍 扫描 {image_route['repository']}@{image_route['branch']} "
        f"的 {year}/{month} 目录..."
    )
    photos = scan_month_from_img(year, month, image_route)

    if photos is None:
        print(f"  ⚠️ 图片仓库中不存在 {year}/{month}，跳过")
        return False

    total_photos = sum(len(v) for v in photos.values())
    print(f"  📷 发现 {len(photos)} 天，共 {total_photos} 张图片")

    # 2. 生成新的 JSON
    new_json = generate_json(year, month, photos, image_route)
    new_json_str = json.dumps(new_json, indent=2, ensure_ascii=False)

    # 3. 获取现有 JSON（如果存在）
    existing_json, existing_sha = get_file_json(PHOTOS_REPO, json_path)

    if existing_json is not None:
        # 比较内容是否一致
        existing_json_str = json.dumps(existing_json, indent=2, ensure_ascii=False)
        if existing_json_str == new_json_str:
            print(f"  ✅ JSON 内容一致，无需更新")
            return False
        print(f"  📝 检测到差异，将覆盖更新")
    else:
        print(f"  🆕 JSON 文件不存在，将创建新文件")

    # 4. 上传/更新 JSON
    print(f"  ⬆️ 上传 {json_filename}...")
    try:
        result = upload_file(
            PHOTOS_REPO,
            json_path,
            new_json_str,
            sha=existing_sha,
            message=f"Update {json_filename} ({total_photos} photos, {len(photos)} days)"
        )
        if result:
            print(f"  ✅ {json_filename} 已更新并推送到 GitHub")
            return True
        else:
            print(f"  ❌ 上传失败（可能 SHA 冲突，请重试）")
            return False
    except Exception as e:
        print(f"  ❌ 上传失败: {e}")
        return False


def parse_date_arg(arg):
    """
    解析 date: 参数，返回月份列表 ["yyyymm", ...]
    支持: date:202312,202504 或 date:201608
    也支持范围: date:202312-202504
    """
    if not arg.startswith("date:"):
        return None

    date_str = arg[5:]
    months = []

    for part in date_str.split(","):
        part = part.strip()
        if "-" in part and len(part.split("-")) == 2:
            # 范围模式: 202312-202504
            start, end = part.split("-")
            if len(start) == 6 and len(end) == 6:
                start_y, start_m = int(start[:4]), int(start[4:6])
                end_y, end_m = int(end[:4]), int(end[4:6])
                current_y, current_m = start_y, start_m
                while (current_y, current_m) <= (end_y, end_m):
                    months.append(f"{current_y:04d}{current_m:02d}")
                    current_m += 1
                    if current_m > 12:
                        current_m = 1
                        current_y += 1
        elif len(part) == 6 and part.isdigit():
            months.append(part)
        else:
            print(f"⚠️ 无法解析的月份格式: {part}")

    return months if months else None


def auto_detect_and_update():
    """按配置规则检查最近月度 JSON 与当前月份之间的全部月份。

    每个月在扫描前都会重新读取 photos 的 _config.yml，因此日期跨越图床
    切换边界时会自动从旧仓库切到新仓库。最新已有月份也会重扫，以捕获
    月内新增照片，避免无效提交由 JSON 内容比较负责抑制。
    """
    now = datetime.now()
    current_yyyymm = f"{now.year:04d}{now.month:02d}"

    print(f"🕐 当前时间: {now.strftime('%Y-%m-%d')}")
    print(f"📁 检查 {PHOTOS_REPO} 最新月份...")
    latest_photos_month = get_photos_repo_latest_month()
    if latest_photos_month:
        print(f"  最新 JSON 月份: {latest_photos_month}")
        start_month = latest_photos_month
    else:
        # 新站点才需要从历史起点补齐；现有站点通常不会走到此分支。
        start_month = "200701"
        print(f"  未找到任何 JSON 文件，将自 {start_month} 开始检查")

    if start_month > current_yyyymm:
        print("  最新 JSON 月份晚于当前月份，仅检查当前月份")
        start_month = current_yyyymm

    print(f"\n🔄 按图床配置检查 {start_month} 至 {current_yyyymm}")
    updated_any = False
    current_y, current_m = int(start_month[:4]), int(start_month[4:6])
    end_y, end_m = int(current_yyyymm[:4]), int(current_yyyymm[4:6])

    while (current_y, current_m) <= (end_y, end_m):
        year = f"{current_y:04d}"
        month = f"{current_m:02d}"
        if update_month_json(year, month):
            updated_any = True
        current_m += 1
        if current_m > 12:
            current_m = 1
            current_y += 1

    if not updated_any:
        print(f"\n✨ 一切已是最新，无需更新")



def force_update_months(months):
    """
    强制更新指定月份的 JSON
    months: ["yyyymm", ...] 列表
    """
    updated_any = False

    for yyyymm in months:
        year = yyyymm[:4]
        month = yyyymm[4:6]
        if update_month_json(year, month):
            updated_any = True

    if not updated_any:
        print(f"\n✨ 指定月份均无需更新")


# ─── 主入口 ──────────────────────────────────────────────

def main():
    print("=" * 60)
    print("📸 Photos Update — 图片库自动同步工具")
    print("=" * 60)

    if len(sys.argv) > 1:
        # 指定月份模式
        arg = sys.argv[1]
        months = parse_date_arg(arg)

        if months is None:
            print(f"❌ 无法解析参数: {arg}")
            print()
            print("用法:")
            print("  python 05_photos-update.py                          # 自动检测")
            print('  python 05_photos-update.py date:202312,202504       # 指定月份')
            print('  python 05_photos-update.py date:201608              # 单个月份')
            print('  python 05_photos-update.py date:202301-202306       # 范围')
            sys.exit(1)

        print(f"🎯 强制更新模式，目标月份: {', '.join(months)}")
        force_update_months(months)
    else:
        # 自动检测模式
        print("🔍 自动检测模式")
        auto_detect_and_update()

    print()


if __name__ == "__main__":
    main()
