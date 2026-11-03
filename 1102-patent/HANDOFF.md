# 工作交接文档（HANDOFF）— 2026 年 10 月互联网专利盘点

> 本文件供「其他 agent / 下一个接手者」使用。包含：任务目标、用户真实意图、关键约束与发现、完整思维链、仓库与工作流状态、当前进度、文件清单、核心代码逻辑、下一步精确命令、已知坑与修复、待决问题。
>
> 维护约定：所有时间戳按 **GMT+8**（北京时间）；**绝不**把 token / cookie / 任何凭证写入仓库或本文档；本文件本身通过 GitHub REST API 推送，不进 `git`。
>
> 最后更新：2026-11-02（北京时间）

---

## 0. 一句话任务

在仓库 `lishuhang/clock` 的新子目录 `1102-patent/` 下，复用一套可复用的 skill 流程，**执行「2026 年 10 月互联网公司专利盘点」**，产出 4 个交付物：

1. **成品稿件** `2026年10月互联网专利盘点.md`（25 篇专利，固定 5 分类模板）
2. **候选专利池** `2026年10月互联网专利盘点_备选专利池.md`
3. **专利 PDF 存档包**（`pdf/` 目录，真实专利原文 PDF）
4. **skill 文件**（可复用流程脚本）

固定 5 分类（顺序不可变）：**音视频相关 / 游戏相关 / AI相关 / 数字人元宇宙 / 公益民生**。

---

## 1. 用户真实意图（关键洞察 — 来自用户原话）

用户在给出真实成品 docx 后明确说：

> “结果是需要专利 pdf 才可以准确摘要，包括找出图片。用比较少的 token 和更多的流程脚本化，构思过程的时候应该 think outside the box。对了把你的思考和工作记录写在 GitHub 的一个工作文档 md 里面，随时准备其他 agent 接手。”

拆解：
- **准确摘要的前提是拿到真实专利 PDF**（PDF 里有原文摘要和附图）；没有 PDF，靠 docx 里那份被二次编辑过的中文摘要去“猜”专利号会大量错配。
- **少 token、多脚本化**：能写成 pipeline 脚本在 runner 上跑的，就不要在主对话里逐条人工查询。主对话只做“编排 + 交接记录”。
- **think outside the box**：本地沙箱环境对专利站点有硬性封锁（见 §3），所以把“下载/检索”这一最重、最易失败的部分整体外包给 **GitHub Actions runner**（无过滤网络）执行，而非在本地死磕。
- **随时可交接**：所有思考与进度都落在本 `HANDOFF.md`，下一个 agent 拿到即可接手。

---

## 2. 关键约束与发现（务必先读）

### 2.1 沙箱代理封锁一切专利二进制源 —— 只能用 runner
- 本地脚本 `resolve_test.py` 访问 `patents.google.com` → 稳定返回 **502 Bad Gateway**（代理层拦截）。
- 结论：**任何对 `patents.google.com` / `patentimages.storage.googleapis.com` 的请求，都必须在 GitHub Actions runner（ubuntu-latest，无过滤外网）上发起**，本地只负责“编排 + 推送文件 + 触发 workflow”。
- `api.github.com` **可以**通过沙箱代理访问 → 所有“读写仓库文件 / 触发 workflow”都用 **GitHub REST API**，不要用 `git clone`/`git push`（代理会 SIGTERM 掉长连接）。

### 2.2 Google Patents xhr 查询结构（本项目最核心的技术发现）
查询端点：
```
https://patents.google.com/xhr/query?url=<urlencode("q=TITLE")>&num=20
```
返回 JSON 结构（注意是**嵌套**的，不是扁平数组）：
```json
{
  "results": {
    "cluster": [
      { "result": [ { "patent": { "title":...,
                                  "snippet":...,        // = 摘要文本
                                  "assignee":...,
                                  "publication_number":..., // 真实公开号
                                  "pdf":...,            // 相对路径，见下
                                  "publication_date":... } } ] }
    ]
  }
}
```
要点：
- 专利对象嵌套在 `results.cluster[i].result[j]["patent"]` 里，**不要**当成扁平 `list[dict]` 取。
- `snippet` 字段就是**摘要文本**（HTML 转义过，需 `html.unescape`）。
- `pdf` 是**相对路径**（如 `"37/0c/15/fcb.../CNxxx.pdf"`），拼成完整 URL：
  `https://patentimages.storage.googleapis.com/pdfs/` + 相对路径。
