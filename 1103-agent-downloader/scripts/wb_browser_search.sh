#!/bin/bash
# 微博 agent-browser 游客搜索探针: 真浏览器走完访客护照JS -> 页面上下文内 fetch 容器搜索API
KW="${1:-马保国}"
echo "=== Step1: open m.weibo.cn (种游客cookie) ==="
agent-browser open "https://m.weibo.cn/" 2>&1 | head -3
agent-browser wait --load networkidle 2>&1 | head -2
agent-browser get url 2>&1 | head -2
agent-browser get title 2>&1 | head -2

echo "=== Step2: 导航到搜索页 ==="
QKW=$(python3 -c "import urllib.parse;print(urllib.parse.quote('$KW'))")
agent-browser open "https://m.weibo.cn/search?containerid=100103type%3D1%26q%3D${QKW}" 2>&1 | head -3
sleep 4
agent-browser get url 2>&1 | head -2

echo "=== Step3: 页面内 fetch 容器搜索API ==="
agent-browser eval "(async () => { const r = await fetch('/api/container/getIndex?containerid=100103type%3D1%26q%3D' + encodeURIComponent('${KW}') + '&page_type=searchall', {headers: {'X-Requested-With':'XMLHttpRequest','Accept':'application/json'}}); const j = await r.json(); if (j.ok !== 1) return 'API_FAIL ok=' + j.ok; const hits = []; for (const c of (j.data.cards || [])) { const mbs = c.mblog ? [c.mblog] : (c.card_group || []).map(g => g.mblog).filter(Boolean); for (const mb of mbs) { const pi = mb.page_info || {}; hits.push({id: mb.id, u: (mb.user||{}).screen_name, vid: !!(pi.media_info && (pi.media_info.stream_url || pi.media_info.playback_list)), t: (mb.text||'').replace(/<[^>]+>/g,'').slice(0,50)}); } } return JSON.stringify(hits.slice(0,15)); })()" 2>&1 | head -30

echo "=== Step4: cookie 概览 (是否拿到游客SUB) ==="
agent-browser eval "document.cookie.split(';').map(c=>c.trim().split('=')[0]).join(',')" 2>&1 | head -3
