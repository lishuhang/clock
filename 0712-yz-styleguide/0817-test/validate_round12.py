from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
R1, R2, R3 = ROOT / 'round1.2', ROOT / 'round2.2', ROOT / 'round3.2'

result: dict[str, object] = {}
htmls_r1 = sorted(R1.glob('*-styled.html'))
htmls_r2 = sorted(R2.glob('*-styled.html'))
htmls_r3 = sorted(R3.glob('*-motion.html'))
mp4s = sorted(R3.glob('*.mp4'))

result['counts'] = {
    'round1_html': len(htmls_r1), 'round1_png': len(list(R1.glob('*-styled.png'))),
    'round2_html': len(htmls_r2), 'round2_png': len(list(R2.glob('*-styled.png'))),
    'round3_motion_html': len(htmls_r3), 'round3_mp4': len(mp4s),
}

all_htmls = htmls_r1 + htmls_r2 + htmls_r3
result['brand_checks'] = {
    'all_use_AliPuHui': all('AliPuHui' in p.read_text(encoding='utf-8') for p in all_htmls),
    'all_inline_original_symbols': all('#yz-logo-' in p.read_text(encoding='utf-8') and '<symbol id="yz-logo-horizontal"' in p.read_text(encoding='utf-8') for p in all_htmls),
    'no_noto_font': not any('Noto' in p.read_text(encoding='utf-8') for p in all_htmls),
    'no_previous_top_bar_rule': not any('card::before' in p.read_text(encoding='utf-8') for p in all_htmls),
}

key_html = (R1 / 'img1-a-heatmap-styled.html').read_text(encoding='utf-8')
result['official_data_spot_checks'] = {
    'heatmap_夏洛特烦恼_专业能力_72pct': '72%' in key_html,
    'heatmap_抓娃娃_社会文化性别_57pct': '57%' in key_html,
    'heatmap_欢迎来龙餐馆_专业能力_92pct': '92%' in key_html,
    'all_three_source_csv_copied': all((R1 / 'data' / name).exists() for name in ['shenteng_works_heatmap.csv','shenteng_dumbbell_chart.csv','f1_subdim_chart.csv']),
}

video_specs = []
for p in mp4s:
    probe = subprocess.run([
        'ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames',
        '-show_entries','format=duration','-of','json',str(p)
    ], check=True, capture_output=True, text=True)
    record = json.loads(probe.stdout)
    s = record['streams'][0]
    video_specs.append({'file':p.name, 'codec':s['codec_name'], 'width':s['width'], 'height':s['height'], 'fps':s['r_frame_rate'], 'frames':s.get('nb_frames'), 'duration':record['format']['duration']})
result['video_specs'] = video_specs
result['all_videos_match_v222c_timing'] = all(v['codec']=='h264' and v['width']==1080 and v['height']==1080 and v['fps']=='30/1' and v['frames']=='480' and abs(float(v['duration'])-16.0)<0.01 for v in video_specs)

out = ROOT / 'round1.2-ocr' / 'final_validation.json'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, ensure_ascii=False, indent=2))
