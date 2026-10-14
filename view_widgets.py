"""Юрий: просмотр пикселей, рамка окна и рисование графиков."""

import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

from image_io import to_pillow
from statistics_ops import RGBImage


class ImagePanel(ttk.Frame):
    """Изображение в масштабе 1:1, прокрутка и события мыши."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.photo: ImageTk.PhotoImage | None = None
        self.canvas = tk.Canvas(
            self, background='#252525', highlightthickness=0,
        )
        vertical = ttk.Scrollbar(
            self, orient='vertical', command=self.canvas.yview,
        )
        horizontal = ttk.Scrollbar(
            self, orient='horizontal', command=self.canvas.xview,
        )
        self.canvas.configure(
            yscrollcommand=vertical.set, xscrollcommand=horizontal.set,
        )
        self.canvas.grid(row=0, column=0, sticky='nsew')
        vertical.grid(row=0, column=1, sticky='ns')
        horizontal.grid(row=1, column=0, sticky='ew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def show(self, image: RGBImage) -> None:
        """Показать изображение без изменения массива пикселей."""
        self.photo = ImageTk.PhotoImage(to_pillow(image))
        self.canvas.delete('all')
        self.canvas.create_image(0, 0, image=self.photo, anchor='nw')
        self.canvas.configure(scrollregion=(0, 0, len(image[0]), len(image)))

    def draw_window(self, x: int, y: int) -> None:
        """Нарисовать внешнюю рамку 13×13 четырьмя полосками.

        Ширина каждой полоски — один пиксель.
        """
        self.canvas.delete('window')
        rectangles = (
            (x - 6, y - 6, x + 7, y - 5),
            (x - 6, y + 6, x + 7, y + 7),
            (x - 6, y - 5, x - 5, y + 6),
            (x + 6, y - 5, x + 7, y + 6),
        )
        for coordinates in rectangles:
            self.canvas.create_rectangle(
                *coordinates, fill='yellow', outline='', tags='window',
            )


def draw_plot(
    canvas: tk.Canvas, values: list[float] | list[int],
    color: str, histogram: bool = False,
) -> None:
    """Визуализация уже рассчитанных значений.

    Библиотеки статистики не используются.
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
