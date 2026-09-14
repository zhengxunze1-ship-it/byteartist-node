import torch
import torch.nn.functional as F


class PanoramaTileOffset:
    """Horizontally roll ComfyUI images by a percentage of their width."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "offset_percent": (
                    "FLOAT",
                    {
                        "default": 50.0,
                        "min": -100.0,
                        "max": 100.0,
                        "step": 0.1,
                    },
                ),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "offset"
    CATEGORY = "image/panorama"

    def offset(self, image, offset_percent):
        width = image.shape[2]
        pixels = round(width * offset_percent / 100.0)
        return (image.roll(shifts=pixels, dims=2),)


def _validate_image(image, name):
    if not isinstance(image, torch.Tensor) or image.ndim != 4:
        raise ValueError(f"{name} must be a BHWC image tensor")
    if image.shape[1] < 1 or image.shape[2] < 1:
        raise ValueError(f"{name} height and width must be positive")


def _validate_mask(mask):
    if not isinstance(mask, torch.Tensor) or mask.ndim != 3:
        raise ValueError("mask must be a BHW tensor")
    if mask.shape[1] < 1 or mask.shape[2] < 1:
        raise ValueError("mask height and width must be positive")


def _broadcast_batch(tensor, target_batch, name):
    batch = tensor.shape[0]
    if batch == target_batch:
        return tensor
    if batch == 1:
        return tensor.expand(target_batch, *tensor.shape[1:])
    raise ValueError(
        f"{name} batch size {batch} is incompatible with target batch size {target_batch}"
    )


def _resize_image(image, height, width):
    if image.shape[1:3] == (height, width):
        return image
    image_bchw = image.permute(0, 3, 1, 2)
    resized = F.interpolate(
        image_bchw, size=(height, width), mode="bilinear", align_corners=False
    )
    return resized.permute(0, 2, 3, 1)


def _resize_mask(mask, height, width):
    if mask.shape[1:3] == (height, width):
        return mask
    resized = F.interpolate(
        mask.unsqueeze(1), size=(height, width), mode="bilinear", align_corners=False
    )
    return resized.squeeze(1)


class MaskImageComposite:
    """Blend two ComfyUI images using a mask, with image A as size reference."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_a": ("IMAGE",),
                "image_b": ("IMAGE",),
                "mask": ("MASK",),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "composite"
    CATEGORY = "image/composite"

    def composite(self, image_a, image_b, mask):
        _validate_image(image_a, "image_a")
        _validate_image(image_b, "image_b")
        _validate_mask(mask)

        if image_a.shape[-1] != image_b.shape[-1]:
            raise ValueError(
                "image_a and image_b channel counts must match "
                f"({image_a.shape[-1]} != {image_b.shape[-1]})"
            )

        target_batch = max(image_a.shape[0], image_b.shape[0], mask.shape[0])
        image_a = _broadcast_batch(image_a, target_batch, "image_a")
        image_b = _broadcast_batch(image_b, target_batch, "image_b")
        mask = _broadcast_batch(mask, target_batch, "mask")

        height, width = image_a.shape[1:3]
        image_b = image_b.to(device=image_a.device, dtype=image_a.dtype)
        mask = mask.to(device=image_a.device, dtype=image_a.dtype)
        image_b = _resize_image(image_b, height, width)
        mask = _resize_mask(mask, height, width).clamp(0.0, 1.0).unsqueeze(-1)

        return (image_a * (1.0 - mask) + image_b * mask,)


NODE_CLASS_MAPPINGS = {
    "PanoramaTileOffset": PanoramaTileOffset,
    "MaskImageComposite": MaskImageComposite,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PanoramaTileOffset": "平铺偏移",
    "MaskImageComposite": "遮罩叠加",
}
