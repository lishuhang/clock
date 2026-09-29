// ============================================================
// TTS Voice Lab v2.17 — Cloudflare Worker
// NiceVoice (primary) + IndexTTS + KikiVoice (backup)
// Voice cloning TTS with subtitle generation & JianYing export
// v2.17: fix segment editing not clickable after generation completes
//        (S.isGenerating=false was set but renderSegmentTable() not re-called).
// ============================================================

const VERSION = '2.17.0';
const DEFAULT_INDEX_API = 'https://kozzzq-indextts2api.hf.space';

// NiceVoice API constants
const NV_API_BASE = 'https://api.turbovoice.online';
const NV_HMAC_KEY = '9BSGc4rO5uSkAEDO1UaHur6fui5B5jJ4';
const NV_APP_ID = '10';
const NV_APP_CODE = '110';
const NV_WAIT_MS = 16000; // 16s between TTS requests
const NV_MAX_POLL = 60;
const NV_MAX_CHARS = 150;

// KikiVoice API constants
const KIKA_BASE = 'https://kikivoice.ai';

// ============================================================
// README_CONTENT — Single source of truth for in-app README modal.
// Stored at the head of the file so it is the first thing readers see
// when opening the source. getReadmeContent() renders this verbatim.
// ============================================================
const README_CONTENT = `
# TTS Voice Lab v${VERSION}

> 基于 Cloudflare Worker 的浏览器端语音克隆 TTS 工具，三引擎切换 + 长文本分段合成 + 字幕生成 + 剪映工程导出。

## 📖 简介

TTS Voice Lab 是一个基于浏览器的语音克隆 TTS 工具，支持长文本分段合成、字幕生成和剪映工程导出。

v2.14 在 v2.13 基础上引入：GLM 系统提示词可编辑、Before/After 双栏预览、说话人交替校验、BGM 混音（sidechain ducking）、人声音量归一化、片头片尾拼接、标题/Shownotes/Tags 自动生成、设置项变更 toast 提示。README 与 changelog 提至文件头部统一管理。

## 🔧 功能特性

- **三引擎支持**：NiceVoice（推荐）+ IndexTTS + KikiVoice，一键切换
- **NiceVoice**：免费无限制语音克隆，无需登录，API 代理自动签名
- **IndexTTS**：基于 kozzzq/indextts2api REST API，支持并发生成
- **KikiVoice**：备选 TTS 引擎，三种模型（Core/Pro/Multilingual），每周 60,000 免费积分
- **文本优先工作流**：先输入文本，自动检测说话人，再为每人分配音源
- **音源管理**：新建、重命名、预览、删除、导入/导出音源，音源可关联克隆 ID
- **数字/符号预处理（v2.14 增强）**：GLM 系统提示词可自定义，默认处理：
  - 顿号 \`、\` → 逗号 \`，\`
  - 书名号 \`《》\` → 去除（保留内容）
  - 破折号 \`——\` → 逗号
  - 省略号 \`……\` → 等等
  - 数字 \`409\` → 四百零九；年份 \`2026\` → 二零二六；金额/百分比 → 中文读法
  - 小数点 \`3.14\` → 三点一四；版本号 \`2.14\` → 二点一四
- **Before/After 双栏预览（v2.14 新增）**：合成前可看到 GLM 处理结果，并可手动编辑后再提交
- **说话人交替校验（v2.14 新增）**：检测连续两段同一说话人，高亮告警并提供"自动交替"按钮
- **BGM 混音（v2.14 新增）**：上传 BGM、人声/BGM 双音量拉杆、5 秒片段实时试听、sidechain ducking（人声段 BGM 自动降 6dB）、配置可保存/导入/导出
- **片头片尾拼接（v2.14 新增）**：参考 podmerge.html 实现，支持淡入淡出/直接拼接
- **人声音量归一化（v2.14 新增）**：peak normalize 到 -3dB；按说话人 RMS 分组拉平；可选女声轻量压缩
- **标题/Shownotes/Tags 生成（v2.14 新增）**：合成完成后调用 GLM 自动生成播客元数据
- **长文本分段**：NiceVoice 150 字/段（智能合并短句），IndexTTS 250 字/段
- **换行保留**：原始换行用于字幕分行
- **Word 文档导入**：支持拖拽或上传 .docx 文件
- **SRT 字幕**：按时间比例分配字幕，多人模式自动标注说话人
- **剪映工程导出**：生成可直接导入剪映的工程 ZIP
- **生成历史**：自动保存生成记录，标注使用引擎
- **配置导入/导出**：备份和恢复所有设置和音源
- **设置变更 toast（v2.14 新增）**：任何设置项变更即时提示"设置已保存"，不遮挡功能区

## 📋 使用方法

1. 选择 TTS 引擎（推荐 NiceVoice）
2. 输入或导入要合成的文本
3. 在说话人分配卡片中为每位说话人选择或新建音源
4. 点击"预览处理"查看 GLM 转换前后的文本，可手动编辑 After 文本
5. 点击"开始合成"，等待生成完成
6. （可选）在结果区点击"生成标题/摘要/标签"
7. 下载 WAV 音频（含/不含 BGM 两个版本）、SRT 字幕或剪映工程

## 🔄 引擎对比

- **NiceVoice**：免费无限、无需登录、声音克隆质量好、150 字/段、段间 16 秒间隔
- **IndexTTS**：需要自建 API 或使用公共 API、250 字/段、支持并发、无间隔限制
- **KikiVoice**：备选、三种模型、每周 60,000 免费积分、需 Geetest 验证

## 🎤 关于参考音频

参考音频的质量直接影响克隆效果。建议：

- 时长 5-15 秒，清晰无噪音
- 避免背景音乐或多人说话
- 可以保存多个音源并随时切换
- 如需变速效果，请预先处理参考音频，本工具不做变速

## 🎬 关于剪映工程

导出的 ZIP 解压后包含以项目名命名的文件夹，内含 \`draft_content.json\`、\`draft_meta_info.json\`、\`audio_main.wav\` 和 \`audio_main.srt\`。将文件夹复制到剪映草稿目录 \`com.lveditor.draft\` 下即可打开。画布比例：9:16，字幕使用思源黑体（白字黑边，字号 10），位于画面下方。音频为完整单段文件。

## 🎵 关于 BGM 混音（v2.14 新增）

- BGM 默认音量 -18dB（约 0.126 增益），可在设置中调节
- 人声段开始时 BGM 自动 ducking 至 -24dB（再降 6dB），人声结束 0.3 秒后恢复
- ducking 算法使用 OfflineAudioContext + GainNode 自动化曲线，参考 podmerge.html 的 sidechain 实现
- 输出包含 BGM 的最终混音 WAV，同时保留纯人声 WAV 作为备份

## 🎚 关于音量归一化（v2.14 新增）

- **peak normalize**：所有段归一到 -3dB（可配置 -6 ~ 0dB）
- **说话人 RMS 拉平**：按说话人分组计算 RMS，自动增益让所有说话人响度一致（误差 ±1dB）
- **女声轻量压缩（可选）**：阈值 -20dB、比例 2:1、攻击 5ms、释放 50ms，治女声忽大忽小

## 📝 更新日志

### v2.14.0 (2026-06-17)

**新增**
- GLM 系统提示词可在设置中编辑、保存到 localStorage、随配置导入导出
- 默认系统提示词新增规则：顿号/书名号/破折号统一转逗号；小数点读"点"汉字；年份/日期/金额/百分比的中文读法
- Before/After 双栏预览面板：合成前可看到 GLM 处理前后对比，After 文本框可手动编辑覆盖
- 说话人交替校验：扫描分段结果检测连续两段同一说话人，高亮告警 + "自动交替"按钮
- BGM 集成：上传/选择、双音量拉杆、5 秒片段实时试听、sidechain ducking、配置可保存/导入/导出
- 片头片尾拼接：参考 podmerge.html 实现，支持淡入淡出/直接拼接两种模式
- 人声音量归一化：peak normalize + 说话人 RMS 拉平 + 可选女声轻量压缩
- 标题/Shownotes/Tags 自动生成：合成完成后调用 GLM 生成播客元数据
- 设置项变更即时 toast 提示，不遮挡功能区（toast 移至右下角）
- 正则预处理新增书名号/顿号/破折号/竖线转逗号规则（无需 GLM 即可工作）
- 下载按钮新增"下载 WAV（纯人声）"选项，含 BGM 时同时保留两份

**修复**
- 保留 v2.13 源码中的 \`/\\.docx$/\` 正则字面量（避免 esbuild 打包后丢失反斜杠的潜在问题）
- 修复部署版中 NEW_FUNCTIONS 未注入的问题（\`</script>\` 在模板字符串中需写作 \`<\\/script>\`）
- 修复 generateMetadata 中 \`\\\`\\\`\\\`\` 代码块标记导致模板字符串提前终止的语法错误
- 修复 \`alert('原文：\\n')\` 等字符串中 \\n 被模板字符串解释为实际换行的语法错误
- 修复 metadataCard 元素未注入 DOM 导致 \`E.metadataCard\` 为 null 的问题（用正则替换代替字面匹配）

**重构**
- README 与 changelog 提至文件头部 \`README_CONTENT\` 常量，\`getReadmeContent()\` 直接引用，避免源码与 UI 显示不一致

**实测验证（2026-06-17）**
- 用 2 个真实音色（小娱音色 + 乐乐-播客音色2）+ 2509 字早报文案测试
- 29 段全部生成成功，0 失败，总时长 6:35
- 数字/日期正则预处理正确（2026→二零二六、6月17日→六月十七日、第38届→第三十八届等）
- ASR 抽样验证 4 段，内容完整可识别，无段落丢失
- 书名号/顿号/破折号在本次测试中未处理（因 GLM 未配置），随后已添加正则回退规则

### v2.13.0 (2026-06-12)

- 修复 nvCloneVoice 音色复用：nvReferenceId 现在正确传递，已有音色无需重复克隆
- 修复无音频数据时的音色复用：即使 localStorage 中没有 base64 数据，只要 referenceId 有效也能复用
- GLM 智能预处理：支持 GLM-4-Flash API 进行中文数字、符号、多音字智能预处理
- GLM API Key 管理：设置中新增 API Key 输入和测试按钮，支持导入导出
- 预处理模式选择：关闭/回退模式（正则失败时用 GLM）/始终使用 GLM
- 预处理安全检查：如果预处理结果异常（过短），自动回退到原文
- GLM API 代理：通过 Worker 代理调用 GLM API，API Key 不暴露到客户端
- TTS 请求日志：记录发送到 TTS 引擎的文本内容和长度，便于调试

### v2.12.0 (2026-06-12)

- 移除顶部参考音频卡：采用"文本优先→再分配音源"工作流
- 说话人分配卡重构：单人模式也显示"默认"音源槽
- 音源互斥：已被一位说话人选择的音源，在其他说话人的下拉中置灰
- 音源管理 2.0：设置面板新增预览、重命名、同步状态指示
- 数字/符号预处理：自动将数字转中文读法，符号转文字
- 年份/日期/电话识别
- 音源数据结构升级：支持 NV/KK 双引擎音色 ID
- 音频压缩：新建音源时自动重采样 24kHz、截取 15 秒

### v2.11.0 (2026-06-11)

- 多人旁白模式：自动检测说话人标记
- 换行续接：没有说话人标记的行自动归属上一个说话人
- 防呆检测：当说话人台词量严重不均衡时警告
- 自定义说话人模式：支持添加自定义正则表达式
- 多人 SRT 字幕：字幕自动标注说话人姓名
- 多人剪映导出：剪映工程也支持多人字幕标签

### v2.9.0 (2026-05-25)

- 新增 KikiVoice 渠道：备选 TTS 引擎，三种免费模型
- Geetest 人机验证：通过 Worker 代理确保 IP 一致
- 积分余量查询：实时显示剩余积分、已用积分和重置时间
- Log 控制台：新增事件记录控制台

### v2.8.0 (2026-05-26)

- JSZip 懒加载：仅在需要时加载
- 移除调试日志：减少执行开销
- 简化字幕算法：优化自动换行算法
- DOM 元素缓存：减少重复查询
- HTTP 缓存：添加页面缓存头

### v2.7.0 (2026-05-25)

- 修复 SRT 时间轴根本问题：弃用位置追踪法，改用字符数累加法
- 修复剪映字幕同步

### v2.6.0 (2026-05-25)

- 修复 SRT 时间轴：修正字幕与音频不同步
- 修复 WAV 下载：直接下载已有文件
- 文件名规则：导入 docx 时文件名与 docx 一致
- 剪映 ZIP 结构规范化
- 生成历史升级：使用 IndexedDB 保存

### v2.5.0 (2026-05-25)

- 修复剪映字幕显示：字幕类型改为 subtitle
- 修复字幕样式格式：stroke 格式对齐 pyJianYingDraft 规范
- 补全字幕素材字段
- 修复字幕坐标：transform 使用归一化坐标 y:-0.8

### v2.4.0 (2026-05-25)

- 规范化文件名：yyyymmdd-hhmmss
- SRT 自动换行：每行不超过 15 字
- 剪映字幕样式：思源黑体、白字黑边、字号 10
- 同次生成时间戳一致

### v2.3.0 (2026-05-24)

- 音色复用优化：保存的音源关联 NiceVoice 服务器端 referenceId
- 智能验证：使用已保存音色时检查服务器端有效性
- 自动重新克隆：服务器端失效时自动重新克隆

### v2.2.0 (2026-05-24)

- 修复文字分段：NiceVoice 模式下短句不再各自成段
- 完整控制台日志：方便 F12 调试
- 分段逻辑重构

### v2.1.0 (2026-05-24)

- 新增 NiceVoice 作为主要 TTS 引擎
- 新增双引擎切换器
- 新增 NiceVoice API 代理（服务端 HMAC-SHA256 签名）
- 新增声音克隆流程：上传 → 训练 → TTS
- 新增音源关联克隆 ID

### v2.0.0 (2026-05-23)

- 全新重构，基于 kozzzq/indextts2api REST API
- 新增剪映工程 ZIP 导出功能
- 新增 SRT 字幕生成
- 新增音源管理、并发 TTS 生成、生成历史记录
- 新增 Word 文档导入、配置导入/导出
`;

// v2.14 default GLM system prompt (user-editable in settings)
const DEFAULT_GLM_PROMPT = '你是一个TTS文本预处理助手。将输入文本转换为适合语音合成朗读的中文。规则：\\n'
  + '1. 数字转中文读法：403→四百零三，2026→二零二六，3.14→三点一四，2.14→二点一四，126.5→一百二十六点五\\n'
  + '2. 百分号 → 百分之：80.3%→百分之八十点三，50%→百分之五十\\n'
  + '3. 标点中转（远端 TTS 无法识别这些标点）：\\n'
  + '   - 顿号、→ 逗号，\\n'
  + '   - 书名号《》→ 直接去除（保留书名内容，例如《飞驰人生3》→ 飞驰人生3）\\n'
  + '   - 破折号——→ 逗号，\\n'
  + '   - 省略号……→ 等等\\n'
  + '   - 冒号：保留（用于说话人标记，TTS 可正确识别）\\n'
  + '4. 符号转文字：≥→大于等于，℃→摄氏度，×→乘以，/→或\\n'
  + '5. 保持原文意思不变，只调整朗读形式\\n'
  + '6. 不要添加解释、标注或前缀\\n'
  + '7. 直接输出转换结果';

const KK_MAX_RETRIES = 3;

function uuidv4() { return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=Math.random()*16|0;return(c==='x'?r:(r&0x3|0x8)).toString(16);}); }

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, x-appid, x-code, x-os, x-ts, x-account, x-sign, x-token',
  };
}

// ==================== NiceVoice HMAC Signing ====================
// Hex-decode the HMAC key (non-hex chars produce 0 bytes, matching NiceVoice's Ff() function)
function hexDecodeKey(hexStr) {
  const bytes = new Uint8Array(hexStr.length / 2);
  for (let i = 0; i < hexStr.length; i += 2) {
    const val = parseInt(hexStr.substring(i, i + 2), 16);
    bytes[i / 2] = isNaN(val) ? 0 : val;
  }
  return bytes;
}

async function nvSign(bodyObj, ts, account) {
  const dataStr = (ts + account + JSON.stringify(bodyObj)).toLowerCase();
  const keyData = hexDecodeKey(NV_HMAC_KEY);
  const key = await crypto.subtle.importKey('raw', keyData, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(dataStr));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
}

async function nvHeaders(bodyObj, account) {
  const ts = Date.now().toString();
  const sign = await nvSign(bodyObj, ts, account || '');
  return {
    'Content-Type': 'application/json',
    'x-os': 'web',
    'x-appid': NV_APP_ID,
    'x-code': NV_APP_CODE,
    'x-ts': ts,
    'x-account': account || '',
    'x-sign': sign,
    'x-token': 'token',
  };
}

// ==================== NiceVoice API Proxy ====================
async function nvProxy(path, bodyObj, account) {
  const headers = await nvHeaders(bodyObj, account);
  const resp = await fetch(NV_API_BASE + path, {
    method: 'POST',
    headers,
    body: JSON.stringify(bodyObj),
  });
  const text = await resp.text();
  let data;
  try { data = JSON.parse(text); } catch(e) { data = { code: resp.status, raw: text }; }
  return new Response(JSON.stringify(data), {
    status: resp.status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders() },
  });
}


// ==================== KikiVoice Proxy Helpers ====================
async function kikiFetch(path, uuid, options={}) {
  const headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://kikivoice.ai',
    'Referer': 'https://kikivoice.ai/ai-voice-cloning/zh-cn',
    'Cookie': 'uuid=' + uuid,
  };
  if (options.contentType) headers['Content-Type'] = options.contentType;
  const fetchOpts = { method: options.method||'GET', headers };
  if (options.body) fetchOpts.body = options.body;
  console.log('[KIKA] ' + fetchOpts.method + ' ' + path.substring(0,80));
  const resp = await fetch(KIKA_BASE + path, fetchOpts);
  const t = await resp.text();
  console.log('[KIKA] ' + resp.status + ': ' + t.substring(0,300));
  return { status: resp.status, body: t, headers: resp.headers };
}

async function kikiProxyResponse(kikiResult) {
  const h = {'Content-Type':'application/json',...corsHeaders()};
  const sc = kikiResult.headers.get('Set-Cookie');
  if (sc) h['X-Set-Cookie'] = sc;
  return new Response(kikiResult.body, {status:kikiResult.status, headers:h});
}

// ==================== Worker Handler ====================
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    // Serve main page
    if (path === '/' && request.method === 'GET') {
      return new Response(getHTML(), {
        headers: { 'Content-Type': 'text/html;charset=UTF-8', 'Cache-Control': 'public, max-age=300', ...corsHeaders() },
      });
    }

    // NiceVoice API proxy endpoints
    if (path.startsWith('/api/nv/')) {
      try {
        const nvPath = '/clone' + path.substring(7); // /api/nv/getUploadUrl -> /clone/getUploadUrl
        const bodyText = await request.text();
        const bodyObj = bodyText ? JSON.parse(bodyText) : {};
        // Log TTS requests for debugging
        if (nvPath === '/clone/tts' && bodyObj.text) {
          console.log('[NV-PROXY] TTS text="' + String(bodyObj.text).substring(0, 100) + '" (len=' + String(bodyObj.text).length + ') refId=' + bodyObj.referenceId);
        }
        // Always use empty account for anonymous mode
        return await nvProxy(nvPath, bodyObj, '');
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), {
          status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders() },
        });
      }
    }

    // NiceVoice upload proxy (PUT to presigned URL)
    if (path === '/api/nv-upload' && request.method === 'POST') {
      try {
        const { uploadUrl, audioBase64 } = await request.json();
        const audioBytes = Uint8Array.from(atob(audioBase64), c => c.charCodeAt(0));
        const resp = await fetch(uploadUrl, {
          method: 'PUT',
          headers: { 'Content-Type': 'audio/wav' },
          body: audioBytes,
        });
        return new Response(JSON.stringify({ ok: resp.ok, status: resp.status }), {
          headers: { 'Content-Type': 'application/json', ...corsHeaders() },
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), {
          status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders() },
        });
      }
    }

    // Audio download proxy
    if (path === '/api/audio-proxy' && request.method === 'GET') {
      try {
        const audioUrl = url.searchParams.get('url');
        if (!audioUrl) return new Response('Missing url', { status: 400 });
        const resp = await fetch(audioUrl);
        const headers = new Headers();
        headers.set('Content-Type', resp.headers.get('Content-Type') || 'audio/mpeg');
        headers.set('Access-Control-Allow-Origin', '*');
        return new Response(resp.body, { status: resp.status, headers });
      } catch (e) {
        return new Response(e.message, { status: 500, headers: corsHeaders() });
      }
    }

    // GLM API proxy for text preprocessing
    if (path === '/api/glm/chat' && request.method === 'POST') {
      try {
        const { apiKey, messages } = await request.json();
        if (!apiKey) return new Response(JSON.stringify({ error: 'Missing apiKey' }), { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
        const resp = await fetch('https://open.bigmodel.cn/api/paas/v4/chat/completions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + apiKey },
          body: JSON.stringify({ model: 'glm-4-flash', messages: messages, temperature: 0.1, max_tokens: 2048 }),
        });
        const data = await resp.text();
        return new Response(data, { status: resp.status, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
      }
    }


    // ==================== KikiVoice API Proxy ====================
    const kikiUuid = url.searchParams.get('uuid') || request.headers.get('X-Kiki-Uuid') || uuidv4();

    if (path === '/api/kiki/model-capabilities') {
      const rr = await kikiFetch('/jsapi/model-capabilities', kikiUuid);
      return kikiProxyResponse(rr);
    }
    if (path === '/api/kiki/get-sig') {
      const rr = await kikiFetch('/jsapi/get-cloning-file-sig', kikiUuid);
      return kikiProxyResponse(rr);
    }
    if (path === '/api/kiki/detect-language') {
      try {
        const body = await request.json();
        const rr = await kikiFetch('/jsapi/detect-language', kikiUuid, { method: 'POST', contentType: 'application/json', body: JSON.stringify(body) });
        return kikiProxyResponse(rr);
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
      }
    }
    if (path === '/api/kiki/create-clone-task') {
      try {
        const body = await request.json();
        const fd = new FormData();
        fd.append('text', body.text);
        fd.append('clone_source_voice_custom_voice_id', body.voice_id);
        fd.append('lang_name_code', body.lang_code);
        fd.append('emotion', body.emotion || 'normal');
        fd.append('intensity', body.intensity || 'normal');
        fd.append('clone_source_voice_gender', String(body.gender || 0));
        fd.append('model_type', body.model_type);
        if (body.region) fd.append('region', body.region);
        fd.append('speed', String(body.speed || 1.0));
        fd.append('volume', String(body.volume || 100));
        fd.append('audio_format', body.format || 'mp3');
        fd.append('audio_high_quality', String(body.hq || 0));
        fd.append('model_version_text', body.mver || 'default');
        const rr = await kikiFetch('/jsapi/create-new-clone-task', kikiUuid, { method: 'POST', body: fd });
        return kikiProxyResponse(rr);
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
      }
    }
    if (path === '/api/kiki/job-status') {
      const jobId = url.searchParams.get('job_id');
      const rr = await kikiFetch('/jsapi/get-job-task-status?job_id=' + encodeURIComponent(jobId), kikiUuid);
      return kikiProxyResponse(rr);
    }
    if (path === '/api/kiki/upload-voice') {
      try {
        const formData = await request.formData();
        const voiceFile = formData.get('voice-file');
        const sig = formData.get('sig');
        const createUrl = formData.get('create_url');
        const voiceName = formData.get('voice_name') || 'MyVoice';
        if (!voiceFile || !sig || !createUrl) {
          return new Response(JSON.stringify({ errcode: -2, errmsg: 'Missing required fields' }), { status: 400, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
        }
        const uploadUrl = createUrl + '?voice_name=' + encodeURIComponent(voiceName) + '&denoise=0&asr=1&sig=' + encodeURIComponent(sig);
        const upFd = new FormData();
        upFd.append('voice-file', voiceFile);
        const headers = {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
          'Origin': 'https://kikivoice.ai',
          'Referer': 'https://kikivoice.ai/ai-voice-cloning/zh-cn',
          'Cookie': 'uuid=' + kikiUuid,
        };
        const resp = await fetch(uploadUrl, { method: 'POST', headers, body: upFd });
        const respText = await resp.text();
        return new Response(respText, { status: resp.status, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
      } catch (e) {
        return new Response(JSON.stringify({ errcode: -1, errmsg: e.message }), { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
      }
    }
    if (path === '/api/kiki-audio') {
      try {
        const audioUrl = url.searchParams.get('url');
        if (!audioUrl) return new Response('Missing url', { status: 400 });
        const resp = await fetch(audioUrl, { headers: { 'User-Agent': 'Mozilla/5.0', 'Referer': 'https://kikivoice.ai/' } });
        const h = new Headers(resp.headers);
        h.set('Access-Control-Allow-Origin', '*');
        h.set('Content-Disposition', 'attachment; filename="kiki_audio.mp3"');
        return new Response(resp.body, { status: resp.status, headers: h });
      } catch (e) {
        return new Response(e.message, { status: 500, headers: corsHeaders() });
      }
    }
    // Geetest validation page proxy
    if (path === '/api/kiki/geetest-page') {
      try {
        const vpath = url.searchParams.get('path');
        if (!vpath) return new Response('Missing path', { status: 400 });
        const resp = await fetch(KIKA_BASE + vpath, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Referer': 'https://kikivoice.ai/',
            'Cookie': 'uuid=' + kikiUuid,
          }
        });
        let html = await resp.text();
        const workerBase = url.origin;
        html = html.replace(/fetch\(['"]\/jsapi\/auth\/geetest-validation['"]/g, "fetch('" + workerBase + "/api/kiki/geetest-submit?uuid=" + encodeURIComponent(kikiUuid) + "'");
        if (!html.includes('<base')) {
          html = html.replace('<head>', '<head><base href="https://kikivoice.ai/">');
        }
        html = html.replace(/<script>\s*\(function\(\)\{function c\(\)\{var b=a\.contentDocument[\s\S]*?<\/script>/gi, '');
        const pm = "<script>(function(){var o=typeof showSuccess==='function'?showSuccess:null;var e2=typeof showError==='function'?showError:null;window.showSuccess=function(){if(o)o();if(window.parent!==window)window.parent.postMessage({type:'geetest-success'},'*');};window.showError=function(){if(e2)e2();if(window.parent!==window)window.parent.postMessage({type:'geetest-error'},'*');};})();</script>";
        html = html.replace('</body>', pm + '</body>');
        return new Response(html, { status: resp.status, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Access-Control-Allow-Origin': '*', 'X-Frame-Options': '' } });
      } catch (e) {
        return new Response('Geetest proxy error: ' + e.message, { status: 500, headers: corsHeaders() });
      }
    }
    // Geetest verification submission proxy
    if (path === '/api/kiki/geetest-submit') {
      try {
        let body;
        try { body = await request.json(); } catch(e) {
          return new Response(JSON.stringify({code:400,msg:'Invalid JSON body'}),{status:400,headers:{'Content-Type':'application/json',...corsHeaders()}});
        }
        const resp = await fetch(KIKA_BASE + '/jsapi/auth/geetest-validation', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Origin': 'https://kikivoice.ai',
            'Referer': 'https://kikivoice.ai/ai-voice-cloning/zh-cn',
            'Cookie': 'uuid=' + kikiUuid,
          },
          body: JSON.stringify(body),
        });
        const respText = await resp.text();
        return new Response(respText, { status: resp.status, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
      } catch (e) {
        return new Response(JSON.stringify({ error: e.message }), { status: 500, headers: { 'Content-Type': 'application/json', ...corsHeaders() } });
      }
    }

    return new Response(JSON.stringify({ error: 'Not found' }), {
      status: 404, headers: { 'Content-Type': 'application/json', ...corsHeaders() },
    });
  }
};

// ==================== HTML Page Generator ====================
function getHTML() {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TTS Voice Lab v${VERSION}</title>
<style>
:root{--bg:#0f0f0f;--surface:#1a1a1a;--surface2:#242424;--surface3:#2e2e2e;--border:#333;--text:#e0e0e0;--text2:#999;--primary:#6c5ce7;--primary-hover:#7d6ff0;--green:#00b894;--orange:#fdcb6e;--red:#e17055;--blue:#74b9ff;--nv-color:#e17055;--idx-color:#74b9ff;--kk-color:#10b981}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans SC',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column}
::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:var(--surface)}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
.header{background:var(--surface);border-bottom:1px solid var(--border);padding:10px 20px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;flex-shrink:0}
.header-left{display:flex;align-items:center;gap:12px}
.header h1{font-size:18px;font-weight:700;background:linear-gradient(135deg,var(--primary),var(--blue));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header .ver{font-size:11px;color:var(--text2);background:var(--surface2);padding:2px 8px;border-radius:10px}
.api-status{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text2)}
.api-status .dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.api-status .dot.online{background:var(--green)}
.api-status .dot.offline{background:var(--red)}
.api-status .dot.checking{background:var(--orange)}
.header-right{display:flex;gap:8px}
.hdr-btn{background:var(--surface2);border:1px solid var(--border);color:var(--text2);padding:6px 14px;border-radius:8px;cursor:pointer;font-size:13px;transition:all .2s}
.hdr-btn:hover{background:var(--primary);color:#fff;border-color:var(--primary)}
.engine-selector{display:flex;gap:0;background:var(--surface2);border-radius:8px;border:1px solid var(--border);overflow:hidden;margin:0 8px}
.engine-btn{padding:6px 16px;font-size:12px;font-weight:600;cursor:pointer;border:none;background:transparent;color:var(--text2);transition:all .2s;white-space:nowrap}
.engine-btn:hover{color:var(--text)}
.engine-btn.active-nv{background:var(--nv-color);color:#fff}
.engine-btn.active-idx{background:var(--idx-color);color:#fff}
.main{flex:1;max-width:1600px;margin:0 auto;padding:20px;width:100%}
.main-grid{display:grid;grid-template-columns:1fr;gap:16px}
.main-content{min-width:0}
.main-log{min-width:0}
.main-log .log-console{max-height:none;height:calc(100vh - 140px);position:sticky;top:80px}
.layout-tabs{display:none}
@media(min-width:1024px){.main-grid{grid-template-columns:1fr 1fr}.layout-tabs{display:none}.main-content{max-height:calc(100vh - 140px);overflow-y:auto;padding-right:8px}}
@media(max-width:1023px){.main-grid{grid-template-columns:1fr}.layout-tabs{display:flex;gap:0;margin-bottom:12px;background:var(--surface2);border-radius:8px;border:1px solid var(--border);overflow:hidden}.layout-tab{flex:1;padding:10px 16px;font-size:13px;font-weight:600;cursor:pointer;border:none;background:transparent;color:var(--text2);transition:all .2s}.layout-tab.active{background:var(--primary);color:#fff}.main-content.hidden-tab{display:none}.main-log.hidden-tab{display:none}.main-log .log-console{max-height:400px;position:static;height:auto}}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px}
.card-title{font-size:15px;font-weight:600;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.engine-badge{font-size:10px;padding:2px 8px;border-radius:10px;font-weight:600;text-transform:uppercase}
.engine-badge.nv{background:var(--nv-color);color:#fff}
.engine-badge.idx{background:var(--idx-color);color:#fff}
.upload-zone{border:2px dashed var(--border);border-radius:8px;padding:28px;text-align:center;cursor:pointer;transition:all .2s;position:relative}
.upload-zone:hover{border-color:var(--primary);background:rgba(108,92,231,0.05)}
.upload-zone.has-file{border-color:var(--green);background:rgba(0,184,148,0.05);border-style:solid}
.upload-zone .uz-icon{font-size:32px;margin-bottom:8px}
.upload-zone .uz-text{color:var(--text2);font-size:13px}
.upload-zone .uz-hint{color:var(--text2);font-size:11px;margin-top:4px;opacity:0.7}
.upload-zone .uz-filename{color:var(--green);font-weight:500;font-size:13px}
.audio-preview{margin-top:12px;display:flex;align-items:center;gap:8px}
.audio-preview audio{flex:1;height:32px}
.clear-btn{background:var(--surface2);border:1px solid var(--border);color:var(--text2);padding:4px 10px;border-radius:6px;cursor:pointer;font-size:12px}
.clear-btn:hover{border-color:var(--red);color:var(--red)}
.source-section{margin-top:14px;padding-top:14px;border-top:1px solid var(--surface2)}
.source-row{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.source-row label{font-size:12px;color:var(--text2);white-space:nowrap}
.source-select{flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:12px;min-width:120px}
.save-source-row{display:flex;gap:6px}
.save-source-row input{flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:12px}
.save-source-row button{background:var(--primary);border:none;color:#fff;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;white-space:nowrap}
.source-list{margin-top:8px;max-height:160px;overflow-y:auto}
.source-item{display:flex;justify-content:space-between;align-items:center;padding:6px 10px;background:var(--surface2);border-radius:6px;margin-bottom:4px;font-size:12px;cursor:pointer;transition:background .15s;border:1px solid transparent}
.source-item:hover{background:var(--surface3)}
.source-item.active{border-color:var(--primary);background:rgba(108,92,231,0.1)}
.source-item .s-name{font-weight:500}
.source-item .s-actions{display:flex;gap:4px}
.source-item .s-actions button{background:var(--surface3);border:none;color:var(--text);padding:2px 6px;border-radius:4px;cursor:pointer;font-size:11px}
.text-area{width:100%;min-height:140px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:12px;color:var(--text);font-size:14px;resize:vertical;font-family:inherit;line-height:1.7}
.text-area:focus{outline:none;border-color:var(--primary)}
.text-stats{display:flex;justify-content:space-between;margin-top:8px;font-size:12px;color:var(--text2)}
.docx-actions{display:flex;gap:8px;margin-top:10px;align-items:center;flex-wrap:wrap}
.docx-btn{display:flex;align-items:center;gap:6px;padding:7px 14px;border-radius:6px;font-size:13px;cursor:pointer;border:1px solid var(--border);background:var(--surface2);color:var(--text);transition:background .2s}
.docx-btn:hover{background:var(--surface3)}
.docx-info{font-size:12px;color:var(--text2)}
.text-card{position:relative}
.docx-drop-overlay{position:absolute;top:0;left:0;right:0;bottom:0;background:rgba(108,92,231,0.12);border:2px dashed var(--primary);border-radius:12px;display:flex;align-items:center;justify-content:center;z-index:10;pointer-events:none;opacity:0;transition:opacity .2s}
.docx-drop-overlay.active{opacity:1}
.docx-drop-overlay p{color:var(--primary);font-size:15px;font-weight:600;padding:20px}
.gen-btn{width:100%;padding:14px;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:8px}
.gen-btn:hover{background:var(--primary-hover)}
.gen-btn:active{opacity:0.9}
.gen-btn:disabled{opacity:0.5;cursor:not-allowed;transform:none}
.gen-btn.nv-active{background:var(--nv-color)}
.gen-btn.idx-active{background:var(--idx-color)}
.cancel-btn{width:100%;padding:10px;background:var(--surface2);border:1px solid var(--border);color:var(--text2);border-radius:8px;font-size:13px;cursor:pointer;margin-top:8px;transition:all .2s}
.cancel-btn:hover{border-color:var(--red);color:var(--red)}
.progress-bar{width:100%;height:6px;background:var(--surface3);border-radius:3px;margin-top:12px;overflow:hidden;display:none}
.progress-bar.active{display:block}
.progress-fill{height:100%;background:linear-gradient(90deg,var(--primary),var(--blue));border-radius:3px;transition:width .3s}
.elapsed{font-size:13px;color:var(--text2);margin-top:8px;text-align:center}
.seg-table{width:100%;border-collapse:collapse;margin-top:12px;font-size:12px}
.seg-table th{text-align:left;padding:6px 10px;border-bottom:1px solid var(--border);color:var(--text2);font-weight:500;font-size:11px}
.seg-table td{padding:6px 10px;border-bottom:1px solid var(--surface2)}
.seg-table .seg-text{max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.seg-table .seg-status{display:flex;align-items:center;gap:5px}
.seg-table .sd{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.seg-table .sd.pending{background:var(--text2)}
.seg-table .sd.cloning{background:var(--orange)}
.seg-table .sd.submitting{background:var(--orange)}
.seg-table .sd.processing{background:var(--blue)}
.seg-table .sd.done{background:var(--green)}
.seg-table .sd.error{background:var(--red)}
.seg-table .sd.cancelled{background:var(--text2);opacity:0.4}
.result-section{display:none}
.result-section.active{display:block}
.result-audio{width:100%;margin-top:12px}
.dl-btns{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.dl-btn{padding:9px 18px;border-radius:8px;font-size:13px;cursor:pointer;border:1px solid var(--border);background:var(--surface2);color:var(--text);transition:all .2s;display:flex;align-items:center;gap:6px}
.dl-btn:hover{background:var(--surface3)}
.dl-btn.primary{background:var(--primary);border-color:var(--primary);color:#fff}
.dl-btn.primary:hover{background:var(--primary-hover)}
.settings-panel{position:fixed;top:0;right:-440px;width:420px;height:100vh;background:var(--surface);border-left:1px solid var(--border);z-index:200;transition:right .3s;overflow-y:auto;padding:20px}
.settings-panel.open{right:0}
.settings-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:199;display:none}
.settings-overlay.open{display:block}
.settings-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
.settings-header h2{font-size:18px;font-weight:600}
.close-btn{background:none;border:none;color:var(--text2);font-size:22px;cursor:pointer;padding:4px}
.close-btn:hover{color:var(--text)}
.settings-group{margin-bottom:20px}
.settings-group h3{font-size:13px;font-weight:600;color:var(--text2);margin-bottom:10px;text-transform:uppercase;letter-spacing:0.5px}
.s-item{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--surface2)}
.s-item label{font-size:13px;color:var(--text)}
.s-item input[type="number"],.s-item input[type="text"],.s-item select{background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:13px;width:130px}
.s-item select{cursor:pointer}
.s-item .wide{width:220px}
.ie-btns{display:flex;gap:8px;margin-top:12px}
.ie-btns button{flex:1;padding:9px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer;font-size:13px;transition:all .2s}
.ie-btns button:hover{background:var(--surface3)}
.readme-btn{width:100%;padding:10px;background:var(--surface2);border:1px solid var(--border);color:var(--text2);border-radius:8px;cursor:pointer;font-size:13px;transition:all .2s;text-align:center;margin-top:12px}
.readme-btn:hover{background:var(--surface3);color:var(--text)}
.modal-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:500;display:none;align-items:center;justify-content:center}
.modal-overlay.open{display:flex}
.modal-content{background:var(--surface);border:1px solid var(--border);border-radius:12px;width:90%;max-width:700px;max-height:80vh;overflow-y:auto;padding:24px;position:relative}
.modal-content h2{font-size:18px;font-weight:600;margin-bottom:16px;color:var(--primary)}
.modal-content h3{font-size:15px;font-weight:600;margin-top:16px;margin-bottom:8px;color:var(--text)}
.modal-content p,.modal-content li{font-size:13px;line-height:1.7;color:var(--text)}
.modal-content ul{padding-left:20px;margin-bottom:12px}
.modal-content code{background:var(--surface2);padding:1px 5px;border-radius:3px;font-size:12px;color:var(--orange)}
.modal-close{position:absolute;top:12px;right:16px;background:none;border:none;color:var(--text2);font-size:22px;cursor:pointer}
.modal-close:hover{color:var(--text)}
.history-list{max-height:65vh;overflow-y:auto}
.history-item{background:var(--surface2);border-radius:8px;padding:12px;margin-bottom:8px}
.history-item .hi-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.history-item .hi-text{font-size:14px;font-weight:500}
.history-item .hi-date{font-size:11px;color:var(--text2)}
.history-item .hi-detail{font-size:12px;color:var(--text2);line-height:1.5;overflow:hidden;text-overflow:ellipsis;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.toast{position:fixed;bottom:20px;right:20px;padding:10px 16px;border-radius:8px;font-size:12px;z-index:600;transform:translateX(120%);transition:transform .3s;max-width:300px;box-shadow:0 4px 12px rgba(0,0,0,0.3)}
.toast.show{transform:translateX(0)}
.toast.success{background:var(--green);color:#000}
.toast.error{background:var(--red);color:#fff}
.toast.info{background:var(--blue);color:#000}
.spinner{width:16px;height:16px;border:2px solid rgba(255,255,255,0.3);border-top-color:#fff;border-radius:50%;animation:spin .6s linear infinite;display:inline-block;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.changelog-version{font-weight:600;color:var(--primary);margin-top:14px;margin-bottom:4px;font-size:14px}
.changelog-date{font-size:11px;color:var(--text2);margin-left:8px}
.clone-status{margin-top:8px;padding:8px 12px;background:var(--surface2);border-radius:6px;font-size:12px;color:var(--text2);display:none}
.clone-status.active{display:block}

.engine-btn.active-kk{background:var(--kk-color);color:#fff}
.engine-badge.kk{background:var(--kk-color);color:#fff}
.gen-btn.kk-active{background:var(--kk-color)}
.kk-cfg-card{display:none}.kk-cfg-card.visible{display:block}
.kk-info-box{background:var(--bg);border-radius:8px;padding:14px;margin-bottom:12px;border:1px solid var(--border);font-size:.85rem;color:var(--text2);line-height:1.8}
.kk-info-box b{color:var(--text)}.kk-info-box code{background:var(--surface2);padding:1px 6px;border-radius:4px;font-size:.8rem;color:var(--orange)}
.kk-conn-status{display:inline-flex;align-items:center;gap:6px;font-size:.85rem;font-weight:500;padding:4px 12px;border-radius:6px}
.kk-conn-status.ok{background:rgba(0,184,148,.15);color:var(--green)}.kk-conn-status.fail{background:rgba(225,112,85,.15);color:var(--red)}.kk-conn-status.pen{background:rgba(253,203,110,.15);color:var(--orange)}
.kk-conn-dot{width:8px;height:8px;border-radius:50%;display:inline-block}
.kk-conn-status.ok .kk-conn-dot{background:var(--green)}.kk-conn-status.fail .kk-conn-dot{background:var(--red)}.kk-conn-status.pen .kk-conn-dot{background:var(--orange)}
.kk-models{display:flex;gap:8px;margin-top:8px}
.kk-model{flex:1;padding:10px 12px;border-radius:8px;border:2px solid var(--border);background:var(--bg);color:var(--text);cursor:pointer;text-align:center;transition:all .2s;font-size:.85rem}
.kk-model:hover{border-color:var(--kk-color)}.kk-model.sel{border-color:var(--kk-color);background:rgba(16,185,129,.15)}
.kk-model .mn{font-weight:600;display:block}.kk-model .md{font-size:.75rem;color:var(--text2);margin-top:2px}.kk-model .mc{font-size:.7rem;color:var(--orange);margin-top:4px}
.kk-params{background:var(--bg);border-radius:8px;padding:14px;margin-top:12px;border:1px solid var(--border)}
.kk-params .pt{font-size:.9rem;font-weight:600;margin-bottom:10px;display:flex;align-items:center;gap:6px}
.kk-param-row{display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap}
.kk-param-row label{min-width:70px;margin-bottom:0;font-size:.85rem;flex-shrink:0}
.kk-param-row input[type=range]{flex:1;min-width:120px;accent-color:var(--kk-color);height:6px}
.kk-param-row .pv{min-width:40px;text-align:right;font-size:.85rem;color:var(--kk-color);font-weight:600;font-family:monospace}
.kk-param-row select{background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:4px 8px;color:var(--text);font-size:.85rem}
.kk-param-row select:focus{outline:none;border-color:var(--kk-color)}
.kk-param-hint{font-size:.75rem;color:var(--text2);margin-left:8px}
.kk-pro-only{opacity:.4;pointer-events:none;transition:opacity .3s}
.kk-pro-only.active{opacity:1;pointer-events:auto}
.kk-quota{background:var(--bg);border-radius:8px;padding:12px 16px;margin-top:12px;border:1px solid var(--border)}
.kk-qbg{height:6px;background:var(--surface3);border-radius:3px;overflow:hidden;margin-top:8px}
.kk-qb{height:100%;border-radius:3px;transition:width .5s}
.kk-qb.g{background:linear-gradient(to right,#34d399,#22c55e)}.kk-qb.y{background:linear-gradient(to right,#fbbf24,#f59e0b)}.kk-qb.r{background:linear-gradient(to right,#f87171,#ef4444)}
.kk-qt{font-size:.8rem;color:var(--text2);margin-top:6px;display:flex;justify-content:space-between}
.cf-panel{border:2px solid var(--orange)!important;background:linear-gradient(135deg,rgba(253,203,110,.05),var(--surface))!important}
.cf-step{display:flex;gap:12px;align-items:flex-start;margin:10px 0;padding:10px;background:var(--bg);border-radius:8px}
.cf-num{min-width:28px;height:28px;border-radius:50%;background:var(--orange);color:white;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.85rem;flex-shrink:0}
.cf-body{flex:1}.cf-body p{margin:2px 0;font-size:.88rem}.cf-body a{color:var(--kk-color);word-break:break-all}
.cf-url-box{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:8px 12px;margin:8px 0;word-break:break-all;font-family:'Courier New',monospace;font-size:.82rem;color:var(--kk-color)}
.cf-actions{display:flex;gap:8px;margin-top:16px;flex-wrap:wrap}
.iframe-wrap{margin-top:16px;border:1px solid var(--border);border-radius:8px;overflow:hidden;background:white;position:relative}
.iframe-wrap iframe{width:100%;height:420px;border:none}
.iframe-overlay{position:absolute;top:0;left:0;right:0;bottom:0;background:rgba(15,15,15,.8);display:flex;align-items:center;justify-content:center;z-index:10}
.iframe-overlay .inner{text-align:center;color:var(--text)}
.iframe-overlay .inner p{margin:8px 0;font-size:.9rem}
.log-console{max-height:400px;overflow-y:auto;background:var(--bg);border-radius:8px;padding:12px;font-family:'Courier New',monospace;font-size:.78rem;line-height:1.5;margin-top:12px}
.log-entry{padding:2px 0;word-break:break-all}.log-entry.i{color:var(--text2)}.log-entry.s{color:var(--green)}.log-entry.e{color:var(--red)}.log-entry.w{color:var(--orange)}

/* Speaker Assignment Styles */
.speaker-card.visible{display:block}
.speaker-warning{background:rgba(253,203,110,0.1);border:1px solid var(--orange);border-radius:8px;padding:12px 16px;margin-bottom:14px;display:flex;align-items:flex-start;gap:10px;font-size:13px;color:var(--orange)}
.speaker-warning .sw-icon{font-size:18px;flex-shrink:0;margin-top:1px}
.speaker-warning .sw-text{flex:1;line-height:1.6}
.speaker-warning .sw-text b{color:#fff}
.speaker-warning .sw-actions{display:flex;gap:6px;margin-top:6px}
.speaker-warning .sw-actions button{padding:4px 12px;border-radius:6px;border:1px solid var(--orange);background:transparent;color:var(--orange);cursor:pointer;font-size:12px;transition:all .2s}
.speaker-warning .sw-actions button:hover{background:var(--orange);color:#000}
.speaker-list{display:flex;flex-direction:column;gap:10px}
.speaker-row{display:flex;align-items:center;gap:12px;padding:12px;background:var(--bg);border-radius:8px;border:1px solid var(--border)}
.speaker-row .sp-color{width:12px;height:12px;border-radius:50%;flex-shrink:0}
.speaker-row .sp-name{font-weight:600;font-size:14px;min-width:60px;flex-shrink:0}
.speaker-row .sp-stats{font-size:11px;color:var(--text2);margin-left:4px}
.speaker-row .sp-select{flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:6px;font-size:13px;min-width:140px}
.speaker-row .sp-upload{display:flex;align-items:center;gap:6px}
.speaker-row .sp-upload-btn{background:var(--primary);border:none;color:#fff;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:12px;white-space:nowrap;transition:all .2s}
.speaker-row .sp-upload-btn:hover{background:var(--primary-hover)}
.speaker-row .sp-upload-filename{font-size:11px;color:var(--green);max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sp-preview{font-size:11px;color:var(--text2);margin-left:4px}
.seg-speaker{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:600;margin-right:4px}
.seg-speaker.sp0{background:rgba(108,92,231,0.3);color:#a29bfe}
.seg-speaker.sp1{background:rgba(0,184,148,0.3);color:#55efc4}
.seg-speaker.sp2{background:rgba(116,185,255,0.3);color:#74b9ff}
.seg-speaker.sp3{background:rgba(253,203,110,0.3);color:#fdcb6e}
.seg-speaker.sp4{background:rgba(225,112,85,0.3);color:#e17055}
.speaker-pattern-row{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.speaker-pattern-row input{flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px;font-size:12px;font-family:monospace}
.speaker-pattern-row .sp-del{background:none;border:none;color:var(--red);cursor:pointer;font-size:16px;padding:2px 6px}
.speaker-pattern-row .sp-del:hover{opacity:0.7}

@media(max-width:640px){.main{padding:12px}.header{padding:8px 12px;flex-wrap:wrap;gap:8px}.settings-panel{width:100%;right:-100%}.card{padding:14px}.modal-content{width:95%;padding:16px}.engine-selector{margin:4px 0}.speaker-row{flex-wrap:wrap}.speaker-row .sp-name{min-width:50px}}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <h1>TTS Voice Lab</h1>
    <span class="ver">v${VERSION}</span>
    <div class="api-status">
      <span class="dot checking" id="apiDot"></span>
      <span id="apiText">检测中...</span>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:8px">
    <div class="engine-selector">
      <button class="engine-btn active-nv" id="btnNV" onclick="switchEngine('nicevoice')">NiceVoice</button>
      <button class="engine-btn" id="btnIDX" onclick="switchEngine('indextts')">IndexTTS</button>
      <button class="engine-btn" id="btnKK" onclick="switchEngine('kikivoice')">KikiVoice</button>
    </div>
    <button class="hdr-btn" onclick="openHistory()">&#x1F4CB; 历史</button>
    <button class="hdr-btn" onclick="toggleSettings()">&#x2699; 设置</button>
  </div>
</div>

<div class="main">
  <div class="layout-tabs">
    <button class="layout-tab active" onclick="switchLayoutTab('content')">&#x1F4C4; 参数设定</button>
    <button class="layout-tab" onclick="switchLayoutTab('log')">&#x1F4BB; 控制台</button>
  </div>
  <div class="main-grid">
  <div class="main-content">
  <!-- KikiVoice Config Card -->
  <div class="card kk-cfg-card" id="kkCfgCard">
    <div class="card-title">KikiVoice 配置 <span class="engine-badge kk">KK</span></div>
    <div class="kk-info-box">
      <p><b>Cloudflare + Geetest 防护机制：</b></p>
      <p>1. <b>CF CDN 挑战</b>：Worker 运行在 CF 网络内，自动绕过 CDN 层的 JS 挑战。</p>
      <p>2. <b>Geetest 人机验证</b>：首次调用 create-clone-task 时需要完成滑块验证。验证页面和提交均通过 Worker 代理，确保 IP 一致。</p>
      <p>3. <b>积分系统</b>：每 7 天重置 60,000 免费积分。Kiki Core = 2x, Kiki Pro = 3x, Kiki Multilingual = 2x。</p>
    </div>
    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px;">
      <span id="kkConn" class="kk-conn-status pen"><span class="kk-conn-dot"></span>未检测</span>
      <button class="clear-btn" onclick="testKK()" style="border-color:var(--kk-color);color:var(--kk-color)">检测连接</button>
    </div>
    <div>
      <label style="display:block;font-weight:500;margin-bottom:6px;font-size:.9rem">选择模型</label>
      <div class="kk-models">
        <div class="kk-model sel" id="mCore" onclick="pickKKModel('kiki_core')"><span class="mn">Kiki Core</span><span class="md">基础克隆，稳定易用</span><span class="mc">2x credits</span></div>
        <div class="kk-model" id="mPro" onclick="pickKKModel('kiki_pro')"><span class="mn">Kiki Pro</span><span class="md">情感控制，高品质</span><span class="mc">3x credits</span></div>
        <div class="kk-model" id="mMulti" onclick="pickKKModel('kiki_multilingual')"><span class="mn">Kiki Multilingual</span><span class="md">口音转换，多语言</span><span class="mc">2x credits</span></div>
      </div>
    </div>
    <div class="kk-params" id="kkParams">
      <div class="pt">模型参数</div>
      <div class="kk-param-row">
        <label>语速 Speed</label>
        <input type="range" id="kSpeed" min="0.5" max="2.0" step="0.1" value="1.0" oninput="updKKParam()">
        <span class="pv" id="kSpeedVal">1.0</span>
        <span class="kk-param-hint">0.5慢 ~ 2.0快</span>
      </div>
      <div class="kk-param-row">
        <label>音量 Volume</label>
        <input type="range" id="kVolume" min="50" max="200" step="10" value="100" oninput="updKKParam()">
        <span class="pv" id="kVolumeVal">100</span>
        <span class="kk-param-hint">50低 ~ 200高</span>
      </div>
      <div class="kk-param-row kk-pro-only" id="emotionRow">
        <label>情感 Emotion</label>
        <select id="kEmotion" onchange="updKKParam()">
          <option value="normal">正常 Normal</option>
          <option value="happy">开心 Happy</option>
          <option value="sad">悲伤 Sad</option>
          <option value="angry">愤怒 Angry</option>
          <option value="fearful">恐惧 Fearful</option>
        </select>
        <span class="kk-param-hint">仅Pro模型</span>
      </div>
      <div class="kk-param-row kk-pro-only" id="intensityRow">
        <label>强度 Intensity</label>
        <select id="kIntensity" onchange="updKKParam()">
          <option value="normal">正常 Normal</option>
          <option value="strong">强烈 Strong</option>
          <option value="weak">轻柔 Weak</option>
        </select>
        <span class="kk-param-hint">仅Pro模型</span>
      </div>
      <div class="kk-param-row">
        <label>性别 Gender</label>
        <select id="kGender" onchange="updKKParam()">
          <option value="0">女声 Female</option>
          <option value="1">男声 Male</option>
        </select>
      </div>
      <div class="kk-param-row">
        <label>高品质 HQ</label>
        <select id="kHq" onchange="updKKParam()">
          <option value="0">标准 Standard</option>
          <option value="1">高品质 High Quality</option>
        </select>
      </div>
    </div>
    <div class="kk-quota">
      <div style="display:flex;justify-content:space-between;align-items:center"><span style="font-size:.9rem;font-weight:600">积分用量</span><span style="font-size:.8rem;color:var(--text2)" id="qReset">7天重置</span></div>
      <div class="kk-qbg"><div class="kk-qb g" id="qBar" style="width:100%"></div></div>
      <div class="kk-qt"><span>剩余: <b id="qAvail">--</b></span><span>已用: <b id="qUsed">--</b></span></div>
    </div>
  </div>

  <!-- CF Verification Panel -->
  <div class="card cf-panel" id="cfPanel" style="display:none">
    <div class="card-title" style="color:var(--orange);font-size:1.1rem">需要人机验证 (Geetest 极验)</div>
    <div class="kk-info-box" style="border-color:var(--orange)">
      <p>KikiVoice 要求完成 Geetest 人机验证后才能创建语音任务。</p>
      <p>Worker IP: <b id="cfIP" style="color:var(--orange)">--</b></p>
      <p>Session UUID: <b id="cfUUID" style="color:var(--text2);font-family:monospace;font-size:.8rem">--</b></p>
      <p style="font-size:.8rem;margin-top:4px">验证页面已通过 Worker 代理加载，验证提交也走 Worker，确保 IP 和 Session 一致。</p>
    </div>
    <div style="margin:8px 0">
      <p style="font-size:.9rem;font-weight:600;margin-bottom:8px">验证步骤：</p>
      <div class="cf-step"><div class="cf-num">1</div><div class="cf-body"><p>点击<b>滑块验证按钮</b>完成人机验证</p><p style="color:var(--text2);font-size:.8rem">验证页面已嵌入下方，直接操作即可</p></div></div>
      <div class="cf-step"><div class="cf-num">2</div><div class="cf-body"><p>看到<b>"Verification Successful"</b>后，点击下方"验证完成，继续生成"</p></div></div>
    </div>
    <div class="iframe-wrap" id="cfIframeWrap">
      <iframe id="cfIframe" src="about:blank" sandbox="allow-scripts allow-same-origin allow-forms allow-popups"></iframe>
      <div class="iframe-overlay" id="cfIframeOverlay"><div class="inner"><p>验证页面加载中...</p><p style="font-size:.8rem;color:var(--text2)">如长时间无响应，请点击下方按钮在新标签页打开</p></div></div>
    </div>
    <div class="cf-actions">
      <button class="clear-btn" onclick="cfDone()" style="background:var(--kk-color);color:white;border-color:var(--kk-color)">验证完成，继续生成</button>
      <button class="clear-btn" onclick="openCFNewTab()" style="background:var(--orange);color:white;border-color:var(--orange)">在新标签页打开</button>
      <button class="clear-btn" onclick="cfCancel()">取消生成</button>
    </div>
    <div style="margin:8px 0">
      <p style="font-size:.85rem;color:var(--text2);margin-bottom:4px">验证页面 URL（代理版）：</p>
      <div class="cf-url-box" id="cfUrl">--</div>
    </div>
    <div class="log-console" style="margin-top:12px;max-height:150px">
      <div class="log-entry w" id="cfRaw">等待验证...</div>
    </div>
  </div>

  <!-- Card 1: Text Input -->
  <div class="card text-card" id="textCard">
    <div class="card-title"><span class="icon">&#x1F4DD;</span> 合成文本</div>
    <div class="docx-drop-overlay" id="docxDropOverlay"><p>&#x1F4C4; 释放 Word 文档，自动读取文本</p></div>
    <textarea class="text-area" id="textInput" placeholder="输入要合成的文本...&#10;支持长文本自动分段处理，也可拖入 Word 文档&#10;换行将保留用于字幕分行" oninput="updateTextStats()"></textarea>
    <div class="docx-actions">
      <button class="docx-btn" onclick="document.getElementById('docxFileInput').click()">&#x1F4C4; 上传 Word 文档</button>
      <span class="docx-info" id="docxInfo"></span>
    </div>
    <input type="file" id="docxFileInput" accept=".docx" style="display:none" onchange="handleDocxUpload(event)">
    <div class="text-stats">
      <span>字数: <b id="charCount">0</b></span>
      <span>行数: <b id="lineCount">0</b></span>
      <span>预计分段: <b id="segCount">0</b></span>
    </div>
  </div>

  <!-- Card 2: Speaker Assignment -->
  <div class="card speaker-card" id="speakerCard">
    <div class="card-title"><span class="icon">&#x1F3A4;</span> 说话人分配 <span style="font-size:11px;color:var(--text2)" id="speakerModeLabel">单人模式</span></div>
    <div class="speaker-warning" id="speakerWarning" style="display:none">
      <span class="sw-icon">&#x26A0;&#xFE0F;</span>
      <div class="sw-text" id="speakerWarningText"></div>
    </div>
    <div class="speaker-list" id="speakerList"></div>
  </div>

  <!-- v2.14 Card: Before/After Preview -->
  <div class="card" id="previewCard" style="display:none">
    <div class="card-title"><span class="icon">🔍</span> GLM 预处理预览 (Before / After)</div>
    <p style="font-size:12px;color:var(--text2);margin-bottom:10px">点击"预览 GLM 处理"查看转换前后对比。After 文本框可手动编辑，编辑后将以此文本提交 TTS。</p>
    <div id="previewBody" style="max-height:400px;overflow-y:auto;font-size:12px"></div>
    <div style="display:flex;gap:8px;margin-top:10px;flex-wrap:wrap">
      <button class="dl-btn" id="previewBtn" onclick="loadPreview()">🔍 预览 GLM 处理</button>
      <button class="dl-btn" id="regenGlmBtn" onclick="loadPreview()" style="display:none">🔄 重新调用 GLM</button>
      <button class="dl-btn primary" id="applyPreviewBtn" onclick="applyPreviewAndGenerate()" style="display:none">✅ 应用并开始合成</button>
      <button class="dl-btn" onclick="document.getElementById('previewCard').style.display='none'">关闭预览</button>
    </div>
  </div>

  <!-- v2.14 Card: Speaker Alternation Warning -->
  <div class="card" id="alternationWarning" style="display:none;border-color:var(--orange);background:rgba(253,203,110,0.05)">
    <div class="card-title" style="color:var(--orange)"><span class="icon">⚠️</span> 说话人交替异常</div>
    <p style="font-size:12px;color:var(--text2);margin-bottom:10px" id="alternationWarningText"></p>
    <button class="dl-btn" id="alternationFixBtn" onclick="autoFixAlternation()" style="background:var(--orange);color:#000;border-color:var(--orange)">🔧 自动交替</button>
  </div>

  <!-- Card 3: Generate -->
  <div class="card">
    <button class="gen-btn nv-active" id="generateBtn" onclick="onGenerateClick()">
      <span id="genBtnText">&#x1F680; 开始合成 (NiceVoice)</span>
    </button>
    <button class="cancel-btn" id="cancelBtn" onclick="cancelGenerate()" style="display:none">&#x23F9; 取消生成</button>
    <div class="progress-bar" id="progressBar">
      <div class="progress-fill" id="progressFill" style="width:0%"></div>
    </div>
    <div class="elapsed" id="elapsed" style="display:none">已用时: 0s</div>
    <table class="seg-table" id="segTable" style="display:none">
      <thead><tr><th>#</th><th>文本</th><th>状态</th><th>时长</th><th>试听</th></tr></thead>
      <tbody id="segBody"></tbody>
    </table>
  </div>

  <!-- Card 4: Results -->
  <div class="card result-section" id="resultSection">
    <div class="card-title"><span class="icon">&#x1F3B5;</span> 合成结果</div>
    <audio class="result-audio" id="resultAudio" controls></audio>
    <div class="dl-btns">
      <button class="dl-btn primary" onclick="downloadWav()">&#x1F4E5; 下载 WAV（含 BGM）</button>
      <button class="dl-btn" onclick="downloadWavVoiceOnly()">&#x1F4E5; 下载 WAV（纯人声）</button>
      <button class="dl-btn" onclick="downloadSrt()">&#x1F4E5; 下载 SRT</button>
      <button class="dl-btn" onclick="downloadJianYing()">&#x1F4E5; 下载剪映工程</button>
    </div>
  </div>

  <!-- v2.15 Card: Podcast Metadata Generation -->
  <div class="card" id="metadataCard" style="display:none">
    <div class="card-title"><span class="icon">&#x1F4DD;</span> 播客元数据生成</div>
    <p style="font-size:12px;color:var(--text2);margin-bottom:10px">基于合成文本调用 GLM 生成播客标题、Shownotes、Tags，方便上传小宇宙等平台。</p>
    <div style="margin-bottom:10px">
      <label style="font-size:12px;color:var(--text2);display:block;margin-bottom:6px">原始新闻要点（可选，作为提示词一部分发送给 GLM）</label>
      <textarea id="metadataRawNews" rows="6" placeholder="粘贴原始 10 条新闻要点，例如：&#10;1.TikTok发布5月短剧分账战报...&#10;2.哔哩哔哩直播姬移动端App停止开播...&#10;..." style="width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:12px;line-height:1.5;resize:vertical;font-family:inherit"></textarea>
    </div>
    <button class="dl-btn primary" id="genMetadataBtn" onclick="generateMetadata()">&#x2728; 生成标题/摘要/标签</button>
    <div style="margin-top:12px;display:none" id="metadataResult">
      <div style="margin-bottom:8px"><label style="font-size:12px;color:var(--text2)">标题</label><input type="text" id="metadataTitle" style="width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:13px"></div>
      <div style="margin-bottom:8px"><label style="font-size:12px;color:var(--text2)">Shownotes</label><textarea id="metadataShownotes" rows="14" style="width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:12px;line-height:1.5;resize:vertical;font-family:inherit"></textarea></div>
      <div style="margin-bottom:8px"><label style="font-size:12px;color:var(--text2)">Tags（逗号分隔）</label><input type="text" id="metadataTags" style="width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:13px"></div>
      <button class="dl-btn" onclick="copyMetadata()">&#x1F4CB; 一键复制全部</button>
    </div>
  </div>
  </div>
  <div class="main-log hidden-tab">
    <div class="card">
      <div class="card-title"><span class="icon">&#x1F4BB;</span> 控制台 Log</div>
      <div class="log-console" id="logBox"></div>
    </div>
  </div>
  </div>
</div>

<!-- Settings Panel -->
<div class="settings-overlay" id="settingsOverlay" onclick="toggleSettings()"></div>
<div class="settings-panel" id="settingsPanel">
  <div class="settings-header">
    <h2>&#x2699; 设置</h2>
    <button class="close-btn" onclick="toggleSettings()">&#x2715;</button>
  </div>
  <div class="settings-group">
    <h3>引擎选择</h3>
    <div class="s-item"><label>TTS 引擎</label>
      <select id="cfgEngine" onchange="switchEngine(this.value)">
        <option value="nicevoice">NiceVoice (推荐)</option>
        <option value="indextts">IndexTTS</option>
        <option value="kikivoice">KikiVoice (备选)</option>
      </select>
    </div>
  </div>
  <div class="settings-group" id="nvSettings">
    <h3>NiceVoice 设置</h3>
    <div class="s-item"><label>请求间隔 (秒)</label><input type="number" id="cfgNvWait" min="10" max="30" step="1"></div>
    <div class="s-item"><label>最大字数/段</label><input type="number" id="cfgNvMaxChars" min="50" max="150"></div>
    <div class="s-item"><label>最大轮询次数</label><input type="number" id="cfgNvMaxPoll" min="20" max="120"></div>
  </div>
  <div class="settings-group" id="idxSettings" style="display:none">
    <h3>IndexTTS 设置</h3>
    <div class="s-item"><label>API 地址</label><input type="text" id="cfgApiBase" class="wide"></div>
    <div class="s-item"><label>语言</label>
      <select id="cfgLanguage">
        <option value="zh">中文</option>
        <option value="en">English</option>
        <option value="ja">日本語</option>
        <option value="ko">한국어</option>
      </select>
    </div>
    <div class="s-item"><label>最大字数/段</label><input type="number" id="cfgMaxChars" min="50" max="1000"></div>
    <div class="s-item"><label>并发数 (1-5)</label><input type="number" id="cfgConcurrency" min="1" max="5"></div>
    <div class="s-item"><label>重试次数</label><input type="number" id="cfgRetry" min="0" max="5"></div>
    <div class="s-item"><label>轮询间隔 (ms)</label><input type="number" id="cfgPollInterval" min="500" max="10000" step="500"></div>
  </div>
  <div class="settings-group" id="kkSettings" style="display:none">
    <h3>KikiVoice 设置</h3>
    <div class="s-item"><label>连接状态</label><span id="kkSettingsConn" style="font-size:13px;color:var(--text2)">未检测</span></div>
    <div class="s-item"><label>当前模型</label><span id="kkSettingsModel" style="font-size:13px;color:var(--text2)">kiki_core</span></div>
  </div>
  <div class="settings-group">
    <h3>音源管理</h3>
    <div style="margin-bottom:8px;display:flex;gap:8px;flex-wrap:wrap">
      <button class="clear-btn" onclick="showNewVoiceForm()" style="background:var(--primary);color:#fff;border-color:var(--primary)">&#x2795; 新建音源</button>
      <button class="clear-btn" onclick="exportVoices()">&#x1F4E4; 导出音源</button>
      <button class="clear-btn" onclick="document.getElementById('importVoicesFile').click()">&#x1F4E5; 导入音源</button>
      <input type="file" id="importVoicesFile" accept=".json" style="display:none" onchange="importVoices(event)">
    </div>
    <div id="newVoiceForm" style="display:none;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:10px">
      <div style="font-weight:600;margin-bottom:8px;font-size:.9rem">新建音源</div>
      <div style="display:flex;gap:8px;margin-bottom:8px"><input type="text" id="newVoiceName" placeholder="音源名称" style="flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:13px"></div>
      <div class="upload-zone" id="settingsUploadZone" onclick="document.getElementById('settingsVoiceFile').click()" style="padding:16px">
        <div class="uz-icon" style="font-size:20px">&#x1F3A4;</div>
        <div class="uz-text" id="settingsUploadText">点击上传参考音频</div>
      </div>
      <input type="file" id="settingsVoiceFile" accept="audio/*" style="display:none" onchange="handleSettingsVoiceUpload(event)">
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="clear-btn" onclick="submitNewVoice()" style="background:var(--green);color:#000;border-color:var(--green)">&#x2714; 提交</button>
        <button class="clear-btn" onclick="hideNewVoiceForm()">取消</button>
      </div>
    </div>
    <div id="settingsVoiceList"></div>
  </div>
  <div class="settings-group">
    <h3>说话人识别模式</h3>
    <div class="s-item" style="flex-direction:column;align-items:flex-start;gap:8px">
      <label style="font-size:12px;color:var(--text2)">内置模式（无需配置）</label>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer"><input type="checkbox" id="cfgSpBracket" checked> 【姓名】格式</label>
        <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer"><input type="checkbox" id="cfgSpColon" checked> 姓名：格式</label>
      </div>
    </div>
    <div style="margin-top:10px">
      <label style="font-size:12px;color:var(--text2);display:block;margin-bottom:6px">自定义说话人正则模式 <span style="font-size:11px;opacity:0.7">（匹配后的第一个捕获组为说话人名）</span></label>
      <div id="speakerPatternsList"></div>
      <div class="save-source-row" style="margin-top:6px">
        <input type="text" id="newSpeakerPattern" placeholder="如: ^(\\\\S+?)\\\\s*>>>\\\\s*">
        <button onclick="addSpeakerPattern()">添加模式</button>
      </div>
    </div>
    <div class="s-item" style="margin-top:8px"><label>防呆阈值（比例）</label><input type="number" id="cfgSpBalance" min="2" max="10" step="1" style="width:80px"></div>
  </div>
  <div class="settings-group">
    <h3>历史记录</h3>
    <div class="s-item"><label>最大保存条数</label><input type="number" id="cfgMaxHistory" min="1" max="50"></div>
  </div>
  <div class="settings-group">
    <h3>GLM 文本预处理</h3>
    <div class="s-item">
      <label>API Key</label>
      <input type="password" id="cfgGlmApiKey" placeholder="输入 GLM API Key（可选）" style="flex:1">
      <button onclick="testGlmApiKey()" style="margin-left:6px;padding:4px 10px;font-size:12px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">测试</button>
    </div>
    <div class="s-item">
      <label>启用智能预处理</label>
      <select id="cfgGlmPreprocess" style="flex:0 0 auto">
        <option value="off">关闭（仅正则）</option>
        <option value="fallback">回退模式（正则失败时用GLM）</option>
        <option value="always">始终使用GLM</option>
      </select>
    </div>
    <p style="font-size:11px;color:var(--text2);margin-top:4px">使用 GLM-Flash-4 进行中文数字、符号、多音字智能预处理，需 API Key。回退模式下仅正则无法处理时调用。</p>
    <div class="s-item" style="flex-direction:column;align-items:flex-start;gap:6px">
      <label>系统提示词（高级，留空使用默认）</label>
      <textarea id="cfgGlmSystemPrompt" rows="8" style="width:100%;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:8px;border-radius:6px;font-size:12px;font-family:monospace;line-height:1.5;resize:vertical" placeholder="留空使用默认提示词。可在此自定义数字/标点/符号处理规则..."></textarea>
      <div style="display:flex;gap:6px">
        <button onclick="resetGlmPrompt()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">恢复默认</button>
        <button onclick="previewGlmProcess()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">试一下</button>
      </div>
    </div>
  </div>

  <div class="settings-group">
    <h3>BGM 混音</h3>
    <div class="s-item"><label>启用 BGM</label><input type="checkbox" id="cfgBgmEnabled"></div>
    <div class="s-item" style="flex-direction:column;align-items:flex-start;gap:6px">
      <label>BGM 文件</label>
      <div style="display:flex;gap:6px;width:100%;align-items:center">
        <button onclick="document.getElementById('bgmFileInput').click()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">📂 选择 BGM</button>
        <span id="bgmFileName" style="font-size:11px;color:var(--text2);flex:1"></span>
        <button onclick="previewBgm()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">▶ 试听</button>
        <button onclick="clearBgm()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--red);cursor:pointer">✖</button>
      </div>
      <input type="file" id="bgmFileInput" accept="audio/*" style="display:none" onchange="handleBgmUpload(event)">
      <audio id="bgmPreviewAudio" style="display:none"></audio>
    </div>
    <div class="s-item"><label>BGM 音量</label><input type="range" id="cfgBgmVolume" min="0" max="100" step="1" style="flex:1;max-width:200px"><span id="cfgBgmVolumeVal" style="font-size:11px;color:var(--text2);min-width:36px;text-align:right">35%</span></div>
    <div class="s-item"><label>人声段 BGM 衰减</label><input type="range" id="cfgBgmDuckDepth" min="0" max="100" step="5" style="flex:1;max-width:200px"><span id="cfgBgmDuckDepthVal" style="font-size:11px;color:var(--text2);min-width:36px;text-align:right">50%</span></div>
    <p style="font-size:11px;color:var(--text2);margin-top:4px">BGM 音量按 sqrt 刻度（35% ≈ -18dB）。人声段 BGM 自动衰减（50% ≈ -6dB 进一步降低）。试听请先选择 BGM。</p>
  </div>

  <div class="settings-group">
    <h3>人声音量归一化</h3>
    <div class="s-item"><label>启用 peak normalize</label><input type="checkbox" id="cfgVoiceNormalize"></div>
    <div class="s-item"><label>目标峰值 (dB)</label><input type="number" id="cfgVoiceTargetPeak" min="-12" max="0" step="1" style="width:80px"></div>
    <div class="s-item"><label>说话人 RMS 拉平</label><input type="checkbox" id="cfgSpeakerRms"></div>
    <div class="s-item"><label>女声轻量压缩</label><input type="checkbox" id="cfgFemaleCompress"></div>
    <p style="font-size:11px;color:var(--text2);margin-top:4px">peak normalize 将所有段峰值归一到目标 dB；RMS 拉平让所有说话人响度一致；女声压缩治忽大忽小。</p>
  </div>

  <div class="settings-group">
    <h3>片头片尾拼接</h3>
    <div class="s-item"><label>启用片头片尾</label><input type="checkbox" id="cfgIntroOutroEnabled"></div>
    <div class="s-item" style="flex-direction:column;align-items:flex-start;gap:6px">
      <label>片头文件</label>
      <div style="display:flex;gap:6px;width:100%;align-items:center">
        <button onclick="document.getElementById('introFileInput').click()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">📂 选择片头</button>
        <span id="introFileName" style="font-size:11px;color:var(--text2);flex:1"></span>
        <button onclick="clearIntro()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--red);cursor:pointer">✖</button>
      </div>
      <input type="file" id="introFileInput" accept="audio/*" style="display:none" onchange="handleIntroUpload(event)">
    </div>
    <div class="s-item" style="flex-direction:column;align-items:flex-start;gap:6px">
      <label>片尾文件</label>
      <div style="display:flex;gap:6px;width:100%;align-items:center">
        <button onclick="document.getElementById('outroFileInput').click()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--text);cursor:pointer">📂 选择片尾</button>
        <span id="outroFileName" style="font-size:11px;color:var(--text2);flex:1"></span>
        <button onclick="clearOutro()" style="padding:4px 10px;font-size:11px;border-radius:6px;border:1px solid var(--border);background:var(--surface2);color:var(--red);cursor:pointer">✖</button>
      </div>
      <input type="file" id="outroFileInput" accept="audio/*" style="display:none" onchange="handleOutroUpload(event)">
    </div>
    <div class="s-item"><label>拼接模式</label>
      <select id="cfgIntroOutroMode" style="flex:0 0 auto">
        <option value="fade">淡入淡出（推荐）</option>
        <option value="direct">直接拼接</option>
      </select>
    </div>
    <div class="s-item"><label>淡入淡出时长 (ms)</label><input type="number" id="cfgIntroOutroFade" min="0" max="3000" step="100" style="width:100px"></div>
    <p style="font-size:11px;color:var(--text2);margin-top:4px">参考 podmerge.html 实现。淡入淡出模式下片头与主音频叠化 500ms。</p>
  </div>

  <div class="settings-group">
    <h3>导入/导出</h3>
    <div class="ie-btns">
      <button onclick="exportConfig()">&#x1F4E4; 导出配置</button>
      <button onclick="document.getElementById('importFile').click()">&#x1F4E5; 导入配置</button>
    </div>
    <input type="file" id="importFile" accept=".json" style="display:none" onchange="importConfig(event)">
  </div>
  <div class="settings-group" style="margin-top:24px;padding-top:16px;border-top:1px solid var(--border)">
    <button class="readme-btn" onclick="showReadme()">&#x1F4D6; 查看 README 与更新日志 (v${VERSION})</button>
  </div>
</div>

<!-- History Modal -->
<div class="modal-overlay" id="historyModal">
  <div class="modal-content">
    <button class="modal-close" onclick="closeHistory()">&#x00D7;</button>
    <h2>&#x1F4CB; 生成历史</h2>
    <div class="history-list" id="historyList"></div>
  </div>
</div>

<!-- README Modal -->
<div class="modal-overlay" id="readmeModal">
  <div class="modal-content">
    <button class="modal-close" onclick="closeReadme()">&#x00D7;</button>
    <div id="readmeBody"></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
// ==================== Constants & State ====================
var APP_VERSION = '${VERSION}';
var DEFAULT_API = '${DEFAULT_INDEX_API}';
// v2.14: Client-side README_CONTENT (base64-decoded to avoid template literal escaping issues)
var README_CONTENT = (function() {
  var b64 = 'CgovLyA9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0KLy8gUkVBRE1FX0NPTlRFTlQg4oCUIFNpbmdsZSBzb3VyY2Ugb2YgdHJ1dGggZm9yIGluLWFwcCBSRUFETUUgbW9kYWwuCi8vIFN0b3JlZCBhdCB0aGUgaGVhZCBvZiB0aGUgZmlsZSBzbyBpdCBpcyB0aGUgZmlyc3QgdGhpbmcgcmVhZGVycyBzZWUKLy8gd2hlbiBvcGVuaW5nIHRoZSBzb3VyY2UuIGdldFJlYWRtZUNvbnRlbnQoKSByZW5kZXJzIHRoaXMgdmVyYmF0aW0uCi8vID09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PQoKIyBUVFMgVm9pY2UgTGFiIHYyLjE3LjAKCj4g5Z+65LqOIENsb3VkZmxhcmUgV29ya2VyIOeahOa1j+iniOWZqOerr+ivremfs+WFi+mahiBUVFMg5bel5YW377yM5LiJ5byV5pOO5YiH5o2iICsg6ZW/5paH5pys5YiG5q615ZCI5oiQICsg5a2X5bmV55Sf5oiQICsg5Ymq5pig5bel56iL5a+85Ye644CCCgojIyDwn5OWIOeugOS7iwoKVFRTIFZvaWNlIExhYiDmmK/kuIDkuKrln7rkuo7mtY/op4jlmajnmoTor63pn7PlhYvpmoYgVFRTIOW3peWFt++8jOaUr+aMgemVv+aWh+acrOWIhuauteWQiOaIkOOAgeWtl+W5leeUn+aIkOWSjOWJquaYoOW3peeoi+WvvOWHuuOAggoKdjIuMTcg5ZyoIHYyLjE2IOWfuuehgOS4iuW8leWFpe+8mkdMTSDns7vnu5/mj5DnpLror43lj6/nvJbovpHjgIFCZWZvcmUvQWZ0ZXIg5Y+M5qCP6aKE6KeI44CB6K+06K+d5Lq65Lqk5pu/5qCh6aqM44CBQkdNIOa3t+mfs++8iHNpZGVjaGFpbiBkdWNraW5n77yJ44CB5Lq65aOw6Z+z6YeP5b2S5LiA5YyW44CB54mH5aS054mH5bC+5ou85o6l44CB5qCH6aKYL1Nob3dub3Rlcy9UYWdzIOiHquWKqOeUn+aIkOOAgeiuvue9rumhueWPmOabtCB0b2FzdCDmj5DnpLrjgIJSRUFETUUg5LiOIGNoYW5nZWxvZyDmj5Doh7Pmlofku7blpLTpg6jnu5/kuIDnrqHnkIbjgIIKCiMjIPCflKcg5Yqf6IO954m55oCnCgotICoq5LiJ5byV5pOO5pSv5oyBKirvvJpOaWNlVm9pY2XvvIjmjqjojZDvvIkrIEluZGV4VFRTICsgS2lraVZvaWNl77yM5LiA6ZSu5YiH5o2iCi0gKipOaWNlVm9pY2UqKu+8muWFjei0ueaXoOmZkOWItuivremfs+WFi+mahu+8jOaXoOmcgOeZu+W9le+8jEFQSSDku6PnkIboh6rliqjnrb7lkI0KLSAqKkluZGV4VFRTKirvvJrln7rkuo4ga296enpxL2luZGV4dHRzMmFwaSBSRVNUIEFQSe+8jOaUr+aMgeW5tuWPkeeUn+aIkAotICoqS2lraVZvaWNlKirvvJrlpIfpgIkgVFRTIOW8leaTju+8jOS4ieenjeaooeWei++8iENvcmUvUHJvL011bHRpbGluZ3VhbO+8ie+8jOavj+WRqCA2MCwwMDAg5YWN6LS556ev5YiGCi0gKirmlofmnKzkvJjlhYjlt6XkvZzmtYEqKu+8muWFiOi+k+WFpeaWh+acrO+8jOiHquWKqOajgOa1i+ivtOivneS6uu+8jOWGjeS4uuavj+S6uuWIhumFjemfs+a6kAotICoq6Z+z5rqQ566h55CGKirvvJrmlrDlu7rjgIHph43lkb3lkI3jgIHpooTop4jjgIHliKDpmaTjgIHlr7zlhaUv5a+85Ye66Z+z5rqQ77yM6Z+z5rqQ5Y+v5YWz6IGU5YWL6ZqGIElECi0gKirmlbDlrZcv56ym5Y+36aKE5aSE55CGKirvvJpHTE0g57O757uf5o+Q56S66K+N5Y+v6Ieq5a6a5LmJ77yM6buY6K6k5aSE55CG77yaCiAgLSDpob/lj7cgXGDjgIFcYCDihpIg6YCX5Y+3IFxg77yMXGAKICAtIOS5puWQjeWPtyBcYOOAiuOAi1xgIOKGkiDljrvpmaTvvIjkv53nlZnlhoXlrrnvvIkKICAtIOegtOaKmOWPtyBcYOKAlOKAlFxgIOKGkiDpgJflj7cKICAtIOecgeeVpeWPtyBcYOKApuKAplxgIOKGkiDnrYnnrYkKICAtIOaVsOWtlyBcYDQwOVxgIOKGkiDlm5vnmb7pm7bkuZ3vvJvlubTku70gXGAyMDI2XGAg4oaSIOS6jOmbtuS6jOWFre+8m+mHkeminS/nmb7liIbmr5Qg4oaSIOS4reaWh+ivu+azlQogIC0g5bCP5pWw54K5IFxgMy4xNFxgIOKGkiDkuInngrnkuIDlm5vvvJvniYjmnKzlj7cgXGAyLjE1XGAg4oaSIOS6jOeCueS4gOS6lAotICoqQmVmb3JlL0FmdGVyIOWPjOagj+mihOiniCoq77ya5ZCI5oiQ5YmN5Y+v55yL5YiwIEdMTSDlpITnkIbnu5PmnpzvvIzlubblj6/miYvliqjnvJbovpHlkI7lho3mj5DkuqQKLSAqKuivtOivneS6uuS6pOabv+agoemqjCoq77ya5qOA5rWL6L+e57ut5Lik5q615ZCM5LiA6K+06K+d5Lq677yM6auY5Lqu5ZGK6K2m5bm25o+Q5L6bIuiHquWKqOS6pOabvyLmjInpkq4KLSAqKkJHTSDmt7fpn7MqKu+8muS4iuS8oCBCR03jgIHkurrlo7AvQkdNIOWPjOmfs+mHj+aLieadhuOAgTUg56eS54mH5q615a6e5pe26K+V5ZCs44CBc2lkZWNoYWluIGR1Y2tpbmfvvIjkurrlo7DmrrUgQkdNIOiHquWKqOmZjSA2ZELvvInjgIHphY3nva7lj6/kv53lrZgv5a+85YWlL+WvvOWHugotICoq54mH5aS054mH5bC+5ou85o6lKirvvJrlj4LogIMgcG9kbWVyZ2UuaHRtbCDlrp7njrDvvIzmlK/mjIHmt6HlhaXmt6Hlh7ov55u05o6l5ou85o6lCi0gKirkurrlo7Dpn7Pph4/lvZLkuIDljJYqKu+8mnBlYWsgbm9ybWFsaXplIOWIsCAtM2RC77yb5oyJ6K+06K+d5Lq6IFJNUyDliIbnu4Tmi4nlubPvvJvlj6/pgInlpbPlo7Dovbvph4/ljovnvKkKLSAqKuagh+mimC9TaG93bm90ZXMvVGFncyDnlJ/miJAqKu+8muWQiOaIkOWujOaIkOWQjuiwg+eUqCBHTE0g6Ieq5Yqo55Sf5oiQ5pKt5a6i5YWD5pWw5o2u77yb5pSv5oyB6L6T5YWl5Y6f5aeL5paw6Ze76KaB54K55L2c5Li65o+Q56S677yM5qCH6aKY5oyJInjmnIh45pel5aix6LWE5q+P5pel5pep5oql77yaeHh4IuagvOW8j+eUn+aIkAotICoq57uf5LiA6K+V5ZCs5YiH5o2i77yIdjIuMTUg5paw5aKe77yJKirvvJrmiYDmnInor5XlkKzmjInpkq7vvIhCR03jgIHpn7PoibLjgIFHTE0g5aSE55CG44CBS2lraVZvaWNlIOauteiQve+8ieaUr+aMgeaSreaUvi/lgZzmraLmgIHliIfmjaIKLSAqKktpa2lWb2ljZSDmrrXokL3or5XlkKzvvIh2Mi4xNSDmlrDlop7vvIkqKu+8muavj+auteeUn+aIkOWujOavleWNs+WPr+ivleWQrO+8jOaXoOmcgOetieW+heWFqOmDqOWujOaIkAotICoq5bem5Y+z5Lik5qCP5ZON5bqU5byP5biD5bGA77yIdjIuMTUg5paw5aKe77yJKirvvJrlrr3lsY/lt6blj7PlubbmjpLvvIjlhoXlrrkgKyBsb2fvvInvvIznqoTlsY8gdGFiIOWIh+aNogotICoq5q616JC957qn5paH5pys57yW6L6R77yIdjIuMTYg5paw5aKe77yJKirvvJrngrnlh7vliIbmrrXooajkuK3nmoTmlofmnKzljbPlj6/nvJbovpHvvIzmlK/mjIEgNCDnp43mmbrog73lnLrmma/vvJoKICAtIOacqueUn+aIkOaute+8mue8lui+keWQjueUqOaWsOaWh+acrOeUn+aIkAogIC0g55Sf5oiQ5Lit5q6177ya6Ieq5Yqo56aB55So57yW6L6R5bm25Zue6YCACiAgLSDlt7LnlJ/miJDkvYblkI7nu63mnKrlrozmiJDvvJrlrozmiJDljp/luo/liJflkI7ph43mlrDnlJ/miJDmlLnliqjmrrUKICAtIOWFqOmDqOWujOaIkOWQjue8lui+ke+8muW8gOWni+aMiemSruWPmCLlupTnlKjmm7TmlLki77yM5Y+q6YeN55Sf5oiQ5pS55Yqo5q61Ci0gKirljoblj7LorrDlvZXnvJbovpHlm57pgIDvvIh2Mi4xNiDmlrDlop7vvIkqKu+8muWOhuWPsuiusOW9leavj+adoeaWsOWinuOAkOe8lui+keOAkeaMiemSru+8jOWPr+i/mOWOn+aJgOacieWIhuaute+8iOWQq+mfs+mike+8ieWIsOS4u+eVjOmdoui/m+ihjOS/ruaUue+8m+mfs+mikeW3suS4ouWkseaXtuaMiemSrue9rueBsAotICoq6ZW/5paH5pys5YiG5q61KirvvJpOaWNlVm9pY2UgMTUwIOWtly/mrrXvvIjmmbrog73lkIjlubbnn63lj6XvvInvvIxJbmRleFRUUyAyNTAg5a2XL+autQotICoq5o2i6KGM5L+d55WZKirvvJrljp/lp4vmjaLooYznlKjkuo7lrZfluZXliIbooYwKLSAqKldvcmQg5paH5qGj5a+85YWlKirvvJrmlK/mjIHmi5bmi73miJbkuIrkvKAgLmRvY3gg5paH5Lu2Ci0gKipTUlQg5a2X5bmVKirvvJrmjInml7bpl7Tmr5TkvovliIbphY3lrZfluZXvvIzlpJrkurrmqKHlvI/oh6rliqjmoIfms6jor7Tor53kuroKLSAqKuWJquaYoOW3peeoi+WvvOWHuioq77ya55Sf5oiQ5Y+v55u05o6l5a+85YWl5Ymq5pig55qE5bel56iLIFpJUAotICoq55Sf5oiQ5Y6G5Y+yKirvvJroh6rliqjkv53lrZjnlJ/miJDorrDlvZXvvIzmoIfms6jkvb/nlKjlvJXmk44KLSAqKumFjee9ruWvvOWFpS/lr7zlh7oqKu+8muWkh+S7veWSjOaBouWkjeaJgOacieiuvue9ruWSjOmfs+a6kAotICoq6K6+572u5Y+Y5pu0IHRvYXN0KirvvJrku7vkvZXorr7nva7pobnlj5jmm7TljbPml7bmj5DnpLoi6K6+572u5bey5L+d5a2YIu+8jOS4jemBruaMoeWKn+iDveWMugoKIyMg8J+TiyDkvb/nlKjmlrnms5UKCjEuIOmAieaLqSBUVFMg5byV5pOO77yI5o6o6I2QIE5pY2VWb2ljZe+8iQoyLiDovpPlhaXmiJblr7zlhaXopoHlkIjmiJDnmoTmlofmnKwKMy4g5Zyo6K+06K+d5Lq65YiG6YWN5Y2h54mH5Lit5Li65q+P5L2N6K+06K+d5Lq66YCJ5oup5oiW5paw5bu66Z+z5rqQCjQuIOeCueWHuyLpooTop4jlpITnkIYi5p+l55yLIEdMTSDovazmjaLliY3lkI7nmoTmlofmnKzvvIzlj6/miYvliqjnvJbovpEgQWZ0ZXIg5paH5pysCjUuIOeCueWHuyLlvIDlp4vlkIjmiJAi77yM562J5b6F55Sf5oiQ5a6M5oiQCjYuIO+8iOWPr+mAie+8ieWcqOe7k+aenOWMuueCueWHuyLnlJ/miJDmoIfpopgv5pGY6KaBL+agh+etviIKNy4g5LiL6L29IFdBViDpn7PpopHvvIjlkKsv5LiN5ZCrIEJHTSDkuKTkuKrniYjmnKzvvInjgIFTUlQg5a2X5bmV5oiW5Ymq5pig5bel56iLCgojIyDwn5SEIOW8leaTjuWvueavlAoKLSAqKk5pY2VWb2ljZSoq77ya5YWN6LS55peg6ZmQ44CB5peg6ZyA55m75b2V44CB5aOw6Z+z5YWL6ZqG6LSo6YeP5aW944CBMTUwIOWtly/mrrXjgIHmrrXpl7QgMTYg56eS6Ze06ZqUCi0gKipJbmRleFRUUyoq77ya6ZyA6KaB6Ieq5bu6IEFQSSDmiJbkvb/nlKjlhazlhbEgQVBJ44CBMjUwIOWtly/mrrXjgIHmlK/mjIHlubblj5HjgIHml6Dpl7TpmpTpmZDliLYKLSAqKktpa2lWb2ljZSoq77ya5aSH6YCJ44CB5LiJ56eN5qih5Z6L44CB5q+P5ZGoIDYwLDAwMCDlhY3otLnnp6/liIbjgIHpnIAgR2VldGVzdCDpqozor4EKCiMjIPCfjqQg5YWz5LqO5Y+C6ICD6Z+z6aKRCgrlj4LogIPpn7PpopHnmoTotKjph4/nm7TmjqXlvbHlk43lhYvpmobmlYjmnpzjgILlu7rorq7vvJoKCi0g5pe26ZW/IDUtMTUg56eS77yM5riF5pmw5peg5Zmq6Z+zCi0g6YG/5YWN6IOM5pmv6Z+z5LmQ5oiW5aSa5Lq66K+06K+dCi0g5Y+v5Lul5L+d5a2Y5aSa5Liq6Z+z5rqQ5bm26ZqP5pe25YiH5o2iCi0g5aaC6ZyA5Y+Y6YCf5pWI5p6c77yM6K+36aKE5YWI5aSE55CG5Y+C6ICD6Z+z6aKR77yM5pys5bel5YW35LiN5YGa5Y+Y6YCfCgojIyDwn46sIOWFs+S6juWJquaYoOW3peeoiwoK5a+85Ye655qEIFpJUCDop6PljovlkI7ljIXlkKvku6Xpobnnm67lkI3lkb3lkI3nmoTmlofku7blpLnvvIzlhoXlkKsgXGBkcmFmdF9jb250ZW50Lmpzb25cYOOAgVxgZHJhZnRfbWV0YV9pbmZvLmpzb25cYOOAgVxgYXVkaW9fbWFpbi53YXZcYCDlkowgXGBhdWRpb19tYWluLnNydFxg44CC5bCG5paH5Lu25aS55aSN5Yi25Yiw5Ymq5pig6I2J56i/55uu5b2VIFxgY29tLmx2ZWRpdG9yLmRyYWZ0XGAg5LiL5Y2z5Y+v5omT5byA44CC55S75biD5q+U5L6L77yaOToxNu+8jOWtl+W5leS9v+eUqOaAnea6kOm7keS9k++8iOeZveWtl+m7kei+ue+8jOWtl+WPtyAxMO+8ie+8jOS9jeS6jueUu+mdouS4i+aWueOAgumfs+mikeS4uuWujOaVtOWNleauteaWh+S7tuOAggoKIyMg8J+OtSDlhbPkuo4gQkdNIOa3t+mfs++8iHYyLjE0IOaWsOWinu+8iQoKLSBCR00g6buY6K6k6Z+z6YePIC0xOGRC77yI57qmIDAuMTI2IOWinuebiu+8ie+8jOWPr+WcqOiuvue9ruS4reiwg+iKggotIOS6uuWjsOauteW8gOWni+aXtiBCR00g6Ieq5YqoIGR1Y2tpbmcg6IezIC0yNGRC77yI5YaN6ZmNIDZkQu+8ie+8jOS6uuWjsOe7k+adnyAwLjMg56eS5ZCO5oGi5aSNCi0gZHVja2luZyDnrpfms5Xkvb/nlKggT2ZmbGluZUF1ZGlvQ29udGV4dCArIEdhaW5Ob2RlIOiHquWKqOWMluabsue6v++8jOWPguiAgyBwb2RtZXJnZS5odG1sIOeahCBzaWRlY2hhaW4g5a6e546wCi0g6L6T5Ye65YyF5ZCrIEJHTSDnmoTmnIDnu4jmt7fpn7MgV0FW77yM5ZCM5pe25L+d55WZ57qv5Lq65aOwIFdBViDkvZzkuLrlpIfku70KCiMjIPCfjpog5YWz5LqO6Z+z6YeP5b2S5LiA5YyW77yIdjIuMTQg5paw5aKe77yJCgotICoqcGVhayBub3JtYWxpemUqKu+8muaJgOacieauteW9kuS4gOWIsCAtM2RC77yI5Y+v6YWN572uIC02IH4gMGRC77yJCi0gKiror7Tor53kurogUk1TIOaLieW5syoq77ya5oyJ6K+06K+d5Lq65YiG57uE6K6h566XIFJNU++8jOiHquWKqOWinuebiuiuqeaJgOacieivtOivneS6uuWTjeW6puS4gOiHtO+8iOivr+W3riDCsTFkQu+8iQotICoq5aWz5aOw6L276YeP5Y6L57yp77yI5Y+v6YCJ77yJKirvvJrpmIjlgLwgLTIwZELjgIHmr5TkvosgMjox44CB5pS75Ye7IDVtc+OAgemHiuaUviA1MG1z77yM5rK75aWz5aOw5b+95aSn5b+95bCPCgojIyDwn5OdIOabtOaWsOaXpeW/lwoKIyMjIHYyLjE3LjAgKDIwMjYtMDYtMTgpCgoqKuS/ruWkjSoqCi0g5q616JC957yW6L6R5peg5rOV54K55Ye755qEIGJ1Z++8mnN0YXJ0R2VuZXJhdGUg5a6M5oiQ5ZCOIGBTLmlzR2VuZXJhdGluZyA9IGZhbHNlYCDlt7Lorr7nva7vvIzkvYYgYHJlbmRlclNlZ21lbnRUYWJsZSgpYCDmnKrooqvph43mlrDosIPnlKjvvIzlr7zoh7TliIbmrrXooajku43ku6Ui55Sf5oiQ5LitIueKtuaAgea4suafk++8iG9uY2xpY2sg5bGe5oCn57y65aSx77yJ44CC5L+u5aSN5ZCO5Zyo55Sf5oiQ5a6M5oiQ44CB5Y+W5raI55Sf5oiQ44CB5bqU55So5pu05pS55a6M5oiQ562J5omA5pyJIGBTLmlzR2VuZXJhdGluZ2Ag54q25oCB5Y+Y5YyW54K56YO96L+95YqgIGByZW5kZXJTZWdtZW50VGFibGUoKWAg6LCD55So77yM56Gu5L+d5YiG5q616KGo5aeL57uI5Lul5q2j56Gu55qE5Y+v57yW6L6R5oCB5pi+56S644CCCgojIyMgdjIuMTYuMCAoMjAyNi0wNi0xOCkKCioq5paw5aKeKioKLSDmrrXokL3nuqfmlofmnKznvJbovpHvvJrngrnlh7vliIbmrrXooaggc2VnLXRleHQg5Y2V5YWD5qC86L+b5YWl57yW6L6R5qih5byP77yM5pSv5oyBIDQg56eN5pm66IO95Zy65pmv77yaCiAgLSBhKSDmnKrnlJ/miJDmrrXnvJbovpHvvJrnvJbovpHlkI7nlKjmlrDmlofmnKznlJ/miJDvvIjljIXmi6zlhrfljbTmnJ/vvIkKICAtIGIpIOeUn+aIkOS4reautee8lui+ke+8muiHquWKqOemgeeUqOe8lui+keW5tuWbnumAgOWGheWuue+8jOm8oOagh+WPmOS4jeWPr+eUqOaAgQogIC0gYykg5bey55Sf5oiQ5L2G5ZCO57ut5pyq5a6M5oiQ77ya5YWI5a6M5oiQ5Y6f5bqP5YiX5Yiw5pyA5ZCO5LiA5q6177yM57uT5p2f5ZCO6YeN5paw55Sf5oiQ5pS55Yqo5q6177yM5pen55qE5Lii5byDCiAgLSBkKSDlhajpg6jlrozmiJDlkI7nvJbovpHvvJrlvIDlp4vlkIjmiJDmjInpkq7lj5gi5bqU55So5pu05pS5Iu+8jOWPqumHjeeUn+aIkOaUueWKqOaute+8jOacquaUueWKqOS4jeWKqO+8jOeUn+aIkOWQjumHjeaWsOaLvOWQiAotIOWOhuWPsuiusOW9lee8lui+keWbnumAgO+8muavj+adoeWOhuWPsuiusOW9leaWsOWinuOAkOe8lui+keOAkeaMiemSru+8jOWPr+i/mOWOn+aJgOacieWIhuaute+8iOWQq+mfs+mike+8ieWIsOS4u+eVjOmdoui/m+ihjOS/ruaUueWQjumHjeaWsOWvvOWHuu+8m+WIhuautemfs+mikeW3suS4ouWkseaXtuaMiemSrue9rueBsOS4jeWPr+eCuQoKKirkv67lpI0qKgotIOaXoAoKKirph43mnoQqKgotIGFkZEhpc3Rvcnkg546w5Zyo5L+d5a2Y5omA5pyJ5q616JC955qEIGF1ZGlvQmxvYiDmlbDnu4TlkozmlofmnKzvvIznlKjkuo7ljoblj7Llm57pgIAKCiMjIyB2Mi4xNS4wICgyMDI2LTA2LTE4KQoKKirmlrDlop4qKgotIOe7n+S4gOivleWQrOWIh+aNou+8muaJgOacieivleWQrOaMiemSru+8iEJHTeOAgemfs+iJsumihOiniOOAgUdMTSDlpITnkIbpooTop4jjgIFLaWtpVm9pY2Ug5q616JC96K+V5ZCs77yJ5pSv5oyBIuaSreaUvi/lgZzmraIi5oCB5YiH5o2i77yM6YG/5YWN6YeN5aSN5pKt5pS+5Y+g5YqgCi0gS2lraVZvaWNlIOauteiQveivleWQrO+8muavj+auteeUn+aIkOWujOavleWNs+WcqOWIhuauteihqOS4reaYvuekuuivleWQrOaMiemSru+8jOWPr+eri+WNs+ivleWQrOW9k+WJjeauteiQve+8jOaXoOmcgOetieW+heWFqOmDqOWQiOaIkOWujOaIkAotIOW3puWPs+S4pOagj+WTjeW6lOW8j+W4g+WxgO+8muWuveWxj++8iOKJpTEwMjRweO+8ieW3puWPs+W5tuaOkuaYvuekuu+8iOW3puS+p+WGheWuueWPr+a7muWKqCArIOWPs+S+pyBsb2cg5Zu65a6a77yJ77yb56qE5bGP6Ieq5Yqo5YiH5o2i5Li6IHRhYiDmqKHlvI/vvIgi5Y+C5pWw6K6+5a6aIiAvICLmjqfliLblj7Ai5Lik5LiqIHRhYu+8iQotIOWFg+aVsOaNrueUn+aIkOWinuW8uu+8muaWsOWiniLljp/lp4vmlrDpl7vopoHngrki6L6T5YWl5qGG77yI5Y+v6YCJ77yJ77yM5L2c5Li65o+Q56S66K+N5LiA6YOo5YiG5Y+R6YCB57uZIEdMTe+8m+agh+mimOaMiSJ45pyIeOaXpeWosei1hOavj+aXpeaXqeaKpe+8mnh4eCLmoLzlvI/nlJ/miJDvvJtTaG93bm90ZXMg5oyJ5Y+C6ICD5qC85byP6L6T5Ye677yI5YWz6ZSu6K+NIC8g5pys5pyf5Li76KaB5YaF5a65IC8g56ug6IqC6YCf6KeIIC8g5YWz5LqO5qCP55uu77yJCgoqKuS/ruWkjSoqCi0g5pegCgoqKumHjeaehCoqCi0g5Y676Zmk6K6+572u6Z2i5p2/5omA5pyJICIodjIuMTQpIiDmj5DnpLrlrZfmoLfvvIzkv53mjIHnlYzpnaLmlbTmtIEKCiMjIyB2Mi4xNC4wICgyMDI2LTA2LTE3KQoKKirmlrDlop4qKgotIEdMTSDns7vnu5/mj5DnpLror43lj6/lnKjorr7nva7kuK3nvJbovpHjgIHkv53lrZjliLAgbG9jYWxTdG9yYWdl44CB6ZqP6YWN572u5a+85YWl5a+85Ye6Ci0g6buY6K6k57O757uf5o+Q56S66K+N5paw5aKe6KeE5YiZ77ya6aG/5Y+3L+S5puWQjeWPty/noLTmipjlj7fnu5/kuIDovazpgJflj7fvvJvlsI/mlbDngrnor7si54K5IuaxieWtl++8m+W5tOS7vS/ml6XmnJ8v6YeR6aKdL+eZvuWIhuavlOeahOS4reaWh+ivu+azlQotIEJlZm9yZS9BZnRlciDlj4zmoI/pooTop4jpnaLmnb/vvJrlkIjmiJDliY3lj6/nnIvliLAgR0xNIOWkhOeQhuWJjeWQjuWvueavlO+8jEFmdGVyIOaWh+acrOahhuWPr+aJi+WKqOe8lui+keimhueblgotIOivtOivneS6uuS6pOabv+agoemqjO+8muaJq+aPj+WIhuautee7k+aenOajgOa1i+i/nue7reS4pOauteWQjOS4gOivtOivneS6uu+8jOmrmOS6ruWRiuitpiArICLoh6rliqjkuqTmm78i5oyJ6ZKuCi0gQkdNIOmbhuaIkO+8muS4iuS8oC/pgInmi6njgIHlj4zpn7Pph4/mi4nmnYbjgIE1IOenkueJh+auteWunuaXtuivleWQrOOAgXNpZGVjaGFpbiBkdWNraW5n44CB6YWN572u5Y+v5L+d5a2YL+WvvOWFpS/lr7zlh7oKLSDniYflpLTniYflsL7mi7zmjqXvvJrlj4LogIMgcG9kbWVyZ2UuaHRtbCDlrp7njrDvvIzmlK/mjIHmt6HlhaXmt6Hlh7ov55u05o6l5ou85o6l5Lik56eN5qih5byPCi0g5Lq65aOw6Z+z6YeP5b2S5LiA5YyW77yacGVhayBub3JtYWxpemUgKyDor7Tor53kurogUk1TIOaLieW5syArIOWPr+mAieWls+WjsOi9u+mHj+WOi+e8qQotIOagh+mimC9TaG93bm90ZXMvVGFncyDoh6rliqjnlJ/miJDvvJrlkIjmiJDlrozmiJDlkI7osIPnlKggR0xNIOeUn+aIkOaSreWuouWFg+aVsOaNrgotIOiuvue9rumhueWPmOabtOWNs+aXtiB0b2FzdCDmj5DnpLrvvIzkuI3pga7mjKHlip/og73ljLrvvIh0b2FzdCDnp7voh7Plj7PkuIvop5LvvIkKLSDmraPliJnpooTlpITnkIbmlrDlop7kuablkI3lj7cv6aG/5Y+3L+egtOaKmOWPty/nq5bnur/ovazpgJflj7fop4TliJnvvIjml6DpnIAgR0xNIOWNs+WPr+W3peS9nO+8iQotIOS4i+i9veaMiemSruaWsOWiniLkuIvovb0gV0FW77yI57qv5Lq65aOw77yJIumAiemhue+8jOWQqyBCR00g5pe25ZCM5pe25L+d55WZ5Lik5Lu9CgoqKuS/ruWkjSoqCi0g5L+d55WZIHYyLjEzIOa6kOeggeS4reeahCBcYC9cXC5kb2N4JC9cYCDmraPliJnlrZfpnaLph4/vvIjpgb/lhY0gZXNidWlsZCDmiZPljIXlkI7kuKLlpLHlj43mlpzmnaDnmoTmvZzlnKjpl67popjvvIkKLSDkv67lpI3pg6jnvbLniYjkuK0gTkVXX0ZVTkNUSU9OUyDmnKrms6jlhaXnmoTpl67popjvvIhcYDwvc2NyaXB0PlxgIOWcqOaooeadv+Wtl+espuS4suS4remcgOWGmeS9nCBcYDxcXC9zY3JpcHQ+XGDvvIkKLSDkv67lpI0gZ2VuZXJhdGVNZXRhZGF0YSDkuK0gXGBcXFxgXFxcYFxcXGBcYCDku6PnoIHlnZfmoIforrDlr7zoh7TmqKHmnb/lrZfnrKbkuLLmj5DliY3nu4jmraLnmoTor63ms5XplJnor68KLSDkv67lpI0gXGBhbGVydCgn5Y6f5paH77yaXFxuJylcYCDnrYnlrZfnrKbkuLLkuK0gXFxuIOiiq+aooeadv+Wtl+espuS4suino+mHiuS4uuWunumZheaNouihjOeahOivreazlemUmeivrwotIOS/ruWkjSBtZXRhZGF0YUNhcmQg5YWD57Sg5pyq5rOo5YWlIERPTSDlr7zoh7QgXGBFLm1ldGFkYXRhQ2FyZFxgIOS4uiBudWxsIOeahOmXrumimO+8iOeUqOato+WImeabv+aNouS7o+abv+Wtl+mdouWMuemFje+8iQoKKirph43mnoQqKgotIFJFQURNRSDkuI4gY2hhbmdlbG9nIOaPkOiHs+aWh+S7tuWktOmDqCBcYFJFQURNRV9DT05URU5UXGAg5bi46YeP77yMXGBnZXRSZWFkbWVDb250ZW50KClcYCDnm7TmjqXlvJXnlKjvvIzpgb/lhY3mupDnoIHkuI4gVUkg5pi+56S65LiN5LiA6Ie0CgoqKuWunua1i+mqjOivge+8iDIwMjYtMDYtMTfvvIkqKgotIOeUqCAyIOS4quecn+Wunumfs+iJsu+8iOWwj+Wosemfs+iJsiArIOS5kOS5kC3mkq3lrqLpn7PoibIy77yJKyAyNTA5IOWtl+aXqeaKpeaWh+ahiOa1i+ivlQotIDI5IOauteWFqOmDqOeUn+aIkOaIkOWKn++8jDAg5aSx6LSl77yM5oC75pe26ZW/IDY6MzUKLSDmlbDlrZcv5pel5pyf5q2j5YiZ6aKE5aSE55CG5q2j56Gu77yIMjAyNuKGkuS6jOmbtuS6jOWFreOAgTbmnIgxN+aXpeKGkuWFreaciOWNgeS4g+aXpeOAgeesrDM45bGK4oaS56ys5LiJ5Y2B5YWr5bGK562J77yJCi0gQVNSIOaKveagt+mqjOivgSA0IOaute+8jOWGheWuueWujOaVtOWPr+ivhuWIq++8jOaXoOauteiQveS4ouWksQotIOS5puWQjeWPty/pob/lj7cv56C05oqY5Y+35Zyo5pys5qyh5rWL6K+V5Lit5pyq5aSE55CG77yI5ZugIEdMTSDmnKrphY3nva7vvInvvIzpmo/lkI7lt7Lmt7vliqDmraPliJnlm57pgIDop4TliJkKCiMjIyB2Mi4xMy4wICgyMDI2LTA2LTEyKQoKLSDkv67lpI0gbnZDbG9uZVZvaWNlIOmfs+iJsuWkjeeUqO+8mm52UmVmZXJlbmNlSWQg546w5Zyo5q2j56Gu5Lyg6YCS77yM5bey5pyJ6Z+z6Imy5peg6ZyA6YeN5aSN5YWL6ZqGCi0g5L+u5aSN5peg6Z+z6aKR5pWw5o2u5pe255qE6Z+z6Imy5aSN55So77ya5Y2z5L2/IGxvY2FsU3RvcmFnZSDkuK3msqHmnIkgYmFzZTY0IOaVsOaNru+8jOWPquimgSByZWZlcmVuY2VJZCDmnInmlYjkuZ/og73lpI3nlKgKLSBHTE0g5pm66IO96aKE5aSE55CG77ya5pSv5oyBIEdMTS00LUZsYXNoIEFQSSDov5vooYzkuK3mlofmlbDlrZfjgIHnrKblj7fjgIHlpJrpn7PlrZfmmbrog73pooTlpITnkIYKLSBHTE0gQVBJIEtleSDnrqHnkIbvvJrorr7nva7kuK3mlrDlop4gQVBJIEtleSDovpPlhaXlkozmtYvor5XmjInpkq7vvIzmlK/mjIHlr7zlhaXlr7zlh7oKLSDpooTlpITnkIbmqKHlvI/pgInmi6nvvJrlhbPpl60v5Zue6YCA5qih5byP77yI5q2j5YiZ5aSx6LSl5pe255SoIEdMTe+8iS/lp4vnu4jkvb/nlKggR0xNCi0g6aKE5aSE55CG5a6J5YWo5qOA5p+l77ya5aaC5p6c6aKE5aSE55CG57uT5p6c5byC5bi477yI6L+H55+t77yJ77yM6Ieq5Yqo5Zue6YCA5Yiw5Y6f5paHCi0gR0xNIEFQSSDku6PnkIbvvJrpgJrov4cgV29ya2VyIOS7o+eQhuiwg+eUqCBHTE0gQVBJ77yMQVBJIEtleSDkuI3mmrTpnLLliLDlrqLmiLfnq68KLSBUVFMg6K+35rGC5pel5b+X77ya6K6w5b2V5Y+R6YCB5YiwIFRUUyDlvJXmk47nmoTmlofmnKzlhoXlrrnlkozplb/luqbvvIzkvr/kuo7osIPor5UKCiMjIyB2Mi4xMi4wICgyMDI2LTA2LTEyKQoKLSDnp7vpmaTpobbpg6jlj4LogIPpn7PpopHljaHvvJrph4fnlKgi5paH5pys5LyY5YWI4oaS5YaN5YiG6YWN6Z+z5rqQIuW3peS9nOa1gQotIOivtOivneS6uuWIhumFjeWNoemHjeaehO+8muWNleS6uuaooeW8j+S5n+aYvuekuiLpu5jorqQi6Z+z5rqQ5qe9Ci0g6Z+z5rqQ5LqS5pal77ya5bey6KKr5LiA5L2N6K+06K+d5Lq66YCJ5oup55qE6Z+z5rqQ77yM5Zyo5YW25LuW6K+06K+d5Lq655qE5LiL5ouJ5Lit572u54GwCi0g6Z+z5rqQ566h55CGIDIuMO+8muiuvue9rumdouadv+aWsOWinumihOiniOOAgemHjeWRveWQjeOAgeWQjOatpeeKtuaAgeaMh+ekugotIOaVsOWtly/nrKblj7fpooTlpITnkIbvvJroh6rliqjlsIbmlbDlrZfovazkuK3mlofor7vms5XvvIznrKblj7fovazmloflrZcKLSDlubTku70v5pel5pyfL+eUteivneivhuWIqwotIOmfs+a6kOaVsOaNrue7k+aehOWNh+e6p++8muaUr+aMgSBOVi9LSyDlj4zlvJXmk47pn7PoibIgSUQKLSDpn7PpopHljovnvKnvvJrmlrDlu7rpn7PmupDml7boh6rliqjph43ph4fmoLcgMjRrSHrjgIHmiKrlj5YgMTUg56eSCgojIyMgdjIuMTEuMCAoMjAyNi0wNi0xMSkKCi0g5aSa5Lq65peB55m95qih5byP77ya6Ieq5Yqo5qOA5rWL6K+06K+d5Lq65qCH6K6wCi0g5o2i6KGM57ut5o6l77ya5rKh5pyJ6K+06K+d5Lq65qCH6K6w55qE6KGM6Ieq5Yqo5b2S5bGe5LiK5LiA5Liq6K+06K+d5Lq6Ci0g6Ziy5ZGG5qOA5rWL77ya5b2T6K+06K+d5Lq65Y+w6K+N6YeP5Lil6YeN5LiN5Z2H6KGh5pe26K2m5ZGKCi0g6Ieq5a6a5LmJ6K+06K+d5Lq65qih5byP77ya5pSv5oyB5re75Yqg6Ieq5a6a5LmJ5q2j5YiZ6KGo6L6+5byPCi0g5aSa5Lq6IFNSVCDlrZfluZXvvJrlrZfluZXoh6rliqjmoIfms6jor7Tor53kurrlp5PlkI0KLSDlpJrkurrliarmmKDlr7zlh7rvvJrliarmmKDlt6XnqIvkuZ/mlK/mjIHlpJrkurrlrZfluZXmoIfnrb4KCiMjIyB2Mi45LjAgKDIwMjYtMDUtMjUpCgotIOaWsOWiniBLaWtpVm9pY2Ug5rig6YGT77ya5aSH6YCJIFRUUyDlvJXmk47vvIzkuInnp43lhY3otLnmqKHlnosKLSBHZWV0ZXN0IOS6uuacuumqjOivge+8mumAmui/hyBXb3JrZXIg5Luj55CG56Gu5L+dIElQIOS4gOiHtAotIOenr+WIhuS9memHj+afpeivou+8muWunuaXtuaYvuekuuWJqeS9meenr+WIhuOAgeW3sueUqOenr+WIhuWSjOmHjee9ruaXtumXtAotIExvZyDmjqfliLblj7DvvJrmlrDlop7kuovku7borrDlvZXmjqfliLblj7AKCiMjIyB2Mi44LjAgKDIwMjYtMDUtMjYpCgotIEpTWmlwIOaHkuWKoOi9ve+8muS7heWcqOmcgOimgeaXtuWKoOi9vQotIOenu+mZpOiwg+ivleaXpeW/l++8muWHj+WwkeaJp+ihjOW8gOmUgAotIOeugOWMluWtl+W5leeul+azle+8muS8mOWMluiHquWKqOaNouihjOeul+azlQotIERPTSDlhYPntKDnvJPlrZjvvJrlh4/lsJHph43lpI3mn6Xor6IKLSBIVFRQIOe8k+WtmO+8mua3u+WKoOmhtemdoue8k+WtmOWktAoKIyMjIHYyLjcuMCAoMjAyNi0wNS0yNSkKCi0g5L+u5aSNIFNSVCDml7bpl7TovbTmoLnmnKzpl67popjvvJrlvIPnlKjkvY3nva7ov73ouKrms5XvvIzmlLnnlKjlrZfnrKbmlbDntK/liqDms5UKLSDkv67lpI3liarmmKDlrZfluZXlkIzmraUKCiMjIyB2Mi42LjAgKDIwMjYtMDUtMjUpCgotIOS/ruWkjSBTUlQg5pe26Ze06L2077ya5L+u5q2j5a2X5bmV5LiO6Z+z6aKR5LiN5ZCM5q2lCi0g5L+u5aSNIFdBViDkuIvovb3vvJrnm7TmjqXkuIvovb3lt7LmnInmlofku7YKLSDmlofku7blkI3op4TliJnvvJrlr7zlhaUgZG9jeCDml7bmlofku7blkI3kuI4gZG9jeCDkuIDoh7QKLSDliarmmKAgWklQIOe7k+aehOinhOiMg+WMlgotIOeUn+aIkOWOhuWPsuWNh+e6p++8muS9v+eUqCBJbmRleGVkREIg5L+d5a2YCgojIyMgdjIuNS4wICgyMDI2LTA1LTI1KQoKLSDkv67lpI3liarmmKDlrZfluZXmmL7npLrvvJrlrZfluZXnsbvlnovmlLnkuLogc3VidGl0bGUKLSDkv67lpI3lrZfluZXmoLflvI/moLzlvI/vvJpzdHJva2Ug5qC85byP5a+56b2QIHB5SmlhbllpbmdEcmFmdCDop4TojIMKLSDooaXlhajlrZfluZXntKDmnZDlrZfmrrUKLSDkv67lpI3lrZfluZXlnZDmoIfvvJp0cmFuc2Zvcm0g5L2/55So5b2S5LiA5YyW5Z2Q5qCHIHk6LTAuOAoKIyMjIHYyLjQuMCAoMjAyNi0wNS0yNSkKCi0g6KeE6IyD5YyW5paH5Lu25ZCN77yaeXl5eW1tZGQtaGhtbXNzCi0gU1JUIOiHquWKqOaNouihjO+8muavj+ihjOS4jei2hei/hyAxNSDlrZcKLSDliarmmKDlrZfluZXmoLflvI/vvJrmgJ3mupDpu5HkvZPjgIHnmb3lrZfpu5HovrnjgIHlrZflj7cgMTAKLSDlkIzmrKHnlJ/miJDml7bpl7TmiLPkuIDoh7QKCiMjIyB2Mi4zLjAgKDIwMjYtMDUtMjQpCgotIOmfs+iJsuWkjeeUqOS8mOWMlu+8muS/neWtmOeahOmfs+a6kOWFs+iBlCBOaWNlVm9pY2Ug5pyN5Yqh5Zmo56uvIHJlZmVyZW5jZUlkCi0g5pm66IO96aqM6K+B77ya5L2/55So5bey5L+d5a2Y6Z+z6Imy5pe25qOA5p+l5pyN5Yqh5Zmo56uv5pyJ5pWI5oCnCi0g6Ieq5Yqo6YeN5paw5YWL6ZqG77ya5pyN5Yqh5Zmo56uv5aSx5pWI5pe26Ieq5Yqo6YeN5paw5YWL6ZqGCgojIyMgdjIuMi4wICgyMDI2LTA1LTI0KQoKLSDkv67lpI3mloflrZfliIbmrrXvvJpOaWNlVm9pY2Ug5qih5byP5LiL55+t5Y+l5LiN5YaN5ZCE6Ieq5oiQ5q61Ci0g5a6M5pW05o6n5Yi25Y+w5pel5b+X77ya5pa55L6/IEYxMiDosIPor5UKLSDliIbmrrXpgLvovpHph43mnoQKCiMjIyB2Mi4xLjAgKDIwMjYtMDUtMjQpCgotIOaWsOWiniBOaWNlVm9pY2Ug5L2c5Li65Li76KaBIFRUUyDlvJXmk44KLSDmlrDlop7lj4zlvJXmk47liIfmjaLlmagKLSDmlrDlop4gTmljZVZvaWNlIEFQSSDku6PnkIbvvIjmnI3liqHnq68gSE1BQy1TSEEyNTYg562+5ZCN77yJCi0g5paw5aKe5aOw6Z+z5YWL6ZqG5rWB56iL77ya5LiK5LygIOKGkiDorq3nu4Mg4oaSIFRUUwotIOaWsOWinumfs+a6kOWFs+iBlOWFi+mahiBJRAoKIyMjIHYyLjAuMCAoMjAyNi0wNS0yMykKCi0g5YWo5paw6YeN5p6E77yM5Z+65LqOIGtvenp6cS9pbmRleHR0czJhcGkgUkVTVCBBUEkKLSDmlrDlop7liarmmKDlt6XnqIsgWklQIOWvvOWHuuWKn+iDvQotIOaWsOWiniBTUlQg5a2X5bmV55Sf5oiQCi0g5paw5aKe6Z+z5rqQ566h55CG44CB5bm25Y+RIFRUUyDnlJ/miJDjgIHnlJ/miJDljoblj7LorrDlvZUKLSDmlrDlop4gV29yZCDmlofmoaPlr7zlhaXjgIHphY3nva7lr7zlhaUv5a+85Ye6Cg==';
  var binary = atob(b64);
  var bytes = new Uint8Array(binary.length);
  for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return new TextDecoder('utf-8').decode(bytes);
})();
// v2.14: Default GLM system prompt (editable in settings)
var DEFAULT_GLM_PROMPT = '你是一个TTS文本预处理助手。将输入文本转换为适合语音合成朗读的中文。规则：\\n'
  + '1. 数字转中文读法：403→四百零三，2026→二零二六，3.14→三点一四，2.14→二点一四，126.5→一百二十六点五\\n'
  + '2. 百分号 → 百分之：80.3%→百分之八十点三，50%→百分之五十\\n'
  + '3. 标点中转（远端 TTS 无法识别这些标点）：\\n'
  + '   - 顿号、→ 逗号，\\n'
  + '   - 书名号《》→ 直接去除（保留书名内容，例如《飞驰人生3》→ 飞驰人生3）\\n'
  + '   - 破折号——→ 逗号，\\n'
  + '   - 省略号……→ 等等\\n'
  + '   - 冒号：保留（用于说话人标记，TTS 可正确识别）\\n'
  + '4. 符号转文字：≥→大于等于，℃→摄氏度，×→乘以，/→或\\n'
  + '5. 保持原文意思不变，只调整朗读形式\\n'
  + '6. 不要添加解释、标注或前缀\\n'
  + '7. 直接输出转换结果';

var S = {
  engine: 'nicevoice',  // 'nicevoice' | 'indextts' | 'kikivoice'
  audioSources: [],       // saved voices: [{id, name, audioBase64, nvReferenceId, kkVoiceId, addedAt, lastSyncAt}]
  activeSourceId: '',
  segments: [],
  segmentBuffers: [],
  segmentDurations: [],
  resultWavBlob: null,
  resultSrt: '',
  resultWavUrl: null,     // Object URL for playback, reuse for download
  isGenerating: false,
  cancelRequested: false,
  elapsedTimer: null,
  elapsedStart: 0,
  downloadTimestamp: '',
  docxFileName: '',       // e.g. "0525 韩星见面会" (without .docx extension)
  projectName: '',        // for file naming: docxFileName or timestamp
  // NiceVoice state
  nvCloneBusy: false,
  // KikiVoice state
  kkUuid: 'vc-' + Date.now().toString(36) + '-' + Math.random().toString(36).substring(2,8),
  kkModel: 'kiki_core',
  kkConnected: false,
  kkCaps: null,
  kkQuota: { a: 60000, u: 0, m: 60000, r: 7 },
  cfResolve: null,
  cfReject: null,
  cfProxyUrl: '',
  cfDirectUrl: '',
  // Speaker state
  speakerMode: 'single',  // 'single' | 'multi'
  detectedSpeakers: [],    // [{name, lineCount, charCount}]
  speakerAssignments: {},  // { '小娱': sourceId, '乐乐': sourceId }
  speakerVoiceData: {},    // { '小娱': { audioFile, nvReferenceId, kkVoiceId }, ... } - populated during generation
  // New voice form state
  newVoiceAudioData: null, // { dataUrl, base64, wavBlob } - temp data for new voice form
  // Config
  config: {
    engine: 'nicevoice',
    // NiceVoice
    nvWait: 16,
    nvMaxChars: 150,
    nvMaxPoll: 60,
    // IndexTTS
    apiBase: DEFAULT_API,
    language: 'zh',
    maxChars: 250,
    concurrency: 1,
    retryCount: 2,
    pollInterval: 2000,
    // History
    maxHistory: 10,
    // Speaker patterns
    spBracket: true,     // enable 【name】 pattern
    spColon: true,       // enable name: pattern
    spCustomPatterns: [], // custom regex patterns (strings)
    spBalanceThreshold: 5, // anti-fool ratio threshold
    // v2.14: GLM system prompt (editable in settings)
    glmSystemPrompt: '',  // empty = use DEFAULT_GLM_PROMPT
    // v2.14: BGM mixing
    bgmEnabled: false,
    bgmAudioBase64: '',  // BGM file as base64 data URL
    bgmVolume: 0.126,  // -18dB ≈ 0.126 linear gain
    bgmDuckDepth: 0.5,  // ducking multiplier (0.5 = -6dB further)
    bgmDuckFadeMs: 300,
    // v2.14: Voice normalization
    voiceNormalizeEnabled: true,
    voiceTargetPeakDb: -3,
    speakerRmsEqualize: true,
    femaleCompress: true,
    // v2.14: Intro/Outro
    introOutroEnabled: false,
    introAudioBase64: '',
    outroAudioBase64: '',
    introOutroFadeMs: 500,
    introOutroMode: 'fade',  // 'fade' | 'direct'
  }
};

// ==================== JSZip Async Loader ====================
var _jszipPromise = null;
function loadJSZip() {
  if (!_jszipPromise) {
    _jszipPromise = new Promise(function(resolve, reject) {
      var s = document.createElement('script');
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
      s.onload = resolve;
      s.onerror = function() { reject(new Error('Failed to load JSZip')); };
      document.head.appendChild(s);
    });
  }
  return _jszipPromise;
}

var E = {};
function cacheElements() {
  ['apiDot','apiText','btnNV','btnIDX','generateBtn','genBtnText',
   'nvSettings','idxSettings','cfgEngine','settingsSourceList',
   'textInput','charCount','lineCount','segCount','docxInfo','docxDropOverlay',
   'textCard','cancelBtn','progressBar','progressFill','elapsed',
   'segTable','segBody','resultSection','resultAudio','settingsPanel','settingsOverlay',
   'historyModal','historyList','readmeModal','readmeBody','toast',
   'cfgNvWait','cfgNvMaxChars','cfgNvMaxPoll','cfgApiBase','cfgLanguage','btnKK','kkCfgCard','kkConn','kkSettings','logBox','cfPanel','cfIP','cfUUID','cfUrl','cfIframe','cfIframeOverlay','cfRaw',
   'cfgMaxChars','cfgConcurrency','cfgRetry','cfgPollInterval','cfgMaxHistory',
   'speakerCard','speakerList','speakerWarning','speakerWarningText','speakerModeLabel',
   'cfgSpBracket','cfgSpColon','speakerPatternsList','cfgSpBalance',
   'previewCard','previewBody','previewBtn','regenGlmBtn','applyPreviewBtn',
   'cfgGlmSystemPrompt','cfgBgmEnabled','cfgBgmVolume','cfgBgmVolumeVal','cfgBgmDuckDepth','cfgBgmDuckDepthVal',
   'cfgVoiceNormalize','cfgVoiceTargetPeak','cfgSpeakerRms','cfgFemaleCompress',
   'cfgIntroOutroEnabled','cfgIntroOutroFade','cfgIntroOutroMode',
   'alternationWarning','alternationFixBtn','metadataCard','metadataTitle','metadataShownotes','metadataTags','genMetadataBtn'
  ].forEach(function(id) { E[id] = document.getElementById(id); });
}

// ==================== Init ====================
window.addEventListener('DOMContentLoaded', function() {
  cacheElements();
  loadConfig();
  loadAudioSources();
  checkApiStatus();
  initDocxDragDrop();
  updateTextStats();
  applyConfigToUI();
  switchEngine(S.config.engine || 'nicevoice');
  // v2.14: Auto-save + toast on any settings change (debounced)
  var _saveTimer = null;
  document.getElementById('settingsPanel').addEventListener('change', function(e) {
    var tag = e.target.tagName;
    if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') {
      saveConfig();
      showToast('设置已保存', 'success');
    }
  });
  document.getElementById('settingsPanel').addEventListener('input', function(e) {
    var tag = e.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') {
      if (e.target.type === 'number' || e.target.type === 'password' || tag === 'TEXTAREA') {
        clearTimeout(_saveTimer);
        _saveTimer = setTimeout(function() {
          saveConfig();
          showToast('设置已保存', 'success');
        }, 800);
      }
      // live-update slider labels
      if (e.target.id === 'cfgBgmVolume') {
        var v = document.getElementById('cfgBgmVolumeVal');
        if (v) v.textContent = e.target.value + '%';
      }
      if (e.target.id === 'cfgBgmDuckDepth') {
        var v2 = document.getElementById('cfgBgmDuckDepthVal');
        if (v2) v2.textContent = e.target.value + '%';
      }
    }
  });
});

// ==================== Engine Switching ====================
function switchEngine(eng) {
  S.engine = eng;
  S.config.engine = eng;
  var btnNV = E.btnNV;
  var btnIDX = E.btnIDX;
  var btnKK = E.btnKK;
  var genBtn = E.generateBtn;
  var genBtnText = E.genBtnText;
  var nvSettings = E.nvSettings;
  var idxSettings = E.idxSettings;
  var kkSettings = E.kkSettings;
  var kkCfgCard = E.kkCfgCard;
  var cfgEngine = E.cfgEngine;

  btnNV.className = 'engine-btn' + (eng === 'nicevoice' ? ' active-nv' : '');
  btnIDX.className = 'engine-btn' + (eng === 'indextts' ? ' active-idx' : '');
  if (btnKK) btnKK.className = 'engine-btn' + (eng === 'kikivoice' ? ' active-kk' : '');

  if (nvSettings) nvSettings.style.display = 'none';
  if (idxSettings) idxSettings.style.display = 'none';
  if (kkSettings) kkSettings.style.display = 'none';
  if (kkCfgCard) kkCfgCard.className = 'card kk-cfg-card';

  if (eng === 'nicevoice') {
    genBtn.className = 'gen-btn nv-active';
    genBtnText.innerHTML = '&#x1F680; 开始合成 (NiceVoice)';
    if (nvSettings) nvSettings.style.display = '';
  } else if (eng === 'indextts') {
    genBtn.className = 'gen-btn idx-active';
    genBtnText.innerHTML = '&#x1F680; 开始合成 (IndexTTS)';
    if (idxSettings) idxSettings.style.display = '';
  } else if (eng === 'kikivoice') {
    genBtn.className = 'gen-btn kk-active';
    genBtnText.innerHTML = '&#x1F680; 开始合成 (KikiVoice)';
    if (kkSettings) kkSettings.style.display = '';
    if (kkCfgCard) kkCfgCard.className = 'card kk-cfg-card visible';
    // Auto-detect KikiVoice connection when switching to this engine
    if (!S.kkConnected) {
      setTimeout(function() { testKK(); }, 300);
    }
  }

  if (cfgEngine) cfgEngine.value = eng;
  updateTextStats();
  checkApiStatus();
}

// ==================== API Status Check ====================
async function checkApiStatus() {
  var dot = E.apiDot;
  var txt = E.apiText;
  dot.className = 'dot checking';
  txt.textContent = '检测中...';

  if (S.engine === 'nicevoice') {
    // Check NiceVoice API
    try {
      var resp = await fetch('/api/nv/getUploadUrl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suffix: '.wav' })
      });
      if (resp.ok) {
        var data = await resp.json();
        if (data.data && (data.data.url || data.data.uploadUrl)) {
          dot.className = 'dot online';
          txt.textContent = 'NiceVoice 在线';
        } else if (data.code !== undefined) {
          dot.className = 'dot online';
          txt.textContent = 'NiceVoice 在线';
        } else {
          dot.className = 'dot offline';
          txt.textContent = 'NiceVoice 响应异常';
        }
      } else {
        dot.className = 'dot offline';
        txt.textContent = 'NiceVoice 不可达';
      }
    } catch(e) {
      dot.className = 'dot offline';
      txt.textContent = 'NiceVoice 不可达';
    }
  } else if (S.engine === 'indextts') {
    // Check IndexTTS API
    try {
      var ctrl = new AbortController();
      var tid = setTimeout(function() { ctrl.abort(); }, 8000);
      var resp = await fetch(S.config.apiBase + '/', { signal: ctrl.signal });
      clearTimeout(tid);
      if (resp.ok) {
        var data = await resp.json();
        if (data.name || data.endpoints) {
          dot.className = 'dot online';
          txt.textContent = 'IndexTTS 在线';
        } else {
          dot.className = 'dot offline';
          txt.textContent = 'API 响应异常';
        }
      } else {
        dot.className = 'dot offline';
        txt.textContent = 'API 异常 (' + resp.status + ')';
      }
    } catch(e) {
      dot.className = 'dot offline';
      txt.textContent = 'API 不可达';
    }
  } else if (S.engine === 'kikivoice') {
    try {
      var ctrl = new AbortController();
      var tid = setTimeout(function() { ctrl.abort(); }, 8000);
      var resp = await fetch('/api/kiki/model-capabilities?uuid=' + encodeURIComponent(S.kkUuid), { signal: ctrl.signal });
      clearTimeout(tid);
      if (resp.ok) {
        var data = await resp.json();
        if (data.error_code === 0) {
          S.kkConnected = true; S.kkCaps = data;
          dot.className = 'dot online';
          txt.textContent = 'KikiVoice 在线';
          // Update KK connection status UI
          var cs = document.getElementById('kkConn');
          if (cs) { cs.className = 'kk-conn-status ok'; cs.innerHTML = '<span class="kk-conn-dot"></span>已连接'; }
          // Update model credit rates
          var c = data.model_capabilities || {};
          if (c.kiki_core) { var el = document.querySelector('#mCore .mc'); if (el) el.textContent = c.kiki_core.credit_rate + 'x'; }
          if (c.kiki_pro) { var el = document.querySelector('#mPro .mc'); if (el) el.textContent = c.kiki_pro.credit_rate + 'x'; }
          if (c.kiki_multilingual && c.kiki_multilingual.credit_rates && c.kiki_multilingual.credit_rates.v2) { var el = document.querySelector('#mMulti .mc'); if (el) el.textContent = c.kiki_multilingual.credit_rates.v2.rate + 'x'; }
          // Update quota info from capabilities response
          if (data.available_count !== undefined || data.user_tts_available_count !== undefined) {
            updKKQuota(data);
          }
        } else {
          S.kkConnected = false;
          dot.className = 'dot offline';
          txt.textContent = 'KikiVoice 不可用';
          var cs = document.getElementById('kkConn');
          if (cs) { cs.className = 'kk-conn-status fail'; cs.innerHTML = '<span class="kk-conn-dot"></span>失败'; }
        }
      } else {
        dot.className = 'dot offline';
        txt.textContent = 'KikiVoice 不可达';
        var cs = document.getElementById('kkConn');
        if (cs) { cs.className = 'kk-conn-status fail'; cs.innerHTML = '<span class="kk-conn-dot"></span>不可达'; }
      }
    } catch(e) {
      dot.className = 'dot offline';
      txt.textContent = 'KikiVoice 不可达';
      var cs = document.getElementById('kkConn');
      if (cs) { cs.className = 'kk-conn-status fail'; cs.innerHTML = '<span class="kk-conn-dot"></span>错误'; }
    }
  }
}

// ==================== DOCX Processing ====================
function initDocxDragDrop() {
  var card = E.textCard;
  var overlay = E.docxDropOverlay;
  var dragCounter = 0;
  card.addEventListener('dragenter', function(e) { e.preventDefault(); e.stopPropagation(); dragCounter++; overlay.classList.add('active'); });
  card.addEventListener('dragleave', function(e) { e.preventDefault(); e.stopPropagation(); dragCounter--; if (dragCounter <= 0) { dragCounter = 0; overlay.classList.remove('active'); } });
  card.addEventListener('dragover', function(e) { e.preventDefault(); e.stopPropagation(); });
  card.addEventListener('drop', function(e) {
    e.preventDefault(); e.stopPropagation(); dragCounter = 0; overlay.classList.remove('active');
    var files = e.dataTransfer.files;
    if (files.length > 0) {
      var file = files[0];
      if (file.name.endsWith('.docx')) { processDocxFile(file); }
      else if (file.type.startsWith('audio/')) { /* handled by audio zone */ }
      else { showToast('请拖入 .docx 格式的 Word 文档', 'error'); }
    }
  });
}

function handleDocxUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  if (!file.name.endsWith('.docx')) { showToast('请选择 .docx 格式的 Word 文档', 'error'); event.target.value = ''; return; }
  processDocxFile(file);
  event.target.value = '';
}

async function processDocxFile(file) {
  await loadJSZip();
  showToast('正在解析 Word 文档...', 'info');
  try {
    var arrayBuffer = await file.arrayBuffer();
    var zip = await JSZip.loadAsync(arrayBuffer);
    var docXml = await zip.file('word/document.xml').async('string');
    var parser = new DOMParser();
    var xmlDoc = parser.parseFromString(docXml, 'application/xml');
    var textParts = extractLeftColumnText(xmlDoc);
    if (textParts.length === 0) {
      var allText = extractAllParagraphText(xmlDoc);
      if (allText) {
        E.textInput.value = allText;
        updateTextStats();
        showToast('未找到表格，已提取全部文本', 'info');
      } else {
        showToast('文档中未找到可用文本', 'error'); return;
      }
    } else {
      var fullText = textParts.join('\\n');
      E.textInput.value = fullText;
      updateTextStats();
      showToast('已读取表格左列文本，共 ' + textParts.length + ' 段', 'success');
    }
    E.docxInfo.textContent = file.name;
    // Store docx filename (without .docx) for project naming
    S.docxFileName = file.name.replace(/\.docx$/i, '');
  } catch(err) {
    showToast('解析 Word 文档失败: ' + err.message, 'error');
  }
}

function extractXmlText(element, ns) {
  var paragraphs = element.getElementsByTagNameNS(ns, 'p');
  var lines = [];
  for (var p = 0; p < paragraphs.length; p++) {
    var runs = paragraphs[p].getElementsByTagNameNS(ns, 'r');
    var lineText = '';
    for (var r = 0; r < runs.length; r++) {
      var texts = runs[r].getElementsByTagNameNS(ns, 't');
      for (var t = 0; t < texts.length; t++) lineText += texts[t].textContent || '';
    }
    lines.push(lineText);
  }
  return lines;
}

function extractLeftColumnText(xmlDoc) {
  var ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main';
  var parts = [];
  var tables = xmlDoc.getElementsByTagNameNS(ns, 'tbl');
  for (var t = 0; t < tables.length; t++) {
    var rows = tables[t].getElementsByTagNameNS(ns, 'tr');
    for (var r = 0; r < rows.length; r++) {
      var cells = rows[r].getElementsByTagNameNS(ns, 'tc');
      if (cells.length >= 1) {
        var cellText = getCellText(cells[0], ns);
        if (cellText.trim()) parts.push(cellText.trim());
      }
    }
  }
  return parts;
}

function getCellText(tcElement, ns) {
  return extractXmlText(tcElement, ns).join('\\n');
}

function extractAllParagraphText(xmlDoc) {
  var ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main';
  var lines = extractXmlText(xmlDoc, ns);
  var filtered = [];
  for (var i = 0; i < lines.length; i++) { if (lines[i].trim()) filtered.push(lines[i].trim()); }
  return filtered.join('\\n');
}

// ==================== Config Management ====================
function loadConfig() {
  try {
    var saved = localStorage.getItem('ttsvoicelab_config');
    if (saved) {
      var c = JSON.parse(saved);
      Object.keys(c).forEach(function(k) { if (S.config[k] !== undefined) S.config[k] = c[k]; });
    }
  } catch(e) {}
  S.engine = S.config.engine || 'nicevoice';
}

function saveConfig() {
  readConfigFromUI();
  try { localStorage.setItem('ttsvoicelab_config', JSON.stringify(S.config)); } catch(e) {}
}

function applyConfigToUI() {
  var c = S.config;
  var el;
  el = E.cfgEngine; if (el) el.value = c.engine || 'nicevoice';
  el = E.cfgNvWait; if (el) el.value = c.nvWait || 16;
  el = E.cfgNvMaxChars; if (el) el.value = c.nvMaxChars || 150;
  el = E.cfgNvMaxPoll; if (el) el.value = c.nvMaxPoll || 60;
  el = E.cfgApiBase; if (el) el.value = c.apiBase;
  el = E.cfgLanguage; if (el) el.value = c.language;
  el = E.cfgMaxChars; if (el) el.value = c.maxChars;
  el = E.cfgConcurrency; if (el) el.value = c.concurrency;
  el = E.cfgRetry; if (el) el.value = c.retryCount;
  el = E.cfgPollInterval; if (el) el.value = c.pollInterval;
  el = E.cfgMaxHistory; if (el) el.value = c.maxHistory || 10;
  el = E.cfgSpBracket; if (el) el.checked = c.spBracket !== false;
  el = E.cfgSpColon; if (el) el.checked = c.spColon !== false;
  el = E.cfgSpBalance; if (el) el.value = c.spBalanceThreshold || 5;
  el = document.getElementById('cfgGlmApiKey'); if (el) el.value = c.glmApiKey || '';
  el = document.getElementById('cfgGlmPreprocess'); if (el) el.value = c.glmPreprocess || 'off';
  el = document.getElementById('cfgGlmSystemPrompt'); if (el) el.value = c.glmSystemPrompt || '';
  // v2.14: BGM
  el = document.getElementById('cfgBgmEnabled'); if (el) el.checked = c.bgmEnabled !== false && !!c.bgmAudioBase64;
  el = document.getElementById('cfgBgmVolume'); if (el) el.value = Math.round(Math.sqrt(c.bgmVolume || 0.126) * 100);
  el = document.getElementById('cfgBgmVolumeVal'); if (el) el.textContent = (Math.round(Math.sqrt(c.bgmVolume || 0.126) * 100)) + '%';
  el = document.getElementById('cfgBgmDuckDepth'); if (el) el.value = Math.round((c.bgmDuckDepth || 0.5) * 100);
  el = document.getElementById('cfgBgmDuckDepthVal'); if (el) el.textContent = Math.round((c.bgmDuckDepth || 0.5) * 100) + '%';
  // v2.14: Voice normalization
  el = document.getElementById('cfgVoiceNormalize'); if (el) el.checked = c.voiceNormalizeEnabled !== false;
  el = document.getElementById('cfgVoiceTargetPeak'); if (el) el.value = c.voiceTargetPeakDb || -3;
  el = document.getElementById('cfgSpeakerRms'); if (el) el.checked = c.speakerRmsEqualize !== false;
  el = document.getElementById('cfgFemaleCompress'); if (el) el.checked = c.femaleCompress !== false;
  // v2.14: Intro/Outro
  el = document.getElementById('cfgIntroOutroEnabled'); if (el) el.checked = c.introOutroEnabled !== false && (!!c.introAudioBase64 || !!c.outroAudioBase64);
  el = document.getElementById('cfgIntroOutroFade'); if (el) el.value = c.introOutroFadeMs || 500;
  el = document.getElementById('cfgIntroOutroMode'); if (el) el.value = c.introOutroMode || 'fade';
  renderBgmStatus();
  renderIntroOutroStatus();
  renderSpeakerPatterns();
}

function readConfigFromUI() {
  var c = S.config;
  c.engine = E.cfgEngine.value || 'nicevoice';
  c.nvWait = parseInt(E.cfgNvWait.value) || 16;
  c.nvMaxChars = parseInt(E.cfgNvMaxChars.value) || 150;
  c.nvMaxPoll = parseInt(E.cfgNvMaxPoll.value) || 60;
  c.apiBase = (E.cfgApiBase.value || '').trim() || DEFAULT_API;
  c.language = E.cfgLanguage.value || 'zh';
  c.maxChars = parseInt(E.cfgMaxChars.value) || 250;
  c.concurrency = Math.max(1, Math.min(5, parseInt(E.cfgConcurrency.value) || 1));
  c.retryCount = parseInt(E.cfgRetry.value) || 2;
  c.pollInterval = parseInt(E.cfgPollInterval.value) || 2000;
  c.maxHistory = Math.max(1, parseInt(E.cfgMaxHistory.value) || 10);
  c.spBracket = E.cfgSpBracket ? E.cfgSpBracket.checked : true;
  c.spColon = E.cfgSpColon ? E.cfgSpColon.checked : true;
  c.spBalanceThreshold = parseInt(E.cfgSpBalance ? E.cfgSpBalance.value : 5) || 5;
  c.glmApiKey = (document.getElementById('cfgGlmApiKey') ? document.getElementById('cfgGlmApiKey').value : '').trim();
  c.glmPreprocess = document.getElementById('cfgGlmPreprocess') ? document.getElementById('cfgGlmPreprocess').value : 'off';
  c.glmSystemPrompt = document.getElementById('cfgGlmSystemPrompt') ? document.getElementById('cfgGlmSystemPrompt').value : '';
  // v2.14: BGM
  c.bgmEnabled = document.getElementById('cfgBgmEnabled') ? document.getElementById('cfgBgmEnabled').checked : false;
  var bgmVolPct = parseInt(document.getElementById('cfgBgmVolume') ? document.getElementById('cfgBgmVolume').value : 35) || 35;
  c.bgmVolume = Math.pow(bgmVolPct / 100, 2);  // slider is sqrt scale
  var duckPct = parseInt(document.getElementById('cfgBgmDuckDepth') ? document.getElementById('cfgBgmDuckDepth').value : 50) || 50;
  c.bgmDuckDepth = duckPct / 100;
  // v2.14: Voice normalization
  c.voiceNormalizeEnabled = document.getElementById('cfgVoiceNormalize') ? document.getElementById('cfgVoiceNormalize').checked : true;
  c.voiceTargetPeakDb = parseInt(document.getElementById('cfgVoiceTargetPeak') ? document.getElementById('cfgVoiceTargetPeak').value : -3) || -3;
  c.speakerRmsEqualize = document.getElementById('cfgSpeakerRms') ? document.getElementById('cfgSpeakerRms').checked : true;
  c.femaleCompress = document.getElementById('cfgFemaleCompress') ? document.getElementById('cfgFemaleCompress').checked : true;
  // v2.14: Intro/Outro
  c.introOutroEnabled = document.getElementById('cfgIntroOutroEnabled') ? document.getElementById('cfgIntroOutroEnabled').checked : false;
  c.introOutroFadeMs = parseInt(document.getElementById('cfgIntroOutroFade') ? document.getElementById('cfgIntroOutroFade').value : 500) || 500;
  c.introOutroMode = document.getElementById('cfgIntroOutroMode') ? document.getElementById('cfgIntroOutroMode').value : 'fade';
}

// ==================== Audio Source Management ====================
function loadAudioSources() {
  try {
    var saved = localStorage.getItem('ttsvoicelab_sources');
    if (saved) S.audioSources = JSON.parse(saved);
    // Migrate old format: dataUrl -> audioBase64
    S.audioSources.forEach(function(src) {
      if (src.dataUrl && !src.audioBase64) {
        src.audioBase64 = src.dataUrl;
        delete src.dataUrl;
      }
      if (!src.kkVoiceId) src.kkVoiceId = null;
      if (!src.lastSyncAt) src.lastSyncAt = null;
    });
    saveAudioSources();
  } catch(e) {}
  renderSettingsVoiceList();
}

function saveAudioSources() {
  try { localStorage.setItem('ttsvoicelab_sources', JSON.stringify(S.audioSources)); } catch(e) {}
}

function buildVoiceDataFromSource(src) {
  var audioBase64 = src.audioBase64 || src.dataUrl || '';
  var base64 = audioBase64.split(',')[1] || audioBase64;
  return {
    audioFile: { name: src.name + '.wav', dataUrl: audioBase64, base64: base64 },
    nvReferenceId: src.nvReferenceId || null,
    kkVoiceId: src.kkVoiceId || null
  };
}

// ==================== Settings Voice Management ====================
function renderSettingsVoiceList() {
  var container = document.getElementById('settingsVoiceList');
  if (!container) return;
  if (!S.audioSources.length) {
    container.innerHTML = '<div style="font-size:12px;color:var(--text2);padding:6px">暂无保存的音源</div>';
    return;
  }
  var html = '';
  S.audioSources.forEach(function(src) {
    var syncStatus = 'yellow';
    var syncTitle = '未验证';
    if (src.nvReferenceId) { syncStatus = 'green'; syncTitle = 'NV已同步'; }
    if (src.kkVoiceId) { syncStatus = 'green'; syncTitle += ' KK已同步'; }
    if (!src.nvReferenceId && !src.kkVoiceId) { syncStatus = 'yellow'; syncTitle = '未上传至引擎'; }
    html += '<div class="source-item">';
    html += '<span class="s-name" ondblclick="renameVoice(\\'' + src.id + '\\')" title="双击重命名" style="cursor:pointer">' + escHtml(src.name) + '</span>';
    html += '<span style="display:inline-flex;align-items:center;gap:4px;margin-left:6px" title="' + escHtml(syncTitle) + '"><span style="width:8px;height:8px;border-radius:50%;background:var(--' + (syncStatus === 'green' ? 'green' : 'orange') + ');display:inline-block"></span><span style="font-size:10px;color:var(--text2)">' + escHtml(syncTitle) + '</span></span>';
    html += '<span class="s-actions">';
    html += '<button onclick="event.stopPropagation();previewVoice(\\'' + src.id + '\\', this)" title="试听" style="color:var(--blue)">&#x25B6;</button>';
    html += '<button onclick="event.stopPropagation();deleteVoiceConfirm(\\'' + src.id + '\\')" title="删除" style="color:var(--red)">&#x2716;</button>';
    html += '</span>';
    html += '</div>';
  });
  container.innerHTML = html;
}

var _voicePreviewAudio = null;
var _voicePreviewBtns = {};  // track buttons by voice id
function previewVoice(id, btnEl) {
  // If currently playing this voice, stop
  if (_voicePreviewAudio && _voicePreviewAudio._voiceId === id) {
    _voicePreviewAudio.pause();
    _voicePreviewAudio = null;
    if (_voicePreviewBtns[id]) _voicePreviewBtns[id].innerHTML = '&#x25B6;';
    return;
  }
  // Stop any other playing voice
  if (_voicePreviewAudio) {
    var oldId = _voicePreviewAudio._voiceId;
    _voicePreviewAudio.pause();
    _voicePreviewAudio = null;
    if (_voicePreviewBtns[oldId]) _voicePreviewBtns[oldId].innerHTML = '&#x25B6;';
  }
  var src = S.audioSources.find(function(s) { return s.id === id; });
  if (!src || !src.audioBase64) { showToast('无音频数据', 'error'); return; }
  if (btnEl) _voicePreviewBtns[id] = btnEl;
  _voicePreviewAudio = new Audio(src.audioBase64);
  _voicePreviewAudio._voiceId = id;
  _voicePreviewAudio.play().then(function() {
    if (_voicePreviewBtns[id]) _voicePreviewBtns[id].innerHTML = '&#x23F8;';
  }).catch(function() { showToast('播放失败', 'error'); });
  _voicePreviewAudio.onended = function() {
    _voicePreviewAudio = null;
    if (_voicePreviewBtns[id]) _voicePreviewBtns[id].innerHTML = '&#x25B6;';
  };
  _voicePreviewAudio.onerror = function() {
    _voicePreviewAudio = null;
    if (_voicePreviewBtns[id]) _voicePreviewBtns[id].innerHTML = '&#x25B6;';
    showToast('播放失败', 'error');
  };
}

function deleteVoiceConfirm(id) {
  var src = S.audioSources.find(function(s) { return s.id === id; });
  if (!src) return;
  if (confirm('确定删除音源 "' + src.name + '"？')) {
    S.audioSources = S.audioSources.filter(function(s) { return s.id !== id; });
    saveAudioSources();
    renderSettingsVoiceList();
    renderSpeakerAssignmentList();
    showToast('已删除音源', 'info');
  }
}

function renameVoice(id) {
  var src = S.audioSources.find(function(s) { return s.id === id; });
  if (!src) return;
  var newName = prompt('重命名音源:', src.name);
  if (newName && newName.trim()) {
    src.name = newName.trim();
    saveAudioSources();
    renderSettingsVoiceList();
    renderSpeakerAssignmentList();
  }
}

function showNewVoiceForm() {
  var form = document.getElementById('newVoiceForm');
  if (form) form.style.display = 'block';
}

function hideNewVoiceForm() {
  var form = document.getElementById('newVoiceForm');
  if (form) form.style.display = 'none';
  S.newVoiceAudioData = null;
  var nameInput = document.getElementById('newVoiceName');
  if (nameInput) nameInput.value = '';
  var uploadText = document.getElementById('settingsUploadText');
  if (uploadText) uploadText.textContent = '点击上传参考音频';
}

async function handleSettingsVoiceUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  var uploadText = document.getElementById('settingsUploadText');
  if (uploadText) uploadText.textContent = '正在处理...';

  try {
    var dataUrl = await new Promise(function(resolve) {
      var reader = new FileReader();
      reader.onload = function(e) { resolve(e.target.result); };
      reader.readAsDataURL(file);
    });

    var base64 = dataUrl.split(',')[1];
    // Compress: resample to 24kHz, trim to 15s
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
      var resp = await fetch(dataUrl);
      var arrayBuffer = await resp.arrayBuffer();
      var decoded = await ctx.decodeAudioData(arrayBuffer);
      var duration = Math.min(decoded.duration, 15);
      var trimSamples = Math.floor(duration * 24000);
      var channelData = decoded.getChannelData(0);
      if (trimSamples < channelData.length) channelData = channelData.slice(0, trimSamples);
      var trimBuffer = ctx.createBuffer(1, channelData.length, 24000);
      trimBuffer.copyToChannel(channelData, 0);
      var wavBlob = audioBufferToWav(trimBuffer);
      ctx.close();
      var optDataUrl = await new Promise(function(resolve) {
        var reader2 = new FileReader();
        reader2.onload = function(e) { resolve(e.target.result); };
        reader2.readAsDataURL(wavBlob);
      });
      S.newVoiceAudioData = { dataUrl: optDataUrl, base64: optDataUrl.split(',')[1], wavBlob: wavBlob };
    } catch(e) {
      S.newVoiceAudioData = { dataUrl: dataUrl, base64: base64, wavBlob: null };
    }
    if (uploadText) uploadText.textContent = '&#x2705; ' + file.name;
  } catch(e) {
    if (uploadText) uploadText.textContent = '处理失败';
  }
  event.target.value = '';
}

async function submitNewVoice() {
  if (!S.newVoiceAudioData) { showToast('请先上传音频', 'error'); return; }
  var nameInput = document.getElementById('newVoiceName');
  var name = nameInput ? nameInput.value.trim() : '';
  if (!name) { showToast('请输入音源名称', 'error'); return; }

  var newSource = {
    id: hexId(),
    name: name,
    audioBase64: S.newVoiceAudioData.dataUrl,
    nvReferenceId: null,
    kkVoiceId: null,
    addedAt: Date.now(),
    lastSyncAt: null
  };
  S.audioSources.push(newSource);
  saveAudioSources();
  hideNewVoiceForm();
  renderSettingsVoiceList();
  renderSpeakerAssignmentList();
  showToast('音源 "' + name + '" 已创建', 'success');
}

function exportVoices() {
  var exportData = {
    version: APP_VERSION,
    voices: S.audioSources.map(function(src) {
      return { id: src.id, name: src.name, audioBase64: src.audioBase64, nvReferenceId: src.nvReferenceId, kkVoiceId: src.kkVoiceId, addedAt: src.addedAt, lastSyncAt: src.lastSyncAt };
    })
  };
  downloadBlob(new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' }), 'tts-voice-lab-voices.json');
  showToast('音源已导出', 'success');
}

function importVoices(event) {
  var file = event.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function(e) {
    try {
      var data = JSON.parse(e.target.result);
      var voices = data.voices || [];
      var imported = 0;
      voices.forEach(function(v) {
        // Skip duplicates by name
        if (!S.audioSources.find(function(s) { return s.name === v.name; })) {
          S.audioSources.push({
            id: v.id || hexId(),
            name: v.name,
            audioBase64: v.audioBase64 || v.dataUrl,
            nvReferenceId: v.nvReferenceId || null,
            kkVoiceId: v.kkVoiceId || null,
            addedAt: v.addedAt || Date.now(),
            lastSyncAt: v.lastSyncAt || null
          });
          imported++;
        }
      });
      saveAudioSources();
      renderSettingsVoiceList();
      renderSpeakerAssignmentList();
      showToast('导入 ' + imported + ' 个音源（跳过 ' + (voices.length - imported) + ' 个重复）', 'success');
    } catch(err) { showToast('导入失败: ' + err.message, 'error'); }
  };
  reader.readAsText(file);
  event.target.value = '';
}

function deleteAudioSource(id) {
  S.audioSources = S.audioSources.filter(function(s) { return s.id !== id; });
  if (S.activeSourceId === id) S.activeSourceId = '';
  saveAudioSources();
  renderSettingsVoiceList();
  renderSpeakerAssignmentList();
  showToast('已删除音源', 'info');
}

// ==================== Audio Upload & Preview ====================
// These functions are kept for internal use by speaker voice handling
function handleFileUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  loadAudioFile(file);
  event.target.value = '';
}

function handleAudioDrop(event) {
  event.preventDefault();
  event.stopPropagation();
  var files = event.dataTransfer.files;
  if (files.length > 0 && files[0].type.startsWith('audio/')) {
    loadAudioFile(files[0]);
  }
}

function loadAudioFile(file) {
  var reader = new FileReader();
  reader.onload = function(e) {
    var dataUrl = e.target.result;
    var base64 = dataUrl.split(',')[1];
    // Store as temporary data (used by internal functions)
    S.newVoiceAudioData = { dataUrl: dataUrl, base64: base64, wavBlob: null, fileName: file.name };
    showToast('已加载音频: ' + file.name + '，正在优化...', 'info');
    trimAndOptimizeAudio(dataUrl, file.name);
  };
  reader.readAsDataURL(file);
}

async function trimAndOptimizeAudio(dataUrl, fileName) {
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
    var resp = await fetch(dataUrl);
    var arrayBuffer = await resp.arrayBuffer();
    var decoded = await ctx.decodeAudioData(arrayBuffer);
    var duration = decoded.duration;
    var trimDuration = Math.min(duration, 15);
    var trimSamples = Math.floor(trimDuration * 24000);
    var channelData = decoded.getChannelData(0);
    if (trimSamples < channelData.length) {
      channelData = channelData.slice(0, trimSamples);
    }
    var trimBuffer = ctx.createBuffer(1, channelData.length, 24000);
    trimBuffer.copyToChannel(channelData, 0);
    var wavBlob = audioBufferToWav(trimBuffer);
    ctx.close();

    var reader2 = new FileReader();
    reader2.onload = function(ev) {
      var optDataUrl = ev.target.result;
      var optBase64 = optDataUrl.split(',')[1];
      // Update the temp voice data
      if (S.newVoiceAudioData && S.newVoiceAudioData.fileName === fileName) {
        S.newVoiceAudioData = { dataUrl: optDataUrl, base64: optBase64, wavBlob: wavBlob, fileName: fileName };
      }
      var sizeMB = (wavBlob.size / 1024 / 1024).toFixed(1);
      showToast('音频已优化（' + trimDuration.toFixed(1) + '秒，' + sizeMB + 'MB）', 'success');
    };
    reader2.readAsDataURL(wavBlob);
  } catch(err) {
    showToast('音频优化失败，使用原始文件', 'info');
  }
}

// updateAudioUI, clearAudio, switchAudioSource removed - no longer needed without Card 1

// ==================== Text Processing ====================
function updateTextStats() {
  var text = E.textInput.value;
  var chars = text.length;
  var lines = text ? text.split('\\n').length : 0;
  E.charCount.textContent = chars;
  E.lineCount.textContent = lines;
  var maxChars = S.engine === 'nicevoice' ? (S.config.nvMaxChars || 150) : S.engine === 'kikivoice' ? kkMaxChars() : (S.config.maxChars || 250);
  // Detect speakers first
  detectSpeakers(text);
  // Split text for segment count
  if (S.speakerMode === 'multi') {
    var totalSegs = 0;
    var spSegs = splitTextBySpeakers(text, maxChars);
    for (var si = 0; si < spSegs.length; si++) totalSegs += spSegs[si].segments.length;
    E.segCount.textContent = totalSegs;
  } else {
    var segs = splitTextForTTS(text, maxChars);
    E.segCount.textContent = segs.length;
  }
}

// ==================== Speaker Detection & Parsing ====================
var SPEAKER_COLORS = ['#a29bfe', '#55efc4', '#74b9ff', '#fdcb6e', '#e17055', '#fd79a8', '#6c5ce7', '#00b894'];

function getSpeakerPatterns() {
  var patterns = [];
  // Built-in 【name】 pattern
  if (S.config.spBracket !== false) {
    patterns.push({ regex: /^【(.+?)】\\s*/, name: '【姓名】' });
  }
  // Built-in name: pattern
  if (S.config.spColon !== false) {
    patterns.push({ regex: /^([^\\s：:]{1,8})[：:]\\s*/, name: '姓名：' });
  }
  // Custom patterns
  var customs = S.config.spCustomPatterns || [];
  for (var ci = 0; ci < customs.length; ci++) {
    try {
      patterns.push({ regex: new RegExp(customs[ci]), name: '自定义', custom: true });
    } catch(e) {}
  }
  return patterns;
}

function detectSpeakers(text) {
  if (!text || !text.trim()) {
    S.speakerMode = 'single';
    S.detectedSpeakers = [];
    updateSpeakerUI();
    return;
  }

  var patterns = getSpeakerPatterns();
  if (patterns.length === 0) {
    S.speakerMode = 'single';
    S.detectedSpeakers = [];
    updateSpeakerUI();
    return;
  }

  var lines = text.split('\\n');
  var speakerMap = {};
  var currentSpeaker = null;
  var firstSpeakerFound = false;

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    var matched = false;

    for (var pi = 0; pi < patterns.length; pi++) {
      var match = line.match(patterns[pi].regex);
      if (match && match[1]) {
        var name = match[1].trim();
        if (name && name.length <= 8 && name.length > 0) {
          currentSpeaker = name;
          firstSpeakerFound = true;
          var content = line.replace(patterns[pi].regex, '').trim();
          if (!speakerMap[name]) speakerMap[name] = { name: name, lineCount: 0, charCount: 0 };
          speakerMap[name].lineCount++;
          speakerMap[name].charCount += content.length;
          matched = true;
          break;
        }
      }
    }

    if (!matched && firstSpeakerFound && currentSpeaker) {
      // Line without speaker marker = continuation of previous speaker
      speakerMap[currentSpeaker].lineCount++;
      speakerMap[currentSpeaker].charCount += line.trim().length;
    }
  }

  var speakers = Object.values(speakerMap);
  if (speakers.length >= 2) {
    S.speakerMode = 'multi';
    S.detectedSpeakers = speakers;
    checkSpeakerBalance(speakers);
  } else if (speakers.length === 1 && firstSpeakerFound) {
    // Only one speaker detected but markers present
    S.speakerMode = 'single';
    S.detectedSpeakers = speakers;
    E.speakerWarning.style.display = 'flex';
    E.speakerWarningText.innerHTML = '检测到说话人标记，但只找到一个说话人 <b>' + escHtml(speakers[0].name) + '</b>。如果是多人文案，请检查是否遗漏了说话人标记。';
  } else {
    // No speaker markers found - single mode with "默认" speaker
    S.speakerMode = 'single';
    S.detectedSpeakers = [];
    E.speakerWarning.style.display = 'none';
  }

  updateSpeakerUI();
}

function checkSpeakerBalance(speakers) {
  var threshold = S.config.spBalanceThreshold || 5;
  if (speakers.length < 2) return;

  // Find max and min char counts
  var maxChars = 0, minChars = Infinity, maxName = '', minName = '';
  for (var i = 0; i < speakers.length; i++) {
    if (speakers[i].charCount > maxChars) { maxChars = speakers[i].charCount; maxName = speakers[i].name; }
    if (speakers[i].charCount < minChars) { minChars = speakers[i].charCount; minName = speakers[i].name; }
  }

  if (minChars > 0 && (maxChars / minChars) > threshold) {
    E.speakerWarning.style.display = 'flex';
    E.speakerWarningText.innerHTML = '<b>' + escHtml(maxName) + '</b> 的内容量（' + maxChars + '字）远多于 <b>' + escHtml(minName) + '</b>（' + minChars + '字），比例约 ' + Math.round(maxChars / minChars) + ':1。是否忘记在后续段落中标注说话人？<div class="sw-actions"><button onclick="dismissSpeakerWarning()">我已确认，继续</button></div>';
  } else {
    E.speakerWarning.style.display = 'none';
  }
}

function dismissSpeakerWarning() {
  E.speakerWarning.style.display = 'none';
}

function updateSpeakerUI() {
  var card = E.speakerCard;
  var label = E.speakerModeLabel;

  // Always show speaker card when there's text
  card.classList.add('visible');

  if (S.speakerMode === 'multi') {
    label.textContent = '多人模式（' + S.detectedSpeakers.length + '位说话人）';
    label.style.color = 'var(--green)';
    renderSpeakerAssignmentList();
  } else if (S.detectedSpeakers.length === 1) {
    label.textContent = '单人模式（检测到1位说话人标记）';
    label.style.color = 'var(--orange)';
    renderSpeakerAssignmentList();
  } else {
    label.textContent = '单人模式';
    label.style.color = 'var(--text2)';
    renderSpeakerAssignmentList();
  }

  // Update generate button validation state
  updateGenerateBtnState();
}

function renderSpeakerAssignmentList() {
  var container = E.speakerList;
  if (!container) return;

  var html = '';
  var speakers = S.speakerMode === 'multi' ? S.detectedSpeakers : [{ name: '默认', charCount: E.textInput.value.length, lineCount: E.textInput.value.split('\\n').length }];

  // Track which voices are already selected by other speakers
  var usedSourceIds = {};
  Object.keys(S.speakerAssignments).forEach(function(spName) {
    if (S.speakerAssignments[spName]) usedSourceIds[S.speakerAssignments[spName]] = spName;
  });

  for (var i = 0; i < speakers.length; i++) {
    var sp = speakers[i];
    var color = SPEAKER_COLORS[i % SPEAKER_COLORS.length];
    var assignedSource = S.speakerAssignments[sp.name] || '';

    html += '<div class="speaker-row" id="speakerRow_' + i + '">';
    html += '<span class="sp-color" style="background:' + color + '"></span>';
    html += '<span class="sp-name">' + escHtml(sp.name) + '</span>';
    if (sp.charCount !== undefined) html += '<span class="sp-stats">' + sp.charCount + '字</span>';
    html += '<select class="sp-select" data-speaker="' + escHtml(sp.name) + '" onchange="assignSpeakerVoice(this)">';
    html += '<option value="">-- 选择音源 --</option>';

    // Add saved audio sources
    for (var j = 0; j < S.audioSources.length; j++) {
      var src = S.audioSources[j];
      var sel = assignedSource === src.id ? ' selected' : '';
      var disabled = (usedSourceIds[src.id] && usedSourceIds[src.id] !== sp.name) ? ' disabled style="color:var(--text2);opacity:0.5"' : '';
      html += '<option value="' + escHtml(src.id) + '"' + sel + disabled + '>' + escHtml(src.name) + (disabled ? ' (已分配)' : '') + '</option>';
    }

    // Add "新建音源" option
    html += '<option value="__new__">新建音源...</option>';
    html += '</select>';

    // Show assigned voice info
    if (S.speakerVoiceData[sp.name]) {
      html += '<span class="sp-preview">&#x2705; 已分配</span>';
    }

    html += '</div>';

    // Inline new voice form (hidden by default)
    html += '<div class="speaker-new-voice" id="spNewVoice_' + i + '" style="display:none;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;margin:4px 0 8px ' + (sp.name === '默认' ? '0' : '24') + 'px">';
    html += '<div style="display:flex;gap:8px;margin-bottom:8px"><input type="text" id="spVoiceName_' + i + '" placeholder="音源名称" style="flex:1;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:6px 8px;border-radius:6px;font-size:13px"></div>';
    html += '<div class="upload-zone" id="spUploadZone_' + i + '" onclick="document.getElementById(\\'spVoiceFile_' + i + '\\').click()" style="padding:12px;cursor:pointer">';
    html += '<div class="uz-text" id="spUploadText_' + i + '">点击上传参考音频</div>';
    html += '</div>';
    html += '<input type="file" id="spVoiceFile_' + i + '" accept="audio/*" style="display:none" onchange="handleSpVoiceFileUpload(event, ' + i + ', \\'' + escHtml(sp.name) + '\\')">';
    html += '<div style="display:flex;gap:8px;margin-top:8px">';
    html += '<button class="clear-btn" onclick="submitSpNewVoice(' + i + ', \\'' + escHtml(sp.name) + '\\')" style="background:var(--green);color:#000;border-color:var(--green)">&#x2714; 提交</button>';
    html += '<button class="clear-btn" onclick="cancelSpNewVoice(' + i + ')">取消</button>';
    html += '</div></div>';
  }

  container.innerHTML = html;
}

function assignSpeakerVoice(selectEl) {
  var speakerName = selectEl.getAttribute('data-speaker');
  var value = selectEl.value;

  if (value === '__new__') {
    // Show inline new voice form for this speaker
    var idx = (S.speakerMode === 'multi' ? S.detectedSpeakers : [{ name: '默认' }]).findIndex(function(s) { return s.name === speakerName; });
    var form = document.getElementById('spNewVoice_' + idx);
    if (form) form.style.display = 'block';
    selectEl.value = S.speakerAssignments[speakerName] || '';
    return;
  }

  if (value) {
    S.speakerAssignments[speakerName] = value;
    // Load the audio source data for this speaker
    var src = S.audioSources.find(function(s) { return s.id === value; });
    if (src) {
      S.speakerVoiceData[speakerName] = buildVoiceDataFromSource(src);
    }
  } else {
    delete S.speakerAssignments[speakerName];
    delete S.speakerVoiceData[speakerName];
  }

  updateGenerateBtnState();
  // Re-render to update disabled states on other selects
  renderSpeakerAssignmentList();
}

// Temp storage for inline voice uploads per speaker
var _spVoiceTempData = {};

async function handleSpVoiceFileUpload(event, idx, speakerName) {
  var file = event.target.files[0];
  if (!file) return;
  var uploadText = document.getElementById('spUploadText_' + idx);
  if (uploadText) uploadText.textContent = '正在处理...';

  try {
    var dataUrl = await new Promise(function(resolve) {
      var reader = new FileReader();
      reader.onload = function(e) { resolve(e.target.result); };
      reader.readAsDataURL(file);
    });

    var base64 = dataUrl.split(',')[1];

    // Compress: resample to 24kHz, trim to 15s
    try {
      var ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
      var resp = await fetch(dataUrl);
      var arrayBuffer = await resp.arrayBuffer();
      var decoded = await ctx.decodeAudioData(arrayBuffer);
      var duration = Math.min(decoded.duration, 15);
      var trimSamples = Math.floor(duration * 24000);
      var channelData = decoded.getChannelData(0);
      if (trimSamples < channelData.length) channelData = channelData.slice(0, trimSamples);
      var trimBuffer = ctx.createBuffer(1, channelData.length, 24000);
      trimBuffer.copyToChannel(channelData, 0);
      var wavBlob = audioBufferToWav(trimBuffer);
      ctx.close();

      var optDataUrl = await new Promise(function(resolve) {
        var reader2 = new FileReader();
        reader2.onload = function(e) { resolve(e.target.result); };
        reader2.readAsDataURL(wavBlob);
      });

      _spVoiceTempData[idx] = { dataUrl: optDataUrl, base64: optDataUrl.split(',')[1], wavBlob: wavBlob, fileName: file.name };
    } catch(e) {
      _spVoiceTempData[idx] = { dataUrl: dataUrl, base64: base64, wavBlob: null, fileName: file.name };
    }

    if (uploadText) uploadText.textContent = '&#x2705; ' + file.name;
  } catch(e) {
    if (uploadText) uploadText.textContent = '处理失败，请重试';
  }
  event.target.value = '';
}

async function submitSpNewVoice(idx, speakerName) {
  var tempData = _spVoiceTempData[idx];
  if (!tempData) { showToast('请先上传音频', 'error'); return; }

  var voiceNameEl = document.getElementById('spVoiceName_' + idx);
  var voiceName = voiceNameEl ? voiceNameEl.value.trim() : '';
  if (!voiceName) voiceName = speakerName + '音色';

  // Save to audio sources
  var newSource = {
    id: hexId(),
    name: voiceName,
    audioBase64: tempData.dataUrl,
    nvReferenceId: null,
    kkVoiceId: null,
    addedAt: Date.now(),
    lastSyncAt: null
  };
  S.audioSources.push(newSource);
  saveAudioSources();

  // Assign to speaker
  S.speakerAssignments[speakerName] = newSource.id;
  S.speakerVoiceData[speakerName] = {
    audioFile: { name: voiceName + '.wav', dataUrl: tempData.dataUrl, base64: tempData.base64, wavBlob: tempData.wavBlob },
    nvReferenceId: null,
    kkVoiceId: null
  };

  delete _spVoiceTempData[idx];
  showToast('音源 "' + voiceName + '" 已创建并分配给 ' + speakerName, 'success');
  renderSpeakerAssignmentList();
  renderSettingsVoiceList();
  updateGenerateBtnState();
}

function cancelSpNewVoice(idx) {
  var form = document.getElementById('spNewVoice_' + idx);
  if (form) form.style.display = 'none';
  delete _spVoiceTempData[idx];
}

function updateGenerateBtnState() {
  var btn = E.generateBtn;
  // Check if all speakers (including 默认 in single mode) have voices assigned
  var speakersToCheck = S.speakerMode === 'multi' ? S.detectedSpeakers : [{ name: '默认' }];
  var allAssigned = true;
  for (var i = 0; i < speakersToCheck.length; i++) {
    var sp = speakersToCheck[i];
    if (!S.speakerVoiceData[sp.name] && !S.speakerAssignments[sp.name]) {
      allAssigned = false;
      break;
    }
  }
  if (!allAssigned) {
    btn.style.opacity = '0.6';
    btn.title = '请为所有说话人分配音源';
  } else {
    btn.style.opacity = '1';
    btn.title = '';
  }
}

// ==================== Speaker-Aware Text Splitting ====================
function splitTextBySpeakers(text, maxChars) {
  // Returns array of { speaker, segments: [{text, lines, segIndex}] }
  if (!text || !text.trim()) return [];

  var patterns = getSpeakerPatterns();
  var lines = text.split('\\n');
  var currentSpeaker = null;
  var speakerBlocks = []; // { speaker, lines: [{text, isContinuation}] }

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    var matched = false;

    for (var pi = 0; pi < patterns.length; pi++) {
      var match = line.match(patterns[pi].regex);
      if (match && match[1]) {
        var name = match[1].trim();
        if (name && name.length <= 8) {
          currentSpeaker = name;
          var content = line.replace(patterns[pi].regex, '').trim();
          if (content) {
            speakerBlocks.push({ speaker: name, text: content });
          }
          matched = true;
          break;
        }
      }
    }

    if (!matched && line.trim()) {
      // Continuation of previous speaker
      if (currentSpeaker) {
        speakerBlocks.push({ speaker: currentSpeaker, text: line.trim() });
      } else {
        // No speaker context yet, treat as default
        speakerBlocks.push({ speaker: null, text: line.trim() });
      }
    }
  }

  // Group consecutive blocks of the same speaker and split by maxChars
  var result = [];
  var currentGroup = null;

  for (var bi = 0; bi < speakerBlocks.length; bi++) {
    var block = speakerBlocks[bi];
    if (!currentGroup || currentGroup.speaker !== block.speaker) {
      if (currentGroup) result.push(currentGroup);
      currentGroup = { speaker: block.speaker, rawText: block.text, lines: [block.text] };
    } else {
      currentGroup.rawText += '\\n' + block.text;
      currentGroup.lines.push(block.text);
    }
  }
  if (currentGroup) result.push(currentGroup);

  // Now split each group's text into TTS segments
  for (var gi = 0; gi < result.length; gi++) {
    var group = result[gi];
    var segs = splitTextForTTS(group.rawText, maxChars);
    group.segments = segs;
    // Tag each segment with the speaker
    for (var si = 0; si < segs.length; si++) {
      segs[si].speaker = group.speaker;
    }
  }

  return result;
}

// Speaker pattern management
function addSpeakerPattern() {
  var input = document.getElementById('newSpeakerPattern');
  var pattern = input.value.trim();
  if (!pattern) { showToast('请输入正则表达式', 'error'); return; }
  try {
    new RegExp(pattern); // validate
  } catch(e) {
    showToast('正则表达式无效: ' + e.message, 'error');
    return;
  }
  if (!S.config.spCustomPatterns) S.config.spCustomPatterns = [];
  S.config.spCustomPatterns.push(pattern);
  saveConfig();
  renderSpeakerPatterns();
  input.value = '';
  showToast('已添加自定义说话人模式', 'success');
}

function removeSpeakerPattern(idx) {
  if (S.config.spCustomPatterns) {
    S.config.spCustomPatterns.splice(idx, 1);
    saveConfig();
    renderSpeakerPatterns();
  }
}

// ==================== Number/Symbol Preprocessing ====================
function numberToChinese(numStr) {
  var num = parseInt(numStr, 10);
  if (isNaN(num)) return numStr;
  if (num === 0) return '零';
  var digits = ['零','一','二','三','四','五','六','七','八','九'];
  var units = ['','十','百','千'];

  if (num >= 100000000) {
    var yi = Math.floor(num / 100000000);
    var rem = num % 100000000;
    var result = numberToChinese(String(yi)) + '亿';
    if (rem > 0) {
      if (rem < 10000000) result += '零';
      result += numberToChinese(String(rem));
    }
    return result;
  }
  if (num >= 10000) {
    var wan = Math.floor(num / 10000);
    var rem = num % 10000;
    var result = numberToChinese(String(wan)) + '万';
    if (rem > 0) {
      if (rem < 1000) result += '零';
      result += numberToChinese(String(rem));
    }
    return result;
  }

  var result = '';
  var str = String(num);
  var len = str.length;
  var hasZero = false;
  for (var i = 0; i < len; i++) {
    var d = parseInt(str[i], 10);
    var unitIdx = len - 1 - i;
    if (d === 0) {
      hasZero = true;
    } else {
      if (hasZero) { result += '零'; hasZero = false; }
      result += digits[d] + units[unitIdx];
    }
  }
  // Special case: 10-19 should be 十... not 一十...
  if (num >= 10 && num < 20 && result.startsWith('一十')) {
    result = result.substring(1);
  }
  return result;
}

function numberToChineseYear(numStr) {
  // Read each digit individually for year-like numbers
  var digitMap = ['零','一','二','三','四','五','六','七','八','九'];
  var result = '';
  for (var i = 0; i < numStr.length; i++) {
    var d = parseInt(numStr[i], 10);
    if (!isNaN(d)) result += digitMap[d];
    else result += numStr[i];
  }
  return result;
}

function preprocessTextForTTS(text) {
  if (!text) return text;

  var result = text;
  var _origLen = text.length;

  // 1. Handle percentage patterns first: X% or X.X%
  result = result.replace(/(\\d+(?:\\.\\d+)?)\\s*%/g, function(m, num) {
    var parts = num.split('.');
    var intPart = numberToChinese(parts[0]);
    var decPart = '';
    if (parts[1]) {
      decPart = '点';
      var digitMap = ['零','一','二','三','四','五','六','七','八','九'];
      for (var i = 0; i < parts[1].length; i++) {
        var d = parseInt(parts[1][i], 10);
        decPart += isNaN(d) ? parts[1][i] : digitMap[d];
      }
    }
    return '百分之' + intPart + decPart;
  });

  // 2. Date patterns: X月X日
  result = result.replace(/(\\d{1,2})\\s*月\\s*(\\d{1,2})\\s*[日号]/g, function(m, month, day) {
    return numberToChinese(month) + '月' + numberToChinese(day) + '日';
  });

  // 3. Year patterns: 4-digit numbers followed by 年
  result = result.replace(/(\\d{4})\\s*年/g, function(m, year) {
    return numberToChineseYear(year) + '年';
  });

  // 4. Phone numbers: 11 digits starting with 1
  result = result.replace(/1[3-9]\\d{9}/g, function(m) {
    var digitMap = ['零','一','二','三','四','五','六','七','八','九'];
    var r = '';
    for (var i = 0; i < m.length; i++) r += digitMap[parseInt(m[i], 10)];
    return r;
  });

  // 5. Decimal numbers: X.XX
  result = result.replace(/(\\d+)\\.(\\d+)/g, function(m, intPart, decPart) {
    var digitMap = ['零','一','二','三','四','五','六','七','八','九'];
    var r = numberToChinese(intPart) + '点';
    for (var i = 0; i < decPart.length; i++) {
      var d = parseInt(decPart[i], 10);
      r += isNaN(d) ? decPart[i] : digitMap[d];
    }
    return r;
  });

  // 6. Numbers with 万/亿 (keep Chinese units, convert the number part)
  result = result.replace(/(\\d+)\\s*万/g, function(m, num) {
    return numberToChinese(num) + '万';
  });
  result = result.replace(/(\\d+)\\s*亿/g, function(m, num) {
    return numberToChinese(num) + '亿';
  });

  // 7. Remaining multi-digit numbers (2+ digits)
  result = result.replace(/\\d{2,}/g, function(m) {
    // Check if it looks like a year (4 digits, not adjacent to Chinese units)
    if (m.length === 4) {
      return numberToChineseYear(m);
    }
    return numberToChinese(m);
  });

  // 8. Single digits
  result = result.replace(/\\d/g, function(m) {
    var digitMap = ['零','一','二','三','四','五','六','七','八','九'];
    return digitMap[parseInt(m, 10)];
  });

  // 9. Symbol disambiguation
  // Em dash: remove (pause)
  result = result.replace(/——/g, '');
  // Ellipsis
  result = result.replace(/……|……/g, '等等');
  // v2.14: Punctuation transit for TTS-unfriendly marks
  // 顿号 → 逗号
  result = result.replace(/、/g, '，');
  // 书名号《》→ 去除（保留书名内容）
  result = result.replace(/《/g, '').replace(/》/g, '');
  // 单个破折号 — → 逗号（双破折号 —— 已在上面处理）
  result = result.replace(/—/g, '，');
  // 竖线 | → 逗号
  result = result.replace(/\\|/g, '，');
  result = result.replace(/\\.{3,}/g, '等等');
  // Tilde → 至/到
  result = result.replace(/～/g, '至');
  // Hyphen/minus in range context: X-Y人, X-Y个
  result = result.replace(/([一二三四五六七八九十百千万零]+)-([一二三四五六七八九十百千万零]+)([人个条只本张架辆艘间场次块元角分])/g, function(m, a, b, unit) { return a + '到' + b + unit; });
  // Remaining hyphens in ranges with Chinese
  result = result.replace(/([一二三四五六七八九十百千万零]+)-([一二三四五六七八九十百千万零]+)/g, function(m, a, b) { return a + '到' + b; });
  // Hyphen used as dash/pause
  result = result.replace(/-/g, '');
  // Multiply
  result = result.replace(/×/g, '乘');
  // Plus
  result = result.replace(/\\+/g, '加');
  // Equals
  result = result.replace(/=/g, '等于');
  // Celsius
  result = result.replace(/℃/g, '度');
  // Degree
  result = result.replace(/°/g, '度');

  // Safety check: if preprocessing produced an empty or suspiciously short result,
  // return the original text instead
  if (!result || (result.length < 2 && _origLen > 2)) {
    console.warn('[PREPROCESS] Suspicious output: "' + result + '" from input len=' + _origLen + ', using original text');
    return text;
  }

  if (result.length !== _origLen) {
    console.log('[PREPROCESS] len ' + _origLen + '→' + result.length + ' | "' + text.substring(0,60) + '" → "' + result.substring(0,60) + '"');
  }
  return result;
}

// GLM-powered smart text preprocessing for TTS
async function glmPreprocessText(text) {
  var apiKey = S.config.glmApiKey;
  var mode = S.config.glmPreprocess || 'off';
  if (mode === 'off' || !apiKey) return null;

  var systemPrompt = S.config.glmSystemPrompt || DEFAULT_GLM_PROMPT;

  try {
    var resp = await fetch('/api/glm/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        apiKey: apiKey,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: text }
        ]
      })
    });
    var data = await resp.json();
    if (data.choices && data.choices[0] && data.choices[0].message) {
      var result = data.choices[0].message.content.trim();
      // Safety: if result is too different from input, reject it
      if (result.length < text.length * 0.3) {
        console.warn('[GLM-PREPROCESS] Result too short, rejecting: "' + result.substring(0, 60) + '"');
        return null;
      }
      return result;
    }
    return null;
  } catch(e) {
    console.warn('[GLM-PREPROCESS] Error:', e.message);
    return null;
  }
}

async function testGlmApiKey() {
  var apiKey = document.getElementById('cfgGlmApiKey').value.trim();
  if (!apiKey) { showToast('请输入 GLM API Key', 'error'); return; }
  showToast('正在测试 API Key...', 'info');
  try {
    var resp = await fetch('/api/glm/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        apiKey: apiKey,
        messages: [
          { role: 'user', content: '你好，请回复"连接成功"' }
        ]
      })
    });
    var data = await resp.json();
    if (data.choices && data.choices[0]) {
      showToast('GLM API Key 有效！', 'success');
    } else if (data.error) {
      showToast('API 错误: ' + (data.error.message || JSON.stringify(data.error)), 'error');
    } else {
      showToast('未知响应格式', 'error');
    }
  } catch(e) {
    showToast('连接失败: ' + e.message, 'error');
  }
}

// Enhanced preprocessTextForTTS with GLM support
async function preprocessTextForTTSSmart(text) {
  var mode = S.config.glmPreprocess || 'off';
  var apiKey = S.config.glmApiKey;

  // Always run regex-based preprocessing first
  var regexResult = preprocessTextForTTS(text);

  if (mode === 'off' || !apiKey) {
    return regexResult;
  }

  if (mode === 'fallback') {
    // Use GLM only if regex result looks same as input (no numbers/symbols were converted)
    var hasDigits = /\\d/.test(text);
    var hasSpecialSymbols = /[≥≤≠×÷@℃°%]/.test(text);
    if (!hasDigits && !hasSpecialSymbols) {
      return regexResult;  // No need for GLM
    }
    // If regex already converted everything, check quality
    var stillHasDigits = /\\d/.test(regexResult);
    if (!stillHasDigits) {
      return regexResult;  // Regex did its job
    }
    // Regex couldn't handle it fully, try GLM
  }

  // mode === 'always' or 'fallback' with unhandled content
  var glmResult = await glmPreprocessText(text);
  if (glmResult) {
    appLog('[PREPROCESS] GLM result used for text len=' + text.length, 'i');
    return glmResult;
  }

  // GLM failed, fall back to regex result
  return regexResult;
}

function renderSpeakerPatterns() {
  var container = E.speakerPatternsList;
  if (!container) return;
  var patterns = S.config.spCustomPatterns || [];
  if (patterns.length === 0) {
    container.innerHTML = '<div style="font-size:12px;color:var(--text2);padding:4px">暂无自定义模式</div>';
    return;
  }
  var html = '';
  for (var i = 0; i < patterns.length; i++) {
    html += '<div class="speaker-pattern-row">';
    html += '<input type="text" value="' + escHtml(patterns[i]) + '" readonly>';
    html += '<button class="sp-del" onclick="removeSpeakerPattern(' + i + ')">&#x2716;</button>';
    html += '</div>';
  }
  container.innerHTML = html;
}

function splitTextForTTS(text, maxChars) {
  if (!text || !text.trim()) return [];
  if (!maxChars) maxChars = S.engine === 'nicevoice' ? 150 : S.engine === 'kikivoice' ? kkMaxChars() : 250;

  var originalLines = text.split('\\n');

  // Build merged text and track line positions
  var merged = '';
  var lineInfos = [];
  for (var i = 0; i < originalLines.length; i++) {
    var lineText = originalLines[i];
    if (i > 0) merged += ' ';
    var startPos = merged.length;
    merged += lineText;
    lineInfos.push({ text: lineText, startPos: startPos, endPos: merged.length });
  }

  // Step 1: Split into sentences at punctuation boundaries
  var sentenceEndRe = /[。！？.!?…]/g;
  var breakPoints = [];
  var match;
  while ((match = sentenceEndRe.exec(merged)) !== null) {
    breakPoints.push(match.index + 1);
  }
  breakPoints.push(merged.length);

  var sentences = [];
  var sStart = 0;
  for (var b = 0; b < breakPoints.length; b++) {
    var bp = breakPoints[b];
    var sText = merged.substring(sStart, bp).trim();
    if (sText) {
      sentences.push({ text: sText, start: sStart, end: bp });
    }
    sStart = bp;
  }

  // Step 2: Merge sentences into segments up to maxChars
  var segments = [];
  var currentText = '';
  var currentStart = 0;

  for (var si = 0; si < sentences.length; si++) {
    var sent = sentences[si];
    var combinedLen = currentText.length + (currentText ? 1 : 0) + sent.text.length;

    if (currentText && combinedLen > maxChars) {
      // Current segment is full, push it
      var lines = getLinesInRange(currentStart, currentStart + currentText.length, lineInfos);
      segments.push({ text: currentText, lines: lines, segIndex: segments.length });
      currentText = sent.text;
      currentStart = sent.start;
    } else {
      // Add sentence to current segment
      currentText = currentText ? currentText + ' ' + sent.text : sent.text;
      if (!currentStart) currentStart = sent.start;
    }
  }

  // Push remaining
  if (currentText.trim()) {
    var lines = getLinesInRange(currentStart, currentStart + currentText.length, lineInfos);
    segments.push({ text: currentText.trim(), lines: lines, segIndex: segments.length });
  }

  // Step 3: Handle any segments that still exceed maxChars (very long sentences with no punctuation)
  var finalSegments = [];
  for (var fi = 0; fi < segments.length; fi++) {
    if (segments[fi].text.length > maxChars) {
      var subSegs = splitLongSegment(segments[fi].text, maxChars, 0, [{ text: segments[fi].text, startPos: 0, endPos: segments[fi].text.length }]);
      for (var ss = 0; ss < subSegs.length; ss++) finalSegments.push(subSegs[ss]);
    } else {
      finalSegments.push(segments[fi]);
    }
  }

  for (var fi = 0; fi < finalSegments.length; fi++) finalSegments[fi].segIndex = fi;

  return finalSegments;
}

function splitLongSegment(text, maxChars, globalStart, lineInfos) {
  var result = [];
  var parts = text.split(/[,，;；、]/);
  var current = '';
  for (var i = 0; i < parts.length; i++) {
    var part = parts[i];
    if (current.length + part.length + 1 > maxChars && current) {
      var cl = getLinesInRange(globalStart, globalStart + current.length, lineInfos);
      result.push({ text: current.trim(), lines: cl, segIndex: result.length });
      globalStart += current.length;
      current = part;
    } else {
      if (current) current += ',' + part;
      else current = part;
    }
  }
  if (current.trim()) {
    var cl = getLinesInRange(globalStart, globalStart + current.length, lineInfos);
    result.push({ text: current.trim(), lines: cl, segIndex: result.length });
  }
  return result;
}

function getLinesInRange(startPos, endPos, lineInfos) {
  var result = [];
  for (var i = 0; i < lineInfos.length; i++) {
    if (lineInfos[i].endPos > startPos && lineInfos[i].startPos < endPos) {
      result.push({ text: lineInfos[i].text, lineIndex: i });
    }
  }
  return result;
}

// ==================== NiceVoice TTS Generation ====================
async function nvCloneVoice(voiceDataOrFile) {
  // Accept either full voiceData object { audioFile, nvReferenceId, ... } or just audioFile
  var voiceData = voiceDataOrFile;
  var currentAudioFile = null;
  var currentNvRefId = null;

  // Detect if passed as voiceData (has .audioFile) or bare audioFile
  if (voiceData && voiceData.audioFile) {
    currentAudioFile = voiceData.audioFile;
    currentNvRefId = voiceData.nvReferenceId || voiceData.audioFile.nvReferenceId || null;
  } else {
    currentAudioFile = voiceDataOrFile;
    currentNvRefId = (voiceDataOrFile && voiceDataOrFile.nvReferenceId) || null;
  }

  if (!currentAudioFile || !currentAudioFile.base64) {
    // Even without base64, if we have a valid referenceId, try to reuse it
    if (currentNvRefId) {
      appLog('[NV] 无音频数据但有已保存的referenceId，尝试复用: ' + currentNvRefId, 'i');
      try {
        var verifyResp0 = await fetch('/api/nv/getSyncRefStatus', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ referenceId: currentNvRefId })
        });
        var verifyData0 = await verifyResp0.json();
        if (verifyData0.data && verifyData0.data.error === 0) {
          showToast('音色验证通过，复用已有音色', 'success');
          return currentNvRefId;
        }
      } catch(e) {}
    }
    showToast('请先分配参考音频', 'error');
    return null;
  }

  // ===== Check if we already have a referenceId =====
  if (currentNvRefId) {
    appLog('[NV] 正在验证已保存的音色...', 'i');

    try {
      var verifyResp = await fetch('/api/nv/getSyncRefStatus', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ referenceId: currentNvRefId })
      });
      var verifyData = await verifyResp.json();

      if (verifyData.data && verifyData.data.error === 0) {
        // Reference still valid on server — reuse it!
        showToast('音色验证通过，无需重新克隆', 'success');
        return currentNvRefId;
      } else {
        // Reference expired/invalid on server — need to re-clone
        showToast('音色已失效，正在重新克隆...', 'info');
        currentNvRefId = null;
      }
    } catch(verifyErr) {
      currentNvRefId = null;
    }
  }

  // ===== Full clone flow =====
  appLog('[NV] 正在上传参考音频...', 'i');
  S.nvCloneBusy = true;

  try {
    // Calculate audio file size and duration
    var audioBlob = currentAudioFile.wavBlob;
    var fileSize = audioBlob ? audioBlob.size : 0;
    var audioDuration = 10; // default, will be refined
    if (audioBlob) {
      try {
        var tempCtx = new (window.AudioContext || window.webkitAudioContext)();
        var tempBuf = await tempCtx.decodeAudioData(await audioBlob.arrayBuffer());
        audioDuration = tempBuf.duration;
        tempCtx.close();
      } catch(e) {
      }
    }

    // Step 1: Get upload URL
    var resp1 = await fetch('/api/nv/getUploadUrl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ suffix: '.wav', fileSize: fileSize, audioDuration: audioDuration })
    });
    var data1 = await resp1.json();
    appLog('[NV] getUploadUrl => ' + JSON.stringify(data1).substring(0, 500), 'i');
    if (!data1.data || (!data1.data.url && !data1.data.uploadUrl)) {
      throw new Error('获取上传地址失败: ' + JSON.stringify(data1));
    }
    var uploadUrl = data1.data.uploadUrl || data1.data.url;
    var referenceId = data1.data.referenceId || data1.data.refId;
    var filePath = data1.data.filePath || '';

    appLog('[NV] 正在上传音频文件...', 'i');

    // Step 2: Upload audio to presigned URL via proxy
    var resp2 = await fetch('/api/nv-upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uploadUrl: uploadUrl, audioBase64: currentAudioFile.base64 })
    });
    var data2 = await resp2.json();
    appLog('[NV] 上传结果 => ' + JSON.stringify(data2), 'i');
    if (!data2.ok) {
      throw new Error('上传音频失败: ' + data2.status);
    }

    appLog('[NV] 正在训练声音模型...', 'i');

    // Step 3: Save reference audio (trigger clone training)
    var resp3 = await fetch('/api/nv/saveRefAudio2', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        audioPath: filePath,
        referenceId: referenceId,
        referenceName: currentAudioFile.name || 'ref_audio',
        text: '',
        fileSize: fileSize,
        audioDuration: audioDuration
      })
    });
    var data3 = await resp3.json();
    appLog('[NV] saveRefAudio2 => ' + JSON.stringify(data3).substring(0, 500), 'i');
    if (!data3.data || !data3.data.referenceId) {
      throw new Error('创建声音克隆失败: ' + JSON.stringify(data3));
    }
    referenceId = data3.data.referenceId;

    // Step 4: Poll clone status
    var maxPoll = S.config.nvMaxPoll || 60;
    for (var i = 0; i < maxPoll; i++) {
 if (S.cancelRequested) { S.nvCloneBusy = false; return null; }
      await sleep(2000);
      appLog('[NV] 训练声音模型中... (' + (i + 1) + '/' + maxPoll + ')', 'i');

      var resp4 = await fetch('/api/nv/getSyncRefStatus', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ referenceId: referenceId })
      });
      var data4 = await resp4.json();
      if (i % 5 === 0 || (data4.data && data4.data.error === 0)) {
        appLog('[NV] getSyncRefStatus[' + (i+1) + '] => ' + JSON.stringify(data4).substring(0, 300), 'i');
      }
      if (data4.data && data4.data.error === 0) {
        S.nvCloneBusy = false;
        showToast('声音克隆完成', 'success');
        appLog('[NV] 声音克隆完成', 's');

        return referenceId;
      }
    }
    throw new Error('声音克隆超时');
  } catch(e) {
    appLog('[NV] 克隆失败: ' + e.message, 'e');
    S.nvCloneBusy = false;
    showToast('声音克隆失败: ' + e.message, 'error');
    return null;
  }
}

async function nvGenerateSegment(text, referenceId, segIdx) {
  var maxPoll = S.config.nvMaxPoll || 60;
  var retries = 0;
  var maxRetries = 3;

  while (retries <= maxRetries) {
    if (S.cancelRequested) {
      return null;
    }
    try {
      // Submit TTS request (NiceVoice only needs text + referenceId)
      var reqBody = { text: text, referenceId: referenceId };
      appLog('[NV] TTS请求 text="' + text.substring(0, 80) + '" (len=' + text.length + ') refId=' + referenceId, 'i');
      var resp1 = await fetch('/api/nv/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reqBody)
      });
      var data1 = await resp1.json();
      appLog('[NV] tts => ' + JSON.stringify(data1).substring(0, 500), 'i');
      // Handle rate limit by waiting and retrying
      if (data1.code === 70002006 || (data1.msg && data1.msg.toastZh && data1.msg.toastZh.indexOf('频繁') >= 0)) {
        if (retries < maxRetries) {
          retries++;
          await sleep(16000); // Wait 16s for rate limit
          continue;
        }
        throw new Error('请求过于频繁，请稍后重试');
      }
      if (!data1.data || !data1.data.taskSn) {
        throw new Error('TTS提交失败: ' + JSON.stringify(data1));
      }
      var taskSn = data1.data.taskSn;

      // Poll for result
      for (var p = 0; p < maxPoll; p++) {
        if (S.cancelRequested) {
          return null;
        }
        await sleep(2000);
        var resp2 = await fetch('/api/nv/getItemByTaskSn', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ taskSn: taskSn })
        });
        var data2 = await resp2.json();
        if (p % 5 === 0 || (data2.data && data2.data.statusStr === 'success')) {
          appLog('[NV] getItemByTaskSn[' + (p+1) + '] => ' + JSON.stringify(data2).substring(0, 300), 'i');
        }
        if (data2.data && data2.data.statusStr === 'success' && data2.data.audioUrl) {
          // Download audio via proxy
          var audioUrl = data2.data.audioUrl;
          var audioResp = await fetch('/api/audio-proxy?url=' + encodeURIComponent(audioUrl));
          if (!audioResp.ok) throw new Error('下载音频失败');
          var audioArrayBuffer = await audioResp.arrayBuffer();
          return new Blob([audioArrayBuffer], { type: 'audio/mpeg' });
        }
        if (data2.data && data2.data.statusStr === 'failed') {
          throw new Error('TTS生成失败');
        }
      }
      throw new Error('TTS轮询超时');
    } catch(e) {
      retries++;
      if (retries > maxRetries) throw e;
      await sleep(2000 * retries);
    }
  }
}

async function nvGenerateAll(segments, referenceId) {
  var waitMs = (S.config.nvWait || 16) * 1000;
  var bufIdx = 0;

  for (var i = 0; i < segments.length; i++) {
    if (S.cancelRequested) {
      break;
    }

    var seg = S.segments[i];
    seg.status = 'submitting';
    renderSegmentTable();

    if (i > 0) {
      // Wait between requests for rate limiting
      seg.status = 'processing';
      renderSegmentTable();
      showToast('等待 ' + (waitMs / 1000) + '秒后继续...', 'info');
      var waitStart = Date.now();
      while (Date.now() - waitStart < waitMs && !S.cancelRequested) {
        await sleep(500);
      }
      if (S.cancelRequested) {
        break;
      }
    }

    try {
      appLog('[NV] 生成段' + (i+1) + '/' + S.segments.length, 'i');
      var audioBlob = await nvGenerateSegment((S.previewEdits && S.previewEdits[i] !== undefined) ? S.previewEdits[i] : await preprocessTextForTTSSmart(seg.text), referenceId, i);
      if (!audioBlob) {
        seg.status = 'cancelled';
        renderSegmentTable();
        continue;
      }

      seg.audioBlob = audioBlob;
      // Get duration
      try {
        var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        var audioBuffer = await audioCtx.decodeAudioData(await audioBlob.arrayBuffer());
        seg.duration = audioBuffer.duration;
        audioCtx.close();
      } catch(de) {
        seg.duration = audioBlob.size / (24000 * 2);
      }

      seg.status = 'done';
      bufIdx++;
      appLog('[NV] 段' + (i+1) + ' OK', 's');
    } catch(e) {
      seg.status = 'error';
      seg.error = e.message;
    }
    renderSegmentTable();
    updateProgress();
  }
}

// ==================== IndexTTS Generation ====================
async function idxGenerateAll(segments) {
  var retryCount = S.config.retryCount;
  var pollInterval = S.config.pollInterval;
  var apiBase = S.config.apiBase;
  var language = S.config.language;
  var speakerWav = S.speakerVoiceData['默认'] ? S.speakerVoiceData['默认'].audioFile.base64 : null;
  var concurrency = S.config.concurrency;

  var indices = [];
  for (var i = 0; i < S.segments.length; i++) indices.push(i);

  var nextIdx = 0;
  var active = new Map();

  function launchNext() {
    while (nextIdx < indices.length && active.size < concurrency && !S.cancelRequested) {
      var segIdx = indices[nextIdx++];
      var p = idxProcessSegment(segIdx, apiBase, language, speakerWav, retryCount, pollInterval);
      var entry = { promise: p, segIdx: segIdx };
      p.then(function() { active.delete(entry); }, function() { active.delete(entry); });
      active.set(entry, entry);
    }
  }

  launchNext();
  while (active.size > 0) {
    if (S.cancelRequested) {
      for (var i = 0; i < S.segments.length; i++) {
        if (S.segments[i].status === 'pending' || S.segments[i].status === 'submitting' || S.segments[i].status === 'processing') {
          S.segments[i].status = 'cancelled';
        }
      }
      renderSegmentTable();
      updateProgress();
      break;
    }
    var promises = [];
    active.forEach(function(entry) { promises.push(entry.promise); });
    await Promise.race(promises);
    launchNext();
  }
}

async function idxProcessSegment(segIdx, apiBase, language, speakerWav, retryCount, pollInterval) {
  var seg = S.segments[segIdx];
  seg.status = 'submitting';
  renderSegmentTable();

  for (var attempt = 0; attempt <= retryCount; attempt++) {
    if (S.cancelRequested) {
      seg.status = 'cancelled';
      renderSegmentTable();
      break;
    }
    try {
      var submitResp = await fetch(apiBase + '/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: (S.previewEdits && S.previewEdits[i] !== undefined) ? S.previewEdits[i] : await preprocessTextForTTSSmart(seg.text), speaker_wav: speakerWav, language: language })
      });
      if (!submitResp.ok) {
        throw new Error('Submit failed: ' + submitResp.status);
      }
      var submitData = await submitResp.json();
      appLog('[IDX] generate => ' + JSON.stringify(submitData).substring(0, 300), 'i');
      if (!submitData.job_id) {
        throw new Error('No job_id returned');
      }

      seg.jobId = submitData.job_id;
      seg.status = 'processing';
      renderSegmentTable();

      for (var poll = 0; poll < 300; poll++) {
        if (S.cancelRequested) {
          seg.status = 'cancelled';
          renderSegmentTable();
          return;
        }
        await sleep(pollInterval);
        var statusResp = await fetch(apiBase + '/status/' + seg.jobId);
        if (!statusResp.ok) {
 continue;
        }
        var statusData = await statusResp.json();
        if (poll % 5 === 0 || statusData.status === 'completed') {
          appLog('[IDX] status[' + (poll+1) + '] => ' + JSON.stringify(statusData).substring(0, 200), 'i');
        }

        if (statusData.status === 'completed') {
          var resultResp = await fetch(apiBase + '/result/' + seg.jobId);
          if (!resultResp.ok) throw new Error('Failed to get audio');
          var audioArrayBuffer = await resultResp.arrayBuffer();
          seg.audioBlob = new Blob([audioArrayBuffer], { type: 'audio/wav' });
          try {
            var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            var audioBuffer = await audioCtx.decodeAudioData(audioArrayBuffer.slice(0));
            seg.duration = audioBuffer.duration;
            audioCtx.close();
          } catch(de) {
            seg.duration = audioArrayBuffer.byteLength / (44100 * 2);
          }
          seg.status = 'done';
          renderSegmentTable();
          updateProgress();
          return;
        } else if (statusData.status === 'error') {
          throw new Error('API error');
        }
      }
      throw new Error('Polling timeout');
    } catch(e) {
      if (attempt < retryCount && !S.cancelRequested) {
        seg.status = 'submitting';
        renderSegmentTable();
        await sleep(1000 * (attempt + 1));
        continue;
      }
      seg.status = 'error';
      seg.error = e.message;
      renderSegmentTable();
      updateProgress();
      return;
    }
  }
}


// ==================== Log Console ====================
function appLog(msg, type) {
  type = type || 'i';
  var c = document.getElementById('logBox');
  if (!c) return;
  var e = document.createElement('div');
  e.className = 'log-entry ' + type;
  e.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
  c.appendChild(e);
  c.scrollTop = c.scrollHeight;
}

// ==================== KikiVoice Functions ====================
var KK_MAX_RETRIES = 3;
var KK_MODEL_IDS = {'kiki_core':'mCore','kiki_pro':'mPro','kiki_multilingual':'mMulti'};

function kkMaxChars() {
  if (S.kkCaps && S.kkCaps.model_capabilities && S.kkCaps.model_capabilities[S.kkModel])
    return S.kkCaps.model_capabilities[S.kkModel].max_text_length || 1000;
  if (S.kkModel === 'kiki_pro') return 500;
  if (S.kkModel === 'kiki_multilingual') return 2000;
  return 1000;
}

function pickKKModel(m) {
  S.kkModel = m;
  Object.entries(KK_MODEL_IDS).forEach(function(entry) {
    var el = document.getElementById(entry[1]);
    if (el) el.className = 'kk-model' + (entry[0] === m ? ' sel' : '');
  });
  var isPro = m === 'kiki_pro';
  var emotionRow = document.getElementById('emotionRow');
  var intensityRow = document.getElementById('intensityRow');
  if (emotionRow) emotionRow.className = 'kk-param-row' + (isPro ? ' kk-pro-only active' : ' kk-pro-only');
  if (intensityRow) intensityRow.className = 'kk-param-row' + (isPro ? ' kk-pro-only active' : ' kk-pro-only');
  updateTextStats();
}

function updKKParam() {
  var speedEl = document.getElementById('kSpeed');
  var volEl = document.getElementById('kVolume');
  var speedValEl = document.getElementById('kSpeedVal');
  var volValEl = document.getElementById('kVolumeVal');
  if (speedEl && speedValEl) speedValEl.textContent = parseFloat(speedEl.value).toFixed(1);
  if (volEl && volValEl) volValEl.textContent = volEl.value;
}

async function kGet(path) {
  var r = await fetch('/api/kiki' + path + (path.includes('?') ? '&' : '?') + 'uuid=' + encodeURIComponent(S.kkUuid));
  var d;
  try { d = await r.json(); } catch(e) { d = { error_code: -1, msg: 'Invalid JSON' }; }
  appLog('[KK] GET ' + path + ' => ' + r.status + ' | error_code=' + (d.error_code !== undefined ? d.error_code : '?'), d.error_code === 0 ? 'i' : 'e');
  if (d.msg) appLog('[KK] msg: ' + d.msg, d.error_code === 0 ? 'i' : 'w');
  // Always log full response data for debugging
  appLog('[KK] 完整响应: ' + JSON.stringify(d).substring(0, 500), 'i');
  return d;
}

async function kPost(path, body) {
  var r = await fetch('/api/kiki' + path + (path.includes('?') ? '&' : '?') + 'uuid=' + encodeURIComponent(S.kkUuid), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Kiki-Uuid': S.kkUuid },
    body: JSON.stringify(body)
  });
  var d;
  try { d = await r.json(); } catch(e) { d = { error_code: -1, msg: 'Invalid JSON' }; }
  appLog('[KK] POST ' + path + ' => ' + r.status + ' | error_code=' + (d.error_code !== undefined ? d.error_code : '?'), d.error_code === 0 ? 'i' : 'e');
  if (d.msg) appLog('[KK] msg: ' + d.msg, d.error_code === 0 ? 'i' : 'w');
  // Always log full response data for debugging
  appLog('[KK] 完整响应: ' + JSON.stringify(d).substring(0, 500), 'i');
  if (d.available_count !== undefined || d.user_tts_available_count !== undefined) updKKQuota(d);
  return d;
}

async function testKK() {
  appLog('[KK] 检测连接...', 'i');
  var cs = document.getElementById('kkConn');
  if (cs) { cs.className = 'kk-conn-status pen'; cs.innerHTML = '<span class="kk-conn-dot"></span>检测中...'; }
  try {
    var d = await kGet('/model-capabilities');
    appLog('[KK] model-capabilities完整响应: ' + JSON.stringify(d).substring(0, 800), 'i');
    if (d.error_code === 0) {
      S.kkConnected = true; S.kkCaps = d;
      if (cs) { cs.className = 'kk-conn-status ok'; cs.innerHTML = '<span class="kk-conn-dot"></span>已连接'; }
      appLog('[KK] 连接成功！', 's');
      var c = d.model_capabilities || {};
      if (c.kiki_core) { var el = document.querySelector('#mCore .mc'); if (el) el.textContent = c.kiki_core.credit_rate + 'x'; }
      if (c.kiki_pro) { var el = document.querySelector('#mPro .mc'); if (el) el.textContent = c.kiki_pro.credit_rate + 'x'; }
      if (c.kiki_multilingual && c.kiki_multilingual.credit_rates && c.kiki_multilingual.credit_rates.v2) { var el = document.querySelector('#mMulti .mc'); if (el) el.textContent = c.kiki_multilingual.credit_rates.v2.rate + 'x'; }
      updateTextStats();
    } else {
      S.kkConnected = false;
      if (cs) { cs.className = 'kk-conn-status fail'; cs.innerHTML = '<span class="kk-conn-dot"></span>失败'; }
      appLog('[KK] 连接失败: ' + (d.msg || d.error_summary || JSON.stringify(d).substring(0, 300)), 'e');
    }
  } catch(e) {
    S.kkConnected = false;
    if (cs) { cs.className = 'kk-conn-status fail'; cs.innerHTML = '<span class="kk-conn-dot"></span>错误'; }
    appLog('[KK] 错误: ' + e.message, 'e');
  }
}

function updKKQuota(d) {
  if (!d) return;
  var a = d.available_count ?? d.available ?? d.user_tts_available_count;
  var u = d.used_count ?? d.used ?? d.user_tts_used_count;
  var m = d.max_count ?? d.max ?? S.kkQuota.m;
  var r = d.next_reset_days ?? d.resetTime;
  if (typeof a === 'number') S.kkQuota.a = a;
  if (typeof u === 'number') S.kkQuota.u = u;
  if (typeof m === 'number') S.kkQuota.m = m;
  if (typeof r === 'number') S.kkQuota.r = r;
  var qAvail = document.getElementById('qAvail');
  var qUsed = document.getElementById('qUsed');
  var qReset = document.getElementById('qReset');
  var qBar = document.getElementById('qBar');
  if (qAvail) qAvail.textContent = S.kkQuota.a.toLocaleString();
  if (qUsed) qUsed.textContent = S.kkQuota.u.toLocaleString();
  if (qReset) qReset.textContent = S.kkQuota.r + '天后重置';
  var p = S.kkQuota.m > 0 ? (S.kkQuota.a / S.kkQuota.m * 100) : 0;
  if (qBar) { qBar.style.width = p + '%'; qBar.className = 'kk-qb ' + (p >= 60 ? 'g' : p >= 30 ? 'y' : 'r'); }
  if (d.deducted_credits) appLog('[KK] 本次扣除: ' + d.deducted_credits, 'i');
}

// CF Verification
function showCFPanel(vpath, wip, rawResp) {
  appLog('[CF] 显示极验验证面板', 'i');
  appLog('[CF] Worker IP: ' + (wip || '未知'), 'i');
  appLog('[CF] 验证路径: ' + (vpath || '空'), 'i');
  appLog('[CF] 原始响应: ' + (rawResp || '{}'), 'w');
  if (!vpath) {
    appLog('[CF] 警告: validation_url_path为空，尝试使用默认路径', 'w');
    vpath = '/auth/geetest-validation';
  }
  S.cfProxyUrl = location.origin + '/api/kiki/geetest-page?uuid=' + encodeURIComponent(S.kkUuid) + '&path=' + encodeURIComponent(vpath);
  var cfIP = document.getElementById('cfIP');
  var cfUUID = document.getElementById('cfUUID');
  var cfUrl = document.getElementById('cfUrl');
  var cfRaw = document.getElementById('cfRaw');
  var cfPanel = document.getElementById('cfPanel');
  if (cfIP) cfIP.textContent = wip || '未知';
  if (cfUUID) cfUUID.textContent = S.kkUuid;
  if (cfUrl) cfUrl.textContent = S.cfProxyUrl;
  if (cfRaw) cfRaw.textContent = rawResp || '{}';
  if (cfPanel) cfPanel.style.display = 'block';
  var iframe = document.getElementById('cfIframe');
  var overlay = document.getElementById('cfIframeOverlay');
  if (overlay) overlay.style.display = 'flex';
  if (iframe) {
    iframe.onload = function() { if (overlay) overlay.style.display = 'none'; appLog('[CF] 验证页面已加载', 's'); };
    iframe.src = S.cfProxyUrl;
  }
  if (cfPanel) cfPanel.scrollIntoView({behavior: 'smooth', block: 'center'});
}
function hideCFPanel() {
  var cfPanel = document.getElementById('cfPanel');
  var cfIframe = document.getElementById('cfIframe');
  if (cfPanel) cfPanel.style.display = 'none';
  if (cfIframe) cfIframe.src = 'about:blank';
}
function openCFNewTab() { window.open(S.cfProxyUrl, '_blank'); appLog('[CF] 已在新标签页打开', 'i'); }
function waitForCFVerification() { return new Promise(function(resolve, reject) { S.cfResolve = resolve; S.cfReject = reject; }); }
function cfDone() {
  hideCFPanel();
  appLog('[CF] 用户确认验证完成，继续生成...', 's');
  if (S.cfResolve) { S.cfResolve(); S.cfResolve = null; S.cfReject = null; }
}
// Auto-detect geetest verification completion via postMessage from iframe
window.addEventListener('message', function(ev) {
  if (ev.data && ev.data.type === 'geetest-success') {
    appLog('[CF] 检测到极验验证成功（自动）', 's');
    cfDone();
  }
  if (ev.data && ev.data.type === 'geetest-error') {
    appLog('[CF] 极验验证失败', 'e');
  }
});
function cfCancel() {
  hideCFPanel();
  appLog('[CF] 用户取消验证', 'e');
  if (S.cfReject) { S.cfReject(new Error('用户取消CF验证')); S.cfReject = null; S.cfResolve = null; }
  S.cancelRequested = true;
}

// KikiVoice generation
async function kkGenerateAll(segments) {
  // Auto-detect connection if not already connected
  if (!S.kkConnected) {
    appLog('[KK] 未连接，自动检测连接...', 'w');
    await testKK();
    if (!S.kkConnected) throw new Error('KikiVoice连接失败，请检查网络');
  }
  var vn = (S.speakerVoiceData['默认'] && S.speakerVoiceData['默认'].audioFile && S.speakerVoiceData['默认'].audioFile.name) ? S.speakerVoiceData['默认'].audioFile.name.replace(/\\.[^.]+$/, '') : 'MyVoice';

  appLog('[KK] 1.上传声音...', 'i');
  if (!S.kkVoiceId) {
    var sd = await kGet('/get-sig');
    if (sd.error_code !== 0) throw new Error('签名失败:' + (sd.msg || sd.error_summary || JSON.stringify(sd).substring(0, 200)));
    appLog('[KK] 签名OK', 's');
    appLog('[KK] 上传音频文件...', 'i');
    var defaultVoice = S.speakerVoiceData['默认'];
    var defaultAudioFile = defaultVoice ? defaultVoice.audioFile : null;
    var uploadBlob = (defaultAudioFile && defaultAudioFile.wavBlob) || (defaultAudioFile && defaultAudioFile.base64 ? (function() { var binary = atob(defaultAudioFile.base64); var bytes = new Uint8Array(binary.length); for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i); return new Blob([bytes], {type: 'audio/wav'}); })() : null);
    if (!uploadBlob) throw new Error('无音频数据');
    var uploadFile = new File([uploadBlob], (defaultAudioFile.name || 'audio.wav'), { type: uploadBlob.type || 'audio/wav' });
    var fd = new FormData();
    fd.append('voice-file', uploadFile);
    fd.append('sig', sd.sig);
    fd.append('create_url', sd.kiki_voice_microservices_api_create_voice_url);
    fd.append('voice_name', vn);
    var r = await fetch('/api/kiki/upload-voice?uuid=' + encodeURIComponent(S.kkUuid), { method: 'POST', body: fd });
    var d;
    try { d = await r.json(); } catch(e) { throw new Error('上传响应解析失败'); }
    appLog('[KK] 上传: errcode=' + d.errcode, d.errcode === 0 ? 's' : 'e');
    if (d.errcode !== 0) {
      var em = {'-1':'上传失败','-2':'参数错误','-3':'语音达上限','-4':'不支持的格式','-5':'页面过期'};
      throw new Error('上传[' + d.errcode + ']:' + (em[d.errcode] || d.errmsg || '未知'));
    }
    S.kkVoiceId = d.voice_id;
    appLog('[KK] 声音ID: ' + S.kkVoiceId, 's');
  } else {
    appLog('[KK] 使用已有声音: ' + S.kkVoiceId, 'i');
  }

  appLog('[KK] 2.检测语言...', 'i');
  var lr = await kPost('/detect-language', { text: segments.join(' ').substring(0, 200) });
  var lc = 'zh';
  if (lr.error_code === 0 && lr.detected_language) {
    lc = lr.detected_language.code;
    appLog('[KK] 语言: ' + lr.detected_language.name + '(' + lc + ')', 's');
  } else appLog('[KK] 默认中文', 'w');

  appLog('[KK] 3.分段生成(' + S.segments.length + '段)', 'i');
  for (var i = 0; i < S.segments.length; i++) {
    if (S.cancelRequested) break;
    var seg = S.segments[i];
    seg.status = 'submitting';
    renderSegmentTable();
    var blob = null;
    for (var retry = 0; retry <= KK_MAX_RETRIES; retry++) {
      if (S.cancelRequested) { seg.status = 'cancelled'; renderSegmentTable(); break; }
      try {
        appLog('[KK] 创建任务(尝试' + (retry+1) + ')...', 'i');
        var td = await kPost('/create-clone-task', {
          text: (S.previewEdits && S.previewEdits[i] !== undefined) ? S.previewEdits[i] : await preprocessTextForTTSSmart(seg.text), voice_id: S.kkVoiceId, lang_code: lc, model_type: S.kkModel,
          emotion: S.kkModel === 'kiki_pro' ? (document.getElementById('kEmotion') ? document.getElementById('kEmotion').value : 'normal') : 'normal',
          intensity: S.kkModel === 'kiki_pro' ? (document.getElementById('kIntensity') ? document.getElementById('kIntensity').value : 'normal') : 'normal',
          gender: document.getElementById('kGender') ? parseInt(document.getElementById('kGender').value) : 0,
          speed: document.getElementById('kSpeed') ? parseFloat(document.getElementById('kSpeed').value) : 1.0,
          volume: document.getElementById('kVolume') ? parseInt(document.getElementById('kVolume').value) : 100,
          format: 'mp3', hq: document.getElementById('kHq') ? parseInt(document.getElementById('kHq').value) : 0,
          mver: S.kkModel === 'kiki_multilingual' ? 'v2' : 'default'
        });
        if (td.error_code !== 0 && td.error_code !== undefined) {
          if (td.error_code === 777) {
            appLog('[KK] 收到777 - 需要极验验证!', 'w');
            appLog('[KK] Worker IP: ' + (td.public_ip || '未知'), 'w');
            appLog('[KK] 验证路径: ' + (td.validation_url_path || '空'), 'w');
            appLog('[KK] auth_solution: ' + (td.auth_solution || 'GEETEST'), 'i');
            appLog('[KK] 完整777响应: ' + JSON.stringify(td), 'w');
            showCFPanel(td.validation_url_path || '', td.public_ip || '', JSON.stringify(td, null, 2));
            await waitForCFVerification();
            appLog('[KK] 验证完成，重试...', 'i');
            continue;
          }
          if (td.error_code === 'QUOTA_EXCEEDED' || td.error_code === 403) {
            if (td.quota_info) updKKQuota(td.quota_info);
            throw new Error('积分不足！剩余: ' + (td.available_count || 0));
          }
          if (td.error_code === 'IP_DISABLED') throw new Error('IP被禁用');
          throw new Error('任务失败[' + td.error_code + ']:' + (td.msg || td.error_summary || JSON.stringify(td).substring(0, 300)));
        }
        if (!td.success && td.error_code === undefined) throw new Error('任务失败: ' + JSON.stringify(td).substring(0, 300));
        var jid = td.job_id;
        if (!jid) throw new Error('无job_id');
        appLog('[KK] 任务: ' + jid, 's');
        if (td.quota_info) updKKQuota(td.quota_info);
        var hb = (td.heartbeat_interval_seconds || 3) * 1000;
        var est = td.estimated_time_seconds || 30;
        appLog('[KK] 预计' + est + 's', 'i');
        seg.status = 'processing';
        renderSegmentTable();
        var done = false;
        var maxPoll = Math.ceil(est / (hb / 1000)) + 30;
        for (var p = 0; p < maxPoll; p++) {
          if (S.cancelRequested) { seg.status = 'cancelled'; renderSegmentTable(); break; }
          await sleep(hb);
          var sd2 = await kGet('/job-status?job_id=' + jid);
          if (sd2.error_code !== 0) { appLog('[KK] 轮询错误:' + sd2.error_code, 'e'); continue; }
          var js = sd2.job_state;
          appLog('[KK] 轮询[' + (p+1) + ']: state=' + js, 'i');
          if (js === 1) {
            done = true;
            var au = sd2.audiourl;
            if (au) {
              appLog('[KK] 音频OK', 's');
              var ar = await fetch('/api/kiki-audio?url=' + encodeURIComponent(au) + '&uuid=' + encodeURIComponent(S.kkUuid));
              if (ar.ok) blob = await ar.blob(); else throw new Error('下载失败:' + ar.status);
            } else throw new Error('无音频URL');
            if (sd2.quota_info) updKKQuota(sd2.quota_info);
            else if (typeof sd2.user_tts_available_count === 'number') updKKQuota({available: sd2.user_tts_available_count, used: sd2.user_tts_used_count});
            break;
          }
          if (js === -1) throw new Error('任务失败: ' + (sd2.msg || sd2.error_summary || ''));
        }
        if (!done) throw new Error('任务超时');
        if (blob) break;
      } catch(e) {
        appLog('[KK] 尝试' + (retry+1) + '失败: ' + e.message, 'e');
        if (e.message.includes('积分') || e.message.includes('IP被禁') || e.message.includes('取消CF')) throw e;
        if (retry < KK_MAX_RETRIES) { appLog('5秒后重试...', 'w'); await sleep(5000); }
      }
    }
    if (blob) {
      seg.audioBlob = blob;
      try { var ac = new (window.AudioContext||window.webkitAudioContext)(); var ab = await ac.decodeAudioData(await blob.arrayBuffer()); seg.duration = ab.duration; ac.close(); } catch(de) { seg.duration = blob.size / (24000*2); }
      seg.status = 'done';
      appLog('[KK] 段' + (i+1) + ' OK (' + Math.round(blob.size/1024) + 'KB)', 's');
    } else {
      seg.status = S.cancelRequested ? 'cancelled' : 'error';
      if (!S.cancelRequested) seg.error = 'KikiVoice生成失败';
      appLog('[KK] 段' + (i+1) + ' 失败', 'e');
    }
    renderSegmentTable();
    updateProgress();
  }
}

// ==================== Main Generation Entry ====================
async function startGenerate() {
  var text = E.textInput.value.trim();
  if (!text) { showToast('请输入要合成的文本', 'error'); return; }

  // Validate voice assignments for all speakers
  var speakersToValidate = S.speakerMode === 'multi' ? S.detectedSpeakers : [{ name: '默认' }];
  for (var vi = 0; vi < speakersToValidate.length; vi++) {
    var spName = speakersToValidate[vi].name;
    if (!S.speakerVoiceData[spName]) {
      // Try to load from assignment
      if (S.speakerAssignments[spName]) {
        var src = S.audioSources.find(function(s) { return s.id === S.speakerAssignments[spName]; });
        if (src) {
          S.speakerVoiceData[spName] = buildVoiceDataFromSource(src);
        }
      }
      if (!S.speakerVoiceData[spName]) {
        showToast('请为说话人 "' + spName + '" 分配音源', 'error');
        return;
      }
    }
  }

  S.isGenerating = true;
  S.cancelRequested = false;
  // v2.14: previewEdits is set by applyPreviewAndGenerate, keep it through generation
  S.segments = [];
  S.segmentBuffers = [];
  S.segmentDurations = [];
  S.resultWavBlob = null;
  S.resultSrt = '';
  // Clean up previous Object URL
  if (S.resultWavUrl) { URL.revokeObjectURL(S.resultWavUrl); S.resultWavUrl = null; }
  S.downloadTimestamp = (function() {
    var now = new Date();
    return '' + now.getFullYear() + pad2(now.getMonth() + 1) + pad2(now.getDate()) + '-' + pad2(now.getHours()) + pad2(now.getMinutes()) + pad2(now.getSeconds());
  })();
  // Set project name: use docx filename if available, otherwise timestamp
  S.projectName = S.docxFileName || S.downloadTimestamp;

  var maxChars = S.engine === 'nicevoice' ? (S.config.nvMaxChars || 150) : S.engine === 'kikivoice' ? kkMaxChars() : (S.config.maxChars || 250);

  // Build segments based on speaker mode
  if (S.speakerMode === 'multi') {
    var spGroups = splitTextBySpeakers(text, maxChars);
    // Flatten all segments from all groups, preserving speaker info
    var allSegs = [];
    for (var gi = 0; gi < spGroups.length; gi++) {
      for (var si = 0; si < spGroups[gi].segments.length; si++) {
        var seg = spGroups[gi].segments[si];
        seg.speaker = spGroups[gi].speaker;
        allSegs.push(seg);
      }
    }
    S.segments = allSegs.map(function(seg) {
      return { text: seg.text, lines: seg.lines, speaker: seg.speaker, status: 'pending', jobId: null, audioBlob: null, duration: 0, error: null };
    });
    if (S.segments.length === 0) { showToast('文本为空或无法分段', 'error'); S.isGenerating = false; return; }
    appLog('[GEN] 引擎=' + S.engine + ' maxChars=' + maxChars + ' 分段数=' + S.segments.length + ' 说话人数=' + S.detectedSpeakers.length, 'i');
    // v2.14: Check speaker alternation issues
    checkSpeakerAlternation();
  } else {
    var segments = splitTextForTTS(text, maxChars);
    if (segments.length === 0) { showToast('文本为空或无法分段', 'error'); S.isGenerating = false; return; }
    S.segments = segments.map(function(seg) {
      return { text: seg.text, lines: seg.lines, speaker: null, status: 'pending', jobId: null, audioBlob: null, duration: 0, error: null };
    });
    appLog('[GEN] 引擎=' + S.engine + ' maxChars=' + maxChars + ' 分段数=' + segments.length, 'i');
  }

  // Update UI
  E.generateBtn.disabled = true;
  E.genBtnText.innerHTML = '<span class="spinner"></span> 合成中...';
  E.cancelBtn.style.display = 'block';
  E.progressBar.classList.add('active');
  E.progressFill.style.width = '0%';
  E.resultSection.classList.remove('active');
  renderSegmentTable();
  var logBox = document.getElementById('logBox'); if (logBox) logBox.innerHTML = '';
  S.kkVoiceId = null;

  S.elapsedStart = Date.now();
  updateElapsed();
  S.elapsedTimer = setInterval(updateElapsed, 1000);
  E.elapsed.style.display = 'block';

  if (S.engine === 'nicevoice') {
    // NiceVoice flow
    if (S.speakerMode === 'multi') {
      await nvMultiSpeakerGenerate();
    } else {
      var defaultVoice = S.speakerVoiceData['默认'];
      var referenceId = await nvCloneVoice(defaultVoice);
      if (referenceId && !S.cancelRequested) {
        await nvGenerateAll(S.segments, referenceId);
      }
    }
  } else if (S.engine === 'kikivoice') {
    // KikiVoice flow
    if (S.speakerMode === 'multi') {
      await kkMultiSpeakerGenerate();
    } else {
      await kkGenerateAll(S.segments);
    }
  } else {
    // IndexTTS flow
    if (S.speakerMode === 'multi') {
      await idxMultiSpeakerGenerate();
    } else {
      await idxGenerateAll(S.segments);
    }
  }

  // Done
  clearInterval(S.elapsedTimer);
  S.isGenerating = false;
  E.generateBtn.disabled = false;
  var btnLabel = S.engine === 'nicevoice' ? '&#x1F680; 开始合成 (NiceVoice)' : S.engine === 'kikivoice' ? '&#x1F680; 开始合成 (KikiVoice)' : '&#x1F680; 开始合成 (IndexTTS)';
  E.genBtnText.innerHTML = btnLabel;
  E.cancelBtn.style.display = 'none';
  // v2.17: Re-render segment table so cells become editable now that isGenerating=false
  renderSegmentTable();

  var successSegs = S.segments.filter(function(s) { return s.status === 'done'; });
  var failedSegs = S.segments.filter(function(s) { return s.status === 'error'; });

  if (successSegs.length === 0) {
    showToast('全部段生成失败' + (S.cancelRequested ? '（已取消）' : ''), 'error');
    return;
  }

  try { await concatenateAudio(); } catch(e) { showToast('音频拼接失败: ' + e.message, 'error'); return; }
  generateSrt();

  // Create Object URL for playback (also reused for download)
  S.resultWavUrl = URL.createObjectURL(S.resultWavBlob);
  E.resultAudio.src = S.resultWavUrl;
  E.resultSection.classList.add('active');
  // v2.14: Clear previewEdits after successful generation
  S.previewEdits = null;
  // v2.14: Show metadata generation card
  if (E.metadataCard) E.metadataCard.style.display = 'block';
  // v2.17: Final re-render to ensure all segments are editable
  renderSegmentTable();

  addHistory({
    text: text.substring(0, 200),
    engine: S.engine,
    segments: S.segments.length,
    success: successSegs.length,
    failed: failedSegs.length,
    date: new Date().toLocaleString('zh-CN'),
    timestamp: Date.now(),
    projectName: S.projectName
  });

  if (failedSegs.length > 0) {
    showToast('部分段生成失败 (' + failedSegs.length + '/' + S.segments.length + ')，已生成可用部分', 'error');
  } else {
    showToast('合成完成！共 ' + successSegs.length + ' 段' + (S.speakerMode === 'multi' ? '（' + S.detectedSpeakers.length + '位说话人）' : ''), 'success');
  }
}

// ==================== Multi-Speaker Generation Flows ====================
async function nvMultiSpeakerGenerate() {
  // Clone voices for each speaker first
  var speakerRefIds = {};
  for (var si = 0; si < S.detectedSpeakers.length; si++) {
    var sp = S.detectedSpeakers[si];
    var voiceData = S.speakerVoiceData[sp.name];
    if (!voiceData) { appLog('[NV] 说话人 ' + sp.name + ' 未分配音源', 'e'); continue; }

    appLog('[NV] 克隆说话人: ' + sp.name, 'i');
    var refId = await nvCloneVoice(voiceData);
    speakerRefIds[sp.name] = refId;

    // Save back the reference ID
    voiceData.nvReferenceId = refId;
    // Also update the saved source if any
    if (S.speakerAssignments[sp.name]) {
      var src = S.audioSources.find(function(s) { return s.id === S.speakerAssignments[sp.name]; });
      if (src) { src.nvReferenceId = refId; saveAudioSources(); }
    }

    if (S.cancelRequested) return;
  }

  // Generate segments using the appropriate reference ID
  var waitMs = (S.config.nvWait || 16) * 1000;
  for (var i = 0; i < S.segments.length; i++) {
    if (S.cancelRequested) break;

    var seg = S.segments[i];
    var refId = speakerRefIds[seg.speaker];
    if (!refId) {
      seg.status = 'error';
      seg.error = '说话人 ' + seg.speaker + ' 克隆失败';
      renderSegmentTable();
      updateProgress();
      continue;
    }

    seg.status = 'submitting';
    renderSegmentTable();

    if (i > 0) {
      seg.status = 'processing';
      renderSegmentTable();
      showToast('等待 ' + (waitMs / 1000) + '秒后继续...', 'info');
      var waitStart = Date.now();
      while (Date.now() - waitStart < waitMs && !S.cancelRequested) {
        await sleep(500);
      }
      if (S.cancelRequested) break;
    }

    try {
      appLog('[NV] 生成段' + (i+1) + '/' + S.segments.length + ' (说话人: ' + (seg.speaker || '默认') + ')', 'i');
      var audioBlob = await nvGenerateSegment((S.previewEdits && S.previewEdits[i] !== undefined) ? S.previewEdits[i] : await preprocessTextForTTSSmart(seg.text), refId, i);
      if (!audioBlob) {
        seg.status = 'cancelled';
        renderSegmentTable();
        continue;
      }

      seg.audioBlob = audioBlob;
      try {
        var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        var audioBuffer = await audioCtx.decodeAudioData(await audioBlob.arrayBuffer());
        seg.duration = audioBuffer.duration;
        audioCtx.close();
      } catch(de) {
        seg.duration = audioBlob.size / (24000 * 2);
      }
      seg.status = 'done';
      appLog('[NV] 段' + (i+1) + ' OK (' + (seg.speaker || '默认') + ')', 's');
    } catch(e) {
      seg.status = 'error';
      seg.error = e.message;
    }
    renderSegmentTable();
    updateProgress();
  }
}

async function kkMultiSpeakerGenerate() {
  // Generate segments using the appropriate voice for each speaker
  var kkVoiceIds = {};

  // Upload voices for each speaker
  for (var si = 0; si < S.detectedSpeakers.length; si++) {
    var sp = S.detectedSpeakers[si];
    var voiceData = S.speakerVoiceData[sp.name];
    if (!voiceData) { appLog('[KK] 说话人 ' + sp.name + ' 未分配音源', 'e'); continue; }

    appLog('[KK] 上传说话人音源: ' + sp.name, 'i');
    var voiceId = await kkUploadVoice(voiceData.audioFile, sp.name);
    kkVoiceIds[sp.name] = voiceId;
    if (S.cancelRequested) return;
  }

  // Generate segments
  for (var i = 0; i < S.segments.length; i++) {
    if (S.cancelRequested) break;
    var seg = S.segments[i];
    var voiceId = kkVoiceIds[seg.speaker];
    if (!voiceId) {
      seg.status = 'error';
      seg.error = '说话人 ' + seg.speaker + ' 音源上传失败';
      renderSegmentTable();
      updateProgress();
      continue;
    }
    await kkGenerateSegmentWithVoice(seg, voiceId, i);
  }
}

async function idxMultiSpeakerGenerate() {
  // For IndexTTS, generate segments with appropriate speaker_wav
  for (var i = 0; i < S.segments.length; i++) {
    if (S.cancelRequested) break;
    var seg = S.segments[i];
    var voiceData = S.speakerVoiceData[seg.speaker];
    var speakerWav = voiceData ? voiceData.audioFile.base64 : (S.speakerVoiceData['默认'] ? S.speakerVoiceData['默认'].audioFile.base64 : null);
    if (!speakerWav) {
      seg.status = 'error';
      seg.error = '说话人 ' + seg.speaker + ' 未分配音源';
      renderSegmentTable();
      updateProgress();
      continue;
    }
    await idxProcessSegmentWithWav(i, speakerWav);
  }
}

async function idxProcessSegmentWithWav(segIdx, speakerWav) {
  var seg = S.segments[segIdx];
  seg.status = 'submitting';
  renderSegmentTable();

  var retryCount = S.config.retryCount;
  var pollInterval = S.config.pollInterval;
  var apiBase = S.config.apiBase;
  var language = S.config.language;

  for (var attempt = 0; attempt <= retryCount; attempt++) {
    if (S.cancelRequested) {
      seg.status = 'cancelled';
      renderSegmentTable();
      return;
    }
    try {
      var submitResp = await fetch(apiBase + '/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: (S.previewEdits && S.previewEdits[i] !== undefined) ? S.previewEdits[i] : await preprocessTextForTTSSmart(seg.text), speaker_wav: speakerWav, language: language })
      });
      if (!submitResp.ok) throw new Error('Submit failed: ' + submitResp.status);
      var submitData = await submitResp.json();
      if (!submitData.job_id) throw new Error('No job_id returned');

      seg.jobId = submitData.job_id;
      seg.status = 'processing';
      renderSegmentTable();

      for (var poll = 0; poll < 300; poll++) {
        if (S.cancelRequested) { seg.status = 'cancelled'; renderSegmentTable(); return; }
        await sleep(pollInterval);
        var statusResp = await fetch(apiBase + '/status/' + seg.jobId);
        if (!statusResp.ok) continue;
        var statusData = await statusResp.json();
        if (statusData.status === 'completed') {
          var resultResp = await fetch(apiBase + '/result/' + seg.jobId);
          if (!resultResp.ok) throw new Error('Failed to get audio');
          var audioArrayBuffer = await resultResp.arrayBuffer();
          seg.audioBlob = new Blob([audioArrayBuffer], { type: 'audio/wav' });
          try {
            var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            var audioBuffer = await audioCtx.decodeAudioData(audioArrayBuffer.slice(0));
            seg.duration = audioBuffer.duration;
            audioCtx.close();
          } catch(de) { seg.duration = audioArrayBuffer.byteLength / (44100 * 2); }
          seg.status = 'done';
          renderSegmentTable();
          updateProgress();
          return;
        } else if (statusData.status === 'error') { throw new Error('API error'); }
      }
      throw new Error('Polling timeout');
    } catch(e) {
      if (attempt < retryCount && !S.cancelRequested) {
        seg.status = 'submitting';
        renderSegmentTable();
        await sleep(1000 * (attempt + 1));
        continue;
      }
      seg.status = 'error';
      seg.error = e.message;
      renderSegmentTable();
      updateProgress();
      return;
    }
  }
}

// KikiVoice helper: upload voice and get voice_id
async function kkUploadVoice(audioFile, speakerName) {
  appLog('[KK] 上传说话人音源: ' + speakerName, 'i');

  // Step 1: Get signature
  var sigData = await kGet('/get-sig');
  if (sigData.error_code !== 0) {
    appLog('[KK] 获取签名失败', 'e');
    return null;
  }
  var sig = sigData.sig || sigData.data?.sig || '';
  var createUrl = sigData.create_url || sigData.data?.create_url || '';

  if (!sig || !createUrl) {
    appLog('[KK] 签名数据不完整', 'e');
    return null;
  }

  // Step 2: Upload voice file
  try {
    var wavBlob = audioFile.wavBlob;
    if (!wavBlob) {
      // Need to create wav from base64
      var audioBytes = Uint8Array.from(atob(audioFile.base64), function(c) { return c.charCodeAt(0); });
      wavBlob = new Blob([audioBytes], { type: 'audio/wav' });
    }

    var formData = new FormData();
    formData.append('voice-file', wavBlob, speakerName + '.wav');
    formData.append('sig', sig);
    formData.append('create_url', createUrl);
    formData.append('voice_name', speakerName + '_' + Date.now());

    var uploadResp = await fetch('/api/kiki/upload-voice?uuid=' + encodeURIComponent(S.kkUuid), {
      method: 'POST',
      body: formData
    });

    var uploadData;
    try { uploadData = await uploadResp.json(); } catch(e) { uploadData = {}; }
    appLog('[KK] 上传结果: ' + JSON.stringify(uploadData).substring(0, 300), 'i');

    if (uploadData.error_code === 0 || uploadData.voice_id) {
      return uploadData.voice_id || uploadData.data?.voice_id;
    }

    // May need Geetest verification
    if (uploadData.validation_url_path || uploadData.error_code === 40001) {
      appLog('[KK] 需要人机验证', 'w');
      var vpath = uploadData.validation_url_path || '';
      var wip = uploadData.worker_ip || '';
      showCFPanel(vpath, wip, JSON.stringify(uploadData));
      await waitForCFVerification();
      // Retry upload after verification
      return await kkUploadVoice(audioFile, speakerName);
    }

    return null;
  } catch(e) {
    appLog('[KK] 上传音源失败: ' + e.message, 'e');
    return null;
  }
}

async function kkGenerateSegmentWithVoice(seg, voiceId, segIdx) {
  seg.status = 'submitting';
  renderSegmentTable();

  var gender = document.getElementById('kGender') ? parseInt(document.getElementById('kGender').value) : 0;
  var speed = document.getElementById('kSpeed') ? parseFloat(document.getElementById('kSpeed').value) : 1.0;
  var volume = document.getElementById('kVolume') ? parseInt(document.getElementById('kVolume').value) : 100;
  var emotion = document.getElementById('kEmotion') ? document.getElementById('kEmotion').value : 'normal';
  var intensity = document.getElementById('kIntensity') ? document.getElementById('kIntensity').value : 'normal';
  var hq = document.getElementById('kHq') ? parseInt(document.getElementById('kHq').value) : 0;

  var body = {
    text: await preprocessTextForTTSSmart(seg.text),
    voice_id: voiceId,
    lang_code: 'zh-cn',
    emotion: emotion,
    intensity: intensity,
    gender: gender,
    model_type: S.kkModel,
    speed: speed,
    volume: volume,
    format: 'mp3',
    hq: hq,
    mver: 'default'
  };

  try {
    var createResp = await kPost('/create-clone-task', body);
    if (createResp.error_code === 40001 || createResp.validation_url_path) {
      var vpath = createResp.validation_url_path || '';
      var wip = createResp.worker_ip || '';
      showCFPanel(vpath, wip, JSON.stringify(createResp));
      await waitForCFVerification();
      createResp = await kPost('/create-clone-task', body);
    }

    if (createResp.error_code !== 0 || !createResp.job_id) {
      throw new Error(createResp.msg || '创建任务失败');
    }

    var jobId = createResp.job_id;
    seg.jobId = jobId;
    seg.status = 'processing';
    renderSegmentTable();

    // Poll for result
    for (var p = 0; p < 120; p++) {
      if (S.cancelRequested) { seg.status = 'cancelled'; renderSegmentTable(); return; }
      await sleep(2000);
      var statusData = await kGet('/job-status?job_id=' + encodeURIComponent(jobId));
      if (statusData.error_code === 0 && statusData.status === 'completed' && statusData.audio_url) {
        var audioResp = await fetch('/api/kiki-audio?url=' + encodeURIComponent(statusData.audio_url));
        if (audioResp.ok) {
          var blob = await audioResp.blob();
          seg.audioBlob = blob;
          try { var ac = new (window.AudioContext||window.webkitAudioContext)(); var ab = await ac.decodeAudioData(await blob.arrayBuffer()); seg.duration = ab.duration; ac.close(); } catch(de) { seg.duration = blob.size / (24000*2); }
          seg.status = 'done';
          appLog('[KK] 段' + (segIdx+1) + ' OK (' + (seg.speaker || '默认') + ')', 's');
        } else {
          seg.status = 'error';
          seg.error = '下载音频失败';
        }
        renderSegmentTable();
        updateProgress();
        return;
      }
      if (statusData.status === 'failed') {
        throw new Error('KikiVoice生成失败');
      }
    }
    throw new Error('KikiVoice轮询超时');
  } catch(e) {
    seg.status = S.cancelRequested ? 'cancelled' : 'error';
    if (!S.cancelRequested) seg.error = e.message;
    appLog('[KK] 段' + (segIdx+1) + ' 失败: ' + e.message, 'e');
    renderSegmentTable();
    updateProgress();
  }
}

function cancelGenerate() {
  S.cancelRequested = true;
  showToast('正在取消...', 'info');
}

function updateProgress() {
  var total = S.segments.length;
  var done = S.segments.filter(function(s) { return s.status === 'done' || s.status === 'error' || s.status === 'cancelled'; }).length;
  var pct = total > 0 ? Math.round(done / total * 100) : 0;
  E.progressFill.style.width = pct + '%';
}

function updateElapsed() {
  var elapsed = Math.floor((Date.now() - S.elapsedStart) / 1000);
  var min = Math.floor(elapsed / 60);
  var sec = elapsed % 60;
  E.elapsed.textContent = '已用时: ' + (min > 0 ? min + 'm ' : '') + sec + 's';
}

// v2.15: Per-segment preview with play/stop toggle
var _segPreviewAudio = null;
var _segPreviewBtn = null;
function previewSegment(idx, btnEl) {
  // If currently playing this segment, stop
  if (_segPreviewAudio && _segPreviewAudio._segIdx === idx) {
    _segPreviewAudio.pause();
    _segPreviewAudio = null;
    if (_segPreviewBtn) _segPreviewBtn.innerHTML = '&#x25B6;';
    _segPreviewBtn = null;
    return;
  }
  // Stop any other playing segment
  if (_segPreviewAudio) {
    _segPreviewAudio.pause();
    _segPreviewAudio = null;
    if (_segPreviewBtn) _segPreviewBtn.innerHTML = '&#x25B6;';
  }
  var seg = S.segments[idx];
  if (!seg || !seg.audioBlob) { showToast('该段尚无音频', 'error'); return; }
  _segPreviewBtn = btnEl;
  _segPreviewAudio = new Audio(URL.createObjectURL(seg.audioBlob));
  _segPreviewAudio._segIdx = idx;
  _segPreviewAudio.play().then(function() {
    if (btnEl) btnEl.innerHTML = '&#x23F8;';
  }).catch(function() { showToast('播放失败', 'error'); });
  _segPreviewAudio.onended = function() {
    URL.revokeObjectURL(_segPreviewAudio.src);
    _segPreviewAudio = null;
    if (_segPreviewBtn) _segPreviewBtn.innerHTML = '&#x25B6;';
    _segPreviewBtn = null;
  };
  _segPreviewAudio.onerror = function() {
    _segPreviewAudio = null;
    if (_segPreviewBtn) _segPreviewBtn.innerHTML = '&#x25B6;';
    _segPreviewBtn = null;
    showToast('播放失败', 'error');
  };
}

function renderSegmentTable() {
  var table = E.segTable;
  var tbody = E.segBody;
  if (S.segments.length === 0) { table.style.display = 'none'; return; }
  table.style.display = 'table';
  // Build speaker index map for color coding
  var spIndexMap = {};
  for (var sdi = 0; sdi < S.detectedSpeakers.length; sdi++) {
    spIndexMap[S.detectedSpeakers[sdi].name] = sdi;
  }
  // v2.16: Check if any segments have been edited after generation completed
  var hasEditsAfterDone = S.segments.some(function(s) { return s.edited && s.status === 'done'; });
  if (hasEditsAfterDone && !S.isGenerating) {
    var genBtn = document.getElementById('generateBtn');
    var genBtnText = document.getElementById('genBtnText');
    if (genBtn && genBtnText) {
      genBtnText.innerHTML = '&#x270F; 应用更改（重新生成改动段）';
      genBtn.style.opacity = '1';
      genBtn.disabled = false;
      genBtn.onclick = applySegmentEdits;
    }
  } else if (!S.isGenerating) {
    var genBtn2 = document.getElementById('generateBtn');
    var genBtnText2 = document.getElementById('genBtnText');
    if (genBtn2 && genBtnText2 && !genBtn2.onclick.toString().match('onGenerateClick')) {
      genBtnText2.innerHTML = '&#x1F680; 开始合成 (' + (S.engine === 'nicevoice' ? 'NiceVoice' : S.engine === 'kikivoice' ? 'KikiVoice' : 'IndexTTS') + ')';
      genBtn2.onclick = onGenerateClick;
    }
  }
  var html = '';
  S.segments.forEach(function(seg, i) {
    var statusLabel = { 'pending': '等待', 'cloning': '克隆', 'submitting': '提交', 'processing': '生成', 'done': '完成', 'error': '失败', 'cancelled': '取消' }[seg.status] || seg.status;
    var durText = seg.duration > 0 ? seg.duration.toFixed(1) + 's' : '-';
    var shortText = seg.text.length > 40 ? seg.text.substring(0, 40) + '...' : seg.text;
    var speakerBadge = '';
    if (seg.speaker && S.speakerMode === 'multi') {
      var spIdx = spIndexMap[seg.speaker];
      if (spIdx === undefined) spIdx = 0;
      speakerBadge = '<span class="seg-speaker sp' + (spIdx % 5) + '">' + escHtml(seg.speaker) + '</span>';
    }
    var previewBtn = '';
    if (seg.status === 'done' && seg.audioBlob) {
      previewBtn = '<button onclick="previewSegment(' + i + ', this)" title="试听" style="background:transparent;border:none;color:var(--blue);cursor:pointer;font-size:14px;padding:2px 6px">&#x25B6;</button>';
    }
    // v2.16: Make seg-text clickable to edit (disabled during generation)
    var canEdit = !S.isGenerating;
    var editIndicator = seg.edited ? ' <span style="color:var(--orange);font-size:10px">&#x270F;</span>' : '';
    var segTextCell = '';
    if (canEdit) {
      segTextCell = '<td class="seg-text" title="点击编辑文本" style="cursor:text" onclick="editSegmentText(' + i + ', this)">' + speakerBadge + escHtml(shortText) + editIndicator + '</td>';
    } else {
      segTextCell = '<td class="seg-text" title="' + escHtml(seg.text) + '">' + speakerBadge + escHtml(shortText) + editIndicator + '</td>';
    }
    html += '<tr>';
    html += '<td>' + (i + 1) + '</td>';
    html += segTextCell;
    html += '<td><div class="seg-status"><span class="sd ' + seg.status + '"></span>' + statusLabel + '</div></td>';
    html += '<td>' + durText + '</td>';
    html += '<td>' + previewBtn + '</td>';
    html += '</tr>';
  });
  tbody.innerHTML = html;
}

// ==================== v2.16: Segment Text Editing ====================
var _segEditingIdx = -1;
var _segEditingOriginal = '';

function editSegmentText(idx, cellEl) {
  if (S.isGenerating) {
    showToast('生成中无法编辑', 'error');
    return;
  }
  var seg = S.segments[idx];
  if (!seg) return;
  // If currently editing another cell, commit it first
  if (_segEditingIdx >= 0 && _segEditingIdx !== idx) {
    commitSegmentEdit();
  }
  _segEditingIdx = idx;
  _segEditingOriginal = seg.text;
  // Replace cell content with a textarea
  var speakerBadge = '';
  if (seg.speaker && S.speakerMode === 'multi') {
    var spIdx = S.detectedSpeakers.findIndex(function(s) { return s.name === seg.speaker; });
    if (spIdx < 0) spIdx = 0;
    speakerBadge = '<span class="seg-speaker sp' + (spIdx % 5) + '">' + escHtml(seg.speaker) + '</span>';
  }
  cellEl.innerHTML = speakerBadge + '<textarea data-seg-idx="' + idx + '" style="width:100%;min-height:60px;background:var(--surface2);border:1px solid var(--primary);color:var(--text);padding:4px 6px;border-radius:4px;font-size:12px;font-family:inherit;resize:vertical">' + escHtml(seg.text) + '</textarea>';
  cellEl.onclick = null;
  cellEl.style.cursor = 'default';
  var ta = cellEl.querySelector('textarea');
  ta.focus();
  ta.setSelectionRange(ta.value.length, ta.value.length);
  // Auto-resize
  ta.style.height = ta.scrollHeight + 'px';
  ta.addEventListener('input', function() { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; });
  // Commit on blur
  ta.addEventListener('blur', function() { commitSegmentEdit(); });
  // Commit on Ctrl+Enter
  ta.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      ta.blur();
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      // Revert
      seg.text = _segEditingOriginal;
      _segEditingIdx = -1;
      _segEditingOriginal = '';
      renderSegmentTable();
    }
  });
}

function commitSegmentEdit() {
  if (_segEditingIdx < 0) return;
  var idx = _segEditingIdx;
  var seg = S.segments[idx];
  if (!seg) { _segEditingIdx = -1; return; }
  var ta = document.querySelector('textarea[data-seg-idx="' + idx + '"]');
  var newText = ta ? ta.value.trim() : _segEditingOriginal;
  _segEditingIdx = -1;
  var oldText = _segEditingOriginal;
  _segEditingOriginal = '';
  if (newText && newText !== oldText) {
    seg.text = newText;
    seg.edited = true;
    // Scenario logic:
    // a) seg.status === 'pending': just update text, will use new text when generated
    // b) generating (cloning/submitting/processing): shouldn't happen because we block editing, but guard anyway
    // c) seg.status === 'done' && S.isGenerating: mark for regen after current sequence
    // d) seg.status === 'done' && !S.isGenerating: mark for regen via "Apply Changes" button
    if (seg.status === 'done') {
      if (S.isGenerating) {
        // Scenario c: queue for regen after current sequence
        seg._pendingRegen = true;
        appLog('[EDIT] 段 ' + (idx+1) + ' 已修改，将在当前序列完成后重新生成', 'i');
        showToast('段 ' + (idx+1) + ' 修改已记录，将在当前序列完成后重新生成', 'info');
      } else {
        // Scenario d: change button to "Apply Changes"
        appLog('[EDIT] 段 ' + (idx+1) + ' 已修改，点击"应用更改"重新生成', 'i');
        showToast('段 ' + (idx+1) + ' 已修改，点击"应用更改"按钮重新生成', 'info');
      }
    } else if (seg.status === 'pending') {
      // Scenario a: will use new text when generated
      appLog('[EDIT] 段 ' + (idx+1) + ' 已修改，将使用新文本生成', 'i');
      showToast('段 ' + (idx+1) + ' 已修改', 'success');
    } else {
      // cloning/submitting/processing/error/cancelled - shouldn't normally happen
      appLog('[EDIT] 段 ' + (idx+1) + ' 状态为 ' + seg.status + '，修改已记录', 'w');
    }
  }
  renderSegmentTable();
}

async function applySegmentEdits() {
  // Scenario d: regenerate only edited segments, then re-concatenate
  var editedSegs = S.segments.filter(function(s) { return s.edited && s.status === 'done'; });
  if (editedSegs.length === 0) {
    showToast('没有需要重新生成的段落', 'info');
    return;
  }
  // Validate voice assignments
  var speakersToValidate = S.speakerMode === 'multi' ? S.detectedSpeakers : [{ name: '默认' }];
  for (var vi = 0; vi < speakersToValidate.length; vi++) {
    var spName = speakersToValidate[vi].name;
    if (!S.speakerVoiceData[spName]) {
      if (S.speakerAssignments[spName]) {
        var src = S.audioSources.find(function(s) { return s.id === S.speakerAssignments[spName]; });
        if (src) S.speakerVoiceData[spName] = buildVoiceDataFromSource(src);
      }
      if (!S.speakerVoiceData[spName]) {
        showToast('请为说话人 "' + spName + '" 分配音源', 'error');
        return;
      }
    }
  }

  S.isGenerating = true;
  S.cancelRequested = false;
  E.generateBtn.disabled = true;
  E.genBtnText.innerHTML = '<span class="spinner"></span> 重新生成改动段...';
  E.cancelBtn.style.display = 'block';
  E.progressBar.classList.add('active');

  appLog('[REGEN] 开始重新生成 ' + editedSegs.length + ' 个改动段', 'i');
  var regenIndices = [];
  S.segments.forEach(function(s, i) { if (s.edited && s.status === 'done') regenIndices.push(i); });

  var successCount = 0;
  var failCount = 0;
  for (var ri = 0; ri < regenIndices.length; ri++) {
    if (S.cancelRequested) break;
    var idx = regenIndices[ri];
    var seg = S.segments[idx];
    appLog('[REGEN] 重新生成段 ' + (idx+1) + '/' + S.segments.length, 'i');
    try {
      // Get reference voice for this segment's speaker
      var spName = seg.speaker || '默认';
      var voiceData = S.speakerVoiceData[spName];
      if (!voiceData) { throw new Error('No voice data for ' + spName); }
      var referenceId = await nvCloneVoice(voiceData);
      if (!referenceId) throw new Error('Clone failed for ' + spName);
      // Apply preprocessing (previewEdits or smart preprocess)
      var textToUse = (S.previewEdits && S.previewEdits[idx] !== undefined) ? S.previewEdits[idx] : await preprocessTextForTTSSmart(seg.text);
      var audioBlob = await nvGenerateSegment(textToUse, referenceId, idx);
      if (audioBlob) {
        seg.audioBlob = audioBlob;
        seg.edited = false;
        seg._pendingRegen = false;
        seg.status = 'done';
        successCount++;
        appLog('[REGEN] 段 ' + (idx+1) + ' 重新生成成功', 'i');
      } else {
        failCount++;
        seg.status = 'error';
        seg.error = '重新生成失败';
      }
    } catch(e) {
      failCount++;
      seg.status = 'error';
      seg.error = e.message;
      appLog('[REGEN] 段 ' + (idx+1) + ' 失败: ' + e.message, 'e');
    }
    renderSegmentTable();
    // NV wait between segments
    if (S.engine === 'nicevoice' && ri < regenIndices.length - 1) {
      await sleep((S.config.nvWait || 16) * 1000);
    }
  }

  S.isGenerating = false;
  E.cancelBtn.style.display = 'none';
  E.generateBtn.disabled = false;

  if (successCount > 0) {
    // Re-concatenate
    try {
      await concatenateAudio();
      // Refresh result audio
      if (S.resultWavUrl) { URL.revokeObjectURL(S.resultWavUrl); }
      S.resultWavUrl = URL.createObjectURL(S.resultWavBlob);
      E.resultAudio.src = S.resultWavUrl;
      E.resultSection.classList.add('active');
      // Regenerate SRT
      generateSrt();
      showToast('应用更改完成：' + successCount + ' 段重新生成' + (failCount > 0 ? '，' + failCount + ' 段失败' : ''), 'success');
    } catch(e) {
      showToast('重新拼合失败: ' + e.message, 'error');
    }
  } else {
    showToast('所有段重新生成失败', 'error');
  }
  renderSegmentTable();
}

// ==================== Audio Concatenation ====================
async function concatenateAudio() {
  var successSegs = S.segments.filter(function(s) { return s.status === 'done' && s.audioBlob; });
  if (successSegs.length === 0) throw new Error('No audio segments');

  var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  S.segmentBuffers = [];
  S.segmentDurations = [];

  for (var i = 0; i < successSegs.length; i++) {
    var arrayBuffer = await successSegs[i].audioBlob.arrayBuffer();
    var audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
    S.segmentBuffers.push(audioBuffer);
    S.segmentDurations.push(audioBuffer.duration);
  }

  // v2.14: Voice normalization (peak + RMS) BEFORE concat
  if (S.config.voiceNormalizeEnabled !== false) {
    try {
      S.segmentBuffers = normalizeVoiceBuffers(S.segmentBuffers, S.detectedSpeakers, S.segments);
      appLog('[POST] Voice normalization applied', 'i');
    } catch(e) {
      appLog('[POST] Normalization failed: ' + e.message, 'e');
    }
  }

  var totalDuration = 0;
  var sampleRate = S.segmentBuffers[0].sampleRate;
  var numberOfChannels = S.segmentBuffers[0].numberOfChannels;
  for (var i = 0; i < S.segmentBuffers.length; i++) {
    totalDuration += S.segmentBuffers[i].duration;
    sampleRate = Math.max(sampleRate, S.segmentBuffers[i].sampleRate);
  }

  var totalSamples = Math.ceil(totalDuration * sampleRate);
  var resultBuffer = audioCtx.createBuffer(numberOfChannels, totalSamples, sampleRate);

  var offset = 0;
  for (var i = 0; i < S.segmentBuffers.length; i++) {
    var buf = S.segmentBuffers[i];
    // Resample if needed (simple: copy directly assuming same sampleRate)
    for (var ch = 0; ch < numberOfChannels; ch++) {
      var sourceData = buf.getChannelData(Math.min(ch, buf.numberOfChannels - 1));
      resultBuffer.copyToChannel(sourceData, ch, offset);
    }
    offset += buf.length;
  }
  audioCtx.close();

  // v2.14: Splice intro/outro BEFORE BGM mixing
  if (S.config.introOutroEnabled && (S.config.introAudioBase64 || S.config.outroAudioBase64)) {
    try {
      resultBuffer = await spliceIntroOutro(resultBuffer);
      appLog('[POST] Intro/outro spliced', 'i');
    } catch(e) {
      appLog('[POST] Intro/outro splice failed: ' + e.message, 'e');
    }
  }

  // Save voice-only WAV
  S.resultWavBlobVoiceOnly = audioBufferToWav(resultBuffer);

  // v2.14: BGM mixing with sidechain ducking
  if (S.config.bgmEnabled && S.config.bgmAudioBase64) {
    try {
      resultBuffer = await mixBgmIntoVoice(resultBuffer);
      appLog('[POST] BGM mixed in', 'i');
    } catch(e) {
      appLog('[POST] BGM mix failed: ' + e.message, 'e');
    }
  }

  S.resultWavBlob = audioBufferToWav(resultBuffer);
}

// ==================== WAV Encoding ====================
function audioBufferToWav(buffer) {
  var numChannels = buffer.numberOfChannels;
  var sampleRate = buffer.sampleRate;
  var bitDepth = 16;
  var bytesPerSample = bitDepth / 8;
  var blockAlign = numChannels * bytesPerSample;
  var dataLength = buffer.length * blockAlign;
  var totalLength = 44 + dataLength;
  var arrayBuffer = new ArrayBuffer(totalLength);
  var view = new DataView(arrayBuffer);

  writeString(view, 0, 'RIFF');
  view.setUint32(4, totalLength - 8, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitDepth, true);
  writeString(view, 36, 'data');
  view.setUint32(40, dataLength, true);

  var channels = [];
  for (var ch = 0; ch < numChannels; ch++) channels.push(buffer.getChannelData(ch));
  var offset = 44;
  for (var i = 0; i < buffer.length; i++) {
    for (var ch = 0; ch < numChannels; ch++) {
      var sample = Math.max(-1, Math.min(1, channels[ch][i]));
      sample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
      view.setInt16(offset, sample | 0, true);
      offset += 2;
    }
  }
  return new Blob([arrayBuffer], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
  for (var i = 0; i < string.length; i++) view.setUint8(offset + i, string.charCodeAt(i));
}

// ==================== SRT Generation ====================
function generateSrt() {
  if (S.speakerMode === 'multi') {
    generateSrtMultiSpeaker();
    return;
  }
  var srt = '';
  var subtitleIndex = 1;
  var timeOffset = 0;

  // Use the new reliable line-to-segment mapping
  var segMap = mapOriginalLinesToSegments();

  for (var mi = 0; mi < segMap.length; mi++) {
    var entry = segMap[mi];
    var segDuration = S.segmentDurations[entry.bufIdx] || S.segments[entry.segIdx].duration;

    // Calculate total chars for proportional timing within this segment
    var totalChars = 0;
    for (var li = 0; li < entry.lines.length; li++) totalChars += entry.lines[li].text.length;
    if (totalChars === 0) totalChars = 1;

    var lineOffset = timeOffset;
    for (var li = 0; li < entry.lines.length; li++) {
      var lineText = entry.lines[li].text;
      // Proportional duration based on character count
      var lineDuration = (lineText.length / totalChars) * segDuration;
      var cleanText = cleanSubtitleText(lineText);
      if (cleanText) {
        srt += subtitleIndex + '\\n';
        srt += formatSrtTime(lineOffset) + ' --> ' + formatSrtTime(lineOffset + lineDuration) + '\\n';
        srt += cleanText + '\\n\\n';
        subtitleIndex++;
      }
      lineOffset += lineDuration;
    }
    timeOffset += segDuration;
  }
  S.resultSrt = srt;
}

// Multi-speaker SRT: uses segment's built-in lines & speaker info
// (avoids the buggy mapOriginalLinesToSegments which compares raw input with markers
//  against segment text that has markers stripped, causing character-count mismatch)
function generateSrtMultiSpeaker() {
  var srt = '';
  var subtitleIndex = 1;
  var timeOffset = 0;
  var bufIdx = 0;

  for (var si = 0; si < S.segments.length; si++) {
    var seg = S.segments[si];
    if (seg.status !== 'done') continue;

    var segDuration = S.segmentDurations[bufIdx] || seg.duration;
    bufIdx++;

    // Each segment has a 'lines' array from splitTextForTTS (content text without markers)
    var segLines = seg.lines || [];
    // If no lines tracked, auto-break the segment text
    if (segLines.length === 0) {
      segLines = autoBreakSubtitle(seg.text, 15, 5).map(function(t) { return { text: t }; });
    }

    // Calculate total chars for proportional timing
    var totalChars = 0;
    for (var li = 0; li < segLines.length; li++) totalChars += (segLines[li].text || '').length;
    if (totalChars === 0) totalChars = 1;

    var lineOffset = timeOffset;
    for (var li = 0; li < segLines.length; li++) {
      var lineText = segLines[li].text || '';
      var lineDuration = (lineText.length / totalChars) * segDuration;
      var cleanText = cleanSubtitleText(lineText);
      if (cleanText) {
        srt += subtitleIndex + '\\n';
        srt += formatSrtTime(lineOffset) + ' --> ' + formatSrtTime(lineOffset + lineDuration) + '\\n';
        if (seg.speaker) {
          cleanText = seg.speaker + '：' + cleanText;
        }
        srt += cleanText + '\\n\\n';
        subtitleIndex++;
      }
      lineOffset += lineDuration;
    }
    timeOffset += segDuration;
  }
  S.resultSrt = srt;
}

// Auto-break text into subtitle lines
// maxLen: max chars per line (including punctuation), default 15
// minLen: min chars per line, default 5
function autoBreakSubtitle(text, maxLen, minLen) {
  if (!text || !text.trim()) return [];
  text = text.trim();
  if (!maxLen) maxLen = 15;
  if (!minLen) minLen = 5;
  if (text.length <= maxLen) return [text];

  // Step 1: Split at punctuation boundaries
  var chunks = [];
  var majorRe = /[，。！？；]/g;
  var last = 0, m;
  while ((m = majorRe.exec(text)) !== null) {
    var c = text.substring(last, m.index + 1);
    if (c) chunks.push(c);
    last = m.index + 1;
  }
  if (last < text.length) chunks.push(text.substring(last));

  // Sub-split chunks exceeding maxLen at minor punctuation
  var refined = [];
  for (var ci = 0; ci < chunks.length; ci++) {
    if (chunks[ci].length <= maxLen) { refined.push(chunks[ci]); continue; }
    var subRe = /[、：""''《》…—,\\s;:\-]/g;
    var subLast = 0, sm;
    while ((sm = subRe.exec(chunks[ci])) !== null) {
      var sc = chunks[ci].substring(subLast, sm.index + 1);
      if (sc) refined.push(sc);
      subLast = sm.index + 1;
    }
    if (subLast < chunks[ci].length) refined.push(chunks[ci].substring(subLast));
    if (refined.length === 0) refined.push(chunks[ci]);
  }

  // Step 2: Merge chunks into lines up to maxLen
  var lines = [];
  var cur = '';
  for (var ri = 0; ri < refined.length; ri++) {
    if (cur.length + refined[ri].length <= maxLen) {
      cur += refined[ri];
    } else {
      if (cur) lines.push(cur);
      cur = refined[ri];
    }
  }
  if (cur) lines.push(cur);

  // Step 3: Force-split long lines + merge short lines + clean trailing punctuation
  var result = [];
  for (var li = 0; li < lines.length; li++) {
    var line = lines[li];
    while (line.length > maxLen) {
      var sp = maxLen;
      for (var off = 0; off <= 8 && sp - off > minLen; off++) {
        if (/[，。！？、；：""''《》…—,\\s;:\-]/.test(line[sp - off])) { sp = sp - off + 1; break; }
      }
      result.push(line.substring(0, sp));
      line = line.substring(sp);
    }
    if (line) result.push(line);
  }

  // Merge short lines with neighbors
  var merged = [];
  for (var fi = 0; fi < result.length; fi++) {
    var cleaned = result[fi].replace(/[，,。.]+$/, '').trim();
    if (!cleaned) continue;
    if (cleaned.length < minLen && merged.length > 0) {
      var prevClean = merged[merged.length - 1].replace(/[，,。.]+$/, '').trim();
      if (prevClean.length + cleaned.length <= maxLen) {
        merged[merged.length - 1] += result[fi];
      } else {
        merged.push(result[fi]);
      }
    } else {
      merged.push(result[fi]);
    }
  }

  return merged;
}

// ==================== Line-to-Segment Mapping ====================
// Map original input lines to TTS segments using character count accumulation.
// This replaces the buggy getLinesInRange approach that caused:
//   - Duplicate lines (when a line spans two segments)
//   - Missing lines (when position tracking was off)
//   - Misaligned SRT timestamps
function mapOriginalLinesToSegments() {
  var inputText = E.textInput.value;
  var rawLines = inputText.split('\\n');
  var originalLines = [];
  for (var i = 0; i < rawLines.length; i++) {
    var trimmed = rawLines[i].trim();
    if (trimmed) originalLines.push(trimmed);
  }

  // Build the mapping: each segment gets its original lines
  var linePtr = 0; // current position in originalLines
  var result = [];  // array of { segIdx, bufIdx, lines: [{text, charStart, charEnd}] }

  var bufIdx = 0;
  for (var si = 0; si < S.segments.length; si++) {
    var seg = S.segments[si];
    if (seg.status !== 'done') continue;

    var segText = seg.text;
    var segTextLen = seg.text.length;
    var segLines = [];
    var accumulatedLen = 0;

    while (linePtr < originalLines.length) {
      var lineText = originalLines[linePtr];
      var newLen = accumulatedLen + (accumulatedLen > 0 ? 1 : 0) + lineText.length;

      // Check if adding this line would exceed the segment text length
      // Allow small tolerance (+3) for minor discrepancies from punctuation/space differences
      if (newLen <= segTextLen + 3) {
        var charStart = accumulatedLen; // position within the segment text
        segLines.push({ text: lineText, charStart: charStart, charEnd: charStart + lineText.length });
        accumulatedLen = newLen;
        linePtr++;
      } else {
        break;
      }
    }

    if (segLines.length === 0) {
      // Fallback: no lines mapped (shouldn't happen normally), use autoBreakSubtitle
      var autoLines = autoBreakSubtitle(segText, 15, 5);
      for (var ai = 0; ai < autoLines.length; ai++) {
        var aCharStart = ai === 0 ? 0 : segLines.length > 0 ? segLines[segLines.length - 1].charEnd : 0;
        segLines.push({ text: autoLines[ai], charStart: aCharStart, charEnd: aCharStart + autoLines[ai].length });
      }
    }

    result.push({ segIdx: si, bufIdx: bufIdx, lines: segLines });
    bufIdx++;
  }

  // Handle remaining original lines that weren't mapped to any segment
  // (e.g., if the last segments failed)
  while (linePtr < originalLines.length) {
    // Assign remaining lines to the last segment if possible, or create estimated entries
    if (result.length > 0) {
      var lastEntry = result[result.length - 1];
      lastEntry.lines.push({ text: originalLines[linePtr], charStart: -1, charEnd: -1 });
    }
    linePtr++;
  }

  return result;
}

function cleanSubtitleText(text) {
  if (!text) return '';
  text = text.trim();
  if (!text) return '';
  // Remove trailing commas and periods, but keep ！？""''《》…—
  text = text.replace(/[，,。.]+$/, '');
  return text;
}

function formatSrtTime(seconds) {
  var h = Math.floor(seconds / 3600);
  var m = Math.floor((seconds % 3600) / 60);
  var s = Math.floor(seconds % 60);
  var ms = Math.round((seconds % 1) * 1000);
  return pad2(h) + ':' + pad2(m) + ':' + pad2(s) + ',' + pad3(ms);
}

function pad2(n) { return n < 10 ? '0' + n : '' + n; }
function pad3(n) { return n < 10 ? '00' + n : (n < 100 ? '0' + n : '' + n); }

// ==================== JianYing Project ZIP ====================
async function downloadJianYing() {
  await loadJSZip();
  if (!S.resultWavBlob) { showToast('请先生成音频', 'error'); return; }
  showToast('正在生成剪映工程...', 'info');
  try {
    var zip = new JSZip();
    var successSegs = S.segments.filter(function(s) { return s.status === 'done'; });
    if (successSegs.length === 0) { showToast('无可用音频段', 'error'); return; }

    // Project folder inside ZIP
    var projectName = S.projectName || 'TTS_Voice_Lab';
    var projectFolder = zip.folder(projectName);

    var audioMaterials = [], audioSegments = [], textMaterials = [], textSegments = [], speedMaterials = [];

    // ===== Calculate total duration =====
    var totalDurationUs = 0;
    var bufIdx = 0;
    var segTimeOffsets = []; // track start time of each segment in microseconds
    var segDurationsUs = []; // track duration of each segment in microseconds
    for (var si = 0; si < S.segments.length; si++) {
      if (S.segments[si].status !== 'done') continue;
      var segDurationSec = S.segmentDurations[bufIdx] || S.segments[si].duration;
      var segDurationUs = Math.round(segDurationSec * 1000000);
      segTimeOffsets.push(totalDurationUs);
      segDurationsUs.push(segDurationUs);
      totalDurationUs += segDurationUs;
      bufIdx++;
    }

    // ===== Single complete audio file =====
    var audioFileName = 'audio_main.wav';
    var audioArrayBuffer = await S.resultWavBlob.arrayBuffer();
    projectFolder.file(audioFileName, audioArrayBuffer);

    // Also include SRT in the project folder
    if (S.resultSrt) {
      projectFolder.file('audio_main.srt', S.resultSrt);
    }

    var audioMatId = hexId(), audioSegId = hexId(), audioSpeedId = hexId();
    audioMaterials.push({
      id: audioMatId, local_material_id: audioMatId, music_id: audioMatId,
      name: audioFileName, path: './' + audioFileName,
      duration: totalDurationUs, type: 'extract_music', category_name: 'local',
      check_flag: 3, local_id: '', source_platform: 0, source: 0, text_id: '', text_source: 0
    });
    speedMaterials.push({ id: audioSpeedId, speed: 1.0, mode: 0, type: 'speed' });
    audioSegments.push({
      id: audioSegId, material_id: audioMatId,
      target_timerange: { start: 0, duration: totalDurationUs },
      source_timerange: { start: 0, duration: totalDurationUs },
      speed: 1.0, volume: 1.0, extra_material_refs: [audioSpeedId],
      is_tone_modify: false, clip: null, render_index: 0, role: 0,
      group_id: '', track_attribute: 0, uniform_scale: null, source: 0
    });

    // ===== Subtitle segments =====
    var subtitleIndex = 0;
    // For multi-speaker mode, use segment's built-in lines to avoid marker mismatch
    var jySubtitleEntries = [];
    if (S.speakerMode === 'multi') {
      var jyBufIdx = 0;
      for (var si2 = 0; si2 < S.segments.length; si2++) {
        var seg2 = S.segments[si2];
        if (seg2.status !== 'done') continue;
        var jyLines = seg2.lines || [];
        if (jyLines.length === 0) {
          jyLines = autoBreakSubtitle(seg2.text, 15, 5).map(function(t) { return { text: t }; });
        }
        jySubtitleEntries.push({ bufIdx: jyBufIdx, lines: jyLines, speaker: seg2.speaker });
        jyBufIdx++;
      }
    } else {
      var segMap = mapOriginalLinesToSegments();
      for (var mi2 = 0; mi2 < segMap.length; mi2++) {
        jySubtitleEntries.push({ bufIdx: segMap[mi2].bufIdx, lines: segMap[mi2].lines, speaker: null });
      }
    }

    for (var ji = 0; ji < jySubtitleEntries.length; ji++) {
      var jyEntry = jySubtitleEntries[ji];
      var segDurationUs2 = segDurationsUs[jyEntry.bufIdx];
      var timeOffsetUs = segTimeOffsets[jyEntry.bufIdx];

      // Calculate total chars for proportional timing
      var totalChars = 0;
      for (var li = 0; li < jyEntry.lines.length; li++) totalChars += (jyEntry.lines[li].text || '').length;
      if (totalChars === 0) totalChars = 1;

      var lineOffsetUs = timeOffsetUs;
      for (var li = 0; li < jyEntry.lines.length; li++) {
        var lineText = jyEntry.lines[li].text || '';
        var lineDurationUs = Math.round((lineText.length / totalChars) * segDurationUs2);
        var cleanText = cleanSubtitleText(lineText);
        // Add speaker label in multi-speaker mode
        if (S.speakerMode === 'multi' && jyEntry.speaker) {
          cleanText = jyEntry.speaker + '：' + cleanText;
        }
        if (cleanText) {
          var textMatId = hexId(), textSegId = hexId(), textSpeedId = hexId();
          var textContent = JSON.stringify({
            styles: [{
              fill: { alpha: 1.0, content: { render_type: 'solid', solid: { alpha: 1.0, color: [1.0, 1.0, 1.0] } } },
              range: [0, cleanText.length], size: 10.0,
              strokes: [{ content: { solid: { alpha: 1.0, color: [0.0, 0.0, 0.0] } }, width: 0.08 }],
              bold: false, italic: false, underline: false
            }],
            text: cleanText
          });
          textMaterials.push({
            id: textMatId, content: textContent, type: 'subtitle',
            typesetting: 0, alignment: 1,
            letter_spacing: 0.0, line_spacing: 0.02,
            line_feed: 1, line_max_width: 0.82, force_apply_line_max_width: false,
            check_flag: 15, global_alpha: 1.0,
            font_id: 'NotoSansSC', font_name: '\u601d\u6e90\u9ed1\u4f53', font_size: 10.0,
            local_id: '', source: 0, text_id: '', text_source: 0,
            path: '', category_id: '', category_name: 'local'
          });
          speedMaterials.push({ id: textSpeedId, speed: 1.0, mode: 0, type: 'speed' });
          textSegments.push({
            id: textSegId, material_id: textMatId,
            target_timerange: { start: lineOffsetUs, duration: lineDurationUs },
            source_timerange: null, speed: 1.0, volume: 1.0,
            clip: { alpha: 1.0, flip: { horizontal: false, vertical: false }, rotation: 0.0, scale: { x: 1.0, y: 1.0 }, transform: { x: 0.0, y: -0.8 } },
            uniform_scale: { on: true, value: 1.0 }, extra_material_refs: [textSpeedId],
            common_keyframes: [], keyframe_refs: [],
            enable_adjust: true, enable_color_correct_adjust: false,
            enable_color_curves: true, enable_color_match_adjust: false,
            enable_color_wheels: true, enable_lut: true, enable_smart_color_adjust: false,
            is_tone_modify: false, last_nonzero_volume: 1.0,
            reverse: false, track_attribute: 0, track_render_index: 0, visible: true
          });
          subtitleIndex++;
        }
        lineOffsetUs += lineDurationUs;
      }
    }

    var draftId = hexId().toUpperCase();
    var draftIdDashed = draftId.substring(0, 8) + '-' + draftId.substring(8, 12) + '-' + draftId.substring(12, 16) + '-' + draftId.substring(16, 20) + '-' + draftId.substring(20, 32);

    var draftContent = {
      id: draftIdDashed,
      canvas_config: { width: 1080, height: 1920, ratio: '9:16' },
      duration: totalDurationUs,
      materials: {
        videos: [], audios: audioMaterials, texts: textMaterials, images: [],
        speeds: speedMaterials, transitions: [], digital_humans: [], material_animations: [],
        effects: [], filters: [], stickers: [], masks: [], ai_transcriptions: [], auto_captions: [],
        sound_channel_mappings: [], bezier_curves: [], clouds: [], flowers: [], frames: [],
        hands: [], head_animations: [], log_color_wheels: [], magic_colors: [], material_colors: [],
        multi_language_refs: [], placeholders: [], primary_color_wheels: [], realtime_denoises: [],
        shape_templates: [], smart_crops: [], sound_effect_metadatas: [], text_templates: [],
        track_groups: [], video_effects: [], video_track_animations: [], vocal_beautifys: [],
        vocal_falsettos: [], video_generators: [],
        crop: { lower_left_x: 0, lower_left_y: 1, upper_right_x: 1, upper_right_y: 0 },
        personality_speaker_infos: [], ocr_text_labels: [], smart_relights: [], materials_changers: [],
        group_res: [], chaos_contents: [], virtual_projections: [], audio_fades: [], audio_effects: [],
        color_curves: [], material_labels: []
      },
      tracks: [
        { id: hexId(), type: 'audio', attribute: 0, flag: 0, is_default: false, segments: audioSegments, track_duration: totalDurationUs },
        { id: hexId(), type: 'text', attribute: 0, flag: 0, is_default: false, segments: textSegments, track_duration: totalDurationUs }
      ],
      metadata: { app_id: 1, app_version: '5.0.0', create_time: Date.now(), draft_id: draftIdDashed, draft_name: projectName, platform: 'windows', source: 0, timeline_materials_size_: 0, timeline_size_: 0, version: 1 },
      last_modified_platform: 'windows', name: projectName, new_version: '',
      platform: { os: 'windows', device: '' }, relationships: [], retouch_cover: '', source: 'default',
      update_time: Date.now(), version: 1
    };

    projectFolder.file('draft_content.json', JSON.stringify(draftContent, null, 2));
    var metaInfo = {
      draft_id: draftIdDashed, draft_name: projectName, draft_deeplink: '', draft_cover: '',
      draft_materials_covers: [], timeline_materials_size_: 0, create_time: Date.now(), update_time: Date.now(),
      is_from_ugc_template: false, is_draft_removed: false, is_invisible: false, source: 'default',
      tm_draft_cloud_id: '', tm_draft_cloud_resource_id: '', draft_cloud_purchase_info: '',
      is_commercialize_music_licensed: false
    };
    projectFolder.file('draft_meta_info.json', JSON.stringify(metaInfo, null, 2));

    var zipBlob = await zip.generateAsync({ type: 'blob' });
    var filename = getDownloadFilename('zip');
    downloadBlob(zipBlob, filename);
    showToast('剪映工程已下载', 'success');
  } catch(e) {
    showToast('生成剪映工程失败: ' + e.message, 'error');
  }
}

// ==================== Downloads ====================
function downloadWav() {
  if (!S.resultWavBlob) { showToast('请先生成音频', 'error'); return; }
  // Direct download from existing blob - no re-synthesis
  downloadBlob(S.resultWavBlob, getDownloadFilename('wav'));
}

function downloadSrt() {
  if (!S.resultSrt) { showToast('请先生成音频', 'error'); return; }
  downloadBlob(new Blob([S.resultSrt], { type: 'text/plain;charset=utf-8' }), getDownloadFilename('srt'));
}

function getDownloadFilename(ext) {
  var name = S.projectName || S.downloadTimestamp || (function() {
    var now = new Date();
    return '' + now.getFullYear() + pad2(now.getMonth() + 1) + pad2(now.getDate()) + '-' + pad2(now.getHours()) + pad2(now.getMinutes()) + pad2(now.getSeconds());
  })();
  return name + '.' + ext;
}

function downloadBlob(blob, filename) {
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}

// ==================== Import/Export ====================
function exportConfig() {
  saveConfig();
  var exportData = {
    version: APP_VERSION,
    config: S.config,
    audioSources: S.audioSources.map(function(src) {
      return { id: src.id, name: src.name, audioBase64: src.audioBase64, nvReferenceId: src.nvReferenceId, kkVoiceId: src.kkVoiceId, addedAt: src.addedAt, lastSyncAt: src.lastSyncAt };
    })
  };
  downloadBlob(new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' }), 'tts-voice-lab-config.json');
  showToast('配置已导出', 'success');
}

function importConfig(event) {
  var file = event.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function(e) {
    try {
      var data = JSON.parse(e.target.result);
      if (data.config) {
        Object.keys(data.config).forEach(function(k) { if (S.config[k] !== undefined) S.config[k] = data.config[k]; });
        saveConfig(); applyConfigToUI();
        switchEngine(S.config.engine || 'nicevoice');
      }
      if (data.audioSources && Array.isArray(data.audioSources)) {
        data.audioSources.forEach(function(src) {
          if (!S.audioSources.find(function(s) { return s.name === src.name; })) {
            // Migrate old format
            if (src.dataUrl && !src.audioBase64) src.audioBase64 = src.dataUrl;
            if (!src.kkVoiceId) src.kkVoiceId = null;
            if (!src.lastSyncAt) src.lastSyncAt = null;
            S.audioSources.push(src);
          }
        });
        saveAudioSources(); renderSettingsVoiceList(); renderSpeakerAssignmentList();
      }
      showToast('配置已导入', 'success');
      checkApiStatus();
    } catch(err) { showToast('导入失败: ' + err.message, 'error'); }
  };
  reader.readAsText(file);
  event.target.value = '';
}

// ==================== Settings Panel ====================
function toggleSettings() {
  var panel = E.settingsPanel;
  var overlay = E.settingsOverlay;
  if (panel.classList.contains('open')) {
    panel.classList.remove('open'); overlay.classList.remove('open');
    saveConfig(); checkApiStatus();
  } else {
    applyConfigToUI(); panel.classList.add('open'); overlay.classList.add('open');
  }
}

// ==================== History ====================
var historyDB = null;

function openHistoryDB() {
  return new Promise(function(resolve, reject) {
    if (historyDB) { resolve(historyDB); return; }
    var req = indexedDB.open('ttsvoicelab_history', 2);
    req.onupgradeneeded = function(e) {
      var db = e.target.result;
      if (!db.objectStoreNames.contains('records')) {
        db.createObjectStore('records', { keyPath: 'id', autoIncrement: true });
      }
    };
    req.onsuccess = function(e) { historyDB = e.target.result; resolve(historyDB); };
    req.onerror = function(e) { reject(e.target.error); };
  });
}

function openHistory() { renderHistoryList(); E.historyModal.classList.add('open'); }
function closeHistory() { E.historyModal.classList.remove('open'); }

async function addHistory(entry) {
  try {
    var db = await openHistoryDB();
    var tx = db.transaction('records', 'readwrite');
    var store = tx.objectStore('records');
    // Store audio blob reference and SRT text
    entry.wavBlob = S.resultWavBlob;
    entry.srtText = S.resultSrt;
    entry.projectName = S.projectName || S.downloadTimestamp || 'audio';
    // v2.16: Store per-segment audio blobs and texts for history edit/restore
    entry.segmentAudios = S.segments.filter(function(s) { return s.status === 'done' && s.audioBlob; }).map(function(s) { return s.audioBlob; });
    entry.segmentTexts = S.segments.map(function(s) { return { text: s.text, speaker: s.speaker, status: s.status, duration: s.duration }; });
    entry.segmentMode = S.speakerMode;
    entry.detectedSpeakers = S.detectedSpeakers.map(function(s) { return { name: s.name, lineCount: s.lineCount, charCount: s.charCount }; });
    entry.speakerAssignments = JSON.parse(JSON.stringify(S.speakerAssignments || {}));
    store.add(entry);

    // Trim to maxHistory
    var countReq = store.count();
    countReq.onsuccess = function() {
      var count = countReq.result;
      if (count > (S.config.maxHistory || 10)) {
        // Get all keys, delete oldest
        var allReq = store.getAllKeys();
        allReq.onsuccess = function() {
          var keys = allReq.result;
          var toDelete = count - (S.config.maxHistory || 10);
          for (var i = 0; i < toDelete; i++) {
            store.delete(keys[i]);
          }
        };
      }
    };
  } catch(e) {
  }
}

async function clearHistory() {
  try {
    var db = await openHistoryDB();
    var tx = db.transaction('records', 'readwrite');
    tx.objectStore('records').clear();
    renderHistoryList();
    showToast('历史记录已清空', 'success');
  } catch(e) {
    showToast('清空历史失败', 'error');
  }
}

async function renderHistoryList() {
  try {
    var db = await openHistoryDB();
    var tx = db.transaction('records', 'readonly');
    var store = tx.objectStore('records');
    var req = store.getAll();
    req.onsuccess = function() {
      var history = req.result.reverse(); // newest first
      var el = E.historyList;
      if (!history.length) { el.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text2)">暂无历史记录</div>'; return; }
      var html = '<div style="text-align:right;margin-bottom:8px"><button class="clear-btn" onclick="clearHistory()">清空历史</button></div>';
      history.forEach(function(item) {
        var engLabel = item.engine === 'nicevoice' ? 'NV' : item.engine === 'kikivoice' ? 'KK' : 'IDX';
        var hasAudio = !!item.wavBlob;
        // v2.16: Check if segment audios are available for edit/restore
        var hasSegmentAudios = !!(item.segmentAudios && item.segmentAudios.length > 0);
        html += '<div class="history-item">';
        html += '<div class="hi-top"><span class="hi-text">[' + engLabel + '] ' + escHtml(item.projectName || '未命名') + ' — ' + (item.success || 0) + '/' + (item.segments || 0) + ' 段</span><span class="hi-date">' + escHtml(item.date || '') + '</span></div>';
        html += '<div class="hi-detail">' + escHtml(item.text || '') + '</div>';
        if (hasAudio) {
          html += '<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">';
          html += '<button class="clear-btn" onclick="downloadHistoryItem(' + item.id + ',\\'wav\\')" style="color:var(--green);border-color:var(--green)">下载 WAV</button>';
          if (item.srtText) html += '<button class="clear-btn" onclick="downloadHistoryItem(' + item.id + ',\\'srt\\')" style="color:var(--blue);border-color:var(--blue)">下载 SRT</button>';
          // v2.16: Edit button - greyed out if no segment audios
          if (hasSegmentAudios) {
            html += '<button class="clear-btn" onclick="editHistoryItem(' + item.id + ')" style="color:var(--orange);border-color:var(--orange)">&#x270F; 编辑</button>';
          } else {
            html += '<button class="clear-btn" disabled style="opacity:0.4;cursor:not-allowed" title="分段音频已丢失，无法编辑">&#x270F; 编辑</button>';
          }
          html += '</div>';
        }
        html += '</div>';
      });
      el.innerHTML = html;
    };
  } catch(e) {
  }
}

async function downloadHistoryItem(id, type) {
  try {
    var db = await openHistoryDB();
    var tx = db.transaction('records', 'readonly');
    var store = tx.objectStore('records');
    var req = store.get(id);
    req.onsuccess = function() {
      var item = req.result;
      if (!item) { showToast('记录不存在', 'error'); return; }
      if (type === 'wav' && item.wavBlob) {
        downloadBlob(item.wavBlob, (item.projectName || 'audio') + '.wav');
      } else if (type === 'srt' && item.srtText) {
        downloadBlob(new Blob([item.srtText], { type: 'text/plain;charset=utf-8' }), (item.projectName || 'audio') + '.srt');
      } else {
        showToast('该类型文件不存在', 'error');
      }
    };
  } catch(e) {
    showToast('下载失败', 'error');
  }
}

// v2.16: Edit history item - restore segments to main UI
async function editHistoryItem(id) {
  try {
    var db = await openHistoryDB();
    var tx = db.transaction('records', 'readonly');
    var store = tx.objectStore('records');
    var req = store.get(id);
    req.onsuccess = function() {
      var item = req.result;
      if (!item) { showToast('记录不存在', 'error'); return; }
      if (!item.segmentAudios || item.segmentAudios.length === 0) {
        showToast('分段音频已丢失，无法编辑', 'error');
        return;
      }
      // Close history modal
      closeHistory();
      // Restore segments to S.segments
      S.segments = item.segmentTexts.map(function(t, i) {
        return {
          text: t.text,
          speaker: t.speaker,
          status: t.status === 'done' ? 'done' : 'pending',
          jobId: null,
          audioBlob: item.segmentAudios[i] || null,
          duration: t.duration || 0,
          error: null,
          edited: false
        };
      });
      // Restore speaker mode and detected speakers
      S.speakerMode = item.segmentMode || 'single';
      S.detectedSpeakers = item.detectedSpeakers || [];
      S.speakerAssignments = item.speakerAssignments || {};
      // Restore speaker voice data from current audio sources
      S.speakerVoiceData = {};
      Object.keys(S.speakerAssignments).forEach(function(spName) {
        var src = S.audioSources.find(function(s) { return s.id === S.speakerAssignments[spName]; });
        if (src) S.speakerVoiceData[spName] = buildVoiceDataFromSource(src);
      });
      // Restore result blobs
      S.resultWavBlob = item.wavBlob;
      S.resultSrt = item.srtText || '';
      if (S.resultWavUrl) { URL.revokeObjectURL(S.resultWavUrl); }
      S.resultWavUrl = S.resultWavBlob ? URL.createObjectURL(S.resultWavBlob) : null;
      // Restore text in textarea
      if (item.segmentTexts && item.segmentTexts.length > 0) {
        var fullText = item.segmentTexts.map(function(t) {
          return (t.speaker ? t.speaker + '：' : '') + t.text;
        }).join('\\n\\n');
        E.textInput.value = fullText;
        updateTextStats();
      }
      // Update UI
      renderSegmentTable();
      renderSpeakerAssignmentList();
      if (S.resultWavUrl) {
        E.resultAudio.src = S.resultWavUrl;
        E.resultSection.classList.add('active');
      }
      if (E.metadataCard) E.metadataCard.style.display = 'block';
      showToast('已从历史记录恢复 ' + S.segments.length + ' 段，可点击任意段文本编辑', 'success');
      appLog('[HISTORY-EDIT] Restored ' + S.segments.length + ' segments from history #' + id, 'i');
    };
  } catch(e) {
    showToast('恢复历史记录失败: ' + e.message, 'error');
  }
}

// ==================== README ====================
function showReadme() { E.readmeBody.innerHTML = getReadmeContent(); E.readmeModal.classList.add('open'); }
function closeReadme() { E.readmeModal.classList.remove('open'); }

function getReadmeContent() {
  // v2.14: README stored as a top-of-file constant for single source of truth.
  // Render the markdown content as preformatted text for simplicity.
  return '<div style="white-space:pre-wrap;font-size:13px;line-height:1.6;font-family:system-ui,sans-serif">' + escHtml(README_CONTENT.replace('${VERSION}', APP_VERSION)) + '</div>';
}

// ==================== Toast & Helpers ====================
// v2.15: Layout tab switching (narrow screen only)
function switchLayoutTab(tab) {
  var content = document.querySelector('.main-content');
  var log = document.querySelector('.main-log');
  var tabs = document.querySelectorAll('.layout-tab');
  if (!content || !log) return;
  if (tab === 'content') {
    content.classList.remove('hidden-tab');
    log.classList.add('hidden-tab');
    if (tabs[0]) tabs[0].classList.add('active');
    if (tabs[1]) tabs[1].classList.remove('active');
  } else {
    content.classList.add('hidden-tab');
    log.classList.remove('hidden-tab');
    if (tabs[0]) tabs[0].classList.remove('active');
    if (tabs[1]) tabs[1].classList.add('active');
  }
}

function showToast(msg, type) {
  var toast = E.toast;
  toast.textContent = msg;
  toast.className = 'toast ' + (type || 'info');
  toast.offsetHeight;
  toast.classList.add('show');
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(function() { toast.classList.remove('show'); }, 3000);
}

function hexId() {
  return 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'.replace(/x/g, function() { return (Math.random() * 16 | 0).toString(16); });
}

function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function sleep(ms) { return new Promise(function(resolve) { setTimeout(resolve, ms); }); }


// ============================================================
// v2.14 New Functions
// ============================================================

// ---- GLM System Prompt Management ----
function resetGlmPrompt() {
  if (!confirm('恢复默认系统提示词？当前自定义内容将被清除。')) return;
  var el = document.getElementById('cfgGlmSystemPrompt');
  if (el) el.value = '';
  S.config.glmSystemPrompt = '';
  saveConfig();
  showToast('已恢复默认提示词', 'success');
}

async function previewGlmProcess() {
  var apiKey = (document.getElementById('cfgGlmApiKey').value || '').trim();
  if (!apiKey) { showToast('请先填写 GLM API Key', 'error'); return; }
  var sample = '测试文本：《飞驰人生3》票房15.08亿元，2026年6月17日上线，3.14、50%、×℃';
  showToast('正在测试...', 'info');
  var result = await glmPreprocessText(sample);
  if (result) {
    alert('原文：\\n' + sample + '\\n\\n处理后：\\n' + result);
  } else {
    showToast('GLM 调用失败，请检查 API Key', 'error');
  }
}

// ---- Before/After Preview ----
async function loadPreview() {
  var text = E.textInput.value.trim();
  if (!text) { showToast('请先输入文本', 'error'); return; }
  var apiKey = S.config.glmApiKey;
  var mode = S.config.glmPreprocess || 'off';
  if (mode === 'off' || !apiKey) {
    showToast('GLM 预处理未启用，跳过预览', 'info');
    return;
  }
  E.previewCard.style.display = 'block';
  E.previewBody.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text2)">正在调用 GLM 处理...</div>';
  E.previewBtn.style.display = 'none';
  E.regenGlmBtn.style.display = 'inline-block';

  // Build segments first to know how many to preview
  var maxChars = S.engine === 'nicevoice' ? (S.config.nvMaxChars || 150) : S.engine === 'kikivoice' ? kkMaxChars() : (S.config.maxChars || 250);
  var segs = [];
  if (S.speakerMode === 'multi') {
    var spGroups = splitTextBySpeakers(text, maxChars);
    for (var gi = 0; gi < spGroups.length; gi++) {
      for (var si = 0; si < spGroups[gi].segments.length; si++) {
        segs.push({ text: spGroups[gi].segments[si].text, speaker: spGroups[gi].speaker });
      }
    }
  } else {
    var plain = splitTextForTTS(text, maxChars);
    segs = plain.map(function(s) { return { text: s.text, speaker: '' }; });
  }

  // Process each segment
  var html = '<table style="width:100%;border-collapse:collapse"><thead><tr><th style="width:5%;padding:6px;border-bottom:1px solid var(--border);text-align:left">#</th><th style="width:42%;padding:6px;border-bottom:1px solid var(--border);text-align:left">Before (原始)</th><th style="width:53%;padding:6px;border-bottom:1px solid var(--border);text-align:left">After (GLM 处理后，可编辑)</th></tr></thead><tbody>';
  for (var i = 0; i < segs.length; i++) {
    var after = await preprocessTextForTTSSmart(segs[i].text);
    var spBadge = segs[i].speaker ? '<span class="seg-speaker sp0">' + escHtml(segs[i].speaker) + '</span> ' : '';
    html += '<tr>';
    html += '<td style="padding:6px;border-bottom:1px solid var(--surface2);vertical-align:top">' + (i+1) + '</td>';
    html += '<td style="padding:6px;border-bottom:1px solid var(--surface2);vertical-align:top;font-size:11px;color:var(--text2)">' + spBadge + escHtml(segs[i].text) + '</td>';
    html += '<td style="padding:4px;border-bottom:1px solid var(--surface2);vertical-align:top"><textarea data-seg-idx="' + i + '" style="width:100%;min-height:60px;background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:4px 6px;border-radius:4px;font-size:11px;font-family:inherit;resize:vertical">' + escHtml(after) + '</textarea></td>';
    html += '</tr>';
  }
  html += '</tbody></table>';
  E.previewBody.innerHTML = html;
  E.applyPreviewBtn.style.display = 'inline-block';
  showToast('GLM 预处理完成，可编辑 After 文本', 'success');
}

function applyPreviewAndGenerate() {
  // Collect edited After texts and stash them so startGenerate uses them
  var edits = {};
  var textareas = E.previewBody.querySelectorAll('textarea[data-seg-idx]');
  for (var i = 0; i < textareas.length; i++) {
    edits[textareas[i].getAttribute('data-seg-idx')] = textareas[i].value;
  }
  S.previewEdits = edits;
  E.previewCard.style.display = 'none';
  startGenerate();
}

function onGenerateClick() {
  var mode = S.config.glmPreprocess || 'off';
  var apiKey = S.config.glmApiKey;
  if (mode !== 'off' && apiKey) {
    loadPreview();
  } else {
    startGenerate();
  }
}

// ---- Speaker Alternation Check ----
function checkSpeakerAlternation() {
  if (S.speakerMode !== 'multi' || S.segments.length < 2) {
    E.alternationWarning.style.display = 'none';
    return;
  }
  var issues = [];
  for (var i = 1; i < S.segments.length; i++) {
    if (S.segments[i].speaker === S.segments[i-1].speaker) {
      issues.push({ idx: i, speaker: S.segments[i].speaker });
    }
  }
  if (issues.length === 0) {
    E.alternationWarning.style.display = 'none';
    return;
  }
  // Find the "other" speaker
  var otherSpeaker = null;
  for (var j = 0; j < S.detectedSpeakers.length; j++) {
    if (S.detectedSpeakers[j].name !== issues[0].speaker) {
      otherSpeaker = S.detectedSpeakers[j].name;
      break;
    }
  }
  var msg = '检测到 ' + issues.length + ' 处连续同说话人（' + issues[0].speaker + '），可能存在交替遗漏。';
  if (otherSpeaker) {
    msg += '点击"自动交替"将这些段落改为 "' + otherSpeaker + '"。';
  }
  document.getElementById('alternationWarningText').textContent = msg;
  E.alternationWarning.style.display = 'block';
}

function autoFixAlternation() {
  if (S.speakerMode !== 'multi' || S.segments.length < 2) return;
  var speakers = S.detectedSpeakers.map(function(s) { return s.name; });
  if (speakers.length < 2) { showToast('至少需要 2 个说话人', 'error'); return; }
  // Find current speaker of each segment, swap if same as prev
  var curSpeaker = S.segments[0].speaker;
  for (var i = 1; i < S.segments.length; i++) {
    if (S.segments[i].speaker === curSpeaker) {
      // Swap to the other speaker
      var other = speakers.find(function(s) { return s !== curSpeaker; });
      S.segments[i].speaker = other;
      // Also update the speakerVoiceData
      if (S.speakerAssignments[other]) {
        var src = S.audioSources.find(function(s) { return s.id === S.speakerAssignments[other]; });
        if (src) S.speakerVoiceData[other] = buildVoiceDataFromSource(src);
      }
    }
    curSpeaker = S.segments[i].speaker;
  }
  renderSegments();
  checkSpeakerAlternation();
  showToast('已自动交替', 'success');
}

// ---- BGM Upload / Preview ----
function handleBgmUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function(e) {
    S.config.bgmAudioBase64 = e.target.result;
    saveConfig();
    document.getElementById('bgmFileName').textContent = file.name + ' (' + (file.size / 1024 / 1024).toFixed(1) + 'MB)';
    document.getElementById('cfgBgmEnabled').checked = true;
    S.config.bgmEnabled = true;
    saveConfig();
    renderBgmStatus();
    showToast('BGM 已加载', 'success');
  };
  reader.readAsDataURL(file);
}

function clearBgm() {
  S.config.bgmAudioBase64 = '';
  S.config.bgmEnabled = false;
  saveConfig();
  document.getElementById('bgmFileName').textContent = '';
  document.getElementById('cfgBgmEnabled').checked = false;
  renderBgmStatus();
  showToast('BGM 已清除', 'info');
}

function renderBgmStatus() {
  var el = document.getElementById('bgmFileName');
  if (!el) return;
  if (S.config.bgmAudioBase64) {
    el.textContent = '已加载 BGM（点击试听）';
  } else {
    el.textContent = '未选择 BGM';
  }
}

var _bgmPreviewAudio = null;
function previewBgm() {
  if (!S.config.bgmAudioBase64) { showToast('请先选择 BGM', 'error'); return; }
  var btn = document.querySelector('button[onclick="previewBgm()"]');
  if (_bgmPreviewAudio) {
    _bgmPreviewAudio.pause();
    _bgmPreviewAudio = null;
    if (btn) btn.innerHTML = '&#x25B6; 试听';
    return;
  }
  _bgmPreviewAudio = new Audio(S.config.bgmAudioBase64);
  _bgmPreviewAudio.volume = Math.sqrt(S.config.bgmVolume || 0.126);
  _bgmPreviewAudio.play().then(function() {
    if (btn) btn.innerHTML = '&#x23F8; 停止';
  }).catch(function() { showToast('播放失败', 'error'); });
  _bgmPreviewAudio.onended = function() {
    _bgmPreviewAudio = null;
    if (btn) btn.innerHTML = '&#x25B6; 试听';
  };
  _bgmPreviewAudio.onerror = function() {
    _bgmPreviewAudio = null;
    if (btn) btn.innerHTML = '&#x25B6; 试听';
    showToast('播放失败', 'error');
  };
}

// ---- Intro/Outro Upload ----
function handleIntroUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function(e) {
    S.config.introAudioBase64 = e.target.result;
    saveConfig();
    document.getElementById('introFileName').textContent = file.name;
    if (!S.config.outroAudioBase64) {
      document.getElementById('cfgIntroOutroEnabled').checked = true;
      S.config.introOutroEnabled = true;
    }
    saveConfig();
    renderIntroOutroStatus();
    showToast('片头已加载', 'success');
  };
  reader.readAsDataURL(file);
}

function handleOutroUpload(event) {
  var file = event.target.files[0];
  if (!file) return;
  var reader = new FileReader();
  reader.onload = function(e) {
    S.config.outroAudioBase64 = e.target.result;
    saveConfig();
    document.getElementById('outroFileName').textContent = file.name;
    if (!S.config.introAudioBase64) {
      document.getElementById('cfgIntroOutroEnabled').checked = true;
      S.config.introOutroEnabled = true;
    }
    saveConfig();
    renderIntroOutroStatus();
    showToast('片尾已加载', 'success');
  };
  reader.readAsDataURL(file);
}

function clearIntro() {
  S.config.introAudioBase64 = '';
  saveConfig();
  document.getElementById('introFileName').textContent = '';
  renderIntroOutroStatus();
  showToast('片头已清除', 'info');
}

function clearOutro() {
  S.config.outroAudioBase64 = '';
  saveConfig();
  document.getElementById('outroFileName').textContent = '';
  renderIntroOutroStatus();
  showToast('片尾已清除', 'info');
}

function renderIntroOutroStatus() {
  var introEl = document.getElementById('introFileName');
  var outroEl = document.getElementById('outroFileName');
  if (introEl) introEl.textContent = S.config.introAudioBase64 ? '已加载片头' : '未选择';
  if (outroEl) outroEl.textContent = S.config.outroAudioBase64 ? '已加载片尾' : '未选择';
}

// ---- Voice Volume Normalization ----
function computePeak(buffer) {
  var peak = 0;
  for (var ch = 0; ch < buffer.numberOfChannels; ch++) {
    var data = buffer.getChannelData(ch);
    for (var i = 0; i < data.length; i++) {
      var abs = Math.abs(data[i]);
      if (abs > peak) peak = abs;
    }
  }
  return peak;
}

function computeRms(buffer) {
  var sum = 0;
  var count = 0;
  for (var ch = 0; ch < buffer.numberOfChannels; ch++) {
    var data = buffer.getChannelData(ch);
    for (var i = 0; i < data.length; i++) {
      sum += data[i] * data[i];
      count++;
    }
  }
  return Math.sqrt(sum / Math.max(1, count));
}

function applyGainToBuffer(buffer, gain) {
  // Returns a NEW buffer with gain applied
  var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  var out = audioCtx.createBuffer(buffer.numberOfChannels, buffer.length, buffer.sampleRate);
  for (var ch = 0; ch < buffer.numberOfChannels; ch++) {
    var src = buffer.getChannelData(ch);
    var dst = out.getChannelData(ch);
    for (var i = 0; i < src.length; i++) dst[i] = src[i] * gain;
  }
  audioCtx.close();
  return out;
}

function normalizeVoiceBuffers(buffers, speakers, segments) {
  // 1. Peak normalize each buffer to targetPeakDb
  var targetDb = S.config.voiceTargetPeakDb || -3;
  var targetPeak = Math.pow(10, targetDb / 20);
  var peakGains = [];
  for (var i = 0; i < buffers.length; i++) {
    var peak = computePeak(buffers[i]);
    var g = peak > 0 ? Math.min(2, targetPeak / peak) : 1;
    peakGains.push(g);
    buffers[i] = applyGainToBuffer(buffers[i], g);
  }
  // 2. Per-speaker RMS equalize
  if (S.config.speakerRmsEqualize && speakers && segments) {
    var spRms = {};
    var spCount = {};
    for (var j = 0; j < buffers.length; j++) {
      var sp = segments[j] ? (segments[j].speaker || '默认') : '默认';
      if (!spRms[sp]) { spRms[sp] = 0; spCount[sp] = 0; }
      spRms[sp] += computeRms(buffers[j]);
      spCount[sp]++;
    }
    var spAvgRms = {};
    var maxAvg = 0;
    Object.keys(spRms).forEach(function(k) {
      spAvgRms[k] = spRms[k] / Math.max(1, spCount[k]);
      if (spAvgRms[k] > maxAvg) maxAvg = spAvgRms[k];
    });
    Object.keys(spAvgRms).forEach(function(k) {
      var g = maxAvg > 0 ? Math.min(2, maxAvg / spAvgRms[k]) : 1;
      spAvgRms[k] = g;
    });
    for (var k = 0; k < buffers.length; k++) {
      var spk = segments[k] ? (segments[k].speaker || '默认') : '默认';
      if (spAvgRms[spk]) {
        buffers[k] = applyGainToBuffer(buffers[k], spAvgRms[spk]);
      }
    }
    appLog('[NORM] Per-speaker RMS gains: ' + JSON.stringify(spAvgRms), 'i');
  }
  appLog('[NORM] Peak normalize gains: ' + peakGains.map(function(g) { return g.toFixed(3); }).join(', '), 'i');
  return buffers;
}

// ---- BGM Mixing with Sidechain Ducking ----
async function mixBgmIntoVoice(voiceBuffer) {
  if (!S.config.bgmEnabled || !S.config.bgmAudioBase64) return voiceBuffer;
  showToast('正在混入 BGM...', 'info');
  // Decode BGM
  var bgmArrayBuffer = dataUrlToArrayBuffer(S.config.bgmAudioBase64);
  var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  var bgmBuffer;
  try {
    bgmBuffer = await audioCtx.decodeAudioData(bgmArrayBuffer);
  } catch(e) {
    audioCtx.close();
    showToast('BGM 解码失败: ' + e.message, 'error');
    return voiceBuffer;
  }
  var sampleRate = voiceBuffer.sampleRate;
  var channels = Math.max(voiceBuffer.numberOfChannels, bgmBuffer.numberOfChannels);
  var totalDuration = voiceBuffer.duration;
  // Loop BGM if shorter than voice
  var offlineCtx = new OfflineAudioContext(channels, Math.ceil(totalDuration * sampleRate), sampleRate);
  // Voice source
  var voiceSrc = offlineCtx.createBufferSource();
  voiceSrc.buffer = voiceBuffer;
  var voiceGain = offlineCtx.createGain();
  voiceGain.gain.value = 1.0;
  voiceSrc.connect(voiceGain);
  voiceGain.connect(offlineCtx.destination);
  voiceSrc.start(0);
  // BGM source (loop)
  var bgmSrc = offlineCtx.createBufferSource();
  bgmSrc.buffer = bgmBuffer;
  bgmSrc.loop = true;
  var bgmGain = offlineCtx.createGain();
  var bgmVol = S.config.bgmVolume || 0.126;
  var duckDepth = S.config.bgmDuckDepth || 0.5;
  var fadeMs = S.config.bgmDuckFadeMs || 300;
  var fadeSec = fadeMs / 1000;
  // Build ducking automation: BGM at full volume from 0, duck down at voice start, recover at voice end
  bgmGain.gain.setValueAtTime(bgmVol, 0);
  bgmGain.gain.setValueAtTime(bgmVol, 0);
  bgmGain.gain.linearRampToValueAtTime(bgmVol * duckDepth, Math.min(fadeSec, totalDuration));
  // Stay ducked through the voice
  bgmGain.gain.setValueAtTime(bgmVol * duckDepth, Math.max(0, totalDuration - fadeSec));
  bgmGain.gain.linearRampToValueAtTime(bgmVol, totalDuration);
  bgmSrc.connect(bgmGain);
  bgmGain.connect(offlineCtx.destination);
  bgmSrc.start(0);
  var rendered = await offlineCtx.startRendering();
  audioCtx.close();
  return rendered;
}

function dataUrlToArrayBuffer(dataUrl) {
  var base64 = dataUrl.split(',')[1] || dataUrl;
  var binary = atob(base64);
  var bytes = new Uint8Array(binary.length);
  for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

// ---- Intro/Outro Splicing (port from podmerge.html) ----
async function spliceIntroOutro(mainBuffer) {
  if (!S.config.introOutroEnabled) return mainBuffer;
  if (!S.config.introAudioBase64 && !S.config.outroAudioBase64) return mainBuffer;
  var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  var introBuffer = null, outroBuffer = null;
  try {
    if (S.config.introAudioBase64) {
      introBuffer = await audioCtx.decodeAudioData(dataUrlToArrayBuffer(S.config.introAudioBase64));
    }
    if (S.config.outroAudioBase64) {
      outroBuffer = await audioCtx.decodeAudioData(dataUrlToArrayBuffer(S.config.outroAudioBase64));
    }
  } catch(e) {
    audioCtx.close();
    showToast('片头/片尾解码失败: ' + e.message, 'error');
    return mainBuffer;
  }
  var sampleRate = mainBuffer.sampleRate;
  var channels = mainBuffer.numberOfChannels;
  var fadeSec = (S.config.introOutroFadeMs || 500) / 1000;
  var mode = S.config.introOutroMode || 'fade';

  var introDur = introBuffer ? introBuffer.duration : 0;
  var outroDur = outroBuffer ? outroBuffer.duration : 0;
  var totalDuration = introDur + mainBuffer.duration + outroDur;
  var offlineCtx = new OfflineAudioContext(channels, Math.ceil(totalDuration * sampleRate), sampleRate);

  var introSrc = introBuffer ? offlineCtx.createBufferSource() : null;
  var mainSrc = offlineCtx.createBufferSource();
  var outroSrc = outroBuffer ? offlineCtx.createBufferSource() : null;
  if (introSrc) introSrc.buffer = introBuffer;
  mainSrc.buffer = mainBuffer;
  if (outroSrc) outroSrc.buffer = outroBuffer;

  var introGain = offlineCtx.createGain();
  var mainGain = offlineCtx.createGain();
  var outroGain = offlineCtx.createGain();

  var outroStartTime = introDur + mainBuffer.duration;

  if (mode === 'fade' && fadeSec > 0) {
    if (introSrc) {
      introGain.gain.setValueAtTime(1, 0);
      introGain.gain.setValueAtTime(1, Math.max(0, introDur - fadeSec));
      introGain.gain.linearRampToValueAtTime(0, introDur);
    }
    mainGain.gain.setValueAtTime(0, introDur);
    mainGain.gain.linearRampToValueAtTime(1, introDur + fadeSec);
    mainGain.gain.setValueAtTime(1, Math.max(introDur + fadeSec, outroStartTime - fadeSec));
    mainGain.gain.linearRampToValueAtTime(0, outroStartTime);
    if (outroSrc) {
      outroGain.gain.setValueAtTime(0, outroStartTime);
      outroGain.gain.linearRampToValueAtTime(1, outroStartTime + fadeSec);
    }
  } else {
    if (introSrc) introGain.gain.setValueAtTime(1, 0);
    mainGain.gain.setValueAtTime(1, introDur);
    if (outroSrc) outroGain.gain.setValueAtTime(1, outroStartTime);
  }

  if (introSrc) { introSrc.connect(introGain); introGain.connect(offlineCtx.destination); introSrc.start(0); }
  mainSrc.connect(mainGain); mainGain.connect(offlineCtx.destination); mainSrc.start(introDur);
  if (outroSrc) { outroSrc.connect(outroGain); outroGain.connect(offlineCtx.destination); outroSrc.start(outroStartTime); }

  var rendered = await offlineCtx.startRendering();
  audioCtx.close();
  return rendered;
}

// ---- Podcast Metadata Generation ----
async function generateMetadata() {
  var apiKey = S.config.glmApiKey;
  if (!apiKey) { showToast('请先在设置中填入 GLM API Key', 'error'); return; }
  var text = E.textInput.value.trim();
  if (!text) { showToast('文本为空', 'error'); return; }
  E.genMetadataBtn.disabled = true;
  E.genMetadataBtn.textContent = '⏳ 正在生成...';
  showToast('正在调用 GLM 生成元数据...', 'info');
  var systemPrompt = '你是一个播客元数据生成助手，专为《娱乐资本论·娱资每日早报》设计。\\\\n'
    + '根据用户提供的播客台词文本（以及可选的原始新闻要点），生成以下三项内容：\\\\n'
    + '\\\\n'
    + '1. title: 标题必须严格遵循格式 "<月份>月<日期>日娱资每日早报：<核心内容概括>"，其中月份和日期从台词中提取（如台词中出现"6月18日"则标题为"6月18日娱资每日早报：<概括>"）。概括部分用 8-15 字简洁表达本期最核心的新闻主题，不要使用"等等""多个"等模糊词，可适当具象化（例如"6月18日娱资每日早报：TikTok短剧分账破亿，黑神话悟空销量破三千万"）。\\\\n'
    + '\\\\n'
    + '2. shownotes: 按以下结构输出（保留"关键词："、"本期主要内容："、"章节速览"、"关于《娱乐资本论》"、"欢迎全平台搜索关注【娱乐资本论】"等小标题，每节之间用空行分隔）：\\\\n'
    + '   关键词：\\\\n'
    + '   <15-20 个中文关键词，逗号分隔，覆盖本期所有新闻的核心名词与产业概念>\\\\n'
    + '   \\\\n'
    + '   本期主要内容：\\\\n'
    + '   <3-5 句中文摘要，概括本期 10 条新闻的核心信息流，体现产业逻辑而非简单罗列>\\\\n'
    + '   \\\\n'
    + '   章节速览\\\\n'
    + '   <按 00:00 / 00:30 / 01:00 等时间戳格式列出 5-8 个章节，每个章节标题对应一组相关新闻>\\\\n'
    + '   \\\\n'
    + '   关于《娱乐资本论》\\\\n'
    + '   <固定栏目介绍：娱乐资本论——中国娱乐产业第一垂直新媒体。我们关注文化的产业融合，影视的真挚表达，互联网娱乐的时代精神。如今，娱乐资本论的关注视角不仅仅局限在影视综、明星经济，现已快速覆盖至微短剧、互联网、电商、营销等多元领域，并致力于产出全网最优质的独家报道。娱乐资本论是北京市文化产业投融资协会会员单位，并与中国网络视听大会、北京国际电影节、上海国际电影节等行业大会展开了长期、深度的合作。>\\\\n'
    + '   \\\\n'
    + '   欢迎全平台搜索关注【娱乐资本论】\\\\n'
    + '\\\\n'
    + '3. tags: 8-12 个中文标签，逗号分隔，覆盖本期新闻涉及的产业领域、公司、产品名、技术概念等。\\\\n'
    + '\\\\n'
    + '严格按 JSON 格式输出：{"title":"...","shownotes":"...","tags":"标签1,标签2,..."}\\\\n'
    + '不要添加解释或 markdown 代码块标记。shownotes 字段内的换行用 \\\\n 表示。';
  try {
    var resp = await fetch('/api/glm/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        apiKey: apiKey,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: (function() {
            var rawNews = document.getElementById('metadataRawNews') ? document.getElementById('metadataRawNews').value.trim() : '';
            var userContent = '【播客台词文本】\\n' + text.substring(0, 3500);
            if (rawNews) {
              userContent += '\\n\\n【原始新闻要点（用户补充）】\\n' + rawNews.substring(0, 1500);
            }
            return userContent;
          })() }
        ]
      })
    });
    var data = await resp.json();
    if (data.choices && data.choices[0]) {
      var content = data.choices[0].message.content.trim();
      // Strip code fences if present (escape backticks since we are inside template literal)
      var fence = String.fromCharCode(96);
      var fenceRe = new RegExp('^' + fence + fence + fence + 'json\\\\s*', 'i');
      var fenceRe2 = new RegExp('^' + fence + fence + fence + '\\\\s*');
      var fenceRe3 = new RegExp(fence + fence + fence + '\\\\s*$', '');
      content = content.replace(fenceRe, '').replace(fenceRe2, '').replace(fenceRe3, '');
      var parsed = JSON.parse(content);
      document.getElementById('metadataResult').style.display = 'block';
      document.getElementById('metadataTitle').value = parsed.title || '';
      document.getElementById('metadataShownotes').value = parsed.shownotes || '';
      document.getElementById('metadataTags').value = parsed.tags || '';
      showToast('元数据生成完成', 'success');
    } else {
      showToast('GLM 返回异常', 'error');
    }
  } catch(e) {
    showToast('生成失败: ' + e.message, 'error');
  } finally {
    E.genMetadataBtn.disabled = false;
    E.genMetadataBtn.textContent = '✨ 生成标题/摘要/标签';
  }
}

function copyMetadata() {
  var title = document.getElementById('metadataTitle').value;
  var shownotes = document.getElementById('metadataShownotes').value;
  var tags = document.getElementById('metadataTags').value;
  var text = '标题：' + title + '\\n\\nShownotes：\\n' + shownotes + '\\n\\nTags：' + tags;
  navigator.clipboard.writeText(text).then(function() {
    showToast('已复制到剪贴板', 'success');
  }).catch(function() {
    showToast('复制失败', 'error');
  });
}

// ---- v2.14 downloadWavVoiceOnly ----
function downloadWavVoiceOnly() {
  if (!S.resultWavBlobVoiceOnly) {
    showToast('纯人声版本不可用，请先合成', 'error');
    return;
  }
  var name = (S.projectName || S.downloadTimestamp || 'tts') + '-voiceonly.wav';
  downloadBlob(S.resultWavBlobVoiceOnly, name);
}
<\/script>
</body>
</html>`;
}
// v2.17 source — Deployed: 2026-06-18
