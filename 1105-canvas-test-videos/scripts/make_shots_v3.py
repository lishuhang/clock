#!/usr/bin/env python3
"""生成 ep1_shots_v3.json：实测时间码 + v3 设计修订（黑底/B站素材）。
并输出分镜表 v3 的第1集表格(md)。
"""
import json

WORK = "/home/z/my-project/ep1-work"
SHOTS_V2 = "/home/z/my-project/github-work/1105-canvas-test-videos/04-ep1-production/ep1_shots_v2.json"
REAL = f"{WORK}/ep1_sentences_real.json"
AUDIO_END = 740.36

# v3 设计修订（仅改动的镜头）：visual / material
V3 = {
    "S02": {
        "visual": "黑底。背景叠底：《牌子》原片街头一镜到底片段(paizi_bg.mp4 36-50s)压暗至18%铺满，"
                  "主体：B站视频页截图裁切逐级推入——播放量条「2152.1万」红框高亮放大停驻，"
                  "右侧竖排「点赞 142.8万」；底部新闻证据卡弹入：「《流浪地球》导演郭帆看到后转发点赞」(腾讯新闻·差评 2026-02-13)，"
                  "「23天」「100万奖金」金色大数字盖章",
        "material": "【外·B站】BV11mFLziEyP 原片片段36-50s(DiDi_OK,播放2152.1万/点赞142.8万,已下载)；"
                    "【外·截图】shots/paizi_playcount.png、paizi_up.png、news_guofan_para.png(郭帆转发点赞段落)；"
                    "pop×2；下载失败回退【canvas】ken_burns",
    },
    "S03": {
        "visual": "黑底。背景叠底：《丧尸清道夫》重制版末日小镇俯瞰片段(sss_bg.mp4 100-115s)压暗至18%铺满，"
                  "主体：B站视频页截图裁切推入——播放量条「424万」红框高亮(角标注明B站·重制版)，"
                  "「中专学历」「3000块成本」「全网播放破亿」三枚白字胶囊逐个盖章(破亿标注口径：全网)",
        "material": "【外·B站】BV1FFRQB2Eqw 重制版片段100-115s(Mx-Shell,B站播放424万,已下载)；"
                    "【外·截图】shots/sss_playcount.png、sss_title.png、sss_up.png；stamp音效",
    },
    "S14": {
        "visual": "黑底。'一元一秒，百元造梦'复古标语横幅居中展开(白字金边做旧)，"
                  "下方原文证据卡滑入并放大：「今年初2.0将视频制作带入『一元一秒，百元造梦』时代」——"
                  "娱乐资本论《画布横评·价格篇》原文段落截图，角注'——2026年初 行业口径'",
        "material": "【外·截图】shots/origin_yiyimiao.png(娱乐资本论原文,腾讯新闻2026-10-08)；"
                    "【canvas】big_number 复古横幅；口号出处留证=事实门禁④已闭环",
    },
    "S23": {
        "visual": "黑底。Higgsfield定价页真截图(暗色官网)滑入占4:3框上部，'45折'标签诱惑闪烁，"
                  "镜头下移红框锁定'Ultra $129/月'档位，右侧算式卡弹出'$129≈¥864/月'+'年付破万'红色警示，绿勾变红叉",
        "material": "【外·截图】shots/higgsfield_pricing.png(higgsfield.com/pricing 实截,含Ultra $129)；"
                    "【canvas】evidence；核查过程感：晚点式克制",
    },
}

# 其余镜头：material 加黑底前缀说明（不改 visual 细节，由暗色母版统一换肤）
DARK_NOTE = "【v3黑底】"


def main():
    shots = json.load(open(SHOTS_V2, encoding="utf-8"))
    real = json.load(open(REAL, encoding="utf-8"))
    n_sent = len(real)

    out = []
    for idx, s in enumerate(shots):
        a, b = s["sents"]
        st = real[a]["start"]
        # 镜头结束=下一镜头首句起点（停顿归属上一镜头）；末镜=音频终点
        if idx + 1 < len(shots):
            en = real[shots[idx + 1]["sents"][0]]["start"]
        else:
            en = AUDIO_END
        new = dict(s)
        new["start"], new["end"] = round(st, 2), round(en, 2)
        new["dur"] = round(en - st, 2)
        if s["id"] in V3:
            new["visual"] = V3[s["id"]]["visual"]
            new["material"] = V3[s["id"]]["material"]
        out.append(new)

    # 校验
    prev = 0.0
    for s in out:
        assert abs(s["start"] - prev) < 0.01, f"{s['id']} 时间不连续 {s['start']} vs {prev}"
        assert s["dur"] > 1.0, f"{s['id']} 时长过短 {s['dur']}"
        prev = s["end"]
    assert abs(prev - AUDIO_END) < 0.05, f"总长 {prev} != {AUDIO_END}"

    json.dump(out, open(f"{WORK}/ep1_shots_v3.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"ep1_shots_v3.json: {len(out)} 镜, 总长 {prev:.2f}s")
    for s in out[:6]:
        print(f"  {s['id']} {s['start']:8.2f}-{s['end']:8.2f} ({s['dur']:5.2f}s)")
    print("  ...")
    print(f"  {out[-1]['id']} {out[-1]['start']:8.2f}-{out[-1]['end']:8.2f}")

    # md 表格
    def mmss(t):
        m, sec = divmod(int(round(t)), 60)
        return f"{m:02d}:{sec:02d}"

    lines = []
    for s in out:
        vis = s["visual"].replace("\n", " ")
        mat = s["material"].replace("\n", " ")
        lines.append(f"| {s['id'][1:]} | {mmss(s['start'])}-{mmss(s['end'])} "
                     f"| {s['narration']} | {vis} | {mat} |")
    open(f"{WORK}/ep1_table_v3.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"ep1_table_v3.md 表格 {len(lines)} 行")


if __name__ == "__main__":
    main()
