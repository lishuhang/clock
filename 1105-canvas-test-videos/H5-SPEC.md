# H5-SPEC.md · 单镜 Canvas 页面接口规范（v1.0，2026-11-07）

> 本文档是**画面层与渲染管线之间的唯一契约**。任何模型（GLM/Kimi K3.1 等）按本规范产出的
> 单镜 HTML，都可以直接进入 `scripts/pipeline.py` 的 render → assemble 流程，无需改动任何
> 其他层。规范由 `scripts/h5_render_v4.py`（截帧器）与总装脚本共同强制执行。
>
> 参考实现：`04-ep1-production/canvas/S08.html`（推箱子，复杂动效）、
> `canvas/S05.html`（counter+stamp）、`canvas-ep2/`、`canvas-ep3/`（共 136 镜现成范例）。

---

## 0. 一句话总则

**页面是"一台被外部时钟驱动的画片机"**：管线调用 `renderFrame({t})`，页面把 t 秒时刻的画面
摆好，仅此而已。**页面自己永远不推进时间。**

## 1. 画布与舞台几何（硬性）

| 项 | 值 | 说明 |
|---|---|---|
| 页面尺寸 | **1080 × 1920**（9:16 竖屏） | `body{width:1080px;height:1920px;overflow:hidden}` |
| 4:3 安全框 | `#stage{position:absolute;top:555px;left:0;width:1080px;height:810px}` | **全部主体内容必须落在框内**（裁成 1080×810 横屏版时不丢内容）；纯装饰可出血（标 `data-deco`） |
| 主体内边距 | `#stage .inner{position:absolute;inset:14px 36px 22px 36px}` | 防贴边 |
| 背景层 | `#bg-layer{position:absolute;inset:0}` 铺满全屏 | 渐变/图片/视频均可 |
| 底色 | `#131110`（暗色系） | 与全片统一 |
| 品牌色 | `--brand:#fc8166; --brand-deep:#e55b46`；正文 `--ink:#312e2e` | 娱资品牌系 |

## 2. 技术栈（硬性）

- **纯 HTML + CSS + vanilla JS 单文件**：无构建步骤、无 import、无框架
- **零网络请求**：禁 CDN、禁 Google Fonts、禁外链图片——素材全部走本地相对路径
  （如 `../assets/logos/tapnow.png`、`../assets/bili/xxx.png`；字体 `../assets/fonts/alipuhui-*.ttf`）
- 字体声明（三字重本地 TTF）：
  ```css
  @font-face { font-family:"AliPuHui"; src:url("../assets/fonts/alipuhui-regular.ttf"); font-weight:400; }
  @font-face { font-family:"AliPuHui"; src:url("../assets/fonts/alipuhui-bold.ttf");     font-weight:700; }
  @font-face { font-family:"AliPuHui"; src:url("../assets/fonts/alipuhui-black.ttf");    font-weight:900; }
  body { font-family:"AliPuHui","Alibaba PuHuiTi","Noto Sans SC",sans-serif; }
  ```
- 命名放置：`canvas-ep{N}/S{编号}.html`（如 `canvas-ep2/S07.html`），与 shots JSON 的 `id` 一一对应

## 3. 受控时钟契约（核心，违反=废片）

### 3.1 必须实现 `window.renderFrame(payload)`

```js
window.renderFrame = function (p) {
  var dur = p.shot_dur || 10;   // 本镜总时长(秒)
  var t = p.t || 0;             // 镜内时刻(秒)，0 ≤ t ≤ dur
  if (p.hud !== undefined) { /* 按 p.hud 显隐 [data-hud] 元素 */ }
  // …按 t 设置所有元素的状态（进度/透明度/位移/计数）…
};
```

- 截帧器流程：加载页面 → 等 `document.fonts.ready` + 全部图片 `complete && naturalWidth>0`
  → 调 `renderFrame({t, shot_dur, hud:false, ...})` → 截图 → 下一个 t
- **禁止**：`requestAnimationFrame` 自驱播放、`setInterval/setTimeout` 驱动画面、
  CSS animation 无限循环、视频自动播放——一切"真实时间"驱动（沙盒掉帧=音画错位）
- 允许：CSS transition（由 renderFrame 改类/样式触发后瞬时落位不依赖等待）不适用，
  动效状态必须由 t 直接计算（`opacity = clamp((t - data-t)/data-d)`）
- HUD 元素全部标 `data-hud`（字幕预览/进度条/水印预览/章节角标），截帧时自动隐藏——
  **成品字幕、水印、进度条全部由 ffmpeg 后处理叠加，页面不做成品层**

### 3.2 必须声明采集窗口

