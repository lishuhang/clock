# 1026-drama-sankey 工作日志

## 任务
用户给出《测试用提示词与加/扣分项》两张表 + 10 平台 favicon 素材（1014-drama-tests/drama-platforms-logos.zip），要求用娱资 infographic skill 的 A 工作流绘制桑基图：提示词在左、加/扣分项在右；四条全涉及的项用淡线且位于下层，部分涉及的加粗项醒目且位于上层；连线需清晰可辨；涉及平台列的平台名替换为 favicon、抽次标注（T1第1抽等）忽略、留空保持留空。使用新 GitHub token（261023-glm）工作。

## v1.0 工作记录（2026-10-26）

### 1. 环境恢复与素材获取
- 会话恢复后发现工作树被环境重置为 origin/main=9a777ed（恰为 "Create drama-platforms-logos.zip" 提交）；1014-drama-tests 未检出，经 `git cat-file blob` 从 git 对象提取 zip 解压，得到 12 个 favicon（含 flova/higgsfield 两个表中未涉及平台，未使用）。
- remote URL 已更新为新 token；fetch/pull 正常（远程新增 1020-feng-video 等 6 提交）。
- 读取 1019 问题清单（属上一项目 v1.1 意见），提炼可复用规范：标题语义断行、图例形状与主体一致、不丢视觉特性、不用难懂缩写。

### 2. 数据核对与裁定
- 两表逐项交叉核对 24 项 × 4 提示词矩阵，发现两处表间不一致：表1 的 T3 行漏列 C1、T2 行漏列 D2；表2 的"涉及提示词"列（C1=T3、T4；D2=T2、T4）与平台抽次记录（巨日禄 T3第3抽、Seko T2第2抽）互证一致 → 按表2裁定，T1/T2/T3/T4 连线数=18/18/20/19，合计 75。
- 正文"20个扣分项"与表2实为 22+2 出入，以表格为准并记录。
- 层级划分：四条均涉及 14 项→淡显下层；部分涉及 10 项→醒目上层。

### 3. 构建与渲染
- deliverables-v1.0/img1-styled.html：style-a 模板原样保留（模板 CSS、yzCheck 自检函数逐字未改），附加桑基样式与布局构建脚本（数据内嵌 → fonts.ready 后建 DOM → 量测 → 两层 SVG 贝塞尔连线：淡 7.5px 下层 / 醒 10px 上层，带宽按行序/T序累积，整图零交叉）。
- 左卡片含标题、类型标签、测试要点；右行为编号色块+名称+favicon（18px，CSS background 避开 yzCheck 的 img 计数）；加分项 B0/C0 用浅橙块+加分标签。
- render.mjs a 一次通过：900×1350 PNG，yzCheck=compliant；几何自检 faint=56/prom=19/无溢出。

### 4. 质检
- VLM 版式质检 6 项全过；连线数据抽查 8 项全过（D4 仅连 T1、C4 仅连 T3、E1 仅连 T2、A4 连 T1+T4、A1 四条淡线、B0/C0 淡线、E3 不连 T2、连线均锚定卡片边缘中部）。
- validate.py --mode a：compliant 13/13（敏感信息扫描为零）。
- source-data.csv 116 行（4+24+75+10+3）行级溯源，C1/D2 裁定与佐证写入 notes。

### 5. 交付与推送
- deliverables-v1.0/：img1-styled.html/png + source-data.csv + README + 双验证报告 + assets（字体/logo/favicons×10）。
- 单次 commit + push（新 token）。

## 状态
v1.0 完成。

---
## img2 · 测试用提示词调整 对比图（2026-10-27）

### 1. 任务
用户下达本批次第二张图：《测试用提示词调整》表（4 行 T1–T4 × 调整前（第1抽）/调整后（2~4抽）/参考图音频的调整 三列），继续用 skill-A 工作流制作。

### 2. 设计
- 版式：900×1350（A 上限宽高比内）；标题《测试用提示词调整》；4 个提示词区块，每块行头（T 码+片名+类型标签）+ 三列对比格。
- 视觉分层（调色板内）：调整前=灰底左灰条；调整后=浅橙红底左深橙条（最醒目）；参考资产=白底描边左浅橙条；三列列头即原表列名。
- 内容口径：逐格提炼要点 35 条，保留全部事实（平台家数 7家/6平台/3家/2家/2家、@图3/7/9/10/17/18/19/20/21/22、@音频1/2、图数变化 4→2+1 / 6→3+1 / 11→9+1 / 19→16+1、替换前后措辞）；特殊符号 →⤴↗↙⊕° 按原文保留。

### 3. 构建与渲染
- deliverables-v1.0/img2-styled.html：模板区与 img1 逐字一致（含 yzCheck），附加三列样式 + 溢出自检脚本 window.__yzAdjust（溢出时一次性启用 compact，修掉了初版的无限递归 bug）。
- render.mjs a 一次通过：rc=0，yzCheck=compliant（browser-validation-img2.json）。
- 自检数据：containerH=scrollH=1350 无溢出；行高 216/216/236/236；末行距页脚 34px；compact 未启用；liCount=35。

