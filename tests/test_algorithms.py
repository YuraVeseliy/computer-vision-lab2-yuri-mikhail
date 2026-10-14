"""Проверки на примерах с заранее известными ответами."""

import unittest
import uuid
from pathlib import Path

from PIL import Image

import image_ops
from image_io import load_rgb, save_rgb
from statistics_ops import (
    component_image, demo_image, histograms, intensity, row_profile,
    statistics, window_values,
)


def gray_image(values: list[list[int]]) -> list[list[tuple[int, int, int]]]:
    return [[(value, value, value) for value in row] for row in values]


class StatisticsTests(unittest.TestCase):
    def test_two_variance_formulas(self) -> None:
        for method in ('two_pass', 'one_pass'):
            self.assertEqual(statistics([2, 4, 4, 4, 5, 5, 7, 9], method),
                             (5.0, 4.0, 2.0))
            self.assertEqual(statistics([128] * 121, method), (128, 0, 0))
            self.assertEqual(statistics([100], method), (100, 0, 0))

    def test_rgb_intensity_and_histograms(self) -> None:
        image = [[(255, 0, 0), (0, 255, 0), (0, 0, 255), (1, 0, 0)]]
        self.assertEqual(intensity(image[0][0]), 85)
        self.assertAlmostEqual(intensity(image[0][3]), 1 / 3)
        distributions = histograms(image)
        self.assertEqual([sum(counts) for counts in distributions], [4] * 4)
        self.assertEqual(distributions[0][85], 3)
        self.assertEqual(distributions[0][0], 1)
        self.assertEqual(component_image(image, 0)[0][0], (255, 255, 255))
        self.assertEqual(row_profile(image, 0), [85, 85, 85, 1 / 3])

    def test_window_sizes_and_invalid_input(self) -> None:
        image = gray_image([[128] * 20 for _ in range(20)])
        self.assertEqual(len(window_values(image, 10, 10)), 121)
        self.assertEqual(len(window_values(image, 0, 0)), 36)
        self.assertEqual(len(window_values(image, 19, 0)), 36)
        with self.assertRaises(ValueError):
            window_values(image, 1, 1, 4)
        with self.assertRaises(ValueError):
            row_profile(image, -1)
        with self.assertRaises(ValueError):
            statistics([])

    def test_homogeneous_and_heterogeneous_same_mean(self) -> None:
        image = demo_image()
        mean, variance, _ = statistics(window_values(image, 64, 48))
        self.assertEqual((mean, variance), (128, 0))
        mean, variance, _ = statistics(window_values(image, 192, 48))
        self.assertEqual(mean, 128)
        self.assertAlmostEqual(variance, 100000 / 11)


