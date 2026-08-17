from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
R2 = ROOT / 'round2.3'
R3 = ROOT / 'round3.3'

comments = sorted(R2.glob('comment-part*-styled.html'))
heatmaps = sorted(R2.glob('img1-part*-styled.html'))
professional = sorted(R2.glob('img2-part*-styled.html'))
dumbbell = R2 / 'img3-part1-styled.html'
mp4s = sorted(R3.glob('*.mp4'))

comment_checks = []
for p in comments:
    text = p.read_text(encoding='utf-8')
    comment_checks.append({
        'file': p.name,
        'has_full_review_card': 'review-card' in text and 'review-poster' in text,
        'no_ocr_filename_text': 'OCR：' not in text and '640(' not in text,
        'no_redundant_data_source_text': '数据：用户提供原始评论截图 OCR' not in text,
        'has_movie_title': '《' in text and '》' in text,
    })

heatmap_checks = []
for p in heatmaps:
    text = p.read_text(encoding='utf-8')
    heatmap_checks.append({'file':p.name, 'five_data_rows': text.count('<tr>') == 6, 'part_marker': '1/2' in text or '2/2' in text})

video_specs=[]
for p in mp4s:
    probe = subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames','-show_entries','format=duration','-of','json',str(p)],check=True,capture_output=True,text=True)
    data=json.loads(probe.stdout); s=data['streams'][0]
    video_specs.append({'file':p.name,'codec':s['codec_name'],'width':s['width'],'height':s['height'],'fps':s['r_frame_rate'],'frames':s.get('nb_frames'),'duration':data['format']['duration']})

result={
    'counts': {'round2_comment_html':len(comments),'round2_heatmap_html':len(heatmaps),'round2_professional_html':len(professional),'round2_dumbbell_html':int(dumbbell.exists()),'round2_png':len(list(R2.glob('*-styled.png'))),'round3_motion_html':len(list(R3.glob('*-motion.html'))),'round3_mp4':len(mp4s)},
    'comment_checks':comment_checks,
    'heatmap_checks':heatmap_checks,
    'dumbbell_sync_structure': {'single_svg': dumbbell.read_text(encoding='utf-8').count('class="dumbbell-svg"') == 1, 'no_old_segment_rows': 'db5-row' not in dumbbell.read_text(encoding='utf-8'), 'all_three_dimensions': all(name in dumbbell.read_text(encoding='utf-8') for name in ['专业能力','民族国家','社会文化/性别'])},
    'assets': {name:(R2/'assets'/'posters'/name).exists() for name in ['xialuo.jpg','duxing.jpg','ribuluo.jpg','longcanguan.jpg']},
    'video_specs':video_specs,
}
result['all_comments_pass']=all(all(v for k,v in item.items() if k!='file') for item in comment_checks)
result['all_heatmaps_pass']=all(all(v for k,v in item.items() if k!='file') for item in heatmap_checks)
result['all_videos_pass']=all(v['codec']=='h264' and v['width']==1080 and v['height']==1080 and v['fps']=='30/1' and v['frames']=='405' and abs(float(v['duration'])-13.5)<.01 for v in video_specs)
out=R2/'evidence'/'final_validation.json'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
