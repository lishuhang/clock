// ============================================================
// gpt2-worker-kmage-v1.5.js —— 版本: kmage-kdr-1.5
// AI生图 · 双通道单文件 Cloudflare Worker（后端代理 + 内嵌前端）
//
// 通道:
//   [kmage]（默认）—— 「kmage 站点」官方 OpenAI 兼容 API
//     - 会话类操作（注册/登录/签到/API Key/额度）走 cookie 会话
//     - 生图走 Bearer API Key，1 积分 = 1 张图，失败自动返还
//   [kdr] —— 「kdr 站点」Keydraw 免费共享 Gift Key 模式
//     - 2026-09 上游改版（Draw Studio）后契约: 生成请求不再使用
//       Authorization 头，改为把 key/host 放入请求 body
//       （host 由上游 /api/channels 下发，免费 Key 固定线路+模型+1K）
//     - 任务制: POST 生成/edits → GET /api/image-tasks/{id} 轮询 →
//       success 后 data[].url 取图（经本 Worker 图片代理转 b64）
//
// 架构（沿袭单文件 Service Worker 骨架）:
//   - HTML_CONTENT 内嵌前端（生图 UI + 设置 + 控制台 + 关于）
//   - /api/kmage/* → kmage 上游 /api/*（会话代理，X-Kmage-Session 头）
//   - /kmage/v1/*  → kmage 上游 /v1/*（Bearer 透传）
//   - /api/kdr/*   → kdr 上游 /api/*（透明转发，鉴权在 body）
//   - /kdr/img?url= → kdr 结果图片拉取代理（回传图片字节）
//   - 号池与设置保存在浏览器 localStorage（Worker 无状态，无 KV）
//
// 号池模式（kmage 通道，参考马良 v27.2 原则）:
//   - 轮换策略 most-credits / round-robin；自动注册、批量签到
//   - 401 自动重登、402 自动换号、429 退避、5xx 同号+换号重试
//   - 反模式化: 拟人邮箱/密码、随机化节奏、UA 透传真实访客 UA
//
// 版本: kmage-kdr-1.5 (2026-09-23)
//   v1.5 变更（直连优先 / Direct-First）:
//   - 故障: 2026-09-23 起双上游同时收紧风控——kdr 将 Cloudflare Worker 出口
//     IP 段列入免费 Key 黑名单（生成报「此 IP 已被加入免费 Key 黑名单」），
//     kmage 将生图环境风控扩大到所有数据中心出口 IP 的生图请求（报
//     「账号使用环境异常，充值后解锁」），两通道经 Worker 代理的生图全拒
//   - 修复: 生图类请求改由访客浏览器直连上游（住宅 IP + 真实 UA，即上游
//     期望的正常使用环境；两上游均开放 Access-Control-Allow-Origin: *），
//     Worker 代理降级为直连网络失败时的自动回退；直连目标地址运行时经
//     GET /about 自描述接口获取，不写入本页静态文本（脱敏原则不变）
//   - 范围: kmage /v1/images/generations（Bearer）与 kdr /api/*（gift-key/
//     generations/edits/轮询）直连优先；kdr 结果图优先浏览器直连图床
//     （实测不校验 Referer），失败回退 /kdr/img 代理；kmage 会话类操作
//     （注册/登录/签到/Key 管理，Cookie 会话）不受风控影响，仍走代理
//   - 可观测性: 每次请求在控制台日志标注「直连/代理」路径与回退事件
//   v1.4 变更:
//   - 导航统一: 全宽度右上角仅一个齿轮按钮，点开浮窗以选项卡切换
//     设置/控制台/关于；桌面三按钮与窄屏汉堡按钮双轨实现移除，
//     三面板 DOM 收敛为隐藏宿主 + hub 搬运复用（组件复用、代码精简）
//   - 设置分区: 「通用选项 / kmage 通道选项 / kdr 通道选项」三区常驻，
//     选中任一通道均可直接调整另一通道的专属选项
//   - 创作面板记忆: 模型（按通道分存）/比例/精细度/分辨率档/提示词
//     存 localStorage["kmage_form_v1"]，下次打开自动恢复
//   - PWA: /manifest.webmanifest + /sw.js + PNG 图标（白底圆角矩形
//     叠加画笔颜料盘 logo），名称「AI生图」，standalone 模式（保留
//     系统标题栏），设置 → 通用选项提供「安装到系统」按钮
//   v1.3 变更:
//   - 竖屏手机适配: 窄屏导航合并为单一菜单按钮 + 选项卡浮窗
//     （设置/控制台/关于三面板复用，内容节点按需搬运，无重复 ID）；
//     版本号收进标题下方堆叠，触控目标与弹窗高度按移动端优化
//   - 深色模式: 设置新增「界面主题」（跟随系统/浅色/深色，默认跟随系统），
//     CSS 全量变量化 + data-theme + prefers-color-scheme 实时跟随
//   - 历史记录增强: 任务持久化（kmage_hist_v1，成功/失败/中断均入册），
//     成功条目存本地缩略图（canvas 生成）与 kdr 上游下载地址，点击回看；
//     支持历史 JSON 导出/导入（跨设备回看上游存储图片）
//   - 图标修正: 设置按钮太阳 -> 齿轮；header 与关于页 logo 换为
//     画笔+颜料盘（与 favicon 同款线条图形）
//   - 排障新知: 上游对直连数据中心 IP 的新生号返回 403
//     account_environment_abnormal（Worker 代理路径正常），已写入文档
//   v1.2 变更:
//   - kdr 通道修复复活: 适配上游 2026-09 改版新契约（key/host 入 body、
//     任务轮询、结果 URL 转存），Gift Key 实测可出图
//   - header 通道选择器（kmage 默认 / kdr），状态与设置按通道隔离
//   - UI 重构: footer 移除；「文档」「帮助」合并为「关于」；
//     「号池」→「设置」、「日志」→「控制台」，均为线条 SVG 图标按钮
//   - 新增设置级 JSON 导入/导出（号池 + 全部设置项 + kdr 自定义 Key）
//   - favicon（画笔+颜料盘线条 SVG）与「ai」字母组合 logo
//     （header 左上角 + 关于弹窗顶部）
//   - 对外页面文档脱敏: 源站一律以「kmage 站点 / kdr 站点」表述，
//     真实上游仅经 /about 自描述接口提供给排障方
//   - 内嵌文档整合马良渠道至今的完整迭代时间线（按实际日期排序）
// ============================================================

const VERSION = 'kmage-kdr-1.5';
const UPSTREAM = 'https://image.dddd.zone';        // kmage 通道上游（对外文档中以「kmage 站点」表述）
const KDR_UPSTREAM = 'https://keydraw.97api.com';  // kdr 通道上游（对外文档中以「kdr 站点」表述）
const SESSION_COOKIE = 'kmage_session';
const SESSION_HEADER = 'X-Kmage-Session';
const SET_SESSION_HEADER = 'X-Kmage-Set-Session';
const UA_FALLBACK_POOL = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15'
];
function pickUA(request) {
  var real = request && request.headers ? request.headers.get('User-Agent') : '';
  if (real && real.length > 20 && real.indexOf('Mozilla') === 0) return real; // 透访客真实 UA（马良原则）
  return UA_FALLBACK_POOL[Math.floor(Math.random() * UA_FALLBACK_POOL.length)];
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, ' + SESSION_HEADER,
    'Access-Control-Expose-Headers': SET_SESSION_HEADER,
    'Access-Control-Max-Age': '86400'
  };
}

function jsonResp(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { 'Content-Type': 'application/json; charset=utf-8' }
  });
}

// ---- kmage 会话类代理: /api/kmage/* → kmage 上游 /api/* ------
// 前端以 SESSION_HEADER 携带某账号的会话令牌值；worker 还原为
// Cookie 头发往上游，并把响应中的新会话经 SET_SESSION_HEADER 送回
// 前端更新 localStorage。
async function handleSessionProxy(request, url) {
  const sub = url.pathname.slice('/api/kmage'.length) || '/';
  const upstreamUrl = UPSTREAM + '/api' + sub + (url.search || '');
  const headers = new Headers();
  headers.set('Content-Type', request.headers.get('Content-Type') || 'application/json');
  headers.set('Accept', 'application/json');
  headers.set('Origin', UPSTREAM);
  headers.set('Referer', UPSTREAM + '/');
  headers.set('User-Agent', pickUA(request));
  const sess = request.headers.get(SESSION_HEADER) || '';
  if (sess) headers.set('Cookie', SESSION_COOKIE + '=' + sess);
  const opts = { method: request.method, headers: headers };
  if (request.method === 'POST' || request.method === 'PUT' || request.method === 'PATCH' || request.method === 'DELETE') {
    const buf = await request.arrayBuffer();
    if (buf.byteLength > 0) opts.body = buf;
  }
  const upResp = await fetch(upstreamUrl, opts);
  const respHeaders = new Headers(corsHeaders());
  const ct = upResp.headers.get('Content-Type');
  if (ct) respHeaders.set('Content-Type', ct);
  // 捕获上游会话续期/轮换（兼容 getSetCookie 与单值读取）
  let setCookies = [];
  try {
    if (typeof upResp.headers.getSetCookie === 'function') setCookies = upResp.headers.getSetCookie();
  } catch (e) {}
  if (!setCookies.length) {
    const sc = upResp.headers.get('Set-Cookie');
    if (sc) setCookies = [sc];
  }
  for (let i = 0; i < setCookies.length; i++) {
    const m = String(setCookies[i]).match(new RegExp(SESSION_COOKIE + '=([^;]+)'));
    if (m && m[1]) { respHeaders.set(SET_SESSION_HEADER, m[1]); break; }
  }
  const body = await upResp.arrayBuffer();
  return new Response(body, { status: upResp.status, headers: respHeaders });
}

// ---- kmage Bearer 代理: /kmage/v1/* → kmage 上游 /v1/* -------
async function handleV1Proxy(request, url) {
  const sub = url.pathname.slice('/kmage/v1'.length) || '/';
  const upstreamUrl = UPSTREAM + '/v1' + sub + (url.search || '');
  const headers = new Headers();
  const ct = request.headers.get('Content-Type');
  if (ct) headers.set('Content-Type', ct);
  headers.set('Accept', 'application/json');
  headers.set('Origin', UPSTREAM);
  headers.set('Referer', UPSTREAM + '/');
  headers.set('User-Agent', pickUA(request));
  const auth = request.headers.get('Authorization');
  if (auth) headers.set('Authorization', auth);
  const opts = { method: request.method, headers: headers };
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    const buf = await request.arrayBuffer();
    if (buf.byteLength > 0) opts.body = buf;
  }
  const upResp = await fetch(upstreamUrl, opts);
  const respHeaders = new Headers(corsHeaders());
  const rct = upResp.headers.get('Content-Type');
  if (rct) respHeaders.set('Content-Type', rct);
  const body = await upResp.arrayBuffer();
  return new Response(body, { status: upResp.status, headers: respHeaders });
}

// ---- kdr 透明代理: /api/kdr/* → kdr 上游 /api/* ---------------
// 2026-09 改版后上游以 body 携带 key/host 鉴权，不再依赖
// Authorization 头；本代理只做透明转发（multipart 亦兼容，前端
// 不带 Content-Type 时不设置，交由浏览器生成 boundary）。
async function handleKdrProxy(request, url) {
  const sub = url.pathname.slice('/api/kdr'.length) || '/';
  const upstreamUrl = KDR_UPSTREAM + '/api' + sub + (url.search || '');
  const headers = new Headers();
  const ct = request.headers.get('Content-Type');
  if (ct) headers.set('Content-Type', ct);
  headers.set('Accept', 'application/json, text/plain, */*');
  headers.set('Accept-Language', 'zh-CN,zh;q=0.9,en;q=0.8');
  headers.set('Origin', KDR_UPSTREAM);
  headers.set('Referer', KDR_UPSTREAM + '/');
  headers.set('User-Agent', pickUA(request));
  const opts = { method: request.method, headers: headers, redirect: 'follow' };
  if (request.method === 'POST' || request.method === 'PUT' || request.method === 'PATCH' || request.method === 'DELETE') {
    const buf = await request.arrayBuffer();
    if (buf.byteLength > 0) opts.body = buf;
  }
  const upResp = await fetch(upstreamUrl, opts);
  const respHeaders = new Headers(corsHeaders());
  const rct = upResp.headers.get('Content-Type');
  if (rct) respHeaders.set('Content-Type', rct);
  const body = await upResp.arrayBuffer();
  return new Response(body, { status: upResp.status, headers: respHeaders });
}

