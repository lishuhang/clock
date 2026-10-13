# -*- coding: utf-8 -*-
"""
wxbridge.py — Windows 365 云电脑微信桥（cruise-bot Phase 2）
=============================================================
作用：把老公/家人的微信消息中转到 cruise-bot（→ WhatsApp/iMessage 给船上的人），
     并执行 Worker 下发的微信发送指令（「回微信 @人 内容」）。

机制（全部免费，复用 Worker 现有端点）：
  收：wxauto 监听指定聊天 → POST /send {who:"owner"} → 老公 WhatsApp 收到
  发：轮询 GET /state?key=wx_outbox → wxauto 逐条发送 → POST /state 置空队列

前提：
  1. Windows 365 云电脑（保持运行不关机），已安装 PC 微信客户端并登录（扫码一次）
  2. Python 3.9+：pip install wxauto requests
  3. 环境变量或在下方直接填：WORKER_URL / AGENT_KEY

诚实边界：wxauto 基于 UI 自动化，微信客户端大版本更新可能导致失效；属于尽力而为模块，
主通道（WhatsApp/iMessage）不依赖本脚本。

部署：
  1. 微信客户端登录、勾选"关闭主面板时最小化到托盘"
  2. 修改下方 LISTEN 列表（要中转的联系人/群名）
  3. 计划任务自启：见 README-win365.md
"""

import json
import os
import time
import traceback

import requests

WORKER_URL = os.environ.get("WORKER_URL", "https://cruise-bot.你的子域.workers.dev")
AGENT_KEY = os.environ.get("AGENT_KEY", "换成你的AGENT_KEY")
POLL_SEC = 30
# 要监听中转的联系人/群（微信备注名，原样匹配）。家人群或父母等需要"上船直达"的会话。
LISTEN = ["文件传输助手", "家人群"]
# 收到微信消息后 bot 推给谁：owner=老公（默认）；wife=直接推船上（谨慎，会打扰度假）
PUSH_WHO = os.environ.get("PUSH_WHO", "owner")
STATE_PREFIX = ""  # 兼容位


def api_state_get(key):
    r = requests.get(f"{WORKER_URL}/state", params={"key": key},
                     headers={"x-agent-key": AGENT_KEY}, timeout=15)
    r.raise_for_status()
    return r.json().get("value")


def api_state_put(key, value, ttl=None):
    r = requests.post(f"{WORKER_URL}/state", headers={"x-agent-key": AGENT_KEY},
                      json={"key": key, "value": value, "ttl": ttl}, timeout=15)
    r.raise_for_status()


def api_send(text, who="owner"):
    r = requests.post(f"{WORKER_URL}/send", headers={"x-agent-key": AGENT_KEY},
                      json={"text": text, "who": who, "channel": "auto"}, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    from wxauto import WeChat   # 延迟导入，便于无 GUI 环境下语法检查

    wx = WeChat()
    print("已连接微信窗口")

    for name in LISTEN:
        try:
            wx.AddListenChat(who=name)
            print(f"监听：{name}")
        except Exception as e:
            print(f"监听失败 {name}: {e}")

    while True:
        # ---- 1) 收：监听消息 → Worker ----
        try:
            msgs = wx.GetListenMessage()
            for chat, content in (msgs or {}).items():
                who = chat.who
                for item in content:  # 每条消息
                    text = getattr(item, "content", None) or str(item)
                    if not text or not text.strip():
                        continue
                    # 过滤自己发出的（wxauto 会带回显）
                    if getattr(item, "is_self", False) or text.startswith("[文件]"):
                        continue
                    try:
                        api_send(f"💬 微信[{who}]：{text.strip()[:1200]}", PUSH_WHO)
                        print(f"转发：{who}: {text[:50]}")
                    except Exception:
                        traceback.print_exc()
        except Exception:
            traceback.print_exc()

        # ---- 2) 发：Worker outbox → 微信 ----
        try:
            raw = api_state_get("wx_outbox")
            box = json.loads(raw) if raw else []
            if box:
                print(f"outbox {len(box)} 条待发")
                for job in box:
                    try:
                        wx.SendMsg(msg=job["text"], who=job["to"])
                        print(f"已发：→{job['to']}: {job['text'][:50]}")
                    except Exception:
                        traceback.print_exc()
                api_state_put("wx_outbox", "[]")
        except Exception:
            traceback.print_exc()

        # ---- 3) 心跳（可在 Worker KV 看到云电脑存活） ----
        try:
            api_state_put("wx_bridge_heartbeat", str(int(time.time())), 86400)
        except Exception:
            pass

        time.sleep(POLL_SEC)


if __name__ == "__main__":
    main()
