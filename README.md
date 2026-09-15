# ByteArtist ComfyUI Nodes

面向全景图和游戏美术流程的轻量 ComfyUI 自定义节点。

## 平铺偏移

`平铺偏移` 按图片宽度的百分比执行水平循环偏移。移出一侧的像素会从另一侧重新进入，因此不会产生空白、拉伸或插值模糊。

- 输入：`IMAGE`
- 参数：`offset_percent`，范围 `-100%` 至 `100%`，默认 `50%`
- 输出：同尺寸 `IMAGE`
- 正值向右移动，负值向左移动
- 适合把经纬度全景图的左右接缝移动到画面中央进行 Mask 和重绘

## 安装

在 ComfyUI 的 `custom_nodes` 目录中运行：

```bash
git clone https://github.com/zhengxunze1-ship-it/byteartist-node.git
```

重启 ComfyUI，在节点搜索框输入 `平铺偏移`、`遮罩叠加` 或 `拉伸到目标尺寸`。

连接方式：

```text
IMAGE → 平铺偏移 → IMAGE
```

典型天空盒接缝工作流：

```text
2:1 经纬度图
  → 平铺偏移 50%
  → 中央区域 Mask / 重绘 / 羽化回贴
  → 平铺偏移 -50%
  → 输出 2:1 经纬度图
```

## 遮罩叠加

`遮罩叠加` 根据一张遮罩平滑混合两张图片：

- 输入：`image_a`、`image_b` 和 `mask`
- 黑色遮罩区域显示图片 A
- 白色遮罩区域显示图片 B
- 灰色区域按遮罩值平滑混合
- 图片 B 和遮罩会自动缩放到图片 A 的分辨率
- 单张输入可以自动广播到批量输入

连接方式：

```text
图片 A ─┐
图片 B ─┼─> 遮罩叠加 ─> IMAGE
遮罩  ──┘
```

图片 A 与图片 B 需要具有相同的通道数。常规 ComfyUI RGB 图片可以直接连接。

## 拉伸到目标尺寸

`拉伸到目标尺寸` 会忽略原图宽高比，把图片强制拉伸到指定分辨率：

- 输入：`image`
- 目标宽度：`target_width`，默认 `2048`，范围 `1` 至 `16384`
- 目标高度：`target_height`，默认 `1024`，范围 `1` 至 `16384`
- 插值：`interpolation`，可选 `bicubic`（默认）、`bilinear`、`nearest`、`area`
- 输出：批量数、通道数、数据类型和设备保持不变的 `IMAGE`

连接方式：

```text
IMAGE → 拉伸到目标尺寸 → 2048 × 1024 IMAGE
```

这个节点不会裁剪或补边；当目标宽高比不同于原图时，画面会按要求产生拉伸变形。

## 测试

```bash
python3 -m unittest discover -s tests -v
```
