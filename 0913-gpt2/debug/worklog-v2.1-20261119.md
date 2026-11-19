# 工作日志 — kmage-kdr-rapi-2.0 → 2.1 迭代（2026-11-19）

> 本文件为本次任务的工作记录备份（防 workspace 崩溃），随进度持续更新。
> 任务指令原文（2026-11-19）：
> 1. 排除 https://gpt2.lishuhang.com/ 的各通道故障
> 2. rapi 通道不支持参考图 → 选择该通道时禁用面板的参考图输入
> 3. 其他通道的残留功能在设置面板中保留但已冗余的，可以去除
> 4. 在 v2ex 等地搜索新的免费生图通道及同类资源，尝试增加新通道
> 5. 更新版本号、readme、changelog；直接在线上部署、测试完备无bug
> 6. 备份新版 worker js
> 补充指令：`clock/0913-gpt2` 为唯一工作文件夹，产物与中间件不外放；及时备份工作记录。

## 凭据（用户提供）

- GitHub token（名称 261023-glm）：`ghp_zzWo…VGBcP`（帐号 lishuhang，可推 clock 仓库）
- Cloudflare token：`cfat_LpiT…Vciwe405d570`（用于 Workers 部署，worker 名 ai-image，域 gpt2.lishuhang.com / ai-image.lishuhang.workers.dev）

## 已完成

### 1. 定位仓库与现状（完成）

- 仓库 `lishuhang/clock`（7.8GB，用 `--filter=blob:none --sparse-checkout 0913-gpt2` 稀疏克隆）
- 工作目录：`/home/z/my-project/clock/0913-gpt2/`
- 现网版本 `kmage-kdr-rapi-2.0`，文件 `gpt2-worker-kmage-v2.0.js`（262994 B，3552 行）
- 全量通读源码完毕（结构：1-204 头注释 / 206-975 后端+路由 / 977-1452 HTML+CSS / 1453-3552 前端 JS 三段 script）
- 关键常量：`VERSION=kmage-kdr-rapi-2.0`；UPSTREAM=image.dddd.zone；KDR_UPSTREAM=keydraw.97api.com；RAPI_UPSTREAM=routerapi.net；RAPI_CANVAS=image.routerapi.net；RAPI_TRIAL_KEY=sk-QJD2…（v2ex t/1240321 公开共享 Key）

### 2. 上游诊断（进行中，shell 曾崩溃约 20 分钟已恢复）

| 通道 | 实测（2026-11-19 ~01:30 UTC） | 结论 |
| --- | --- | --- |
| kmage | `POST /v1/images/generations` 假 Key → 401 `invalid_api_key`（契约正常响应） | 上游存活、契约未变；免费生图仍在充值闸门后（v1.7 已归类，历史遗留，非新故障） |
| kdr | `GET /api/gift-key` → 200 `{"alias":"GO-ON-GOODLUCK","key":"GO-ON-GOODLUCK"}` | 上游存活、仍会员制占位符（v2.0 已标注待命，非新故障） |
| rapi | `POST /api/rapi/trial-session`（经 Worker）→ 200 `{credential:JWT, enabled:true, max_concurrent_images:5, max_images:1}`；直连上游带 Canvas Origin 同样 200 | 会话换发正常；生图全流程（generations→tasks/batch→图床）待测 |

- rapi 生图流程测试被 shell 崩溃中断，待重测
- RouterAPI v2ex 原帖（t/1240321）活跃至 2026-11-18，试用 Key 未停发（第 1 页回复确认；9月曾有滥用限流调整但恢复）
- v2ex 站内搜索「生图」被重定向到搜索引擎技术研究节点，无有效结果；sov2ex API 超时（待重试）

### 3. 源码结构要点（为改动作参考）

- 通道切换：`switchChannel()` / `applyChannel()`（约 1733 行起）；`sizeRowKdr`（分辨率档 kdrSize）当前对 kdr 和 rapi 都显示——但 `generateRapi` 只用 ratio 映射 size，`kdrSize` 对 rapi 是**冗余 UI**
- `generateRapi`（约 2947-3010 行）：body={model,prompt,n,size}，**不用 quality**（精细度对 rapi 也是冗余 UI）；参考图当前是「忽略并提示」（appLog 警告），用户要求改为**禁用输入**
- 参考图 DOM：`<label class="f">参考图…</label><div class="ref-list" id="refList">`（约 1288-1292 行）→ 需包一层容器便于整体隐藏
- kdr 设置分区（设置面板内）：Gift Key 行（`giftKeyAlias`/`btnRefreshGift`）+ 自定义 Key textarea（`kdrCustomKeys`）——kdr 已会员制待命，二者为**冗余残留**候选；相关 JS：`ensureGiftKey`/`renderGiftLine`/`switchChannel` 内 `ensureGiftKey(true)`/`bindEvents` 内绑定（约 3406 行起）/`exportSettingsAll` 导出含 kdr 字段（数据模型保留兼容）
- 历史版本文件命名规范：`gpt2-worker-kmage-v{X.Y}.js`；README 含完整迭代时间线（正序）+ 顶部「最后更新」日期；todo-gpt2-full-1024-1430.md 为交接文档
- 工程坑（源码头注释「工程坑防守」）：DOM 元素删除后 JS 引用需 null guard；无状态原则（不引 KV）；脱敏原则（对外文档不写真实上游地址，仅 /about 提供）

### 2.5 新通道调研（2026-11-19 完成，结论：无一可接入）

调研途径：v2ex「生图」标签聚合页全量扫帖（2026-09~11）、sov2ex 全文检索、z-ai web_search、linux.do 与 NodeSeek（均登录墙）、候选站前端 bundle 逆向。