### 4. 质检
- PIL：900×1350 RGB，色彩 4702，着墨率 36.6%。
- VLM 版式质检 7/7 过（含特殊符号无 tofu）；VLM 数据忠实性抽查 7/7 过。
- validate.py --mode a 目录级（img1+img2）：compliant 22/22。
- source-data.csv 追加 13 行（12 格+口径行）→ 129 行，无重复，img1 116 行原样。

### 5. 交付与推送
- deliverables-v1.0/ 新增 img2-styled.html/png、browser-validation-img2.json，更新 source-data.csv/README/validation.json。
- 单次 commit + push。

## 状态
v1.0（img1+img2）完成。

---
## img3 · 剧情介绍 表格流程图（2026-10-27）

### 1. 任务
用户指出 img1 只用了"测试要点"列、未呈现剧情，要求单独摘出原表一"剧情"列，做 | 编号 | 提示词名称 | 简介 | 三列表格 + 向下箭头流程串联，标题【剧情介绍】，脚注【资料来源：娱乐资本论整理】。

### 2. 设计
- 900×1080：表头三列（编号96px/提示词名称216px/简介自适应）；4 个行卡片（浅灰底圆角），T1→T2→T3→T4 之间 3 个向下箭头↓（对齐编号列，27px 橙红 900）。
- 简介列逐字引用剧情原文（69/67/61/59 字，含「」引号！等全部标点，零缩略零改写）。

### 3. 构建与渲染
- 模板区与 img1/img2 逐字一致；附加表格流程样式 + __yzFlow 溢出自检（一次性 compact）。
- 初版底部余 105px 空隙（.chart-body 未设 flex）→ 修复后节奏均匀，末行距页脚 34px。
- render.mjs a 一次通过：rc=0，yzCheck compliant；4×115px 行高无溢出。

### 4. 质检
- PIL：900×1080、3133 色、着墨 38.5%。
- VLM 版式 7/7 过（含↓正常显示无 tofu）。
- 剧情逐字校验：VLM 3x 放大转写 + 程序化逐字比对，四段与原文完全一致（首轮全图转写 6 处差异确认系 VLM 误读 16px 小字，非渲染问题）。
- validate.py 目录级（img1+img2+img3）：compliant 31/31。
- source-data.csv 追加 5 行（4 剧情+口径）→ 134 行无重复。

### 5. 交付与推送
- deliverables-v1.0/ 新增 img3-styled.html/png、browser-validation-img3.json，更新 source-data.csv/README/validation.json。
- 单次 commit + push。

## 状态
v1.0（img1+img2+img3）完成。

---
## img4 · 模型缩水：2.5 还是 2.0 还是 Lite？ 扣分对比表（2026-10-27）

### 1. 任务
用户提供《模型缩水》平台扣分表（10平台×8列），要求"不自我发挥，用我的输入来生成"：逐字引用全部单元格、图例、排序说明；扣分相同按拼音排序；页脚含"数据截至2026年10月23日"。

### 2. 排障记录（本次关键事件）
- 首次渲染失败：assets 字体/logo 缺失 → 根因为昨日 img3 推送时的 stash→rebase→pop 触发 sparse-checkout 剪除 1026 目录未修改文件 → `git sparse-checkout add 1026-drama-sankey` 修复并永久纳入 cone。
- 渲染通过后发现坐标验证全偏：DOM 量测（getBoundingClientRect）与 PNG 实际绘制不一致 → 多轮像素扫描+VLM 裁图定位判定：**Chromium 对含 writing-mode 竖排单元格的 table-layout:auto 表格，计算布局与绘制分裂**（A3 竖排表头绘制丢失、A5 表头截断、行高错位）。
- 修复：`table-layout:fixed` + colgroup 定宽 + 表格自然高度垂直居中（弃 height:100% 拉伸）→ DOM 与绘制完全一致（平台列10文字带逐一落入10行DOM矩形）。

### 3. 构建与渲染
- 900×1350：标题（68px Black 两行）+ 图例行 + 排序说明 + 8列fixed表格（平台92/扣分56/A1-54/A2-40/A3-52/A4-148/A5-148/备注-166）+ 页脚两行来源。
- A1-A5 竖排表头（writing-mode:vertical-rl，<b>码</b>+列名分段）；扣分组间加重分隔线；偶数行斑马纹；●橙红/△灰。
- render.mjs a 通过：rc=0，yzCheck compliant；__yzTable 无溢出。

### 4. 质检
- PIL：900×1350、3334 色、着墨 8.4%。
- VLM 整图版式 7/7 过（含竖排表头完整无截断、垂直居中留白均衡）。
- 逐字校验：竖排表头5列全文 + 17个内容格（A5全10格、A4长文本×2、备注、平台名、扣分、A1含两个15.1s）全部与用户输入零差异；A3全角括号无tofu。
- 排序核对：1分组 L<S<X、不扣分组 A<J<N<O<S<T<W 与用户行序一致。
- validate.py 目录级（img1-img4）：compliant 40/40；CSV 145行无重复。

