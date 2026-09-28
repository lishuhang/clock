#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按博客 ``_config.yml`` 的 image_prefixes 规则解析图床上传路由。

模块刻意不依赖 PyYAML，避免给 Windows 生产环境增加安装步骤。它仅解析
keepitrun 使用的受限 YAML 子集：``image_prefixes`` 下的 ``range``、``prefix``
及嵌套 ``upload`` 配置。范围使用半开区间 ``[start_YYYY-MM, end_YYYY-MM)``。

推荐配置示例::

    image_prefixes:
      - range: [null, "2026-08"]
        prefix: "https://lishuhang.me/img/"
        upload:
          repository: "modem-56k/img"
          branch: "main"
          path_prefix: ""
      - range: ["2026-08", null]
        prefix: "https://lishuhang.me/img2/"
        upload:
          repository: "modem-56k/img2"
          branch: "main"
          path_prefix: ""
"""

from __future__ import annotations

import base64
import re
from typing import Any, Callable, Dict, Iterable, List, Optional


class ImageRouteError(RuntimeError):
    """配置缺失、格式错误或无法确定上传目标时抛出。"""


_DATE_KEY_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_RAW_GITHUB_PREFIX = re.compile(
    r"^https?://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)(?:/|$)"
)

# 兼容 v1.20 及更早的配置。新的配置应始终明确写 upload，避免依赖此回退。
_LEGACY_PREFIX_TARGETS = {
    "https://lishuhang.me/img": {
        "repository": "lishuhang/img",
        "branch": "master",
        "path_prefix": "",
    },
}


def _unquote_yaml_scalar(value: str) -> Optional[str]:
    """解析本模块支持的 YAML 标量（null、单双引号和裸文本）。"""
    value = value.strip()
    if not value or value.lower() in {"null", "~"}:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    # 配置值中允许在末尾写普通注释；URL 中的 # 不作该处理。
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return value


def _parse_range(value: str) -> List[Optional[str]]:
    """解析 ``[start, end]`` 格式的 image_prefixes 范围。"""
    match = re.match(r"^\[\s*(.*?)\s*,\s*(.*?)\s*\]$", value.strip())
    if not match:
        raise ImageRouteError(f"image_prefixes.range 格式无效: {value!r}")
    lower = _unquote_yaml_scalar(match.group(1))
    upper = _unquote_yaml_scalar(match.group(2))
    for label, date_key in (("起始", lower), ("截止", upper)):
        if date_key is not None and not _DATE_KEY_PATTERN.match(date_key):
            raise ImageRouteError(
                f"image_prefixes.range 的{label}月份必须是 YYYY-MM: {date_key!r}"
            )
    if lower and upper and lower >= upper:
        raise ImageRouteError(
            f"image_prefixes.range 的起始月份必须早于截止月份: {lower!r}, {upper!r}"
        )
    return [lower, upper]


def parse_image_prefixes(config_text: str) -> List[Dict[str, Any]]:
    """从完整 ``_config.yml`` 文本读取 image_prefixes 规则。

    仅支持 keepitrun 当前约定的缩进结构。遇到不完整或歧义配置会明确失败，
    从而避免把图片上传到默认或错误仓库。
    """
    lines = config_text.splitlines()
    in_block = False
    current: Optional[Dict[str, Any]] = None
    in_upload = False
    entries: List[Dict[str, Any]] = []

    for raw_line in lines:
        if not in_block:
            if re.match(r"^image_prefixes\s*:\s*(?:#.*)?$", raw_line):
                in_block = True
            continue

        # image_prefixes 块结束：回到顶层、不是空行/注释且不是列表项。
        if raw_line and not raw_line[0].isspace() and not raw_line.lstrip().startswith("#"):
            break
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        entry_match = re.match(r"^\s*-\s*range\s*:\s*(.+?)\s*$", raw_line)
        if entry_match:
            if current is not None:
                entries.append(current)
            current = {"range": _parse_range(entry_match.group(1)), "upload": {}}
            in_upload = False
            continue

        if current is None:
            raise ImageRouteError("image_prefixes 下必须以 '- range:' 开始规则")

        key_match = re.match(r"^(\s+)([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*$", raw_line)
        if not key_match:
            raise ImageRouteError(f"无法解析 image_prefixes 配置行: {raw_line!r}")
        indent, key, raw_value = key_match.groups()
        value = _unquote_yaml_scalar(raw_value)

        if len(indent) <= 4:
            in_upload = key == "upload"
            if key == "prefix":
                current["prefix"] = value or ""
            elif key == "upload":
                if value is not None:
                    raise ImageRouteError("image_prefixes.upload 必须是嵌套映射")
            elif key == "range":
                # 防止同一规则里意外再次定义范围。
                raise ImageRouteError("每条 image_prefixes 规则只能定义一次 range")
            else:
                current[key] = value
        elif in_upload:
            current["upload"][key] = value or ""
        else:
            raise ImageRouteError(f"image_prefixes 中不支持的嵌套配置: {raw_line!r}")

    if current is not None:
        entries.append(current)
    if not in_block:
        raise ImageRouteError("目标博客的 _config.yml 未定义 image_prefixes")
    if not entries:
        raise ImageRouteError("目标博客的 image_prefixes 为空")

    for index, entry in enumerate(entries, 1):
        if not entry.get("prefix"):
            raise ImageRouteError(f"第 {index} 条 image_prefixes 未设置 prefix")
    return entries


def select_image_prefix(entries: Iterable[Dict[str, Any]], date_key: str) -> Dict[str, Any]:
    """根据 YYYY-MM 选择唯一的日期范围；范围边界遵循 [start, end)。"""
    if not _DATE_KEY_PATTERN.match(date_key):
        raise ImageRouteError(f"图片日期必须为 YYYY-MM: {date_key!r}")

    matches = []
    for entry in entries:
        lower, upper = entry.get("range", [None, None])
        if lower and date_key < lower:
            continue
        if upper and date_key >= upper:
            continue
        matches.append(entry)

    if not matches:
        raise ImageRouteError(f"image_prefixes 未覆盖图片月份 {date_key}")
    if len(matches) > 1:
        raise ImageRouteError(f"image_prefixes 对图片月份 {date_key} 存在重叠规则")
    return matches[0]


def _infer_legacy_upload_target(prefix: str) -> Dict[str, str]:
    """从旧式公开 URL 推导上传目标；新配置应使用 upload 显式声明。"""
    normalized = prefix.rstrip("/")
    if normalized in _LEGACY_PREFIX_TARGETS:
        return dict(_LEGACY_PREFIX_TARGETS[normalized])

    raw_match = _RAW_GITHUB_PREFIX.match(prefix)
    if raw_match:
        owner, repo, branch = raw_match.groups()
        return {"repository": f"{owner}/{repo}", "branch": branch, "path_prefix": ""}

    raise ImageRouteError(
        "image_prefixes 规则未设置 upload，且无法从 prefix 推导上传仓库: "
        f"{prefix!r}；请在该规则中显式配置 upload.repository 与 upload.branch"
    )


def resolve_upload_route(config_text: str, post_date: str) -> Dict[str, str]:
    """解析配置并返回给上传程序使用的标准化路由。

    ``post_date`` 接受 ``YYYY-MM-DD`` 或 ``YYYY-MM``；返回值包含面向展示的
    ``prefix``，以及 ``repository``、``branch``、``path_prefix`` 三个上传字段。
    """
    date_key = post_date[:7]
    entries = parse_image_prefixes(config_text)
    selected = select_image_prefix(entries, date_key)
    upload = dict(selected.get("upload") or {})
    if not upload.get("repository") or not upload.get("branch"):
        upload = _infer_legacy_upload_target(selected["prefix"])

    repository = str(upload.get("repository", "")).strip()
    if not re.match(r"^[^/\s]+/[^/\s]+$", repository):
        raise ImageRouteError(f"upload.repository 必须为 owner/repo: {repository!r}")
    branch = str(upload.get("branch", "")).strip()
    if not branch:
        raise ImageRouteError("image_prefixes.upload.branch 不得为空")
    path_prefix = str(upload.get("path_prefix", "")).strip().strip("/")

    return {
        "date_key": date_key,
        "prefix": str(selected["prefix"]).rstrip("/") + "/",
        "repository": repository,
        "branch": branch,
        "path_prefix": path_prefix,
    }


def load_upload_route(
    get_file_info: Callable[[str, str, str, Optional[str]], Optional[Dict[str, Any]]],
    blog_repository: str,
    blog_branch: str,
    post_date: str,
) -> Dict[str, str]:
    """通过既有 GitHub Contents API 封装读取目标博客的 ``_config.yml``。"""
    if "/" not in blog_repository:
        raise ImageRouteError(f"博客仓库必须为 owner/repo: {blog_repository!r}")
    owner, repo = blog_repository.split("/", 1)
    info = get_file_info(owner, repo, "_config.yml", branch=blog_branch)
    if not info or not info.get("content"):
        raise ImageRouteError(
            f"无法读取 {blog_repository}@{blog_branch} 的 _config.yml"
        )
    try:
        config_text = base64.b64decode(info["content"]).decode("utf-8-sig")
    except Exception as exc:
        raise ImageRouteError(
            f"无法解码 {blog_repository}@{blog_branch} 的 _config.yml"
        ) from exc
    return resolve_upload_route(config_text, post_date)


def join_repo_path(route: Dict[str, str], relative_path: str) -> str:
    """将配置的路径前缀与图片相对路径安全拼接为 Contents API 路径。"""
    relative_path = relative_path.strip().lstrip("/")
    if not relative_path:
        raise ImageRouteError("图片相对路径不得为空")
    prefix = route.get("path_prefix", "").strip().strip("/")
    return f"{prefix}/{relative_path}" if prefix else relative_path


def public_image_base_url(route: Dict[str, str]) -> str:
    """返回供 photos 月度 JSON 使用的 URL 模板根路径。"""
    prefix = route.get("prefix", "").strip()
    if not prefix:
        raise ImageRouteError("image_prefixes.prefix 不得为空")
    return prefix.rstrip("/") + "/{year}/{month}/{day}/"