// ---- kdr 结果图片拉取代理: /kdr/img?url= ----------------------
// kdr 上游任务终态返回第三方图床 URL，需带 Referer 拉取后回传字节，
// 前端将其转为 base64 展示/下载（与 kmage 通道的 b64 数据流对齐）。
async function handleKdrImage(request, url) {
  const target = url.searchParams.get('url') || '';
  if (!/^https?:\/\//i.test(target)) return jsonResp({ error: 'missing or bad url' }, 400);
  let upResp;
  try {
    upResp = await fetch(target, {
      headers: {
        'User-Agent': pickUA(request),
        'Accept': 'image/*,*/*;q=0.8',
        'Referer': KDR_UPSTREAM + '/'
      },
      cf: { cacheEverything: true, cacheTtl: 86400, cacheTtlByStatus: { '200-299': 86400, '400-499': 60, '500-599': 0 } }
    });
  } catch (err) {
    return jsonResp({ error: 'image fetch failed: ' + (err && err.message ? err.message : String(err)) }, 502);
  }
  const respHeaders = new Headers(corsHeaders());
  const ct = upResp.headers.get('Content-Type');
  respHeaders.set('Content-Type', ct || 'application/octet-stream');
  respHeaders.set('Cache-Control', 'public, max-age=86400');
  const body = await upResp.arrayBuffer();
  return new Response(body, { status: upResp.status, headers: respHeaders });
}

// ---- PWA（v1.4）：可安装到操作系统 --------------------------------
// 图标为统一 logo（画笔+颜料盘）叠加白底圆角矩形；应用名「AI生图」；
// display=standalone（保留系统标题栏与窗口控制）。
// SW 仅缓存页面外壳与图标（不拦截代理/API 请求），缓存名随版本更新。
const PWA_ICONS = {
  '/icon-192.png': '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',
  '/icon-512.png': 'iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAMAAADDpiTIAAAA/1BMVEX+/v5Pa/EAAABwh/Spt/hZc/LQ1/uWp/fm6v2GmfZjfPP///+6xfnDzfr///99kfXc4fz///////////////////+gr/gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwexoYAAAAQHRSTlP+/wD//////////wv//9D//3CPTS6w/wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAamx76gAAGAFJREFUeNrtXdti46gSxAaEJEuRHDv5/089uUzmbDKxgOZOVz/tw06iqIvuqqJB4pw6Lvfb9fr88vL09CQQTvH2ql6er9fb/ZI8O2eRMvW36wuSHgaFl+fbpUUAXG7PL0hfrHi5pkOBSJJ8rPsEILi3AIDL/YrkJ4vnBKQgKgDuz0hS6kIQuxkIZL+1uF4qBMAFlb/RMhAFAHcw/mbLgIhA+rH4izDCSxUAuFyRiqYhIJB+3hAQSD9vCAiknzcdJAMA1K+WeLoXAACEX1W+wCUzAC4w/brpAxQA3FH9++kDAsufdxHwBsANr7orJiCw/PuJW3IAoPt3VwS8AADrpz8uKFD+ebcBdwBcUP6bCM/dAWcA3PFquyQCAuqvPyJwiQ8A0L+m4h4ZAKB//VJBFwBcsPXXXFwjAgD57xkBAvKvVzkYCQDIf9+GgED+eSNAIP+8u4AA/+ONAIH880bAIQDg//SvBgX8X94IENj/6TxuVABg/7eTuNMAcMGb6yUuFADAAOgnDucDBARA/3E0IyRAAHlLAQECyFsKCBAA3lJAgADwJoICBIBHPLsDAA4AJxog0AB40wABBcCbBggoAN5ugEAD4N0EBBoA7ybwEwAYAmPWBAQsAN5NQIAB8m4CAlOAvJuAgAfIKy5HAEAB6D+eDwCAAsCQBwoUAGbx8hAAKAA84vYIACgAHKWgQAHgXQIETEDeJeD/AIAJyCauvwEA24CM4vILALANyLMECFBA3ixAQAPyFgICFJB3CRCggLxLgMAoKMt4+Q4AUEC2SlCgA/CM528AQAdgWwIEOgBvGijQAXjTQAEXiHcPEHCBuMb1LwBAAVjG018AYBSEcQ8QEIG8e4AABeCtAwQoAO8eIEAB+MbtEwCgAFzj+RMAmAbkLATfAIAXwTbu7wAAB2QtBAU4IG8hKLATxJsECHBA3k6AgA/I2wkQEAG8WaCACODNAgXGwXizQAEVyJsFCqhA1nEX2AriLQMAAOYyQMAHYh3PAAB3AMAI5G0EMADAOAzruiyL+oy3/1rWYRhHZP/dCOj2LxtWZSY569NBaC23yahlGACAfmJf3hJ/8g65vSMBJaHtVa8oqf9eFKRRA7pDg41+MaG5/1YP3mCAl9pM0VebPiUIOQEF9cdq5lPKkGYN1CB/yKjWen6DFHhGzLqv5ClHSEPL2ltfmiP+OESR7H9lzbsdHD2fBgaayv6frE2LuyCZrD9NIY3kvr+dSoVULhpxdYOngd6kiH2jT0VDqt3yhO7VySCfERtrHXVgnLzaChqBT+cvvfj/i4EHfED5PqJEH4jGqzLH9AuTJzwjioAb8ZOn+mL+0QoGmik1Ib3W1V9j+j9i+49RuJD7CTLcaPo/y8BX+w/4GTuy3Fbx/+HrvXcCE/Qj4Aw2ufr/QwhfA0GEGhAuqpuOGXLwF1F9YhRggsGeSuMBNfgtdnniFnCEuFb/r4AUCLTUmieCyDzZUT94q3KbJmPM58Ggt/8w07RJy5kRNIGSyz9GarScjFotI/7jsKr3mc16sAAtGOiofeipyf9sx74qs1XQd6AEwrr/HDjKvy9qKgsD7jwwgPxLs0YqoENBFDAvAdRpT72p2N1zSHTeyBY7yr933U82ZP9WCiKAQJvP40DjG6ZQAmKX/zn1EYs9cA51+/58ygpyiH+ftZWHM60BhUDunlscC8/0j/7lX+Z8VQP9EOpPd2eU2BUMN390/mM1OxUDk5/VwdEM8h2nnAt5psRjSfPggwCGPcAE8aq8sU4x2sAGHUCmf1txs0zN4W3goJJobvn3kllTFV4p4ZTSjyNgC0gAJf9TNVb56D0F/GPyW4IEuGii74uInv7h/fZAOc9STirOlsHo3wa+JXbFVICn/J/JC2P56ePEsA8p/qBxYwGMWODurKrIZ2gftOtQIUnbtjRO0oePFeRu/0zEsn1wsEiHXM8xEr3hyaUHaKz/n2+EelefSVNVAqYWpQuJQP4PWqdP79ee2szdDQqYWxntJIAJ/3PM/zwkWf6/ajPXCBkY+nsIcOZtBLjyf3KndqTpKhG07AiQrAHgmH9y93f3F179mWXoSYURAHBcn1Pin0+rAcGnFj8RwLoFyGTlmZAjz18T4djihxbgrAKcVFTAtSmeKs3rF42nUxQEcJaBxk8v+es/332aeMVFO2JvO3jI7o0glZT9U9boFO3hF7G6ydtpYmsFO5HokC1RwvESZ7FhcS824bfByXEzyMUACro1jWLTOZ/MP67weoxBEzvfDnZYH2H3JsqEL311+ylhR1zXrvM/OVHkzAXAuQTMrg8e0ga4E0CZvMKQSYdxl5N0u7jri2KG5BSIKtNl+NObOH5Rz58RcSCAoRSYfGXrGFpcfq5c6lU3PVOALT3853TcW3n6iSPpWXq2gVT6/NON2inwR//y70mOQMcuwJ6h/ZE/2mBfeZLwz2UiNtpmzBnAHzCrMQZBa4nkSnbcAaYcxS/gm5JrCH+VsR6oXxtwzdL8DqqMXMfx6HoOFQLfMRYkR7YNIM4emO3nD0QCstLXrRcC+jUBbM05kv/1+BfstucwUTzgQCbYbQGwWYB6TAwAbV3KUxwPOAgBhm0DiHXuOw0AhrC0OTtCmm0DOBK/7xc5m/cb313ugE7TAmRg93I9BNOtB7BTK9/448JWPS1jfhKogquX21GCfmfBJO0P//2Szm0ly8BdUZi8vwdMdCj3XvO/OJ2U+Sf9D+vmwV0RAUbQENMDpliU/XpAM+HNHx/tfXhiNIEVrOL0basU6HcQ5NUf+PZ9tCmg1HqtZKoH7E0Eu/1WxGg7IvGL7+bAmn8vAvG3g8kesGcl6XcbePJeeI5TPWuo7ebSgddofVsyBcDgXfhMSM5UZAowx2kADg/Wqwu8+ToAU9CqpfaALYUH7OUFGY4FYA7k8Uu0HrCk8IC99GmnPrD0XEGeNH7wbdp+GizUA/b6sxS/AvDvCtp1cOIiHg1TsRqAcPmzNLsCECN7U5QSMCfzgH14TYd7QaunjiNw+CGERR6vZRlrwTpeKyWZFYAtCoWfCYTbbS2raOvVdR6gu92gwVP4TnHad5wrYmJ5wB7CpjslOPn9tTQNHyolHzWAaB7wHojETncBdHDeYpkBqqwHbHW32w3fr6MRj9PKsJeuSnvAdj+y1fB8g+St3F+qsfu5TFXcA/5vdJV/5fkGyZfwq4DCq0jCLaoH3K0VMHuWUPIXmjcy9354HVlWD7jTTeHBswAEXML9wIWifzAirwfcqQ6YPAtAwO16tAlBnXQOmNjW+hkMG33/zIB5zoedc3jcgfUrVbjF94C79IKUr4g6YEvarMtEe2vD9GsRPvxsXH4PuMfZ4Nm3zj3+B58nR1dqTf7nw5Hy+MORBTzgDifDBu9XqG1LztCb8v716djN2D8dW8AD7lAIGu+/0foZtSHPPmoRD7g/EqC9SdSpEgAU8YC7GwoY/NeQtlEGlcVCL+QB9+YGG/8mOtvyO+fwz0p5wL3tCGp/yn7QMbfx8DvQMftmKQ+4s+HggVBED8m31nneWS4PWGYpZ1V2gDkuZ4rrn2bzgPepbyuIch9jwGbQmKcBxPOA1VGH6CD/OylZ5PzLTA0gmgc8H76ivet9ABnZN4nJAbN5wIOL8dlySBJfU6UpQC4P2By/o9f2AUB7i9ST3bGGKHJ5wDp0Z6P6WIllVJbtALk84DWjr1mdCFwClmBiDZDLA56y7mwUiZmarJLbZ7k84K9rsceO5wLJdXQtWAByecDK/pY6pgCvQYsnJWfO5gE7/H+tDwUZ+nv0FwKRjNN8HrBDyWl9MlgGdDdvL2DI0QBiesAMABC0kDwH6VWWBhDTA3b4SxufCBjCXqSXEojkmWT1gO3/a+NesArb5vD54m4sxZzVA+4eAFNgK3VHQKz85/WAuweADC3Yrmf7o1mmeT3gr3jtdSgswlJysgOiDQJm9oDtaGkbAHuMV2lXgzoaVc7tAfcOgDizTrvtdv14bll2D9haeNoGgIlk2i1HHwCLaJXk94A7J4FTNNG+PFibW0ynrIAHbP3/2waAjFjZdvNPGZBqzPS4yTzgzp3AyGeexsVsnyjQcjLRX00JD9gKvab3AsYM0/sRn7aEB2ylDHvLABiaGnQp4gFbS2XT8wBLS6NuZTxgK2SapgCqpWnnMh6wbaW0fTjQpLduMzxrUg/Y9svbngre2vG3SnnAtqbR9i1Bsh11W8oDtnHAtp3guRlxU8wDtpWftkcCmxl2LucBf8RrpyqwneMO5Txgy69v+2BQMweeCnrAlvrT9tnQvRF1W9IDtuCvbQ7YypnXkh6wpWwMnQKgqspW0gO28Yam83/wZqtygkt6wJYC1PjtAEsT/lZRD9giQRUAULBP5fCALQxkBwAKWwCpPeBj4tj6PaGqAQCU9YAtdcN0C4BqelthD9giQQYAoGwDSO4BH0uQ5m+Krh8AS1kP2CJBVL8AIFzmNK7KTJuU06SWaKVRxzpxTNSSQyQLsnsSuP44FKK3KEdCVGEP+Ng5aP+W2EgycDe/vicZfmhqLusBW/7ZAAB8VMmDz2kEQmCv1wM+dfHJuBgAOG6uYSeDl7IesInGQGuN8M2g1fq5vRCvRBX1gC357+FrQcHbwS7fW5Y7+flMSQ/Y9rctXQPArb+53Q+lhxQASO0B2/LfxUdjx6D1NTrfEkldLKqcB2y9+aqPT4YGTbp43BK6xK5QHgvQ4gH/annt1tsPO/lqdAgAvG6JHWI/n/ssFsEDXuxfkt77AEDAwRC/e6I1zRfcwouKvwc8Olx8aPrI/8HqsC1Z35viaSUznAT4e8DK4UPycyf5px8O3U++QVozY/BOsK8HPMiEHa2+mKg+O+GDUXtchLolwdMDHrZ0YK4yqBdELP75pzUB40nfgzxgx/T30wDo30OcCQAg1c1AIejjASvXqqb3fgCw0lBOKQDEEqBDpgHcPeDVQ9Qs/eSfevkV8auxlBIwhSTCzQMe1aRTs9kGnaCd7K1FfXVLgBB08IAHv+T3YwHa18hC9lZizPDGMAMtOJWT1P5/w9xX/mm3X2kiAEg9wCoEP4ZR5TyTnyqDo9miEbBFNIFCeoA6+nGrkVny3qMAsL1eHc0FDuuf+6me0ENv+T86+BRpG4i2hRej4SD/YWb7GlkEUu1gg/yXkQGGsCTlsg9TZA9lrSX/e4/5P1jO0l+YSZt0Jx2mqyP/cuwy/0cF1r9rjDZQkQCw1ZD/TXQai7dqH601I/K9E6qC/Jte83+kspTvv0gEgLF8+19Fv6F9ScBobRpT3BYQIjvQ/kM6rDcpMzYPngaAwkJQia5DeTsBRyM2+/FQJW0rfSi6/Pe+83/0dk30ijzEblPJu3/ny/94QesqrOCw3xgW09h//o8W9B5ZllE305dC1X8QHMJ78Jbekk38KpUw/avgEYP3iiW3ZPI4pcbqL+IEPCBtU2YKkH8/aGOU/sN8mqg9YGqjAGgzClax5OoBa3yEJiD+q+AWo7dwp+kAqgbI6ANNi+AY0rtq65wUMNN28GxWwTSUN2+jlABZbwHQ0qyj4Bu7/04IwQ4eqiwAszTLLriH9F63/suSKgHiTwPoeZZym4xahlEgbBV98PYPozLAaPNAK9JMW2WTiNIEyM7KHCf/Blkm9oBHx/DHOYcCiEUBJ+SYXGdpH1OINVRjsP5L94CHhwQHneH9x5gH1AsyHKK1Hi5f1y4QMlUTYV9PIb32WCklwO266KCZ6sB9QD0tUHpuoWkr2C7SwmaqA0Sg3hQcnjhv+uhql10mHaqcyHV/QE7jGW6HWVzmhOybwgEZ7+qkooGW250WmWywAk2/ChpoXcnjP9ds6ilKDUbTzxeHms5hWa1qkrM+6Vlu0TbYRjT9fLFUaKXuaPq1lIAy62tA069ECRa6IXVA06/FDCpzSHo4WPlo+tHjcOetyCWpe/wBEwSVc091PRE6f+4SUGSoqrKWxJsF6KoeSCJbuYVAiSYgMeVZUQko8M7NCTSwohKQXwksJ7CAmkpA9sZ7KEzgAmVeciVW3VydO9l7yEQHPFIoU0z7J4gh0RGvJI+Dee/sblD2e9N1df40cx6Y+5SNqqogQQpmr7tjXQUJPDD7x5OmynQJeOBpHmt6GowFZOeBmQW4pQRo5Ct7E8jbeW2jwXAD8pfdvC/dVMVK0QTyi0GNJpA9rEf/c7LvBU0ge9iPZOREgIQSqM4OyooA231E2BfMr77yIsB2Uwjmw0rQgJwIMCfsCVSnBbNqAQkpWCENyIiAUYMFVEgDMiowixbcka4C8iurK2xwGWj2cLkONt+3tTfYgTUSwYzzATPMoBqJYD4KPqAHVEkE8718BSsgfzh9sycXESB82ACRQQpkIwID7OAC4XYrfJ42MGE8tE4xmKsN7JgKKCEG3RCQ5cscEm5wvQg4bemLwAIrqFZDKPjzIG796PEvR5oqQED6IqABgLoRkJqNzzACyoT795tkUk9AYke4cib4rsjGEgBABagHAQltIbSAcrF7IECnogJQAQXD64vRcxIIQAaWRYDXd9xSVAEYQYVjO5WFwAQruHB4ftA9xtcD3SgANoMyxXLyDBnRH1bYDm5LDn591S9SGTjamcZASJ1i4KtAR8nPhJGwOoLyVW9tgi1iDIVWE+p0yo8BhbHwiojAfCJigDw39IorAppvA384IaUQ2DwoJKSRNvAXBOsY85fBBSihBuQpKOZJDU4oGI1VeeJoYHtF4A8pkEat+8Hv2JUDzqABCsUuT3FCy8kYtazDPn4VhXEfFiPdXCfYgMXCnCoI7AT2UAQCAgWgaCwaBQB9AAWAtzFYsg9gFKSGWOdiAMA+YCWmgEYDABVAA2AdY34IwAOsDQJ5G4He8c5ZVwFsAtUIgXx0EGMgtZqDEuufuzU0pe//yH/dneA1rTc0g//VXwYSagIMgfFmA/D/GhIF8TEgWfr/Tw1jYIvK/ph+JOyp6adfpkh8QL9yTf9L63/CHqEQaLZnwJ7EcxfCQG0BlUAy5n4vfQDggxIsRpIWP2vn50Vc+/IIFrN5OEXylbvv9yxuPVpFizKbpRzozWDTR7yt/3vHf93whgRlpk3KeZ71G0vQep7lZtQyYOTvCwAXvATOcRPnJ7wFxnEX5xe8BcZxEecr3gLjOIvzDW+Bbzy9AQAskLMN8AYAsEDOKvAdAGCBjFXgOwDAAhmLgHcA3PEe+IqAdwCc8R64xssnAEAC+HLADwDACeDLAT8AACeALwf8AAB6ANN4Ov8BAIQgz3j+AgB6AFsK8AkAuMFsKcAfAKAHMHUBvgCAHsDUBfgCAHQAx7j/BwDwgphSgC8AoAfwFIF/AXB+xgth2QH+AgAlgFs8Xb4BADSQZwf4PwBAA1l2gP8DAG4gsw5w/gkAlABWcf0HABeUAHYmwDcAYEOAIQX8BgAoQX4U8BsAUAL4UcDvAAALYBO3XwEAIcCmAFx+BwBKADMN+BMAKAHMNOA/AMCOALcC8BMAOCjKrAD8BADmApgVgH8AADeIVwH4BwBwg3gVgH8BcAEPZOMB/AoA8MDO4362AABNoOt4OVsBAD+QUQH4DQBoAmwY4AMAoAlwYYCPAIAmwKUBPAAAmkCn8Xx2BAC2BfuMizMAsCfQY9zO7gAADWDRAB4DADSAgQI4BABoQP8K4BgAoAH9E4BjAGBfsHsCcAwAEMHuCYAFABgP6toBcAAApEDfBNAOAEiBrgmgAwCAgB7ieqYDAFvD/QoANwDADmg9Xi5hAAACes6/CwCAgC4NAA8AXICAbvPvBAAgoN/8uwEAWqDb/LsCAAjokP95AQAI6DP/7gCAJ9ic/+OSfw8AYGeosfy7ZdUDAJgPaClu5/gAwIxQO3E/pwDA+QIq2Iv8owEAVLAj+kcDwPkOItBL+6cBAL5w7eX/fk4LALSBbso/FQBQAx2w/yAAQA10svzJAHjjgigC9XX/GyGRVACgCFQX18s5JwDABOqKlzstiwEAgCfQePUPBwD6QNPVPwIAAIHG0x8OADiDTac/BgAAgZK9PzD9cQAACBSjfpfg1MUBwDsXgCLIbfvdYyQuFgDeIHCDL9BS7Y8OAJSBfNmPs/jjA+ANAnewgTZKfyIAAAOJDd/rPXK64gPgwyO+gg8kKPy3S/xUpQHABycECCKu/CTJTwqAPyh4fgEvDFz311S5zwCAP6Tgdr2+AeEtkE+3pD89vbw8X6+3+yV5dv4HqBJuWxTqNJoAAAAASUVORK5CYII=',
  '/icon-maskable-512.png': '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',
  '/apple-touch-icon.png': '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'
};
function handleManifest() {
  const manifest = {
    id: '/',
    name: 'AI生图',
    short_name: 'AI生图',
    description: 'AI生图 · kmage + kdr 双通道生图工作台（单文件 Cloudflare Worker）',
    lang: 'zh-CN',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    orientation: 'any',
    background_color: '#f4f6fb',
    theme_color: '#f4f6fb',
    icons: [
      { src: '/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' }
    ]
  };
  return new Response(JSON.stringify(manifest), {
    headers: { 'Content-Type': 'application/manifest+json; charset=utf-8', 'Cache-Control': 'no-cache' }
  });
}
function handleSw() {
  const NL = String.fromCharCode(10);
  const sw = [
    "// AI生图 Service Worker（" + VERSION + "）—— 外壳缓存：仅缓存页面外壳与 PWA 图标，",
    "// 不拦截任何代理/API 请求；发布更新后自动清理旧缓存。",
    "var CACHE='ai-image-shell-" + VERSION + "';",
    "var SHELL=['/','/manifest.webmanifest','/icon-192.png','/icon-512.png','/icon-maskable-512.png','/apple-touch-icon.png'];",
    "self.addEventListener('install',function(e){",
    "  e.waitUntil(caches.open(CACHE).then(function(c){return c.addAll(SHELL)}).then(function(){return self.skipWaiting()}));",
    "});",
    "self.addEventListener('activate',function(e){",
    "  e.waitUntil(caches.keys().then(function(ks){return Promise.all(ks.filter(function(k){return k!==CACHE}).map(function(k){return caches.delete(k)}))}).then(function(){return self.clients.claim()}));",
    "});",
    "self.addEventListener('fetch',function(e){",
    "  var u=new URL(e.request.url);",
    "  if(e.request.method!=='GET'||u.origin!==location.origin)return;",
    "  var p=u.pathname;",
    "  var isShell=(p==='/'||p==='/manifest.webmanifest'||p.indexOf('/icon-')===0||p==='/apple-touch-icon.png');",
    "  if(!isShell)return;",
    "  if(p==='/'){",
    "    e.respondWith(fetch(e.request).then(function(r){var cp=r.clone();caches.open(CACHE).then(function(c){c.put('/',cp)});return r}).catch(function(){return caches.match('/')}));",
    "  }else{",
    "    e.respondWith(caches.match(e.request).then(function(r){return r||fetch(e.request).then(function(r2){var cp=r2.clone();caches.open(CACHE).then(function(c){c.put(e.request,cp)});return r2})}));",
    "  }",
    "});"
  ].join(NL);
  return new Response(sw, {
    headers: { 'Content-Type': 'application/javascript; charset=utf-8', 'Cache-Control': 'no-cache', 'Service-Worker-Allowed': '/' }
  });
}
function handleIcon(pathname) {
  const b64 = PWA_ICONS[pathname];
  if (!b64) return new Response(null, { status: 404 });
  const bytes = Uint8Array.from(atob(b64), function (c) { return c.charCodeAt(0); });
  return new Response(bytes, {
    headers: { 'Content-Type': 'image/png', 'Cache-Control': 'public, max-age=86400' }
  });
}

async function handleRequest(request) {
  const url = new URL(request.url);
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (url.pathname === '/favicon.ico') {
    return new Response(null, { status: 204 });
  }
  if (url.pathname === '/manifest.webmanifest') return handleManifest();
  if (url.pathname === '/sw.js') return handleSw();
  if (url.pathname === '/icon-192.png' || url.pathname === '/icon-512.png' || url.pathname === '/icon-maskable-512.png' || url.pathname === '/apple-touch-icon.png') {
    return handleIcon(url.pathname);
  }
  if (url.pathname === '/healthz') {
    return jsonResp({ version: VERSION, upstream: UPSTREAM, kdr_upstream: KDR_UPSTREAM, channels: ['kmage', 'kdr'], time: new Date().toISOString() });
  }
  if (url.pathname === '/about') {
    // 自描述接口：供 AI Agent / 排障工具快速了解本服务（此处保留真实上游地址）
    return jsonResp({
      name: 'AI生图（kmage + kdr 双通道）',
      version: VERSION,
      kind: 'single-file-cloudflare-worker',
      ui: {
        brand: 'AI生图',
        theme: '跟随系统/浅色/深色（默认跟随系统，设置内切换）',
        layout: '全宽度统一：右上角单齿轮按钮 + 选项卡浮窗（设置/控制台/关于）',
        pwa: '可安装（/manifest.webmanifest + /sw.js + PNG 图标：白底圆角 logo），名称「AI生图」，standalone 模式保留系统标题栏',
        history: '近期任务持久化（localStorage: kmage_hist_v1），成功/失败均入册，成功条目含本地缩略图与 kdr 上游下载地址，支持 JSON 导出/导入跨设备回看'
      },
      channels: {
        kmage: {
          default: true,
          upstream: { name: 'kmage 站点', base: UPSTREAM },
          mode: '账号号池（注册/签到攒积分）+ OpenAI 兼容生图；v1.5 直连优先',
          endpoints: {
            session_proxy: '/api/kmage/* -> ' + UPSTREAM + '/api/*（会话经 X-Kmage-Session 头；Cookie 会话无法跨域，仍走代理）',
            v1_proxy: '/kmage/v1/* -> ' + UPSTREAM + '/v1/*（Bearer 透传；v1.5 起为直连失败时的自动回退）',
            v1_direct: '浏览器直连 ' + UPSTREAM + '/v1/images/generations（Bearer；v1.5 起生图直连优先——2026-09-23 上游将数据中心出口 IP 的生图请求全部判为环境异常，Worker 出口 IP 已被拦截）'
          },
          frontend: { pool_storage: 'localStorage: kmage_state_v1' }
        },
        kdr: {
          upstream: { name: 'kdr 站点', base: KDR_UPSTREAM },
          mode: '共享 Gift Key（免费）+ 可选自定义付费 Key；2026-09 新契约: key/host 入 body；v1.5 直连优先',
          endpoints: {
            proxy: '/api/kdr/* -> ' + KDR_UPSTREAM + '/api/*（透明转发；v1.5 起为直连失败时的自动回退）',
            direct: '浏览器直连 ' + KDR_UPSTREAM + '/api/*（key/host 在 body，无鉴权头；v1.5 起直连优先——2026-09-23 上游将 Cloudflare Worker 出口 IP 段列入免费 Key 黑名单）',
            image: '/kdr/img?url=（结果图拉取代理；v1.5 起为浏览器直连图床失败时的回退）',
            task_flow: 'POST /api/image-tasks/generations 或 /edits → GET /api/image-tasks/{id} 轮询 → data[].url'
          },
          frontend: { storage: 'localStorage: kdr_state_v1' }
        }
      },
      shared: { logs_storage: 'localStorage: kmage_logs_v1', channel_storage: 'localStorage: kmage_channel_v1', form_storage: 'localStorage: kmage_form_v1（创作面板选项记忆，模型按通道分存）', history_storage: 'localStorage: kmage_hist_v1（任务历史，成功/失败均入册）', direct_mode: 'v1.5 直连优先: 生图类请求由浏览器直连上游（本接口即地址来源），网络失败自动回退 Worker 代理；kmage 会话类仍走代理（Cookie 跨域不可携带）' },
      docs: '页面右上角「关于」按钮内含自包含 README（含完整迭代时间线，与仓库 README.md 对齐互补）；本 JSON 可作为排障入口',
      generated_at: new Date().toISOString()
    });
  }
  if (url.pathname === '/api/kmage' || url.pathname.startsWith('/api/kmage/')) {
    try { return await handleSessionProxy(request, url); }
    catch (err) { return jsonResp({ error: '代理请求失败: ' + (err && err.message ? err.message : String(err)) }, 502); }
  }
  if (url.pathname === '/kmage/v1' || url.pathname.startsWith('/kmage/v1/')) {
    try { return await handleV1Proxy(request, url); }
    catch (err) { return jsonResp({ error: { message: '代理请求失败: ' + (err && err.message ? err.message : String(err)), type: 'worker_proxy_error' } }, 502); }
  }
  if (url.pathname === '/api/kdr' || url.pathname.startsWith('/api/kdr/')) {
    try { return await handleKdrProxy(request, url); }
    catch (err) { return jsonResp({ error: 'kdr 代理请求失败: ' + (err && err.message ? err.message : String(err)) }, 502); }
  }
  if (url.pathname === '/kdr/img') {
    try { return await handleKdrImage(request, url); }
    catch (err) { return jsonResp({ error: 'kdr 图片代理失败: ' + (err && err.message ? err.message : String(err)) }, 502); }
  }
  return new Response(HTML_CONTENT, {
    headers: { 'Content-Type': 'text/html;charset=UTF-8', 'Cache-Control': 'no-cache' }
  });
}

addEventListener('fetch', function (event) {
  event.respondWith(handleRequest(event.request));
});
// ============================================================
// 内嵌前端
// ============================================================
const HTML_CONTENT = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- ============================================================
  AI AGENT / 排障提示（AI Agent Notice）:
  本页是自包含的单文件 Cloudflare Worker 应用（后端代理 + 内嵌前端 + 号池）。
  - 可将本页/本文件整体作为 skill 调用：所有交互均在页面内完成，无外部依赖
  - 排障请先读: 右上角齿轮按钮 →「关于」选项卡（自包含 README，
    含马良渠道至今完整迭代时间线；仓库内 README.md 为维护者版，已并入原 CHANGELOG，两版对齐互补）
  - 服务自描述: GET /about（版本、双通道端点、存储键、真实上游地址，
    v1.5 起亦为浏览器直连上游的地址来源）；健康: GET /healthz
  - v1.5 直连优先: 2026-09-23 起上游拉黑数据中心出口 IP（kdr: 免费 Key
    黑名单；kmage: 生图环境异常），生图类请求由访客浏览器直连上游
    （地址自 /about 获取），网络失败自动回退 Worker 代理；会话类仍走代理
  - 前端日志: localStorage["kmage_logs_v1"]；kmage 号池: localStorage["kmage_state_v1"]；
    kdr 设置: localStorage["kdr_state_v1"]；当前通道: localStorage["kmage_channel_v1"]；
    任务历史（成功/失败均含，成功存缩略图与 kdr 上游地址）: localStorage["kmage_hist_v1"]，
    可在「近期任务」处导出/导入 JSON；界面主题: 设置内（跟随系统/浅色/深色）；
    创作面板选项记忆（模型按通道分存/比例/精细度/提示词）: localStorage["kmage_form_v1"]
  - PWA: 可安装到操作系统（/manifest.webmanifest + /sw.js + PNG 图标），
    名称「AI生图」，standalone 模式（保留系统标题栏）；右上角单齿轮按钮
    打开浮窗，选项卡切换设置/控制台/关于（全宽度统一组件）
  - 上游: 双通道（kmage 站点 / kdr 站点），真实地址见 GET /about（对外页面脱敏）
============================================================ -->
<title>AI生图 · kmage-kdr-1.5</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32' fill='none' stroke='%234f6bf2' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M14.5 5.5C8.4 5.5 3.5 10.3 3.5 16.3S8.4 27 14.5 27c1.8 0 2.9-1 2.9-2.4 0-.7-.3-1.2-.8-1.8-.4-.5-.7-1-.7-1.6 0-1.3 1-2.2 2.5-2.2h2.9c3 0 5.2-1.9 5.2-4.8 0-5.1-5.4-8.7-12-8.7z'/%3E%3Cpath d='M19.8 19.5l6.3-9.9c.7-1.1.4-2.6-.7-3.3-1.1-.7-2.6-.4-3.3.7l-6.3 9.9 1 3.4z'/%3E%3Ccircle cx='9.3' cy='12.4' r='1.3'/%3E%3Ccircle cx='14.6' cy='10' r='1.3'/%3E%3Ccircle cx='8.9' cy='18.7' r='1.3'/%3E%3C/svg%3E">
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#f4f6fb">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#12151c">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="AI生图">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<style>
:root{
  --bg:#f4f6fb; --card:#ffffff; --border:#e3e7f0; --text:#1c2333; --text-2:#5a6478; --text-muted:#8a93a6;
  --accent:#4f6bf2; --accent-strong:#3d55cc; --accent-hover:#3d55cc; --accent-soft:#eceffd;
  --ok:#18a058; --ok-soft:#e8f7ef; --warn:#d98324; --warn-soft:#fdf3e4; --err:#d64541; --err-soft:#fdecec;
  --input-bg:#fbfcfe; --btn-bg:#ffffff; --soft-bg:#f4f6fb; --pill-mut-bg:#eef0f5;
  --header-bg:rgba(244,246,251,.92); --backdrop:rgba(28,35,51,.45);
  --radius:12px; --shadow:0 1px 3px rgba(28,35,51,.06),0 8px 24px rgba(28,35,51,.05);
  color-scheme:light;
}
/* 深色主题: data-theme="dark"（手动）或 system 且系统为深色 */
:root[data-theme="dark"]{
  --bg:#12151c; --card:#1a1f2b; --border:#2b3345; --text:#e6e9f2; --text-2:#aab3c5; --text-muted:#6e788c;
  --accent:#6c85f5; --accent-strong:#9db0ff; --accent-hover:#5570e0; --accent-soft:#222c4d;
  --ok:#34c477; --ok-soft:#142a1d; --warn:#e8a04c; --warn-soft:#302413; --err:#e06460; --err-soft:#371d1d;
  --input-bg:#141822; --btn-bg:#202634; --soft-bg:#171b26; --pill-mut-bg:#252b39;
  --header-bg:rgba(18,21,28,.88); --backdrop:rgba(0,0,0,.62);
  --shadow:0 1px 3px rgba(0,0,0,.45),0 8px 24px rgba(0,0,0,.38);
  color-scheme:dark;
}
@media (prefers-color-scheme:dark){
  :root[data-theme="system"]{
    --bg:#12151c; --card:#1a1f2b; --border:#2b3345; --text:#e6e9f2; --text-2:#aab3c5; --text-muted:#6e788c;
    --accent:#6c85f5; --accent-strong:#9db0ff; --accent-hover:#5570e0; --accent-soft:#222c4d;
    --ok:#34c477; --ok-soft:#142a1d; --warn:#e8a04c; --warn-soft:#302413; --err:#e06460; --err-soft:#371d1d;
    --input-bg:#141822; --btn-bg:#202634; --soft-bg:#171b26; --pill-mut-bg:#252b39;
    --header-bg:rgba(18,21,28,.88); --backdrop:rgba(0,0,0,.62);
    --shadow:0 1px 3px rgba(0,0,0,.45),0 8px 24px rgba(0,0,0,.38);
    color-scheme:dark;
  }
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.6}
a{color:var(--accent);text-decoration:none}
.wrap{max-width:1080px;margin:0 auto;padding:0 16px 48px}
header.top{display:flex;align-items:center;gap:12px;padding:12px 0;position:sticky;top:0;background:var(--header-bg);backdrop-filter:blur(8px);z-index:50;border-bottom:1px solid var(--border)}
.brand{display:flex;align-items:center;gap:9px;flex:none;min-width:0}
.brand .logo{width:27px;height:27px;color:var(--accent);flex:none}
.brand h1{font-size:17px;margin:0;letter-spacing:.5px;white-space:nowrap}
.brand-txt{display:flex;flex-direction:column;line-height:1.2;flex:none}
.brand .ver{font-size:10px;color:var(--text-muted);white-space:nowrap}
.chan-sel{padding:4px 8px;border:1px solid var(--border);border-radius:8px;background:var(--input-bg);color:var(--text);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;outline:none;margin-left:2px}
.chan-sel:focus{border-color:var(--accent)}
.top-right{margin-left:auto;display:flex;align-items:center;gap:8px;flex:none}
.badge{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:999px;background:var(--accent-soft);color:var(--accent-strong);font-size:12px;font-weight:600;max-width:150px;white-space:nowrap}
.badge.zero{background:var(--err-soft);color:var(--err)}
.icon-btn{width:36px;height:32px;padding:0;display:inline-flex;align-items:center;justify-content:center;border-radius:8px;border:1px solid var(--border);background:var(--btn-bg);color:var(--text-2);cursor:pointer;transition:all .15s;flex:none}
.icon-btn:hover{border-color:var(--accent);color:var(--accent)}
.icon-btn svg{width:17px;height:17px}
.dialog-host{display:none}
.hub-pane .dlg-body{padding:0;max-height:none;overflow:visible}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow)}
.gen-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px;margin-top:16px}
@media (max-width:860px){.gen-grid{grid-template-columns:1fr}}
.panel{padding:18px}
.panel h2{margin:0 0 12px;font-size:15px}
label.f{display:block;margin:12px 0 6px;font-size:12px;color:var(--text-2);font-weight:600}
textarea,input[type=text],input[type=email],input[type=password],input[type=number],select{
  width:100%;padding:9px 12px;border:1px solid var(--border);border-radius:8px;background:var(--input-bg);color:var(--text);
  font-size:14px;font-family:inherit;outline:none;transition:border .15s
}
textarea{min-height:110px;resize:vertical;line-height:1.55}
textarea:focus,input:focus,select:focus{border-color:var(--accent)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:9px 16px;border-radius:8px;border:1px solid var(--border);
  background:var(--btn-bg);color:var(--text);font-size:13px;font-weight:600;cursor:pointer;transition:all .15s;font-family:inherit}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.primary:hover{background:var(--accent-hover);border-color:var(--accent-hover);color:#fff}
.btn.lg{width:100%;padding:12px;font-size:15px;margin-top:16px}
.btn.sm{padding:4px 10px;font-size:12px;border-radius:6px}
.btn.danger{color:var(--err)}
.btn.danger:hover{border-color:var(--err);background:var(--err-soft)}
.ref-list{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.ref-item{position:relative;width:56px;height:56px;border-radius:8px;overflow:hidden;border:1px solid var(--border)}
.ref-item img{width:100%;height:100%;object-fit:cover}
.ref-item .rm{position:absolute;top:2px;right:2px;width:18px;height:18px;border-radius:50%;background:rgba(0,0,0,.55);color:#fff;border:none;
  font-size:11px;line-height:18px;cursor:pointer;padding:0}
.ref-add{width:56px;height:56px;border-radius:8px;border:1px dashed var(--border);background:var(--input-bg);color:var(--text-muted);cursor:pointer;font-size:20px}
.status{margin-top:12px;padding:10px 12px;border-radius:8px;font-size:13px;display:none}
.status.show{display:block}
.status.info{background:var(--accent-soft);color:var(--accent-strong)}
.status.ok{background:var(--ok-soft);color:var(--ok)}
.status.err{background:var(--err-soft);color:var(--err)}
.result-empty{color:var(--text-muted);text-align:center;padding:60px 10px;font-size:13px}
.result-img-wrap{display:none}
.result-img-wrap img{width:100%;border-radius:10px;border:1px solid var(--border);display:block;background:var(--soft-bg)}
.result-meta{display:flex;align-items:center;gap:10px;margin-top:10px;flex-wrap:wrap}
.result-meta .m{font-size:12px;color:var(--text-muted)}
.hist{margin-top:16px}
.hist-bar{display:flex;align-items:center;gap:6px;margin:0 0 2px}
.hist-bar h2{margin:0;font-size:13px;color:var(--text-2)}
.hist-bar .grow{flex:1}
.hist-list{margin:8px 0 0;padding:0;list-style:none}
.hist-list li{display:flex;gap:10px;align-items:center;padding:7px 6px;border-bottom:1px dashed var(--border);font-size:12px;color:var(--text-2);cursor:pointer;border-radius:8px}
.hist-list li:hover{background:var(--soft-bg)}
.hist-list li.cur{background:var(--accent-soft)}
.hist-list li .hthumb{width:40px;height:40px;border-radius:6px;object-fit:cover;border:1px solid var(--border);flex:none;background:var(--soft-bg)}
.hist-list li .hph{width:40px;height:40px;border-radius:6px;flex:none;display:flex;align-items:center;justify-content:center;background:var(--soft-bg);color:var(--text-muted);font-size:10px}
.hist-list li .hp{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:40px}
.hist-list li .okc{color:var(--ok)}
.hist-list li .errc{color:var(--err)}
.hist-list li .st{flex:none;width:14px;text-align:center}
.hist-list li .chtag{font-size:10px;color:var(--text-muted);border:1px solid var(--border);border-radius:4px;padding:0 4px;flex:none}
.hist-list li .htime{flex:none;color:var(--text-muted);font-size:11px}
.hist-empty{border:none!important;color:var(--text-muted);cursor:default!important}
.hist-empty:hover{background:transparent!important}
dialog{border:none;border-radius:14px;box-shadow:0 24px 64px rgba(28,35,51,.25);padding:0;max-width:860px;width:calc(100% - 32px);background:var(--card);color:var(--text)}
dialog::backdrop{background:var(--backdrop)}
.dlg-head{display:flex;align-items:center;padding:16px 20px;border-bottom:1px solid var(--border);gap:8px}
.dlg-head h3{margin:0;font-size:16px}
.dlg-head .x{margin-left:auto;border:none;background:none;font-size:20px;color:var(--text-muted);cursor:pointer;line-height:1;flex:none}
.dlg-body{padding:16px 20px 20px;max-height:66vh;overflow:auto}
.pool-actions{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.pool-actions .grow{flex:1}
table.pool{width:100%;border-collapse:collapse;font-size:12.5px}
table.pool th{ text-align:left;color:var(--text-muted);font-weight:600;padding:8px 6px;border-bottom:1px solid var(--border);white-space:nowrap}
table.pool td{padding:8px 6px;border-bottom:1px dashed var(--border);vertical-align:middle}
table.pool td.op{white-space:nowrap;text-align:right}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}
.pill.ok{background:var(--ok-soft);color:var(--ok)}
.pill.warn{background:var(--warn-soft);color:var(--warn)}
.pill.err{background:var(--err-soft);color:var(--err)}
.pill.mut{background:var(--pill-mut-bg);color:var(--text-muted)}
.settings-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}
.chk{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-2);margin-top:10px}
.chk input{width:16px;height:16px}
.hint{font-size:12px;color:var(--text-muted);margin:8px 0}
.gift-line{display:flex;align-items:center;gap:8px}
.sub-title{font-size:12px;font-weight:700;color:var(--text-2);margin:16px 0 8px;padding-top:12px;border-top:1px dashed var(--border)}
.sub-title:first-child{border-top:none;margin-top:0;padding-top:0}
.help p{margin:8px 0;color:var(--text-2);font-size:13px}
.help h4{margin:14px 0 4px;font-size:13px}
.toast-wrap{position:fixed;right:16px;bottom:16px;z-index:200;display:flex;flex-direction:column;gap:8px}
.toast{padding:10px 16px;border-radius:8px;color:#fff;font-size:13px;box-shadow:var(--shadow);max-width:340px;word-break:break-all}
.toast.success{background:var(--ok)}
.toast.error{background:var(--err)}
.toast.info{background:#3b4252}
.log-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px}
.log-bar .grow{flex:1}
.log-chk{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-2)}
.log-console{background:#10141f;color:#c9d2e8;border-radius:10px;padding:10px 12px;height:52vh;overflow-y:auto;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'Courier New',monospace;font-size:12px;line-height:1.55}
.log-console .le{padding:1px 0;word-break:break-all;white-space:pre-wrap}
.log-console .le .t{color:#5f6b85}
.log-console .le.i{color:#c9d2e8}
.log-console .le.s{color:#4ade80}
.log-console .le.w{color:#fbbf24}
.log-console .le.e{color:#f87171}
.log-console .le .tag{color:#7c8db5}
.log-console .empty{color:#5f6b85}
.log-console::-webkit-scrollbar{width:8px}
.log-console::-webkit-scrollbar-thumb{background:#2a3350;border-radius:4px}
.about-hero{display:flex;align-items:center;gap:12px;margin:2px 0 12px}
.about-hero svg{width:40px;height:40px;color:var(--accent);flex:none}
.about-hero .t{font-size:17px;font-weight:700}
.about-hero .v{font-size:12px;color:var(--text-muted)}
.docs-body h3{margin:16px 0 6px;font-size:14px;color:var(--accent-strong)}
.docs-body h4{margin:12px 0 4px;font-size:13px}
.docs-body p,.docs-body li{color:var(--text-2);font-size:13px;margin:6px 0}
.docs-body pre{background:var(--soft-bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;font-size:12px;overflow-x:auto}
.docs-body code{background:var(--soft-bg);border-radius:4px;padding:1px 5px;font-size:12px}
.docs-body hr{border:none;border-top:1px solid var(--border);margin:14px 0}
.tl{margin:6px 0;padding-left:2px}
.tl .ti{display:flex;gap:10px;margin:7px 0}
.tl .td{flex:none;width:86px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;color:var(--accent-strong);font-weight:600;padding-top:1px}
.tl .tc{font-size:12.5px;color:var(--text-2)}
/* ---- 移动端合并面板（选项卡） ---- */
.hub-tabs{display:flex;gap:6px;flex:1;min-width:0;overflow-x:auto}
.hub-tab{padding:7px 14px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text-2);font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap;font-family:inherit}
.hub-tab.on{background:var(--accent-soft);color:var(--accent-strong);border-color:var(--accent)}
.hub-panes{padding:16px 16px 18px;max-height:74dvh;overflow:auto}
/* ---- 竖屏 / 窄屏适配 ---- */
@media (max-width:680px){
  .wrap{padding:0 12px 40px}
  header.top{padding:9px 0;gap:8px}
  .brand{gap:7px}
  .brand .logo{width:24px;height:24px}
  .brand h1{font-size:15.5px}
  .brand .ver{font-size:9px}
  .chan-sel{padding:4px 6px;font-size:11px;margin-left:0}
  .top-right{gap:6px}
  .badge{padding:3px 9px;font-size:11px;max-width:96px;overflow:hidden;text-overflow:ellipsis}
  .panel{padding:14px}
  .dlg-body{max-height:70dvh;padding:14px 14px 16px}
  .dlg-head{padding:13px 14px}
  dialog{width:calc(100% - 20px)}
  .log-console{height:48dvh}
  .toast-wrap{left:12px;right:12px;bottom:12px}
  .toast{max-width:100%}
  .hist-list li{flex-wrap:wrap;row-gap:2px}
  .hist-list li .hp{flex-basis:100%;order:5;white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
  .settings-grid{grid-template-columns:1fr}
  .row2{grid-template-columns:1fr 1fr}
  .result-empty{padding:40px 10px}
  .btn.lg{padding:13px;font-size:14.5px}
}
@media (max-width:360px){
  .row2{grid-template-columns:1fr}
  .badge{max-width:72px}
}
</style>
</head>
<body>
<div class="wrap">
  <header class="top">
    <div class="brand">
      <svg class="logo" viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><title>AI生图</title><path d="M14.5 5.5C8.4 5.5 3.5 10.3 3.5 16.3S8.4 27 14.5 27c1.8 0 2.9-1 2.9-2.4 0-.7-.3-1.2-.8-1.8-.4-.5-.7-1-.7-1.6 0-1.3 1-2.2 2.5-2.2h2.9c3 0 5.2-1.9 5.2-4.8 0-5.1-5.4-8.7-12-8.7z"/><path d="M19.8 19.5l6.3-9.9c.7-1.1.4-2.6-.7-3.3-1.1-.7-2.6-.4-3.3.7l-6.3 9.9 1 3.4z"/><circle cx="9.3" cy="12.4" r="1.3"/><circle cx="14.6" cy="10" r="1.3"/><circle cx="8.9" cy="18.7" r="1.3"/></svg>
      <div class="brand-txt">
        <h1>AI生图</h1>
        <span class="ver">kmage-kdr-1.5</span>
      </div>
      <select class="chan-sel" id="channelSelect" title="生成通道（默认 kmage）">
        <option value="kmage" selected>kmage</option>
        <option value="kdr">kdr</option>
      </select>
    </div>
    <div class="top-right">
      <span class="badge" id="creditBadge" title="号池可用总积分">积分 -</span>
      <button class="icon-btn" id="navBtn" type="button" title="设置 / 控制台 / 关于" aria-label="打开设置、控制台或关于"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1 1.55V21a2 2 0 1 1-4 0v-.09a1.7 1.7 0 0 0-1-1.55 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.55-1H3a2 2 0 1 1 0-4h.09a1.7 1.7 0 0 0 1.55-1 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34h.09a1.7 1.7 0 0 0 1-1.55V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87v.09a1.7 1.7 0 0 0 1.55 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.55 1z"/></svg></button>
    </div>
  </header>
  </header>

  <div class="gen-grid">
    <section class="card panel">
      <h2>创作</h2>
      <label class="f" for="prompt">提示词 Prompt</label>
      <textarea id="prompt" placeholder="描述你想要的画面，例如：雨后的未来主义城市街道，霓虹倒影，电影感"></textarea>

      <label class="f" for="model">模型</label>
      <select id="model"></select>

      <div class="row2">
        <div>
          <label class="f" for="ratio">画面比例</label>
          <select id="ratio">
            <option value="1:1" selected>1:1 方形</option>
            <option value="3:2">3:2 横向</option>
            <option value="2:3">2:3 纵向</option>
            <option value="16:9">16:9 宽幅</option>
            <option value="9:16">9:16 竖屏</option>
            <option value="4:3">4:3 横向</option>
            <option value="3:4">3:4 纵向</option>
            <option value="auto">自动</option>
          </select>
        </div>
        <div>
          <label class="f" for="quality">精细度</label>
          <select id="quality">
            <option value="auto" selected>自动</option>
            <option value="low">轻量（快）</option>
            <option value="medium">标准</option>
            <option value="high">精细</option>
          </select>
        </div>
      </div>

      <div id="sizeRowKdr" style="display:none">
        <label class="f" for="kdrSize">分辨率档</label>
        <select id="kdrSize">
          <option value="1K" selected>1K（免费档）</option>
          <option value="2K">2K（需自定义 Key）</option>
          <option value="4K">4K（需自定义 Key）</option>
          <option value="auto">自动</option>
        </select>
      </div>

      <label class="f">参考图（可选，图生图，最多 10 张）</label>
      <div class="ref-list" id="refList">
        <button class="ref-add" id="refAdd" type="button" title="添加参考图">+</button>
      </div>
      <input type="file" id="refInput" accept="image/png,image/jpeg,image/webp" multiple style="display:none">

      <button class="btn primary lg" id="btnGenerate" type="button">开始生成（消耗 1 积分）</button>
      <div class="status" id="genStatus"></div>
    </section>

    <section class="card panel">
      <h2>结果</h2>
      <div class="result-empty" id="resultEmpty">生成结果将显示在这里</div>
      <div class="result-img-wrap" id="resultWrap">
        <img id="resultImg" alt="生成结果">
        <div class="result-meta">
          <button class="btn sm" id="btnDownload" type="button">下载图片</button>
          <span class="m" id="resultMeta"></span>
        </div>
      </div>
      <div class="hist">
        <div class="hist-bar">
          <h2>近期任务</h2>
          <span class="grow"></span>
          <button class="btn sm" id="btnExportHist" type="button" title="导出历史记录 JSON（含预览图与 kdr 上游下载地址，可跨设备回看）">导出</button>
          <button class="btn sm" id="btnImportHist" type="button" title="导入历史记录 JSON（自动合并去重）">导入</button>
          <input type="file" id="importHistFile" accept=".json,application/json" style="display:none">
        </div>
        <ul class="hist-list" id="histList"></ul>
      </div>
    </section>
  </div>
</div>

<!-- ============ 设置 / 控制台 / 关于：三个面板宿主（隐藏）。
     全宽度统一由右上角齿轮按钮打开 hub 浮窗（选项卡切换），面板 DOM 按 tab 搬运复用（v1.4） ============ -->
<div id="host-settings" class="dialog-host">
<div class="dlg-body" id="poolBody">
  <div class="pool-actions">
    <button class="btn" id="btnExportSettings" type="button" title="导出号池 + 全部设置项（含 kdr 自定义 Key）为一份 JSON">导出全部设置</button>
    <button class="btn" id="btnImportPool" type="button" title="从 JSON 导入（自动识别：设置包 / 旧版号池）">导入设置</button>
    <input type="file" id="importPoolFile" accept=".json,application/json" style="display:none">
    <span class="grow"></span>
    <button class="btn" id="btnInstallApp" type="button" style="display:none" title="将本应用安装到操作系统（PWA）">安装到系统</button>
  </div>

  <div class="sub-title">通用选项</div>
  <div class="settings-grid" style="border-top:none;margin-top:0;padding-top:0">
    <div>
      <label class="f" for="themeSel">界面主题</label>
      <select id="themeSel">
        <option value="system" selected>跟随系统（默认）</option>
        <option value="light">浅色</option>
        <option value="dark">深色</option>
      </select>
      <p class="hint" style="margin-top:6px">跟随系统时自动感应设备深色模式变化。</p>
    </div>
    <div>
      <div class="chk"><input type="checkbox" id="notifyChk"><label for="notifyChk">生图结果浏览器通知（成功/失败/超时，双通道生效）</label></div>
      <p class="hint">本应用可安装到操作系统（PWA）；「导出/导入全部设置」可跨设备迁移号池与偏好。</p>
    </div>
  </div>

  <div class="sub-title">kmage 通道选项</div>
  <div class="pool-actions">
    <button class="btn" id="btnRegister" type="button">+ 注册新账号</button>
    <button class="btn" id="btnBatchRegister" type="button">批量注册 ×<span id="batchN">3</span></button>
    <input type="number" id="batchCount" min="1" max="10" value="3" style="width:64px" title="批量注册数量">
    <button class="btn" id="btnCheckinAll" type="button">批量签到</button>
    <button class="btn" id="btnEnsureKeys" type="button">补建 API Key</button>
    <button class="btn" id="btnRefreshCredits" type="button">刷新额度</button>
    <button class="btn" id="btnExportPool" type="button" title="仅导出号池账号列表为 JSON（含会话与 Key）">导出号池</button>
    <span class="grow"></span>
    <button class="btn danger" id="btnArchiveDisabled" type="button">归档已禁用</button>
  </div>
  <div style="overflow-x:auto">
    <table class="pool">
      <thead>
        <tr>
          <th>账号</th><th>积分</th><th>API Key</th><th>今日签到</th><th>状态</th><th style="text-align:right">操作</th>
        </tr>
      </thead>
      <tbody id="poolTbody">
        <tr><td colspan="6" style="color:var(--text-muted)">号池为空，点击"注册新账号"开始。</td></tr>
      </tbody>
    </table>
  </div>
  <div class="settings-grid">
    <div>
      <label class="f" for="rotationStrategy">轮换策略</label>
      <select id="rotationStrategy">
        <option value="most-credits" selected>积分优先（most-credits）</option>
        <option value="round-robin">轮询均衡（round-robin）</option>
      </select>
    </div>
    <div>
      <label class="f" for="emailDomain">注册邮箱域名</label>
      <input type="text" id="emailDomain" placeholder="gmail.com" maxlength="64">
    </div>
    <div>
      <div class="chk"><input type="checkbox" id="autoRegisterChk" checked><label for="autoRegisterChk">生图无号可用时自动注册新号（+1 分）</label></div>
    </div>
    <div>
      <div class="chk"><input type="checkbox" id="autoCheckinChk" checked><label for="autoCheckinChk">打开页面时自动为可签账号签到（+5 分/天）</label></div>
    </div>
  </div>

  <div class="sub-title">kdr 通道选项</div>
  <div class="settings-grid" style="border-top:none;margin-top:0;padding-top:0">
    <div>
      <label class="f">共享 Gift Key（免费，自动获取轮换）</label>
      <div class="gift-line">
        <span class="pill ok" id="giftKeyAlias">未获取</span>
        <button class="btn sm" id="btnRefreshGift" type="button">刷新</button>
      </div>
    </div>
    <div>
      <label class="f" for="kdrCustomKeys">自定义 API Key（可选，付费按量，每行一个）</label>
      <textarea id="kdrCustomKeys" style="min-height:74px" placeholder="填入后自动优先于共享 Key 使用，可解锁全部模型与 2K/4K 分辨率"></textarea>
    </div>
  </div>
  <p class="hint">分区说明：各通道选项常驻可调——当前选中 kmage 时也可直接配置 kdr（反之亦然），配置仅对对应通道生效。kdr 免费共享 Key 仅支持基础模型与 1K；生图为任务制（约 10~60 秒出图）。自定义 Key 填写后自动优先，可解锁全部模型与更高分辨率。</p>

  <div class="status" id="poolStatus"></div>
</div>
</div>

<div id="host-console" class="dialog-host">
<div class="dlg-body" id="logBody">
  <div class="log-bar">
    <button class="btn sm" id="btnExportLogAll" type="button">导出全部日志</button>
    <button class="btn sm" id="btnExportLogRun" type="button" title="只导出最近一次生图运行">导出本次运行</button>
    <button class="btn sm" id="btnCopyLog" type="button">复制</button>
    <span class="grow"></span>
    <label class="log-chk"><input type="checkbox" id="logErrOnly">只看错误</label>
    <button class="btn sm danger" id="btnClearLog" type="button">清空</button>
  </div>
  <div style="font-size:11px;color:var(--text-muted);margin:-4px 0 8px" id="logCount"></div>
  <div class="log-console" id="logBox"><div class="empty">暂无日志。日志会记录每次生图与设置操作：请求、状态码、耗时与上游响应摘要，刷新页面不丢失。</div></div>
</div>
</div>

<div id="host-about" class="dialog-host">
<div class="dlg-body docs-body" id="docsHost"><div id="docsBody"></div></div>
</div>

<!-- ============ hub 浮窗：右上角单齿轮按钮打开，选项卡切换；面板内容自上方宿主按需搬运（无重复 ID） ============ -->
<dialog id="hubDialog">
  <div class="dlg-head">
    <div class="hub-tabs" id="hubTabs">
      <button class="hub-tab" data-hub="settings" type="button">设置</button>
      <button class="hub-tab" data-hub="console" type="button">控制台</button>
      <button class="hub-tab" data-hub="about" type="button">关于</button>
    </div>
    <button class="x" id="hubClose" type="button" title="关闭">×</button>
  </div>
  <div class="hub-panes">
    <div class="hub-pane" id="hubPane-settings"></div>
    <div class="hub-pane" id="hubPane-console" style="display:none"></div>
    <div class="hub-pane" id="hubPane-about" style="display:none"></div>
  </div>
</dialog>


<div class="toast-wrap" id="toastWrap"></div>
<script>
// ================= AI生图 前端（kmage + kdr 双通道） =================
var VERSION='kmage-kdr-1.5';
var STATE_KEY='kmage_state_v1';
var LOG_KEY='kmage_logs_v1';
var CHAN_KEY='kmage_channel_v1';
var KDR_KEY='kdr_state_v1';
var KDR_LEGACY_KEY='maliang_state'; // 旧 kdr 前端存储（迁移自定义 Key 用）
var FORM_KEY='kmage_form_v1'; // 创作面板选项记忆（v1.4: 模型按通道分存/比例/精细度/分辨率档/提示词）
var formState={prompt:'',ratio:'',quality:'',kdrSize:'',model:{kmage:'',kdr:''}};
var installPromptEvent=null; // PWA beforeinstallprompt 暂存
// ---------- v1.5 直连优先（Direct-First）----------
// 2026-09-23 起: kdr 上游将 Cloudflare Worker 出口 IP 段列入免费 Key 黑名单
//（「此 IP 已被加入免费 Key 黑名单」），kmage 上游将生图环境风控扩大到所有
// 数据中心出口 IP（「账号使用环境异常，充值后解锁」）——经 Worker 代理的
// 生图请求全部被拒。修复: 生图类请求改由访客浏览器直连上游（住宅 IP、
// 真实 UA，即上游期望的正常使用环境），Worker 代理降级为网络失败时的
// 自动回退。会话类操作（Cookie 会话，无法跨域携带）仍走 Worker 代理。
// 脱敏原则不变: 上游真实地址不写入本页静态文本，运行时经 GET /about 获取。
var directBases={kmage:'',kdr:''};
function stripTailSlash(s){var b=String(s||'');while(b.charAt(b.length-1)==='/'){b=b.slice(0,-1)}return b}
async function initDirect(){
  try{
    var t0=Date.now();
    var resp=await fetch('/about',{credentials:'omit'});
    var data=null;
    try{data=await resp.json()}catch(e){}
    if(data&&data.channels&&data.channels.kmage&&data.channels.kmage.upstream&&data.channels.kmage.upstream.base){
      directBases.kmage=stripTailSlash(data.channels.kmage.upstream.base);
    }
    if(data&&data.channels&&data.channels.kdr&&data.channels.kdr.upstream&&data.channels.kdr.upstream.base){
      directBases.kdr=stripTailSlash(data.channels.kdr.upstream.base);
    }
    if(directBases.kmage||directBases.kdr){
      appLog('[core] 直连模式就绪: kmage '+(directBases.kmage?'✓':'✕')+' / kdr '+(directBases.kdr?'✓':'✕')+'（自 /about 获取，'+(Date.now()-t0)+'ms）','i');
    }else{
      appLog('[core] 直连模式不可用（/about 未提供上游地址），生图将全部走 Worker 代理','w');
    }
  }catch(e){appLog('[core] 直连模式初始化失败（'+(e.message||e)+'），生图将全部走 Worker 代理','w')}
}
var DEFAULT_SETTINGS={rotationStrategy:'most-credits',autoRegister:true,autoCheckin:true,emailDomain:'gmail.com',notificationsEnabled:false,theme:'system'};
var state={accounts:[],abandoned:[],settings:{},rotationIndex:0};
var kdrState={customKeys:[],gift:{key:'',alias:'',ts:0}};
var channel='kmage';        // 当前通道: kmage（默认）| kdr
var runLogs=[];              // 日志环形缓冲 {ts,run,lvl,msg,detail}
var currentRunId='';         // 最近一次生图运行 id（用于“导出本次运行”）
var refImages=[];            // data URL 数组（图生图，双通道共用）
var lastResultB64=null;      // 当前结果 base64
var histItems=[];            // 任务历史（成功/失败/中断均入册；成功条目含缩略图与 kdr 上游地址）
var HIST_KEY='kmage_hist_v1';  // 历史持久化键
var HIST_MAX=40;               // 历史条数上限（含缩略图，控制在 localStorage 安全容量内）
var curHistView=null;          // 当前回看的历史条目下标（null=非回看态）
var generating=false;

// ---------- 基础工具 ----------
function $(id){return document.getElementById(id)}
function randStr(n,alphabet){
  var abc=alphabet||'abcdefghijklmnopqrstuvwxyz0123456789';var s='';
  for(var i=0;i<n;i++){s+=abc.charAt(Math.floor(Math.random()*abc.length))}
  return s;
}
// 拟人化邮箱池（马良原则 v27.2）：姓名词库 × 6 种模式 × 随机大小写，
// 避免固定前缀/时间戳等机器指纹
var EMAIL_FIRST=['emily','sarah','michael','david','jessica','james','ashley','chris','amanda','daniel','stephanie','joshua','nicole','andrew','samantha','ryan','lauren','justin','rachel','brandon','megan','tyler','katherine','kevin','elizabeth','brian','jennifer','jason','michelle','patrick','kimberly','travis','heather','nathan','courtney','maria','alex','lisa','robert','john'];
var EMAIL_LAST=['chen','wang','li','zhang','smith','johnson','lee','brown','garcia','martinez','wilson','taylor','thomas','moore','jackson','white','harris','clark','lewis','robinson','walker','young','allen','king','wright','scott','hill','green','adams','baker'];
var EMAIL_ADJ=['happy','lucky','cool','sunny','swift','calm','bold','bright','dreamy','fresh','kind','wild','pure','warm','zen','chill','neon','cosmic','pixel','sage'];
var EMAIL_NOUN=['cat','fox','moon','star','sky','bear','wolf','deer','fish','hawk','tree','lake','rain','wave','wind','seed','leaf','snow','dawn','ray'];
function genEmail(){
  var dom=(state.settings.emailDomain||'gmail.com').replace(/^@/,'');
  var fn=EMAIL_FIRST[Math.floor(Math.random()*EMAIL_FIRST.length)];
  var ln=EMAIL_LAST[Math.floor(Math.random()*EMAIL_LAST.length)];
  var adj=EMAIL_ADJ[Math.floor(Math.random()*EMAIL_ADJ.length)];
  var noun=EMAIL_NOUN[Math.floor(Math.random()*EMAIL_NOUN.length)];
  var r2=Math.floor(10+Math.random()*90),r3=Math.floor(100+Math.random()*900),r4=Math.floor(1000+Math.random()*9000);
  var cap=function(x){return x.charAt(0).toUpperCase()+x.slice(1)};
  var sc=function(x){return Math.random()>0.5?cap(x):x};
  var local='';
  switch(Math.floor(Math.random()*6)){
    case 0: local=sc(fn)+'.'+sc(ln)+r2; break;
    case 1: local=sc(fn)+sc(ln)+r3; break;
    case 2: local=adj+'.'+noun+r4; break;
    case 3: local=sc(fn)+'_'+noun+r2; break;
    case 4: local=sc(fn)+r3; break;
    default: local=adj+sc(ln)+r3;
  }
  return local.toLowerCase()+'@'+dom;
}
// 强随机密码：无固定后缀/固定结构
function genPassword(){
  var up='ABCDEFGHJKLMNPQRSTUVWXYZ',low='abcdefghijkmnpqrstuvwxyz',dg='23456789',sy='#%!@+';
  var all=up+low+dg+sy;
  var len=12+Math.floor(Math.random()*4); // 12~15
  var p=randStr(1,up)+randStr(1,low)+randStr(1,dg)+randStr(1,sy)+randStr(len-4,all);
  var arr=p.split('');for(var i=arr.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=arr[i];arr[i]=arr[j];arr[j]=t}
  return arr.join('');
}
// API Key 备注名：小词池随机组合，避免固定前缀规律
var KEY_NAME_WORDS=['pool','img','draw','art','gen','lab','studio','pic'];
function genKeyName(){return KEY_NAME_WORDS[Math.floor(Math.random()*KEY_NAME_WORDS.length)]+'-'+randStr(4)}
function maskEmail(e){if(!e)return '-';var i=e.indexOf('@');if(i<=1)return e;return e.charAt(0)+'***'+e.slice(i)}
function fmtTime(ts){var d=new Date(ts);return d.getHours().toString().padStart(2,'0')+':'+d.getMinutes().toString().padStart(2,'0')}
function todayGmt8(){
  var d=new Date(Date.now()+8*3600*1000);
  return d.getUTCFullYear()+'-'+('0'+(d.getUTCMonth()+1)).slice(-2)+'-'+('0'+d.getUTCDate()).slice(-2);
}
function toast(msg,type,ms){
  var w=$('toastWrap');var el=document.createElement('div');
  el.className='toast '+(type||'info');el.textContent=msg;w.appendChild(el);
  setTimeout(function(){el.style.opacity='0';el.style.transition='opacity .4s';setTimeout(function(){el.remove()},420)},ms||3200);
}
function setStatus(elId,msg,cls){
  var el=$(elId);if(!msg){el.className='status';el.textContent='';return}
  el.className='status show '+(cls||'info');el.textContent=msg;
}
function saveState(){try{localStorage.setItem(STATE_KEY,JSON.stringify(state))}catch(e){toast('本地存储失败：'+e.message,'error')}}
function loadState(){
  try{
    var raw=localStorage.getItem(STATE_KEY);
    if(raw){var d=JSON.parse(raw);state.accounts=d.accounts||[];state.abandoned=d.abandoned||[];state.rotationIndex=d.rotationIndex||0;
      state.settings=Object.assign({},DEFAULT_SETTINGS,d.settings||{})}
    else{state.settings=Object.assign({},DEFAULT_SETTINGS)}
  }catch(e){state.settings=Object.assign({},DEFAULT_SETTINGS)}
}
// ---------- kdr 通道本地状态 ----------
function saveKdrState(){try{localStorage.setItem(KDR_KEY,JSON.stringify(kdrState))}catch(e){}}
function loadKdrState(){
  try{
    var raw=localStorage.getItem(KDR_KEY);
    if(raw){var d=JSON.parse(raw);kdrState.customKeys=(d.customKeys||[]).filter(function(x){return x&&typeof x==='string'});
      kdrState.gift={key:d.gift&&d.gift.key||'',alias:d.gift&&d.gift.alias||'',ts:d.gift&&d.gift.ts||0}}
  }catch(e){kdrState={customKeys:[],gift:{key:'',alias:'',ts:0}}}
}
// 旧版 kdr 前端（存储键 maliang_state）的自定义 Key 一次性迁移
function migrateLegacyKdrKeys(){
  try{
    if(kdrState.customKeys.length)return;
    var raw=localStorage.getItem(KDR_LEGACY_KEY);
    if(!raw)return;
    var d=JSON.parse(raw);
    var keys=(d&&d.settings&&d.settings.customApiKeys)||[];
    if(Array.isArray(keys)&&keys.length){
      kdrState.customKeys=keys.filter(function(x){return x&&typeof x==='string'});
      saveKdrState();
      appLog('已从旧版 kdr 存储迁移 '+kdrState.customKeys.length+' 个自定义 Key','s');
    }
  }catch(e){}
}
// ---------- 创作面板选项记忆（v1.4）----------
// localStorage 记住左侧创作面板：模型（按通道分存）/比例/精细度/分辨率档/提示词
function saveFormState(){
  try{
    formState.prompt=String($('prompt').value||'').slice(0,4000);
    formState.ratio=$('ratio').value;
    formState.quality=$('quality').value;
    if($('kdrSize'))formState.kdrSize=$('kdrSize').value;
    if($('model')&&$('model').selectedIndex>=0)formState.model[channel]=$('model').value;
    localStorage.setItem(FORM_KEY,JSON.stringify(formState));
  }catch(e){}
}
function restoreFormState(){
  try{
    var raw=localStorage.getItem(FORM_KEY);
    if(raw){
      var d=JSON.parse(raw);
      formState.prompt=String(d.prompt||'').slice(0,4000);
      formState.ratio=d.ratio||'';
      formState.quality=d.quality||'';
      formState.kdrSize=d.kdrSize||'';
      formState.model=Object.assign({kmage:'',kdr:''},d.model||{});
    }
  }catch(e){}
  try{
    if(formState.prompt)$('prompt').value=formState.prompt;
    pickOption('ratio',formState.ratio);
    pickOption('quality',formState.quality);
    pickOption('kdrSize',formState.kdrSize);
  }catch(e){}
}
function pickOption(id,val){
  var el=$(id);if(!el||!val)return;
  for(var i=0;i<el.options.length;i++){if(el.options[i].value===val){el.selectedIndex=i;break}}
}
var formSaveTimer=null;
function saveFormStateDebounced(){
  if(formSaveTimer)clearTimeout(formSaveTimer);
  formSaveTimer=setTimeout(function(){formSaveTimer=null;saveFormState()},400);
}
// ---------- PWA 安装（v1.4）----------
function bindInstall(){
  var b=$('btnInstallApp');
  window.addEventListener('beforeinstallprompt',function(e){
    e.preventDefault();
    installPromptEvent=e;
    if(b)b.style.display='';
    appLog('PWA: 浏览器已就绪可安装（beforeinstallprompt）','i');
  });
  if(b)b.addEventListener('click',function(){
    if(!installPromptEvent)return;
    installPromptEvent.prompt();
    installPromptEvent.userChoice.then(function(c){
      appLog('PWA: 安装结果 '+(c&&c.outcome),'i');
      if(c&&c.outcome==='accepted')toast('「AI生图」安装已开始','success');
      installPromptEvent=null;
      b.style.display='none';
    }).catch(function(){});
  });
  window.addEventListener('appinstalled',function(){
    toast('「AI生图」已安装到系统','success');
    appLog('PWA: appinstalled','s');
    var x=$('btnInstallApp');if(x)x.style.display='none';
  });
}
// ---------- 主题（v1.3：跟随系统/浅色/深色） ----------
function applyTheme(){
  var t=state.settings.theme||'system';
  if(t!=='dark'&&t!=='light')t='system';
  document.documentElement.setAttribute('data-theme',t);
}
function bindThemeMedia(){ // system 模式下实时跟随系统深浅切换
  try{
    var mq=window.matchMedia('(prefers-color-scheme: dark)');
    var fn=function(){if((state.settings.theme||'system')==='system')applyTheme()};
    if(mq.addEventListener)mq.addEventListener('change',fn);else if(mq.addListener)mq.addListener(fn);
  }catch(e){}
}
// ---------- 通道管理 ----------
function loadChannel(){
  try{var c=localStorage.getItem(CHAN_KEY);if(c==='kdr'||c==='kmage')channel=c}catch(e){}
}
function saveChannel(){try{localStorage.setItem(CHAN_KEY,channel)}catch(e){}}
// 通道模型清单（label 展示 + 值为上游模型名）
var KMODELS_KMAGE=[
  {v:'gpt-image-2',l:'GPT Image 2（兼容旧版）'},
  {v:'gpt-image-2.5-flare',l:'GPT Image 2.5 · Flare（速度优先）'},
  {v:'gpt-image-2.5-sunburst',l:'GPT Image 2.5 · Sunburst（效果优先）'}
];
var KMODELS_KDR=[
  {v:'gpt-image-2',l:'GPT Image 2（免费档可用）'},
  {v:'gpt-image-2.5-flare',l:'GPT Image 2.5 · Flare（需自定义 Key）'},
  {v:'gpt-image-2.5-sunburst',l:'GPT Image 2.5 · Sunburst（需自定义 Key）'},
  {v:'gpt-image-2-4km',l:'GPT Image 2 · 4K（需自定义 Key）'},
  {v:'banana2-4k',l:'Banana2 · 4K（需自定义 Key）'},
  {v:'bananapro-4k',l:'Banana Pro · 4K（需自定义 Key）'}
];
var KDR_FREE_MODEL='gpt-image-2';
var KDR_FREE_HOST='www.97api.com';      // 免费 Key 固定线路（kdr 站点默认线路）
var KDR_PAID_HOST='www.97api.com';      // 自定义 Key 线路（同站点双线路，默认主线路）
var KDR_GIFT_FALLBACK='Gift-Key-dont-spam-thanks';
function fillModelOptions(){
  var sel=$('model');var list=(channel==='kdr')?KMODELS_KDR:KMODELS_KMAGE;
  var html='';
  for(var i=0;i<list.length;i++){html+='<option value="'+list[i].v+'">'+list[i].l+'</option>'}
  sel.innerHTML=html;
  // v1.4: 模型按通道记忆——有保存值且在当前通道列表内则恢复，否则用默认
  var saved=(formState.model||{})[channel];
  var found=-1;
  for(var j=0;j<list.length;j++){if(list[j].v===saved){found=j;break}}
  sel.selectedIndex=found>=0?found:(channel==='kdr'?0:2);
}
// kdr 生效参数：自定义 Key → 全模型 + 任意分辨率；免费 Gift Key → 固定基础模型 + 1K
function kdrEffective(){
  var custom=kdrState.customKeys.length?kdrState.customKeys[0]:'';
  if(custom){
    return {key:custom,isCustom:true,host:KDR_PAID_HOST,model:$('model').value||KMODELS_KDR[0].v,size:($('kdrSize')&&$('kdrSize').value)||'1K',sizeLocked:false};
  }
  return {key:(kdrState.gift.key||KDR_GIFT_FALLBACK),isCustom:false,host:KDR_FREE_HOST,model:KDR_FREE_MODEL,size:'1K',sizeLocked:true};
}
function applyChannel(){
  $('channelSelect').value=channel;
  $('sizeRowKdr').style.display=(channel==='kdr')?'block':'none';
  $('btnGenerate').textContent=(channel==='kdr')?'开始生成（kdr · 免费）':'开始生成（消耗 1 积分）';
  fillModelOptions();
  renderBadge();
  if($('hubDialog').open){renderGiftLine();renderPool()}
}
function switchChannel(c){
  if(c===channel||generating){$('channelSelect').value=channel;return}
  channel=c;saveChannel();applyChannel();
  appLog('切换通道 → '+c,'i');
  toast('已切换到 '+c+' 通道','success');
  if(c==='kdr'){ensureGiftKey(true).then(renderGiftLine).catch(function(){})}
}

// ---------- 运行日志系统 ----------
// 结构: {ts, run, lvl(i/s/w/e), msg, detail}；持久化最近 300 条（detail 截断），内存 800 条
function loadLogs(){
  try{
    var raw=localStorage.getItem(LOG_KEY);
    if(raw){var d=JSON.parse(raw);if(Array.isArray(d))runLogs=d}
  }catch(e){runLogs=[]}
}
// ---------- 任务历史（v1.3）----------
// 成功/失败均入册：成功条目存 canvas 缩略图（kmage 上游仅回 b64，无持久下载地址）
// 与 kdr 上游结果 URL（可跨设备在线回看原图）；失败条目存错误摘要。
function saveHist(){
  try{localStorage.setItem(HIST_KEY,JSON.stringify(histItems.slice(0,HIST_MAX)))}
  catch(e){ // 容量兜底：剥缩略图再存一次
    try{
      var slim=histItems.slice(0,HIST_MAX).map(function(h){var c=Object.assign({},h);delete c.thumb;return c});
      localStorage.setItem(HIST_KEY,JSON.stringify(slim));
    }catch(e2){}
  }
}
function loadHist(){
  try{var raw=localStorage.getItem(HIST_KEY);if(raw){var d=JSON.parse(raw);if(Array.isArray(d))histItems=d}}catch(e){}
  var fixed=0;
  for(var i=0;i<histItems.length;i++){
    if(histItems[i].status==='running'){histItems[i].status='error';histItems[i].error='页面刷新/关闭导致中断';fixed++}
  }
  if(fixed)saveHist();
}
// 结果 b64 -> 本地缩略图（长边 160px JPEG q0.65，约 4~10KB/条）
function makeThumb(b64,cb){
  try{
    var img=new Image();
    img.onload=function(){
      try{
        var M=160,w=img.width||M,h=img.height||M;
        var sc=Math.min(1,M/Math.max(w,h));
        var cw=Math.max(1,Math.round(w*sc)),ch=Math.max(1,Math.round(h*sc));
        var c=document.createElement('canvas');c.width=cw;c.height=ch;
        c.getContext('2d').drawImage(img,0,0,cw,ch);
        var du='';try{du=c.toDataURL('image/jpeg',0.65)}catch(e2){}
        cb(du);
      }catch(e){cb('')}
    };
    img.onerror=function(){cb('')};
    img.src='data:image/png;base64,'+b64;
  }catch(e){cb('')}
}
// 回看历史条目：kdr 有上游 URL 在线加载；kmage 仅本地缩略图（当次会话内可用原图）
function histReplay(i){
  var h=histItems[i];if(!h)return;
  curHistView=i;
  if(h.status!=='ok'){
    setStatus('genStatus','任务 '+h.run+' 未成功（'+new Date(h.ts).toLocaleString()+'，'+(h.channel||'kmage')+' 通道）: '+(h.error||'未知错误'),'err');
    appLog('历史回看 #'+i+'（'+h.run+'）: 失败任务，原因: '+(h.error||'未知'),'i');
    renderHist();return;
  }
  var src='',note='';
  if(h.run===currentRunId&&lastResultB64){src='data:image/png;base64,'+lastResultB64;note='原图（本次会话内存）'}
  else if(h.url){src=h.url;note='在线回看（kdr 上游存储地址）'}
  else if(h.thumb){src=h.thumb;note='预览缩略图（kmage 上游仅返回图片数据，无持久下载地址）'}
  if(!src){toast('该条目缺少可展示的图像数据','info');return}
  $('resultEmpty').style.display='none';
  $('resultWrap').style.display='block';
  $('resultImg').src=src;
  $('resultMeta').textContent='历史回看 · '+new Date(h.ts).toLocaleString()+' · '+(h.model||'')+' · '+note;
  $('btnDownload').disabled=!(h.url)&&!(h.run===currentRunId&&lastResultB64);
  appLog('历史回看 #'+i+'（'+h.run+'，'+(h.channel||'kmage')+'，'+note+'）','i');
  renderHist();
}
// 历史导出：全部条目（含 thumb/url），跨设备导入后 kdr 条目仍可在线回看上游原图
function exportHist(){
  var data={type:'ai-image-history',version:VERSION,exportedAt:new Date().toISOString(),items:histItems.slice(0,HIST_MAX)};
  var name='ai-image-history-'+new Date().toISOString().slice(0,10).replace(/-/g,'')+'.json';
  var blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;
  document.body.appendChild(a);a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},800);
  appLog('导出历史记录: '+name+'（'+data.items.length+' 条，含预览图与 kdr 上游地址）','s');
  toast('已导出 '+data.items.length+' 条历史记录','success');
}
async function importHistData(txt){
  var data;
  try{data=JSON.parse(txt)}catch(e){toast('JSON 解析失败: '+e.message,'error');return}
  var arr=Array.isArray(data)?data:((data&&data.type==='ai-image-history'&&Array.isArray(data.items))?data.items:(data&&Array.isArray(data.items)?data.items:null));
  if(!arr){toast('未识别的历史记录格式（需要 ai-image-history JSON）','error');return}
  var add=0,skip=0;
  for(var i=0;i<arr.length;i++){
    var it=arr[i];
    if(!it||!it.ts||!it.run){skip++;continue}
    var dup=false;
    for(var j=0;j<histItems.length;j++){if(histItems[j].run===it.run){dup=true;break}}
    if(dup){skip++;continue}
    histItems.push({ts:it.ts,run:it.run,channel:it.channel||'kmage',prompt:String(it.prompt||'').slice(0,120),model:it.model||'',
      size:it.size||'',quality:it.quality||'',account:it.account||'',status:it.status==='ok'?'ok':'error',
      error:String(it.error||'').slice(0,200),ms:it.ms||0,thumb:it.thumb||'',url:it.url||''});
    add++;
  }
  histItems.sort(function(a,b){return b.ts-a.ts});
  histItems=histItems.slice(0,HIST_MAX);
  saveHist();renderHist();
  var msg='导入历史 '+add+' 条'+(skip?('，跳过 '+skip+'（重复/无效）'):'');
  toast(msg,add?'success':'info');
  appLog('导入历史记录: '+msg,'s');
}
function saveLogs(){
  try{
    var keep=runLogs.slice(-300).map(function(x){
      return {ts:x.ts,run:x.run,lvl:x.lvl,msg:String(x.msg).slice(0,300),detail:x.detail?String(x.detail).slice(0,300):''};
    });
    localStorage.setItem(LOG_KEY,JSON.stringify(keep));
  }catch(e){}
}
var LOG_LEVEL_NAME={i:'INFO',s:'OK  ',w:'WARN',e:'ERR '};
function appLog(msg,lvl,detail,run){
  var entry={ts:Date.now(),run:run||currentRunId||'-',lvl:lvl||'i',msg:String(msg),detail:detail?String(detail):''};
  runLogs.push(entry);
  if(runLogs.length>800)runLogs=runLogs.slice(-800);
  if($('hubDialog').open)renderLogBox();
  if(runLogs.length%8===0)saveLogs();
  return entry;
}
function fmtLogTs(ts){
  var d=new Date(ts);
  return ('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2)+':'+('0'+d.getSeconds()).slice(-2)+'.'+('00'+(d.getMilliseconds()%1000)).slice(-3);
}
function renderLogBox(){
  var box=$('logBox');
  var errOnly=$('logErrOnly').checked;
  var rows=[];
  for(var i=0;i<runLogs.length;i++){
    var x=runLogs[i];
    if(errOnly&&x.lvl!=='e')continue;
    rows.push(x);
  }
  $('logCount').textContent='（共 '+runLogs.length+' 条'+(errOnly?('，错误 '+rows.length+' 条'):'')+'）';
  if(!rows.length){box.innerHTML='<div class="empty">暂无日志。</div>';return}
  var html='';
  var lastRun=null;
  for(var j=0;j<rows.length;j++){
    var y=rows[j];
    if(y.run!==lastRun&&y.run&&y.run!=='-'){html+='<div class="le" style="color:#5f6b85">---- '+esc(y.run)+' ----</div>';lastRun=y.run}
    html+='<div class="le '+y.lvl+'"><span class="t">'+fmtLogTs(y.ts)+'</span> <span class="tag">['+esc(y.run)+']</span> '+esc(y.msg)
      +(y.detail?('<span class="t"> | '+esc(y.detail)+'</span>'):'')+'</div>';
  }
  box.innerHTML=html;
  box.scrollTop=box.scrollHeight;
}
function logsToText(rows,label){
  var head=[];
  head.push('AI生图 运行日志'+(label?('（'+label+'）'):''));
  head.push('导出时间: '+new Date().toLocaleString());
  head.push('版本: '+VERSION);
  head.push('通道: '+channel);
  head.push('页面: '+location.href);
  head.push('UA: '+navigator.userAgent);
  head.push('条数: '+rows.length);
  head.push('');
  var lines=rows.map(function(x){
    return '['+fmtLogTs(x.ts)+'] ['+(LOG_LEVEL_NAME[x.lvl]||'INFO')+'] ['+x.run+'] '+x.msg+(x.detail?(' || '+x.detail):'');
  });
  return head.concat(lines).join(String.fromCharCode(10));
}
function downloadText(filename,text){
  var blob=new Blob([text],{type:'text/plain;charset=utf-8'});
  var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=filename;
  document.body.appendChild(a);a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},800);
}
function exportLogs(mode){
  var errOnly=$('logErrOnly').checked;
  var rows=[];
  if(mode==='run'){
    for(var i=0;i<runLogs.length;i++){if(runLogs[i].run===currentRunId)rows.push(runLogs[i])}
    if(!rows.length){toast('本次运行暂无日志','info');return}
  }else{
    for(var j=0;j<runLogs.length;j++){if(!errOnly||runLogs[j].lvl==='e')rows.push(runLogs[j])}
    if(!rows.length){toast('暂无可导出的日志','info');return}
  }
  var name='ai-image-log-'+(mode==='run'?'run-':'')+(new Date().toISOString().slice(0,19).replace(/[:T-]/g,''))+'.txt';
  downloadText(name,logsToText(rows,mode==='run'?'本次运行 '+(currentRunId||'-'):'全部'));
  appLog('导出日志: '+name,'s','','');
}
function copyLogsAll(){
  var errOnly=$('logErrOnly').checked;
  var rows=[];
  for(var i=0;i<runLogs.length;i++){if(!errOnly||runLogs[i].lvl==='e')rows.push(runLogs[i])}
  if(!rows.length){toast('暂无可复制的日志','info');return}
  var text=logsToText(rows,'全部');
  (navigator.clipboard&&navigator.clipboard.writeText?navigator.clipboard.writeText(text):Promise.reject()).then(function(){
    toast('已复制 '+rows.length+' 条日志','success');
  },function(){
    var ta=document.createElement('textarea');ta.value=text;document.body.appendChild(ta);ta.select();
    try{document.execCommand('copy');toast('已复制 '+rows.length+' 条日志','success')}catch(e){toast('复制失败，请用导出','error')}
    ta.remove();
  });
}

// ---------- 浏览器原生通知 ----------
function notificationsSupported(){return typeof Notification!=='undefined'}
function notificationsActive(){
  return !!(state.settings.notificationsEnabled&&notificationsSupported()&&Notification.permission==='granted');
}
async function requestNotificationPermission(){
  if(!notificationsSupported()){toast('当前浏览器不支持通知','error');return false}
  if(Notification.permission==='granted')return true;
  if(Notification.permission==='denied'){toast('通知权限已被浏览器拒绝，请在浏览器地址栏权限图标中手动开启','error');return false}
  var result=await Notification.requestPermission();
  if(result==='granted'){toast('通知权限已开启','success');return true}
  toast('未授予通知权限，生图结果将只在页面内提示','info');
  return false;
}
function notifyUser(title,body,tag){
  try{
    if(!notificationsActive())return;
    var n=new Notification(title,{body:body,tag:tag||('aigc-'+Date.now()),renotify:true});
    n.onclick=function(){window.focus();n.close()};
    setTimeout(function(){try{n.close()}catch(e){}},9000);
  }catch(e){appLog('通知发送失败: '+e.message,'w')}
}

// ---------- kmage 通道 API 封装 ----------
// 会话类：/api/kmage/*（携带账号会话令牌；自动接收会话轮换）
function captureSession(resp,account){
  var ns=resp.headers.get('X-Kmage-Set-Session');
  if(ns&&account){account.session=ns}
}
async function kmageApi(path,opts,account){
  opts=opts||{};
  var headers=Object.assign({'Content-Type':'application/json'},opts.headers||{});
  if(account&&account.session)headers['X-Kmage-Session']=account.session;
  var t0=Date.now();
  var resp=await fetch('/api/kmage'+path,{method:opts.method||'GET',headers:headers,body:opts.body||undefined,credentials:'omit'});
  captureSession(resp,account);
  // body 只能读一次：先取全文再尝试 JSON 解析，非 JSON 时保留原文供日志
  var data=null,rawTxt='';
  try{
    rawTxt=await resp.text();
    try{data=JSON.parse(rawTxt)}catch(e){data={_raw:rawTxt.slice(0,240)}}
  }catch(e){data={_raw:'(读取响应失败: '+e.message+')'}}
  var dur=Date.now()-t0;
  var owner=account?('['+maskEmail(account.email)+'] '):'';
  appLog('[kmage] '+owner+(opts.method||'GET')+' /api'+path+' → HTTP '+resp.status+' ('+dur+'ms)',
    resp.ok?'i':(resp.status>=500?'e':'w'),
    (!resp.ok)?((rawTxt?('非JSON响应: '+rawTxt):JSON.stringify(data).slice(0,240))):'');
  return {ok:resp.ok,status:resp.status,data:data};
}
// v1 类：kmage 生图 Bearer 请求（v1.5 直连优先：浏览器直连上游，网络失败自动回退 Worker 代理）
async function kmageV1(path,opts,apiKey){
  opts=opts||{};
  var base=directBases.kmage;
  if(base){
    try{
      return await kmageV1Via(base+'/v1'+path,opts,apiKey,'直连','/v1'+path);
    }catch(e){
      if(e&&e.name==='AbortError'){throw e}
      appLog('[kmage] 直连上游失败（'+(e.message||e)+'），自动回退 Worker 代理','w');
    }
  }
  return await kmageV1Via('/kmage/v1'+path,opts,apiKey,'代理','/v1'+path);
}
async function kmageV1Via(url,opts,apiKey,modeLabel,dispPath){
  opts=opts||{};
  var headers=Object.assign({'Content-Type':'application/json'},opts.headers||{});
  if(apiKey)headers['Authorization']='Bearer '+apiKey;
  var fo={method:opts.method||'GET',headers:headers,credentials:'omit'};
  if(opts.body)fo.body=opts.body;
  if(opts.signal)fo.signal=opts.signal;
  var t0=Date.now();
  var resp=await fetch(url,fo);
  // body 只能读一次：先取全文再尝试 JSON 解析，非 JSON 时保留原文供日志
  var data=null,rawTxt='';
  try{
    rawTxt=await resp.text();
    try{data=JSON.parse(rawTxt)}catch(e){data={_raw:rawTxt.slice(0,240)}}
  }catch(e){data={_raw:'(读取响应失败: '+e.message+')'}}
  var dur=Date.now()-t0;
  appLog('[kmage] '+(opts.method||'GET')+' '+dispPath+'（'+modeLabel+'）→ HTTP '+resp.status+' ('+dur+'ms)',
    resp.ok?'s':(resp.status>=500||resp.status===0?'e':'w'),
    resp.ok?'':((rawTxt?('非JSON响应: '+rawTxt):JSON.stringify(data).slice(0,240))));
  return {ok:resp.ok,status:resp.status,data:data,durationMs:dur};
}
// ---------- kdr 通道 API 封装 ----------
// v1.5 直连优先: 浏览器直连上游 /api/*，网络失败自动回退 Worker 代理；
// 鉴权（key/host）由调用方放入请求 body
async function kdrApi(path,opts){
  opts=opts||{};
  var base=directBases.kdr;
  if(base){
    try{
      return await kdrApiVia(base+'/api'+path,opts,'直连','/api'+path);
    }catch(e){
      appLog('[kdr] 直连上游失败（'+(e.message||e)+'），自动回退 Worker 代理','w');
    }
  }
  return await kdrApiVia('/api/kdr'+path,opts,'代理','/api'+path);
}
async function kdrApiVia(url,opts,modeLabel,dispPath){
  opts=opts||{};
  var fo={method:opts.method||'GET',credentials:'omit'};
  if(opts.headers)fo.headers=opts.headers;
  if(opts.body)fo.body=opts.body;
  var t0=Date.now();
  var resp=await fetch(url,fo);
  var data=null,rawTxt='';
  try{
    rawTxt=await resp.text();
    try{data=JSON.parse(rawTxt)}catch(e){data={_raw:rawTxt.slice(0,240)}}
  }catch(e){data={_raw:'(读取响应失败: '+e.message+')'}}
  var dur=Date.now()-t0;
  appLog('[kdr] '+(opts.method||'GET')+' '+dispPath+'（'+modeLabel+'）→ HTTP '+resp.status+' ('+dur+'ms)',
    resp.ok?'i':(resp.status>=500?'e':'w'),
    (!resp.ok)?((rawTxt?('非JSON响应: '+rawTxt):JSON.stringify(data).slice(0,240))):'');
  return {ok:resp.ok,status:resp.status,data:data,durationMs:dur};
}
// Gift Key 获取（缓存 10 分钟；失败回退到站点公开默认 Key）
async function ensureGiftKey(force){
  var g=kdrState.gift||{key:'',alias:'',ts:0};
  if(!force&&g.key&&(Date.now()-g.ts)<10*60*1000)return g;
  var r=await kdrApi('/gift-key');
  if(r.ok&&r.data&&(r.data.key||r.data.alias)){
    kdrState.gift={key:String(r.data.key||r.data.alias).trim(),alias:String(r.data.alias||r.data.key||'').trim(),ts:Date.now()};
    saveKdrState();renderGiftLine();
    appLog('[kdr] Gift Key 已更新: '+kdrState.gift.alias,'s');
    return kdrState.gift;
  }
  appLog('[kdr] Gift Key 获取失败（HTTP '+r.status+'），使用回退 Key','w');
  if(!g.key){kdrState.gift={key:KDR_GIFT_FALLBACK,alias:'fallback',ts:Date.now()};saveKdrState();renderGiftLine()}
  return kdrState.gift;
}
function renderGiftLine(){
  var el=$('giftKeyAlias');if(!el)return;
  if(kdrState.gift&&kdrState.gift.key){
    el.textContent=(kdrState.gift.alias||kdrState.gift.key).slice(0,28);
    el.className='pill ok';
  }else{el.textContent='未获取';el.className='pill mut'}
  var ta=$('kdrCustomKeys');
  if(ta&&document.activeElement!==ta)ta.value=(kdrState.customKeys||[]).join(String.fromCharCode(10));
}
function upstreamErrMsg(r,fallback){
  if(r&&r.data){
    if(typeof r.data.error==='string')return r.data.error;
    if(r.data.error&&r.data.error.message)return r.data.error.message;
    if(r.data.message)return r.data.message;
    if(r.data._raw)return String(r.data._raw).slice(0,160);
  }
  return fallback||('上游错误 HTTP '+(r?r.status:''));
}
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function sleep(ms){return new Promise(function(res){setTimeout(res,ms)})}
</script>
<script>
// ---------- kmage 账号生命周期 ----------
// 注册：{email,password} → 201 + Set-Cookie 会话；随后建 API Key
async function registerAccount(silent){
  var email=genEmail(),password=genPassword();
  var a={id:'acc_'+randStr(10),email:email,password:password,session:'',apiKey:'',apiKeyId:'',apiKeyHint:'',
    credits:1,lastCheckinDay:'',eligibleAt:0,createdAt:Date.now(),disabled:false,lastError:''};
  appLog('[kmage] 注册新账号 '+maskEmail(email),'i');
  var r=await kmageApi('/auth/register',{method:'POST',body:JSON.stringify({email:email,password:password})},a);
  if(!r.ok){
    appLog('[kmage] 注册失败 '+maskEmail(email),'e','','');
    throw new Error('注册失败: '+upstreamErrMsg(r,'HTTP '+r.status));
  }
  a.credits=(r.data&&r.data.user&&typeof r.data.user.credits==='number')?r.data.user.credits:1;
  if(!a.session){ // 极少数情况上游未返回 Set-Cookie，主动登录补会话
    try{await loginAccount(a)}catch(e){a.lastError='会话获取失败:'+e.message}
  }
  // 注册成功后立刻创建 API Key（密钥只显示一次，必须当场保存）
  try{await createKeyFor(a)}catch(e){a.lastError='建Key失败:'+e.message}
  appLog('[kmage] 注册完成 '+maskEmail(email)+'（'+a.credits+' 分，24h 后可签到）','s');
  state.accounts.push(a);saveState();renderAll();
  if(!silent)toast('注册成功: '+maskEmail(email)+'（'+a.credits+' 分'+(a.apiKey?', Key已建':'')+'）','success');
  return a;
}
// 登录（会话失效时自动调用）
async function loginAccount(a){
  appLog('[kmage] 登录 '+maskEmail(a.email),'i');
  var r=await kmageApi('/auth/login',{method:'POST',body:JSON.stringify({email:a.email,password:a.password})},a);
  if(!r.ok)throw new Error('登录失败: '+upstreamErrMsg(r,'HTTP '+r.status));
  if(!a.session)throw new Error('登录成功但未取得会话');
  return true;
}
// 确保会话可用（401 时重登一次）
async function withSession(a,fn){
  var r=await fn();
  if(r.status===401){
    await loginAccount(a);
    r=await fn();
  }
  return r;
}
// 创建 API Key
async function createKeyFor(a){
  var r=await withSession(a,function(){return kmageApi('/api-keys',{method:'POST',body:JSON.stringify({name:genKeyName()})},a)});
  if(!r.ok)throw new Error(upstreamErrMsg(r,'HTTP '+r.status));
  if(r.data&&r.data.key){a.apiKey=r.data.key;a.apiKeyId=(r.data.api_key&&r.data.api_key.id)||'';a.apiKeyHint=(r.data.api_key&&r.data.api_key.hint)||''}
  else throw new Error('响应中无密钥');
}
// 刷新额度（/auth/me）
async function refreshAccount(a){
  var r=await withSession(a,function(){return kmageApi('/auth/me',{},a)});
  if(!r.ok){a.lastError=upstreamErrMsg(r,'HTTP '+r.status);return false}
  if(r.data&&r.data.user){
    a.credits=typeof r.data.user.credits==='number'?r.data.user.credits:a.credits;
    a.lastError='';
  }
  return true;
}
// 签到：GET 状态 → eligible 则 POST
async function checkinAccount(a){
  var st=await withSession(a,function(){return kmageApi('/checkin',{},a)});
  if(!st.ok){a.lastError=upstreamErrMsg(st,'HTTP '+st.status);return {skipped:true}}
  var d=st.data||{};
  a.eligibleAt=d.eligible_at||0;
  if(d.credits!=null&&typeof d.credits==='number')a.credits=d.credits;
  if(d.checked_in===true){a.lastCheckinDay=todayGmt8();return {already:true,reward:d.reward_credits}}
  if(d.eligible===false){
    var remain=(d.eligible_at||a.eligibleAt||0)-Date.now();
    return {wait:true,eligibleAt:d.eligible_at||0,remainMs:remain>0?remain:0};
  }
  var claim=await withSession(a,function(){return kmageApi('/checkin',{method:'POST'},a)});
  if(!claim.ok){a.lastError=upstreamErrMsg(claim,'HTTP '+claim.status);return {failed:true,msg:a.lastError}}
  var cd=claim.data||{};
  var awarded=(typeof cd.awarded_credits==='number')?cd.awarded_credits:((typeof cd.reward_credits==='number'&&!cd.checked_in)?cd.reward_credits:0);
  if(typeof cd.credits==='number'){a.credits=cd.credits}
  else if(awarded){a.credits=(typeof a.credits==='number'?a.credits:0)+awarded}
  a.lastCheckinDay=todayGmt8();
  return {done:true,reward:awarded,credits:a.credits};
}
</script>
<script>
// ---------- 号池批量操作（kmage） ----------
async function batchRegister(n,silent){
  var done=0,fail=0;
  appLog('[kmage] 批量注册开始 ×'+n,'i');
  for(var i=0;i<n;i++){
    try{await registerAccount(true);done++}
    catch(e){fail++;toast(e.message,'error');break}
    // 反规律化：2.5~8 秒随机间隔（含偶尔较长停顿），避免等间隔请求指纹
    var gap=2500+Math.floor(Math.random()*5500);
    if(Math.random()<0.15)gap+=4000;
    appLog('[kmage] 批量注册间隔 '+Math.round(gap/1000)+'s','i');
    await sleep(gap);
  }
  appLog('[kmage] 批量注册结束: 成功 '+done+'，失败 '+fail,done?'s':'e');
  if(!silent)toast('批量注册完成: 成功 '+done+' 个'+(fail?('，失败 '+fail+' 个'):''),fail?'info':'success');
  renderAll();
}
async function checkinAll(silent){
  var done=0,already=0,wait=0,failed=0;
  // 反规律化：打乱签到顺序，逐号随机间隔 0.8~2.8s
  var order=[];
  for(var k=0;k<state.accounts.length;k++){if(!state.accounts[k].disabled&&state.accounts[k].session)order.push(state.accounts[k])}
  for(var s1=order.length-1;s1>0;s1--){var j=Math.floor(Math.random()*(s1+1));var t=order[s1];order[s1]=order[j];order[j]=t}
  appLog('[kmage] 批量签到开始 ×'+order.length,'i');
  for(var i=0;i<order.length;i++){
    var a=order[i];
    try{
      var r=await checkinAccount(a);
      if(r.done){done++;if(r.credits!=null)a.credits=r.credits;appLog('[kmage] 签到成功 '+maskEmail(a.email)+' +'+(r.reward||0)+' 分','s')}
      else if(r.already)already++;
      else if(r.wait){wait++;appLog('[kmage] 签到等待 '+maskEmail(a.email)+'（注册未满24h，剩 '+fmtRemain(r.remainMs)+'）','w')}
      else failed++;
    }catch(e){failed++;appLog('[kmage] 签到异常 '+maskEmail(a.email)+': '+e.message,'e')}
    renderAll();
    await sleep(800+Math.floor(Math.random()*2000));
  }
  saveState();renderAll();
  appLog('[kmage] 批量签到结束: 成功 '+done+'，已签 '+already+'，待激活 '+wait+'，失败 '+failed,failed?'w':'s');
  if(!silent){
    var parts=[];
    if(done)parts.push('签到成功 '+done);
    if(already)parts.push('已签 '+already);
    if(wait)parts.push('待激活 '+wait);
    if(failed)parts.push('失败 '+failed);
    toast(parts.length?('批量签到: '+parts.join('，')):'没有需要签到的账号',failed&&!done?'error':'success');
  }
  return {done:done,already:already,wait:wait,failed:failed};
}
// 剩余时间格式化：X小时Y分
function fmtRemain(ms){
  if(!ms||ms<0)ms=0;
  var h=Math.floor(ms/3600000),m=Math.ceil((ms%3600000)/60000);
  if(m===60){h++;m=0}
  return (h>0?h+'小时':'')+m+'分';
}
async function ensureKeysAll(){
  var n=0;
  for(var i=0;i<state.accounts.length;i++){
    var a=state.accounts[i];
    if(a.disabled||a.apiKey)continue;
    try{await createKeyFor(a);n++}catch(e){a.lastError='建Key失败:'+e.message}
    renderAll();
    await sleep(400);
  }
  saveState();renderAll();
  toast(n?('为 '+n+' 个账号补建了 API Key'):'所有账号都已有 Key',n?'success':'info');
}
async function refreshAllCredits(){
  var ok=0;
  for(var i=0;i<state.accounts.length;i++){
    var a=state.accounts[i];
    if(a.disabled||!a.session)continue;
    try{if(await refreshAccount(a))ok++}catch(e){}
    renderAll();
    await sleep(300);
  }
  saveState();renderAll();
  toast('已刷新 '+ok+' 个账号额度','success');
}
function archiveDisabled(){
  var kept=[],moved=0;
  for(var i=0;i<state.accounts.length;i++){
    var a=state.accounts[i];
    if(a.disabled){state.abandoned.push(a);moved++}else kept.push(a);
  }
  state.accounts=kept;saveState();renderAll();
  toast('已归档 '+moved+' 个禁用账号','success');
}

// ---------- 导出：号池 / 全部设置 ----------
// 1) 仅号池账号列表（旧格式兼容，含会话与 API Key，注意保管）
function poolExportAccounts(){
  return state.accounts.map(function(a){return {email:a.email,password:a.password,session:a.session||'',apiKey:a.apiKey||'',apiKeyId:a.apiKeyId||'',apiKeyHint:a.apiKeyHint||'',credits:a.credits!=null?a.credits:0,lastCheckinDay:a.lastCheckinDay||'',eligibleAt:a.eligibleAt||0,createdAt:a.createdAt||0,disabled:!!a.disabled}});
}
function exportPool(){
  var data={
    type:'kmage-pool',version:VERSION,exportedAt:new Date().toISOString(),
    accounts:poolExportAccounts(),
    abandoned:(state.abandoned||[]).map(function(a){return {email:a.email,password:a.password,abandonedAt:a.abandonedAt||Date.now()}}),
    settings:{emailDomain:state.settings.emailDomain||'gmail.com',rotationStrategy:state.settings.rotationStrategy||'most-credits'}
  };
  var name='kmage-pool-'+new Date().toISOString().slice(0,10).replace(/-/g,'')+'.json';
  var blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;
  document.body.appendChild(a);a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},800);
  appLog('导出号池: '+name+'（活跃 '+data.accounts.length+'，归档 '+data.abandoned.length+'）','s');
  toast('已导出 '+data.accounts.length+' 个活跃账号（含会话与 Key，请妥善保管）','success');
}
// 2) 全部设置包：kmage 号池与设置 + kdr 自定义 Key/Gift Key + 通知 + 当前通道
function exportSettingsAll(){
  var data={
    type:'ai-image-settings',version:VERSION,exportedAt:new Date().toISOString(),
    channel:channel,
    kmage:{
      accounts:poolExportAccounts(),
      abandoned:(state.abandoned||[]).map(function(a){return {email:a.email,password:a.password,abandonedAt:a.abandonedAt||Date.now()}}),
      settings:{
        emailDomain:state.settings.emailDomain||'gmail.com',
        rotationStrategy:state.settings.rotationStrategy||'most-credits',
        autoRegister:state.settings.autoRegister!==false,
        autoCheckin:state.settings.autoCheckin!==false,
        theme:state.settings.theme||'system'
      }
    },
    kdr:{
      customKeys:(kdrState.customKeys||[]).slice(),
      gift:{key:(kdrState.gift&&kdrState.gift.key)||'',alias:(kdrState.gift&&kdrState.gift.alias)||''}
    },
    notificationsEnabled:!!state.settings.notificationsEnabled
  };
  var name='ai-image-settings-'+new Date().toISOString().slice(0,10).replace(/-/g,'')+'.json';
  var blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'});
  var a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;
  document.body.appendChild(a);a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},800);
  appLog('导出全部设置: '+name+'（账号 '+data.kmage.accounts.length+'，kdr 自定义 Key '+data.kdr.customKeys.length+'）','s');
  toast('已导出全部设置（含明文凭据，请妥善保管）','success');
}
// 账号合并（去重）：设置包与旧号池格式共用
function mergeAccounts(arr){
  var n=0,skip=0;
  for(var i=0;i<arr.length;i++){
    var it=arr[i];
    if(!it.email||!it.password){skip++;continue}
    var dup=false;
    for(var j=0;j<state.accounts.length;j++){if(state.accounts[j].email===it.email){dup=true;break}}
    if(!dup&&Array.isArray(state.abandoned)){for(var j2=0;j2<state.abandoned.length;j2++){if(state.abandoned[j2].email===it.email){dup=true;break}}}
    if(dup){skip++;continue}
    state.accounts.push({id:'acc_'+randStr(10),email:it.email,password:it.password,session:it.session||'',apiKey:it.apiKey||'',apiKeyId:it.apiKeyId||'',apiKeyHint:it.apiKeyHint||'',
      credits:(typeof it.credits==='number')?it.credits:0,lastCheckinDay:it.lastCheckinDay||'',eligibleAt:it.eligibleAt||0,createdAt:it.createdAt||Date.now(),disabled:!!it.disabled,lastError:''});
    n++;
  }
  return {n:n,skip:skip};
}
// 导入：自动识别 设置包(ai-image-settings) / 旧号池(kmage-pool) / 裸账号数组
async function importPoolData(txt){
  var data;
  try{data=JSON.parse(txt)}catch(e){toast('JSON 解析失败: '+e.message,'error');return}
  if(data&&data.type==='ai-image-settings'){
    // ---- 设置包 ----
    var n=0,skip=0,kn=0;
    if(data.kmage&&Array.isArray(data.kmage.accounts)){
      var m=mergeAccounts(data.kmage.accounts);n=m.n;skip=m.skip;
      if(Array.isArray(data.kmage.abandoned)){
        if(!Array.isArray(state.abandoned))state.abandoned=[];
        for(var k=0;k<data.kmage.abandoned.length;k++){
          var ab=data.kmage.abandoned[k];
          if(!ab.email)continue;
          var dup2=state.abandoned.some(function(x){return x.email===ab.email})||state.accounts.some(function(x){return x.email===ab.email});
          if(!dup2){state.abandoned.push({email:ab.email,password:ab.password,abandonedAt:ab.abandonedAt||Date.now()})}
        }
      }
      if(data.kmage.settings)state.settings=Object.assign({},state.settings,data.kmage.settings);
    }
    if(data.kdr){
      if(Array.isArray(data.kdr.customKeys)){kdrState.customKeys=data.kdr.customKeys.filter(function(x){return x&&typeof x==='string'});kn=kdrState.customKeys.length}
      if(data.kdr.gift&&data.kdr.gift.key){kdrState.gift={key:data.kdr.gift.key,alias:data.kdr.gift.alias||'',ts:0}}
    }
    if(typeof data.notificationsEnabled==='boolean')state.settings.notificationsEnabled=data.notificationsEnabled;
    saveState();saveKdrState();
    if(data.channel==='kmage'||data.channel==='kdr'){channel=data.channel;saveChannel()}
    renderSettings();applyTheme();renderGiftLine();applyChannel();renderAll();
    toast('设置包导入: kmage 账号 +'+n+(skip?('（跳过 '+skip+'）'):'')+'，kdr 自定义 Key '+kn+' 个',n||kn?'success':'info');
    appLog('导入设置包: kmage 账号 +'+n+'，kdr Key '+kn+'，通道 → '+channel,'s');
    await relinkAccounts();
    return;
  }
  // ---- 旧号池格式 ----
  var arr=Array.isArray(data)?data:(data.accounts||[]);
  if(!arr.length&&!data.accounts){ // 兼容单对象 {email,password}
    if(data.email&&data.password)arr=[data];
  }
  var abArr=(Array.isArray(data)?[]:(data.abandonedAccounts||data.abandoned||[]));
  var m2=mergeAccounts(arr);
  var n2=m2.n,skip2=m2.skip,abN=0;
  if(!Array.isArray(state.abandoned))state.abandoned=[];
  for(var k2=0;k2<abArr.length;k2++){
    var ab2=abArr[k2];
    if(!ab2.email)continue;
    var dup3=state.abandoned.some(function(x){return x.email===ab2.email})||state.accounts.some(function(x){return x.email===ab2.email});
    if(!dup3){state.abandoned.push({email:ab2.email,password:ab2.password,abandonedAt:ab2.abandonedAt||Date.now()});abN++}
  }
  saveState();renderAll();
  var msg='导入 '+n2+' 个账号'+(skip2?('，跳过 '+skip2+'（重复或缺字段）'):'')+(abN?('，归档池 +'+abN):'');
  toast(msg,n2?'success':'info');
  appLog('导入号池: '+msg,'s');
  await relinkAccounts();
}
// 无会话账号自动重登恢复（随机间隔，反规律化）
async function relinkAccounts(){
  var relink=0;
  for(var m=0;m<state.accounts.length;m++){
    var a2=state.accounts[m];
    if(!a2.session&&!a2.disabled){
      try{await loginAccount(a2);relink++;saveState();renderPool();await sleep(600+Math.floor(Math.random()*900))}catch(e){appLog('[kmage] 导入登录失败 '+maskEmail(a2.email)+': '+e.message,'w')}
    }
  }
  if(relink){toast('已为 '+relink+' 个账号恢复会话','success');appLog('[kmage] 导入后会话恢复 ×'+relink,'s')}
}
async function importPoolFile(file){
  var txt=await file.text();
  await importPoolData(txt);
}

// ---------- 选号与生成 ----------
function poolCredits(){
  var s=0;for(var i=0;i<state.accounts.length;i++){var a=state.accounts[i];if(!a.disabled&&typeof a.credits==='number')s+=a.credits}
  return s;
}
function pickAccount(){
  var cands=[];
  for(var i=0;i<state.accounts.length;i++){
    var a=state.accounts[i];
    if(!a.disabled&&a.apiKey&&(typeof a.credits==='number'&&a.credits>=1))cands.push(a);
  }
  if(!cands.length)return null;
  if(state.settings.rotationStrategy==='round-robin'){
    cands.sort(function(x,y){return x.createdAt-y.createdAt});
    var idx=state.rotationIndex%cands.length;state.rotationIndex=(state.rotationIndex+1)%Math.max(cands.length,1);
    return cands[idx];
  }
  cands.sort(function(x,y){return (y.credits-x.credits)||(x.createdAt-y.createdAt)});
  return cands[0];
}
async function findReadyAccount(){
  // 1) 直接可用的号
  var a=pickAccount();if(a)return a;
  // 2) 有会话但没 Key → 补建
  for(var i=0;i<state.accounts.length;i++){
    var x=state.accounts[i];
    if(!x.disabled&&x.session&&!x.apiKey&&(typeof x.credits==='number'&&x.credits>=1)){
      try{await createKeyFor(x);saveState();renderAll();return x}catch(e){}
    }
  }
  // 3) 有 Key 但额度显示 0/未知 → 刷新额度再试
  for(var j=0;j<state.accounts.length;j++){
    var y=state.accounts[j];
    if(!y.disabled&&y.apiKey){
      try{await refreshAccount(y)}catch(e){}
      if(typeof y.credits==='number'&&y.credits>=1){saveState();renderAll();return y}
    }
  }
  saveState();renderAll();
  // 4) 自动注册（+1 分）
  if(state.settings.autoRegister){
    try{
      var na=await registerAccount(true);
      if(na.apiKey)return na;
      await createKeyFor(na);return na;
    }catch(e){throw new Error('无可用账号且自动注册失败: '+e.message)}
  }
  throw new Error('号池没有可用账号（有 Key 且积分 ≥ 1）。请打开设置注册或签到。');
}
function refCount(){return refImages.length}
// ---------- 生图统一入口（按通道分派） ----------
async function generate(){
  if(generating)return;
  var prompt=$('prompt').value.trim();
  if(!prompt&&!refCount()){setStatus('genStatus','请先输入提示词（或添加参考图）。','err');return}
  generating=true;curHistView=null;var btn=$('btnGenerate');btn.disabled=true;btn.textContent='生成中…';
  currentRunId='R'+Date.now().toString(36)+randStr(3);
  saveFormState();
  var histEntry={ts:Date.now(),run:currentRunId,channel:channel,prompt:(prompt||'（参考图创作）').slice(0,80),model:$('model').value,size:channel==='kdr'?((($('kdrSize')&&$('kdrSize').value)||'1K')+' / '+$('ratio').value):$('ratio').value,quality:$('quality').value,account:'',status:'running',error:'',ms:0,thumb:'',url:''};
  histItems.unshift(histEntry);histItems=histItems.slice(0,HIST_MAX);renderHist();saveHist();
  var t0=Date.now();
  appLog('====== 生图开始 '+currentRunId+'（通道 '+channel+'）======','i','',currentRunId);
  appLog('参数: 通道='+channel+' model='+$('model').value+' 比例='+$('ratio').value+(channel==='kdr'?(' 档='+($('kdrSize')&&$('kdrSize').value)):'')+' quality='+$('quality').value+' 参考图='+refCount()+'张 prompt="'+(prompt||'').slice(0,80)+'"','i','',currentRunId);
  try{
    if(channel==='kdr')await generateKdr(histEntry,currentRunId,t0);
    else await generateKmage(histEntry,currentRunId,t0);
  }catch(e){
    var m=(e&&e.name==='AbortError')?'生成超时（180s），已终止。':(e.message||String(e));
    histEntry.status='error';histEntry.error=m.slice(0,120);
    setStatus('genStatus',m,'err');
    appLog('生图失败: '+m,'e','',currentRunId);
    appLog('====== 生图结束（失败，耗时 '+((Date.now()-t0)/1000).toFixed(1)+'s）======','e','',currentRunId);
    notifyUser('❌ 生图失败','【AI生图·'+channel+'】'+m.slice(0,120),'fail-'+currentRunId);
  }finally{
    histEntry.ms=Math.round((Date.now()-t0)/100)/10;
    saveState();saveKdrState();saveHist();saveLogs();generating=false;btn.disabled=false;
    btn.textContent=(channel==='kdr')?'开始生成（kdr · 免费）':'开始生成（消耗 1 积分）';
    renderAll();renderHist();
  }
}
// ---------- kmage 生图流程 ----------
async function generateKmage(histEntry,runId,t0){
  var acc=await findReadyAccount();
  histEntry.account=maskEmail(acc.email);
  appLog('[kmage] 选中账号 '+maskEmail(acc.email)+'（积分 '+acc.credits+'，注册于 '+new Date(acc.createdAt).toLocaleString()+'）','i','',runId);
  if(acc.createdAt&&(Date.now()-acc.createdAt)<24*3600*1000){
    appLog('[kmage] 提示: 该账号注册未满 24 小时。24h 冷却只限制签到，不影响生图（实测新生号可立即生图）；若本号生图异常将自动换号','w','',runId);
  }
  setStatus('genStatus','使用 '+maskEmail(acc.email)+'（'+acc.credits+' 分）· 正在上游生成，约 20~60 秒…','info');
  var body={prompt:$('prompt').value.trim()||'基于参考图创作',model:$('model').value,size:$('ratio').value,quality:$('quality').value,response_format:'b64_json',n:1};
  if(refCount())body.reference_images=refImages.slice(0,10);
  var r=await genWithAccount(acc,body,runId);
  if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
    finishGenSuccess(r,acc,histEntry,runId);
  }else{
    var msg=upstreamErrMsg(r,'生成失败');
    // 401: Key 失效 → 重登 + 重建 Key 重试一次；402: 积分不足 → 标记后换号重试一次；429: 稍候重试一次
    if(r.status===401){
      appLog('[kmage] API Key 失效，重登并重建 Key 后重试','w','',runId);
      setStatus('genStatus','API Key 失效，正在重新登录并重建 Key…','info');
      await loginAccount(acc);await createKeyFor(acc);saveState();
      r=await genWithAccount(acc,body,runId);
      if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
        finishGenSuccess(r,acc,histEntry,runId);
      }else{throw new Error(upstreamErrMsg(r,'重试后仍失败'))}
    }else if(r.status===402){
      acc.credits=0;saveState();renderAll();
      appLog('[kmage] 积分不足，标记后换号重试','w','',runId);
      setStatus('genStatus',maskEmail(acc.email)+' 积分不足，切换其他账号…','info');
      var acc2=await findReadyAccount();
      if(acc2===acc)throw new Error('积分不足: '+msg);
      histEntry.account=maskEmail(acc2.email);
      appLog('[kmage] 切换到 '+maskEmail(acc2.email)+'（积分 '+acc2.credits+'）','i','',runId);
      setStatus('genStatus','使用 '+maskEmail(acc2.email)+'（'+acc2.credits+' 分）· 重新生成…','info');
      r=await genWithAccount(acc2,body,runId);
      if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
        finishGenSuccess(r,acc2,histEntry,runId);
      }else{throw new Error(upstreamErrMsg(r,'切换账号后仍失败'))}
    }else if(r.status===429){
      appLog('[kmage] 上游限流，5 秒后重试','w','',runId);
      setStatus('genStatus','上游限流，5 秒后重试…','info');
      await sleep(5000);
      r=await genWithAccount(acc,body,runId);
      if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
        finishGenSuccess(r,acc,histEntry,runId);
      }else{throw new Error(upstreamErrMsg(r,'限流重试失败'))}
    }else if(r.status>=500){
      // 网关类错误（502/503/504，图生图大请求体时偶发，上游失败自动返还积分）：
      // 等 4s 同号重试一次，仍失败换号再试一次（均记日志）
      appLog('[kmage] 上游网关错误 HTTP '+r.status+'，4 秒后同号重试','w','',runId);
      setStatus('genStatus','上游网关错误（HTTP '+r.status+'），4 秒后自动重试…','info');
      await sleep(4000);
      r=await genWithAccount(acc,body,runId);
      if(!(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json)){
        appLog('[kmage] 同号重试仍失败（HTTP '+r.status+'），换号再试','w','',runId);
        setStatus('genStatus','重试仍失败，切换其他账号…','info');
        var accG=null;
        for(var gi=0;gi<state.accounts.length;gi++){
          var candG=state.accounts[gi];
          if(candG!==acc&&!candG.disabled&&candG.apiKey&&(typeof candG.credits==='number'&&candG.credits>=1)){accG=candG;break}
        }
        if(accG){
          histEntry.account=maskEmail(accG.email);
          appLog('[kmage] 切换到 '+maskEmail(accG.email)+'（积分 '+accG.credits+'）重试','i','',runId);
          r=await genWithAccount(accG,body,runId);
          if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
            finishGenSuccess(r,accG,histEntry,runId);
          }else{throw new Error(upstreamErrMsg(r,'换号重试后仍失败（HTTP '+r.status+'）'))}
        }else{
          throw new Error(upstreamErrMsg(r,'网关错误 '+r.status+'（重试与换号均不可用）'));
        }
      }else{
        finishGenSuccess(r,acc,histEntry,runId);
      }
    }else{
      // 新生号保护：若账号注册未满 24h 且生图被拒（如 403），自动换其他账号重试一次
      var fresh=acc.createdAt&&(Date.now()-acc.createdAt)<24*3600*1000;
      if(fresh&&(r.status===403||r.status===400)){
        var remain=24*3600*1000-(Date.now()-acc.createdAt);
        appLog('[kmage] 新生号（未满24h，剩 '+fmtRemain(remain)+'）生图被拒 HTTP '+r.status+'，尝试换其他账号','w','',runId);
        setStatus('genStatus','账号注册未满 24 小时（剩 '+fmtRemain(remain)+'）可能受限，尝试其他账号…','info');
        var acc3=null;
        for(var fi=0;fi<state.accounts.length;fi++){
          var cand=state.accounts[fi];
          if(cand!==acc&&!cand.disabled&&cand.apiKey&&(typeof cand.credits==='number'&&cand.credits>=1)){acc3=cand;break}
        }
        if(acc3){
          histEntry.account=maskEmail(acc3.email);
          appLog('[kmage] 切换到 '+maskEmail(acc3.email)+'（积分 '+acc3.credits+'）','i','',runId);
          r=await genWithAccount(acc3,body,runId);
          if(r.ok&&r.data&&r.data.data&&r.data.data.length&&r.data.data[0].b64_json){
            finishGenSuccess(r,acc3,histEntry,runId);
          }else{throw new Error(upstreamErrMsg(r,'换号后仍失败'))}
        }else{
          throw new Error(msg+'（提示: 号池其他账号均不可用；当前号注册未满 24 小时，剩 '+fmtRemain(remain)+'，若上游限制新生号请稍后再试）');
        }
      }else{
        throw new Error(msg);
      }
    }
  }
}
// 单次 kmage 生图请求（180s 超时）
async function genWithAccount(acc,body,runId){
  var ctrl=new AbortController();var timer=setTimeout(function(){ctrl.abort()},180000);
  try{
    appLog('[kmage] POST /v1/images/generations（'+maskEmail(acc.email)+'，超时 180s）','i','',runId);
    var r=await kmageV1('/images/generations',{method:'POST',body:JSON.stringify(body),signal:ctrl.signal},acc.apiKey);
    if(r.ok){appLog('[kmage] 上游受理成功，耗时 '+((r.durationMs||0)/1000).toFixed(1)+'s','s','',runId)}
    return r;
  }catch(e){
    if(e&&e.name==='AbortError'){appLog('[kmage] 请求超时 180s，已中止（AbortError）','e','',runId)}
    else{appLog('[kmage] 请求异常: '+(e.message||e),'e','',runId)}
    throw e;
  }finally{clearTimeout(timer)}
}
function finishGenSuccess(r,acc,histEntry,runId){
  lastResultB64=r.data.data[0].b64_json;
  showResult(r.data);
  histEntry.ms=Math.round(((r.data.generation_time_ms||r.durationMs||0))/100)/10;
  makeThumb(r.data.data[0].b64_json,function(t){if(t){histEntry.thumb=t;saveHist();if(curHistView!==null&&histItems[curHistView]&&histItems[curHistView].run===histEntry.run)renderHist()}else{saveHist()}});
  if(typeof acc.credits==='number')acc.credits=Math.max(0,acc.credits-1);
  histEntry.status='ok';
  var secs=((r.data.generation_time_ms||r.durationMs||0)/1000).toFixed(1);
  setStatus('genStatus','生成完成（耗时 '+secs+'s）· '+maskEmail(acc.email)+' 剩余 '+acc.credits+' 分','ok');
  appLog('====== 生图结束（成功，上游耗时 '+secs+'s，'+maskEmail(acc.email)+' 剩 '+acc.credits+' 分）======','s','',runId);
  saveHist();
  notifyUser('✅ 生图完成','【AI生图·kmage】'+(histEntry.prompt||'').slice(0,40)+' … 已完成（'+secs+'s）','ok-'+runId);
}
// ---------- kdr 生图流程（2026-09 新契约：key/host 入 body，任务轮询） ----------
function kdrClientTaskId(){
  try{if(typeof crypto!=='undefined'&&crypto.randomUUID)return crypto.randomUUID()}catch(e){}
  return 'k'+Date.now().toString(36)+'-'+randStr(8);
}
async function generateKdr(histEntry,runId,t0){
  await ensureGiftKey();
  var eff=kdrEffective();
  histEntry.account=eff.isCustom?('自定义Key '+(eff.key.slice(0,6))+'…'):'共享GiftKey';
  appLog('[kdr] 生效参数: '+(eff.isCustom?'自定义 Key':'免费 Gift Key('+(kdrState.gift.alias||'gift')+')')+' host='+eff.host+' model='+eff.model+' size='+eff.size+(eff.sizeLocked?'（免费档锁定 1K）':''),'i','',runId);
  if(eff.sizeLocked&&$('kdrSize')&&$('kdrSize').value!=='1K'){
    appLog('[kdr] 免费 Key 不支持所选分辨率，已回退 1K','w','',runId);
  }
  setStatus('genStatus','[kdr] 提交任务中（'+(eff.isCustom?'自定义 Key':'共享 Gift Key')+'）…','info');
  var body={client_task_id:kdrClientTaskId(),key:eff.key,host:eff.host,model:eff.model,
    prompt:$('prompt').value.trim()||'基于参考图创作',quality:$('quality').value,size:eff.size,ratio:$('ratio').value,n:1};
  var task;
  if(refCount()){
    appLog('[kdr] 图生图模式：'+Math.min(refCount(),10)+' 张参考图（multipart /edits）','i','',runId);
    task=await kdrSubmitEdit(body,runId);
  }else{
    task=await kdrSubmitGenerate(body,runId);
  }
  if(!task.ok){
    var msg=upstreamErrMsg(task,'任务提交失败');
    if(task.status>=500){
      // 网关类错误：4s 后重试一次
      appLog('[kdr] 提交遇网关错误 HTTP '+task.status+'，4 秒后重试','w','',runId);
      setStatus('genStatus','[kdr] 上游网关错误（HTTP '+task.status+'），4 秒后重试…','info');
      await sleep(4000);
      task=refCount()?await kdrSubmitEdit(body,runId):await kdrSubmitGenerate(body,runId);
      if(!task.ok)throw new Error(upstreamErrMsg(task,'重试后仍失败（HTTP '+task.status+'）'));
    }else if((task.status===401||task.status===403)&&!eff.isCustom){
      // 免费 Key 被拒：强制刷新 Gift Key 重试一次
      appLog('[kdr] Key 被拒（HTTP '+task.status+'），强制刷新 Gift Key 后重试','w','',runId);
      setStatus('genStatus','[kdr] Key 被拒，刷新共享 Key 后重试…','info');
      await ensureGiftKey(true);
      var eff2=kdrEffective();body.key=eff2.key;body.host=eff2.host;
      task=refCount()?await kdrSubmitEdit(body,runId):await kdrSubmitGenerate(body,runId);
      if(!task.ok)throw new Error(upstreamErrMsg(task,'刷新 Key 后仍失败'));
    }else{
      throw new Error(msg);
    }
  }
  var tid=task.data&&task.data.id;
  if(!tid)throw new Error('上游未返回任务 id');
  appLog('[kdr] 任务已受理 id='+tid,'s','',runId);
  setStatus('genStatus','[kdr] 任务已提交，轮询出图中（约 10~60 秒）…','info');
  var result=await kdrPollTask(tid,runId);
  var imgUrl=(result.data&&result.data[0]&&result.data[0].url)||'';
  if(!imgUrl)throw new Error('任务完成但未返回图片 URL');
  appLog('[kdr] 出图完成，经代理拉取结果图转 base64','i','',runId);
  var b64=await kdrFetchB64(imgUrl,runId);
  if(!b64)throw new Error('结果图转存失败（空数据）');
  lastResultB64=b64;
  showResult({model:result.model||eff.model,size:result.size||eff.size,ratio:result.ratio||''});
  histEntry.status='ok';
  histEntry.url=imgUrl;   // 上游存储地址：历史导出后可在其他设备在线回看
  histEntry.ms=Math.round((Date.now()-t0)/100)/10;
  makeThumb(b64,function(t){if(t){histEntry.thumb=t;saveHist();renderHist()}else{saveHist()}});
  var secs=((Date.now()-t0)/1000).toFixed(1);
  setStatus('genStatus','生成完成（耗时 '+secs+'s）· kdr '+(eff.isCustom?'自定义 Key':'免费共享 Key'),'ok');
  appLog('====== 生图结束（成功，总耗时 '+secs+'s，kdr 通道）======','s','',runId);
  notifyUser('✅ 生图完成','【AI生图·kdr】'+(histEntry.prompt||'').slice(0,40)+' … 已完成（'+secs+'s）','ok-'+runId);
}
async function kdrSubmitGenerate(body,runId){
  appLog('[kdr] POST /api/image-tasks/generations（model='+body.model+' size='+body.size+' ratio='+body.ratio+'，key/host 入 body）','i','',runId);
  return await kdrApi('/image-tasks/generations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
}
function dataUrlToBlob(du){
  var b64=du.slice(du.indexOf(',')+1);var bin=atob(b64);var arr=new Uint8Array(bin.length);
  for(var i=0;i<bin.length;i++)arr[i]=bin.charCodeAt(i);
  return new Blob([arr],{type:'image/png'});
}
async function kdrSubmitEdit(body,runId){
  var fd=new FormData();
  fd.append('key',body.key);fd.append('host',body.host);fd.append('model',body.model);
  fd.append('prompt',body.prompt);fd.append('quality',body.quality);fd.append('size',body.size);
  fd.append('ratio',body.ratio);fd.append('n','1');fd.append('client_task_id',body.client_task_id);
  var n=Math.min(refImages.length,10);
  for(var i=0;i<n;i++){fd.append('image',dataUrlToBlob(refImages[i]),'ref'+i+'.png')}
  appLog('[kdr] POST /api/image-tasks/edits（multipart，'+n+' 张参考图，key/host 入表单）','i','',runId);
  return await kdrApi('/image-tasks/edits',{method:'POST',body:fd});
}
async function kdrPollTask(tid,runId){
  var t0=Date.now(),errs=0;
  while(Date.now()-t0<180000){
    await sleep(3000);
    var r;
    try{r=await kdrApi('/image-tasks/'+encodeURIComponent(tid))}
    catch(e){errs++;appLog('[kdr] 轮询网络异常: '+(e.message||e),'w','',runId);if(errs>8)throw new Error('轮询连续失败: '+(e.message||e));continue}
    if(r.status===404)throw new Error('任务已失效（404，可能已过期）');
    if(!r.ok){errs++;appLog('[kdr] 轮询非 2xx（HTTP '+r.status+'），第 '+errs+' 次','w','',runId);if(errs>8)throw new Error('轮询连续失败（HTTP '+r.status+'）');continue}
    errs=0;
    var st=r.data&&r.data.status;
    if(st==='success'||st==='done')return r.data||{};
    if(st==='error'||st==='failed')throw new Error(upstreamErrMsg(r,'kdr 上游任务失败'));
    setStatus('genStatus','[kdr] 生成中（'+(st||'processing')+'，已 '+Math.round((Date.now()-t0)/1000)+'s）…','info');
  }
  throw new Error('生成超时（180s轮询）。免费通道失败不产生扣费。');
}
// 统一 blob → base64（v1.5 抽取自 kdrFetchB64，直连/代理两条路径共用）
function blobToB64(blob){
  return new Promise(function(res,rej){
    var fr=new FileReader();
    fr.onload=function(){res(String(fr.result).split(',')[1]||'')};
    fr.onerror=function(){rej(new Error('结果图读取失败'))};
    fr.readAsDataURL(blob);
  });
}
async function kdrFetchB64(u,runId){
  var t0=Date.now();
  // v1.5: 优先浏览器直连图床（2026-09-23 实测图床不校验 Referer，无 Referer 直拉 200），
  // 失败自动回退 Worker /kdr/img 代理（代理带 Referer 兼容校验 Referer 的图床）
  try{
    var dresp=await fetch(u,{credentials:'omit',referrerPolicy:'no-referrer'});
    if(dresp.ok){
      appLog('[kdr] 直连图床 GET → HTTP '+dresp.status+' ('+(Date.now()-t0)+'ms)','i','',runId);
      var db64=await blobToB64(await dresp.blob());
      if(db64)return db64;
      appLog('[kdr] 直连图床响应为空，回退 Worker 代理','w','',runId);
    }else{
      appLog('[kdr] 直连图床 HTTP '+dresp.status+'，回退 Worker 代理','w','',runId);
    }
  }catch(e){appLog('[kdr] 直连图床异常（'+(e.message||e)+'），回退 Worker 代理','w','',runId)}
  var resp=await fetch('/kdr/img?url='+encodeURIComponent(u),{credentials:'omit'});
  appLog('[kdr] GET /kdr/img（代理）→ HTTP '+resp.status+' ('+(Date.now()-t0)+'ms)',resp.ok?'i':'e','',runId);
  if(!resp.ok)throw new Error('结果图拉取失败 HTTP '+resp.status);
  return await blobToB64(await resp.blob());
}
// ---------- 结果展示（双通道共用） ----------
function showResult(data){
  $('resultEmpty').style.display='none';
  $('resultWrap').style.display='block';
  $('resultImg').src='data:image/png;base64,'+lastResultB64;
  var kb=Math.round(lastResultB64.length*3/4/1024);
  $('resultMeta').textContent=(data&&data.model?data.model:'')+' · '+((data&&data.size)||'')+((data&&data.ratio)?(' · '+data.ratio):'')+' · 约 '+kb+' KB';
}
function downloadResult(){
  var h=(curHistView!==null)?histItems[curHistView]:null;
  if(h&&!(h.run===currentRunId&&lastResultB64)){
    if(h.url){window.open(h.url,'_blank');return}
    toast('该历史条目仅有预览缩略图（kmage 上游未提供下载地址）','info');return;
  }
  if(!lastResultB64)return;
  var b64=lastResultB64,len=b64.length,bin=new Uint8Array(Math.floor(len*3/4)+3),p=0;
  var raw=atob(b64);for(var i=0;i<raw.length;i++)bin[i]=raw.charCodeAt(i);
  var blob=new Blob([bin.subarray(0,raw.length)],{type:'image/png'});
  var a=document.createElement('a');a.href=URL.createObjectURL(blob);
  a.download=(channel==='kdr'?'kdr_':'kmage_')+new Date().toISOString().slice(0,19).replace(/[:T-]/g,'')+'.png';
  document.body.appendChild(a);a.click();
  setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},800);
}
</script>
<script>
// ---------- 渲染 ----------
function renderBadge(){
  var b=$('creditBadge');
  if(channel==='kdr'){
    var n=(kdrState.customKeys||[]).length;
    if(n){b.textContent='自定义 Key ×'+n;b.className='badge';b.title='kdr 通道：自定义 Key 数量（优先于共享 Key 使用）'}
    else{b.textContent='kdr · 共享 Key';b.className='badge';b.title='kdr 通道：免费共享 Gift Key（打开设置可配置自定义 Key）'}
    return;
  }
  var total=poolCredits();
  b.textContent='积分 '+total;
  b.className='badge'+(total<=0?' zero':'');
  b.title='号池可用总积分（'+state.accounts.length+' 个账号）';
}
function acctStatus(a){
  if(a.disabled)return '<span class="pill mut">已禁用</span>';
  if(!a.session)return '<span class="pill err">无会话</span>';
  if(!a.apiKey)return '<span class="pill warn">未建Key</span>';
  if(a.lastCheckinDay===todayGmt8())return '<span class="pill ok">今日已签</span>';
  var now=Date.now();
  if(a.eligibleAt&&a.eligibleAt>now){
    return '<span class="pill warn">待激活 '+fmtRemain(a.eligibleAt-now)+'</span>';
  }
  if(typeof a.credits==='number'&&a.credits<=0)return '<span class="pill err">0分</span>';
  return '<span class="pill ok">正常</span>';
}
function renderPool(){
  var tb=$('poolTbody');
  if(!state.accounts.length){tb.innerHTML='<tr><td colspan="6" style="color:var(--text-muted)">号池为空，点击"注册新账号"开始。</td></tr>';return}
  var html='';
  for(var i=0;i<state.accounts.length;i++){
    var a=state.accounts[i];
    html+='<tr>'
      +'<td title="'+esc(a.email)+'">'+esc(maskEmail(a.email))+'</td>'
      +'<td>'+(typeof a.credits==='number'?a.credits:'-')+'</td>'
      +'<td>'+(a.apiKey?'<span class="pill ok">已有</span>':'<span class="pill mut">无</span>')+'</td>'
      +'<td>'+(a.lastCheckinDay===todayGmt8()?'✓':'—')+'</td>'
      +'<td>'+acctStatus(a)+'</td>'
      +'<td class="op">'
      +'<button class="btn sm" data-act="checkin" data-i="'+i+'">签到</button> '
      +'<button class="btn sm" data-act="refresh" data-i="'+i+'">刷新</button> '
      +'<button class="btn sm" data-act="toggle" data-i="'+i+'">'+(a.disabled?'启用':'禁用')+'</button> '
      +'<button class="btn sm danger" data-act="remove" data-i="'+i+'">删除</button>'
      +'</td></tr>';
  }
  tb.innerHTML=html;
}
function renderHist(){
  var ul=$('histList');var html='';
  for(var i=0;i<histItems.length;i++){
    var h=histItems[i];
    var st=h.status==='ok'?'<span class="okc">✓</span>':(h.status==='running'?'⋯':'<span class="errc">✗</span>');
    var pic=h.thumb?('<img class="hthumb" src="'+h.thumb+'" alt="">'):'<span class="hph">'+(h.status==='ok'?'图':'—')+'</span>';
    var tip=esc(h.prompt)+'（'+esc(h.channel||'kmage')+' · '+esc(String(h.model||'').replace('gpt-image-',''))+' · '+new Date(h.ts).toLocaleString()+'）'+(h.error?(' 失败: '+esc(h.error)):'');
    html+='<li data-hi="'+i+'"'+(curHistView===i?' class="cur"':'')+' title="'+tip+'">'+pic
      +'<span class="st">'+st+'</span>'
      +'<span class="hp">'+esc(h.prompt)+'</span>'
      +'<span class="chtag">'+esc(h.channel||'kmage')+'</span>'
      +'<span class="htime">'+fmtTime(h.ts)+'</span></li>';
  }
  ul.innerHTML=html||'<li class="hist-empty">暂无任务；成功与失败的任务都会记录在此，点击条目可回看</li>';
}
function renderRefs(){
  var list=$('refList');
  var html='';
  for(var i=0;i<refImages.length;i++){
    html+='<div class="ref-item"><img src="'+refImages[i]+'"><button class="rm" data-rm="'+i+'" type="button">×</button></div>';
  }
  html+='<button class="ref-add" id="refAdd" type="button" title="添加参考图">+</button>';
  list.innerHTML=html;
  bindRefAdd();
}
function renderAll(){renderBadge();if($('hubDialog').open){renderPool();renderGiftLine()}}
function renderSettings(){
  $('themeSel').value=state.settings.theme||'system';
  $('rotationStrategy').value=state.settings.rotationStrategy||'most-credits';
  $('emailDomain').value=state.settings.emailDomain||'gmail.com';
  $('autoRegisterChk').checked=state.settings.autoRegister!==false;
  $('autoCheckinChk').checked=state.settings.autoCheckin!==false;
  $('notifyChk').checked=!!state.settings.notificationsEnabled;
}
function saveSettingsFromUI(){
  state.settings.theme=$('themeSel').value;
  applyTheme();
  state.settings.rotationStrategy=$('rotationStrategy').value;
  state.settings.emailDomain=($('emailDomain').value.trim()||'gmail.com');
  state.settings.autoRegister=$('autoRegisterChk').checked;
  state.settings.autoCheckin=$('autoCheckinChk').checked;
  state.settings.notificationsEnabled=$('notifyChk').checked;
  saveState();
}
function saveKdrSettingsFromUI(){
  // 注意：本文件内嵌于外层模板字符串，内层正则不可写 CR/LF 转义序列
  // （会被外层转义为真实换行，重演 kd-v2.2 坑）；用 String.fromCharCode 拆行
  var CR=String.fromCharCode(13),LF=String.fromCharCode(10);
  var lines=$('kdrCustomKeys').value.split(CR).join(LF).split(LF).map(function(s){return s.trim()}).filter(Boolean);
  kdrState.customKeys=lines;saveKdrState();renderBadge();
  appLog('[kdr] 自定义 Key 已保存 ×'+lines.length,'i');
}

