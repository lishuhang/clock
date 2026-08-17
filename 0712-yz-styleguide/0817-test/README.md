# 0817-test｜沈腾信息图官方数据校准版

本目录是对 `0816-test` 的数据翻新交付。它保留原项目的三步分发逻辑：`round1` 为文章主图，`round2` 为 1:1 社媒拆图，`round3` 为可在浏览器中播放入场动画的同内容版本。所有图表均为确定性 SVG/HTML 渲染，并同时提供 PNG 预览。

## 交付物

| 目录 | 文件 | 用途 | 数据状态 |
| --- | --- | --- | --- |
| `round1` | `01-professional-focus.html/.png` | 10 部作品的专业能力评价焦点主图 | 已按 `f1_subdim_chart.csv` 逐片校准 |
| `round1` | `02-issue-fade.html/.png` | F3/F4 热映期—近期哑铃主图 | 已按 `chart_04_f4_f3.csv` 校准 |
| `round2` | `01-comedy-anchor.html/.png` | 早期喜剧演员定型期拆图 | 已按 `f1_subdim_chart.csv` 校准 |
| `round2` | `02-beyond-comedy.html/.png` | 关键作品趋势拆图 | 已按 `f1_subdim_chart.csv` 校准 |
| `round2` | `03-issue-fade.html/.png` | 议题退潮代表案例拆图 | 已按 `chart_04_f4_f3.csv` 校准 |
| `round3` | `01/02/03-*-motion.html/.png` | 对应 round2 的动效就绪版与静态终态预览 | 使用同一校准数据；HTML 中含入场 CSS |

## 数据使用说明

| 资料 | 已使用位置 | 方法约束 |
| --- | --- | --- |
| `data/f1_subdim_chart.csv` | 专业能力主图及 round2/round3 的前两张图 | 直接使用每部作品的官方整数百分比；不重算、不归一化。逐项取整后部分行的总和为 99%–102%，图中已如实保留并在脚注说明。 |
| `data/f1_subdim_matrix.csv` | 数据交叉核验 | 用于核对作品、年份和“非喜剧”占比。 |
| `data/chart_04_f4_f3.csv` | F3/F4 主图与拆图 | 使用热映期/近期原始比例及源表给出的有效样本范围。 |

## 完整表 1 与表 3 的补数边界

本次仅收到三份 CSV。用户提及但未出现在上传目录或仓库中的两份官方底稿是：

| 缺失文件 | 影响 | 当前处理 |
| --- | --- | --- |
| `shenteng_works_heatmap.csv` | 无法严谨重制表 1 的“10 部作品 × 6 维度”热力表 | 未复用 0816 的手工数值，也未填造数值；生成脚本可在数据到位后扩展。 |
| `shenteng_dumbbell_chart.csv` | 无法严谨重制表 3 的“专业能力、民族国家、社会文化/性别”三维完整哑铃图 | 当前只以已提供的 F3/F4 构建独立、明确标注为“官方补充数据”的图，不冒充完整表 3。 |

## 复现

在 `0712-yz-styleguide/0817-test` 目录执行：

```bash
python3 generate_infographics.py
./render_png.sh
```

`generate_infographics.py` 生成可编辑的 HTML/SVG 源文件；`render_png.sh` 使用本地 Chromium 读取 SVG 的实际画布高度后输出 PNG，并等待动效结束以导出 round3 的静态终态。

## 设计与编辑原则

新版着重表达：沈腾被讨论的变化并不等于线性“去喜剧化”。《抓娃娃》的喜剧占比回升至 73%，而《欢迎来龙餐馆》在喜剧/搞笑、演技/声台形表、剧本/节奏/整体三个重点项上分别为 4%、25%、57%。图表故意保留这类回弹，避免用阶段平均数抹平作品差异。关于热映期议题，图中将题材性讨论与演员个人的稳定标签分开表达，并以同尺度展示小比例维度。

详见 `analysis/brief.md`、`analysis/calibration_plan.md` 和 `analysis/data_audit.json`。
