# 事实核查门禁（references/facts-gate.md）

> 目标：防止编造数据与算错衍生指标（实测翻车案例：参保人数÷离退休人数算"抚养比"心算错误；"充值 4556 vs 4856"口径打架）。**门禁不过，禁止进入分镜阶段。**

## 一、facts_ledger.json 格式（Step 1 产物）

```json
[
  {
    "claim": "10家平台充值门槛中位数是万兴剧厂的399元",
    "raw_inputs": "万兴剧厂专业版包月 399 元；10 家门槛排序后第 5/6 位",
    "formula": "median([218,299,375,399,...])",
    "source_url": "netdisk:/1-价格/万兴剧厂/充值/万兴剧厂-充值价格.png + 成品稿件价格篇",
    "exact_quote": "10家平台充值门槛的中位数是万兴剧厂的399元",
    "is_estimated": false,
    "verification_status": "verified"
  }
]
```

字段硬规则：
- `claim`：口播里实际说出的每个数字/结论，一条不漏
- `raw_inputs` + `formula`：可被 Python 重算的表达式（心算禁止）
- `source_url`：网盘路径 / 文章段落 / 官方链接三选一，**禁止空**
- `is_estimated: true` 的条目，画面必须自动打"\*推算/示意"角标（模板已支持）
- `verification_status` 只允许 `verified / vector / estimated / override`（沿用信息图 skill 口径；override 须写理由）

## 二、验算脚本逻辑（可并进 env_check 或独立跑）

1. 逐条 `eval(formula)`（安全子集：四则/median/max/min/round），与 claim 中数字比对
2. 所有 source_url 非空且可定位（网盘路径存在 / URL 可达）
3. 同一事实在多集出现时做**口径一致性检查**（例：总充值额在 V1/V3 必须同源同值，打架则列为"口径矛盾"交用户裁决，**不静默改数**）
4. 引用外部事实（《牌子》播放量、人物身份等）须附检索来源与日期；检索不到的降级为"文案原话转述"并标注

## 三、画面数字三原则

1. 图表数字必须能回指 source-data.csv 的 verified 行（信息图管线产物直接复用）
2. 示意性数据（非实测，如"废片率对比"）必须打角标，禁止与实测数字同版式混排
3. 汇率/时价类数字标注口径日期（例："10-05 锁定价"）

## 四、红线（出现即整片打回）

- 画面数字与口播数字不一致
- 无出处的具体数字（尤其钱、百分比、排名）
- 把 estimate/示意 冒充 verified
- 口径矛盾未在 production-report 列明就交付
