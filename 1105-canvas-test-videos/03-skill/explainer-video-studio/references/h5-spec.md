# H5 画面层接口规范（references/h5-spec.md · v2.3 新增）

> 本文档是解说视频管线中**画面层（单镜 canvas 页面）与渲染管线之间的唯一契约**。
> 作用：让"页面谁来做"变成可替换项——本 skill 的宿主模型、或任何外部模型（H5 能力更强的
> 第三方模型）只要按此契约交付单镜 HTML，即可无缝进入 render→assemble 流程，
> 不需要了解管线任何其他部分。
>
> 参考实现：1105 工程 `H5-SPEC.md`（含该项目 Profile 具体数值）+ 136 镜现成范例。

## 0. 一句话总则

**页面是"一台被外部时钟驱动的画片机"**：截帧器调 `renderFrame({t})`，页面把 t 秒时刻的画面
摆好。**页面自己永远不推进时间**（禁 rAF 自驱/无限 CSS 动画/setInterval 驱动画面）。

## 1. 硬性契约（截帧器强制执行，违反=拒收）

| # | 契约 | 强制方式 |
|---|---|---|
| 1 | 页面尺寸与舞台几何按项目 Profile（画布/安全框/字幕带数值以项目 README Profile 为准；skill 默认档案见 layout-spec.md §0） | yzCheck 溢出检测 |
| 2 | 纯 HTML+CSS+vanilla JS 单文件；**零网络请求**（禁 CDN/Google Fonts/外链图），素材走本地相对路径 | 截帧器图片加载等待超时即告警 |
| 3 | 字体 `@font-face` 本地 TTF；截帧前 `document.fonts.ready` | 渲染器内置 |
| 4 | 实现 `window.renderFrame({t, shot_dur, hud, subtitle, chapter, progress_pct, watermark})`——动效状态由 t 直接计算 | 无此函数=该镜 0 帧 |
| 5 | 实现 `window.yzCheck()`，返回 `{status:"compliant"}` 或问题清单 | 非 compliant 拒收该镜 |
| 6 | 声明 `window.SHOOT_DENSE=[[t0,t1,fps],...]`（连续动画窗，不声明动画会卡成幻灯片）；`SHOOT_KEYS` 信息性 | 渲染器解析 |
| 7 | HUD（字幕/水印/进度条预览）全标 `data-hud`——**成品字幕/水印/变速全部由 ffmpeg 后处理，页面不做成品层** | 截帧时隐藏 |
| 8 | 视频背景镜：body/#bg-layer 背景透明（渲染器自动检测 body 计算样式→omit_background 透明截帧），主体加 scrim 保证可读 | 渲染器自动检测 |
| 9 | 动效时刻 ≤ 本镜 dur（dur 来自 shots JSON）；入场 `data-t` 跟台词读音对位 | G11 语义锚点门禁 |
| 10 | 页面命名 `canvas*/S##.html`，与 shots JSON 的 `id` 一一对应 | 渲染器按表找页 |

## 2. 动效原语（模板 `assets/h5_templates/vertical_master.html` 自带）

| 属性 | 取值 | 语义 |
|---|---|---|
| `data-anim` | pop/fade/up/stamp/wipe-in/wipe-out/typing | 入场动效（renderFrame 按 t 计算） |
| `data-t` | 秒 或 `end-0.4` | 入场起始时刻 |
| `data-d` | 秒（默认 0.5） | 动效时长 |
| `data-counter` | "起点,终点,时长,小数位" | 数字滚动 |
| `data-ambient` | float/pulse | 环境微动（定格≤3s 铁律的解法） |
| `data-deco` | — | 装饰元素，允许出血安全框 |

新页面制作规矩：**复制母版只改 YZ_EDIT 区**（背景/主体两段注释块之间），
禁止自写整页 CSS（排版崩坏+文字溢出是弱模型最大翻车点）。

## 3. 交付与回接（换模型工作流）

```
给外部模型：本契约 + 项目 Profile 数值 + 1-2 个同项目现成镜做参考 + 该镜素材清单
收交付物：  单镜 HTML（yzCheck compliant + renderFrame 契约）
回接验收：  1) 预览器顺序人审（项目内 play.html，或逐镜浏览器打开）
           2) pipeline.py --only-shots S## --steps render   # 单镜重截帧
           3) pipeline.py --steps assemble                  # 重组装，G 门禁自动把关
红线：     H5 替换只动画面层；shots JSON（时间轴）/字幕权威卡/clips 切片一律不碰
```

## 4. 为什么契约长这样（防回归注记）

- 受控时钟而非实时录屏：沙盒高负载下 rAF 掉帧=音画错位（铁律 B7）。
- 拒收而非修复：yzCheck 在截帧前把关，坏页面不会污染帧库后才发现。
- 状态由 t 直接计算而非 transition 等待：截帧是无间隔跳时刻的，任何依赖"真实时间流逝"
  的动效在受控时钟下都会定格错误。
