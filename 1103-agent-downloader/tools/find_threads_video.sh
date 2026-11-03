#!/bin/bash
# 用 yt-dlp-threads 插件 --simulate 逐个验证候选帖子是否带视频
Y=/home/z/.venv/bin/yt-dlp
for pair in "mosseri DfA1glCj_5s" "mosseri De90Pbuk52l" "mosseri De921QjmXvg" "mosseri De2ynfJjTo3" "zuck DfNR0Psxewa" "zuck DeZtp-TkQHh" "zuck DeZtrvAEfEr"; do
  set -- $pair
  out=$($Y --simulate --no-warnings --print "HAS_VIDEO dur=%(duration)s title=%(title).40B" "https://www.threads.com/@$1/post/$2" 2>&1 | tail -1)
  echo "@$1/$2 -> $out"
done