| 候选 | 域名 | 淘汰原因 |
| --- | --- | --- |
| Midalo API（t/1250311/t/1254216） | agent.midalo.ai | 免费 $2-5 需 QQ 群人工认领，一次性 |
| 麋鹿云（t/1231045） | moosecloud.cc | 兑换码 20 个当天领完，追加需人工加群 |
| 优米 API（t/1257341） | api.uxmio.com | 纯付费（¥0.01/张），无免费证据 |
| zimage.run（t/1182699） | zimage.run | 无 API 纯网页；用户反馈卡死闪退 |
| gpt-image-2.me（t/1207873） | gpt-image-2.me | 无 API，注册仅 5 积分 |
| happy-horse.tv（t/1209172） | happy-horse.tv | 无 API，零回复无佐证 |
| pai.zaiduyu.top（t/1251127） | pai.zaiduyu.top | 无 API（回复确认纯网页），5000 积分≈33 张 |
| miaosf（t/1254988，活跃） | miaosf.com→miaosf.rsod.top | better-auth + **Turnstile 验证码 + 邮箱 OTP 验证 + 邀请码**三重门槛；50 张一次性；bundle 逆向确认 |
| liuliuqiu.net/imagegen（t/1222012#53） | liuliuqiu.net | FastAPI 任务制但全端点需登录，注册契约未见免验证路径 |
| 猫图AI（t/1216905） | catsapi.com→artart.icu | **邮箱验证码注册**（/api/auth/register/send-code）阻断自动化；积分靠回帖人工送 |
| imagegoai（t/1254372） | imagegoai.com | 电商垂直 SaaS 无 API，新号仅 3 张 |
| MossImage（t/1251081） | getmossimage.com | 无 API；每日 2 积分带水印 |
| MiniMax H3 工具（t/1256012） | minimaxh3img.com | 无 API 无免费说明 |
| 爱图工坊（t/1246030） | （网页工作台） | 无 API，免费状态不明 |
| pikpikgo（t/1242510） | pikpikgo.com | 商业 C 端站无免费 |
| DSH 生图算力（t/1257442） | github.com/nanxfu/dsh-our-imagen | Kaggle/Colab 自跑 notebook，无服务端 API（同类资源可记档） |
| 大香蕉/nano-banana 系中转（t/1182765 等） | 多家 | 均付费中转（¥0.05-0.12/张） |

**结论**：2026-11 时点，v2ex 等社区在推的免费生图服务全部落在「无 API / 人工赠送 / 验证码墙 / 一次性额度 / 纯付费」五类中，唯一符合本工具「共享凭据 + 每日续给 + 可程序化」模式的仍是 RouterAPI（已接入为 rapi）。调研过程与结论写入 v2.1 README（备后续复查，避免重复劳动）。

## 完工状态（2026-11-19 11:00 GMT+8）

全部任务完成：

- [x] 三通道诊断（rapi 健康 / kmage 付费墙-上游策略 / kdr 免费档会员制+付费 Key 路径实测通畅）
- [x] 新通道调研（20+ 候选无一可接入，全表记档 README v2.1 节 Survey）
- [x] rapi 参考图禁用 + 精细度/分辨率档隐藏 + rapi 提示词必填（applyChannel 通道裁剪）
- [x] 设置面板清理（Gift Key 行移除、付费 Key textarea 保留、徽章/文案/预取更新）
- [x] 版本号 6 处 2.1；README/关于文档/时间线/头部注释//about notes_v2_1 全同步
- [x] 结构自检 36/36（debug/selfcheck-v2.1.js）+ node --check 通过
- [x] CF 部署（02:19:09Z success）+ 线上测试：/healthz /about /sw.js manifest、无头浏览器三通道切换/设置面板/关于渲染/零错误、生产 E2E rapi 生图 33.0s completed（截图 debug/e2e-rapi-v2.1-20261119.png）
- [x] 备份：gpt2-worker-kmage-v2.1.js + README + todo-gpt2-full-1119-1100.md（v2.0 部署前现网脚本与仓库 v2.0 逐字节一致，回滚源即 gpt2-worker-kmage-v2.0.js；本地另存 debug/deployed-v2.0-backup-20261119.js，因完全重复未提交仓库）

## 待办（更新）

- [ ] rapi 生图全流程实测（generations→tasks/batch→图床 b64）
- [ ] kmage 注册端点复测（净号直注链是否仍通）
- [ ] v2ex/sov2ex 再搜新免费生图通道（含 NodeSeek、Linux.do 同类）
- [ ] 代码修改：rapi 禁用参考图输入（applyChannel + 容器包装）
- [ ] 代码修改：冗余 UI 清理（rapi 下隐藏 kdrSize/quality；kdr 设置分区 Gift Key 行与自定义 Key textarea 处理）
- [ ] 若找到可用新通道：新增通道
- [ ] 版本号 → 2.1；README/changelog/「关于」文档同步；SW cache 版本同步
- [ ] Cloudflare API 部署 + 线上逐项测试
- [ ] 备份 gpt2-worker-kmage-v2.1.js 到仓库 + 推送 GitHub

## 环境事件记录

- 2026-11-19 ~01:35 UTC：Bash 工具持续 `spawn /usr/bin/bash ENOENT` 约 20 分钟（疑似 sandbox 回收），期间用 Read/WebFetch 工具继续源码通读与 v2ex 调研；01:44 恢复
- 期间 `/home/z/my-project/clock` 稀疏克隆曾被清空，已重新克隆并校验文件一致；`work/` 中间目录已按用户指令并入 `clock/0913-gpt2` 并删除