// ---------- 关于（自包含 README + 完整迭代时间线 + 使用帮助） ----------
// 对外脱敏：源站一律以「kmage 站点 / kdr 站点」表述；真实上游仅经 GET /about 提供排障方
var LOGO_SVG='<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14.5 5.5C8.4 5.5 3.5 10.3 3.5 16.3S8.4 27 14.5 27c1.8 0 2.9-1 2.9-2.4 0-.7-.3-1.2-.8-1.8-.4-.5-.7-1-.7-1.6 0-1.3 1-2.2 2.5-2.2h2.9c3 0 5.2-1.9 5.2-4.8 0-5.1-5.4-8.7-12-8.7z"/><path d="M19.8 19.5l6.3-9.9c.7-1.1.4-2.6-.7-3.3-1.1-.7-2.6-.4-3.3.7l-6.3 9.9 1 3.4z"/><circle cx="9.3" cy="12.4" r="1.3"/><circle cx="14.6" cy="10" r="1.3"/><circle cx="8.9" cy="18.7" r="1.3"/></svg>';
function ABOUT_HTML(){
  var h=[];
  h.push('<div class="about-hero">'+LOGO_SVG+'<div><div class="t">AI生图</div><div class="v">'+VERSION+' · kmage + kdr 双通道 · 单文件 Cloudflare Worker</div></div></div>');
  h.push('<p style="color:var(--accent-strong);font-weight:600">AI Agent 提示：本页为自包含单文件 Cloudflare Worker（后端代理+内嵌前端+号池），可将本页整体作为 skill 调用；本文档即调试入口与使用说明。服务自描述: GET /about（含真实上游地址）；健康检查: GET /healthz。</p>');
  h.push('<h3>1. 这是什么</h3>');
  h.push('<p>本页把「准备凭据 → 发起生图 → 取回结果」整条链路自动化，提供 kmage（默认）与 kdr 两个免费生图通道，可通过 header 上的通道选择器随时切换。生成结果、运行日志、任务历史与设置全部保存在你自己的浏览器本地。界面适配桌面与手机竖屏：右上角为统一的单齿轮按钮，点开浮窗用选项卡切换设置/控制台/关于（全宽度同一组件）；支持深色模式（设置 → 界面主题：跟随系统/浅色/深色，默认跟随系统并实时感应系统切换）。</p>');
  h.push('<h3>2. 安装到系统（PWA）与界面记忆（v1.4）</h3>');
  h.push('<p>· 本应用是 PWA，可安装到操作系统：浏览器地址栏出现「安装」图标时点击即可（设置 → 通用选项 → 「安装到系统」按钮亦可；iOS Safari 用「分享 → 添加到主屏幕」）。应用名「AI生图」，图标为白底圆角矩形叠加画笔颜料盘 logo（与 favicon 同款）；以 standalone 模式打开，保留系统标题栏与窗口控制。</p>');
  h.push('<p>· 创作面板选项（模型 / 画面比例 / 精细度 / kdr 分辨率档 / 提示词）自动记忆在浏览器 localStorage（kmage_form_v1），下次打开自动恢复；模型按通道分别记忆（kmage 与 kdr 各一套）。</p>');
  h.push('<h3>3. 双通道说明</h3>');
  h.push('<p><b>kmage 通道（默认）</b>：基于「kmage 站点」官方 OpenAI 兼容 API。自动注册账号 → 每日签到攒积分 → API Key 调用生图；1 积分 = 1 张图，失败的请求上游自动返还积分。支持 3 个模型、7 种比例、精细度与图生图（≤10 张参考图）。</p>');
  h.push('<p><b>kdr 通道</b>：基于「kdr 站点」免费共享 Gift Key（无账号体系）。生图为任务制：提交后轮询约 10~60 秒出图。免费档固定基础模型与 1K 分辨率；在设置中填入自定义付费 Key 后可解锁全部模型与 2K/4K 分辨率（自定义 Key 自动优先）。2026-09 上游改版后契约为 key/host 入请求 body，本版已适配并恢复可用。</p>');
  h.push('<h3>4. kmage 积分与 24 小时规则</h3>');
  h.push('<p>· 新注册账号送 1 积分；账号注册满 24 小时后开放每日签到，+5 积分/天；因此号池 N 个账号约等于每天 5N 张图的稳定产能。</p>');
  h.push('<p>· 注意：24 小时冷却只限制「签到」，不限制「生图」——新注册的账号凭 1 积分可以立即生图（已实测）。若某个新生号生图被上游拒绝，工具会提示剩余冷却时间并自动切换其他账号。</p>');
  h.push('<p>· 站内老虎机为娱乐玩法，理论返还率 95.88%（负期望），本工具不对其进行自动化，避免把积分赌没。</p>');
  h.push('<h3>5. 号池怎么用（kmage）</h3>');
  h.push('<p>· 右上角齿轮按钮 →「设置」选项卡 → kmage 通道选项分区：点"注册新账号"或批量注册，工具会自动完成注册、创建 API Key、记录会话；全部数据只保存在浏览器 localStorage 中。</p>');
  h.push('<p>· 每天打开页面时（或手动点"批量签到"），工具会自动为满足条件的账号签到。"待激活"状态的账号要等注册满 24 小时才会开放签到。</p>');
  h.push('<p>· 生成时按轮换策略选号：积分优先（most-credits）或轮询均衡（round-robin）。遇 402（积分不足）自动换下一个号；401（会话失效）自动重登并重建 Key；429 限流退避重试；5xx 网关错误自动同号重试一次再换号重试一次。</p>');
  h.push('<h3>6. 设置分区与迁移（JSON 导入/导出）</h3>');
  h.push('<p>· 设置面板分为「通用选项 / kmage 通道选项 / kdr 通道选项」三个分区，全部常驻显示——当前选中 kmage 时也可以直接调整 kdr 专属选项（反之亦然），各选项只作用于对应通道。</p>');
  h.push('<p>· 「导出号池」：仅 kmage 账号列表（含邮箱密码、会话与 API Key）。</p>');
  h.push('<p>· 「导出全部设置」：一份 JSON 打包 kmage 号池与全部设置项（含界面主题）+ kdr 自定义 Key 与共享 Key 缓存 + 通知开关 + 当前通道，用于跨浏览器/跨设备完整迁移。</p>');
  h.push('<p>· 「导入设置」自动识别格式（设置包 / 旧版号池 / 裸账号数组）；缺会话的账号导入后自动重登恢复。导出文件含明文凭据，请妥善保管。</p>');
  h.push('<h3>7. 任务历史与回看（v1.3）</h3>');
  h.push('<p>· 结果卡片下方「近期任务」记录每次生成任务——成功与失败都入册（含被页面刷新中断的任务，启动时自动标记）。成功条目保存本地预览缩略图（canvas 生成，长边 160px）与元数据；点击任意条目即可回看，失败条目点击显示失败原因。</p>');
  h.push('<p>· 回看优先级：本次会话内存原图 → kdr 上游下载地址（在线加载原图）→ 本地缩略图。实测 kmage 上游 API 仅返回图片数据本身（response_format=url 也只回 data URI，无持久 CDN 地址），因此 kmage 历史在别的设备上回看的是缩略图；kdr 任务结果自带上游 URL，历史导出后在任何设备都能在线回看上游存储的原图。</p>');
  h.push('<p>· 「导出」按钮生成 ai-image-history JSON（全部条目，含缩略图与上游地址）；「导入」按运行号自动合并去重。历史持久化于 localStorage 的 kmage_hist_v1（上限 40 条；容量不足时自动剥离缩略图保存）。</p>');
  h.push('<h3>8. 运行控制台</h3>');
  h.push('<p>右上角齿轮按钮 →「控制台」选项卡。每次生图以运行号（R+时间戳）分组记录：通道、账号/Key 选择、请求参数、上游状态码与耗时、错误响应摘要（含非 JSON 响应原文截断）、换号/重试决策。支持导出全部/本次运行（.txt，含版本、通道、UA、页面地址）、一键复制、只看错误、清空；日志持久化到 localStorage，刷新不丢。</p>');
  h.push('<h3>9. 架构与端点</h3>');
  h.push('<pre>/            页面（HTML+CSS+JS 全内嵌，无外部资源）'+String.fromCharCode(10)+'/healthz     健康检查（版本/上游/通道/时间）'+String.fromCharCode(10)+'/about       服务自描述 JSON（AI Agent 排障入口，含真实上游，v1.5 直连地址来源）'+String.fromCharCode(10)+'/api/kmage/* -> kmage 上游 /api/*   会话类代理（注册/登录/签到/Key/额度，v1.5 仍走代理）'+String.fromCharCode(10)+'/kmage/v1/*  -> kmage 上游 /v1/*    Bearer 透传（v1.5 起为直连失败时的自动回退）'+String.fromCharCode(10)+'/api/kdr/*   -> kdr 上游 /api/*     透明转发（v1.5 起为直连失败时的自动回退）'+String.fromCharCode(10)+'/kdr/img     kdr 结果图拉取代理（v1.5 起为直连图床失败时的回退）'+String.fromCharCode(10)+'v1.5 直连优先: 生图类请求由浏览器直连上游（住宅 IP + 真实 UA，地址自 /about 获取），网络失败自动回退本 Worker 代理；2026-09-23 起上游拉黑数据中心出口 IP，代理路径仅作兜底</pre>');
  h.push('<h3>10. 数据模型（localStorage）</h3>');
  h.push('<pre>kmage_state_v1   accounts[]: {email,password,session,apiKey,apiKeyId,apiKeyHint,'+String.fromCharCode(10)+'                 credits,lastCheckinDay,eligibleAt,createdAt,disabled,lastError}'+String.fromCharCode(10)+'                 abandoned[]: 已删除/归档账号'+String.fromCharCode(10)+'                 settings: {rotationStrategy,autoRegister,autoCheckin,'+String.fromCharCode(10)+'                 emailDomain,notificationsEnabled,theme}'+String.fromCharCode(10)+'kdr_state_v1     customKeys[]: 自定义付费 Key（可选）'+String.fromCharCode(10)+'                 gift: {key,alias,ts} 共享 Gift Key 缓存（10 分钟）'+String.fromCharCode(10)+'kmage_channel_v1 当前通道（kmage | kdr，默认 kmage）'+String.fromCharCode(10)+'kmage_hist_v1    任务历史（≤40 条；成功条目: {ts,run,channel,prompt,model,size,quality,'+String.fromCharCode(10)+'                 account,status,error,ms,thumb,url}，失败条目同构无 thumb/url）'+String.fromCharCode(10)+'kmage_form_v1    创作面板选项记忆: {prompt,ratio,quality,kdrSize,model:{kmage,kdr}}'+String.fromCharCode(10)+'kmage_logs_v1    运行日志环形缓冲（最近 300 条，detail 截断 300 字符）</pre>');
  h.push('<h3>11. 反模式化原则（沿袭马良 v27.2）</h3>');
  h.push('<p>· 邮箱：姓名/形容词/名词词库 × 6 种模式 × 随机大小写，无固定前缀与时间戳指纹。</p>');
  h.push('<p>· 密码：12~15 位完全随机强密码，无固定后缀；API Key 备注名从词池随机。</p>');
  h.push('<p>· 节奏：批量注册间隔 2.5~8s 随机（15% 概率再 +4s），批量签到乱序 + 0.8~2.8s 随机间隔；登录/刷新等操作带随机抖动。</p>');
  h.push('<p>· UA：Worker 端透传访客浏览器真实 UA（缺失时从 4 个常见池随机），不做 IP 伪造（马良 v26.1 已证实无效且移除）。</p>');
  h.push('<h3>12. 排障指引（AI Agent 适用）</h3>');
  h.push('<p>① GET /about 确认版本、通道端点与真实上游；② 打开「控制台」导出日志，定位首个非 2xx 上游请求（日志带 [kmage]/[kdr] 前缀并标注「直连/代理」路径）；③ kmage 常见错误：401 会话/Key 失效（自动重登重建）、402 积分不足（自动换号）、429 限流（5s 退避）、5xx 网关错误（4s 后同号+换号重试，失败自动返还积分）、180s 超时、403 account_environment_abnormal（2026-09-13 首现于数据中心 IP 直连注册的未满 24h 新号；2026-09-23 起扩大到所有数据中心出口 IP 的生图请求，Worker 代理路径亦被拒「账号使用环境异常，充值后解锁」——v1.5 起生图由浏览器直连上游，若仍被拒请更换网络环境后重试，新生号 403/400 仍自动换号）；④ kdr 常见错误：401/403 Key 被拒（自动刷新共享 Key 重试）、403「此 IP 已被加入免费 Key 黑名单」（2026-09-23 起上游拉黑数据中心出口 IP 的免费 Key 使用——v1.5 起浏览器直连后仅当访客自身 IP 被拉黑时出现）、404 任务失效、轮询超时 180s（免费通道不扣费）；⑤ 号池/设置可导出 JSON 离线分析；⑥ 上游探活：kmage 站点直接访问首页（注册无验证码，签到接口账号未满 24h 返回 403）；kdr 站点 GET /api/gift-key 应返回 key/alias。</p>');
  h.push('<h3>13. 项目迭代时间线（按实际日期正序）</h3>');
  h.push('<div class="tl">');
  h.push('<div class="ti"><span class="td">2026-07 上旬前</span><span class="tc"><b>马良渠道 v0.x → v27.2</b>：项目起点，免费生图首条路线（上游「马良」站点）。本地迭代 27+ 版：号池轮换、水印模块、浏览器通知等能力成形，「拟人化凭据 / 随机化节奏 / UA 透传 / 不做 IP 伪造」等反模式化原则在此确立。后上游加 challenge 墙，服务端不可用，通道终止。</span></div>');
  h.push('<div class="ti"><span class="td">2026-07-22</span><span class="tc"><b>kd v1.0 → v1.2</b>：接入 Keydraw（V2EX 公开 Gift Key 模式）。v1.0 多通道架构（KeyDraw + 马良，自动故障切换）；v1.1 性能精简；v1.2 上游错误透传、自定义付费 Key 通道，马良标记下线。</span></div>');
  h.push('<div class="ti"><span class="td">2026-07-23</span><span class="tc"><b>kd-v2.0 → v2.2</b>：收敛为单一 KeyDraw 通道；日额度本地计数徽章（GMT+8 零点重置）；更名「AI生图」；修复设置面板函数误删与模板字符串换行转义坑。</span></div>');
  h.push('<div class="ti"><span class="td">2026-07 下旬～08</span><span class="tc"><b>SQ / PM 路线试错</b>：Squido（人机验证阻断，KV+Cron 保活原型未走通）、Pixmind（登录接口 500，双 Worker 半自动方案止步）。<b>2026-08-19 复核结论</b>：当时无「免登录、免人机验证、可第三方代理、明确免费额度」的合格上游，未发版。</span></div>');
  h.push('<div class="ti"><span class="td">2026-09 上旬</span><span class="tc"><b>kdr 通道瘫死</b>：kdr 上游改版（Draw Studio），生成 API 契约变化——key 与 host 必须放入请求 body（host 由 /api/channels 下发），旧版 Authorization 头方式全部 400「请求地址只能选择…」，共享 Gift Key 本身仍有效。</span></div>');
  h.push('<div class="ti"><span class="td">2026-09-13</span><span class="tc"><b>kmage-v1.0 上线</b>：选定「kmage 站点」为新上游（官方 OpenAI 兼容 API、注册无验证码、签到 +5 分/天、失败返还）。号池模式全套（自动注册/批量签到/补建 Key/401 重登/402 换号/429 退避），同位替换瘫死的 kdr。</span></div>');
  h.push('<div class="ti"><span class="td">2026-09-13</span><span class="tc"><b>kmage-1.1</b>：运行日志控制台（分组/导出/复制/持久化）、号池 JSON 导入导出、浏览器原生通知、24h 规则明确化（仅限签到）、反模式化（拟人凭据/随机节奏/UA 透传）、内嵌自包含文档与 /about；修复日志原文丢失问题（resp.json() 消费 body 后取不到原文，改先读全文再 parse）。同日补丁：用户实测图生图偶发 504（大请求体），增加 5xx 同号+换号自动重试。</span></div>');
  h.push('<div class="ti"><span class="td">2026-09-13</span><span class="tc"><b>kmage-kdr-1.2</b>：kdr 通道修复复活（适配 key/host 入 body 新契约、任务轮询、结果图代理转存，免费 Gift Key 实测可出图）；header 通道选择器（默认 kmage）；UI 重构——footer 移除，「号池」→「设置」、「日志」→「控制台」、「文档」+「帮助」合并为「关于」，均改线条 SVG 图标；新增画笔颜料盘 favicon 与「ai」字母组合 logo；设置级 JSON 导入导出（号池+全部设置项）；对外文档源站脱敏（以「kmage 站点 / kdr 站点」表述）；本文档整合马良至今完整时间线；工程坑防守——内嵌模板字符串内禁止反斜杠转义序列（含正则），换行统一 String.fromCharCode(10)，静态检查强制（kd-v2.2 换行转义坑重演拦截）。</span></div>');
  h.push('<div class="ti"><span class="td">2026-09-13</span><span class="tc"><b>kmage-kdr-1.3</b>：竖屏手机适配——窄屏下设置/控制台/关于合并为单菜单按钮+选项卡浮窗（面板节点搬运复用，无重复 ID），版本号收进标题下方堆叠，触控目标、弹窗高度与历史列表换行按移动端优化；深色模式——CSS 全量变量化，设置内可选跟随系统/浅色/深色，跟随系统时实时感应系统切换；任务历史持久化——成功/失败/中断均入册，成功条目存 canvas 缩略图与 kdr 上游下载地址，点击回看，支持 ai-image-history JSON 导出/导入跨设备回看；图标修正——设置按钮太阳改齿轮，header 与关于页 logo 换为画笔+颜料盘（与 favicon 同款）；排障新知——上游对直连数据中心 IP 的新生号返回 403 环境异常风控（Worker 代理路径正常）。</span></div>');
  h.push('<div class="ti"><span class="td">2026-09-13</span><span class="tc"><b>kmage-kdr-1.4</b>：导航统一——全宽度右上角仅保留一个齿轮按钮，点开浮窗以选项卡切换设置/控制台/关于，桌面三按钮与窄屏汉堡按钮的双轨实现移除（面板 DOM 收敛为隐藏宿主 + 搬运复用，代码精简）；设置分区——「通用选项 / kmage 通道选项 / kdr 通道选项」三区常驻，选中任一通道均可直接调整另一通道的专属选项；创作面板记忆——模型（按通道分存）/比例/精细度/分辨率档/提示词存 kmage_form_v1，下次打开自动恢复；PWA 化——manifest + Service Worker + PNG 图标（白底圆角矩形叠加画笔颜料盘 logo），应用名「AI生图」，standalone 模式保留系统标题栏，设置 → 通用选项提供「安装到系统」按钮。</span></div>');
  h.push('<div class="ti"><span class="td">2026-09-23</span><span class="tc"><b>kmage-kdr-1.5（本版）</b>：直连优先修复双通道风控拦截——2026-09-23 起 kdr 上游将 Cloudflare Worker 出口 IP 段列入免费 Key 黑名单（生成报「此 IP 已被加入免费 Key 黑名单」），kmage 上游将生图环境风控扩大到所有数据中心出口 IP（报「账号使用环境异常，充值后解锁」），两通道经 Worker 代理的生图全部被拒；实测两上游均开放 CORS（Access-Control-Allow-Origin: *），故 v1.5 将生图类请求改由访客浏览器直连上游（住宅 IP + 真实 UA，即上游期望的正常使用环境），Worker 代理降级为直连网络失败时的自动回退；直连地址运行时经 GET /about 自描述接口获取（脱敏原则不变，上游域名不写入页面静态文本）；kmage 会话类操作（Cookie 会话，无法跨域携带）不受风控影响仍走代理；kdr 结果图优先浏览器直连图床（实测不校验 Referer）失败回退 /kdr/img 代理；控制台日志对每次请求标注「直连/代理」路径与回退事件。</span></div>');
  h.push('</div>');
  h.push('<h3>14. 边界说明</h3>');
  h.push('<p>· 会话与密钥为本工具对注册账号的自身凭据管理，不涉及破解或绕过任何验证；请遵守上游站点服务条款，控制用量，避免滥用免费产能。</p>');
  h.push('<p>· 邀请奖励需被邀请人首次充值后才到账，不属于免费路径，工具不做链式邀请。kdr 通道自定义 Key 为用户自购的付费凭据，工具仅代为填用。</p>');
  h.push('<hr>');
  h.push('<p style="color:var(--text-muted)">本页 HTML 头部注释含 AI Agent 排障提示；本弹窗内容与 /about、/healthz 共同构成自包含说明文档。</p>');
  return h.join('');
}
function renderDocs(){$('docsBody').innerHTML=ABOUT_HTML()}

