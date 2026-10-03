# -*- coding: utf-8 -*-
"""验证 keepitrun.py resolve_blog_since_date 的日期类型 bug（v1.28 → v1.29 修复依据）。

从 1.28 包内 keepitrun.py 提取原函数体逐字复现，证明：
  - datetime 与 date 直接 < 比较抛 TypeError（v1.28 现状，bug 确认）
  - .date() 修复后行为正确（窗口内不动 / 超窗截断 / 非法输入回退）
"""
import sys
from datetime import datetime, date, timedelta

BLOG_SYNC_WINDOW_DAYS = 30


def make_resolver(use_fix: bool):
    def resolve_blog_since_date(last_date, today, logger=None, prefix=""):
        try:
            last_dt = datetime.strptime(last_date, "%Y%m%d")
            if use_fix:
                last_dt = last_dt.date()
        except (TypeError, ValueError):
            return last_date
        floor_dt = today - timedelta(days=BLOG_SYNC_WINDOW_DAYS)
        if last_dt < floor_dt:  # v1.28: datetime < date → TypeError
            floor_str = floor_dt.strftime("%Y%m%d")
            if logger:
                logger.info(f"{prefix}截断到窗口下界 {floor_str}")
            return floor_str
        return last_date
    return resolve_blog_since_date


class Log:
    def __init__(self): self.msgs = []
    def info(self, m): self.msgs.append(m)


def main():
    today = date(2026, 10, 3)
    old = make_resolver(use_fix=False)   # 复刻 v1.28 原样
    new = make_resolver(use_fix=True)    # 修复版
    lg = Log()

    # 1) 复现 v1.28 崩溃（生产场景：last_blog_crawl.txt 记录 20260801）
    try:
        old("20260801", today, lg, "[首次启动] ")
        print("[FAIL] v1.28 复现未触发 TypeError —— 与预期不符，需重新分析")
        return 1
    except TypeError as e:
        print(f"[PASS] v1.28 复现崩溃: TypeError: {e}")

    # 2) 边界：last_dt == floor_dt 时同样崩溃（比较不成立也先抛类型错误）
    try:
        old("20260903", today)  # 2026-09-03 == today-30d
        print("[FAIL] 等界日期未触发 TypeError")
        return 1
    except TypeError:
        print("[PASS] 等界日期 v1.28 同样崩溃（任何合法 8 位日期均触发）")

    # 3) 修复版：窗口内日期原样返回
    r = new("20260915", today, lg)
    assert r == "20260915", r
    print("[PASS] 修复版窗口内不动: 20260915")

    # 4) 修复版：超窗截断到下界并写日志
    r = new("20260801", today, lg)
    assert r == "20260903", r  # today - 30d = 2026-09-03
    assert len(lg.msgs) == 1, lg.msgs
    print(f"[PASS] 修复版超窗截断: 20260801 -> 20260903，日志: {lg.msgs[0][:40]}...")

    # 5) 修复版：等界日期不截断
    r = new("20260903", today)
    assert r == "20260903", r
    print("[PASS] 修复版等界日期不截断（< 严格小于）")

    # 6) 修复版：非法输入回退原值（与 v1.28 行为一致）
    for bad in ("", "abc", "2026-09-01", None, "2026093"):
        assert new(bad, today) == bad, bad
    print("[PASS] 修复版非法输入回退原值: '', 'abc', '2026-09-01', None, '2026093'")

    # 7) 修复版与调度侧参数拼接类型正确（str，可直接进 album: 参数）
    r = new("20260701", today)
    assert isinstance(r, str) and len(r) == 8
    print("[PASS] 修复版返回 str 8 位日期，可直接拼 album: 参数")

    print("\n结论：v1.28 的 resolve_blog_since_date 在任何合法 8 位日期输入下"
          "必然抛 TypeError（比较在 try 块之外）；.date() 修复后 7 项行为全部正确。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
