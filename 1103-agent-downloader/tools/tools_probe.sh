#!/bin/bash
# [A05] 安装 yt-dlp + gallery-dl 到现有 venv，报告版本与 8 平台 extractor 覆盖（不实抓）
PY=/home/z/.venv/bin
echo "== pip install (quiet) =="
$PY/pip install -q yt-dlp gallery-dl 2>&1 | tail -3
echo "== versions =="
echo "yt-dlp: $($PY/yt-dlp --version 2>&1)"
echo "gallery-dl: $($PY/gallery-dl --version 2>&1)"
echo "== yt-dlp extractor coverage =="
LE=$($PY/yt-dlp --list-extractors 2>/dev/null)
echo "total extractors: $(echo "$LE" | wc -l)"
for kw in YouTube Instagram Twitter Threads Weibo Douyin TikTok XiaoHongShu RedNote BiliBili; do
  n=$(echo "$LE" | grep -ic "$kw")
  echo "yt-dlp | $kw -> $n"
  echo "$LE" | grep -i "$kw" | head -3 | sed 's/^/    /'
done
echo "== gallery-dl extractor coverage =="
GL=$($PY/gallery-dl --list-extractors 2>/dev/null)
echo "total extractors: $(echo "$GL" | wc -l)"
for kw in instagram threads twitter weibo bilibili douyin xiaohongshu rednote; do
  n=$(echo "$GL" | grep -ic "$kw")
  echo "gallery-dl | $kw -> $n"
  echo "$GL" | grep -i "$kw" | head -4 | sed 's/^/    /'
done
