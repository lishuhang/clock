// Render pipeline: a/b -> PNG (element screenshot), c/anim -> MP4 (16s: 6s in + 4s hold + 6s out).
// Requires: playwright + ffmpeg-static installed, and `npx playwright install chromium` run once.
const { chromium } = require('C:/Users/james/.workbuddy/binaries/node/workspace/node_modules/playwright');
const ffmpegPath = require('C:/Users/james/.workbuddy/binaries/node/workspace/node_modules/ffmpeg-static');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const DIR = __dirname + '/';
const FRAME_DIR = 'C:/tmp/yzframes';
const FPS = 30, DUR = 6.0;

// ---- a-step 大图 -> PNG ----
const aFiles = ['img1-a-styled.html','img2-a-styled.html','img3-a-styled.html','wujing-a-styled.html','shenteng-a-styled.html'];
// ---- b-step 1:1 -> PNG ----
const bFiles = [
  'img1-part1-styled.html','img1-part2-styled.html','img1-part3-styled.html',
  'img2-part1-styled.html','img2-part2-styled.html','img2-part3-styled.html','img2-part4-styled.html',
  'img3-part1-styled.html','img3-part2-styled.html',
  'img4-part1-styled.html','img4-part2-styled.html','img4-part3-styled.html','img4-part4-styled.html',
  'img5-simultaneous-styled.html',
  'shenteng-part1-styled.html','shenteng-part2-styled.html','shenteng-part3-styled.html',
  'shenteng-part4-styled.html','shenteng-part5-styled.html','shenteng-part6-styled.html'
];
// ---- c-step anim -> MP4 ----
// Demos already contain the animation inline (round3.4-animations); new ones are *-anim.html.
const cFiles = [
  'img1-part1-styled.html','img1-part2-styled.html','img1-part3-styled.html',
  'img2-part1-styled.html','img2-part2-styled.html','img2-part3-styled.html','img2-part4-styled.html',
  'img4-part1-styled.html','img4-part2-styled.html','img4-part3-styled.html','img4-part4-styled.html',
  'img5-simultaneous-styled.html',
  'img3-part1-anim.html','img3-part2-anim.html',
  'shenteng-part1-anim.html','shenteng-part2-anim.html','shenteng-part3-anim.html',
  'shenteng-part4-anim.html','shenteng-part5-anim.html','shenteng-part6-anim.html'
];

function ensureDir(d){ if(!fs.existsSync(d)) fs.mkdirSync(d,{recursive:true}); }

async function shotPNG(page, selector, outPath){
  const el = await page.$(selector);
  await el.screenshot({ path: outPath });
}

async function recordMP4(page, selector, outPath){
  const el = await page.$(selector);
  ensureDir(FRAME_DIR);
  for(const f of fs.readdirSync(FRAME_DIR)) fs.unlinkSync(path.join(FRAME_DIR,f));
  const total = Math.round(FPS*DUR);
  for(let i=0;i<total;i++){
    await el.screenshot({ path: path.join(FRAME_DIR, `frame_${String(i).padStart(4,'0')}.png`) });
    await page.waitForTimeout(1000/FPS);
  }
  const last = path.join(FRAME_DIR, `frame_${String(total-1).padStart(4,'0')}.png`);
  execFileSync(ffmpegPath, ['-y','-framerate',String(FPS),'-i',path.join(FRAME_DIR,'frame_%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-preset','ultrafast', path.join(FRAME_DIR,'entrance.mp4')]);
  execFileSync(ffmpegPath, ['-y','-loop','1','-i',last,'-t','4','-r',String(FPS),'-c:v','libx264','-pix_fmt','yuv420p','-preset','ultrafast', path.join(FRAME_DIR,'static.mp4')]);
  execFileSync(ffmpegPath, ['-y','-i',path.join(FRAME_DIR,'entrance.mp4'),'-vf','reverse','-c:v','libx264','-pix_fmt','yuv420p','-preset','ultrafast', path.join(FRAME_DIR,'exit.mp4')]);
  const concat = path.join(FRAME_DIR,'concat.txt');
  fs.writeFileSync(concat, `file '${path.join(FRAME_DIR,'entrance.mp4')}'\nfile '${path.join(FRAME_DIR,'static.mp4')}'\nfile '${path.join(FRAME_DIR,'exit.mp4')}'\n`);
  execFileSync(ffmpegPath, ['-y','-f','concat','-safe','0','-i',concat,'-c:v','libx264','-pix_fmt','yuv420p','-preset','ultrafast', outPath]);
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport:{width:1200,height:1200}, deviceScaleFactor:1 });
  let done=0, fail=0;
  const mode = process.argv[2] || 'all';

  if(mode==='png'||mode==='all'){
    for(const f of [...aFiles, ...bFiles]){
      try{
        await page.goto('file://'+DIR+f, {waitUntil:'networkidle'});
        await page.evaluate(()=>document.fonts.ready);
        await page.waitForTimeout(300);
        const sel = f.includes('-a-') ? '.chart-container' : '.chart-container-1x1';
        const out = DIR + f.replace('-styled.html','.png');
        await shotPNG(page, sel, out);
        console.log('PNG ok: '+out); done++;
      }catch(e){ console.log('PNG FAIL '+f+': '+e.message); fail++; }
    }
  }
  if(mode==='mp4'||mode==='all'){
    for(const f of cFiles){
      try{
        await page.goto('file://'+DIR+f, {waitUntil:'networkidle'});
        await page.evaluate(()=>document.fonts.ready);
        await page.waitForTimeout(300);
        const out = DIR + (f.endsWith('-anim.html') ? f.replace('-anim.html','.mp4') : f.replace('-styled.html','.mp4'));
        await recordMP4(page, '.chart-container-1x1', out);
        console.log('MP4 ok: '+out); done++;
      }catch(e){ console.log('MP4 FAIL '+f+': '+e.message); fail++; }
    }
  }
  await browser.close();
  console.log(`\nDONE=${done} FAIL=${fail}`);
})();