- `publication_number` 即真实公开号（如 `CN112437342B`、`WO2026031593A1`）。

### 2.3 字段操作符（如 `assignee:"腾讯"`）在 xhr 端点**无效**
- 用 `assignee:"腾讯"` 查询 → 返回**空结果**。xhr 端点不认 web UI 那套字段操作符。
- 必须用**自由文本**：`专利名称 + " " + 公司关键词`，再从结果里用 `kw in assignee` 做归属判定（见 §7 的 `resolve_one`）。

### 2.4 Google 限流是头号障碍
- 一次性发出大量请求（如 24 专利 × 3 策略 ≈ 72 请求）会触发 Google 限流，绝大多数返回空 → `confidence=none`。
- 缓解（已落到代码）：
  - 每个专利**只发 1 次主搜索**（`标题 + 公司关键词`），命中就收。
  - `resolve_one` 内部用 `time.sleep(4~10s)` 做礼貌限速。
  - 用 **`PAT_RANGE` 分批**（如一次只处理 4~6 条）把总请求量摊薄，规避限流。
- 经验值：**单次 run 处理 4~6 条** 最稳；全量 24 条一次跑基本只会解出前几条，后半段全 `none`。

### 2.5 凭证安全（铁律）
- **GitHub Token**：仅通过环境变量 `GHTOK` 注入（运行时），或在本地 `.ghtok` 文件（绝不在仓库内，`.gitignore` 已忽略）。**绝不**写进任何被推送的文件或本 HANDOFF.md。
- **天眼查 Cookie**：仅作为 repo secret `TYCCOOKIE`（NaCl 公钥加密）存放在 GitHub，runner 上解密使用。本任务最终没走天眼查（Google 更直接），但该 secret 已设，保留备用。
- 仓储 `.gitignore` 已忽略 `.cookies/`。

### 2.6 Windows / Python 路径怪癖（Git-Bash 环境下）
- `_push.py` 中的路径用 **Windows 风格** `C:\Users\james\...`，在 Git-Bash 里能正常被 Python 解析。
- Token 用环境变量传，**不要**落到 `/tmp/ghtok`（历史教训：易丢、易误提交）。

---

## 3. 思维链（完整诊断过程，按时间线）

> 这一段把“为什么走到今天这一步”讲清楚，方便接手者不重复踩坑。

1. **起点**：用户要 25 篇 10 月互联网专利盘点，固定 5 分类，且要有**真实专利原文图片 + 打包真实 PDF**。
2. **第一次尝试（本地直连）**：写 `resolve_test.py` 本地查 Google Patents → **502**。确认沙箱代理封锁专利站。
   - → 决策：所有外网专利请求移到 runner。
3. **建立 runner 执行通道**：把 Python 脚本 push 进仓库，配 `.github/workflows/*.yml`，用 `workflow_dispatch` + REST API 触发；脚本在 `ubuntu-latest` 上跑（无过滤外网）。
4. **第一次解析失败**：`AttributeError: 'str' object has no attribute 'get'` —— `search_raw` 把字符串混进了结果列表。
   - → 修复：只保留 `isinstance(j, dict) and j.get("patent")` 的项。
5. **第一次整段挂死（>10min 被取消）**：把“解析 + 下载”写成一个 monolith workflow，下载阶段遇 Google 503 不断退避，直到结束才提交，取消即全丢。
   - → 决策：**拆成两个 workflow**——`resolve.yml`（快、先提交 resolved.json）+ `download.yml`（独立、尽力而为）。
6. **git push 冲突**：runner `git push` 被拒 `! [rejected] ... (fetch first)`（Pages 构建并发推了 main）。
   - → 修复：workflow 加 `concurrency: group: patent-pipeline` + `git pull --rebase` + 用 `x-access-token` 重设 origin。
7. **v3 解析全错（`confidence=none`）**：`resolve_one` 对原始 xhr dict 直接用 `j.get("pub")` 过滤（原始项没有 `pub` 键）。
   - → 修复：遍历结果时统一调 `parse_result(p)` 取 `publication_number`。
8. **v4/v5 解出“错公司”**：误以为 xhr 返回扁平结构 + 用 `assignee:"kw"` 字段操作符。
   - → 重大发现：真实结构是**嵌套 `results.cluster[].result[].patent`**；`assignee:` 字段操作符在 xhr **无效**。
   - → 重写 `parse_result` / `search_raw` / `resolve_one`：解析嵌套 patent；用自由文本 `名称 + 公司kw`；以 `kw in assignee` 判定归属。
