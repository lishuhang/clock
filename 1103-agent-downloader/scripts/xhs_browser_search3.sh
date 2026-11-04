#!/bin/bash
# 小红书探针3(游客线收尾): _webmsxyw签名 -> 浏览器内POST search/notes API
KW="${1:-万智牌}"

echo "=== A: cookie 域分布 ==="
agent-browser cookies --json 2>/dev/null | python3 -c "
import json,sys
try:
    d = json.load(sys.stdin)
    cookies = d if isinstance(d, list) else d.get('cookies', d.get('data', []))
    for c in cookies[:20]:
        print(c.get('domain',''), '|', c.get('name',''))
except Exception as e:
    print('parse_err', e)" 2>&1 | head -20

echo "=== B: 回 xiaohongshu.com 域(探索页, 看是否重定向) ==="
agent-browser open "https://www.xiaohongshu.com/explore" 2>&1 | head -3
sleep 4
agent-browser get url 2>&1 | head -2

echo "=== C: 签名函数检查 ==="
agent-browser eval "typeof window._webmsxyw" 2>&1 | head -2

echo "=== D: 签名+POST search/notes API ==="
agent-browser eval "(async () => { try { const uri='/api/sns/web/v1/search/notes'; const sid=((BigInt(Date.now())<<64n)+BigInt(Math.floor(Math.random()*2147483646))).toString(36); const data={keyword:'${KW}',page:1,page_size:20,search_id:sid,sort:'general',note_type:0,ext_flags:[],geo:'',image_formats:['jpg','webp','avif']}; const s=await window._webmsxyw(uri,data); const xs=s['X-s']||s['x-s']; const xt=String(s['X-t']||s['x-t']); const r=await fetch('https://edith.xiaohongshu.com'+uri,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json;charset=UTF-8','x-s':xs,'x-t':xt},body:JSON.stringify(data)}); const t=await r.text(); return 'HTTP'+r.status+' | '+t.slice(0,500); } catch(e) { return 'ERR '+e.message; } })()" 2>&1 | head -15
