# Image Stretch To Size Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a ComfyUI node named `拉伸到目标尺寸` that forcibly resizes BHWC image tensors to an exact width and height with selectable interpolation.

**Architecture:** Keep the node in the repository's existing single-module layout. `ImageStretchToSize.stretch()` validates its input, returns the original tensor for a no-op resize, otherwise converts BHWC to BCHW, delegates resizing to `torch.nn.functional.interpolate`, and converts back to BHWC.

**Tech Stack:** Python 3, PyTorch (`torch.nn.functional.interpolate`), ComfyUI custom-node metadata, `unittest`

## Global Constraints

- Display name: `拉伸到目标尺寸`.
- Internal class and mapping key: `ImageStretchToSize`.
- Category: `image/transform`.
- Inputs: `image`, `target_width`, `target_height`, `interpolation`.
- `target_width`: `INT`, default `2048`, minimum `1`, maximum `16384`, step `1`.
- `target_height`: `INT`, default `1024`, minimum `1`, maximum `16384`, step `1`.
- `interpolation` choices, in order: `bicubic`, `bilinear`, `nearest`, `area`; default `bicubic`.
- Resize to the exact requested dimensions without preserving aspect ratio.
- Preserve batch size, channel count, dtype, and device.
- When the input already has the requested dimensions, return the original tensor object without interpolation.
- Reject non-BHWC tensors, zero-sized source dimensions, target dimensions below `1`, and unsupported interpolation strings with `ValueError`.
- Use `align_corners=False` only for `bicubic` and `bilinear`.
- Do not add runtime dependencies.

---

### Task 1: Image Stretch Node and Tests

**Files:**
- Modify: `tests/test_nodes.py`
- Modify: `nodes.py`

**Interfaces:**
- Consumes: `_validate_image(image: object, name: str) -> None` from `nodes.py` and `torch.nn.functional.interpolate(input, size, mode, align_corners=None) -> torch.Tensor`.
- Produces: `ImageStretchToSize.INPUT_TYPES() -> dict`, `ImageStretchToSize.stretch(image: torch.Tensor, target_width: int, target_height: int, interpolation: str) -> tuple[torch.Tensor]`, `NODE_CLASS_MAPPINGS["ImageStretchToSize"]`, and `NODE_DISPLAY_NAME_MAPPINGS["ImageStretchToSize"]`.

- [ ] **Step 1: Write the failing tests**

Add `ImageStretchToSize` to the import from `nodes`, then append this test class to `tests/test_nodes.py`:

