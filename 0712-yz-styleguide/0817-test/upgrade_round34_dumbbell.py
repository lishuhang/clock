from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV = ROOT / 'round1.2' / 'data' / 'shenteng_dumbbell_chart.csv'
TARGET = ROOT / 'round3.4' / 'img3-part1-styled-motion.html'


def main() -> None:
    with CSV.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    dims = ['专业能力', '民族国家', '社会文化/性别']
    works: list[str] = []
    for row in rows:
        if row['作品'] not in works:
            works.append(row['作品'])
    moves = []
    for work in works:
        for dim in dims:
            row = next(item for item in rows if item['作品'] == work and item['维度'] == dim)
            moves.append({'init': float(row['上映期占比%']), 'curr': float(row['近年回看占比%'])})

    runtime = '''
<style data-purpose="reused-round39-dumbbell-motion-override">
/* Reused round3.9 motion semantics: each chart primitive owns its animation; no mask or canvas overlay exists. */
.dumbbell-svg .svg-axis,.dumbbell-svg .svg-axis-text,.dumbbell-svg .svg-film,.dumbbell-svg .svg-base,.dumbbell-svg line:not(.svg-axis):not(.svg-base),.dumbbell-svg circle,.chart-legend{animation:none!important;transform:none!important;opacity:0}
</style>
<script data-purpose="round39-controlled-simultaneous-svg-runtime">
(function(){
 const MOVES=__MOVES__;
 const svg=document.querySelector('.dumbbell-svg'); if(!svg) return;
 const scale=v=>260+(935-260)*v/100;
 const fade=(node,delay,duration=350)=>node.animate([{opacity:0},{opacity:1}],{delay,duration,fill:'forwards',easing:'ease-out'});
 const logo=document.querySelector('.chart-logo-1x1'), title=document.querySelector('.chart-title-1x1'), footer=document.querySelector('.chart-footer-1x1'), legend=document.querySelector('.chart-legend'), container=document.querySelector('.chart-container-1x1');
 fade(logo,100,550);fade(title,400,550);fade(footer,600,550);fade(legend,800,400);
 [...svg.querySelectorAll('.svg-axis,.svg-axis-text,.svg-film')].forEach(n=>fade(n,500));
 [...svg.querySelectorAll('.svg-base')].forEach(n=>fade(n,650,280));
 const coloredLines=[...svg.querySelectorAll('line')].filter(n=>['#17324D','#D94B3D','#C97B8D'].includes(n.getAttribute('stroke')));
 const circles=[...svg.querySelectorAll('circle')];
 coloredLines.forEach((line,i)=>{
   const m=MOVES[i],x0=scale(m.init),x1=scale(m.curr);line.setAttribute('x1',x0);line.setAttribute('x2',x0);line.style.opacity='1';
   line.animate([{x2:x0,opacity:0},{x2:x0,opacity:1,offset:.04},{x2:x1,opacity:1}],{delay:1000,duration:9000,fill:'forwards',easing:'linear'});
 });
 circles.forEach((dot,i)=>{
   const m=MOVES[Math.floor(i/2)],x0=scale(m.init),x1=scale(m.curr);dot.setAttribute('cx',x0);dot.style.opacity='1';
   if(i%2===0) dot.animate([{opacity:0,transform:'scale(.35)'},{opacity:1,transform:'scale(1)'}],{delay:900,duration:350,fill:'forwards',easing:'ease-out'});
   else dot.animate([{cx:x0,opacity:0,transform:'scale(.35)'},{cx:x0,opacity:1,transform:'scale(1)',offset:.04},{cx:x1,opacity:1,transform:'scale(1)'}],{delay:1000,duration:9000,fill:'forwards',easing:'linear'});
 });
 container.animate([{opacity:1},{opacity:0}],{delay:12500,duration:1000,fill:'forwards',easing:'linear'});
})();
</script>'''.replace('__MOVES__', json.dumps(moves, ensure_ascii=False))

    text = TARGET.read_text(encoding='utf-8')
    marker = '<style data-purpose="reused-round39-dumbbell-motion-override">'
    if marker in text:
        text = text.split(marker, 1)[0] + '</body></html>'
    text = text.replace('</body>', runtime + '</body>')
    TARGET.write_text(text, encoding='utf-8')
    print(f'Applied {len(moves)} controlled period-to-recent SVG trajectories to {TARGET.name}')


if __name__ == '__main__':
    main()
