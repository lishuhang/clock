#!/bin/bash
# 探测候选目标存活情况：抖音示例链接 / 人民网douyin主页 / threads候选帖
UA_IOS="Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
UA_GB="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

echo "== [1] 抖音短链 v.douyin.com/kcvMpuN/ 解析 =="
curl -s -o /dev/null -m 15 -A "$UA_IOS" \
  -w "http=%{http_code} redirect=%{redirect_url}\n" "https://v.douyin.com/kcvMpuN/"

echo "== [2] 抖音 aweme 7604129988555574538 分享页 SSR =="
curl -s -m 15 -A "$UA_IOS" "https://www.iesdouyin.com/share/video/7604129988555574538/" -o /tmp/dy_probe.html -w "http=%{http_code} bytes=%{size_download}\n"
grep -c "_ROUTER_DATA" /tmp/dy_probe.html 2>/dev/null | head -1 | sed 's/^/_ROUTER_DATA出现次数: /'
grep -o '"desc":"[^"]\{0,60\}' /tmp/dy_probe.html 2>/dev/null | head -2

echo "== [3] 人民网 douyin 用户分享页(找近期视频ID) =="
curl -s -m 15 -A "$UA_IOS" "https://www.iesdouyin.com/share/user/MS4wLjABAAAA8U_l6rBzmy7bcy6xOJel4v0RzoR_wfAubGPeJimN__4" -o /tmp/dy_user.html -w "http=%{http_code} bytes=%{size_download}\n"
grep -oE "(share/video|aweme_id)/?[0-9]{15,}" /tmp/dy_user.html 2>/dev/null | head -5

echo "== [4] Threads 候选帖(插件 simulate 验证是否有视频) =="
/home/z/.venv/bin/yt-dlp --simulate --no-warnings --print "TITLE=%(title)s|UP=%(uploader)s|DUR=%(duration)s" \
  "https://www.threads.com/@iamreinyourheart/post/DV-Oc3uAbDe" 2>&1 | tail -3

echo "== [5] Threads @zuck 主页 Googlebot SSR(找 post 链接) =="
curl -s -m 15 -A "$UA_GB" "https://www.threads.net/@zuck" -o /tmp/th_zuck.html -w "http=%{http_code} bytes=%{size_download}\n"
grep -oE "post/[A-Za-z0-9_-]{8,15}" /tmp/th_zuck.html 2>/dev/null | sort -u | head -5