### 5. 交付与推送
- deliverables-v1.0/ 新增 img4-styled.html/png、browser-validation-img4.json，更新 source-data.csv/README/validation.json。
- 单次 commit + push。

## 状态
v1.0（img1+img2+img3+img4）完成。

---
## img4 修订 · 表头竖排→横排（2026-10-27）

### 1. 任务
用户 IM 指示：表格标题栏（第一列起）竖排文字改横排。落地为 A1–A5 五列表头全部由 writing-mode 竖排改为横排（窄列内自动换行、居中），表头文字逐字不变，表体数据/图例/排序/脚注零改动。

### 2. 修改
- `.vh`（vertical-rl）→ `.ah`（horizontal-tb，13px，word-break:break-all 安全换行，居中）；`<b>A1</b><br>列名` → `<b>A1</b> 列名`（保留码前缀粗体橙）。
- colgroup 重排：92/54/56/56/70/130/134/164（原 92/56/54/40/52/148/148/166），总和 756 不变；compact 样式同步替换。
- 仅动表头与列宽，模板区与 yzCheck 脚本零改动。

### 3. 验证
- render.mjs a 重渲：rc=0，yzCheck compliant。
- 自检量测（/home/z/my-project/scripts/img4-revision-check.cjs）：无溢出（scrollH=1350=containerH）、theadH 88px、表头 8 格 computed writing-mode 全为 horizontal-tb、无单元格横向溢出；行高 70/88/69/86/53×6，gapToFooter 114px。
- PIL：900×1350、3332 色、着墨 7.4%。
- VLM 三轮：表头 3x 转写 8 格逐字一致 + 确认"每字横排多行堆叠"；表体 2x 逐行转写 10 行数据一致；AniShort 备注 2x 误读"保留"经 4x 复核为"停留"无误（渲染正确）。无 tofu。
- source-data.csv：img4,4,11 备注更新（竖排→横排）+ 追加 img4,4,12 修订溯源行 → 147 行。
- validate.py 目录级复跑：compliant 40/40。

### 4. 交付
- 更新 img4-styled.html/png、browser-validation-img4.json、source-data.csv、validation.json、README。
- 单次 commit + push（先 fetch 确认远端无新提交）。

---
## img4 修订2 · A1–A5 等宽 + 备注稍窄（2026-10-27）

### 1. 任务（含长期规则）
用户 IM 指示：A1–A5 几列等宽、最右备注一列稍窄、不用介意单元格高度；**后续图同此要求（不改 skill，规则记于此处与 README 沿用）**。

### 2. 修改
- colgroup：92/54/56/56/70/130/134/164 → **92/54/104/104/104/104/104/90**（总宽 756 不变，仅动 colgroup 一行，HTML 其他零改动）。

### 3. 验证
- render.mjs a：rc=0，yzCheck compliant；无溢出（scrollH=1350，未触发 compact，gapToFooter 75px）。
- 程序化量测：列宽 [92,54,104×5,90] 精确生效；全表 td/th 零横向溢出；行高 53–123px 不齐（窄列换行，用户明示接受）。
- PIL：900×1350、2687 色、着墨 7.3%。
- VLM：表头 3x 确认 A1–A5 等宽、备注稍窄，8 格逐字一致；表体 2x 十行转写一致无 tofu（LibTV 行 VLM 列归属错位经 **DOM 80 格程序化逐字比对闭环：0 差异**，A4=△乱码、A5=●积分/-退点列义正确）。
- source-data.csv 追加 img4,4,13 修订溯源行 → 148 行；validate.py 目录级 40/40。

### 4. 交付
- 更新 img4-styled.html/png、browser-validation-img4.json、source-data.csv、validation.json、README（新增"列宽规则"长期要求条目）。
- 单次 commit + push。

---
## img4 修订3 · 数据修订（用户五条指示，2026-10-27）

### 1. 任务
用户 IM 指示五条数据修改：①所有平台均不扣分；②LibTV A5 改"即时退点"、备注写"平台标称为2小时内退还"；③删除两个平台文字错误表述（ShotLab/小云雀 A4 乱码，排查后为幻觉）；④A5 括号内容拿出不写"-"（-（即时退点）→即时退点、-（失败未扣点）→失败未扣点），小云雀与 AniShort 改"未出现抽卡失败"；⑤平台恢复按拼音排序。

### 2. 修改
- tbody 10 行重写：纯拼音序 AniShort<巨日禄<LibTV<纳逗Pro<OiiOii<Seko<ShotLab<TapNow<万兴剧厂<小云雀（A<J<L<N<O<Se<Sh<T<W<X）；扣分列全"-"；A4 全"-"；A5/A1/备注按上述口径；去除 grp-end 分组线与 ●△ 符号 span（表中已无对应符号）。
- 图例行、排序说明、表头、脚注、列宽规则（92/54/104×5/90）零改动。

