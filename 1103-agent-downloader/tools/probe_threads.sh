#!/bin/bash
# Threads 目标发现: Googlebot UA 抓知名账号主页 SSR, 找 /post/ 链接与 video_versions
UA_GB="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
for h in mosseri zuck threadsapp; do
  curl -sL -m 20 -A "$UA_GB" "https://www.threads.com/@$h" -o /tmp/th_$h.html \
    -w "[$h] http=%{http_code} bytes=%{size_download} final=%{url_effective}\n"
  echo "  post链接: $(grep -oE '/@[A-Za-z0-9_.]+/post/[A-Za-z0-9_-]+' /tmp/th_$h.html | sort -u | head -3 | tr '\n' ' ')"
  echo "  video_versions: $(grep -c 'video_versions' /tmp/th_$h.html)"
done
