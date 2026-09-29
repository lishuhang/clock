#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
keepitrun - 定时任务调度脚本 (Windows 11 / 跨平台常驻)
版本: 1.28 (2026-09-29)
基于: keepitrun-260424.py (v1.0)

每日定时任务（GMT+8）:
  02:00  01_getrss.py 抓取第 1 次 RSS
  10:05  03_convert-daily.py 抓取 AIGC 早报
  10:10  04_convert-blog.py 抓取博客文章
  14:00  01_getrss.py 抓取第 2 次 RSS
  14:05  02_combine-gemini.py 合并、去重并翻译 RSS
  15:00  05_photos-update.py 自动同步（脚本存在时启用）

v1.28 变更:
  - blog 同步改纯增量：04 新增 URL 级已同步记忆（blog_sync_memory.json），
    同步过一次的文章永远不再抓取处理；调度侧合集窗口封顶 30 天
    （last_blog_crawl 过旧/新电脑冷启动时只回溯最近 30 天，历史全量永不重跑）。
  - blog 发布日期以正文标注「文/书航 yyyy.mm.dd」为准（转载稿公众号
    时间戳晚于实际首发）；正则放宽到无空格与一位数月/日。
  - 04 每篇同步文章自动追加 featured 标签（首页大图滚动区域数据源）。
  - 03 同日早报首同步版本为准：同日期重发（可能因审查删改）不覆盖已同步版本。
  - 03 题图 1:1 比例校正：非 1:1（如 2:3）按原始分辨率中心裁切为 1:1，
    避免展示端再缩放裁切导致整体比原图小一圈。

v1.27 变更:
  - 冷启动提速：90_cleanup 从「逐文件 API 拉全文」重建为 Git Trees 一次列全量
    + raw CDN 并行拉取 + sha 增量缓存（cleanup_scan_memory.json）+ 内部时间预算
    （超时存断点、退出码 2、续扫不重头）。0928 生产日志中该任务三连 1800s 超时
    拖慢冷启动约 90 分钟且从未完成过；修复后首扫约 1 分钟，日常首次启动秒级。
  - 判定语义修正：裸 "aigc"/"早报" 文件名不再不经内容确认即判删（避免误删
    正经 AIGC 主题文章）；判定 = front matter 内容匹配或无歧义拼音组合文件名。

v1.26 变更:
  - 同日版本替换后首次运行只执行今天尚未完成的任务：版本升级不再触发
    当日已完成任务重做（移除 VERSION_TASK_CHANGES 重做机制）；
    task_completion.json 继续记录完成版本，仅作审计与跳过判断。
  - LLM 免费档模型升级（依据官方定价文档）：
    · 02/92 Gemini gemini-2.5-flash → gemini-3.8-flash（Free of charge 档）
    · 02/92 GLM glm-4-flash → glm-4.7-flash（输入/输出均免费档，200K 上下文）

v1.25 变更:
  - 02 新增 24 小时已提取记忆（rss_issue_memory.json）：摘要发出后即使被取走，
    过去 24 小时内出现过的条目也不会再次进入新摘要。
  - 移除 piczip/oxipng.exe：03/04/91 的 PNG 压缩改用 Pillow 无损优化，
    全流程纯 Python（Pillow 已是既有依赖），后缀名转换规则不变。

v1.24 变更:
  - 子脚本 stdout/stderr 实时写入主控制台与总日志，便于定位 02 翻译超时点。
  - RSS 抓取阶段只还原、规范化 URL；跨批次去重统一由 02 合并器完成。
  - Photos 将尚不存在的月份目录视为空目录，且失败时不再误记为今日已完成。

v1.23 变更:
  - Techmeme RSS 优先从条目摘要提取原始报道 URL，避免聚合页被部分 IP 阻断时无法还原。
  - 修复图片维护工具在 Windows 上找不到内置 oxipng，并以 Pillow 补足 JPEG/GIF 压缩。

v1.22 变更:
  - 修复博客图片压缩时 PNG/JPG 扩展名转换未回写正文与题图 URL 的问题；上传路径、正文 Markdown 和 front matter 现保持一致。

v1.20 变更:
  - 后台 daily/blog 子任务使用无交互模式；调度器关闭未提供输入的子进程标准输入。
  - daily 以远程已发布日期集合做差集判定，避免同日内容重复抓取与覆盖提示阻塞。

v1.19 变更:
  - 移除 Unsplash 与马良注册的自动任务及其发行包脚本。
  - 依照实际任务顺序为活动脚本添加两位序号；90+ 留给手动维护工具。

v1.11 变更 (2026-07-05) — 图片存储架构重构:
  - 04_convert-blog.py / 03_convert-daily.py: 图片 URL 改为相对路径 /img/...
    · 文章 front matter image 和正文 ![](/img/...) 均使用相对路径
    · 由 lishuhang.github.io/_plugins/image_prefix.rb 在构建时解析
    · _config.yml 新增 image_prefixes 配置，支持按日期范围使用不同存储
      (前缀 A/B/C 分别对应不同时间段，便于日后迁移到 R2/其他仓库)
  - 新增 91_compress-images.py CLI: 无损图片压缩
    · PNG: oxipng -o 4 (无损)
    · JPEG: jpegoptim --max=90 (近无损)
    · GIF: gifsicle -O3 (无损)
    · 典型节省 15-40%，零可见质量损失
  - 04_convert-blog.py / 03_convert-daily.py: 上传前自动压缩图片
    · 新增 compress_image_local() / compress_image_file()
    · 工具不可用时静默跳过
  - lishuhang/img 仓库: 新增 .github/workflows/compress-images.yml
    · 自动压缩新增图片 (push 触发)
    · 手动触发可指定 min_size 和 year_filter
  - lishuhang.github.io 仓库: 新增 _plugins/image_prefix.rb
    · Jekyll Generator，按 post.date 解析 /img/ → 完整 URL
  - 已完成: 921 篇现有文章的 lishuhang.me/img/ → /img/ 替换 (3427 处)
  - 备份: lishuhang/photos/0704_blog_backup/0704_blog_backup.zip