### 3. 验证
- render.mjs a：rc=0，yzCheck compliant；无溢出（scrollH=1350，gapToFooter 121px，未触发 compact）。
- DOM 80 格与用户五条修订后的基准程序化逐格比对：**0 差异**；列宽 [92,54,104×5,90] 保持；全表零横向溢出。
- PIL：900×1350、2551 色、着墨 7.2%。
- VLM 表体 2x 逐行转写 10 行与修订指示完全一致（扣分全-/A4 全-/行序正确）；整图版式要素齐全、垂直居中无缺陷；无 tofu。
- source-data.csv 追加 img4,4,13→14 修订溯源行 → 149 行；validate.py 目录级 40/40。

### 4. 交付
- 更新 img4-styled.html/png、browser-validation-img4.json、source-data.csv、validation.json、README。
- 单次 commit + push。

---
## img4 修订4 · 画幅拉宽 + 字号统一 + 新标题（2026-10-27）

### 1. 任务
用户 IM 指示四条：①画幅适度拉宽；②最小字体放大到与脚注一样大；③标题大小不变、不折行、改为【实测未检出平台疑似"模型缩水"】。

### 2. 合规路径（关键决策）
- SKILL.md 第 12 行优先级条款："用户对当前项目的明确要求 > 本文件 > HTML 模板"——用户明确要求拉宽画幅构成官方例外。
- 画布 900×1350 → **1200×1500**（宽高比 1:1.5 → 1:1.25，"适度拉宽"）；CSS 覆盖方式（附加样式区 .chart-container{width:1200px;height:1500px}，模板文本零改动）。
- yzCheck 宽度常量 900→1200 同步（检查逻辑保留，仅常量更新）；OVERRIDE 记录写入 overrides.txt（SKILL.md 第 148 行纯文本例外格式）。
- 拉宽的直接动因：新标题 15 字 @68px ≈ 998px，900 画布可用宽 756px 放不下单行；1200 画布可用 1056px ✓。

### 3. 字号统一（用户"最小字体=脚注大小"）
- 图例 15px、排序说明 13.5px、表头 13px、表体 13-16px → **全部 26px**（=脚注 chart-source 26px 锚点）；标题 68px 层级不变。
- 程序化核对 12 个选择器 computed fontSize 全部 26px。
- compact 样式改为仅压缩内边距、绝不缩字号（保 26px 底线）。

### 4. 布局
- colgroup 重排：125/96/137×5/150（A1–A5 等宽规则保持，备注稍窄；总宽 1056=1200-144）。
- 自检：画布 1200×1500、标题单行 h=76px、无溢出（scrollH=1500=containerH、compact 未触发、gapToFooter 35px）、全表零横向溢出；行高 65-209px 不齐（用户接受）。

### 5. 验证
- render.mjs a：rc=0，yzCheck compliant（宽度检查已同步 1200）。
- DOM 80 格逐字零差异；VLM 标题区 2x（逐字一致+单行+图例清晰）、表体 2x 前 8 行逐行一致、末两行补裁 2x 逐字一致；无 tofu。
- PIL：1200×1500、2588 色、着墨 7.5%、宽高比 1:1.25。
- source-data.csv 追加修订4溯源行 → 150 行；validate.py 目录级 40/40。

### 6. 交付
- 更新 img4-styled.html/png、browser-validation-img4.json、source-data.csv、validation.json、README；新增 overrides.txt。
- 单次 commit + push。

---
## img5 · T1第一抽平台具体错误信息 两列表（2026-10-27）

### 1. 任务
用户下达本批次第五张图：《T1第一抽平台具体错误信息》表（7 平台 × 平台|信息 两列），逐字引用；脚注日期 2026年10月19日（与 img4 的 10月23日 不同，各自按输入保留）。

### 2. 设计决策
- 沿用 img4 修订4 用户已批准基线：1200 宽画布 + 26px 统一字号 + 68px 标题单行。直接动因：本图标题 13 字 @68px≈800px，900 画布可用宽 756px 无法单行（用户既定"标题不折行"）；OVERRIDE 记录于 overrides.txt（a.canvas-1200x1200-img5）。
- 高度按内容取 1200（宽高比 1:1）；列宽 平台 160 / 信息 896（总 1056=1200-144）；行序=用户输入原序（万兴剧厂居首，未做排序，用户输入未含排序说明则不加）；无图例（输入未含，零发挥）。
- 信息列长句 28 字 @26px=728px < 896 单行完整显示。

### 3. 构建与渲染
- 模板区与 img1-img4 逐字一致（含 yzCheck，宽度常量 1200 与 img4 修订4 相同无需再改）；附加 2 列 fixed 表格样式 + __yzTable 自检（新增 titleH/thW 字段）。
- render.mjs a 一次通过：rc=0，yzCheck compliant（browser-validation-img5.json）。

