"""просмотр пикселей, рамка окна и рисование графиков."""

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from image_io import to_pillow
from statistics_ops import RGBImage


class ImagePanel(ttk.Frame):
    """Вписывание изображения и перевод экранных координат"""
    def __init__(self, parent: tk.Misc) -> None: # контейнер панели
        super().__init__(parent) # инициализация ttk frame
        self.photo: ImageTk.PhotoImage | None = None # атрибут объекта фото Tkinter
        self.source: Image.Image | None = None # хранение изображения в полном размере
        self.display_size = (0, 0)
        self.offset = (0, 0) # смещения для размещения картинки по центру
        self.window_pixel: tuple[int, int] | None = None # сохранение координат пикселя для рисования окна
        self.canvas = tk.Canvas(
            self, background='#252525', highlightthickness=0, # фон
        )
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.canvas.bind('<Configure>', self.redraw) # перерисование картинки
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def show(self, image: RGBImage) -> None:
        """Показ изображения на панели."""
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
        if self.source is None: # если картинки нет то завершаем метод
            return
        width = max(1, self.canvas.winfo_width()) # ширина области рисования
        height = max(1, self.canvas.winfo_height()) # высота области рисования
        source_width, source_height = self.source.size # получение размеров исходного изобр.
        scale = min(width / source_width, height / source_height) # масштаб
        target_width = max(1, min(width, round(source_width * scale))) # расчет размера экранной копии
        target_height = max(1, min(height, round(source_height * scale)))
        self.display_size = (target_width, target_height) # сохранение размеров в атрибут
        self.offset = ((width - target_width) // 2,
                       (height - target_height) // 2)
        preview = self.source.resize( # создание экраннйо копии через resize
            self.display_size, Image.Resampling.NEAREST, # Каждый пиксель экранной копии получает цвет ближайшего пикселя исходного изображения
        )
        self.photo = ImageTk.PhotoImage(preview) # экранная копия в объект для tkinter
        self.canvas.delete('all')
        self.canvas.create_image(
            *self.offset, image=self.photo, anchor='nw', # размещение новой картинки на чистом поле слева сверху
        )
        if self.window_pixel is not None: # восстановление рамки 11х11
            self.draw_window(*self.window_pixel)

    def image_coordinates(self, x: float, y: float) -> tuple[int, int] | None:
        """перевод координат мыши в координаты пикселя исходного изображения.."""
        if self.source is None:
            return None
        local_x = x - self.offset[0]
        local_y = y - self.offset[1]
        width, height = self.display_size
        if not (0 <= local_x < width and 0 <= local_y < height):
            return None
        source_width, source_height = self.source.size # пеервод координат из масштаба копии в исходный
        return (int(local_x * source_width / width),
                int(local_y * source_height / height))

    def clear_window(self) -> None:
        """Убрать рамку и забыть её положение."""
        self.window_pixel = None
        self.canvas.delete('window')

    def draw_window(self, x: int, y: int) -> None:
        """Нарисовать внешнюю рамку 13×13 четырьмя полосками.
        """
        self.canvas.delete('window') # удаление рамки при движении мышкой
        if self.source is None:
            return
        self.window_pixel = (x, y)
        scale_x = self.display_size[0] / self.source.width
        scale_y = self.display_size[1] / self.source.height
        rectangles = ( # создание полосок
            (x - 6, y - 6, x + 7, y - 5),
            (x - 6, y + 6, x + 7, y + 7),
            (x - 6, y - 5, x - 5, y + 6),
            (x + 6, y - 5, x + 7, y + 6),
        )
        for coordinates in rectangles: # рисование полосок
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
    canvas.delete('all') # удаление прошлого графика
    width = max(260, canvas.winfo_width()) # размеры и отступы
    height = max(130, canvas.winfo_height())
    left, top, right, bottom = 52, 12, width - 15, height - 30 # границы графика
    peak = max(values) if histogram else 255 # верхняя граница шкалы y
    peak = max(1, peak) # не может быть равно 0 счетчики
    canvas.create_line( # рисование осей
        [left, top, left, bottom, right, bottom], fill='#555555',
    )
    # подписи осей
    canvas.create_text(left - 7, top, text=f'{peak:.0f}', anchor='e')
    canvas.create_text(left - 7, bottom, text='0', anchor='e')
    canvas.create_text(left, bottom + 14, text='0')
    canvas.create_text(right, bottom + 14, text=str(len(values) - 1))
    if histogram:
        for index, value in enumerate(values): # индексы - яркость, значение - число пикселей
            x = left + index * (right - left) / 255
            y = bottom - value * (bottom - top) / peak
            canvas.create_line(x, bottom, x, y, fill=color)
    else:
        points = [] # профиль исходного
        for index, value in enumerate(values):
            x = left + index * (right - left) / max(1, len(values) - 1) # перевод значение пикселя в координаты
            y = bottom - value * (bottom - top) / 255 # y = низ_графика - доля_яркости * высота_графика
            points.extend((x, y)) # перевод положения и яркость в экранные координаты
        if len(values) == 1: # показ одной точки или линии
            x, y = points # извлечение двух координат если в строке только один пиксель
            canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=color)
        elif values:
            canvas.create_line(*points, fill=color, width=2) # рисование профиля
