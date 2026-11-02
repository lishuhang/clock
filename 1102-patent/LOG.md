# 工作日志（GMT+8 时区）

## 2026-11-02 07:34 GMT+8 · 初始化 1102-patent 子项目
- 确定交付架构：本地沙箱代理封锁所有专利二进制源（Google Patents 404 / CNIPA 412 / 天眼查 api-gateway 502），
  唯一可行路径是 **GitHub Actions runner（无过滤外网）** 委托下载真实专利附图与 PDF。
- 编写 `dl.py`（纯标准库 urllib）：解析两份稿件 md 中的 `img/<类别>[/备选]/<公开号>.png` 与
  `pdf/<类别>[/备选]/<公开号>.pdf` 相对链接 → 调天眼查 `api-gateway-web` 搜索/详情接口 → 落地真实图与 PDF，
  并写出 `api_probe.json`（前 3 件原始结构，已脱敏）供字段核对。
- 编写 `.github/workflows/download-patents.yml`：
  - 从 `secrets.TYCCOOKIE` 写入 runner 临时 `.cookies/tyc.txt`（**绝不入库**）。
  - `python3 dl.py` 下载。
  - 仅 `git add img/ pdf/ api_probe.json LOG.md`，明确排除 cookie，避免空提交。
- 复制成品稿件（25 件）与备选专利池（约 47 件）md 进本目录，供 `dl.py` 解析。
- 新增 `.gitignore`（忽略 `.cookies/`）、`README.md`。
- 推送策略：先推送 workflow / .gitignore / README / LOG（不触发自动下载），再设置 `TYCCOOKIE` 仓库密钥，
  最后推送 `dl.py` + 两份 md（触发 `download-patents`）。全程 **不提交 token / cookie**，且**不频繁 push**。

## 待办 / 风险
- [ ] 验证天眼查 `api-gateway-web` 在 runner 上是否可用（本地 502，runner 未知）。
- [ ] 若天眼查接口字段与 `dl.py` 假设的 key 不符，依据 `api_probe.json` 调整 `deep_find` 的 key 列表。
- [ ] 若天眼查本身也封锁 runner IP，需考虑备选数据源（仍须为可合法公开获取的专利原文托管）。