9. **v6 更差（14 个 none）**：上多策略（每专利 3 次搜索 × 24）触发更狠限流。
   - → 修复（v7）：每专利只 1 次主搜索 + 单 fallback + 降低请求总量。
10. **v7 编辑引入 `IndentationError`**：重复 `return` + 游离 `time.sleep`（本次交接前已清理，见 §6）。
11. **限流仍是终局瓶颈**：最近一次全量 run（41467041146）只解出 8/24，其余 16 因限流 `none`。
    - → 引入 **`PAT_RANGE` 分批**（本次交接已实装并接进 `resolve.yml` 的 dispatch 输入）——把 24 条拆成 4~6 条/批跑，每批之间隔一段时间触发，逐批吃掉 `none`。

**当前结论**：技术路径已跑通（runner 能解真实公开号 + 摘要 + 相对 PDF 路径），唯一剩余工程问题是“用分批把 16 个 none 解完”。

---

## 4. 仓库与工作流状态（实时核对于 2026-11-02）

仓库：`lishuhang/clock`，工作目录：`1102-patent/`。

### 4.1 目录文件（via API 核对）
| 文件 | 大小 | 说明 |
|---|---|---|
| `.gitignore` | 162 | 忽略 `.cookies/` 等 |
| `2026年10月互联网专利盘点.md` | 18.1K | 成品稿件（初版，待按真实 PDF 重校） |
| `2026年10月互联网专利盘点_备选专利池.md` | 28.8K | 候选专利池（初版） |
| `LOG.md` | 3.6K | 工作日志 |
| `README.md` | 2.7K | 说明 |
| `patents.json` | 16.9K | **输入**：从真实 docx 解析的 24 条专利（含分类/申请人/名称/进度/摘要） |
| `pipeline.py` | 10.2K | **核心脚本**：`resolve` / `download` 双模式（v7 + 本次 PAT_RANGE 增强） |
| `resolved.json` | 35.4K | **输出**：解析结果（24 条，8 有 pub，16 none） |
| `debug.json` / `dl.py` / `gtry.py` / `probe.py` / `gtry_report.txt` / `probe_report.txt` | — | **遗留调试脚本**，可忽略/后续清理 |

### 4.2 工作流（workflows）
| 文件 | id | 触发 | 作用 |
|---|---|---|---|
| `.github/workflows/resolve.yml` | 404354550 | push(patents.json/pipeline.py/resolve.yml) 或 `workflow_dispatch`（含 `pat_range` 输入） | `python3 pipeline.py resolve` → 提交 `resolved.json` |
| `.github/workflows/download.yml` | 404354619 | push(resolved.json) 或 `workflow_dispatch` | `python3 pipeline.py download` → 下载真实 PDF 到 `pdf/`，提交 |
| 遗留：`download-patents.yml`(404248686) / `gtry.yml`(404275710) / `probe.yml`(404259231) / `cruise-bot.yml`(383321849) | — | — | 旧链路，建议清理 |

> 注：`download.yml` 至今**未成功跑过一次**（没有产生过有效 PDF 提交），因为此前 resolved 阶段还没稳定产出 `ok` 条目。

### 4.3 密钥
- repo secret `TYCCOOKIE`：已设（NaCl 加密），天眼查备用，当前未使用。
- GitHub Token：仅通过 `GHTOK` 环境变量在本地 `_push.py` 使用，不进仓库。

---

## 5. 当前进度（实时核对）

`resolved.json`：24 条，分布 `{'company': 2, 'assignee': 6, 'none': 16}`，`downloaded=None`。

