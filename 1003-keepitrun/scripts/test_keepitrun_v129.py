# -*- coding: utf-8 -*-
"""对修复后的真实 keepitrun.py 做导入级验证（v1.29 发版前测试）。

直接 import 包内 keepitrun.py 并调用其 resolve_blog_since_date，
覆盖：窗口内/超窗/等界/非法输入/返回类型 + 版本常量 + 全脚本 py_compile。
"""
import importlib.util
import os
import py_compile
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..", "work-v129")


def main():
    failures = []

    # 1) 全部 10 脚本 py_compile（04 允许历史 docstring SyntaxWarning）
    for f in sorted(os.listdir(PKG)):
        if f.endswith(".py"):
            r = subprocess.run([sys.executable, "-m", "py_compile", f],
                               cwd=PKG, capture_output=True, text=True)
            warn = "SyntaxWarning" in (r.stderr or "")
            if r.returncode != 0:
                failures.append(f"py_compile 失败: {f}")
            else:
                print(f"[PASS] py_compile: {f}" + ("（含历史 docstring 警告，非本轮引入）" if warn else ""))

    # 2) 导入真实模块
    os.chdir(PKG)
    sys.path.insert(0, PKG)
    spec = importlib.util.spec_from_file_location("keepitrun_v129", "keepitrun.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    # 3) 版本常量断言
    if m.VERSION == "1.29" and m.VERSION_DATE == "2026-10-03":
        print(f"[PASS] 版本常量: VERSION={m.VERSION}, VERSION_DATE={m.VERSION_DATE}")
    else:
        failures.append(f"版本常量错误: {m.VERSION} / {m.VERSION_DATE}")

    if "1.29 变更" in (m.__doc__ or ""):
        print("[PASS] 模块 docstring 含 v1.29 变更块")
    else:
        failures.append("模块 docstring 缺 v1.29 变更块")

    # 4) 修复后的 resolve_blog_since_date 行为（today 用真实 schedule_today 类型：date）
    from datetime import date
    today = date(2026, 10, 3)

    class Log:
        def __init__(self): self.msgs = []
        def info(self, msg): self.msgs.append(msg)
    lg = Log()

    cases = [
        ("20260915", "20260915", None),          # 窗口内不动
        ("20260801", "20260903", "log"),         # 超窗截断 + 日志
        ("20260903", "20260903", None),          # 等界不截断
        ("20261002", "20261002", None),          # 昨日不动
        ("", "", None),                          # 非法回退
        ("abc", "abc", None),                    # 非法回退
        ("2026-09-01", "2026-09-01", None),      # 非法格式回退
        (None, None, None),                      # TypeError 输入回退
        ("2026093", "2026093", None),            # 7 位回退
    ]
    for last, expect, logmark in cases:
        got = m.resolve_blog_since_date(last, today, lg, prefix="[测试] ")
        if got != expect:
            failures.append(f"resolve({last!r}) = {got!r}, 期望 {expect!r}")
        else:
            print(f"[PASS] resolve_blog_since_date({last!r}) = {got!r}")

    if len(lg.msgs) == 1 and "20260903" in lg.msgs[0]:
        print(f"[PASS] 超窗日志恰 1 条且含窗口下界: {lg.msgs[0][:50]}...")
    else:
        failures.append(f"超窗日志异常: {lg.msgs}")

    # 5) 模拟真实调度语义：与 schedule_today() 同类型 today，8 位 str 进 album: 参数
    since = m.resolve_blog_since_date("20260701", m.schedule_today(), lg)
    if isinstance(since, str) and len(since) == 8 and since.isdigit():
        print(f"[PASS] 与 schedule_today() 配合返回 8 位数字串: {since}")
    else:
        failures.append(f"album 参数类型错误: {since!r}")

    # 6) 真实 8 位日期不再抛 TypeError（v1.28 缺陷的回归验证）
    try:
        for d in ("20250101", "20260101", "20260901", "20261003", "20270101"):
            m.resolve_blog_since_date(d, today)
        print("[PASS] 回归验证：历史/今天/未来合法日期均不再抛 TypeError")
    except TypeError as e:
        failures.append(f"回归失败，仍抛 TypeError: {e}")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("全部通过：修复后 keepitrun.py 导入级 20 项验证 OK。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
