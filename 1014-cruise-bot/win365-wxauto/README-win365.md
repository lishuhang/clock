# Windows 365 微信桥部署（cruise-bot Phase 2）

## 定位

可选增强模块。**主通道（WhatsApp/iMessage）完全不依赖本模块**，没有它一切照常。
价值场景：老公/家人在微信里的重要消息、群里通知，自动中转到船上（WhatsApp/iMessage）；
老公也可以从 WhatsApp 反向指挥云电脑发微信（「回微信 @联系人 内容」）。

云电脑全程使用你已有的 Windows 365 订阅，无新增费用。

## 部署步骤（约 15 分钟）

### 1. 防休眠（云电脑必须常开）

管理员 PowerShell：

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /change monitor-timeout-ac 15
```

注意：部分 Windows 365 策略会在断开会话后休眠——在 Intune/云电脑门户把"断开连接后"策略改为不休眠，
或保持一个 RDP 会话不断（用另一台设备挂着一个断开连接的会话也行）。

### 2. 登录微信客户端

- 下载 PC 版微信，扫码登录（老公的号）
- 设置：关闭主面板时最小化到托盘；消息通知开
- 保持前台可用（wxauto 需要窗口存在）

### 3. 安装 Python 依赖

```powershell
pip install wxauto requests
```

### 4. 配置脚本

编辑 `wxbridge.py` 顶部：

- `WORKER_URL` / `AGENT_KEY`（与 Worker secret 一致）
- `LISTEN`：要中转的联系人/群备注名列表

### 5. 注册计划任务（开机自启 + 掉线自动重启）

管理员 PowerShell：

```powershell
$script = "C:\cruisebot\wxbridge.py"
New-Item -ItemType Directory -Force -Path C:\cruisebot | Out-Null
Copy-Item .\wxbridge.py $script

$action  = New-ScheduledTaskAction -Execute "python.exe" -Argument $script `
           -WorkingDirectory "C:\cruisebot"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
           -ExecutionTimeLimit (New-TimeSpan -Days 365)
Register-ScheduledTask -TaskName "cruisebot-wxbridge" -Action $action -Trigger $trigger `
           -Settings $settings -RunLevel Highest -Force
Start-ScheduledTask -TaskName "cruisebot-wxbridge"
```

### 6. 验证

- 让 `LISTEN` 里的联系人在微信发一条消息 → 老公 WhatsApp 应收到「💬 微信[xx]：…」
- 老公从 WhatsApp 发「回微信 @文件传输助手 测试」→ 云电脑微信应发出
- Worker KV `wx_bridge_heartbeat` 时间戳每 30 秒刷新 = 桥活着

## 已知坑（诚实清单）

| 坑 | 对策 |
|---|---|
| 微信大版本更新破坏 wxauto UI 适配 | 尽力而为模块；挂了不影响主通道；等待 wxauto 社区适配 |
| 云电脑策略强制休眠 | 第 1 步电源策略 + 保持登录会话 |
| 微信多开/扫码过期 | 偶发需人工重新扫码；心跳停止即告警（README 主文档说明） |
| UI 自动化把窗口抢前台 | 云电脑无人用，无影响；本地物理机不要这样跑 |
| 合规 | 自动化的是自己账号、自用消息转发；微信 ToS 对 UI 自动化属灰色地带，风险自担（个人低频使用实践中无碍） |
