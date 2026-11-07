# 解耦管线与废墟重启协议（references/decoupled-pipeline.md · v2.3 新增）

> 来源：2026-11-07 用户解耦指令——"一些过程交给脚本，另一些交给其他模型；可以只生成所有
> 带外链素材的 html 按顺序播放，录屏、合并、调速、加字幕、加水印交给脚本，且可指定停留在
> 任何一个步骤（不运行某个子脚本）；分步优化节省 token、避免已固化步骤重造轮子导致效果
> 不一致；任何时候可从 workspace 废墟重启回到原有进度。"
> 参考实现：1105 工程 `scripts/pipeline.py` + `PIPELINE-DECOUPLE.md`（实测：沙盒全损后
> clone→check 三集 PASS→136 镜重截帧→重组装，零素材重下零动效重做）。

## 一、职责三分（谁干什么）

| 层 | 职责 | 执行者 | 烧 token？ |
|---|---|---|---|
| 创意层 | 选题/文案/分镜/事实核查/**H5 页面制作** | AI（宿主或**外部模型**，按 h5-spec.md 契约逐镜可替换） | 是 |
| 数据层 | shots JSON（时间轴）/字幕权威卡/clips 切片+MANIFEST/配音/assets | 工程仓=唯一事实源，一次生成多次复用 | 生成时一次 |
| 机械层 | check 齐全性/render 截帧/assemble 总装15段/deliver 归档 | **脚本**（pipeline.py 统一编排，零 token） | 否 |

**核心判断法**：这件事的产出是"创意决策"还是"可复现的机械变换"？前者给模型（可换更好的），
后者给脚本（跑多少遍结果都一样）。水印/裁切/变速/字幕/响度/质检全部属于机械层。

## 二、统一运行器接口（每个项目应提供 `scripts/pipeline.py`）

```
python3 scripts/pipeline.py --list                    # 三集步骤×状态总览（废墟重启第一命令）
python3 scripts/pipeline.py --ep 1                    # 单集全流程 check→render→assemble→deliver
python3 scripts/pipeline.py --ep all --from render    # 从某步开始
python3 scripts/pipeline.py --ep 3 --to assemble      # 跑到某步为止（指定停留）
python3 scripts/pipeline.py --ep all --steps check,render   # 只跑指定步
python3 scripts/pipeline.py --ep 1 --skip render      # 跳过某步
python3 scripts/pipeline.py --ep 1 --segments subs,subs_h,qc     # 只重跑总装某几段
python3 scripts/pipeline.py --ep 2 --only-shots S07   # render 只重截指定镜（换 H5 后）
```

assemble 标准段序（幂等，每段可独立重跑）：
`setup(对账) → bg(切片叠底) → seq(帧序列) → enc(逐镜编码) → cat(拼接) → final/final_h(水印/裁切) → audio(混音响度) → mux/mux_h → speed/speed_h(变速) → subs/subs_h(字幕最后烧) → qc(门禁)`

### 最小重跑路径表（省 token 的关键，改什么只重跑什么）

| 改了什么 | 只需重跑 |
|---|---|
| 字幕文本/字号/时间 | `--segments subs,subs_h,qc` |
| 某镜 H5（外部模型交付） | `--only-shots S## --steps render` + `--steps assemble --segments seq,enc,cat,...` |
| 水印/BGM/响度 | `--segments audio,mux,mux_h,speed,speed_h,subs,subs_h,qc` |
| 变速参数 | `--segments speed,speed_h,subs,subs_h,qc` |
| 时间轴/镜表 | 重走分镜→对齐→全量（频率最低成本最高，符合直觉） |

## 三、幂等契约（每段的重入安全标准）

- 产物存在 + **内容验证通过**才允许跳过（帧数 ffprobe 断言，防"残骸文件骗过 getsize"）；
- 覆盖式段（speed/subs）无条件重跑，由 qc 兜底；
- 每镜级 `.done` 标记（截帧）、manifest 帧表（seq/enc）——最小粒度断点；
- 状态文件仅作日志，**真实状态=文件系统**（永不失真）；
- 长任务在沙盒跑法：后台进程会被会话回收（实测 nohup/setsid 均存活不过调用边界），
  一律**前台 timeout 分段轮次推进**，每轮自动续跑。

## 四、废墟重启协议（任何时候回到原有进度）

1. **入仓规则决定可恢复性**（铁律 5/6/36 的另一面）：
   - 入仓（事实源）：分镜/字幕卡/切片+MANIFEST/canvas 页面/脚本/字体/logo/配音
   - 不入仓（派生物，崩溃后脚本重生成）：frames 帧库/build 中间件/成片（交付后归档除外）
2. 崩溃后：clone 工作仓（浅克隆）→ `pipeline.py --list` 一屏看全状态 →
   `--from <断点>` 或直接全量重跑（幂等=自动续跑）
3. 预期成本：check 秒级；render 按镜数十分钟级；assemble 按集几十分钟级——
   全部 CPU 时间，**零 token、零素材重下**。
4. 每完成一个可交付小步 commit+push（防回收窗口期损失）。

## 五、版本后缀约定（流程验证轮）

内容零变化、仅验证流程改造的重建版本，小版本加 **b** 后缀（如 v8→v8b、v1→v1b），
交付物同名映射；QC 全 PASS + 帧数与原版一致才可交付。让"流程实验"与"内容迭代"
在版本线上可区分。