class TransformTests(unittest.TestCase):
    def test_brightness_clipping_and_channel_target(self) -> None:
        image = [[(250, 10, 0)]]
        result = image_ops.point_transform(image, 'brightness', 20, 0)
        self.assertEqual(result, [[(255, 10, 0)]])
        result = image_ops.point_transform(image, 'brightness', -20)
        self.assertEqual(result, [[(230, 0, 0)]])
        self.assertEqual(image, [[(250, 10, 0)]])

    def test_contrast_known_values(self) -> None:
        image = gray_image([[100, 150]])
        result = image_ops.point_transform(image, 'contrast', 2)
        self.assertEqual(result, gray_image([[75, 175]]))
        self.assertEqual(image_ops.point_transform(image, 'contrast', 0),
                         gray_image([[125, 125]]))
        self.assertEqual(
            image_ops.point_transform(image, 'contrast', 1), image,
        )

    def test_negative_swap_gamma_and_mirrors(self) -> None:
        image = [[(10, 20, 30), (40, 50, 60)],
                 [(70, 80, 90), (100, 110, 120)]]
        negative = image_ops.point_transform(image, 'negative')
        self.assertEqual(negative[0][0], (245, 235, 225))
        self.assertEqual(
            image_ops.point_transform(negative, 'negative'), image,
        )
        self.assertEqual(image_ops.swap_channels(image, 0, 2)[0][0],
                         (30, 20, 10))
        self.assertEqual(image_ops.point_transform(image, 'gamma', 1), image)
        self.assertEqual(
            image_ops.mirror(image, True)[0], list(reversed(image[0])),
        )
        self.assertEqual(image_ops.mirror(image, False), list(reversed(image)))
        self.assertEqual(
            image_ops.mirror(image_ops.mirror(image, True), True), image,
        )
        with self.assertRaises(ValueError):
            image_ops.point_transform(image, 'gamma', 0)

    def test_blur_includes_center_and_uses_old_values(self) -> None:
        image = gray_image([[0, 0, 0], [0, 90, 0], [0, 0, 0]])
        four = image_ops.blur(image, 4)
        eight = image_ops.blur(image, 8)
        self.assertEqual(four[1][1], (18, 18, 18))
        self.assertEqual(eight[1][1], (10, 10, 10))
        self.assertEqual(eight[0][0], (23, 23, 23))
        self.assertEqual(four[0][0], (0, 0, 0))
        self.assertEqual(image[1][1], (90, 90, 90))
        for connectivity in (4, 8):
            self.assertEqual(image_ops.blur([[(128, 128, 128)]], connectivity),
                             [[(128, 128, 128)]])

    def test_contrast_from_lecture_excludes_center(self) -> None:
        image = gray_image([[0, 0, 0], [0, 100, 0], [0, 0, 0]])
        four, total = image_ops.contrast_map(image, '4')
        self.assertEqual(four[1][1], 100)
        self.assertAlmostEqual(four[0][1], 100 / 3)
        self.assertEqual(four[0][0], 0)
        self.assertAlmostEqual(total, 700 / 27)
        eight, total = image_ops.contrast_map(image, '8')
        self.assertEqual(eight[1][1], 100)
        self.assertAlmostEqual(eight[0][1], 20)
        self.assertAlmostEqual(total, 940 / 27)
        self.assertEqual(image_ops.contrast_map(image, 'window', 3)[0], eight)

    def test_integral_window_matches_direct_sum(self) -> None:
        image = [[((x * 37) % 256, (y * 43) % 256, (x + y) % 256)
                  for x in range(7)] for y in range(5)]
        for size in (3, 5, 11):
            result, _ = image_ops.contrast_map(image, 'window', size)
            radius = size // 2
            for y in range(5):
                for x in range(7):
                    neighbors = []
                    top, bottom = max(0, y - radius), min(5, y + radius + 1)
                    left, right = max(0, x - radius), min(7, x + radius + 1)
                    for ny in range(top, bottom):
                        for nx in range(left, right):
                            if (nx, ny) != (x, y):
                                neighbors.append(intensity(image[ny][nx]))
                    expected = abs(intensity(image[y][x])
                                   - sum(neighbors) / len(neighbors))
                    self.assertAlmostEqual(result[y][x], expected)
        for neighborhood in ('4', '8', 'window'):
            self.assertEqual(
                image_ops.contrast_map([[(128, 128, 128)]], neighborhood),
                ([[0]], 0),
            )

    def test_contrast_is_difference_from_mean(self) -> None:
        image = gray_image([[0, 100, 0], [0, 100, 200], [0, 100, 0]])
        four, _ = image_ops.contrast_map(image, '4')
        eight, _ = image_ops.contrast_map(image, '8')
        self.assertEqual(four[1][1], 0)
        self.assertEqual(eight[1][1], 50)


class FileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = (Path(__file__).resolve().parent
                       / ('.test-files-' + uuid.uuid4().hex))
        self.folder.mkdir()

    def tearDown(self) -> None:
        for path in self.folder.iterdir():
            path.unlink()
        self.folder.rmdir()

    def test_lossless_round_trip(self) -> None:
        image = [[(1, 2, 3), (253, 254, 255)], [(10, 20, 30), (0, 0, 0)]]
        for suffix in ('.png', '.bmp', '.tif'):
            path = str(self.folder / ('sample' + suffix))
            save_rgb(image, path)
            self.assertEqual(load_rgb(path), image)

    def test_reject_lossy_and_non_rgb_input(self) -> None:
        for mode, suffix in (('RGB', '.jpg'), ('RGBA', '.png'), ('L', '.png')):
            path = str(self.folder / ('sample' + suffix))
            Image.new(mode, (2, 2)).save(path)
            with self.assertRaises(ValueError):
                load_rgb(path)


if __name__ == '__main__':
    unittest.main()
