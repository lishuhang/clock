#!/bin/bash
# 同步 /home/z/my-project/scripts/ 下脚本到仓库 tools/ 并 commit+push
# 用法: gh_sync.sh "提交说明"    (token 从文件读, 不回显)
set -u
TOKEN=$(cat /home/z/my-project/scripts/.ghtoken 2>/dev/null || cat /home/z/my-project/.secrets/github_token 2>/dev/null)
REPO=/home/z/my-project/clock
DEST=$REPO/1103-agent-downloader
[ -z "$TOKEN" ] && { echo "no token"; exit 1; }
mkdir -p "$DEST/tools" "$DEST/logs"
cp -f /home/z/my-project/scripts/*.py "$DEST/tools/" 2>/dev/null
cp -f /home/z/my-project/scripts/*.sh "$DEST/tools/" 2>/dev/null
chmod +x "$DEST/tools/"*.sh 2>/dev/null
cd "$REPO" || exit 1
git remote set-url origin "https://x-access-token:${TOKEN}@github.com/lishuhang/clock.git" 2>/dev/null
git add 1103-agent-downloader >/dev/null 2>&1
MSG="$(TZ=Asia/Hong_Kong date '+%F %T') $*"
if git diff --cached --quiet 2>/dev/null; then
  echo "(nothing to commit)"
else
  if git -c user.name=z-ai-agent -c user.email=z-ai-agent@users.noreply.github.com commit -m "$MSG" >/dev/null 2>&1; then
    echo "committed: $MSG"
  fi
fi
git push origin HEAD 2>&1 | sed "s/${TOKEN}/****/g" | tail -2
