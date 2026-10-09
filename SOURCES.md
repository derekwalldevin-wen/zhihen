# 测试样片来源与许可

于 2026-10-09 核对 scikit-image 官方数据文档：
https://scikit-image.org/docs/stable/api/skimage.data.html

| 类别 | 本地文件 | 作者 / 原始来源 | 许可 | 原始像素 |
| --- | --- | --- | --- | --- |
| 人物 | samples/astronaut.png | NASA，Eileen Collins 肖像，NASA Great Images 数据库 https://flic.kr/p/r9qvLn | 官方数据文档记载无已知版权限制，公有领域 | 512 × 512 |
| 动物 | samples/chelsea.png | Stefan van der Walt，Chelsea the cat | CC0，由摄影者授权 | 451 × 300 |
| 物件 | samples/coffee.png | Rachel Michetti，Pikolo Espresso Bar 咖啡杯 | CC0，由摄影者授权 | 600 × 400 |

下载来源固定到 scikit-image v0.24.0：

- https://raw.githubusercontent.com/scikit-image/scikit-image/v0.24.0/skimage/data/astronaut.png
- https://raw.githubusercontent.com/scikit-image/scikit-image/v0.24.0/skimage/data/chelsea.png
- https://raw.githubusercontent.com/scikit-image/scikit-image/v0.24.0/skimage/data/coffee.png

三个 PNG 的原始字节内嵌在 HTML；运行 `tests/prepare_samples.py` 可恢复下表所列本地文件，仓库不重复存放样片。`coffee-upload.jpg` 由验收脚本将 coffee.png 以 JPEG quality=95 转换生成。内嵌样片为这些 PNG 的 Base64 数据；没有在线加载图片。

全部效果图是工具计算并经浏览器实际 PNG 下载所得，没有使用 AI 宣传概念图，没有人工补画输出。未使用用户个人照片；公开仓库仅包含上述许可明确的内嵌样片。工具运行时不会上传用户导入的照片。

CC0 说明：https://creativecommons.org/publicdomain/zero/1.0/

本文件说明素材来源，不表示 NASA 或摄影者为该工具背书。
