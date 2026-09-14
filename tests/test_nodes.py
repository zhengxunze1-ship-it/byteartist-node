import sys
import unittest
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nodes import (  # noqa: E402
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
    MaskImageComposite,
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


class MaskImageCompositeTests(unittest.TestCase):
    def setUp(self):
        self.node = MaskImageComposite()

    def test_black_mask_returns_image_a(self):
        image_a = torch.tensor([[[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]]])
        image_b = torch.ones_like(image_a)
        mask = torch.zeros((1, 1, 2))

        output, = self.node.composite(image_a, image_b, mask)

        self.assertTrue(torch.equal(output, image_a))

    def test_white_mask_returns_image_b(self):
        image_a = torch.zeros((1, 1, 2, 3))
        image_b = torch.tensor([[[[0.2, 0.4, 0.6], [0.8, 0.5, 0.1]]]])
        mask = torch.ones((1, 1, 2))

        output, = self.node.composite(image_a, image_b, mask)

        self.assertTrue(torch.equal(output, image_b))

    def test_gray_mask_blends_linearly(self):
        image_a = torch.zeros((1, 1, 1, 3))
        image_b = torch.ones((1, 1, 1, 3))
        mask = torch.full((1, 1, 1), 0.25)

        output, = self.node.composite(image_a, image_b, mask)

        self.assertTrue(torch.equal(output, torch.full_like(image_a, 0.25)))

    def test_resizes_image_b_and_mask_to_image_a(self):
        image_a = torch.zeros((1, 4, 6, 3))
        image_b = torch.ones((1, 2, 3, 3))
        mask = torch.ones((1, 1, 2))

        output, = self.node.composite(image_a, image_b, mask)

        self.assertEqual(tuple(output.shape), (1, 4, 6, 3))
        self.assertTrue(torch.equal(output, torch.ones_like(image_a)))

    def test_broadcasts_singleton_batches(self):
        image_a = torch.zeros((2, 2, 2, 3))
        image_b = torch.stack(
            [torch.full((2, 2, 3), 0.25), torch.full((2, 2, 3), 0.75)]
        )
        mask = torch.ones((1, 2, 2))

        output, = self.node.composite(image_a, image_b, mask)

        self.assertTrue(torch.equal(output, image_b))

    def test_rejects_incompatible_batches(self):
        image_a = torch.zeros((2, 2, 2, 3))
        image_b = torch.zeros((3, 2, 2, 3))
        mask = torch.zeros((1, 2, 2))

        with self.assertRaisesRegex(ValueError, "batch"):
            self.node.composite(image_a, image_b, mask)

    def test_rejects_channel_mismatch(self):
        image_a = torch.zeros((1, 2, 2, 3))
        image_b = torch.zeros((1, 2, 2, 4))
        mask = torch.zeros((1, 2, 2))

        with self.assertRaisesRegex(ValueError, "channel"):
            self.node.composite(image_a, image_b, mask)

    def test_comfyui_metadata_and_chinese_display_name(self):
        self.assertEqual(MaskImageComposite.RETURN_TYPES, ("IMAGE",))
        self.assertEqual(MaskImageComposite.FUNCTION, "composite")
        self.assertEqual(MaskImageComposite.CATEGORY, "image/composite")
        self.assertIs(NODE_CLASS_MAPPINGS["MaskImageComposite"], MaskImageComposite)
        self.assertEqual(NODE_DISPLAY_NAME_MAPPINGS["MaskImageComposite"], "遮罩叠加")


if __name__ == "__main__":
    unittest.main()
