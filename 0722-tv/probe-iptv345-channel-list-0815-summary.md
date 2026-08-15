# IPTV HLS 探测汇总

总线路数：**1778**。探测标准为可取得有效 HLS 清单并连续取得两个媒体资源；仅代表传输链路，不代表 DRM/私有加扰内容可被浏览器解码。

| 来源类别 | 线路数 | 传输可用 | 可用率 | 主要失败分类 |
|---|---:|---:|---:|---|
| 345-custom-legacy | 1692 | 0 | 0.0% | http_error=1692 |
| 345-custom-xuexi | 40 | 0 | 0.0% | http_error=40 |
| 345-custom-ysp | 46 | 32 | 69.6% | transport_ok=32, http_error=14 |

## 全部分类

| 分类 | 数量 |
|---|---:|
| http_error | 1746 |
| transport_ok | 32 |

## 最慢的清单请求（前 20）

| 频道 | 来源类别 | 延迟（ms） | 探测分类 | URL |
|---|---|---:|---|---|
| fjitv83 | 345-custom-legacy | 6564.3 | http_error | `https://345.lishuhang.com/ws33.m3u8` |
| 湖北卫视 | 345-custom-ysp | 6557.9 | transport_ok | `https://345.lishuhang.com/yspw06.m3u8` |
| 吉林卫视 | 345-custom-ysp | 6417.2 | transport_ok | `https://345.lishuhang.com/yspw23.m3u8` |
| 康巴卫视 | 345-custom-xuexi | 5987.3 | http_error | `https://345.lishuhang.com/xuexi_2e1b591d.m3u8` |
| 湖南卫视 | 345-custom-ysp | 5943.1 | transport_ok | `https://345.lishuhang.com/yspw05.m3u8` |
| 青海卫视 | 345-custom-xuexi | 5895.7 | http_error | `https://345.lishuhang.com/xuexi_49718a9c.m3u8` |
| 大湾区卫视 | 345-custom-xuexi | 5858.8 | http_error | `https://345.lishuhang.com/xuexi_b3b303ac.m3u8` |
| itv26 | 345-custom-legacy | 5772.6 | http_error | `https://345.lishuhang.com/itv26.m3u8` |
| 内蒙古蒙语卫视 | 345-custom-xuexi | 5750.4 | http_error | `https://345.lishuhang.com/xuexi_3072aafb.m3u8` |
| 广西卫视 | 345-custom-xuexi | 5608.5 | http_error | `https://345.lishuhang.com/xuexi_d45e1b2d.m3u8` |
| itv26 | 345-custom-legacy | 5504.7 | http_error | `https://345.lishuhang.com/ys20.m3u8` |
| 宁夏卫视 | 345-custom-xuexi | 5238.1 | http_error | `https://345.lishuhang.com/xuexi_782bc32a.m3u8` |
| 贵州卫视 | 345-custom-ysp | 5078.7 | transport_ok | `https://345.lishuhang.com/yspw16.m3u8` |
| 北京卫视 | 345-custom-ysp | 4965.1 | transport_ok | `https://345.lishuhang.com/yspw01.m3u8` |
| 黑龙江卫视 | 345-custom-ysp | 4860.5 | transport_ok | `https://345.lishuhang.com/yspw09.m3u8` |
| fjitv33 | 345-custom-legacy | 4792.4 | http_error | `https://345.lishuhang.com/ws6.m3u8` |
| fjitv6 | 345-custom-legacy | 4685.7 | http_error | `https://345.lishuhang.com/ys7.m3u8` |
| 河北卫视 | 345-custom-xuexi | 4649.2 | http_error | `https://345.lishuhang.com/xuexi_39f6908c.m3u8` |
| itv25 | 345-custom-legacy | 4619.9 | http_error | `https://345.lishuhang.com/itv25.m3u8` |
| 新疆卫视 | 345-custom-ysp | 4615.7 | transport_ok | `https://345.lishuhang.com/yspw31.m3u8` |
