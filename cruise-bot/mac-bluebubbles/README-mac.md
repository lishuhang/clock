# iMessage 通道部署（她的 Mac + BlueBubbles + Cloudflare Tunnel）

## 原理与定位

- **用途**：iMessage 备通道。WhatsApp 24h 服务窗口关闭时（她超过 23 小时没发消息），
  主动推送自动降级走这里——**iMessage 没有 24h 窗口，随时可推**，这是早报不漏发的主力保险。
- **原理**：BlueBubbles（开源，https://bluebubbles.app ）在 Mac 上驱动 macOS 自带 Messages.app 收发 iMessage。
  Mac 与她 iPhone 登录**同一 Apple ID**：bot 从 Mac 发出的 iMessage 同步显示在她的 iPhone；
  她在 iPhone 上的回复也会同步回 Mac，被 BlueBubbles webhook 推给 Worker 处理——闭环完成。
- **外网访问**：Cloudflare Tunnel（免费）把 Mac 的 BlueBubbles 端口发布到固定域名，无需公网 IP、无需开端口。
- **Bot 名义账号**：消息从她自己的 Apple ID 发出（显示为"你"/自聊天）。5 天临时用完全可接受；
  若介意，备选方案是把该 Mac 的 iMessage 退出她的账号、登录老公的 Apple ID（影响 FaceTime 同步，自行权衡）。

## 前提

- 她的 Mac：macOS 12+，接电源，iMessage 已登录 Apple ID 且能正常收发
- Mac 上 Messages.app 至少与她 iPhone 有一次 iMessage 会话（用于取 chatGuid）
- 一个 Cloudflare 账号（老公的即可），域名已托管 Cloudflare（lishuhang.me 可用）

## 步骤（约 20 分钟）

### 1. 安装 BlueBubbles Server

下载：https://bluebubbles.app/server/ （dmg 拖入 Applications）
首次打开按向导走完，关键项：

- **API Password**：设置一个强密码（记下来，后面填 Worker secret `BB_PASSWORD`）
- macOS 权限：按提示授予"完全磁盘访问 + 通知 + 自动化（Messages）"
- Settings → Connection：**记下本地端口**（默认 1234）

### 2. 取 chatGuid（发给老婆的消息目标）

BlueBubbles 运行状态下，Mac 终端执行（替换密码与端口）：

```bash
curl -s "http://localhost:1234/api/v1/chat?password=你的密码" | python3 -m json.tool | grep -E '"guid"|"participants"' | head -40
```

找到与她 iPhone 号码对应的 chatGuid（形如 `iMessage;+;+8613xxxxxxxxx` 或 `iMessage;-;+8613...`）。
**记下来** → Worker secret `WIFE_IGUID`。

自测发送：

```bash
curl -s -X POST "http://localhost:1234/api/v1/message/text?password=你的密码" \
  -H "content-type: application/json" \
  -d '{"chatGuid":"iMessage;+;+8613xxxxxxxxx","message":"🤖 cruise-bot iMessage 通道测试","method":"private-api"}'
```

她 iPhone 应立即收到（同 ID 同步）。

### 3. Cloudflare Tunnel

```bash
brew install cloudflared
cloudflared tunnel login          # 浏览器授权
cloudflared tunnel create cruise-imsg
cloudflared tunnel route dns cruise-imsg imsg.lishuhang.me   # 子域随意
```

写配置 `~/.cloudflared/config.yml`：

```yaml
tunnel: cruise-imsg
credentials-file: /Users/你的用户名/.cloudflared/xxxx.json   # create 命令输出的路径
ingress:
  - hostname: imsg.lishuhang.me
    service: http://localhost:1234
  - service: http_status:404
```

启动并验证：

```bash
cloudflared tunnel run cruise-imsg &
curl -s "https://imsg.lishuhang.me/api/v1/server/info?password=你的密码" | head -c 300
```

注册为系统服务（开机自启）：

```bash
sudo cloudflared service install
sudo launchctl enable system/com.cloudflare.cloudflared 2>/dev/null || true
```

### 4. 配置 BlueBubbles webhook（收消息 → Worker）

BlueBubbles Server → Settings → API → Webhook：

- URL：`https://cruise-bot.你的子域.workers.dev/webhook/imessage?p=BlueBubbles密码`
- Events：勾选 `new-message`（可选 `sent-message`）

### 5. 防睡眠（五天不能断）

```bash
# 接电源永不睡眠、磁盘不睡（sudo）
sudo pmset -c sleep 0 disksleep 0 displaysleep 10
# 若 MacBook 需要合盖：Apple Silicon macOS 12+ 可禁止合盖睡眠
sudo pmset -a disablesleep 1
```

同时建议：系统设置 → 节能 → "防止在显示器关闭时自动进入睡眠"；BlueBubbles 与 Messages 设为登录自启
（系统设置 → 通用 → 登录项）。

### 6. 监控脚本（可选但推荐）

`monitor.sh` 每 10 分钟探活 BlueBubbles，挂了自动拉起（launchd 托管）：

```bash
bash monitor.sh install   # 内含安装 launchd plist 的逻辑
```

### 7. Worker 侧联通验证

老公手机发 iMessage 指令给 bot（或让老婆发"帮助"）→ Worker 日志应出现
`/webhook/imessage` 请求；bot 回复经 Mac 发出，iPhone 收到。

## 断电/断网降级链

Mac 断线 → `sendIMessage` 失败 → Worker 自动写 KV 待发队列 → 下次她发消息补发；
WhatsApp 侧不受影响。README 主文档有完整降级链说明。

## 已知坑

| 坑 | 对策 |
|---|---|
| 合盖睡眠断通道 | `pmset disablesleep 1` 或不合盖 |
| private-api 发送方式被 macOS 更新限制 | BlueBubbles 设置里切 `apple-script` 方式（慢一点但稳） |
| 同 ID 消息 fromMe=true 分不清人/bot | bot 消息统一带 🤖 前缀，Worker 过滤 |
| 家庭宽断网 | Tunnel 出站连接，无需公网 IP；断网即降级，恢复自动续上 |
| Messages 提示"重新登录" | 出发前一周内重启一次 Mac 并确认 iMessage 在线 |