v1.9 变更 (2026-07-03):
  - 修复 04_convert-blog.py 部分微信文章正文无法提取的 bug (升级至 v3.2)
    · 原因：部分微信文章正文在 <section> 标签内而非 <p>，
      detect_article_type 因 heading_count=0 误判为短文，
      convert_short_article 的 <p> 遍历也找不到内容
    · 表现：发布到主博客的文章只有 front matter 和图片，正文缺失
      （如 2026-06-25-zhong-guo-ban-mythos-bi-de.md 仅 14 行）
    · 修复：convert_short_article 在 <p> 提取结果过少时回退从叶 <section>
      提取文本；convert_long_article 新增 section 标签到 find_all 列表
  - 修复 90_cleanup-daily-from-blog.py 分支探测 bug (v1.8 硬编码 "master"
    但 lishuhang.github.io 默认分支是 "main"，导致 404 失败)
    · v1.9 改为自动探测分支（先查 default_branch，再试 main/master）
    · 改进匹配逻辑：增加文件名 pinyin 模式 + "贴图" category/tags 匹配
  - keepitrun.py v1.9 首次启动时自动调用 90_cleanup-daily-from-blog.py
    清理之前误同步到主博客的 AIGC 早报内容

v1.6 变更 (2026-06-13):
  - 新增 blog/daily 文章归档机制：GitHub 同步成功后自动将本地 .md 和 images/ 移入 archived/
    · blog 生成的 YYYY-MM-DD-*.md 文件从脚本主目录移入 archived/
    · daily 生成的 _posts/*.md 文件移入 archived/_posts/
    · images/ 整个目录树移入 archived/images/
    · 与 RSS 归档一致，archived/ 中超过 30 天自动清理
  - 修复打包包含 .env 导致用户解压覆盖后 GitHub Token 丢失的问题
    · 发行包不再包含 .env，改为 .env.example 模板

v1.5 变更 (2026-06-12):
  - 修复 05_photos-update.py 401 认证失败时原始 traceback 崩溃，改为友好提示
  - 修复 blog 首次启动默认 album:diff 导致 8 合集全量遍历超时 600s
    · 无爬取记录时默认抓取最近 30 天 (album:YYYYMMDD)，不再用 album:diff
  - album:diff 仍可手动使用，但不作为自动调度默认值

v1.4 变更 (2026-06-12):
  - 修复所有子脚本 Windows 控制台 UnicodeEncodeError (cp1252 无法输出 emoji/中文)
  - 为 05_photos-update.py, 04_convert-blog.py, 03_convert-daily.py, 01_getrss.py 添加 UTF-8 编码修复
  - 05_photos-update.py 现已包含在 keepitrun 发行包中

v1.3 变更 (2026-06-11):
  - 重新启用微信公众号AIGC早报抓取 (10:05)
  - 新增版本感知任务完成追踪系统
    · v1.26 起不再按版本变更重做当日任务，仅保留完成记录用于同日去重
    · 任务完成记录持久化至 logs/task_completion.json
  - 03_convert-daily.py 从 disabled/ 移回主目录

v1.2 变更 (2026-06-11):
  - 重新启用微信公众号文章抓取 (10:10)
  - 使用合集API替代公众平台后台Cookie登录 (04_convert-blog.py v3.0)
  - 无需Cookie即可抓取文章列表

异常处理:
  - 若某次 RSS 抓取因脚本未启动而缺失，14:05 时自动补抓
  - 输出成功后，将之前的 RSS 抓取结果移至 /archived 子文件夹
  - blog/daily 文章同步 GitHub 后，将本地文件移至 /archived 子文件夹

日志与清理:
  - 所有操作记录到 logs/ 子文件夹
  - 临时文件存放于 tmp/ 子文件夹
  - 分级自动清理:
    · tmp/   中超过 1 天的文件 → 自动删除
    · logs/  中超过 7 天的日志 → 移入 logs/archive/
    · logs/archive/ 中超过 30 天的日志 → 自动删除
    · archived/ 中超过 30 天的文件 → 自动删除

用法:
  python keepitrun.py
  (常驻运行，通过 while True 循环每 30 秒检查一次时间)
"""

import time
import re
import subprocess
import os
import sys
import shutil
import glob
import json
import logging
import threading
from datetime import date, datetime, timedelta, timezone

# ================= Windows 编码修复 =================
# Windows 默认控制台编码为 cp1252，无法输出中文等超出 Latin-1 范围的字符
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
# 版本信息
# ═══════════════════════════════════════════════════════════════

VERSION = "1.28"
VERSION_DATE = "2026-09-29"

# ═══════════════════════════════════════════════════════════════
# 配置区域
# ═══════════════════════════════════════════════════════════════

# 脚本所在目录（所有子脚本也在此目录）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 子脚本文件名按日常任务实际顺序编号；名称部分用连字符分词。
RSS_SCRIPT = "01_getrss.py"
COMBINE_SCRIPT = "02_combine-gemini.py"
DAILY_SCRIPT = "03_convert-daily.py"
BLOG_SCRIPT = "04_convert-blog.py"
PHOTOS_SCRIPT_NAME = "05_photos-update.py"

# 手动维护工具不参与每日调度，使用 90+ 序号。
CLEANUP_DAILY_SCRIPT = "90_cleanup-daily-from-blog.py"

# RSS 抓取结果与尚未取走摘要的文件匹配模式。
RSS_FILE_PATTERN = "rss_*.md"
PENDING_SUMMARY_PATTERN = re.compile(r"^\d{8}-\d{6}\.(?:md|py)$")

# 子目录
ARCHIVED_DIR = os.path.join(SCRIPT_DIR, "archived")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
LOG_ARCHIVE_DIR = os.path.join(LOG_DIR, "archive")
TMP_DIR = os.path.join(SCRIPT_DIR, "tmp")

# 清理阈值 (天)
TMP_RETENTION_DAYS = 1       # tmp/ 中文件保留 1 天
LOG_ARCHIVE_DAYS = 7         # logs/ 中文件 7 天后移入 archive
LOG_DELETE_DAYS = 30         # logs/archive/ 中文件 30 天后删除
ARCHIVED_RETENTION_DAYS = 30 # archived/ 中文件保留 30 天

# 上次成功 blog 爬取日期记录文件 (v1.2 重新启用)
BLOG_LAST_CRAWL_FILE = os.path.join(SCRIPT_DIR, "last_blog_crawl.txt")

# v1.28: blog 合集增量窗口封顶天数。同步目的＝「找出最近新增且未同步的文章」
# 并对已同步文章去重，无需遍历历史全量（当前约万篇，随年份增长）；
# last_blog_crawl 过旧（长期停跑/换新电脑）时也只回溯最近 N 天，
# 已同步文章由 04 的 blog_sync_memory.json 记忆跳过。
BLOG_SYNC_WINDOW_DAYS = 30


def resolve_blog_since_date(last_date, today, logger=None, prefix=""):
    """v1.28: 将上次爬取日期收敛到最近 N 天窗口内（N=BLOG_SYNC_WINDOW_DAYS）。

    last_date 距今超过窗口天数时截断为窗口下界，避免合集随年份增长后
    每次增量都从陈旧位置重扫历史。
    """
    try:
        last_dt = datetime.strptime(last_date, "%Y%m%d")
    except (TypeError, ValueError):
        return last_date
    floor_dt = today - timedelta(days=BLOG_SYNC_WINDOW_DAYS)
    if last_dt < floor_dt:
        floor_str = floor_dt.strftime("%Y%m%d")
        if logger:
            logger.info(
                f"{prefix}上次爬取日期 {last_date} 超过 {BLOG_SYNC_WINDOW_DAYS} 天窗口，"
                f"按 {floor_str} 起增量（历史全量不重跑，已同步文章由记忆跳过）")
        return floor_str
    return last_date

# Photos 同步脚本与调度器同目录发布，避免依赖机器特定的绝对路径。


def _resolve_photos_path():
    """返回已编号的本地 Photos 同步脚本路径。"""
    local = os.path.join(SCRIPT_DIR, PHOTOS_SCRIPT_NAME)
    return local if os.path.isfile(local) else ""


PHOTOS_UPDATE_SCRIPT = _resolve_photos_path()

# 每日首次启动标记文件
DAILY_BOOT_FLAG = os.path.join(LOG_DIR, ".boot_flag")

# 调度时钟固定使用 GMT+8，避免宿主系统时区变化造成错过任务。
SCHEDULE_TIMEZONE = timezone(timedelta(hours=8))

# 时间检查间隔（秒）
CHECK_INTERVAL = 30

# 主调度器允许单次子脚本运行的统一上限。所有任务具体时限均不得超过该值。
MAX_SUBPROCESS_TIMEOUT_SECONDS = 3600
SUBPROCESS_ATTEMPTS = 3
SUBPROCESS_RETRY_DELAY_SECONDS = 30

TASK_TIMEOUTS = {
    "rss": 1200,
    "combine": 3600,
    "daily": 1800,
    "blog": 3600,
    "photos": 1800,
    "cleanup": 1800,
}


def schedule_now():
    """返回用于定时判断的当前 GMT+8 时间。"""
    return datetime.now(SCHEDULE_TIMEZONE)


def schedule_today():
    """返回 GMT+8 调度日期。"""
    return schedule_now().date()

# ═══════════════════════════════════════════════════════════════
# 同日任务完成追踪 (v1.26 语义)
# ═══════════════════════════════════════════════════════════════

# v1.26 起：任务今天已完成（无论由哪个版本完成）即不再重复执行。
# 版本替换当日，首次运行新版只执行今天尚未完成的任务，不再按版本变更重做。
# v1.25 及更早的 VERSION_TASK_CHANGES 重做映射已移除；task_completion.json
# 仍记录完成任务时的版本号，用于审计与跳过提示。

TASK_COMPLETION_FILE = os.path.join(LOG_DIR, "task_completion.json")

# 全局日志对象 (由 setup_logging() 初始化)
logger = None


def load_task_completion():
    """从JSON文件加载任务完成记录"""
    if os.path.isfile(TASK_COMPLETION_FILE):
        try:
            with open(TASK_COMPLETION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_task_completion(records):
    """保存任务完成记录到JSON文件"""
    os.makedirs(os.path.dirname(TASK_COMPLETION_FILE), exist_ok=True)
    try:
        with open(TASK_COMPLETION_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except OSError as e:
        if logger:
            logger.error(f"保存任务完成记录失败: {e}")


def record_task_done(task_name):
    """记录任务今日已完成（附带当前版本号，仅作审计用途）"""
    records = load_task_completion()
    today_str = schedule_today().strftime("%Y-%m-%d")
    if task_name not in records:
        records[task_name] = {}
    records[task_name][today_str] = VERSION
    save_task_completion(records)
    if logger:
        logger.debug(f"记录任务完成: {task_name} @ {today_str} (v{VERSION})")


def get_done_version_today(task_name):
    """返回任务今天完成时所用的版本号；今天尚未完成则返回空字符串。"""
    records = load_task_completion()
    today_str = schedule_today().strftime("%Y-%m-%d")
    return str(records.get(task_name, {}).get(today_str) or "")


# ═══════════════════════════════════════════════════════════════
# 日志系统
# ═══════════════════════════════════════════════════════════════

def setup_logging():
    """初始化日志系统：文件+控制台，统一存放于 logs/ 目录"""
    global logger
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(LOG_ARCHIVE_DIR, exist_ok=True)

    log_name = datetime.now().strftime("%Y%m%d") + ".log"
    log_path = os.path.join(LOG_DIR, log_name)

    logger = logging.getLogger("keepitrun")
    # 防止重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 文件 handler（追加模式，同一天同一文件）
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # 控制台 handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def cleanup_tmp(logger):
    """删除 tmp/ 中超过 TMP_RETENTION_DAYS 天的文件

    tmp/ 目录存放 RSS 抓取中间结果等临时文件，
    超过 1 天的文件可安全删除（已被合并或归档）。
    """
    if not os.path.isdir(TMP_DIR):
        return

    cutoff = datetime.now() - timedelta(days=TMP_RETENTION_DAYS)
    deleted = 0

    for f in os.listdir(TMP_DIR):
        filepath = os.path.join(TMP_DIR, f)
        if not os.path.isfile(filepath):
            continue
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
                deleted += 1
        except OSError:
            continue

    if deleted > 0:
        logger.info(f"tmp/ 清理: 删除了 {deleted} 个超过 {TMP_RETENTION_DAYS} 天的临时文件")


def cleanup_logs(logger):
    """分级清理日志:
    1. logs/ 中超过 LOG_ARCHIVE_DAYS 天的日志 → 移入 logs/archive/
    2. logs/archive/ 中超过 LOG_DELETE_DAYS 天的日志 → 删除
    """
    os.makedirs(LOG_ARCHIVE_DIR, exist_ok=True)

    # 阶段1: 移动旧日志到 archive
    if os.path.isdir(LOG_DIR):
        archive_cutoff = datetime.now() - timedelta(days=LOG_ARCHIVE_DAYS)
        moved = 0

        for log_file in glob.glob(os.path.join(LOG_DIR, "*.log")):
            # 跳过 archive 子目录中的文件
            if LOG_ARCHIVE_DIR in log_file:
                continue
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                if mtime < archive_cutoff:
                    dest = os.path.join(LOG_ARCHIVE_DIR, os.path.basename(log_file))
                    # 避免覆盖同名文件
                    if os.path.exists(dest):
                        base, ext = os.path.splitext(os.path.basename(log_file))
                        dest = os.path.join(LOG_ARCHIVE_DIR, f"{base}_{int(time.time())}{ext}")
                    shutil.move(log_file, dest)
                    moved += 1
            except OSError:
                continue

        if moved > 0:
            logger.info(f"日志归档: 移动了 {moved} 个超过 {LOG_ARCHIVE_DAYS} 天的日志到 logs/archive/")

    # 阶段2: 删除过旧的归档日志
    if os.path.isdir(LOG_ARCHIVE_DIR):
        delete_cutoff = datetime.now() - timedelta(days=LOG_DELETE_DAYS)
        deleted = 0

        for log_file in glob.glob(os.path.join(LOG_ARCHIVE_DIR, "*.log")):
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                if mtime < delete_cutoff:
                    os.remove(log_file)
                    deleted += 1
            except OSError:
                continue

        if deleted > 0:
            logger.info(f"日志清理: 删除了 {deleted} 个超过 {LOG_DELETE_DAYS} 天的归档日志")


def cleanup_archived(logger):
    """删除 archived/ 中超过 ARCHIVED_RETENTION_DAYS 天的文件

    v1.6: 支持递归清理子目录（images/、_posts/ 等），
    删除过期文件后自动清理空目录。
    """
    if not os.path.isdir(ARCHIVED_DIR):
        return

    cutoff = datetime.now() - timedelta(days=ARCHIVED_RETENTION_DAYS)
    deleted = 0

    # 递归清理所有子目录中的过期文件
    deleted += cleanup_archived_tree(logger, ARCHIVED_DIR, cutoff)

    if deleted > 0:
        logger.info(f"archived/ 清理: 删除了 {deleted} 个超过 {ARCHIVED_RETENTION_DAYS} 天的归档文件")


def run_all_cleanup(logger):
    """执行全部清理任务"""
    cleanup_tmp(logger)
    cleanup_logs(logger)
    cleanup_archived(logger)


def cleanup_archived_tree(logger, dir_path, cutoff):
    """递归删除目录树中超过 cutoff 的文件，并清理空目录"""
    if not os.path.isdir(dir_path):
        return 0
    deleted = 0
    for root, dirs, files in os.walk(dir_path, topdown=False):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    os.remove(fpath)
                    deleted += 1
            except OSError:
                continue
        # 清理空目录（不删除根目录本身）
        if root != dir_path:
            try:
                if not os.listdir(root):
                    os.rmdir(root)
            except OSError:
                pass
    return deleted


def archive_blog_daily_files(logger):
    """将 blog/daily 脚本生成的本地文件移动到 archived/ 目录

    这些文件已同步到 GitHub，本地副本移至 archived/ 以备后续自动清理。
    与 archive_rss_files() 机制一致，确保脚本主目录不被散放的文章文件污染。

    移动范围:
    1. blog 生成的 YYYY-MM-DD-*.md 文件（排除 RSS 合并输出 YYYYMMDD-HHMMSS.md）
    2. daily 生成的 _posts/ 目录内容
    3. images/ 目录（blog 和 daily 共享的图片本地副本）
    """
    os.makedirs(ARCHIVED_DIR, exist_ok=True)
    moved = 0

    # 1. 移动 blog 生成的 .md 文件（YYYY-MM-DD-*.md，排除 RSS 合并结果）
    for f in glob.glob(os.path.join(SCRIPT_DIR, "????-??-??-*.md")):
        basename = os.path.basename(f)
        # 排除 RSS 合并输出 (格式: YYYYMMDD-HHMMSS.md)
        if re.match(r'\d{8}-\d{6}\.md$', basename):
            continue
        try:
            dest = os.path.join(ARCHIVED_DIR, basename)
            if os.path.exists(dest):
                base, ext = os.path.splitext(basename)
                dest = os.path.join(ARCHIVED_DIR, f"{base}_{int(time.time())}{ext}")
            shutil.move(f, dest)
            moved += 1
        except Exception as e:
            logger.error(f"归档 blog 文件失败 {f}: {e}")

    # 2. 移动 _posts/ 目录内容到 archived/_posts/
    posts_dir = os.path.join(SCRIPT_DIR, "_posts")
    if os.path.isdir(posts_dir):
        archived_posts = os.path.join(ARCHIVED_DIR, "_posts")
        os.makedirs(archived_posts, exist_ok=True)
        for f in glob.glob(os.path.join(posts_dir, "*.md")):
            basename = os.path.basename(f)
            try:
                dest = os.path.join(archived_posts, basename)
                if os.path.exists(dest):
                    base, ext = os.path.splitext(basename)
                    dest = os.path.join(archived_posts, f"{base}_{int(time.time())}{ext}")
                shutil.move(f, dest)
                moved += 1
            except Exception as e:
                logger.error(f"归档 daily 文件失败 {f}: {e}")
        # 如果 _posts/ 目录为空，删除它
        try:
            if not os.listdir(posts_dir):
                os.rmdir(posts_dir)
        except OSError:
            pass

    # 3. 移动 images/ 目录到 archived/images/
    images_dir = os.path.join(SCRIPT_DIR, "images")
    if os.path.isdir(images_dir):
        archived_images = os.path.join(ARCHIVED_DIR, "images")
        if os.path.exists(archived_images):
            # 目标已存在：合并目录（将 images/ 子树合并到 archived/images/）
            try:
                shutil.copytree(images_dir, archived_images, dirs_exist_ok=True)
                shutil.rmtree(images_dir)
                moved += 1
            except Exception as e:
                logger.error(f"合并 images 目录失败: {e}")
        else:
            try:
                shutil.move(images_dir, archived_images)
                moved += 1
            except Exception as e:
                logger.error(f"归档 images 目录失败: {e}")

    if moved > 0:
        logger.info(f"已将 {moved} 个 blog/daily 文件/目录归档到 {ARCHIVED_DIR}")


# ═══════════════════════════════════════════════════════════════
# 子脚本执行
# ═══════════════════════════════════════════════════════════════

def _stream_script_pipe(script_name, pipe, level, chunks, suffix=""):
    """逐行转发子进程输出，并保留 stdout 供需要解析结果的调用方使用。"""
    try:
        for raw_line in iter(pipe.readline, ""):
            chunks.append(raw_line)
            line = raw_line.rstrip("\r\n")
            if line:
                logger.log(level, f"  [{script_name}{suffix}] {line}")
    finally:
        pipe.close()


def run_script(
    script_name,
    args=None,
    timeout=None,
    stdin_input=None,
    attempts=SUBPROCESS_ATTEMPTS,
    cwd=None,
    return_output=False,
):
    """执行子脚本并在超时或非零退出时重试。

    每次实际时限都被限制在 MAX_SUBPROCESS_TIMEOUT_SECONDS 内，避免子脚本
    的预期运行时长超过主调度器允许的上限而被意外终止。未显式提供输入时，
    使用空标准输入，防止后台子脚本等待人工确认而被误判为超时。
    """
    script_path = script_name if os.path.isabs(script_name) else os.path.join(SCRIPT_DIR, script_name)
    if not os.path.isfile(script_path):
        logger.error(f"脚本不存在: {script_path}")
        return False, -1

    effective_timeout = min(timeout or MAX_SUBPROCESS_TIMEOUT_SECONDS, MAX_SUBPROCESS_TIMEOUT_SECONDS)
    effective_attempts = max(1, attempts)
    command = [sys.executable, script_path]
    if args:
        command.extend(args)
    working_directory = cwd or SCRIPT_DIR
    last_returncode = -1
    last_stdout = ""

    for attempt in range(1, effective_attempts + 1):
        logger.info(
            "执行 %s（第 %s/%s 次，单次时限 %s 秒）: %s",
            os.path.basename(script_path), attempt, effective_attempts, effective_timeout, " ".join(command),
        )
        try:
            child_env = os.environ.copy()
            child_env["PYTHONUNBUFFERED"] = "1"
            process = subprocess.Popen(
                command,
                cwd=working_directory,
                stdin=subprocess.PIPE if stdin_input is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=child_env,
            )
            if stdin_input is not None:
                process.stdin.write(stdin_input)
                process.stdin.close()

            stdout_chunks, stderr_chunks = [], []
            script_label = os.path.basename(script_path)
            readers = [
                threading.Thread(
                    target=_stream_script_pipe,
                    args=(script_label, process.stdout, logging.INFO, stdout_chunks),
                    daemon=True,
                ),
                threading.Thread(
                    target=_stream_script_pipe,
                    args=(script_label, process.stderr, logging.WARNING, stderr_chunks, ":stderr"),
                    daemon=True,
                ),
            ]
            for reader in readers:
                reader.start()

            try:
                last_returncode = process.wait(timeout=effective_timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                last_returncode = -1
                logger.error("脚本 %s 在 %s 秒后超时", script_label, effective_timeout)
            finally:
                for reader in readers:
                    reader.join()

            last_stdout = "".join(stdout_chunks)
            if last_returncode == 0:
                return (True, 0, last_stdout) if return_output else (True, 0)
            if last_returncode != -1:
                logger.error("脚本 %s 返回非零退出码: %s", script_label, last_returncode)
        except Exception as exc:
            last_returncode = -1
            logger.error("执行脚本 %s 时发生异常: %s", os.path.basename(script_path), type(exc).__name__)

        if attempt < effective_attempts:
            wait_seconds = SUBPROCESS_RETRY_DELAY_SECONDS * attempt
            logger.warning("%s 将在 %s 秒后重试", os.path.basename(script_path), wait_seconds)
            time.sleep(wait_seconds)

    return (False, last_returncode, last_stdout) if return_output else (False, last_returncode)


# ═══════════════════════════════════════════════════════════════
# RSS 抓取结果管理
# ═══════════════════════════════════════════════════════════════

def get_today_rss_files():
    """获取今天的 RSS 抓取结果文件列表 (从 tmp/ 目录查找)"""
    today = schedule_today().strftime("%Y-%m-%d")
    pattern = os.path.join(TMP_DIR, f"rss_{today}_*.md")
    return sorted(glob.glob(pattern))


def count_today_rss_files():
    """统计今天的 RSS 抓取结果文件数量"""
    return len(get_today_rss_files())


def get_pending_summary_files():
    """返回根目录中尚未被用户取走的日期摘要，兼容历史 `.py` 后缀。"""
    pending = []
    for name in os.listdir(SCRIPT_DIR):
        if PENDING_SUMMARY_PATTERN.fullmatch(name):
            path = os.path.join(SCRIPT_DIR, name)
            if os.path.isfile(path):
                pending.append(path)
    return sorted(pending)


def archive_rss_files(logger):
    """将所有 RSS 抓取结果文件移动到 archived 子文件夹"""
    os.makedirs(ARCHIVED_DIR, exist_ok=True)

    # 同时检查 tmp/ 和根目录（兼容旧版文件）
    rss_files = glob.glob(os.path.join(TMP_DIR, RSS_FILE_PATTERN))
    rss_files += glob.glob(os.path.join(SCRIPT_DIR, RSS_FILE_PATTERN))
    # 去重
    rss_files = list(set(rss_files))
    moved = 0

    for f in rss_files:
        try:
            dest = os.path.join(ARCHIVED_DIR, os.path.basename(f))
            if os.path.exists(dest):
                # 避免覆盖：添加时间戳后缀
                base, ext = os.path.splitext(os.path.basename(f))
                dest = os.path.join(ARCHIVED_DIR, f"{base}_{int(time.time())}{ext}")
            shutil.move(f, dest)
            moved += 1
        except Exception as e:
            logger.error(f"归档文件失败 {f}: {e}")

    if moved > 0:
        logger.info(f"已将 {moved} 个 RSS 抓取结果文件移动到 {ARCHIVED_DIR}")


# ═══════════════════════════════════════════════════════════════
# Photos 自动同步
# ═══════════════════════════════════════════════════════════════

def is_photos_update_enabled():
    """检查 Photos 同步脚本是否存在"""
    exists = os.path.isfile(PHOTOS_UPDATE_SCRIPT)
    if not exists and PHOTOS_UPDATE_SCRIPT:
        logger.debug(f"Photos 同步脚本未找到: {PHOTOS_UPDATE_SCRIPT}")
    return exists


def run_photos_update():
    """运行 Photos 自动同步脚本

    仅当脚本文件存在时才会被调用。
    脚本工作目录设为脚本所在目录，
    以便它找到同目录下的 .env 文件。
    无参数运行 = 自动检测模式（检查图片库是否有新内容需要同步）。
    """
    logger.info("-- 开始运行 Photos 自动同步 --")
    logger.info(f"  脚本路径: {PHOTOS_UPDATE_SCRIPT}")

    photos_dir = os.path.dirname(os.path.abspath(PHOTOS_UPDATE_SCRIPT))

    success, _ = run_script(
        os.path.abspath(PHOTOS_UPDATE_SCRIPT),
        timeout=TASK_TIMEOUTS["photos"],
        cwd=photos_dir,
    )
    if success:
        logger.info("Photos 自动同步完成")
    return success


# ═══════════════════════════════════════════════════════════════
# AIGC 早报清理 (v1.9 新增)
# ═══════════════════════════════════════════════════════════════

def run_cleanup_daily_from_blog():
    """运行 AIGC 早报清理脚本 (每日首次启动维护)

    清理之前因 04_convert-blog.py bug 误同步到主博客 lishuhang.me 的 AIGC 早报内容。
    v2.0 起脚本内部使用 trees API + raw CDN 并行 + sha 增量缓存，首次全量扫描
    约 1 分钟，日常运行秒级；退出码 2 表示预算内未扫完（已存断点），由重试与
    次日运行续扫。
    """
    script_path = os.path.join(SCRIPT_DIR, CLEANUP_DAILY_SCRIPT)
    if not os.path.isfile(script_path):
        logger.info("[cleanup] 清理脚本不存在，跳过")
        return False

    logger.info("-- 开始运行 AIGC 早报清理 (v2.0 快速扫描) --")
    logger.info(f"  脚本路径: {script_path}")

    dry_success, _, dry_output = run_script(
        script_path,
        args=["--dry-run"],
        timeout=TASK_TIMEOUTS["cleanup"],
        return_output=True,
    )
    if not dry_success:
        logger.error("[cleanup] 预览失败，停止实际删除")
        return False

    has_files = "MATCH" in dry_output or "待删除" in dry_output
    if not has_files:
        logger.info("[cleanup] 没有需要清理的 AIGC 早报文件")
        return True

    logger.info("[cleanup] 检测到需清理文件，执行实际删除...")
    success, _ = run_script(script_path, timeout=TASK_TIMEOUTS["cleanup"])
    if success:
        logger.info("[cleanup] AIGC 早报清理完成")
    return success


# ═══════════════════════════════════════════════════════════════
# RSS 合并与去重翻译
# ═══════════════════════════════════════════════════════════════

def run_rss_capture(task_name="rss_recovery"):
    """执行一次 RSS 抓取，并在成功时记录相应任务。"""
    success, _ = run_script(RSS_SCRIPT, timeout=TASK_TIMEOUTS["rss"])
    if success and task_name:
        record_task_done(task_name)
    return success


def run_combine(allow_single_recovery=True):
    """优先收敛积压摘要，并将当天 RSS 一并交给合并器去重。"""
    logger.info("-- 开始合并 RSS 结果 --")
    rss_files = get_today_rss_files()
    pending_summaries = get_pending_summary_files()

    if not rss_files and not pending_summaries and allow_single_recovery:
        logger.warning("没有当天 RSS 或积压摘要，先执行一次恢复抓取")
        if not run_rss_capture():
            logger.error("恢复抓取失败，无法生成合并产物")
            return False
        time.sleep(2)
        rss_files = get_today_rss_files()

    if not rss_files and not pending_summaries:
        logger.error("没有 RSS 中间文件或积压摘要，合并取消")
        return False

    logger.info(
        "将合并当天 %s 份 RSS 文件与 %s 份积压摘要；积压摘要由合并器优先收敛",
        len(rss_files), len(pending_summaries),
    )
    file_args = [os.path.basename(path) for path in rss_files]
    success, _ = run_script(COMBINE_SCRIPT, args=file_args, timeout=TASK_TIMEOUTS["combine"])
    if success:
        logger.info("RSS 合并去重翻译完成")
        archive_rss_files(logger)
        return True

    logger.error("RSS 合并去重翻译在重试后仍失败；保留 RSS 中间文件与积压摘要以便下次恢复")
    return False


def run_first_boot_rss_recovery():
    """根据 GMT+8 当前时段恢复 RSS：不重复抓取，优先利用今天已有中间文件。"""
    now = schedule_now()
    rss_files = get_today_rss_files()
    after_combine_slot = now.hour > 14 or (now.hour == 14 and now.minute >= 5)
    between_rss_slots = now.hour >= 2 and not after_combine_slot

    pending_summaries = get_pending_summary_files()
    logger.info(
        "[首次启动] 发现今天 %s 份 RSS 文件和 %s 份积压摘要（GMT+8 %s）",
        len(rss_files), len(pending_summaries), now.strftime("%H:%M"),
    )
    if pending_summaries and not rss_files:
        logger.info("[首次启动] 优先收敛积压摘要，不为此额外抓取 RSS")
        return run_combine(allow_single_recovery=False)
    if not rss_files:
        logger.info("[首次启动] 没有可恢复的 RSS 文件，执行一次抓取后合并")
        if not run_rss_capture("rss_1"):
            return False
    elif between_rss_slots and len(rss_files) == 1:
        logger.info("[首次启动] 位于 02:00-14:05，补抓一次以与已有文件合并")
        run_rss_capture("rss_2")
    elif after_combine_slot:
        logger.info("[首次启动] 已过 14:05，直接合并已有文件，不重复抓取")
    else:
        logger.info("[首次启动] 直接合并已有 RSS 文件")

    return run_combine(allow_single_recovery=False)


# ═══════════════════════════════════════════════════════════════
# 每日首次启动：立即执行全部任务
# ═══════════════════════════════════════════════════════════════

def is_first_boot_today():
    """判断今天是否是首次启动 keepitrun"""
    try:
        if os.path.isfile(DAILY_BOOT_FLAG):
            with open(DAILY_BOOT_FLAG, "r", encoding="utf-8") as f:
                flag_date = f.read().strip()
                today_str = schedule_today().strftime("%Y-%m-%d")
                return flag_date != today_str
    except OSError:
        pass
    return True


def mark_boot_today():
    """标记今天已经启动过 keepitrun"""
    os.makedirs(LOG_DIR, exist_ok=True)
    try:
        with open(DAILY_BOOT_FLAG, "w", encoding="utf-8") as f:
            f.write(schedule_today().strftime("%Y-%m-%d"))
    except OSError as e:
        logger.error(f"写入启动标记失败: {e}")


def run_first_boot_tasks():
    """每日首次启动时执行今日尚未完成的任务

    场景: Windows 更新重启、脚本意外退出后重新启动、版本替换后首次运行等。
    v1.26 起：今天已完成的任务（无论由哪个版本完成）直接跳过，
    只补做今天尚未完成的任务，不因版本变更把当天所有事情重来一遍。
    """
    logger.info("=" * 60)
    logger.info("检测到今日首次启动，仅执行今天尚未完成的任务")
    logger.info("=" * 60)

    # 1. 先恢复/合并 RSS：已有文件优先，绝不为凑两份而重复抓取。
    if get_done_version_today("combine"):
        logger.info(
            "[首次启动] 步骤 1/4: RSS 恢复合并今天已完成 (v%s)，跳过",
            get_done_version_today("combine"),
        )
    else:
        logger.info("[首次启动] 步骤 1/4: 恢复并合并 RSS 结果")
        combine_ok = run_first_boot_rss_recovery()
        if combine_ok:
            record_task_done("combine")
            logger.info("[首次启动] RSS 合并去重翻译完成")
        else:
            logger.warning("[首次启动] RSS 合并去重翻译失败，保留中间文件等待下次恢复")

    # 2. 爬取最新 daily + blog
    logger.info("[首次启动] 步骤 2/4: 爬取最新 daily + blog")
    daily_path = os.path.join(SCRIPT_DIR, DAILY_SCRIPT)
    if not os.path.isfile(daily_path):
        logger.info("[首次启动] Daily脚本不存在，跳过")
    elif get_done_version_today("daily"):
        logger.info(
            "[首次启动] daily 今天已完成 (v%s)，跳过", get_done_version_today("daily")
        )
    else:
        success_daily, _ = run_script(
            DAILY_SCRIPT, args=["--non-interactive"], timeout=TASK_TIMEOUTS["daily"]
        )
        if success_daily:
            record_task_done("daily")
    time.sleep(2)

    blog_path = os.path.join(SCRIPT_DIR, BLOG_SCRIPT)
    if not os.path.isfile(blog_path):
        logger.info("[首次启动] Blog脚本不存在，跳过")
    elif get_done_version_today("blog"):
        logger.info(
            "[首次启动] blog 今天已完成 (v%s)，跳过", get_done_version_today("blog")
        )
    else:
        # 读取上次成功爬取日期
        last_date = ""
        if os.path.isfile(BLOG_LAST_CRAWL_FILE):
            try:
                with open(BLOG_LAST_CRAWL_FILE, "r", encoding="utf-8") as f:
                    last_date = f.read().strip()
            except OSError:
                pass
        # 构建参数
        # 如果没有上次爬取日期记录，默认抓取最近30天（而非 album:diff，避免全量遍历超时）
        # v1.28: 有记录时也封顶 30 天窗口，历史全量永不重跑
        args = []
        if last_date and re.match(r'\d{8}$', last_date):
            since_date = resolve_blog_since_date(
                last_date, schedule_today(), logger, prefix="[首次启动] ")
            args.append(f"album:{since_date}")
        else:
            fallback_date = (schedule_today() - timedelta(days=30)).strftime("%Y%m%d")
            args.append(f"album:{fallback_date}")
            logger.info(f"[首次启动] 无上次爬取记录，默认抓取最近30天 (album:{fallback_date})")
        args.append("--non-interactive")
        success_blog, _ = run_script(BLOG_SCRIPT, args=args, timeout=TASK_TIMEOUTS["blog"])
        if success_blog:
            record_task_done("blog")
            # 更新上次爬取日期
            try:
                os.makedirs(os.path.dirname(BLOG_LAST_CRAWL_FILE), exist_ok=True)
                with open(BLOG_LAST_CRAWL_FILE, "w", encoding="utf-8") as f:
                    f.write(schedule_today().strftime("%Y%m%d"))
            except OSError:
                pass

    # 4.5 归档 blog/daily 本地文件（两者都执行完后统一归档）
    archive_blog_daily_files(logger)

    # 5. Photos 同步
    if get_done_version_today("photos_update"):
        logger.info(
            "[首次启动] 步骤 3/4: Photos 自动同步今天已完成 (v%s)，跳过",
            get_done_version_today("photos_update"),
        )
    elif is_photos_update_enabled():
        logger.info("[首次启动] 步骤 3/4: Photos 自动同步")
        if run_photos_update():
            record_task_done("photos_update")
    else:
        logger.info("[首次启动] 步骤 3/4: Photos 同步脚本不存在，跳过")

    # 4. AIGC 早报清理（手动维护工具，首次启动时仍按既有安全预览流程执行）
    if get_done_version_today("cleanup"):
        logger.info(
            "[首次启动] 步骤 4/4: AIGC 早报清理今天已完成 (v%s)，跳过",
            get_done_version_today("cleanup"),
        )
    else:
        logger.info("[首次启动] 步骤 4/4: AIGC 早报清理（一次性维护）")
        if run_cleanup_daily_from_blog():
            record_task_done("cleanup")

    logger.info("=" * 60)
    logger.info("首次启动任务执行完毕，进入定时调度模式")
    logger.info("=" * 60)


# ═══════════════════════════════════════════════════════════════
# 已执行任务记录（防止同一分钟内重复执行）
# ═══════════════════════════════════════════════════════════════

_executed_tasks = {}


def should_run(task_name):
    """判断某个任务今天是否应该执行

    v1.26 语义:
    1. 同一会话内同一任务只执行一次 (内存去重)
    2. 今天已完成（无论由哪个版本完成）即不再执行；
       版本替换当日，首次运行新版只执行今天尚未完成的任务。
    """
    today = schedule_today().strftime("%Y-%m-%d")
    key = f"{task_name}_{today}"

    # 内存去重: 本会话内已执行过（含失败），不因版本变更重跑
    if key in _executed_tasks:
        return False

    # 今天已完成（任意版本）即跳过；版本号仅用于日志提示
    done_version = get_done_version_today(task_name)
    if done_version:
        if done_version == VERSION:
            logger.info(f"任务 {task_name} 今天已完成 (v{done_version}), already_done")
        else:
            logger.info(
                f"任务 {task_name} 今天已完成 (v{done_version})，版本替换日不重做, already_done"
            )
        return False

    _executed_tasks[key] = True
    return True


# ═══════════════════════════════════════════════════════════════
# 主循环
# ═══════════════════════════════════════════════════════════════

def main_loop():
    """主循环：每 30 秒检查一次当前时间，触发对应任务"""

    logger.info("=" * 60)
    logger.info(f"keepitrun v{VERSION} 启动")
    logger.info(f"脚本目录: {SCRIPT_DIR}")
    logger.info(f"日志目录: {LOG_DIR}")
    logger.info(f"临时目录: {TMP_DIR}")
    logger.info(f"归档目录: {ARCHIVED_DIR}")
    logger.info("")
    logger.info("清理策略:")
    logger.info(f"  tmp/       > {TMP_RETENTION_DAYS} 天  -> 删除")
    logger.info(f"  logs/      > {LOG_ARCHIVE_DAYS} 天  -> 移入 logs/archive/")
    logger.info(f"  logs/archive/ > {LOG_DELETE_DAYS} 天 -> 删除")
    logger.info(f"  archived/  > {ARCHIVED_RETENTION_DAYS} 天 -> 删除")
    logger.info("")
    logger.info("每日任务计划（GMT+8）:")
    logger.info(f"  02:00 - RSS 抓取（第 1 次） [{RSS_SCRIPT}]")
    logger.info(f"  10:05 - AIGC 早报 [{DAILY_SCRIPT}]")
    logger.info(f"  10:10 - 博客文章 [{BLOG_SCRIPT}]")
    logger.info(f"  14:00 - RSS 抓取（第 2 次） [{RSS_SCRIPT}]")
    logger.info(f"  14:05 - RSS 合并、去重与翻译 [{COMBINE_SCRIPT}]")
    if is_photos_update_enabled():
        logger.info(f"  15:00 - Photos 自动同步 [{PHOTOS_SCRIPT_NAME}]")
    else:
        logger.info(f"  15:00 - Photos 自动同步 [未找到: {PHOTOS_SCRIPT_NAME}]")
    logger.info(f"  首次启动维护 - daily 清理预览/执行 [{CLEANUP_DAILY_SCRIPT}]")
    logger.info("同日任务去重: 已启用 (task_completion.json；版本替换日不重做已完成任务)")
    logger.info("=" * 60)

    # 启动时执行清理
    run_all_cleanup(logger)

    # 确保必要目录存在
    os.makedirs(TMP_DIR, exist_ok=True)
    os.makedirs(ARCHIVED_DIR, exist_ok=True)

    # -- 每日首次启动：立即执行全部任务 --
    if is_first_boot_today():
        run_first_boot_tasks()
        mark_boot_today()
    else:
        logger.info("今日已启动过，跳过首次启动任务，进入定时调度模式")

    last_cleanup_date = schedule_today()

    while True:
        try:
            now = schedule_now()
            current_time = now.strftime("%H:%M")
            current_date = now.date()

            # 每天凌晨第一次循环时执行清理
            if current_date != last_cleanup_date:
                run_all_cleanup(logger)
                last_cleanup_date = current_date

            # -- 02:00 RSS 抓取 (第1次) --
            if current_time == "02:00" and should_run("rss_1"):
                logger.info(">>> 触发 02:00 RSS 抓取 (第1次)")
                run_rss_capture("rss_1")
                time.sleep(60)

            # -- 14:00 RSS 抓取 (第2次) --
            elif current_time == "14:00" and should_run("rss_2"):
                logger.info(">>> 触发 14:00 RSS 抓取 (第2次)")
                run_rss_capture("rss_2")
                time.sleep(60)

            # -- 14:05 合并去重翻译 --
            elif current_time == "14:05" and should_run("combine"):
                logger.info(">>> 触发 14:05 合并去重翻译 RSS 结果")
                combine_ok = run_combine()
                if combine_ok:
                    record_task_done("combine")
                time.sleep(60)

            # -- 10:05 爬取最新 daily (v1.3 重新启用) --
            elif current_time == "10:05" and should_run("daily"):
                daily_path = os.path.join(SCRIPT_DIR, DAILY_SCRIPT)
                if os.path.isfile(daily_path):
                    logger.info(">>> 触发 10:05 爬取最新 daily")
                    success, _ = run_script(
                        DAILY_SCRIPT, args=["--non-interactive"], timeout=TASK_TIMEOUTS["daily"]
                    )
                    if success:
                        record_task_done("daily")
                        # daily 成功后归档本地文件
                        archive_blog_daily_files(logger)
                else:
                    logger.warning(f"Daily脚本不存在: {daily_path}")
                time.sleep(60)

            # -- 10:10 爬取最新 blog (v1.2 重新启用) --
            elif current_time == "10:10" and should_run("blog"):
                blog_path = os.path.join(SCRIPT_DIR, BLOG_SCRIPT)
                if os.path.isfile(blog_path):
                    logger.info(">>> 触发 10:10 爬取最新 blog")
                    # 读取上次成功爬取日期
                    last_date = ""
                    if os.path.isfile(BLOG_LAST_CRAWL_FILE):
                        try:
                            with open(BLOG_LAST_CRAWL_FILE, "r", encoding="utf-8") as f:
                                last_date = f.read().strip()
                        except OSError:
                            pass
                    # 构建参数
                    # 如果没有上次爬取日期记录，默认抓取最近30天
                    # v1.28: 有记录时也封顶 30 天窗口，历史全量永不重跑
                    args = []
                    if last_date and re.match(r'\d{8}$', last_date):
                        since_date = resolve_blog_since_date(
                            last_date, schedule_today(), logger, prefix=">>> ")
                        args.append(f"album:{since_date}")
                    else:
                        fallback_date = (schedule_today() - timedelta(days=30)).strftime("%Y%m%d")
                        args.append(f"album:{fallback_date}")
                        logger.info(f">>> 无上次爬取记录，默认抓取最近30天 (album:{fallback_date})")
                    args.append("--non-interactive")
                    success, _ = run_script(BLOG_SCRIPT, args=args, timeout=TASK_TIMEOUTS["blog"])
                    if success:
                        record_task_done("blog")
                        # 更新上次爬取日期
                        try:
                            os.makedirs(os.path.dirname(BLOG_LAST_CRAWL_FILE), exist_ok=True)
                            with open(BLOG_LAST_CRAWL_FILE, "w", encoding="utf-8") as f:
                                f.write(schedule_today().strftime("%Y%m%d"))
                        except OSError:
                            pass
                        # blog 成功后归档本地文件
                        archive_blog_daily_files(logger)
                else:
                    logger.warning(f"Blog脚本不存在: {blog_path}")
                time.sleep(60)

            # -- 15:00 Photos 自动同步 (每日) --
            elif current_time == "15:00" and should_run("photos_update") and is_photos_update_enabled():
                logger.info(">>> 触发 15:00 Photos 自动同步")
                if run_photos_update():
                    record_task_done("photos_update")
                time.sleep(60)

            # 每 30 秒检查一次
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            logger.info("用户中断 (Ctrl+C)，退出 keepitrun")
            break
        except Exception as e:
            logger.error(f"主循环异常: {e}", exc_info=True)
            time.sleep(60)


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger = setup_logging()
    main_loop()
