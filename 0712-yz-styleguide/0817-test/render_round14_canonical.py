from __future__ import annotations

import base64
import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import websocket

ROOT=Path(__file__).resolve().parent
R14=ROOT/'round1.4'
PORT=9358
PROFILE=Path('/tmp/round14-canonical-profile')


def fetch(url: str):
    with urllib.request.urlopen(url,timeout=1) as r:
        return json.loads(r.read().decode())


def call(ws, counter: list[int], method: str, params: dict|None=None):
    counter[0]+=1; ident=counter[0];ws.send(json.dumps({'id':ident,'method':method,'params':params or {}}))
    while True:
        msg=json.loads(ws.recv())
        if msg.get('id')==ident:
            if 'error' in msg: raise RuntimeError(msg['error'])
            return msg.get('result',{})


def main():
    if PROFILE.exists(): shutil.rmtree(PROFILE)
    proc=subprocess.Popen(['chromium','--headless=new',f'--remote-debugging-port={PORT}',f'--user-data-dir={PROFILE}','--remote-allow-origins=*','--no-sandbox','--disable-gpu','--hide-scrollbars','--force-device-scale-factor=1','--window-size=1100,5000','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try: pages=fetch(f'http://127.0.0.1:{PORT}/json'); break
            except Exception: time.sleep(.1)
        else: raise RuntimeError('Chromium did not open debug endpoint')
        page=next(p for p in pages if p.get('type')=='page')
        ws=websocket.create_connection(page['webSocketDebuggerUrl'],timeout=20)
        seq=[0];call(ws,seq,'Page.enable');call(ws,seq,'Runtime.enable')
        report=[]
        for html in sorted(R14.glob('*-styled.html')):
            call(ws,seq,'Page.navigate',{'url':html.resolve().as_uri()+f'?v={time.time_ns()}'})
            time.sleep(.7)
            result=call(ws,seq,'Runtime.evaluate',{'expression':'''(async()=>{await document.fonts.ready;await new Promise(r=>setTimeout(r,120));const c=document.querySelector('.chart-container');const pass=yzSelfCheck();return {pass,errors:window.yzSelfCheckErrors||[],banner:document.getElementById('yz-selfcheck-banner').textContent,svgUse:document.querySelector('.yz-watermark svg use')?.getAttribute('href'),fontReady:document.fonts.check('900 34px AliPuHui'),rect:(()=>{const r=c.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})(),style:{watermark:getComputedStyle(document.querySelector('.yz-watermark svg')).width,opacity:getComputedStyle(document.querySelector('.yz-watermark svg')).opacity,logo:getComputedStyle(document.querySelector('.yz-logo-svg')).height,font:getComputedStyle(document.body).fontFamily}}})()''','awaitPromise':True,'returnByValue':True})
            value=result['result']['value']
            if not value['pass']: raise RuntimeError(f'Canonical self-check failed for {html.name}: {value}')
            rect=value['rect'];shot=call(ws,seq,'Page.captureScreenshot',{'format':'png','clip':{'x':rect['x'],'y':rect['y'],'width':rect['width'],'height':rect['height'],'scale':1},'fromSurface':True})
            png=html.with_suffix('.png');png.write_bytes(base64.b64decode(shot['data']))
            report.append({'file':html.name,'png':png.name,**value})
            print('Rendered',png.name,value['rect'])
        (R14/'canonical_render_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        ws.close()
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill()

if __name__=='__main__':main()
