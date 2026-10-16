// wechat_notify.js — Android pad 微信通知桥（AutoX.js，免 root，免费）
// =====================================================================
// 原理：Android 系统级通知监听（NotificationListenerService）捕获微信新消息
//       通知 → HTTP POST 到 cruise-bot Worker → 转发到 WhatsApp/iMessage。
//       相比 PC 微信 UI 自动化（wxauto），通知监听是系统 API，不依赖微信界面结构，
//       微信升级基本不影响；微信 Pad 端登录可与手机端长期共存（系统支持）。
//
// 部署（在 pad 上）：
//   1. 装 AutoX.js（开源，GitHub Releases 下载 apk）
//   2. 给 AutoX.js 授予：通知使用权（设置→通知使用权）、后台运行/电池不限制
//   3. 把本脚本放进 AutoX.js 脚本目录，运行
//   4. （可选）AutoX.js 设置里配置"开机自启"
//
// 边界与诚实说明：
//   - 通知文本可能被微信折叠（如"发来 3 条消息"），适合中转单聊/关键群，
//     不适合全文存档；需要全文可用聊天页打开后再看
//   - 部分系统在强后台限制下会杀监听服务：把 AutoX.js 加入电池白名单+最近任务锁定

const WORKER_URL = "https://cruise-bot.lishuhang.workers.dev";
const AGENT_KEY = "填入你的 AGENT_KEY";
const PUSH_WHO = "owner";       // 中转给岸上（老公）；改 "wife" 直接推船上
const FORWARD_KEYWORDS = null;  // 例：["爸", "妈", "家"] 只转发含关键词的通知；null=全部
const MUTE_SELF = true;         // 忽略"自己发出"的通知

function forward(title, text) {
  const body = `💬 Pad微信 [${title}]\n${text}`.slice(0, 1400);
  try {
    const r = http.postJson(`${WORKER_URL}/send`, { text: body, who: PUSH_WHO, channel: "auto" }, {
      headers: { "x-agent-key": AGENT_KEY },
    });
    console.log(`转发: ${title} → HTTP ${r.statusCode}`);
  } catch (e) {
    console.error("转发失败:", e);
  }
}

events.observeNotification(function (n) {
  try {
    const pkg = n.getPackageName();
    if (pkg !== "com.tencent.mm") return;          // 只要微信
    const title = String(n.getTitle() || "");
    const text = String(n.getText() || "");
    if (!text) return;
    if (MUTE_SELF && /我:/.test(text.slice(0, 8))) return;
    if (FORWARD_KEYWORDS && !FORWARD_KEYWORDS.some(k => (title + text).includes(k))) return;
    forward(title, text);
  } catch (e) {
    console.error("notification handler:", e);
  }
});

console.log("微信通知桥已启动，监听中…");
// 每 10 分钟心跳到 Worker（KV 里可查 pad 存活）
setInterval(function () {
  try {
    http.postJson(`${WORKER_URL}/state`, { key: "pad_bridge_heartbeat", value: String(Date.now()), ttl: 86400 }, {
      headers: { "x-agent-key": AGENT_KEY },
    });
  } catch (e) {}
}, 10 * 60 * 1000);
