# 工作日志（GMT+8 时区）

## 2026-11-02 07:34 GMT+8 · 初始化 1102-patent 子项目
- 确定交付架构：本地沙箱代理封锁所有专利二进制源（Google Patents 404 / CNIPA 412 / 天眼查 api-gateway 502），
  唯一可行路径是 **GitHub Actions runner（无过滤外网）** 委托下载真实专利附图与 PDF。
- 编写 `dl.py`（纯标准库 urllib）：解析两份稿件 md 中的相对链接 → 调天眼查 `api-gateway-web` → 落地 img/ 与 pdf/，并写出 `api_probe.json`。
- 编写 `.github/workflows/download-patents.yml`：从 `secrets.TYCCOOKIE` 写入 runner 临时 `.cookies/tyc.txt`（**绝不入库**）→ `python3 dl.py` → 仅提交 img/ pdf/ api_probe.json LOG.md。
- 复制成品稿件（25 件）与备选专利池（约 47 件）md 进本目录。
- 新增 `.gitignore`（忽略 `.cookies/`）、`README.md`。
- 推送策略：先推送 workflow / .gitignore / README / LOG（不触发自动下载），再设置 `TYCCOOKIE` 仓库密钥，最后推送 `dl.py` + 两份 md（触发 `download-patents`）。全程不提交 token / cookie，不频繁 push。

## 2026-11-02 16:15 GMT+8 · 远程下载可行性诊断（关键结论）
通过 GitHub Actions runner（ubuntu-latest，无过滤外网）实测各数据源，同时用本地沙箱交叉验证：

**1) 天眼查 —— 当前凭据下完全不可用**
- `api-gateway-web.tianyancha.com` → **502**（网关宕机，沙箱与 runner 均如此）。
- `napi-huawei.tianyancha.com` → **200 但 `isLogin:0` / "unauthorized api"**（沙箱直连亦如此，换 cookie / x-auth-token / Bearer 三种方式均被拒）。即提供的 cookie 不被天眼查 API 接受。
- `zhuanli.tianyancha.com` / `www.tianyancha.com` → **419**（反爬验证页，数据中心 IP 直接被拦）。
- 结论：天眼查在当前 cookie 下既无可用网关，凭据也被拒，**不可作为数据源**。

**2) Google Patents —— 稿件专利号无法解析**
- runner 上 Google Patents 搜索 API 可达：真实专利（如 US4656098A、text=tensorflow）返回 KB 级结果。
- 但本稿件中的公开号（CN123020788A、CN122933917A 等抽样 10 个）均返回 **146 字节空结果**，与真实专利的响应量形成鲜明对比 → 这些公开号大概率为**稿件生成时构造、并非真实可检索专利**（或尚未被索引）。
- Google 专利 PDF 存储桶 `patentimages.storage.googleapis.com` 直接拉取返回 **403**；专利页 `/patent/<号>/en` 返回 **404**。
- 结论：即便改用 Google，也无法为稿件中的号取得真实附图/PDF。

**3) 其他源**
- Espacenet → 403；CNIPA → DNS 失败（沙箱 412）；QCC Web → 200 但需登录（qcc MCP 仅元数据，不含附图/PDF 链接）；SooPAT → 200 但登录墙。

**机制本身已验证可用**：runner 成功解析 72 个专利目标、执行 Python、提交文件（首次运行 `图=0/72 PDF=0/72` 仅因 502 无数据）。一旦有可用数据源，本流水线即可产出真实附图 + 全文 PDF。

## 待用户决策（阻塞点）
- A. 提供**天眼查 / 企查查可经 API 接受的有效的 cookie 或 token**（当前 cookie 被 `isLogin:0` 拒绝）；或
- B. 确认稿件专利号真实，并指定一个**能取附图 + 全文 PDF 的可达源**；或
- C. 允许**改用 Google Patents** 并重新生成稿件专利号（当前对稿件号返回空、PDF 桶 403，需另行验证可行路径）。
- 稿件文本内容（申请人/名称/摘要）大概率源自 qcc MCP 真实元数据，但**附图与 PDF 资产在当前无任何可达源下无法获取**。
