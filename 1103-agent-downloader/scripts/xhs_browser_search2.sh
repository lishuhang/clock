#!/bin/bash
# 小红书探针2: rednote国际版搜索页 + _webmsxyw签名函数 + 浏览器内调search/notes API
KW="${1:-万智牌}"
QKW=$(python3 -c "import urllib.parse;print(urllib.parse.quote('$KW'))")

echo "=== A: rednote.com 国际版搜索页 ==="
agent-browser open "https://www.rednote.com/search_result?keyword=${QKW}&source=web_explore_feed" 2>&1 | head -3
sleep 6
agent-browser get url 2>&1 | head -2
agent-browser eval "JSON.stringify({errPage: location.href.includes('website-login/error'), bodyLen: document.body.innerText.length, hasKW: document.body.innerText.includes('${KW}'), links: [...new Set([...document.querySelectorAll('a[href*=explore]')].map(a=>a.getAttribute('href')))].length})" 2>&1 | head -8

echo "=== B: 签名函数存在性 ==="
agent-browser eval "JSON.stringify({hasSign: typeof window._webmsxyw, keys: Object.keys(window).filter(k=>k.toLowerCase().includes('web')||k.toLowerCase().includes('sign')).slice(0,10)})" 2>&1 | head -6

echo "=== C: 抽取搜索结果链接 ==="
agent-browser eval "JSON.stringify([...new Set([...document.querySelectorAll('a[href*=explore], a[href*=discovery]')].map(a=>a.getAttribute('href')).filter(Boolean))].slice(0,10))" 2>&1 | head -15

echo "=== D: 页面文本头部(看内容还是风控页) ==="
agent-browser eval "document.body.innerText.replace(/\s+/g,' ').slice(0,300)" 2>&1 | head -8