### 5.1 已解出真实公开号（8 条）
| confidence | 公开号 | 申请人(docx) | 真实标题 |
|---|---|---|---|
| assignee | WO2026031593A1 | 湖南快乐阳光互动娱乐传媒有限公司 | 一种动态视频生成方法及装置、电子设备、存储介质 |
| assignee | CN112437342B | 上海哔哩哔哩科技有限公司 | 一种视频编辑的方法及设备 |
| assignee | CN122513157A | 上海哔哩哔哩科技有限公司 | 回源服务抗毁切换控制方法、流媒体数据转推控制方法及系统 |
| assignee | CN112235530B | 网易（杭州）网络有限公司 | 远程会议的实现方法及装置、电子设备、存储介质 |
| assignee | CN113559518B | 网易（杭州）网络有限公司 | 虚拟模型的交互检测方法、装置、电子设备及存储介质 |
| assignee | WO2022252911A1 | 腾讯科技（深圳）有限公司 | 虚拟场景中召唤对象的控制方法、装置、设备、存储介质及程序产品 |
| **company** | **EP3964933B1** | 上海爱奇艺新媒体科技有限公司 | **Display method and electronic device**（⚠ 弱匹配，需人工核对是否对应“自动拆解爆款/翻拍AI短片”） |
| **company** | **AU2020274322B2** | 北京优酷科技有限公司 | **Process and apparatus for estimating rea...**（⚠ 弱匹配，需人工核对） |

> ⚠ **2 个 `company` 条目是“按申请人检索命中该公司某专利”，但标题与 docx 描述未必一致**，必须人工核对（用 `candidates` 字段里同申请人的其他结果挑更贴切的）。

### 5.2 仍未解出（16 条，索引 8~23，本次分批的重点）
| idx | 申请人(docx) | docx 专利名（节选） |
|---|---|---|
| 8 | 上海鹰角网络科技有限公司 | 摆兵前先看它往哪走 |
| 9 | 咪咕互动娱乐有限公司 | 多人体感识别按需调精度 |
| 10 | 优酷文化科技（北京）有限公司 | 剧本审稿无需“提示词工程师” |
| 11 | 百度在线网络技术(北京)有限公司 | 智能体干活“所见即所得” |
| 12 | 腾讯科技（深圳）有限公司 | 虚拟角色自己发朋友圈 |
| 13 | 腾讯科技（深圳）有限公司 | 计数过程中睡着了？AI补齐数据 |
| 14 | 腾讯科技（深圳）有限公司 | AI看图自动挑重点 |
| 15 | 北京优酷科技有限公司 | 数字人/元宇宙 |
| 16 | 北京字跳网络技术有限公司 | 虚拟场景里拖时间轴出短片 |
| 17 | 腾讯科技（深圳）有限公司 | 把“变声道具”扔进虚拟房间 |
| 18 | 北京字跳网络技术有限公司 | 3D模型转身渲染提速 |
| 19 | 金山办公 | 数字分身代你回消息 |
| 20 | 腾讯 | 进风险区就强制下线 |
| 21 | 青岛海尔多媒体有限公司 | 摸电视能摸到画面 |
| 22 | 荣耀终端股份有限公司 | 不看的小窗自动降帧省电 |
| 23 | 美团科技有限公司 | 手机管无人机装货放飞 |

### 5.3 数量对账（重要待办）
- docx 内按分类统计为 **音视频相关 5 + 游戏相关 5 + AI相关 11（含数字人/元宇宙 ×2）+ 公益民生 4 = 25** 篇。
- 但 `patents.json` 只解析出 **24** 条 → **少 1 篇**。需重新解析 docx 确认是否漏了一篇（很可能某条标题/结构没被正则抓到），补齐到 25 再继续。

---

## 6. 核心代码逻辑（接手者速读）

### 6.1 `pipeline.py` 两个模式
- `python3 pipeline.py resolve`：读 `patents.json` → 对每条用 Google xhr 解真实公开号/摘要/申请人 → 写 `resolved.json`。
- `python3 pipeline.py download`：读 `resolved.json` → 对每条 `ok` 的专利，预热 cookie 后下真实 PDF 到 `pdf/<pub>.pdf`。

### 6.2 关键函数
- `parse_result(p)`：从嵌套 patent 对象抽 `pub/publication_number`、`title`、`abstract`(=unescape(snippet))、`assignee`、`pubdate`、拼出 `pdf` 完整 URL。
- `search_raw(query, num)`：构造 xhr URL，重试 3 次；解析嵌套 `cluster[].result[].patent` 为 items 列表。
- `resolve_one(name, kw)`：
  1. 主搜索 `name + " " + kw`（自由文本，1 次）；
  2. 命中 `kw in assignee` → `confidence="assignee"`（最可信）；
  3. 否则标题子串命中 → `"title_sub"`；
  4. 兜底：仅 `kw` 搜公司，按 `assignee`/`title` 命中挑 → `"assignee"`/`"company_title"`/`"company"`；
  5. 都没有 → `"top"` / `"none"`。
