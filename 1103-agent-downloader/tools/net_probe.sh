#!/bin/bash
# [A02] 网络连通性矩阵 —— 从沙盒探测 16 个关键域名的 HTTPS 可达性（6s 超时）
# 判读: HTTP=200-399 网络层可达; HTTP=4xx/5xx TCP通但被WAF/风控拦截; FAILED/timeout 网络层不可达
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
urls=(
 "https://github.com"
 "https://api.github.com"
 "https://raw.githubusercontent.com"
 "https://www.google.com"
 "https://www.youtube.com"
 "https://www.instagram.com"
 "https://x.com"
 "https://www.threads.net"
 "https://weibo.com"
 "https://m.weibo.cn"
 "https://www.douyin.com"
 "https://www.xiaohongshu.com"
 "https://www.bilibili.com"
 "https://api.bilibili.com"
 "https://pypi.org"
 "https://ipinfo.io/json"
)
for u in "${urls[@]}"; do
  r=$(curl -sS -o /dev/null -m 6 --connect-timeout 4 -A "$UA" \
      -w "HTTP=%{http_code} t=%{time_total}s ip=%{remote_ip}" "$u" 2>&1)
  echo "$u | $r"
done
echo "---- egress_ip_location ----"
curl -sS -m 6 "https://ipinfo.io/json" 2>&1 | head -c 300
echo
curl -sS -m 6 -A "$UA" "https://api.bilibili.com/x/web-interface/zone" 2>&1 | head -c 300
