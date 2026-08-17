from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'round2.3'
R24 = ROOT / 'round2.4'
R34 = ROOT / 'round3.4'

# Timing is deliberately lifted from the existing 0811 round3.4 / round3.9 patterns:
# logo=.1s, title=.4s, footer=.6s, body=.5s, then content-specific element motion.
MOTION_CSS = r'''
<style data-purpose="reused-round34-round39-element-motion">
/* Reused timing grammar: elements fade themselves; no canvas masking or crop-reveal is used. */
@keyframes yzFade { from{opacity:0} to{opacity:1} }
@keyframes yzBloom { from{opacity:0;transform:scale(.72)} 70%{opacity:1;transform:scale(1.05)} to{opacity:1;transform:scale(1)} }
@keyframes yzGrowX { from{opacity:0;transform:scaleX(0)} to{opacity:1;transform:scaleX(1)} }
@keyframes yzPop { 0%{opacity:0;transform:scale(.35)} 75%{opacity:1;transform:scale(1.14)} 100%{opacity:1;transform:scale(1)} }
@keyframes yzType { to{opacity:1} }
.chart-logo-1x1,.chart-title-1x1,.chart-footer-1x1{opacity:0}.chart-logo-1x1{animation:yzFade .55s ease-out .1s forwards}.chart-title-1x1{animation:yzFade .55s ease-out .4s forwards}.chart-footer-1x1{animation:yzFade .55s ease-out .6s forwards}
/* 评论：海报自身淡入，文字在海报完成后逐字出现。 */
.review-card{opacity:0;animation:yzFade .35s ease-out .5s forwards}.review-poster{opacity:0;animation:yzFade .7s ease-out .65s forwards}.review-quote,.review-meta{opacity:1}.yz-type-char{opacity:0;display:inline;animation:yzType .02s linear forwards}.review-meta{opacity:0;animation:yzFade .35s ease-out 2.1s forwards}
/* 表1：从左上到右下，每个真实表头/单元格单独绽放。 */
.hm-table th,.hm-table td{opacity:0;transform:scale(.72);transform-origin:center}.hm-table .yz-bloom{animation:yzBloom .33s cubic-bezier(.18,.75,.25,1) forwards}.hm-legend{opacity:0;animation:yzFade .45s ease-out 3.8s forwards}
/* 表2：每行、每条堆叠段从自己的左侧成长；保留 round3.4 growRight 语义。 */
.sb-row{opacity:0;animation:yzFade .35s ease-out forwards}.sb-seg,.sb-bar{transform:scaleX(0);transform-origin:left center;animation:yzGrowX .65s ease-out forwards}.sb-label{opacity:0;animation:yzFade .28s ease-out forwards}
/* 表3：轴、作品标签、每一条路径和端点均为自身淡入/生长；不允许使用中心白色遮罩。 */
.dumbbell-svg .svg-axis,.dumbbell-svg .svg-axis-text,.dumbbell-svg .svg-film{opacity:0;animation:yzFade .35s ease-out .5s forwards}.dumbbell-svg .svg-base{opacity:0;animation:yzFade .3s ease-out .65s forwards}.dumbbell-svg .yz-db-line{transform-box:fill-box;transform-origin:left center;opacity:0;animation:yzGrowX .75s ease-out forwards}.dumbbell-svg .yz-db-dot{transform-box:fill-box;transform-origin:center;opacity:0;animation:yzPop .38s ease-out forwards}.chart-legend{opacity:0;animation:yzFade .4s ease-out 1.55s forwards}
</style>
'''

MOTION_JS = r'''
<script data-purpose="reused-round34-round39-motion-runtime">
(function(){
  const title = document.querySelector('.chart-title-1x1');
  const isComment = !!document.querySelector('.review-card');
  const isHeatmap = !!document.querySelector('.hm-table');
  const isStacked = !!document.querySelector('.sb-row');
  const isDumbbell = !!document.querySelector('.dumbbell-svg');
  if (isComment) {
    const quote = document.querySelector('.review-quote');
    if (quote && !quote.dataset.typed) {
      const text = quote.textContent; quote.textContent=''; quote.dataset.typed='true';
      [...text].forEach((char,index)=>{ const span=document.createElement('span'); span.className='yz-type-char'; span.textContent=char; span.style.animationDelay=(1.42+index*.045)+'s'; quote.appendChild(span); });
    }
  }
  if (isHeatmap) {
    const cells=[...document.querySelectorAll('.hm-table th,.hm-table td')];
    cells.forEach((cell,index)=>{ cell.classList.add('yz-bloom'); cell.style.animationDelay=(.62+index*.07)+'s'; });
  }
  if (isStacked) {
    document.querySelectorAll('.sb-row').forEach((row,i)=>{ row.style.animationDelay=(.58+i*.23)+'s'; row.querySelectorAll('.sb-seg,.sb-bar').forEach((seg,j)=>seg.style.animationDelay=(.8+i*.23+j*.06)+'s'); row.querySelectorAll('.sb-label').forEach(label=>label.style.animationDelay=(1.22+i*.23)+'s'); });
  }
  if (isDumbbell) {
    const svg=document.querySelector('.dumbbell-svg');
    const lines=[...svg.querySelectorAll('line')].filter(x=>x.getAttribute('stroke') && x.getAttribute('stroke')!=='#d8d8d8');
    const dots=[...svg.querySelectorAll('circle')];
    lines.forEach((line,i)=>{line.classList.add('yz-db-line'); line.style.animationDelay=(.85+(i%3)*.08+Math.floor(i/3)*.018)+'s';});
    dots.forEach((dot,i)=>{dot.classList.add('yz-db-dot'); dot.style.animationDelay=(1.25+(i%3)*.08+Math.floor(i/3)*.018)+'s';});
  }
})();
</script>
'''


def inject(source: Path, target: Path) -> None:
    text=source.read_text(encoding='utf-8')
    # The round2.3 file is copied byte-for-byte except for the reusable motion extension.
    text=text.replace('</head>', MOTION_CSS+'</head>')
    text=text.replace('</body>', MOTION_JS+'</body>')
    target.write_text(text,encoding='utf-8')


def main() -> None:
    for folder in [R24,R34]:
        folder.mkdir(exist_ok=True)
    # Sources remain self-contained by reusing the round2.3 local assets through a sibling symlink/copy.
    for folder in [R24,R34]:
        asset=folder/'assets'
        if asset.exists() or asset.is_symlink():
            if asset.is_symlink() or asset.is_file(): asset.unlink()
            else: shutil.rmtree(asset)
        shutil.copytree(SOURCE/'assets',asset)
    for source in sorted(SOURCE.glob('*-styled.html')):
        inject(source,R24/source.name)
        inject(source,R34/f'{source.stem}-motion.html')
    print(f'Generated {len(list(R24.glob("*.html")))} round2.4 and {len(list(R34.glob("*.html")))} round3.4 element-motion HTML files.')

if __name__=='__main__':
    main()