### 4. 质检
- img5-check.cjs（DOM 逐字比对）：标题/表头 2 格/表体 7×2 格/脚注与用户输入零差异（行序=原序）；字号全 26px（含脚注锚点）；列宽 [160,896] 精确生效；无溢出（scrollH=1200=containerH，compact 未触发，gapToFooter 89px）；标题单行 h=76px；行高 97-98px 均匀；全表零横向溢出。
- PIL：1200×1200、2781 色、着墨 7.3%、宽高比 1:1。
- VLM 双轮：表体 2x 逐行转写 7 行与用户输入逐字一致（含全角冒号/括号/逗号）；整图版式 7/7 过（标题单行、两列表头、7 行、脚注两行、横版 Logo、竖版水印、无截断/重叠/tofu、留白得体）。
- validate.py 目录级（img1-img5）：compliant 49/49；source-data.csv 追加 8 行（7 平台+图级口径）→ 158 行无重复。

### 5. 交付
- deliverables-v1.0/ 新增 img5-styled.html/png、browser-validation-img5.json，更新 source-data.csv/validation.json/README/overrides.txt。
- 单次 commit + push。

## 状态
v1.0（img1+img2+img3+img4+img5）完成。

---
Task ID: 7
Agent: main (Z.ai)
Task: skill-A 制作本批次第六张图《哪些因素影响了抽卡效率？》平台×B1-B4 扣分表（1026-drama-sankey img6）

Work Log:
- 会话恢复核对：git 状态干净（main 与 origin 同步于 4fd8aa8），deliverables-v1.0 已含 img1-img5；沿用 img4 修订4/img5 已批准基线（1200 宽+26px 统一字号+68px 标题单行）。
- 数据核对：用户输入 10 平台行；巨日禄扣分 1 置顶，扣分 0 组拼音序 A<L<N<O<Se<Sh<T<W<X 与用户行序一致（程序化核对）；图例/排序说明与 img4 同套逐字复用；脚注数据截至 2026年10月23日。
- 构建 img6-styled.html：模板区与 img5 逐字一致（含 yzCheck 1200 宽常量）；7 列 fixed 表格列宽 122/88/148/200/140/140/218（B2 与备注为长文本列稍宽）；B 列单元格内 ●/△ 符号沿用图例配色（●=深强调/△=次级，加粗）。
- 画布高度按内容定 1650（初设即命中）：render rc=0 yzCheck compliant 一次通过。
- 质检链全过：img6-check.cjs DOM 77 格（表头 7+表体 70）+标题+图例 3 项+排序说明+脚注逐字零差异、11 项选择器字号全 26px、列宽精确、无溢出、compact 未触发、gapToFooter 56、行高 [209,65,65,101,65,65,65,208,137,65]；PIL 1200×1650/2588 色/着墨 7.0%；VLM r1 全图逐字转写程序化比对全过 + r2 整图版式 7/7 无 tofu；validate.py 目录级 58/58。
- source-data.csv 追加 11 行（10 平台+图级口径）→ 169 行无重复；README/overrides.txt（img6 OVERRIDE 行）/双 worklog 同步。
- fetch 确认远端无新提交后单次 commit + push。

Stage Summary:
- 1026-drama-sankey v1.0 现含六张图：img1 桑基图 + img2 提示词调整对比 + img3 剧情介绍 + img4 模型缩水扣分表（1200×1500）+ img5 T1第一抽错误信息表（1200×1200）+ img6 抽卡效率影响因素扣分表（1200×1650）。
- 约定沿用确认：B 系列表头 B 码深橙加粗样式与 img4 A 列一致；●△ 符号在单元格内沿用图例配色，符号↔图例颜色一一对应。

---
Task ID: 8
Agent: main (Z.ai)
Task: skill-A 制作本批次第七张图《@类引用能否自动补全？》平台×B0主体库@引用智能补全与自动连线+T4填词耗时 两列表（1026-drama-sankey img8）

Work Log:
- 会话恢复核对：git 状态干净（main 与 origin 同步于 a50691b，img6 已交付）；skill 文件链全文重读（charts SKILL.md→_rules.md→playwright-css.md + yz-infographic v3.1 SKILL.md）。
- 用户随图重申口径：skill 原表格宽度限制可适当灵活拉宽、字体不要太小、最小字号=底部脚注大小 → 与 img4 修订4 已批准基线（1200 宽+26px 统一字号+68px 标题单行）完全一致，本图沿用并记 OVERRIDE（a.canvas-1200x1200-img8）。
- 数据核对：用户输入 10 平台行；行序=用户输入原序，两个同分组内拼音升序程序化核对一致（B0 净支持组 A<O<W<X；● 不支持组 J<L<N<Se<T；ShotLab 支持但带●可复现问题，单列于两组之间）；图例/排序说明与 img4/img6 同套逐字复用；脚注数据截至 2026年10月23日。
- 构建 img8-styled.html：模板区与 img6 逐字一致（含 yzCheck 1200 宽常量）；3 列 fixed 表格列宽 150/646/260（B0 为长文本列最宽，总宽 1056）；画布高度按内容定 1200（宽高比 1:1，同 img5）；B0 列 ● 符号沿用图例配色（深强调加粗）；T4 耗时值加粗居中（skill"Bold 700=数值"规范）。
- render.mjs a 一次通过：rc=0，yzCheck compliant（browser-validation-img8.json）。
- 质检链全过：img8-check.cjs DOM 40 格（表头 3+表体 30）+标题+图例 3 项+排序说明+脚注逐字零差异、9 项选择器字号全 26px、列宽精确、无溢出、compact 未触发、gapToFooter 63、行高 65-66px 全部单行（ShotLab 23 字长文本在 646px B0 列内单行完整）、theadH 60（三列表头均单行）；PIL 1200×1200/2742 色/着墨 9.0%；VLM r1 全图逐字转写程序化比对全过（标题/图例/排序说明/表头/10 行表体/脚注）+ r2 整图版式 7/7 合格无 tofu；validate.py 目录级 67/67。
- source-data.csv 追加 11 行（10 平台+图级口径）→ 180 行无重复；README/overrides.txt（img8 OVERRIDE 行）/双 worklog 同步。
- fetch 确认远端无新提交后单次 commit + push。