// ---------- hub 合并面板（v1.4 全宽度统一）：右上角单齿轮按钮 + 选项卡 ----------
// 三个功能面板（设置/控制台/关于）的 body 节点按需搬进 hub 浮窗，关闭时搬回隐藏宿主，
// 保证同一节点全站唯一（无重复 ID），事件绑定随节点走。
var HUB_HOSTS=[['settings','poolBody','host-settings'],['console','logBody','host-console'],['about','docsHost','host-about']];
function movePanels(toHub){
  for(var i=0;i<HUB_HOSTS.length;i++){
    var host=$(HUB_HOSTS[i][1]);if(!host)continue;
    if(toHub){
      var pane=$('hubPane-'+HUB_HOSTS[i][0]);
      if(host.parentNode!==pane)pane.appendChild(host);
    }else{
      var dlg=$(HUB_HOSTS[i][2]);
      if(host.parentNode!==dlg)dlg.appendChild(host);
    }
  }
}
function switchHubTab(t){
  var tabs=$('hubTabs').children;
  for(var i=0;i<tabs.length;i++){tabs[i].className='hub-tab'+(tabs[i].getAttribute('data-hub')===t?' on':'')}
  for(var j=0;j<HUB_HOSTS.length;j++){
    $('hubPane-'+HUB_HOSTS[j][0]).style.display=(HUB_HOSTS[j][0]===t)?'':'none';
  }
  if(t==='console')renderLogBox();
  if(t==='about')renderDocs();
  if(t==='settings'){renderPool();renderGiftLine()}
}
function openHub(tab){
  movePanels(true);
  $('hubDialog').showModal();
  switchHubTab(tab||'settings');
}
function closeHub(){$('hubDialog').close()} // 面板归位由 'close' 事件统一处理
// ---------- 事件绑定 ----------
function bindPoolActions(){
  $('poolTbody').addEventListener('click',async function(ev){
    var t=ev.target.closest?ev.target.closest('button[data-act]'):null;
    if(!t)return;
    var i=parseInt(t.getAttribute('data-i'),10);var a=state.accounts[i];if(!a)return;
    var act=t.getAttribute('data-act');
    t.disabled=true;
    try{
      if(act==='checkin'){
        var r=await checkinAccount(a);
        if(r.done)toast('签到成功 +'+(r.reward||0)+' 分','success');
        else if(r.already)toast('今日已签到','info');
        else if(r.wait)toast('注册未满 24 小时，签到将于 '+fmtRemain(r.remainMs)+' 后开放（不影响生图）','info');
        else toast(r.msg||'签到失败','error');
      }else if(act==='refresh'){
        await refreshAccount(a);toast('额度已刷新','success');
      }else if(act==='toggle'){
        a.disabled=!a.disabled;saveState();
      }else if(act==='remove'){
        if(confirm('确定从号池删除该账号？（仅本地删除，不影响上游账号）')){
          state.abandoned.push(a);state.accounts.splice(i,1);saveState();
        }
      }
    }catch(e){toast(e.message,'error')}
    saveState();renderPool();renderBadge();
    t.disabled=false;
  });
}
function bindRefAdd(){
  var btn=$('refAdd');
  if(!btn)return;
  btn.addEventListener('click',function(){$('refInput').click()});
}
function bindAll(){
  $('channelSelect').addEventListener('change',function(){switchChannel($('channelSelect').value)});
  ['ratio','quality','kdrSize','model'].forEach(function(id){var el=$(id);if(el)el.addEventListener('change',saveFormState)});
  $('prompt').addEventListener('input',saveFormStateDebounced);
  window.addEventListener('beforeunload',saveFormState);
  $('btnGenerate').addEventListener('click',generate);
  $('btnDownload').addEventListener('click',downloadResult);
  $('navBtn').addEventListener('click',function(){openHub('settings')});
  $('hubDialog').addEventListener('close',function(){movePanels(false)});
  $('hubClose').addEventListener('click',closeHub);
  $('hubTabs').addEventListener('click',function(ev){
    var b=ev.target.closest?ev.target.closest('button[data-hub]'):null;
    if(b)switchHubTab(b.getAttribute('data-hub'));
  });
  $('btnExportHist').addEventListener('click',exportHist);
  $('btnImportHist').addEventListener('click',function(){$('importHistFile').click()});
  $('importHistFile').addEventListener('change',function(ev){
    var f=(ev.target.files||[])[0];
    if(f)f.text().then(importHistData).catch(function(e){toast('读取文件失败: '+e.message,'error')});
    ev.target.value='';
  });
  $('histList').addEventListener('click',function(ev){
    var li=ev.target.closest?ev.target.closest('li[data-hi]'):null;
    if(li)histReplay(parseInt(li.getAttribute('data-hi'),10));
  });
  $('themeSel').addEventListener('change',saveSettingsFromUI);
  $('btnExportLogAll').addEventListener('click',function(){exportLogs('all')});
  $('btnExportLogRun').addEventListener('click',function(){exportLogs('run')});
  $('btnCopyLog').addEventListener('click',copyLogsAll);
  $('btnClearLog').addEventListener('click',function(){
    if(!confirm('确定清空全部运行日志？（不影响号池数据）'))return;
    runLogs=[];try{localStorage.removeItem(LOG_KEY)}catch(e){}
    renderLogBox();toast('日志已清空','success');
  });
  $('logErrOnly').addEventListener('change',renderLogBox);
  $('btnExportPool').addEventListener('click',exportPool);
  $('btnExportSettings').addEventListener('click',exportSettingsAll);
  $('btnImportPool').addEventListener('click',function(){$('importPoolFile').click()});
  $('importPoolFile').addEventListener('change',function(ev){
    var f=(ev.target.files||[])[0];if(f)importPoolFile(f);ev.target.value='';
  });
  $('btnRefreshGift').addEventListener('click',async function(){
    var b=$('btnRefreshGift');b.disabled=true;
    try{await ensureGiftKey(true);toast('共享 Gift Key 已刷新','success')}catch(e){toast(e.message,'error')}
    b.disabled=false;renderGiftLine();
  });
  $('kdrCustomKeys').addEventListener('change',saveKdrSettingsFromUI);
  $('notifyChk').addEventListener('change',async function(){
    if($('notifyChk').checked){
      var ok=await requestNotificationPermission();
      if(!ok){$('notifyChk').checked=false}
    }
    saveSettingsFromUI();
  });
  $('btnRegister').addEventListener('click',async function(){
    var b=$('btnRegister');b.disabled=true;
    try{await registerAccount(false)}catch(e){toast(e.message,'error')}
    b.disabled=false;renderPool();
  });
  $('btnBatchRegister').addEventListener('click',async function(){
    var n=Math.max(1,Math.min(10,parseInt($('batchCount').value,10)||3));
    var b=$('btnBatchRegister');b.disabled=true;
    setStatus('poolStatus','批量注册中（0/'+n+'）…','info');
    var done=0;
    for(var i=0;i<n;i++){
      try{await registerAccount(true);done++}
      catch(e){toast(e.message,'error');break}
      setStatus('poolStatus','批量注册中（'+done+'/'+n+'）…','info');
      var gap=2500+Math.floor(Math.random()*5500);if(Math.random()<0.15)gap+=4000;
      await sleep(gap);
    }
    setStatus('poolStatus','批量注册完成: 成功 '+done+'/'+n,done===n?'ok':'warn');
    b.disabled=false;renderPool();renderBadge();
  });
  $('btnCheckinAll').addEventListener('click',async function(){
    var b=$('btnCheckinAll');b.disabled=true;setStatus('poolStatus','批量签到中…','info');
    await checkinAll(false);
    setStatus('poolStatus','批量签到完成','ok');
    b.disabled=false;
  });
  $('btnEnsureKeys').addEventListener('click',async function(){
    var b=$('btnEnsureKeys');b.disabled=true;
    await ensureKeysAll();b.disabled=false;
  });
  $('btnRefreshCredits').addEventListener('click',async function(){
    var b=$('btnRefreshCredits');b.disabled=true;setStatus('poolStatus','刷新额度中…','info');
    await refreshAllCredits();
    setStatus('poolStatus','额度刷新完成','ok');
    b.disabled=false;
  });
  $('btnArchiveDisabled').addEventListener('click',archiveDisabled);
  $('rotationStrategy').addEventListener('change',saveSettingsFromUI);
  $('emailDomain').addEventListener('change',saveSettingsFromUI);
  $('autoRegisterChk').addEventListener('change',saveSettingsFromUI);
  $('autoCheckinChk').addEventListener('change',saveSettingsFromUI);
  $('refInput').addEventListener('change',function(ev){
    var files=Array.prototype.slice.call(ev.target.files||[]);
    var room=10-refImages.length;
    files.slice(0,Math.max(0,room)).forEach(function(f){
      if(f.size>10*1024*1024){toast(f.name+' 超过 10MB，已跳过','error');return}
      var rd=new FileReader();
      rd.onload=function(){refImages.push(String(rd.result));renderRefs()};
      rd.readAsDataURL(f);
    });
    ev.target.value='';
  });
  $('refList').addEventListener('click',function(ev){
    var t=ev.target.closest?ev.target.closest('button[data-rm]'):null;
    if(t){var i=parseInt(t.getAttribute('data-rm'),10);refImages.splice(i,1);renderRefs()}
  });
}

