# IPTV HLS 探测汇总

总线路数：**257**。探测标准为可取得有效 HLS 清单并连续取得两个媒体资源；仅代表传输链路，不代表 DRM/私有加扰内容可被浏览器解码。

| 来源类别 | 线路数 | 传输可用 | 可用率 | 主要失败分类 |
|---|---:|---:|---:|---|
| 345-custom-wso | 3 | 2 | 66.7% | transport_ok=2, http_error=1 |
| 345-custom-xuexi | 40 | 0 | 0.0% | http_error=40 |
| 345-custom-ysp | 46 | 32 | 69.6% | transport_ok=32, http_error=14 |
| 345-workers-dev-legacy | 47 | 0 | 0.0% | http_error=47 |
| direct-non345 | 121 | 65 | 53.7% | transport_ok=62, request_exception=22, partial_segment_failure=16, http_error=15 |

## 全部分类

| 分类 | 数量 |
|---|---:|
| http_error | 117 |
| not_hls | 2 |
| partial_segment_failure | 16 |
| request_exception | 22 |
| segment_failure | 1 |
| transport_ok | 96 |
| transport_ok_encrypted_hint | 3 |

## 最慢的清单请求（前 20）

| 频道 | 来源类别 | 延迟（ms） | 探测分类 | URL |
|---|---|---:|---|---|
| CGTN | direct-non345 | 14972.3 | transport_ok | `https://play.kankanlive.com/live/1698423645566913.m3u8` |
| 内蒙古蒙语卫视 | 345-custom-xuexi | 10812.1 | http_error | `https://345.lishuhang.com/xuexi_3072aafb.m3u8` |
| GB News | direct-non345 | 8619.7 | transport_ok | `https://amg01076-lightningintern-gbnews-samsunguk-0lu52.amagi.tv/playlist/amg01076-lightningintern-gbnews-samsunguk/playlist.m3u8` |
| CCTV5+ | direct-non345 | 8581.4 | transport_ok | `http://222.169.85.8:9901/tsfile/live/0116_1.m3u8` |
| CCTV9 | direct-non345 | 7639.4 | transport_ok | `https://play.kankanlive.com/live/1698423397390920.m3u8` |
| 东方卫视 | 345-custom-xuexi | 7616.8 | http_error | `https://345.lishuhang.com/xuexi_b03d633a.m3u8` |
| GB News | direct-non345 | 7341.8 | transport_ok | `https://cdn-apse1-prod.tsv2.amagi.tv/linear/amg01076-lightningintern-gbnewsnz-samsungnz/playlist.m3u8` |
| CCTV Plus 2 | direct-non345 | 7072.8 | transport_ok | `https://cd-live-stream.news.cctvplus.com/live/smil:CHANNEL2.smil/playlist.m3u8` |
| 海南卫视 | 345-custom-wso | 6562.7 | transport_ok | `https://345.lishuhang.com/wso-hainan.m3u8` |
| CGTN | direct-non345 | 6485.2 | transport_ok | `https://0472.org/hls/cgtn.m3u8` |
| 延边卫视 | direct-non345 | 6472.7 | transport_ok | `https://srs.iyb983.cn/video/CYS/index.m3u8` |
| 北京卫视 | 345-custom-xuexi | 6425.2 | http_error | `https://345.lishuhang.com/xuexi_b2e730bc.m3u8` |
| 海南卫视 | direct-non345 | 6314.4 | transport_ok | `http://cssbyd.imwork.net:8082/hls/31/index.m3u8` |
| TVB翡翠台 | direct-non345 | 6073.0 | not_hls | `https://o11.163189.xyz/stream/tvb/fct/` |
| NBD AI | direct-non345 | 6057.2 | transport_ok | `https://swiftplay.hxkjmedia.com/tv/spbW.m3u8` |
| CGTN Doc | direct-non345 | 6012.1 | transport_ok | `https://0472.org/hls/cgtnd.m3u8` |
| 陕西卫视 | 345-custom-wso | 5881.3 | transport_ok | `https://345.lishuhang.com/wso-shaanxi.m3u8` |
| 大湾区卫视 | 345-custom-xuexi | 5829.8 | http_error | `https://345.lishuhang.com/xuexi_b3b303ac.m3u8` |
| TVB明珠台 | direct-non345 | 5811.3 | not_hls | `https://o11.163189.xyz/stream/tvb/mzt/` |
| 甘肃卫视 | direct-non345 | 5811.1 | transport_ok | `http://live.zohi.tv/video/s10001-fztv-3/index.m3u8` |