Stage Summary:
- 1026-drama-sankey v1.0 现含七张图：img1 桑基图 + img2 提示词调整对比 + img3 剧情介绍 + img4 模型缩水扣分表（1200×1500）+ img5 T1第一抽错误信息表（1200×1200）+ img6 抽卡效率影响因素扣分表（1200×1650）+ img8 @类引用自动补全两列表（1200×1200）。
- 口径沉淀：用户 2026-10-27 重申"表格宽度可灵活拉宽+最小字号=脚注"——即 img4 修订4 基线为系列长期口径，后续表格图直接沿用（OVERRIDE 模板已备）。

---
Task ID: 8-r1
Agent: main (Z.ai)
Task: img8 修订1 · T4 填词耗时列三处数据更新（用户 IM："img8的最后一列稍作修改，其余不变，快速输出新版"）

Work Log:
- 修改 img8-styled.html（外科式 3 处，其余零改动）：LibTV 15→20分钟、纳逗Pro 12→15分钟、Seko 15→20分钟；HTML 头部追加修订注释。
- 基准同步：img8-check.cjs BASE_ROWS 与 img8-vlm-compare.py expect rows 同步三处新值。
- render.mjs a 重渲一次通过：rc=0，yzCheck compliant（browser-validation-img8.json 更新）。
- 质检链全过：img8-check.cjs DOM 40 格+标题+图例 3 项+排序说明+脚注逐字零差异、9 项选择器字号全 26px、列宽 150/646/260 精确、无溢出、compact 未触发、gapToFooter 63（与修订前完全一致，纯数字替换不影响版式）；PIL 1200×1200/2742 色。
- VLM r1 全图逐字转写：10 行表体三处新值全部正确（LibTV 20分钟/纳逗Pro 15分钟/Seko 20分钟）；图例"可复现"被 r1 误读为"可重现"、表头 | 分隔符漏读——两处经 2x 裁图（y 55-340 区域）VLM 复核闭环：图例"可复现"正确、表头文字完整，均为 VLM 误读而非渲染缺陷（DOM 层为权威）。
- source-data.csv 追加修订溯源 4 行（LibTV/纳逗Pro/Seko 三行新值+图级修订口径）→ 184 行无重复；README（img8 内容口径/修订1 条目/目录结构 CSV 计数/验证链第 6 条）同步。
- validate.py 目录级复跑：compliant 67/67。
- fetch 确认远端无新提交后单次 commit + push。

Stage Summary:
- img8 修订1 完成：T4 列三处更新（LibTV 20/纳逗Pro 15/Seko 20 分钟），版式/字号/列宽/其余内容零变化，全套验证通过并推送 main。
- 就地修订 v1.0 文件（沿用 img4 修订1-4 先例，git 历史留存旧版）。

---
Task ID: 9
Agent: main (Z.ai)
Task: skill-A 制作本批次第八张图《提示词改写与画面污染情况》平台×出错次数▼+C1-C4 六列表（1026-drama-sankey img9）

Work Log:
- 会话恢复核对：git 状态干净（main 与 origin 同步于 a7e32e6，img8 修订1 已交付）；沿用 img4 修订4/img5/img6/img8 已批准基线（1200 宽+26px 统一字号+68px 标题单行）。
- 数据核对：用户输入 10 平台行；行序=用户输入原序=出错次数降序（4→0）+同次数组内拼音升序（3次组 O<Sh<T、2次组 L<Se<X、1次组 A<N，程序化双核验一致）；图例仅 1 项"- 不扣分"（本表无 ●，仅 ShotLab C1/C2 两格带 △ 前缀）；脚注数据截至 2026年10月23日（与 img4/img6/img8 同日期）。
- 构建 img9-styled.html：模板区与 img6/img8 逐字一致（含 yzCheck 1200 宽常量）；6 列 fixed 表格列宽 140/138/216/216/216/130（总宽 1056，C4 列全为"-"故最窄，C1-C3 问题文本列等宽）；出错次数▼ 居中窄列沿用 img6 扣分▼列式（.hz-c）；出错次数数值加粗居中（Bold 700=数值，同 img8 T4）；C 列 △ 符号沿用系列配色（次级灰加粗 .st，同 img6）。
- 画布高度按内容调参：初设 1560 时 DOM 全过但 gapToFooter=11 偏窄（theadH 128、行高 66-137 高于预估）→ 按实测调至 1600（gap=31）→ 重渲 rc=0 yzCheck compliant。
- 质检链全过：img9-check.cjs DOM 66 格（表头 6+表体 60）+标题+图例 1 项+排序说明+脚注逐字零差异、行序双核验（降序+拼音组）、10 项选择器字号全 26px、列宽精确、无溢出、compact 未触发；PIL 1200×1600/2941 色/着墨 6.1%；VLM r1 全图逐字转写程序化比对全过（标题/图例/排序说明/表头/10 行表体/脚注）+ r2 整图版式 7/7 合格无 tofu（△▼ 均正常渲染）。
- source-data.csv 追加 11 行（10 平台+图级口径）→ 195 行无重复；README（img9 章节/目录结构/验证链）/overrides.txt（a.canvas-1200x1600-img9）/双 worklog 同步；validation.json 刷新 76/76。
- fetch 确认远端无新提交后单次 commit + push。

