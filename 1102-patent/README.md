# 1102-patent · 互联网大厂专利月度盘点（真实附图 + 全文 PDF 下载）

本目录承载「互联网大厂月度专利盘点」项目的**可执行产物与真实专利素材**。

## 背景
按月（每月 5 日前）盘点优酷 / 爱奇艺 / 腾讯 / 阿里 / B站 / 百度 / 搜狐 / 微博 / 小米 / 华为 / 荣耀 / OPPO / vivo / 咪咕 及主要游戏公司，**近 1 个月内公开**的文娱 / 技术成熟度高的专利，固定 5 大类别：

1. 音视频相关
2. 游戏相关
3. AI 相关
4. 数字人元宇宙
5. 公益民生

每件专利在稿件中以「真实专利附图 + 全文 PDF」呈现（非自绘），图片与 PDF 均按 `<类别>[/备选]/<公开号>` 目录归档。

## 目录结构
```
1102-patent/
├── dl.py                              # runner 端下载器（仅标准库，解析两份 md 的相对链接 → 天眼查查询 → 落地 img/ 与 pdf/）
├── .github/workflows/download-patents.yml   # GitHub Actions：注入 cookie secret → 跑 dl.py → 提交真实素材
├── 2026年10月互联网专利盘点.md            # 成品稿件（25 件，5 类各 5 件）
├── 2026年10月互联网专利盘点_备选专利池.md  # 备选专利池（约 47 件）
├── img/<类别>[/备选]/<公开号>.png        # 专利说明书附图（真实）
├── pdf/<类别>[/备选]/<公开号>.pdf        # 专利全文 PDF（真实）
├── api_probe.json                     # 前 3 件 search/detail 原始结构（已脱敏），用于核对字段
├── LOG.md                             # 工作日志（GMT+8）
└── .cookies/                          # 本地/runner 临时凭据（git 忽略，绝不上库）
```

## 为什么用 GitHub Actions 下载
本地沙箱代理会拦截所有专利二进制来源（Google Patents 404、CNIPA 412、天眼查 api-gateway 502 等）。
GitHub Actions 的 ubuntu-latest runner 具备**无过滤外网**，可直达天眼查接口拉取真实附图与 PDF，
因此把下载动作委托给 Actions，runner 仅把**图片与 PDF**（绝不碰 cookie）提交回仓库。

## 使用方式
1. 在仓库 Settings → Secrets 配置 `TYCCOOKIE`（天眼查 Netscape 格式 cookie 全文）。
2. 手动触发 `download-patents` workflow（或在两份 md 有改动时自动触发）。
3. 跑完会自动 commit `img/`、`pdf/`、`api_probe.json`、`LOG.md`，不含任何凭据。

## 凭据安全
- `.cookies/` 已被 `.gitignore` 忽略。
- workflow 仅从 `${{ secrets.TYCCOOKIE }}` 写入 runner 临时文件，且 `git add` 明确排除它。
- **任何情况下不要把 token / cookie 提交入库或打印到日志。**
