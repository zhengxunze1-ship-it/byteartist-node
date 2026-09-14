import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nodes import (  # noqa: E402
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    PanoramaTileOffset,
)


class FakeImage:
    def __init__(self, values):
        self.values = np.asarray(values)

    @property
    def shape(self):
        return self.values.shape

    def roll(self, shifts, dims):
        return FakeImage(np.roll(self.values, shift=shifts, axis=dims))


class PanoramaTileOffsetTests(unittest.TestCase):
    def setUp(self):
        self.node = PanoramaTileOffset()
        self.image = FakeImage(np.arange(4).reshape(1, 1, 4, 1))

    def test_fifty_percent_swaps_image_halves(self):
        result, = self.node.offset(self.image, 50.0)
        np.testing.assert_array_equal(
            result.values,
            np.array([[[[2], [3], [0], [1]]]]),
        )

    def test_positive_moves_right_and_negative_moves_left(self):
        right, = self.node.offset(self.image, 25.0)
        left, = self.node.offset(self.image, -25.0)
        np.testing.assert_array_equal(right.values, np.array([[[[3], [0], [1], [2]]]]))
        np.testing.assert_array_equal(left.values, np.array([[[[1], [2], [3], [0]]]]))

    def test_zero_and_full_width_offsets_preserve_pixels(self):
        for percent in (0.0, 100.0, -100.0):
            result, = self.node.offset(self.image, percent)
            np.testing.assert_array_equal(result.values, self.image.values)

    def test_batch_shape_is_preserved(self):
        batch = FakeImage(np.arange(2 * 3 * 8 * 4).reshape(2, 3, 8, 4))
        result, = self.node.offset(batch, 12.5)
        self.assertEqual(result.shape, batch.shape)

    def test_comfyui_metadata_and_chinese_display_name(self):
        spec = PanoramaTileOffset.INPUT_TYPES()["required"]["offset_percent"]
        self.assertEqual(spec[0], "FLOAT")
        self.assertEqual(spec[1], {"default": 50.0, "min": -100.0, "max": 100.0, "step": 0.1})
        self.assertEqual(PanoramaTileOffset.RETURN_TYPES, ("IMAGE",))
        self.assertEqual(PanoramaTileOffset.FUNCTION, "offset")
        self.assertEqual(PanoramaTileOffset.CATEGORY, "image/panorama")
        self.assertIs(NODE_CLASS_MAPPINGS["PanoramaTileOffset"], PanoramaTileOffset)
        self.assertEqual(NODE_DISPLAY_NAME_MAPPINGS["PanoramaTileOffset"], "平铺偏移")


if __name__ == "__main__":
    unittest.main()