Stage Summary:
- 1026-drama-sankey v1.0 现含八张图：img1 桑基图 + img2 提示词调整对比 + img3 剧情介绍 + img4 模型缩水扣分表（1200×1500）+ img5 T1第一抽错误信息表（1200×1200）+ img6 抽卡效率影响因素扣分表（1200×1650）+ img8 @类引用自动补全两列表（1200×1200，含修订1）+ img9 提示词改写与画面污染六列表（1200×1600）。
- 详细记录见 clock/1026-drama-sankey/worklog.md Task 9。

---
Task ID: 10
Agent: main (Z.ai)
Task: skill-A 制作本批次第九张图《分镜切分与空间站位》平台×扣分▼+D1-D4 六列表（1026-drama-sankey img10）

Work Log:
- 会话恢复核对：git 状态干净（main 与 origin 同步于 5ac8924，img9 已交付）；沿用 img4 修订4/img5/img6/img8/img9 已批准基线（1200 宽+26px 统一字号+68px 标题单行）。
- 数据核对：用户输入 10 平台行；扣分列全"-"→行序=用户输入原序=全表拼音升序 A<J<L<N<O<Se<Sh<T<W<X（程序化核验一致）；图例三项全套"- 不扣分 ● 可复现（每抽3-4次） △ 抽卡波动（每抽1-2次）"（与 img4/img6/img8 同套逐字复用，本表体无●仅 4 格带△前缀）；脚注数据截至 2026年10月23日。
- 两处裁定：①D4 表头"轻微"引号取规范弯引号方向 U+201C…U+201D——与 img1 桑基图原始数据 D4 行逐字一致（用户输入引号方向翻转系复制意外，语义零变化）；②D2/D3 问题分布与 img1 表2 互证（D2 涉及平台=Seko、D3 涉及平台=纳逗Pro+OiiOii，与 img10 问题格完全对应）。
- 构建 img10-styled.html：模板区与 img9 逐字一致（含 yzCheck 1200 宽常量）；6 列 fixed 表格列宽 140/88/207×4（总宽 1056=1200-144，D1-D4 同类列等宽=img4 修订2 用户长期规则，扣分▼窄列 88 沿用 img6 先例）；扣分列全"-"灰色居中（.cntv.na，img4 修订3 先例）；D 列 △ 符号沿用系列配色（次级灰加粗 .st）；巨日禄 D 类四项均无扣分（与 img9 出错 4 次对照：出错≠必然扣分）。
- render.mjs a 一次通过：rc=0，yzCheck compliant（browser-validation-img10.json）；画布高度 1200×1400 初设即命中（宽高比 1:1.167，gapToFooter=39px 无需调参）。
- 质检链全过：img10-check.cjs DOM 66 格（表头 6+表体 60）+标题+图例 3 项+排序说明+脚注逐字零差异、行序全表拼音升序核验、11 项选择器字号全 26px、列宽精确、无溢出、compact 未触发、标题单行 h=76px；PIL 1200×1400/2570 色/着墨 30.6%（斑马纹浅灰计入口径）。
- VLM 双轮+两处闭环：r1 全图逐字转写程序化比对全过（VLM 本次以制表符分隔单元格，img10-vlm-compare.py 归一化处理[\s|]后表头/10 行表体/标题/排序/脚注全部一致）；图例"可复现"VLM 两读不一（r1 读"可再现"、2x 头部裁图读"可重现"——img8 修订1 同款误读模式且两次结果不同=识别不稳定）→ **像素级闭环**：img10 图例区域与 img8 逐像素零差异（diff bbox=None），img8 该处已经 2x VLM 复核确认"可复现"正确 → 渲染无误、DOM 层权威；r2 版式 1-6 过、第 7 项"水印遮挡 D2/D3 内容"经表格中部裁图（y 480-900 含全部△文本行）复核"没有文字被遮挡或不可读"闭环为 VLM 误报（半透明水印=yzCheck 强制合规项、img1-img9 同款、z-index 10 位于表格文字 z-index 20 下层）。
- validate.py 目录级（img1-img10）：compliant 85/85；source-data.csv 追加 11 行（10 平台+图级口径）→ 206 行无重复；README（img10 章节/目录结构/验证链）/overrides.txt（a.canvas-1200x1400-img10）/validation.json（85/85）同步。
- fetch 确认远端无新提交后单次 commit + push。