```html
<script>
window.SHOOT_KEYS  = [0.15, 0.4, 2.7, 5.2];        // 关键帧时刻(信息性)
window.SHOOT_DENSE = [[0, 18.01, 12]];             // [t0, t1, fps] 连续高密度截帧窗
</script>
```

- 基础网格 2fps + 入场窗 1.5s@30fps 由截帧器自动加；**有连续动画的时段必须写进
  SHOOT_DENSE**（如整镜动效用 `[[0, dur, 12]]`），否则动画在成片里会卡成幻灯片
- 时刻值 ≤ 本镜 dur（来自 shots JSON），页面动效不得超出 dur

### 3.3 必须实现 `window.yzCheck()`

返回 `{status:"compliant"}` 或 `{status:"overflow", problems:[...]}`。最小实现：

```js
window.yzCheck = function () {
  var problems = [];
  var st = document.getElementById('stage').getBoundingClientRect();
  document.querySelectorAll('#el-stage *').forEach(function (el) {
    var r = el.getBoundingClientRect();
    if (r.width && r.height && (r.right > st.right + 2 || r.bottom > st.bottom + 2
        || r.left < st.left - 2)) {
      problems.push(el.tagName + ':' + (el.className || el.id) + ' 溢出安全框');
    }
  });
  return problems.length ? { status:'overflow', problems:problems }
                         : { status:'compliant' };
};
```

截帧器对每镜跑 yzCheck，**非 compliant 直接拒收该镜**（不截帧）。

## 4. 动效原语（模板自带，直接用 data- 属性）

| 属性 | 取值 | 语义 |
|---|---|---|
| `data-anim` | `pop / fade / up / stamp / wipe-in / wipe-out / typing` | 入场动效类型（renderFrame 按 t 计算） |
| `data-t` | 秒，或 `end-0.4`（镜末前 0.4s） | 入场起始时刻 |
| `data-d` | 秒（默认 0.5） | 动效时长 |
| `data-counter` | `"500,0,3.2,2"`=起点,终点,时长,小数位 | 数字滚动（配 `data-t`） |
| `data-ambient` | `float`（漂浮）/ `pulse`（呼吸） | 环境微动（amp 4-8 / sp≤0.32，相位错开防整齐划一） |
| `data-deco` | （无值） | 装饰元素，允许出血安全框 |

入场时刻 `data-t` 应跟台词读音对位（字幕卡 JSON 的分卡时间是依据）；复杂镜（如推箱子）
可在页面内包一层自己的 renderFrame 驱动逻辑（先存 `window._rf` 再包）。

## 5. 视频背景镜（透明页）

该镜若由 ffmpeg 叠加实拍视频做底（见 clips/MANIFEST.json 的 `used_by`）：

- `body` 与 `#bg-layer` 背景设为 `transparent`（截帧器自动检测 body 计算样式，
  以 `omit_background` 产出透明 PNG，总装时叠到视频上）
- 页面主体加半透明压暗层（scrim，如 `rgba(0,0,0,.78)`）保证文字可读

## 6. 素材引用

- 只用仓库已有素材：`../assets/logos/`（平台 logo，**平台名必须配官方 logo**）、
  `../assets/bili/`（截图证据）、`../assets/ep2|ep3/`（分集素材）、`../assets/shots/`
- 需要新素材：先确认 <20MB、切好片、登记 MANIFEST 再引用；**禁止引用网盘/外网 URL**
- 图片必须本地加载成功（截帧器等待 `naturalWidth>0`，8s 超时告警继续）

## 7. 文案与排版红线（来自历轮验收，违反=打回）

- 禁间隔号 `·` 作分隔/换行美化；禁思考性括注入画面；最小信息原则（不复述台词的胶囊）
- 正文字号 ≥28、标签 ≥24、logo 高 ≥78（网格）/84（单行）；字幕带 Y1435~1545 留空
  （成品字幕区，画面主体避让）
- 定格 ≤3s：静态画面必须有环境微动或分步入场；抽象概念必须动画化讲解
- 画面语义跟台词（镜头边界语义归属已在 shots JSON 定死，页面不得改变概念归属）

## 8. 交付与回接验收流程

```bash
# 1. 预览（浏览器人审，顺序播放全部镜头）
python3 -m http.server -d 1105-canvas-test-videos 8000   # 打开 http://localhost:8000/play.html
# 2. 单镜重截帧（只动这一镜）
python3 scripts/pipeline.py --ep 1 --only-shots S08 --steps render
# 3. 重组装（时间轴/字幕/音频零改动，G11 语义锚点+G13 像素锚点自动把关防回归）
python3 scripts/pipeline.py --ep 1 --steps assemble
```

验收硬指标：yzCheck compliant（截帧器强制）→ 该镜帧序列产出 → assemble 后 G1-G14 全 PASS。
