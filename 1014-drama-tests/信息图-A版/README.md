# 信息图 A 版（功能篇重构）

本目录为 2026-10-14 功能篇重构产出的 12 张 yz-infographic v3.1 A 模式静态信息图。

## 文件说明

- `img1-styled.html/png`：表1 做漫剧的 bingo
- `img2-styled.html/png`：表2 做影视的 bingo
- `img3-styled.html/png`：表3 做生意的 bingo
- `img4-styled.html/png`：表4 六项标配
- `img5-styled.html/png`：表6 独家功能
- `img6-styled.html/png`：表7 防串脸排名
- `img7-styled.html/png`：表8 剧本与分镜排名
- `img8-styled.html/png`：表9 3D与拉片排名
- `img9-styled.html/png`：表10 音画分离排名
- `img10-styled.html/png`：表11 并行与协作
- `img11-styled.html/png`：表12 出海与生态
- `img12-styled.html/png`：表5 任务四环节
- `source-data.csv`：数据来源存档（77 行，每个视觉事实回指一行）
- `validation.json`：yz skill validate.py 报告（112 项检查通过，state: compliant）

## 查看与重新渲染

HTML 依赖 `assets/` 下的阿里普惠字体与娱乐资本论 logo（未随本目录提交，体积较大）。渲染步骤：

1. 从 step-4-1014-0019.zip 内的 yz-infographic-v3.1.zip 解出 `assets/`（字体与 SVG）放到本目录同级；
2. `node render.mjs a img{n}-styled.html img{n}-styled.png`（需 playwright）。

## 显式例外记录（OVERRIDE）

```
OVERRIDE | a.chart-body table font-size 32px | 用户转述主编原话："现在的字有点小…手机阅读的话，那个字体肯定是太小了…希望更大吧"（step2 10-09 18:25/19:33） | 原因：当前项目明确要求，移动端可读性优先
```

模板基准字号 28px，表格与榜单字号提升至 32px；.chart-body 基准 28px 与其余规范（900px 画布、68px 标题、品牌位、水印、自检函数）未改动，`yzCheck()` 全部返回 compliant。
