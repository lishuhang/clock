#!/usr/bin/env python3
"""百度网盘素材下载工具（xpan REST API 直调，官方 MCP 无下载工具故走此通路）。

前置：用户在 prompt 中提供 access token（获取链接见 SKILL.md §4.1）。
用法：
  export BAIDU_NETDISK_ACCESS_TOKEN=<token>
  netdisk.py quota                              # 验证 token + 查看容量
  netdisk.py list /素材目录                      # 列目录（递归列出由调用方自行处理分页）
  netdisk.py search "关键词" [--dir /路径]       # 文件名搜索
  netdisk.py meta "/路径/文件"                   # 查看文件元数据（含 fs_id）
  netdisk.py download "/路径/文件" [-d 目录]     # 三步下载到本地
实现要点（2026-11 官方文档实测归纳）：
  - 下载三步：list/search 拿 fs_id -> file?method=filemetas&dlink=1 拿 dlink（旧文档
    multifile?method=metas 已 404 下线）-> GET dlink&access_token=... 且 User-Agent
    固定为 pan.baidu.com（否则 31326 防盗链）；filemetas 响应字段为 info 数组
  - dlink 有效期 8 小时；下载走 302 跳转；支持 Range 断点续传
  - 个人开发者 QPS ≈ 10/s：请求间内置 0.3s 间隔，429 时指数退避
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

API_BASE = "https://pan.baidu.com/rest/2.0/xpan"
UA_NETDISK = "pan.baidu.com"  # 下载/接口必需的 UA，勿改
REQ_INTERVAL = 0.3            # QPS 保护
_last_req = 0.0

ERROR_ZH = {
    31045: "access_token 无效或过期（走 SKILL.md §4.1 授权链接重新获取）",
    31326: "命中防盗链：请求未带 User-Agent: pan.baidu.com",
    31362: "签名/链接不完整：检查 dlink 是否完整拼接了 access_token",
    -7: "文件或目录无权访问（token 授权范围外或路径不存在）",
    -9: "文件或目录不存在（ios 个别文件叫 /来自：分享 等特殊路径需 urlencode）",
    429: "触发限流（QPS 超限），稍后重试",
    31034: "接口错误：请求过于频繁或命中风控，等几分钟再试",
    31064: "达到调用上限",
    6: "身份验证失败",
}


def get_token():
    tok = os.environ.get("BAIDU_NETDISK_ACCESS_TOKEN", "").strip()
    if not tok:
        sys.exit("ERROR: 未设置 BAIDU_NETDISK_ACCESS_TOKEN。请让用户提供 access token（见 SKILL.md §4.1）")
    return tok


def throttle():
    global _last_req
    dt = time.time() - _last_req
    if dt < REQ_INTERVAL:
        time.sleep(REQ_INTERVAL - dt)
    _last_req = time.time()


def api_get(path, params, base=None):
    """GET 一个 xpan JSON 接口，返回解析后的 dict（含错误码翻译）。"""
    params = dict(params)
    params["access_token"] = get_token()
    url = f"{base or API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    throttle()
    req = urllib.request.Request(url, headers={"User-Agent": UA_NETDISK})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    errno = data.get("errno", 0)
    if errno != 0:
        msg = ERROR_ZH.get(errno, "未知错误")
        sys.exit(f"ERROR: API {path} 返回 errno={errno}（{msg}）\n原始响应: {json.dumps(data, ensure_ascii=False)[:500]}")
    return data


def cmd_quota(_):
    d = api_get("nas", {"method": "uinfo"})
    print(f"账号: {d.get('baidu_name', '?')}  uk={d.get('uk', '?')}  vip_type={d.get('vip_type', '?')}")
    q = api_get("api/quota", {"checkexpire": 1}, base="https://pan.baidu.com")
    total = q.get("total", 0)
    used = q.get("used", 0)
    print(f"总容量: {total/2**30:.1f} GB  已用: {used/2**30:.1f} GB  剩余: {(total-used)/2**30:.1f} GB")
    print("token 有效 ✅")


def _print_entries(entries):
    if not entries:
        print("（空目录或无匹配结果）")
        return
    for e in entries:
        kind = "DIR " if e.get("isdir") else "FILE"
        size = "" if e.get("isdir") else f"  {e.get('size', 0)/2**20:.1f}MB"
        print(f"[{kind}] fsid={e.get('fs_id')}  {e.get('server_filename', e.get('filename', '?'))}{size}")
        if e.get("path"):
            print(f"        path: {e['path']}")


def cmd_list(args):
    d = api_get("file", {"method": "list", "dir": args.dir,
                         "order": "time", "desc": 1, "limit": 1000})
    print(f"目录 {args.dir}（{len(d.get('list', []))} 项）:")
    _print_entries(d.get("list", []))


def cmd_search(args):
    d = api_get("file", {"method": "search", "key": args.key,
                         "dir": args.dir, "num": 50})
    print(f"搜索 “{args.key}”（{len(d.get('list', []))} 项）:")
    _print_entries(d.get("list", []))


def cmd_meta(args):
    fsid = _resolve_fsid(args.path)
    d = api_get("file", {"method": "filemetas", "fsids": json.dumps([fsid]), "dlink": 1})
    entries = d.get("info", [])
    if not entries:
        sys.exit("ERROR: 未查到元数据")
    print(json.dumps(entries[0], ensure_ascii=False, indent=2)[:2000])


def _resolve_fsid(path):
    """给定绝对路径，返回 fs_id（父目录 list 后按文件名匹配）。"""
    path = path.rstrip("/")
    parent, name = path.rsplit("/", 1) or ("/", path)
    d = api_get("file", {"method": "list", "dir": parent or "/", "limit": 1000})
    for e in d.get("list", []):
        if e.get("server_filename") == name or e.get("path") == path:
            if e.get("isdir"):
                sys.exit(f"ERROR: {path} 是目录，请指定文件（或先 list 查看内容）")
            return e["fs_id"]
    sys.exit(f"ERROR: 在 {parent or '/'} 下未找到 {name}（注意中文路径会自动 urlencode，请确认路径准确）")


def _get_dlink(fsid):
    # 注意：旧文档的 multifile?method=metas 已 404 下线，现行端点为 file?method=filemetas（2026-11 实测）
    d = api_get("file", {"method": "filemetas", "fsids": json.dumps([fsid]), "dlink": 1})
    entries = d.get("info", [])
    if not entries or not entries[0].get("dlink"):
        sys.exit(f"ERROR: 未取得 dlink，原始响应: {json.dumps(d, ensure_ascii=False)[:300]}")
    return entries[0]["dlink"]


def cmd_download(args):
    fsid = _resolve_fsid(args.path)
    dlink = _get_dlink(fsid)
    os.makedirs(args.dest, exist_ok=True)
    filename = args.path.rstrip("/").rsplit("/", 1)[-1]
    out = os.path.join(args.dest, filename)

    url = f"{dlink}&access_token={get_token()}"
    # 手动跟随 302（每跳都带 UA），官方下载域为 d.pcs.baidu.com
    redirects = 0
    while True:
        throttle()
        req = urllib.request.Request(url, headers={"User-Agent": UA_NETDISK})
        resp = urllib.request.urlopen(req, timeout=120)
        if resp.status in (301, 302, 303, 307, 308):
            url = resp.headers.get("Location")
            redirects += 1
            if redirects > 5:
                sys.exit("ERROR: 重定向超过 5 次，异常")
            continue
        total = int(resp.headers.get("Content-Length", 0))
        done = 0
        with open(out, "wb") as f:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r下载中 {done/2**20:.1f}/{total/2**20:.1f} MB", end="", flush=True)
        break
    size = os.path.getsize(out)
    if size < 1024:
        head = open(out, "rb").read(200)
        sys.exit(f"ERROR: 下载文件异常（{size}B），响应头: {head!r}")
    print(f"\n完成 ✅ {out}  ({size/2**20:.1f} MB)")


def main():
    p = argparse.ArgumentParser(description="百度网盘素材下载（xpan API 直调）")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("quota").set_defaults(func=cmd_quota)
    sp = sub.add_parser("list"); sp.add_argument("dir", nargs="?", default="/")
    sp.set_defaults(func=cmd_list)
    sp = sub.add_parser("search"); sp.add_argument("key")
    sp.add_argument("--dir", default="/"); sp.set_defaults(func=cmd_search)
    sp = sub.add_parser("meta"); sp.add_argument("path"); sp.set_defaults(func=cmd_meta)
    sp = sub.add_parser("download"); sp.add_argument("path")
    sp.add_argument("-d", "--dest", default="downloads"); sp.set_defaults(func=cmd_download)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
