# TODO 0714-2235 - 交接给新agent（有VLM额度）

> 交接时间：2026-07-14 22:35 (北京时间)
> 上一个agent：GLM agent (从前向后处理，VLM额度耗尽)
> 状态：⏸️ 等待新agent接手

## 一句话简报

VLM额度耗尽，需新agent接手。当前114711视频处理到段83/122(68%)，819行已识别。剩余39段+1个完整视频待处理。完成后重新生成xlsx和v3稿件图表。

## GitHub仓库信息

- Repo: lishuhang/clock
- 工作文件夹: 0713-bed-short-drama/
- Token: [GITHUB_TOKEN_7day] (7天有效)
- 备用Token: [GITHUB_TOKEN_30day] (30天有效)
- Branch: main

## 当前进度

### ✅ 已完成视频（24个GLM + 4个qwen = 28个）

GLM已完成24个（per-video JSON均在GitHub的 scripts/results/ 目录）：
- 20260519_161651.mp4 (支付宝, 313行)
- 20260519_164321.mp4 (拼多多, 390行)
- 20260519_170132.mp4 (美团, 359行)
- 20260519_171050.mp4 (红果, 422行)
- 20260519_181604.mp4 (支付宝, 329行)
- 20260519_182323.mp4 (快手, 268行)
- 20260519_183231.mp4 (拼多多, 348行)
- 20260519_184314.mp4 (美团, 304行)
- 20260519_185112.mp4 (红果, 383行)
- 20260519_185956.mp4 (支付宝, 296行)
- 20260519_190612.mp4 (快手, 265行)
- 20260519_224053.mp4 (拼多多, 381行)
- 20260519_230119.mp4 (美团, 405行)
- 20260519_231329.mp4 (红果, 366行)
- 20260519_232140.mp4 (支付宝, 326行)
- 20260519_232942.mp4 (快手, 226行)
- 20260519_233619.mp4 (拼多多, 319行)
- 20260519_235318.mp4 (快手, 327行)
- 20260520 183705美团.mp4 (美团, 250行)
- 20260520 184407支付宝.mp4 (支付宝, 255行)
- 20260520 185229红果.mp4 (红果, 342行)
- 20260520_000104.mp4 (红果, 344行)
- 20260520_023737.mp4 (美团, 313行)
- 20260520_024604.mp4 (拼多多, 353行)

qwen已完成4个：
- sh-红果.mp4 (20行), sh-美团.mp4 (17行), sh-快手2.mp4 (131行), sh-支付宝.mp4 (25行)

### ⏳ 进行中（1个）— 需新agent继续

**20260519_114711-拼多多.mp4**（拼多多，122段）
- 当前进度：段83/122 (68%)，819行已识别
- VLM于北京时间14:20返回429限流，持续未恢复
- 视频文件已解压到 /tmp/vidwork/20260519_114711-拼多多.mp4 (279MB)
- per-video JSON在GitHub: scripts/results/20260519_114711-拼多多.json

**继续处理命令（从段83开始）：**
```
cd /home/z/.bun/install/global && timeout 150 bun /home/z/my-project/work/scripts/process_segment_v6.js "20260519_114711-拼多多.mp4" 83
```
逐段处理直到 segment 121（最后一段），videoComplete=true。

### ❌ 待处理（1个）— 需新agent处理

**20260520 183107pdd.mp4**（拼多多，2个zip分卷）
- 视频分卷在GitHub: 0713-bed-short-drama/rest-vid/20260520 183107pdd.zip.001 和 .002
- 下载合并解压：
```
cd /tmp/vidwork
TOKEN="[GITHUB_TOKEN_7day]"
for ext in 001 002; do
  fn="20260520 183107pdd.zip.$ext"
  encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('0713-bed-short-drama/rest-vid/$fn'))")
  curl -sL -H "Authorization: token $TOKEN" "https://raw.githubusercontent.com/lishuhang/clock/main/$encoded" -o "$fn"
done
cat "20260520 183107pdd.zip.001" "20260520 183107pdd.zip.002" > merged_pdd.zip
unzip -o merged_pdd.zip -d /tmp/vidwork/
```
- 然后处理：
```
cd /home/z/.bun/install/global && timeout 150 bun /home/z/my-project/work/scripts/process_segment_v6.js "20260520 183107pdd.mp4" 0
```

## 本地工作区状态

路径: /home/z/my-project/work/
- scripts/ — 所有处理脚本（process_segment_v6.js, build_merged_xlsx.py, v3_analysis.py, generate_v3_manuscript.py, generate_v3_charts.py, upload_v3.py）
- output/ — 生成的xlsx和分析JSON
- results/ — 29个per-video JSON（已同步GitHub）
- v3/ — v3稿件和图表（基于28段，待114711和183107完成后需更新）
- info/ — qwen xlsx

**注意**：脚本中的TOKEN已替换为实际值。process_segment_v6.js的TODO_DIR已改为"0713-bed-short-drama/rest-vid"。

## 完成全部视频后的操作

### 1. 重新生成合并xlsx
```
cd /home/z/my-project/work && python3 scripts/build_merged_xlsx.py
```

### 2. 更新v3分析脚本中的xlsx路径
编辑 scripts/v3_analysis.py，将 V2_XLSX 路径改为最新生成的xlsx文件。

### 3. 重新运行v3分析
```
cd /home/z/my-project/work && python3 scripts/v3_analysis.py
```

### 4. 重新生成v3稿件
```
cd /home/z/my-project/work && python3 scripts/generate_v3_manuscript.py
```

### 5. 重新生成v3图表
```
cd /home/z/my-project/work && python3 scripts/generate_v3_charts.py
```

### 6. 上传v3到GitHub
```
cd /home/z/my-project/work && python3 scripts/upload_v3.py
```

## v3关键数字（基于当前28段，待更新）

当前v3基于28段已识别视频：
- 合并后片段数：1069个
- 含亲密戏片段数：142个
- 独立短剧数：818部

完成114711（819行→预计约1300行）和183107pdd后，数字会更新。

## 注意事项

1. VLM可能再次429限流，如遇到需等待恢复（通常短时5-10分钟，或第二天零点）
2. 每段处理约30-90秒，超时用 timeout 150 包裹
3. 段处理失败（500/1210/1301）会返回0行但不影响进度推进
4. bash工具偶尔超时，重启会话即可恢复，进度在GitHub不会丢失
5. process_segment_v6.js会自动上传per-video JSON到GitHub

## 交接班Prompt（给新智能体）

请读取GitHub仓库lishuhang/clock的0713-bed-short-drama/todo-0714-2235-handoff.md交接文档（token: [GITHUB_TOKEN_7day]），继续处理未完成的短剧录屏视频。当前114711视频在段83/122，剩余39段+1个完整视频(20260520 183107pdd.mp4)待处理。每完成一个视频就运行build_merged_xlsx.py重新生成合并xlsx并上传GitHub。全部处理完后，重新运行v3_analysis.py、generate_v3_manuscript.py、generate_v3_charts.py、upload_v3.py生成最终v3稿件和图表。
