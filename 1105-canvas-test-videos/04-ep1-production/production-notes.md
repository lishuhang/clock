# 第一篇「价格篇」投产记录（2026-11-05 成片）

## 成片
- `output/AI视频画布横评-第一篇-价格篇-成片.mp4`（1080×1920, 30fps, H.264+AAC, 12:20.36, 37MB）
- `output/qc_report.json`：G1零坏帧/G2时长/G3分辨率/G4响度-15LUFS/G5无长黑屏/G6无Remotion元数据 → BUILD_SUCCESS
- 字幕独立交付：`output/字幕.srt`（385条，B站投稿兼容）

## 管线（十步状态机 Step 5-9 实录）
1. canvas 43 镜（S01-S43.html，v2 规格母版）→ h5_render.py 受控截帧 2578 帧（JPEG q90，163MB，不入库可再生）
2. 总装 `scripts/ffmpeg_master_v2_seg.py`（分段模式，绕沙箱 600s 命令超时+后台进程被杀问题）：
   - 段A 0-370s / 段B 370-740.36s，段B 字幕+sendcmd 时间轴偏移 -370s
   - 视频链：concat帧轨 → 轨道PNG(1080×8) → sendcmd+drawbox 动画进度条(#e55b46, 0.5s步进) → ASS字幕(普惠体68px白字黑边Outline=7单行) → 全屏wm75.png水印(最顶层)
   - 音频链：配音(44.1k单声道)与BGM(48k立体声) aformat统一48k立体声 → sidechaincompress闪避 → loudnorm两遍 I=-15
   - concat拼段 → 混流 → faststart + metadata comment清空
3. 双重目检：VLM 6抽帧（字幕对位精确/水印/画面无缺陷）+ 像素级进度条测量（6帧全部0-1px误差，370s分段缝无缝）

## 踩坑（补入 skill 铁律候选）
- ffmpeg `crop`/`drawbox` 的 w/h 表达式只在初始化求值一次，不支持 t 逐帧动画 → 用 `sendcmd` 指令文件驱动 drawbox（`drawbox@命名实例` sendcmd 不识别，只能按滤镜类型名命中，图内须唯一同类型滤镜）
- sidechaincompress 要求主/侧链输入采样率+声道数一致 → 入口先 aformat=sample_rates=48000:channel_layouts=stereo
- 多输入 filter_complex 中 PNG 索引要按实际输入序号（配音/BGM 占位后轨道/水印后移），预览与全渲染输入布局不同需参数化
- 沙箱 Bash 600s 上限 + 后台进程会被静默回收（setsid 也一样被杀于~80s）→ 长编码必须分段前台跑，段间幂等续跑
- concat demuxer `-ss` 输入寻址与输出寻址帧差≈0（可用），段边界字幕事件跨缝双写（A段截尾/B段截头）实现无缝续显