- `download_pdf(pub, pdf_hint)`：先访问专利 HTML 页让 cookie 落地 → 依次试 `pdf_hint` 和 `.../patent/<pub>/PDF` → 校验 `data[:4]==b"%PDF"` → 存 `pdf/<pub>.pdf`，3 次指数退避。

### 6.3 本次交接新增：`PAT_RANGE` 分批 + 增量合并
- `do_resolve()` 现在读 `PAT_RANGE` 环境变量（如 `"8:14"`）只处理该索引区间。
- **区间外的条目保留 `resolved.json` 中已有结果（增量合并）**，不会覆盖已解出的专利。
- `resolve.yml` 已加 `workflow_dispatch.inputs.pat_range`，可通过 REST API 传 `inputs.pat_range` 触发分批。

> ⚠ **严禁**直接跑“全量 resolve”（不设 PAT_RANGE）。一次全量 24 条会因限流把已有 8 条也冲掉成 `none`。永远用分批。

---

## 7. 下一步精确命令（接手者照做）

### 步骤 A：补齐缺失的第 25 篇
1. 重新解析用户真实 docx（本地用 `python-docx` 或 WorkBuddy 的 pdf/docx 解析能力），确认是否真有 25 篇、哪篇漏了。
2. 把漏的那条补进 `patents.json`（保持现有字段：`category/applicant/patent_name/title/progress/summary`）。
3. 推送 `patents.json`（见步骤 C 的推送方式）——这会触发 `resolve.yml` 全量重新解析（危险！见 ⚠）。
   - **更安全**：先本地把 `patents.json` 补齐到 25，再单独为新增那条用 PAT_RANGE 跑一次，或等全部 24 解完后单独补。

### 步骤 B：分批解出剩余 16 个 none（核心工作）
对每个区间，用 REST API 触发 `resolve.yml` 并传入 `pat_range` 输入（区间外会自动保留已有结果）：

```bash
# 在本地（沙箱代理可达 api.github.com）执行，TOKEN 用 GHTOK 环境变量
# 分批区间建议（覆盖索引 8~23，每批 ≤6 条；索引 0~7 已解，不必重跑）：
#   "8:14"   "14:20"   "20:24"
# 触发命令（示例，批 1）：
curl -X POST \
  -H "Authorization: Bearer $GHTOK" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/lishuhang/clock/actions/workflows/resolve.yml/dispatches \
  -d '{"ref":"main","inputs":{"pat_range":"8:14"}}'
```
- 每批跑完看 `resolved.json` 是否新增了 `ok` 条目；若某批仍有 `none`，隔几分钟再补跑该批（或拆更细如 `"8:11" "11:14"`）。
- 也可用本地 `_push.py` 的 `dispatch` 思路改造成支持 `inputs` 的版本（当前 `dispatch()` 不传 inputs，需小改）。
- 每批之间**间隔几分钟**，避免 Google 把同一 IP 限流。

### 步骤 C：推送/更新文件的方式（不进 git，走 REST API）
本地 `_push.py` 封装了 `put_file` / `set_secret` / `dispatch`（`STAGE = C:\Users\james\WorkBuddy\clock_staging`）。例：
```bash
cd C:/Users/james/WorkBuddy/clock_staging
GHTOK=<你的token> python3 -c "import importlib.util,sys; spec=importlib.util.spec_from_file_location('p','_push.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.put_file('pipeline.py','1102-patent/pipeline.py','feat: PAT_RANGE batching'); m.put_file('resolve.yml','.github/workflows/resolve.yml','ci: pat_range input')"
```
（也可直接按 `_push.py` 的 REST 逻辑写小脚本。）

### 步骤 D：下载真实 PDF
全部 24/25 条解出后，触发一次 `download.yml`（手动 dispatch，不必带输入）：
```bash
curl -X POST -H "Authorization: Bearer $GHTOK" -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/lishuhang/clock/actions/workflows/download.yml/dispatches \
  -d '{"ref":"main"}'
```
它会读 `resolved.json`，把每条 `ok` 的真实 PDF 下到 `pdf/<pub>.pdf` 并提交。若部分失败，重跑即可（已下载的会被覆盖，无害）。

