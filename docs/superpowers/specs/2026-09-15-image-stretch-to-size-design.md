# ComfyUI 拉伸到目标尺寸节点设计

## 目标

在 `byteartist-node` 中新增一个 ComfyUI 图片节点，将输入图片强制拉伸为用户指定的精确宽高。节点不保持原始宽高比，允许画面产生横向或纵向变形。

## 节点接口

- 显示名称：`拉伸到目标尺寸`
- 内部类名：`ImageStretchToSize`
- 分类：`image/transform`
- 输入 `image`：ComfyUI `IMAGE`，布局为 `B × H × W × C`
- 输入 `target_width`：整数，范围 `1–16384`，默认 `2048`，步长 `1`
- 输入 `target_height`：整数，范围 `1–16384`，默认 `1024`，步长 `1`
- 输入 `interpolation`：`bicubic`、`bilinear`、`nearest`、`area`，默认 `bicubic`
- 输出：一个 ComfyUI `IMAGE`

## 行为

- 输出宽高必须精确等于 `target_width × target_height`。
- 不锁定、不计算也不保持输入图片的宽高比。
- `bicubic` 为默认插值方式，适合普通图片和天空盒的接近尺寸缩放。
- `bilinear` 提供更快、更平滑的通用缩放。
- `nearest` 保留硬边和像素块，适合像素画及离散数据。
- `area` 主要用于缩小图片以减少锯齿。
- 保持输入图片的批次数、通道数、数据类型和运行设备不变。
- 输入宽高无效时给出明确错误，不静默修正。
- 当目标尺寸与输入尺寸一致时直接返回输入，避免无意义的插值。

## 实现方式

使用 PyTorch `torch.nn.functional.interpolate`。先把 ComfyUI 的 `B × H × W × C` 张量转换为 `B × C × H × W`，按选定模式插值到目标尺寸，再转换回原布局。`bilinear` 与 `bicubic` 使用 `align_corners=False`；`nearest` 与 `area` 不传该参数。

## 验证

- 默认参数为 `2048 × 1024` 且默认插值为 `bicubic`。
- 不同比例输入均会强制变为精确目标宽高。
- 四种插值模式均能执行并返回正确形状。
- 批次数、通道数、数据类型和设备保持不变。
- 同尺寸输入走无插值路径并返回原张量对象。
- 非法图片布局或非正目标尺寸给出明确错误。
- 节点映射和中文显示名能被 ComfyUI 加载与搜索。
