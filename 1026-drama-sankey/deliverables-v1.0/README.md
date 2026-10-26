# 1026-drama-sankey · 交付说明 v1.0

生成日期：2026-10-26 · 依据：娱资 infographic skill v3.1 工作流 A（900px 静态信息图）

## 一、图表内容

将《测试用提示词与加/扣分项》两张主表合并为一张桑基图（`img1-styled.png`，900×1350）：

- **左侧**：4 条测试提示词卡片（T1–T4），含标题、类型标签（文戏/武戏 × 少参/多参）与测试要点；
- **右侧**：24 个加/扣分项（A1–E5，含 B0/C0 两个加分项），含编号色块与项目名称；
- **连线**：共 75 条，按用户要求分两层——
  - 四条提示词**均涉及**的 14 项 → **淡灰细线，渲染在下层**；
  - **部分涉及**的 10 项（A4、B2、C1、C4、D2、D3、D4、E1、E3、E5）→ **橙红粗线，醒目且渲染在上层**；
  - 连线带按右侧行序 / T1→T4 序排布，整图无交叉，逐条可辨；
- **涉及平台列**：平台名称一律替换为附件 favicon（18px 方形图标，hairline 描边），"（T1第1抽）"等抽次标注按用户要求**忽略不加**；表中留空的平台格保持留空；
- 加分项（B0/C0）以浅橙编号块 + "加分"标签标识，连线按"四条均涉及"归入淡显下层。

## 二、目录结构

```
deliverables-v1.0/
├── img1-styled.html        # A 版源文件（模板 + 桑基布局构建脚本）
├── img1-styled.png         # 成品 900×1350
├── source-data.csv         # 116 行级溯源（4提示词+24项目+75连线+10favicon+3口径）
├── browser-validation.json # render.mjs yzCheck 报告（compliant）
├── validation.json         # validate.py 报告（13/13 通过）
└── assets/                 # 阿里普惠体×3 + 河豚/字标 SVG + favicons/×10
```

## 三、数据裁定记录（两处表间不一致）

| 项 | 表1（提示词表） | 表2（加/扣分项表） | 裁定 | 佐证 |
|---|---|---|---|---|
| C1 涉及 T3？ | T3 行未列 C1 | C1"涉及提示词=T3、T4" | **涉及**（按表2） | 巨日禄（T3第3抽：C1蓝光） |
| D2 涉及 T2？ | T2 行未列 D2 | D2"涉及提示词=T2、T4" | **涉及**（按表2） | Seko（T2第2抽） |

另：正文称"2个加分项、20个扣分项"，表2实为 **22 个扣分项 + 2 个加分项**，以表格为准绘制。

## 四、验证链

1. `render.mjs a` → rc=0，`yzCheck()` 返回 **compliant**（contract/canvas/title/body/font/logo/watermark/external/shadow 全过）；
2. 内嵌几何自检：faint=56、prom=19，合计 75 条连线与数据矩阵一致，左右列均无溢出；
3. VLM 视觉质检：版式 6 项全过；连线数据抽查 8 项全过（D4→仅T1、C4→仅T3、E1→仅T2、A4→T1+T4、A1→全四条淡线、B0/C0→淡线、E3→T1/T3/T4 不连T2、连线均锚定卡片边缘）；
4. `validate.py --mode a` → **compliant，13/13**（含敏感信息扫描为零，GitHub token 未进入任何产物）。

## 五、版本规则

本版为 v1.0；后续修改在 `deliverables-v1.1/` 递增目录进行，不覆盖本版。重渲染：`node …/assets/render.mjs a img1-styled.html img1-styled.png`（需 NODE_PATH 指向全局 node_modules）。
