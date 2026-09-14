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

重启 ComfyUI，在节点搜索框输入 `平铺偏移`。

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

## 测试

```bash
python3 -m unittest discover -s tests -v
```
