"""Проверки масштаба, мыши и рамки в настоящем Tkinter."""

import tkinter as tk
import unittest

from application import Application


class FittedViewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.app = Application(self.root)
        self.app.load_demo()
        self.root.update()

    def event_at(self, x: int, y: int, map_view: bool = False) -> tk.Event:
        panel = self.app.map_viewer if map_view else self.app.viewer
        source = panel.source
        assert source is not None
        width, height = panel.display_size
        source_width, source_height = source.size
        event = tk.Event()
        event.x = int(panel.offset[0] + (x + 0.5) * width / source_width)
        event.y = int(panel.offset[1] + (y + 0.5) * height / source_height)
        return event

    def assert_ring(self) -> None:
        panel = self.app.viewer
        source = panel.source
        assert source is not None
        scale_x = panel.display_size[0] / source.width
        scale_y = panel.display_size[1] / source.height
        rectangles = [panel.canvas.coords(item)
                      for item in panel.canvas.find_withtag('window')]
        self.assertEqual(len(rectangles), 4)
        left = min(rectangle[0] for rectangle in rectangles)
        right = max(rectangle[2] for rectangle in rectangles)
        top = min(rectangle[1] for rectangle in rectangles)
        bottom = max(rectangle[3] for rectangle in rectangles)
        self.assertAlmostEqual((right - left) / scale_x, 13)
        self.assertAlmostEqual((bottom - top) / scale_y, 13)
        area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rectangles)
        self.assertAlmostEqual(area / (scale_x * scale_y), 48)

    def test_fit_resize_and_statistics_use_original_pixels(self) -> None:
        original = [row[:] for row in self.app.original]
        for geometry in ('1280x820', '1050x700', '1400x900'):
            self.root.geometry(geometry)
            self.root.update()
            panel = self.app.viewer
            width, height = panel.display_size
            field_width = panel.canvas.winfo_width()
            field_height = panel.canvas.winfo_height()
            self.assertLessEqual(width, field_width)
            self.assertLessEqual(height, field_height)
            self.assertTrue(width == field_width or height == field_height)
            self.assertLessEqual(abs(width - height * 4 / 3), 1)
            for x, y in ((0, 0), (64, 48), (192, 48), (255, 191)):
                self.app.mouse_move(self.event_at(x, y))
                self.assertEqual(self.app.last_pixel, (x, y))
            self.app.mouse_move(self.event_at(64, 48))
            self.assertIn('N=121: μ=58.667; D=2.222',
                          self.app.pixel_info.get())
            self.app.mouse_move(self.event_at(192, 48))
            self.assertIn('μ=101.333; D=2.222; σ=1.491',
                          self.app.pixel_info.get())
            self.assertEqual(self.app.current, original)
            self.assertEqual(self.app.original, original)

    def test_scaled_ring_resize_and_leaving_picture(self) -> None:
        self.app.mouse_move(self.event_at(64, 48))
        self.assert_ring()
        self.root.geometry('1100x730')
        self.root.update()
        self.assert_ring()
        panel = self.app.viewer
        self.assertIsNone(panel.image_coordinates(-1, 0))
        self.assertIsNone(panel.image_coordinates(
            panel.offset[0] + panel.display_size[0], panel.offset[1],
        ))
        event = tk.Event()
        event.x, event.y = -1, 0
        self.app.mouse_move(event)
        self.root.geometry('1280x820')
        self.root.update()
        self.assertIsNone(self.app.last_pixel)
        self.assertFalse(panel.canvas.find_withtag('window'))

    def test_blur_demo_loading_filters_and_reset(self) -> None:
        self.app.load_blur_demo()
        self.root.update()
        original = self.app.original
        self.assertEqual(original[96][64], (255, 255, 255))
        self.app.apply_blur(4)
        self.assertEqual(self.app.current[96][64], (51, 51, 51))
        self.assertEqual(original[96][64], (255, 255, 255))
        self.app.reset()
        self.app.apply_blur(8)
        self.assertEqual(self.app.current[96][64], (28, 28, 28))
        self.app.undo()
        self.assertEqual(self.app.current, original)
        self.app.load_demo()
        self.assertEqual(self.app.current[48][64], (64, 48, 64))

    def test_single_pixel_thin_and_downscaled_images(self) -> None:
        panel = self.app.viewer
        for source_width, source_height in ((1, 1), (1, 192), (256, 1),
                                            (1000, 800)):
            image = [[(17, 38, 91)] * source_width
                     for _ in range(source_height)]
            panel.show(image)
            self.root.update()
            width, height = panel.display_size
            left, top = panel.offset
            self.assertEqual(panel.image_coordinates(left, top), (0, 0))
            self.assertEqual(panel.image_coordinates(
                left + width - 0.0001, top + height - 0.0001,
            ), (source_width - 1, source_height - 1))
            self.assertIsNone(panel.image_coordinates(left, top + height))
            self.assertIsNone(panel.image_coordinates(left - 0.01, top))
            source = panel.source
            assert source is not None
            self.assertEqual(source.size, (source_width, source_height))
            self.assertEqual(image[0][0], (17, 38, 91))

    def test_profile_map_and_cleared_map_after_resize(self) -> None:
        self.app.apply_point('brightness')
        self.root.update()
        self.app.select_profile_row(self.event_at(64, 48))
        self.assertEqual(self.app.profile_row.get(), '48')
        self.assertEqual(self.app.profile_values[64], 176 / 3)
        self.app.notebook.select(3)
        self.root.update()
        self.app.calculate_map()
        self.root.update()
        self.app.map_mouse_move(self.event_at(192, 48, map_view=True))
        self.assertIn('x=192, y=48', self.app.status.get())
        self.assertIn(f'C(p)={self.app.map_values[48][192]:.4f}',
                      self.app.status.get())
        self.app.reset()
        self.root.geometry('1100x730')
        self.root.update()
        self.assertFalse(self.app.map_viewer.canvas.find_all())
        self.assertIsNone(self.app.map_viewer.source)


if __name__ == '__main__':
    unittest.main()
