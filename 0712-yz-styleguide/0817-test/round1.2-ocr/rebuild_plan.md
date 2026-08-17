# 沈腾图表 round1.2 / round2.2 / round3.2 重建方案

## 1. 不可变设计契约

| 项目 | 执行规则 | 来源 |
| --- | --- | --- |
| 品牌标识 | 使用原始 skill 的 SVG symbol：round1 右下为 `#yz-logo-horizontal`，round2/3 标题右侧为 `#yz-logo-icon`；不以“娱乐资本论”文字替代 SVG。 | `v2.22a/b-yz-styleguide.html` |
| 字体 | 正文、标题、数值均使用阿里巴巴普惠体 `AliPuHui`（400/700/900）；网页离线渲染前加载本地副本。 | `v2.22a/b-yz-styleguide.html` |
| 颜色与容器 | 白色画布、#312e2e 正文、#fc8166 数据强调色、#efefef 图表底色、#e5e5e5 分隔线、圆角 6px。不得增加顶部橙条、外框、渐变背景或未定义装饰。 | `v2.22a/b-yz-styleguide.html` |
| 组件复用 | 仅使用原始共享组件语义：`.chart-container` / `.chart-container-1x1`、`.chart-header(-1x1)`、`.chart-footer(-1x1)`、`.yz-logo-svg` / `.chart-logo-1x1`、`.hm-table`、`.sb-*`、`.db5-*`、`.tc-*`、`.axis-scale`、`.chart-legend`。 | `v2.22a/b-yz-styleguide.html` |
| round2 字号 | 1:1 图片为 1080×1080 等比例版；正文 ≥40px、辅助 ≥28px、脚注 ≥27px、编号 ≥24px。密度超限时拆图，不缩字。 | `v2.22b-yz-styleguide.html` |
| round3 | 每个 round2.2 图对应一个 MP4：16 秒、30fps、6 秒四阶入场 + 4 秒静止 + 6 秒倒放出场；导出无灰边的 1:1 容器画面。 | `v2.22c-yz-styleguide.html` |
| 文字 | 不新增解释性观点、标题副标题或结论句；只使用表题、维度名、来源数据、OCR 可核验引文和必要元数据。 | 用户反馈与原始 prompt |

## 2. round1.2 大图

| 文件 | 内容 | 精确数据源 | 视觉组件 |
| --- | --- | --- | --- |
| `img1-a-heatmap` | 10 部作品 × 6 维度热力表 | `shenteng_works_heatmap.csv` | `.hm-table`、`.hm-legend`、`.chart-footer`、水平 SVG logo、居中纵向 SVG watermark |
| `img2-a-professional` | 10 部作品的专业能力评价子维度堆叠条形图 | `f1_subdim_chart.csv` | `.sb-wrap`、`.sb-row`、`.sb-bar`、`.sb-seg`、`.chart-legend` |
| `img3-a-dumbbell` | 热映期与近年回看：专业能力、民族国家、社会文化/性别三面板对照 | `shenteng_dumbbell_chart.csv` | `.db5-wrap`、`.db5-sub`、`.db5-row`、`.dumbbell-*`、`.axis-scale`、`.chart-legend` |
| `comments-a` | 用户提供截图中 5 条豆瓣、2 条小红书代表评论的原文引语表 | `ocr_notes.md` / 原始截图 | `.tc-grid`、`.tc-card`、`.tc-quote`，以平台/截图元数据为脚注 |

## 3. round2.2 1:1 拆图

| 图组 | 拆法 | 数量 | 核心规则 |
| --- | --- | ---: | --- |
| 表 1 热力表 | 10 行按 4-3-3 拆三张 | 3 | 每张保持 6 维度列和同一颜色图例，数字全部源自官方 CSV。 |
| 表 2 专业能力 | 10 行按 4-3-3 拆三张 | 3 | 每张保持相同子维度图例与 100% 堆叠基准。 |
| 表 3 哑铃图 | 3 个维度各一张 | 3 | 每张保留 10 部作品的完整横向对比，展示源 CSV 的两期值与 `变化Δpp`。 |
| 豆瓣单条图 | 5 条截图各一张 | 5 | 只放一条 OCR 引文和截图可见元数据；不填写模糊昵称、不虚构片名。 |
| 小红书单条图 | 2 条截图各一张 | 2 | 只放一条 OCR 引文和截图可见元数据；不把个体评论写成统计结论。 |

## 4. round3.2 视频

round3.2 对应 round2.2 的 16 条图：每条保留 round2.2 的同一容器、同一 SVG logo、同一字体、同一数据；仅注入 v2.22c 四阶段 CSS 动画，并录制为 MP4。热力表按行淡入、堆叠条从底生长、哑铃线由左向右绘制并出现端点、评论卡向上淡入。不得使用前轮自制的橙色顶线、私有卡片样式或 Noto 字体。

## 5. OCR 使用清单

| 单条卡文件 | 平台 | 唯一可用引文 | 截图证据 |
| --- | --- | --- | --- |
| `comment-d01` | 豆瓣 | “男性视角的意淫” | `640(3).png` |
| `comment-d02` | 豆瓣 | “好消息是沈腾贡献了最富层次的一次表演，坏消息是成片的质量到底辜负了他。” | `640.png` |
| `comment-d03` | 豆瓣 | “各种夸张和尴尬，还用沈腾做幌子。” | `640(2).png` |
| `comment-d04` | 豆瓣 | “看到沈腾的名字立即选座无脑买的。” | `640(1).png` |
| `comment-d05` | 豆瓣 | “作为女性，对于这种中年男人的意淫完全接受不了。” | `640(4).png` |
| `comment-x01` | 小红书 | “腾哥是我们这一辈的星爷😭” | `640(1).jpg` |
| `comment-x02` | 小红书 | “内娱你欠沈腾一个实至名归的影帝。” | `640(1).jpg` |

