#!/bin/bash
# 小红书 agent-browser 游客搜索探针: 真浏览器(游客) -> 搜索页 -> 抽结果链接(含xsec_token)
KW="${1:-万智牌}"
echo "=== Step1: open xiaohongshu.com 首页(游客) ==="
agent-browser open "https://www.xiaohongshu.com" 2>&1 | head -3
agent-browser wait --load networkidle 2>&1 | head -2
agent-browser get url 2>&1 | head -2
agent-browser get title 2>&1 | head -2

echo "=== Step2: 打开搜索结果页 ==="
QKW=$(python3 -c "import urllib.parse;print(urllib.parse.quote('$KW'))")
agent-browser open "https://www.xiaohongshu.com/search_result?keyword=${QKW}&source=web_explore_feed" 2>&1 | head -3
sleep 6
agent-browser get url 2>&1 | head -2
agent-browser get title 2>&1 | head -2

echo "=== Step3: 抽取笔记链接(含xsec_token) ==="
agent-browser eval "JSON.stringify([...new Set([...document.querySelectorAll('a[href*=explore], a[href*=search_result]')].map(a=>a.getAttribute('href')).filter(h=>h&&h.includes('/explore/')))].slice(0,12))" 2>&1 | head -20

echo "=== Step4: 页面特征(登录墙检测) ==="
agent-browser eval "JSON.stringify({loginModal: !!document.querySelector('.login-container, .sign-in-container, [class*=login-modal]'), bodyLen: document.body.innerText.length, hasKeyword: document.body.innerText.includes('${KW}'), textHead: document.body.innerText.replace(/\\s+/g,' ').slice(0,200)})" 2>&1 | head -10

echo "=== Step5: network 请求里的搜索API ==="
agent-browser network requests --filter "search" 2>&1 | head -10
