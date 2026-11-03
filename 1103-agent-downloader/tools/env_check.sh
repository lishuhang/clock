#!/bin/bash
# 1103-agent-downloader 环境与连通性检查
echo "=== [1] 基础信息 ==="
echo "now: $(TZ=Asia/Hong_Kong date '+%F %T %z')"
uname -sr
df -h /home/z | tail -1
echo "=== [2] 工具 ==="
for c in git python3 pip3 curl jq ffmpeg ffprobe node; do
  if command -v $c >/dev/null 2>&1; then
    echo "$c: $($c --version 2>&1 | head -1)"
  else
    echo "$c: MISSING"
  fi
done
command -v yt-dlp >/dev/null 2>&1 && echo "yt-dlp: $(yt-dlp --version)" || echo "yt-dlp: MISSING"
python3 -c "import requests; print('py-requests:', requests.__version__)" 2>/dev/null || echo "py-requests: MISSING"
echo "proxy_env: $(env | grep -i -E '^(http|https|all)_proxy' | head -3 || echo none)"
echo "=== [3] 连通性 (HTTP code, 000=不可达) ==="
t() {
  code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 6 -m 12 \
    -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0' "$1" 2>/dev/null)
  echo "$2 -> $code"
}
t https://www.youtube.com/ youtube.com
t https://www.googlevideo.com/ googlevideo.com
t https://x.com/ x.com
t "https://cdn.syndication.twimg.com/tweet-result?id=1&token=a" twitter-syndication
t https://www.threads.net/ threads.net
t https://m.weibo.cn/ m.weibo.cn
t https://weibo.com/ weibo.com
t https://www.douyin.com/ douyin.com
t https://v.douyin.com/ v.douyin.com
t https://www.iesdouyin.com/ iesdouyin.com
t https://www.xiaohongshu.com/ xiaohongshu.com
t "https://api.bilibili.com/x/web-interface/popular" bili-api
t https://www.bilibili.com/ bilibili.com
t https://api.github.com/ api.github.com
t https://github.com/ github.com
t https://pypi.org/simple/ pypi
t https://api.fxtwitter.com/ fxtwitter-api