// ---------- 启动 ----------
(async function init(){
  loadState();loadKdrState();loadChannel();loadLogs();loadHist();migrateLegacyKdrKeys();
  restoreFormState();
  applyTheme();bindThemeMedia();
  renderSettings();renderGiftLine();renderBadge();renderHist();renderRefs();bindAll();bindPoolActions();
  applyChannel();
  bindInstall();
  if('serviceWorker' in navigator){
    navigator.serviceWorker.register('/sw.js').then(function(){
      appLog('PWA: Service Worker 已注册','i');
    }).catch(function(e){appLog('PWA: Service Worker 注册失败 '+e.message,'w')});
  }
  appLog('页面加载完成（'+VERSION+'，通道 '+channel+'，主题 '+(state.settings.theme||'system')+'，日志 '+(runLogs.length)+' 条，历史 '+histItems.length+' 条已恢复）','i');
  // v1.5 直连优先: 启动时从 /about 获取上游真实地址（最多等 2s，不阻塞页面交互）；
  // 获取成功前若发起生图，会先走 Worker 代理（行为同 v1.4）
  try{await Promise.race([initDirect(),sleep(2000)])}catch(e){}
  // kdr 通道：预热共享 Gift Key（v1.5 起直连优先）
  if(channel==='kdr'){ensureGiftKey(true).then(function(){renderGiftLine()}).catch(function(){})}
  // 自动签到（kmage）：仅对今天尚未签到且已过激活时间的账号尝试一次
  if(state.settings.autoCheckin){
    setTimeout(async function(){
      try{
        var need=false;
        for(var i=0;i<state.accounts.length;i++){
          var a=state.accounts[i];
          if(!a.disabled&&a.session&&a.lastCheckinDay!==todayGmt8()){need=true;break}
        }
        if(need)await checkinAll(true);
        renderBadge();
      }catch(e){}
    },1200);
  }
})();
</script>
</body>
</html>`;
