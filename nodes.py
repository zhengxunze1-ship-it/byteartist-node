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


NODE_CLASS_MAPPINGS = {
    "PanoramaTileOffset": PanoramaTileOffset,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PanoramaTileOffset": "平铺偏移",
}
