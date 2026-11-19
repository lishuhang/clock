#!/usr/bin/env node
// v2.2 worker 结构自检：语法 + 关键改动点 + 遗留引用扫描（沿袭 v2.1 版式）
const fs = require('fs');
const path = require('path');
const f = path.join(__dirname, '..', 'gpt2-worker-kmage-v2.2.js');
const s = fs.readFileSync(f, 'utf8');
let fail = 0;
const check = (name, ok) => { console.log((ok ? 'PASS' : 'FAIL') + '  ' + name); if (!ok) fail++; };

// 1. 版本号（6 处）
check('VERSION backend = 2.2', s.includes("const VERSION = 'kmage-kdr-rapi-zimage-2.2'"));
check('VERSION frontend = 2.2', s.includes("var VERSION='kmage-kdr-rapi-zimage-2.2'"));
check('<title> 2.2', s.includes('<title>AI生图 · kmage-kdr-rapi-zimage-2.2</title>'));
check('header ver badge 2.2', s.includes('<span class="ver">kmage-kdr-rapi-zimage-2.2</span>'));
check('文件头注释 v2.2', s.includes('// gpt2-worker-kmage-v2.2.js'));
check('版本注释 v2.2', s.includes('// 版本: kmage-kdr-rapi-zimage-2.2 (2026-11-19)'));

// 2. zimage 后端
check('ZIMAGE_UPSTREAM 常量', s.includes("const ZIMAGE_UPSTREAM = 'https://zimage.run'"));
check('ZIMAGE_FILES_PREFIX 常量', s.includes("const ZIMAGE_FILES_PREFIX = 'https://files.zimage.run/'"));
check('handleZimageProxy 存在', s.includes('async function handleZimageProxy(request, url)'));
check('handleZimageImage 存在', s.includes('async function handleZimageImage(request, url)'));
check('generate 路由', s.includes("if (sub === '/generate' && request.method === 'POST')"));
check('task 路由 + uuid 白名单', s.includes("/^[A-Za-z0-9_-]{1,64}$/.test(uuid)"));
check('batchSize 强制 1', s.includes('batchSize: 1'));
check('模型白名单 8 个', (s.match(/'turbo', 'qwen-image-2-1', 'ernie-image-turbo', 'flux2-klein-9b', 'flux-3-image-klein', 'beyond-reality', 'redcraft', 'dark-beast'/g) || []).length >= 1);
check('img 代理前缀限制', s.includes('target.indexOf(ZIMAGE_FILES_PREFIX) !== 0'));
check('路由分发 /api/zimage', s.includes("url.pathname === '/api/zimage' || url.pathname.startsWith('/api/zimage/')"));
check('路由分发 /zimage/img', s.includes("url.pathname === '/zimage/img'"));
check('healthz channels 含 zimage', s.includes("channels: ['kmage', 'kdr', 'rapi', 'zimage']"));
check('healthz zimage_upstream', s.includes('zimage_upstream: ZIMAGE_UPSTREAM'));

// 3. zimage 前端
check('通道下拉 zimage 选项', s.includes('<option value="zimage">zimage</option>'));
check('KMODELS_ZIMAGE 定义', s.includes('var KMODELS_ZIMAGE=['));
check('ZIMAGE_DEFAULT_MODEL', s.includes("var ZIMAGE_DEFAULT_MODEL='turbo'"));
check('zimageSizeFor 映射', s.includes('function zimageSizeFor(ratio)'));
check('RATIO_OPTIONS_ZIMAGE 裁剪', s.includes('var RATIO_OPTIONS_ZIMAGE=[[') && s.includes("['3:2','3:2 横向（768×512）']"));
check('applyRatioOptions 调用于 applyChannel', s.includes('  applyRatioOptions();'));
check('refSection rapi+zimage 隐藏', s.includes("var noRef=(channel==='rapi'||channel==='zimage')"));
check('refDisabledHint 动态文案（zimage 分支）', s.includes('当前通道（zimage 匿名免费）不支持参考图'));
check('qualityCell rapi+zimage 隐藏', s.includes("$('qualityCell').style.display=noRef?'none':'block'"));
check('zimageHint 元素', s.includes('id="zimageHint"') && s.includes("$('zimageHint').style.display=(channel==='zimage')?'block':'none'"));
check('generateZimage 流程', s.includes('async function generateZimage(histEntry,runId,t0)'));
check('zimageApi 代理封装', s.includes('function zimageApi(path,body,runId)'));
check('zimagePollTask 轮询', s.includes('async function zimagePollTask(uuid,runId)'));
check('zimageFetchB64 直连优先', s.includes('async function zimageFetchB64(u,runId)'));
check('DAILY_LIMIT 中文兜底文案', s.includes('zimage 匿名每日额度已用完'));
check('生图入口分派 zimage', s.includes("else if(channel==='zimage')await generateZimage(histEntry,currentRunId,t0)"));
check('提示词必填含 zimage', s.includes("(channel==='rapi'||channel==='zimage')"));
check('渲染徽章 zimage 分支', s.includes('zimage · 免费无登录'));
check('生成按钮文案 zimage', s.includes('开始生成（zimage · 免费无登录）'));
check('下载前缀 zimage_', s.includes("'zimage_'"));
check('switchChannel zimage 就绪日志', s.includes("if(c==='zimage'){appLog('[zimage] 通道就绪"));

// 4. v2.0 遗留 bug 修复
check('loadChannel 白名单含 rapi+zimage', s.includes("if(c==='kdr'||c==='kmage'||c==='rapi'||c==='zimage')channel=c"));
check('广播恢复含 zimage', s.includes("data.channel==='rapi'||data.channel==='zimage'"));
check('formState model 含 zimage', s.includes("model:{kmage:'',kdr:'',rapi:'',zimage:''}"));

// 5. 文案与文档
check('通知开关四通道', s.includes('四通道生效'));
check('about 名称四通道', s.includes('四通道'));
check('channels.zimage 自描述', s.includes('zimage: {'));
check('notes_v2_2 存在', s.includes('notes_v2_2'));
check('时间线 v2.2（本版）', s.includes('kmage-kdr-rapi-zimage-2.2（本版）'));
check('时间线 v2.1 去本版标记', s.includes('<b>kmage-kdr-rapi-2.1</b>：三通道复检'));
check('时间线 v2.1 加勘误回注', s.includes('zimage.run 当时被判「无 API 纯网页」，v2.2 已勘误接入'));
check('头部注释 zimage 通道块', s.includes('[zimage]（v2.2 新增）'));
check('关于路由表含 /api/zimage', s.includes('/api/zimage/* -> zimage 上游 /api/z-image/*'));

// 6. 模板字符串完整性（沿袭）
const ticks = (s.match(/`/g) || []).length;
check('反引号配对（偶数个 ' + ticks + '）', ticks % 2 === 0);
check('无 \\n/\\r/\\t 转义序列（模板内坑）', !/\\[nrt]/.test(s));
for (const id of ['refSection', 'refDisabledHint', 'qualityCell', 'kdrStatePill', 'kdrCustomKeys', 'zimageHint']) {
  check(`id ${id} 定义存在`, s.includes(`id="${id}"`));
}

console.log(fail ? `\n${fail} 项未通过` : '\n全部结构自检通过');
process.exit(fail ? 1 : 0);