```python
class ImageStretchToSizeTests(unittest.TestCase):
    def setUp(self):
        self.node = ImageStretchToSize()

    def test_comfyui_metadata_defaults_and_registration(self):
        required = ImageStretchToSize.INPUT_TYPES()["required"]
        self.assertEqual(required["image"], ("IMAGE",))
        self.assertEqual(
            required["target_width"],
            ("INT", {"default": 2048, "min": 1, "max": 16384, "step": 1}),
        )
        self.assertEqual(
            required["target_height"],
            ("INT", {"default": 1024, "min": 1, "max": 16384, "step": 1}),
        )
        self.assertEqual(
            required["interpolation"],
            (["bicubic", "bilinear", "nearest", "area"], {"default": "bicubic"}),
        )
        self.assertEqual(ImageStretchToSize.RETURN_TYPES, ("IMAGE",))
        self.assertEqual(ImageStretchToSize.RETURN_NAMES, ("image",))
        self.assertEqual(ImageStretchToSize.FUNCTION, "stretch")
        self.assertEqual(ImageStretchToSize.CATEGORY, "image/transform")
        self.assertIs(NODE_CLASS_MAPPINGS["ImageStretchToSize"], ImageStretchToSize)
        self.assertEqual(
            NODE_DISPLAY_NAME_MAPPINGS["ImageStretchToSize"], "拉伸到目标尺寸"
        )

    def test_stretches_to_exact_requested_dimensions(self):
        image = torch.arange(1 * 2 * 3 * 1, dtype=torch.float32).reshape(1, 2, 3, 1)

        output, = self.node.stretch(image, 5, 4, "bicubic")

        self.assertEqual(tuple(output.shape), (1, 4, 5, 1))

    def test_supports_every_interpolation_mode(self):
        image = torch.rand((1, 3, 5, 3), dtype=torch.float32)

        for mode in ("bicubic", "bilinear", "nearest", "area"):
            with self.subTest(mode=mode):
                output, = self.node.stretch(image, 8, 6, mode)
                self.assertEqual(tuple(output.shape), (1, 6, 8, 3))

    def test_preserves_batch_channels_dtype_and_device(self):
        image = torch.rand((2, 3, 4, 4), dtype=torch.float64)

        output, = self.node.stretch(image, 7, 5, "bilinear")

        self.assertEqual(tuple(output.shape), (2, 5, 7, 4))
        self.assertEqual(output.dtype, image.dtype)
        self.assertEqual(output.device, image.device)

    def test_same_size_returns_original_tensor_object(self):
        image = torch.rand((1, 3, 4, 3), dtype=torch.float32)

        output, = self.node.stretch(image, 4, 3, "bicubic")

        self.assertIs(output, image)

    def test_rejects_invalid_target_dimensions(self):
        image = torch.rand((1, 2, 2, 3), dtype=torch.float32)

        with self.assertRaisesRegex(ValueError, "target_width"):
            self.node.stretch(image, 0, 2, "bicubic")
        with self.assertRaisesRegex(ValueError, "target_height"):
            self.node.stretch(image, 2, 0, "bicubic")

    def test_rejects_invalid_image_and_interpolation(self):
        with self.assertRaisesRegex(ValueError, "BHWC"):
            self.node.stretch(torch.zeros((2, 2, 3)), 4, 4, "bicubic")

        image = torch.rand((1, 2, 2, 3), dtype=torch.float32)
        with self.assertRaisesRegex(ValueError, "interpolation"):
            self.node.stretch(image, 4, 4, "lanczos")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: FAIL while importing `ImageStretchToSize` because it has not been defined in `nodes.py`.

- [ ] **Step 3: Implement the node and register it**

Add this class to `nodes.py` after `_resize_mask` and before `MaskImageComposite`:

```python
class ImageStretchToSize:
    """Force a ComfyUI image to an exact width and height."""

    INTERPOLATION_MODES = ("bicubic", "bilinear", "nearest", "area")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "target_width": (
                    "INT",
                    {"default": 2048, "min": 1, "max": 16384, "step": 1},
                ),
                "target_height": (
                    "INT",
                    {"default": 1024, "min": 1, "max": 16384, "step": 1},
                ),
                "interpolation": (
                    list(cls.INTERPOLATION_MODES),
                    {"default": "bicubic"},
                ),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "stretch"
    CATEGORY = "image/transform"

    def stretch(self, image, target_width, target_height, interpolation):
        _validate_image(image, "image")
        if target_width < 1:
            raise ValueError("target_width must be at least 1")
        if target_height < 1:
            raise ValueError("target_height must be at least 1")
        if interpolation not in self.INTERPOLATION_MODES:
            raise ValueError(
                "interpolation must be one of: "
                + ", ".join(self.INTERPOLATION_MODES)
            )

        if image.shape[1:3] == (target_height, target_width):
            return (image,)

        image_bchw = image.permute(0, 3, 1, 2)
        resize_options = {
            "size": (target_height, target_width),
            "mode": interpolation,
        }
        if interpolation in ("bicubic", "bilinear"):
            resize_options["align_corners"] = False

        resized = F.interpolate(image_bchw, **resize_options)
        return (resized.permute(0, 2, 3, 1),)
```

Extend the mappings at the bottom of `nodes.py`:

```python
NODE_CLASS_MAPPINGS = {
    "PanoramaTileOffset": PanoramaTileOffset,
    "MaskImageComposite": MaskImageComposite,
    "ImageStretchToSize": ImageStretchToSize,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PanoramaTileOffset": "平铺偏移",
    "MaskImageComposite": "遮罩叠加",
    "ImageStretchToSize": "拉伸到目标尺寸",
}
```

- [ ] **Step 4: Run the complete test suite to verify it passes**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all existing and new tests PASS, including four interpolation subtests.

- [ ] **Step 5: Commit the tested node**

```bash
git add nodes.py tests/test_nodes.py
git commit -m "feat: add image stretch node"
```

### Task 2: User Documentation and Release Verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: registered display name `拉伸到目标尺寸` and inputs from `ImageStretchToSize.INPUT_TYPES()`.
- Produces: installation/search instructions and a concise usage reference for the new node.

- [ ] **Step 1: Document the node and update search instructions**

Change the search sentence to:

```markdown
重启 ComfyUI，在节点搜索框输入 `平铺偏移`、`遮罩叠加` 或 `拉伸到目标尺寸`。
```

Insert this section before `## 测试`:

```markdown
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
```

- [ ] **Step 2: Run regression tests and repository checks**

Run:

```bash
python3 -m unittest discover -s tests -v
git diff --check
git status --short --branch
```

Expected: all tests PASS; `git diff --check` prints nothing; status shows only the intended `README.md` modification after Task 1's commit.

- [ ] **Step 3: Commit the documentation**

```bash
git add README.md docs/superpowers/plans/2026-09-15-image-stretch-to-size.md
git commit -m "docs: document image stretch node"
```

- [ ] **Step 4: Upload and verify the repository state**

Run:

```bash
git push origin main
git status --short --branch
git log -3 --oneline --decorate
```

Expected: push succeeds; status reports `main...origin/main` with no ahead/behind marker and no working-tree changes; the three newest commits include the design, implementation, and documentation commits.
