# Photos 2026-09-02 前端小修交接

## 用户需求

`lishuhang/photos` 上次改为默认显示 weserv 480×480 方形缩略图后，点击缩略图的新窗口仍然打开同一张 480×480 图。用户要求：缩略图保持不变；新窗口使用 `images.weserv.nl/?url=<原图>` 且不带 `w`、`h`、`fit`、`output`、`q` 等变换参数，从而返回原尺寸。

## 最小修改

只改 `index.html` 中展开图片时的目标链接：

- `<img src>` 仍为 `w=480&h=480&fit=cover&output=jpg&q=80`；
- 默认关闭“原图预览”时，`<a href>` 改为只含编码后原图 URL 的 weserv 地址；
- 用户主动打开“原图预览”时，链接仍直达原始 raw URL。

没有改 CSS、数据格式、图片路由、缩略图质量、导航或其他交互。

## 验证与发布

- 在本地页面加载生产 `data/202608.json`，展开 08/01，共生成 135 个图片链接；所有目标链接均不含缩放或格式参数。
- 真实浏览器点击第一张缩略图后，新窗口 URL 为仅带 `url=` 的 weserv 地址，页面标题显示图片尺寸 `4096×3072`，证明打开的是原尺寸而非 480×480 缩略图。
- 已通过无交互 GitHub API 推送到 `lishuhang/photos` 的 `main` 分支。
- 提交：`1f2aa2de69cf065de207454886c856aa171d58db`（`Fix full-size photo links`）。
- GitHub Pages 构建成功；`https://lishuhang.me/photos/` 已返回新代码。

