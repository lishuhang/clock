#!/bin/bash
# cruise-bot — BlueBubbles 探活守护（macOS launchd）
# 用法：bash monitor.sh install | uninstall | run
# 每 600 秒探测一次 BlueBubbles API，失败自动尝试重启 cloudflared（BlueBubbles 本体为 GUI 应用，
# launchd 拉起 GUI 应用不可靠，主要守护 Tunnel 断线——BlueBubbles 建议放"登录项"自启）。

set -u
BB_PORT="${BB_PORT:-1234}"
BB_PASSWORD="${BB_PASSWORD:-}"          # 环境变量或留空探测 404 也算"活着"
LABEL="com.cruisebot.monitor"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG="$HOME/Library/Logs/cruisebot-monitor.log"

probe() {
  local code
  if [ -n "$BB_PASSWORD" ]; then
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
      "http://localhost:${BB_PORT}/api/v1/server/info?password=${BB_PASSWORD}")
  else
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
      "http://localhost:${BB_PORT}/")
  fi
  # 200=OK；401/403=服务活着只是鉴权错（也算活）
  [ "$code" = "200" ] || [ "$code" = "401" ] || [ "$code" = "403" ]
}

run_once() {
  echo "$(date '+%F %T') probe start" >> "$LOG"
  if probe; then
    echo "$(date '+%F %T') BlueBubbles OK" >> "$LOG"
  else
    echo "$(date '+%F %T') BlueBubbles 不可达 → 重启 cloudflared" >> "$LOG"
    launchctl kickstart -k "gui/$(id -u)/com.cloudflare.cloudflared" 2>>"$LOG" \
      || (pgrep cloudflared | xargs kill 2>>"$LOG"; nohup cloudflared tunnel run cruise-imsg >>"$LOG" 2>&1 &)
    # 再探一次本机端口，仍不通则提示（GUI 应用需要人工打开）
    sleep 20
    if probe; then
      echo "$(date '+%F %T') 恢复 OK" >> "$LOG"
    else
      echo "$(date '+%F %T') 仍不可达：请人工打开 BlueBubbles Server（可能 GUI 未启动）" >> "$LOG"
      osascript -e 'display notification "BlueBubbles 不可达，请检查！" with title "cruise-bot"' 2>>"$LOG"
    fi
  fi
}

install() {
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string><string>$(cd "$(dirname "$0")" && pwd)/monitor.sh</string><string>run</string>
  </array>
  <key>StartInterval</key><integer>600</integer>
  <key>RunAtLoad</key><true/>
  <key>EnvironmentVariables</key><dict>
    <key>BB_PORT</key><string>${BB_PORT}</string>
    <key>BB_PASSWORD</key><string>${BB_PASSWORD}</string>
  </dict>
</dict></plist>
EOF
  launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  echo "已安装并启动：$PLIST（日志：$LOG）"
}

uninstall() {
  launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null
  rm -f "$PLIST"
  echo "已卸载"
}

case "${1:-run}" in
  install) install ;;
  uninstall) uninstall ;;
  run) run_once ;;
  *) echo "用法：bash monitor.sh install|uninstall|run" ;;
esac
