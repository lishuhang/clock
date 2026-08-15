# IPTV HLS 探测汇总

总线路数：**1692**。探测标准为可取得有效 HLS 清单并连续取得两个媒体资源；仅代表传输链路，不代表 DRM/私有加扰内容可被浏览器解码。

| 来源类别 | 线路数 | 传输可用 | 可用率 | 主要失败分类 |
|---|---:|---:|---:|---|
| 345-custom-legacy | 1692 | 33 | 2.0% | http_error=1250, request_exception=314, not_hls=57, transport_ok=33 |

## 全部分类

| 分类 | 数量 |
|---|---:|
| http_error | 1250 |
| not_hls | 57 |
| partial_segment_failure | 20 |
| request_exception | 314 |
| segment_failure | 16 |
| transport_ok | 33 |
| variant_http_error | 2 |

## 最慢的清单请求（前 20）

| 频道 | 来源类别 | 延迟（ms） | 探测分类 | URL |
|---|---|---:|---|---|
| movie423 | 345-custom-legacy | 14535.2 | http_error | `https://345.lishuhang.com/movie423.m3u8` |
| hlitv68 | 345-custom-legacy | 13430.1 | http_error | `https://345.lishuhang.com/itv74.m3u8` |
| fjitv258 | 345-custom-legacy | 13049.8 | http_error | `https://345.lishuhang.com/fjitv258.m3u8` |
| fjitv2 | 345-custom-legacy | 12975.2 | transport_ok | `https://345.lishuhang.com/ys2.m3u8` |
| itv201 | 345-custom-legacy | 12853.6 | http_error | `https://345.lishuhang.com/itv201.m3u8` |
| fjitv266 | 345-custom-legacy | 12846.6 | http_error | `https://345.lishuhang.com/fjitv266.m3u8` |
| movie138 | 345-custom-legacy | 12495.2 | http_error | `https://345.lishuhang.com/movie138.m3u8` |
| fjitv7 | 345-custom-legacy | 11699.8 | not_hls | `https://345.lishuhang.com/itv14.m3u8` |
| fjitv11 | 345-custom-legacy | 11507.3 | transport_ok | `https://345.lishuhang.com/ys13.m3u8` |
| fjitv3 | 345-custom-legacy | 11244.3 | transport_ok | `https://345.lishuhang.com/ys3.m3u8` |
| itv180 | 345-custom-legacy | 11126.6 | http_error | `https://345.lishuhang.com/itv180.m3u8` |
| itv211 | 345-custom-legacy | 11062.3 | http_error | `https://345.lishuhang.com/itv211.m3u8` |
| movie114 | 345-custom-legacy | 10808.0 | http_error | `https://345.lishuhang.com/movie114.m3u8` |
| movie94 | 345-custom-legacy | 10707.9 | http_error | `https://345.lishuhang.com/movie94.m3u8` |
| itv181 | 345-custom-legacy | 10465.4 | http_error | `https://345.lishuhang.com/itv181.m3u8` |
| fjitv155 | 345-custom-legacy | 10422.6 | not_hls | `https://345.lishuhang.com/itv46.m3u8` |
| movie1 | 345-custom-legacy | 10414.6 | http_error | `https://345.lishuhang.com/movie1.m3u8` |
| fjitv280 | 345-custom-legacy | 10412.1 | http_error | `https://345.lishuhang.com/fjitv280.m3u8` |
| ipv696 | 345-custom-legacy | 10289.7 | http_error | `https://345.lishuhang.com/itv66.m3u8` |
| ys35 | 345-custom-legacy | 10229.9 | not_hls | `https://345.lishuhang.com/ys35.m3u8` |
