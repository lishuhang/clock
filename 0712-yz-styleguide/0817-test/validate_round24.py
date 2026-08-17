from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
R24 = ROOT / 'round2.4'
R34 = ROOT / 'round3.4'
html24 = sorted(R24.glob('*-styled.html'))
html34 = sorted(R34.glob('*-motion.html'))
mp4s = sorted(R34.glob('*.mp4'))
forbidden = ['overlay_crop', 'clip-path:inset', 'mask:', 'white-overlay', 'center-mask']
all_source = '\n'.join(p.read_text(encoding='utf-8') for p in html34)

specs=[]
for p in mp4s:
    d=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames','-show_entries','format=duration','-of','json',str(p)]))
    s=d['streams'][0]
    specs.append({'file':p.name,'codec':s['codec_name'],'width':s['width'],'height':s['height'],'fps':s['r_frame_rate'],'frames':s['nb_frames'],'duration':d['format']['duration']})

result={
  'counts':{'round24_html':len(html24),'round24_preview_png':len(list(R24.glob('*-styled.png'))),'round34_motion_html':len(html34),'round34_mp4':len(mp4s)},
  'no_canvas_white_overlay':{key:(key not in all_source) for key in forbidden},
  'reused_motion_hooks':{
    'comments_typewriter':'yz-type-char' in all_source,
    'heatmap_bloom':'yz-bloom' in all_source,
    'stacked_bar_element_growth':'yzGrowX' in all_source,
    'dumbbell_element_primitives':'yz-db-line' in all_source,
    'round39_controlled_trajectory':'round39-controlled-simultaneous-svg-runtime' in all_source and 'const MOVES=' in all_source,
  },
  'video_specs':specs,
}
result['all_video_specs_pass']=all(s['codec']=='h264' and s['width']==1080 and s['height']==1080 and s['fps']=='30/1' and s['frames']=='405' and abs(float(s['duration'])-13.5)<.01 for s in specs)
result['all_pass']=all(result['no_canvas_white_overlay'].values()) and all(result['reused_motion_hooks'].values()) and result['all_video_specs_pass'] and result['counts']['round24_html']==13 and result['counts']['round34_motion_html']==13 and result['counts']['round34_mp4']==13
out=R24/'evidence'/'final_animation_validation.json'
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
