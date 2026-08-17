from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "analysis" / "data_audit.json"


def read_csv(name: str) -> list[dict[str, str]]:
    with (DATA / name).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def n(row: dict[str, str], key: str) -> float:
    return float(row[key])


f1 = read_csv("f1_subdim_chart.csv")
matrix = read_csv("f1_subdim_matrix.csv")
f4f3 = read_csv("chart_04_f4_f3.csv")

assert len(f1) == 10, f"f1 行数错误：{len(f1)}"
assert len(matrix) == 10, f"matrix 行数错误：{len(matrix)}"
assert len(f4f3) == 10, f"f4/f3 行数错误：{len(f4f3)}"

f1_cols = [
    "喜剧/搞笑占比%", "演技/声台形表占比%", "共情/感染力占比%",
    "角色塑造/突破占比%", "剧本/节奏/整体占比%",
]
percentage_sum_deviation = {}

for row, detail in zip(f1, matrix, strict=True):
    assert row["作品"] == detail["作品"], f"作品错位：{row['作品']} / {detail['作品']}"
    assert row["年份"] == detail["年份"], f"年份错位：{row['作品']}"
    total = sum(n(row, col) for col in f1_cols)
    # 这些是逐项取整后的百分比，合计偏差仅作记录，不用于重算原始官方数据。
    percentage_sum_deviation[row["作品"]] = round(total - 100, 1)
    assert n(row, "非喜剧(S2+S3+S4)占比%") == n(detail, "非喜剧%"), f"非喜剧比例不一致：{row['作品']}"

stages = {
    "喜剧演员定型期（2015–2018）": ["夏洛特烦恼", "羞羞的铁拳", "西虹市首富"],
    "形象扩容与争议期（2019–2023）": ["飞驰人生", "独行月球", "超能一家人"],
    "转型被看见（2023–2026）": ["满江红", "抓娃娃", "飞驰人生3", "欢迎来龙餐馆"],
}

stage_summary = {}
for label, works in stages.items():
    rows = [row for row in f1 if row["作品"] in works]
    stage_summary[label] = {
        "works": works,
        "unweighted_mean_pct": {
            col: round(sum(n(row, col) for row in rows) / len(rows), 1)
            for col in f1_cols + ["非喜剧(S2+S3+S4)占比%"]
        },
        "effective_n": sum(int(row["有效(S0外)"]) for row in rows),
    }

highlights = {
    "喜剧最高": max(f1, key=lambda r: n(r, "喜剧/搞笑占比%")),
    "喜剧最低": min(f1, key=lambda r: n(r, "喜剧/搞笑占比%")),
    "演技最高": max(f1, key=lambda r: n(r, "演技/声台形表占比%")),
    "共情最高": max(f1, key=lambda r: n(r, "共情/感染力占比%")),
    "剧本节奏最高": max(f1, key=lambda r: n(r, "剧本/节奏/整体占比%")),
    "非喜剧最高": max(f1, key=lambda r: n(r, "非喜剧(S2+S3+S4)占比%")),
}

issue_changes = []
for row in f4f3:
    for key, label in [("F4", "商业资本"), ("F3", "民族国家")]:
        hot = n(row, f"hot_{key}_pct")
        latest = n(row, f"latest_{key}_pct")
        issue_changes.append({
            "作品": row["电影"],
            "维度": label,
            "热映期占比%": hot,
            "近期占比%": latest,
            "变化pp": round(latest - hot, 1),
            "热映期有效样本": int(row["hot_有框架_n"]),
            "近期有效样本": int(row["latest_有框架_n"]),
        })

payload = {
    "validation": {
        "f1_rows": len(f1),
        "matrix_rows": len(matrix),
        "f4f3_rows": len(f4f3),
        "f1_subdimension_percentage_sum_deviation_pp": percentage_sum_deviation,
        "note": "各子维度为原始官方整数百分比，逐项取整后合计可能存在偏差；阶段均值为作品等权平均，仅用于叙事辅助；核心图呈现逐片原始比例。",
    },
    "stage_summary": stage_summary,
    "highlights": {
        label: {
            "作品": row["作品"], "年份": int(row["年份"]),
            "value_pct": n(row, {
                "喜剧最高": "喜剧/搞笑占比%", "喜剧最低": "喜剧/搞笑占比%",
                "演技最高": "演技/声台形表占比%", "共情最高": "共情/感染力占比%",
                "剧本节奏最高": "剧本/节奏/整体占比%", "非喜剧最高": "非喜剧(S2+S3+S4)占比%",
            }[label]),
        }
        for label, row in highlights.items()
    },
    "issue_changes": issue_changes,
}

OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