### 步骤 E：重生成 4 个交付物
1. 用 `resolved.json` 里**真实的 `abstract_real`** 替换 docx 摘要里的二手中文摘要，确保准确。
2. 用真实 PDF 提取**原文附图**，嵌入稿件（不是自绘）。
3. 按固定 5 分类重排 25 篇 → 更新 `2026年10月互联网专利盘点.md` 与 `_备选专利池.md`。
4. 把整条 `pipeline.py` + `resolve.yml` + `download.yml` 收尾为可复用 **skill**。

---

## 8. 已知坑与修复记录（排查用）

| 现象 | 根因 | 修复 |
|---|---|---|
| 本地查 Google → 502 | 沙箱代理封锁专利站 | 全改在 runner 执行 |
| `AttributeError: 'str' has no attribute 'get'` | search_raw 混入字符串元素 | 仅保留 `isinstance(j,dict) and j.get("patent")` |
| 整段 >10min 挂死被取消 | 解析+下载合一，下载遇 503 死退避 | 拆 `resolve.yml` / `download.yml` |
| `git push` rejected `fetch first` | Pages 构建并发推 main | `concurrency` + `git pull --rebase` + token origin |
| v3 全 none | 对原始 xhr dict 用 `j.get("pub")` 过滤 | 统一 `parse_result()` |
| v4/v5 解出错公司 | 误用扁平结构 + `assignee:` 操作符 | 改解析嵌套 patent + 自由文本 + `kw in assignee` |
| v6 更差（14 none） | 3 策略 ×24 触发限流 | 每专利 1 主搜 + PAT_RANGE 分批 |
| v7 `IndentationError` | 编辑残留重复 return | 本次交接清理，并加 `_placeholder` + 增量合并 |
| `company` 弱匹配 | 仅按申请人命中，标题未必对应 | 人工核对 `candidates` 字段 |
| 全量 resolve 冲掉已解 | 旧 do_resolve 整体覆盖 | 新增区间外保留（增量合并） |

---

## 9. 待决问题 / 风险

1. **数量对账**：docx 25 篇 vs `patents.json` 24 条，缺 1 篇，需补齐（§5.3 / 步骤 A）。
2. **2 个 `company` 弱匹配**需人工核对（爱奇艺 EP3964933B1、优酷 AU2020274322B2）。
3. **Google 限流**仍是主要不确定性；分批节奏要靠实测微调（每批 ≤6，批次间隔几分钟）。
4. **真实 PDF 下载尚未实证成功过**（download.yml 没跑出过 PDF），`download_pdf` 的 cookie 预热 + Referer 逻辑需首次实战验证；若 403/503 持续，可能要换 `pdf_hint` 直链或加更长退避。
5. **遗留调试脚本/旧 workflow** 建议清理，避免误导。
6. 仓库 secret `TYCCOOKIE`（天眼查）当前未用，保留备用；若 Google 路径受阻，可评估天眼查作为公开号检索的备线。

---

## 10. 附注：用户真实成品（source of truth）

- 文件：`C:/Users/james/Downloads/10月互联网专利盘点.docx`（用户提供的真实成品，标题《爱奇艺帮你自动拆解爆款，翻拍AI短片｜10 月互联网专利盘点》，作者 木目）。
- 结构：每篇含 **专利申请方 / 专利名称 / 申请进度 / 专利摘要**，含 25 张嵌入式 PNG 附图，**无专利公开号**（所以才需要去 Google Patents 反查真实号）。
- 该文件在用户本机，可能不持久；若丢失，需向用户重新索取，它是所有准确性判断的基准。

---

## 11. 快速接手清单（checklist）

- [ ] 重新解析 docx，确认 25 篇并补齐 `patents.json` 缺失的 1 篇
- [ ] 推送更新后的 `pipeline.py`（已含 PAT_RANGE + 增量合并）与 `resolve.yml`（已含 pat_range 输入）
- [ ] 分批触发 resolve：`"8:14"` → `"14:20"` → `"20:24"`，间隔几分钟，直到 none 清零
- [ ] 核对 2 个 `company` 弱匹配条目
- [ ] 触发 `download.yml` 下载真实 PDF 到 `pdf/`
- [ ] 用真实 `abstract_real` + 真实附图重生成两份 md 稿件
- [ ] 收尾为可复用 skill
- [ ] 清理遗留调试脚本与旧 workflow
- [ ] 全程 **不提交任何 token / cookie**，本文档随进度更新并推送

> 接手者有任何进展/卡点，直接更新本 `HANDOFF.md` 对应小节并推送即可，保持交接链不断。
