from __future__ import annotations

import csv
import json
from pathlib import Path

UPLOAD = Path('/home/ubuntu/upload')
OUT = Path(__file__).resolve().parent / 'official_data_audit.json'


def read_csv(name: str) -> list[dict[str, str]]:
    with (UPLOAD / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def percent(text: str) -> float:
    return float(text.strip().rstrip('%'))


heatmap = read_csv('shenteng_works_heatmap.csv')
dumbbell = read_csv('shenteng_dumbbell_chart.csv')
f1 = read_csv('f1_subdim_chart.csv')
f1_matrix = read_csv('f1_subdim_matrix.csv')
f34 = read_csv('chart_04_f4_f3.csv')

heatmap_sums = []
for row in heatmap:
    fields = ['专业能力', '道德人格', '民族国家', '商业资本', '社会文化/性别', '身份符号']
    total = round(sum(percent(row[field]) for field in fields), 2)
    heatmap_sums.append({'作品': row['作品'], '年份': row['年份'], 'sum_pct': total, 'valid_integer_rounding': 98 <= total <= 102})

dumbbell_checks = []
for row in dumbbell:
    release = float(row['上映期占比%'])
    recent = float(row['近年回看占比%'])
    provided = float(row['变化Δpp'])
    recomputed = round(recent - release, 1)
    # Source appears to use one-decimal display; tolerate 0.1 pp display/rounding discrepancies.
    dumbbell_checks.append({
        '作品': row['作品'], '年份': row['年份'], '维度': row['维度'],
        '上映期占比%': release, '近年回看占比%': recent, '变化Δpp_source': provided,
        '变化Δpp_recomputed': recomputed, 'within_display_tolerance': abs(provided - recomputed) <= 0.1,
    })

result = {
    'sources': {
        'shenteng_works_heatmap.csv': len(heatmap),
        'shenteng_dumbbell_chart.csv': len(dumbbell),
        'f1_subdim_chart.csv': len(f1),
        'f1_subdim_matrix.csv': len(f1_matrix),
        'chart_04_f4_f3.csv': len(f34),
    },
    'heatmap_sum_checks': heatmap_sums,
    'dumbbell_delta_checks': dumbbell_checks,
    'key_values': {
        'heatmap_抓娃娃_社会文化性别': next(r for r in heatmap if r['作品'] == '抓娃娃')['社会文化/性别'],
        'heatmap_欢迎来龙餐馆_专业能力': next(r for r in heatmap if r['作品'] == '欢迎来龙餐馆')['专业能力'],
        'dumbbell_抓娃娃_专业能力': next(r for r in dumbbell if r['作品'] == '抓娃娃' and r['维度'] == '专业能力'),
        'dumbbell_抓娃娃_社会文化性别': next(r for r in dumbbell if r['作品'] == '抓娃娃' and r['维度'] == '社会文化/性别'),
        'dumbbell_独行月球_民族国家': next(r for r in dumbbell if r['作品'] == '独行月球' and r['维度'] == '民族国家'),
    },
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'output': str(OUT), 'sources': result['sources'], 'bad_heatmap_rows': [r for r in heatmap_sums if not r['valid_integer_rounding']], 'bad_delta_rows': [r for r in dumbbell_checks if not r['within_display_tolerance']]}, ensure_ascii=False, indent=2))
