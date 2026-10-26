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
