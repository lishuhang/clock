#!/bin/bash
# [A01] 环境探针 —— 只读检测本沙盒可用工具链。输出已压缩，避免 token 浪费。
sec() { echo; echo "===== $1 ====="; }

sec "DATE_UTC"; date -u "+%Y-%m-%dT%H:%M:%SZ"
sec "OS"; uname -sr; grep -m1 PRETTY /etc/os-release 2>/dev/null
sec "CPU_MEM"; echo "cores=$(nproc)"; free -h | awk 'NR<=2'
sec "PYTHON"; python3 --version 2>&1; python3 -c "import sys; print(sys.executable)" 2>&1
sec "NODE"; node --version 2>&1 || echo MISSING
sec "GIT"; git --version 2>&1
sec "CURL"; curl --version 2>/dev/null | head -1
sec "FFMPEG"; ffmpeg -version 2>/dev/null | head -1 || echo MISSING
sec "YT-DLP(system)"; yt-dlp --version 2>/dev/null || echo MISSING
sec "GALLERY-DL(system)"; gallery-dl --version 2>/dev/null || echo MISSING
sec "INSTALOADER"; instaloader --version 2>/dev/null || echo MISSING
sec "YOU-GET"; you-get --version 2>/dev/null || echo MISSING
sec "LUX"; lux --version 2>/dev/null || echo MISSING
sec "BBDOWN"; BBDown --version 2>/dev/null || echo MISSING
sec "GH_CLI"; gh --version 2>/dev/null | head -1 || echo MISSING
sec "PIP3"; pip3 --version 2>&1 | head -1
sec "VENV_CAPABLE"; python3 -m venv --help >/dev/null 2>&1 && echo yes || echo no
sec "PROXY_ENV"; env | grep -iE "proxy" || echo none
sec "PIP_PKGS_MATCH"; pip3 list 2>/dev/null | grep -iE "yt-dlp|gallery|instaloader|requests|httpx|playwright|selenium|execjs" || echo none
sec "PLAYWRIGHT_BROWSERS"; ls "$HOME/.cache/ms-playwright" 2>/dev/null || echo none
sec "CHROME_BINARIES"; command -v google-chrome chromium chromium-browser 2>/dev/null || echo none
