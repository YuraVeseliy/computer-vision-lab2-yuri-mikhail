"""Юрий: просмотр пикселей, рамка окна и рисование графиков."""

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from image_io import to_pillow
from statistics_ops import RGBImage


class ImagePanel(ttk.Frame):
    """Вписывание изображения и перевод экранных координат."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.photo: ImageTk.PhotoImage | None = None
        self.source: Image.Image | None = None
        self.display_size = (0, 0)
        self.offset = (0, 0)
        self.window_pixel: tuple[int, int] | None = None
        self.canvas = tk.Canvas(
            self, background='#252525', highlightthickness=0,
        )
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.canvas.bind('<Configure>', self.redraw)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def show(self, image: RGBImage) -> None:
        """Показать изображение без изменения массива пикселей."""
        self.source = to_pillow(image)
        self.window_pixel = None
        self.redraw()

    def clear(self) -> None:
        """Убрать картинку, в том числе при следующем изменении окна."""
        self.source = None
        self.photo = None
        self.display_size = (0, 0)
        self.offset = (0, 0)
        self.clear_window()
        self.canvas.delete('all')

    def redraw(self, _event: tk.Event | None = None) -> None:
        """Вписать только экранную копию, сохранив пропорции."""
        if self.source is None:
            return
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        source_width, source_height = self.source.size
        scale = min(width / source_width, height / source_height)
        target_width = max(1, min(width, round(source_width * scale)))
        target_height = max(1, min(height, round(source_height * scale)))
        self.display_size = (target_width, target_height)
        self.offset = ((width - target_width) // 2,
                       (height - target_height) // 2)
        preview = self.source.resize(
            self.display_size, Image.Resampling.NEAREST,
        )
        self.photo = ImageTk.PhotoImage(preview)
        self.canvas.delete('all')
        self.canvas.create_image(
            *self.offset, image=self.photo, anchor='nw',
        )
        if self.window_pixel is not None:
            self.draw_window(*self.window_pixel)

    def image_coordinates(self, x: float, y: float) -> tuple[int, int] | None:
        """Вернуть пиксель массива; вне картинки вернуть None."""
        if self.source is None:
            return None
        local_x = x - self.offset[0]
        local_y = y - self.offset[1]
        width, height = self.display_size
        if not (0 <= local_x < width and 0 <= local_y < height):
            return None
        source_width, source_height = self.source.size
        return (int(local_x * source_width / width),
                int(local_y * source_height / height))

    def clear_window(self) -> None:
        """Убрать рамку и забыть её положение."""
        self.window_pixel = None
        self.canvas.delete('window')

    def draw_window(self, x: int, y: int) -> None:
        """Нарисовать внешнюю рамку 13×13 четырьмя полосками.
        """
        self.canvas.delete('window')
        if self.source is None:
            return
        self.window_pixel = (x, y)
        scale_x = self.display_size[0] / self.source.width
        scale_y = self.display_size[1] / self.source.height
        rectangles = (
            (x - 6, y - 6, x + 7, y - 5),
            (x - 6, y + 6, x + 7, y + 7),
            (x - 6, y - 5, x - 5, y + 6),
            (x + 6, y - 5, x + 7, y + 6),
        )
        for coordinates in rectangles:
            left, top, right, bottom = coordinates
            self.canvas.create_rectangle(
                self.offset[0] + left * scale_x,
                self.offset[1] + top * scale_y,
                self.offset[0] + right * scale_x,
                self.offset[1] + bottom * scale_y,
                fill='yellow', outline='', tags='window',
            )


def draw_plot(
    canvas: tk.Canvas, values: list[float] | list[int],
    color: str, histogram: bool = False,
) -> None:
    """Визуализация уже рассчитанных значений.
    """
    canvas.delete('all')
    width = max(260, canvas.winfo_width())
    height = max(130, canvas.winfo_height())
    left, top, right, bottom = 52, 12, width - 15, height - 30
    peak = max(values) if histogram else 255
    peak = max(1, peak)
    canvas.create_line(
        [left, top, left, bottom, right, bottom], fill='#555555',
    )
    canvas.create_text(left - 7, top, text=f'{peak:.0f}', anchor='e')
    canvas.create_text(left - 7, bottom, text='0', anchor='e')
    canvas.create_text(left, bottom + 14, text='0')
    canvas.create_text(right, bottom + 14, text=str(len(values) - 1))
    if histogram:
        for index, value in enumerate(values):
            x = left + index * (right - left) / 255
            y = bottom - value * (bottom - top) / peak
            canvas.create_line(x, bottom, x, y, fill=color)
    else:
        points = []
        for index, value in enumerate(values):
            x = left + index * (right - left) / max(1, len(values) - 1)
            y = bottom - value * (bottom - top) / 255
            points.extend((x, y))
        if len(values) == 1:
            x, y = points
            canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color)
        elif values:
            canvas.create_line(*points, fill=color, width=2)
