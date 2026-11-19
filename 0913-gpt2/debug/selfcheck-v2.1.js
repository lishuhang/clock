#!/usr/bin/env node
// v2.1 worker 结构自检：语法 + 关键改动点 + 遗留引用扫描
const fs = require('fs');
const path = require('path');
const f = path.join(__dirname, '..', 'gpt2-worker-kmage-v2.1.js');
const s = fs.readFileSync(f, 'utf8');
let fail = 0;
const check = (name, ok) => { console.log((ok ? 'PASS' : 'FAIL') + '  ' + name); if (!ok) fail++; };

// 1. 关键改动点
check('VERSION backend = 2.1', s.includes("const VERSION = 'kmage-kdr-rapi-2.1'"));
check('VERSION frontend = 2.1', s.includes("var VERSION='kmage-kdr-rapi-2.1'"));
check('<title> 2.1', s.includes('<title>AI生图 · kmage-kdr-rapi-2.1</title>'));
check('header ver badge 2.1', s.includes('<span class="ver">kmage-kdr-rapi-2.1</span>'));
check('refSection 容器', s.includes('id="refSection"'));
check('refDisabledHint 在容器外', (() => {
  const w = s.indexOf('id="refSection"'), h = s.indexOf('id="refDisabledHint"'), cEnd = s.indexOf('</div>', s.indexOf('id="refList"'));
  return w > -1 && h > -1 && h > cEnd; // hint 出现在 refList 所在容器闭合之后
})());
check('qualityCell 标记', s.includes('id="qualityCell"'));
check("refSection rapi 隐藏", s.includes("$('refSection').style.display=(channel==='rapi')?'none':'block'"));
check("sizeRowKdr 仅 kdr", s.includes("$('sizeRowKdr').style.display=(channel==='kdr')?'block':'none'"));
check("qualityCell rapi 隐藏", s.includes("$('qualityCell').style.display=(channel==='rapi')?'none':'block'"));
check('Gift Key UI 已移除', !s.includes('id="giftKeyAlias"') && !s.includes('id="btnRefreshGift"'));
check('renderGiftLine no-op', s.includes('function renderGiftLine(){/* v2.1 no-op */}'));
check('btnRefreshGift 绑定已移除', !s.includes("$('btnRefreshGift').addEventListener"));
check('自定义 Key textarea 保留', s.includes('id="kdrCustomKeys"'));
check('kdrStatePill 状态徽章', s.includes('id="kdrStatePill"'));
check('renderBadge rapi 分支', s.includes("rapi · 免费试用';b.className='badge'"));
check('renderBadge kdr 待命', s.includes('kdr · 待命'));
check('renderSettings 回填 textarea', s.includes("if(tk&&document.activeElement!==tk)tk.value=(kdrState.customKeys||[]).join(String.fromCharCode(10))"));
check('notes_v2_1 存在', s.includes('notes_v2_1'));
check('时间线 v2.1（本版）', s.includes('kmage-kdr-rapi-2.1（本版）'));
check('时间线 v2.0 去本版标记', s.includes('<b>kmage-kdr-rapi-2.0</b>：新增'));
check('通知三通道文案', s.includes('三通道生效'));
check('init Gift 预取已移除', !s.includes("if(channel==='kdr'){ensureGiftKey(true).then(function(){renderGiftLine()})"));
check('switch Gift 预取已移除', !s.includes("if(c==='kdr'){ensureGiftKey(true).then(renderGiftLine)"));
check('generateKdr 内 ensureGiftKey 保留（质询解销刷新路径）', (s.match(/ensureGiftKey\(true\)/g) || []).length === 2);
check('rapi prompt 必填', s.includes("(channel==='rapi'||!refCount())"));
check('generateRapi 防御兜底保留', s.includes('试用通道仅支持文生图（'));
check('头部注释 三通道', s.includes('上游: 三通道（kmage 站点 / kdr 站点 / Canvas 站点 RouterAPI）'));
check('kdr mode 更新（付费 Key 通畅）', s.includes('自定义付费 Key 路径通畅'));
check('rapi mode 更新（参考图禁用）', s.includes('v2.1: 仅文生图——选择该通道时参考图输入区整体禁用'));

// 2. 模板字符串完整性：HTML_CONTENT 反引号配对（粗检：数量为偶数且首尾存在）
const ticks = (s.match(/`/g) || []).length;
check('反引号配对（偶数个 ' + ticks + '）', ticks % 2 === 0);
// 3. 无 CR/LF 转义序列（kd-v2.2 工程坑）
check('无 \\n/\\r/\\t 转义序列（模板内坑）', !/\\[nrt]/.test(s));
// 4. 引用的 DOM id 都有对应元素或已守卫（抽查新增 id）
for (const id of ['refSection', 'refDisabledHint', 'qualityCell', 'kdrStatePill', 'kdrCustomKeys']) {
  check(`id ${id} 定义存在`, s.includes(`id="${id}"`));
}
console.log(fail ? `\n${fail} 项未通过` : '\n全部结构自检通过');
process.exit(fail ? 1 : 0);