Stage Summary:
- 1026-drama-sankey v1.0 现含九张图：img1 桑基图 + img2 提示词调整对比 + img3 剧情介绍 + img4 模型缩水扣分表（1200×1500）+ img5 T1第一抽错误信息表（1200×1200）+ img6 抽卡效率影响因素扣分表（1200×1650）+ img8 @类引用自动补全两列表（1200×1200，含修订1）+ img9 提示词改写与画面污染六列表（1200×1600）+ img10 分镜切分与空间站位六列表（1200×1400）。
- 口径沉淀：D4 表头引号方向裁定（规范 U+201C…U+201D，img1 互证）；D2/D3 问题分布与 img1 表2 平台互证链建立；VLM"可复现"误读新增像素级等价闭环手段（跨图同套图例区域 diff）。

---
Task ID: 11
Agent: main (Z.ai)
Task: skill-A 制作本批次第十张图《音画控制与后处理情况》平台×次数（除水印/角标）▼+E1-E5 七列表（1026-drama-sankey img11）

Work Log:
- 会话恢复核对：git 状态干净（main 与 origin 同步于 5ac8924，img10 已交付）；skill 文件链重读（yz-infographic v3.1 SKILL.md 全文 + render.mjs/validate.py 用法）；沿用 img4 修订4/img5/img6/img8/img9/img10 已批准基线（1200 宽+26px 统一字号+68px 标题单行）。
- 数据核对：用户输入 10 平台行；行序=次数降序（10→1）+同次数组内拼音升序（5次组 巨日禄<纳逗Pro、2次组 LibTV<ShotLab<小云雀，程序化核验与用户行序一致）；图例仅"- 不扣分"1 项（同 img9）；**次数列算术核验**：程序化解析 E2/E3/E5 抽次文本（T码单抽/顿号列表/连字符区间三形态）求和=次数列，10/10 平台全部吻合（E4 水印/角标按表头"除水印/角标"口径排除）。
- 两处互证裁定（均以用户当前输入为最高优先级，差异记录于 README 三 + CSV notes）：①与 img1 表2 的 E2/E3 涉及平台分布差异（img1 表2 E2 仅记 OiiOii、E3 含巨日禄不含 OiiOii；本表 E2 七平台、E3 含 OiiOii 不含巨日禄）；②E 系表头措辞用户方简化（E1 无"段"、E3 无"画面"、E4 简写、E5"未还原"替代"没有还原"且无引号）。E4 两格"AI生成"引号取规范方向 U+201C…U+201D（img10 D4 先例）。
- 构建 img11-styled.html：模板区与 img9/img10 逐字一致（含 yzCheck 1200 宽常量）；7 列 fixed 列宽 140/188/96/163/163/145/161（总宽 1056=1200-144；内容列优先 E2/E3=163、E4=145，E1/E5 全"-"列取剩余 96/161，次数列 188=表头"次数（除水印/角标）▼"两行换行所需）；次数列数值加粗居中（Bold 700=数值，同 img9 出错次数列）。
- 画布高度按内容调参：初设 1560 时 gapToFooter=-6（表格底缘越过页脚分隔线 6px）→ 按实测调至 1650（上下留隙各 39px，与 img10 已批准水准一致，画布尺寸同 img6）→ 重渲 rc=0 yzCheck compliant。
- 质检链全过：img11-check.cjs DOM 77 格（表头 7+表体 70）+标题+图例 1 项+排序说明+脚注逐字零差异、行序双核验、次数列算术核验 10/10、11 项选择器字号全 26px、列宽精确、无溢出、compact 未触发、标题单行；PIL 1200×1650/2982 色/着墨 32.7%（斑马纹口径）；VLM r1 全图逐字转写程序化比对全过（含 E4 弯引号方向专项核对，本轮零误读零待复核项）+r2 版式 7/7 无 tofu（▼/全角标点/连字符/弯引号均正常）；validate.py 目录级 94/94。
- source-data.csv 追加 11 行（10 平台+图级口径）→ 217 行无重复；README（img11 章节/目录结构/数据裁定 img11 差异表/验证链）/overrides.txt（a.canvas-1200x1650-img11）/validation.json（94/94）/browser-validation-img11.json 同步。
- fetch 确认远端无新提交后单次 commit + push。

Stage Summary:
- img11 交付完成：1200×1650 成品 PNG + HTML 源 + 11 行溯源 + 全套验证（含次数列算术核验新手段：T 码抽次文本程序化解析求和=次数列）。
- 1026-drama-sankey v1.0 现含十张图：img1 桑基图 + img2 提示词调整对比 + img3 剧情介绍 + img4 模型缩水扣分表 + img5 T1第一抽错误信息表 + img6 抽卡效率扣分表 + img8 @引用补全两列表 + img9 提示词改写污染表 + img10 分镜切分站位表 + img11 音画控制后处理表。
