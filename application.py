"""Михаил: состояние программы, события мыши и кнопки."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

import analysis_views
import image_ops
from analysis_views import build_notebook
from editor_controls import build_controls
from image_io import load_rgb, save_rgb
from statistics_ops import (
    RGBImage, ScalarImage, clamp, demo_image,
)
from view_widgets import ImagePanel


class Application:
    """Хранит исходный и текущий массивы.

    Связывает кнопки с расчётами.
    """

    VIEW_NAMES = ('RGB текущее', 'RGB исходное', 'Яркость I', 'Канал R',
                  'Канал G', 'Канал B')
    CHANNEL_NAMES = ('Все RGB / яркость', 'R', 'G', 'B')

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        # Виджеты создаёт build_notebook; аннотации описывают их типы.
        self.viewer: ImagePanel
        self.map_viewer: ImagePanel
        self.notebook: ttk.Notebook
        self.channels_tab: ttk.Frame
        self.preview_labels: list[ttk.Label]
        self.histogram_canvases: list[tk.Canvas]
        self.profile_canvas: tk.Canvas
        self.original: RGBImage = []
        self.current: RGBImage = []
        self.previous: RGBImage = []
        self.last_pixel: tuple[int, int] | None = None
        self.map_values: ScalarImage = []
        self.thumbnail_photos: list[ImageTk.PhotoImage] = []
        self.distributions: list[list[int]] = []
        self.profile_values: list[float] = []

        self.view = tk.StringVar(value=self.VIEW_NAMES[0])
        self.channel = tk.StringVar(value=self.CHANNEL_NAMES[0])
        self.method = tk.StringVar(value='Два прохода')
        self.delta = tk.StringVar(value='20')
        self.factor = tk.StringVar(value='1.2')
        self.gamma = tk.StringVar(value='0.5')
        self.swap_pair = tk.StringVar(value='R ↔ G')
        self.profile_row = tk.StringVar(value='0')
        self.neighborhood = tk.StringVar(value='4 соседа')
        self.window_size = tk.StringVar(value='11')
        self.status = tk.StringVar(
            value='Откройте RGB-изображение или учебный пример.',
        )
        self.pixel_info = tk.StringVar(
            value='Двигайте мышь внутри изображения.',
        )
        self.map_info = tk.StringVar(value='Нажмите «Рассчитать карту».')

        root.title('Практическая работа 2 — статистика по изображению')
        root.geometry('1280x820')
        root.minsize(1050, 700)
        self.build_interface()

    def build_interface(self) -> None:
        toolbar = ttk.Frame(self.root, padding=6)
        toolbar.pack(fill='x')
        buttons = (
            ('Открыть', self.open_image),
            ('Сохранить RGB', self.save_image),
            ('Учебный пример', self.load_demo),
            ('Исходное', self.reset),
            ('Отменить последнее', self.undo),
        )
        for text, command in buttons:
            ttk.Button(toolbar, text=text, command=command).pack(
                side='left', padx=3,
            )
        body = ttk.Frame(self.root, padding=6)
        body.pack(fill='both', expand=True)
        controls = ttk.Frame(body, width=230, padding=(0, 0, 10, 0))
        controls.pack(side='left', fill='y')
        build_controls(self, controls)
        build_notebook(self, body)
        ttk.Label(
            self.root, textvariable=self.status, padding=6,
        ).pack(fill='x')

    def need_image(self) -> bool:
        if self.current:
            return True
        messagebox.showinfo('Нет изображения', 'Сначала откройте изображение.')
        return False

    def set_image(self, image: RGBImage, name: str) -> None:
        self.original = image
        self.current = image
        self.previous = []
        self.profile_row.set('0')
        self.view.set(self.VIEW_NAMES[0])
        self.status.set(
            f'{name}: {len(image[0])}×{len(image)}, RGB, 8 бит на канал.',
        )
        self.refresh()
        self.show_profile()

    def open_image(self) -> None:
        path = filedialog.askopenfilename(
            title='Открыть RGB без потерь',
            filetypes=[('PNG, BMP, TIFF', '*.png *.bmp *.tif *.tiff')],
        )
        if path:
            try:
                self.set_image(load_rgb(path), path)
            except (OSError, ValueError) as error:
                messagebox.showerror('Ошибка загрузки', str(error))

    def load_demo(self) -> None:
        self.set_image(demo_image(), 'Учебный пример')

    def save_image(self) -> None:
        if not self.need_image():
            return
        path = filedialog.asksaveasfilename(
            title='Сохранить текущий RGB', defaultextension='.png',
            filetypes=[('PNG', '*.png'), ('BMP', '*.bmp'), ('TIFF', '*.tif')],
        )
        if path:
            try:
                save_rgb(self.current, path)
                self.status.set(f'Сохранено: {path}')
            except (OSError, ValueError) as error:
                messagebox.showerror('Ошибка сохранения', str(error))

    def refresh(self) -> None:
        analysis_views.refresh(self)

    def change_view(self, _event: tk.Event | None = None) -> None:
        analysis_views.change_view(self)

    def redraw_histograms(self, _event: tk.Event | None = None) -> None:
        analysis_views.redraw_histograms(self)

    def show_profile(self) -> None:
        analysis_views.show_profile(self)

    def redraw_profile(self, _event: tk.Event | None = None) -> None:
        analysis_views.redraw_profile(self)

    def mouse_move(self, event: tk.Event) -> None:
        if not self.current:
            return
        image = (self.original if self.view.get() == self.VIEW_NAMES[1]
                 else self.current)
        canvas = self.viewer.canvas
        mouse_x, mouse_y = canvas.canvasx(event.x), canvas.canvasy(event.y)
        if not (0 <= mouse_x < len(image[0]) and 0 <= mouse_y < len(image)):
            self.mouse_leave()
            return
        x, y = int(mouse_x), int(mouse_y)
        if self.last_pixel == (x, y):
            return
        self.last_pixel = (x, y)
        self.update_pixel_info(x, y, image)

    def update_pixel_info(self, x: int, y: int, image: RGBImage) -> None:
        analysis_views.update_pixel_info(self, x, y, image)

    def mouse_leave(self, _event: tk.Event | None = None) -> None:
        self.viewer.canvas.delete('window')
        self.last_pixel = None
        self.pixel_info.set('Двигайте мышь внутри изображения.')

    def change_method(self, _event: tk.Event | None = None) -> None:
        if self.last_pixel is not None:
            image = (self.original if self.view.get() == self.VIEW_NAMES[1]
                     else self.current)
            self.update_pixel_info(*self.last_pixel, image)

    def select_profile_row(self, event: tk.Event) -> None:
        if not self.current:
            return
        self.mouse_move(event)
        if self.last_pixel is not None:
            self.profile_row.set(str(self.last_pixel[1]))
            self.show_profile()
            self.notebook.select(2)

    def commit_image(self, image: RGBImage, description: str) -> None:
        self.previous = self.current
        self.current = image
        self.view.set(self.VIEW_NAMES[0])
        self.refresh()
        self.status.set(description)

    def apply_point(self, operation: str) -> None:
        if not self.need_image():
            return
        variables = {'brightness': self.delta, 'contrast': self.factor,
                     'gamma': self.gamma}
        try:
            parameter = 0.0
            if operation != 'negative':
                parameter = float(variables[operation].get().replace(',', '.'))
                if not -10000 <= parameter <= 10000:
                    raise ValueError('Нужно число от -10000 до 10000.')
            channel = self.CHANNEL_NAMES.index(self.channel.get()) - 1
            result = image_ops.point_transform(
                self.current, operation, parameter, channel,
            )
            names = {'brightness': 'яркость', 'contrast': 'контраст',
                     'negative': 'негатив', 'gamma': 'гамма-коррекция'}
            self.commit_image(
                result, f'Применено: {names[operation]}, '
                f'параметр {parameter}, каналы: {self.channel.get()}.',
            )
        except ValueError as error:
            messagebox.showerror('Ошибка параметра', str(error))

    def apply_swap(self) -> None:
        if self.need_image():
            pairs = {'R ↔ G': (0, 1), 'R ↔ B': (0, 2), 'G ↔ B': (1, 2)}
            result = image_ops.swap_channels(
                self.current, *pairs[self.swap_pair.get()],
            )
            self.commit_image(
                result, f'Обмен каналов: {self.swap_pair.get()}.',
            )

    def apply_mirror(self, horizontal: bool) -> None:
        if self.need_image():
            result = image_ops.mirror(self.current, horizontal)
            self.commit_image(result, 'Применено зеркальное отражение.')

    def apply_blur(self, connectivity: int) -> None:
        if self.need_image():
            self.root.configure(cursor='watch')
            self.root.update_idletasks()
            try:
                result = image_ops.blur(self.current, connectivity)
                self.commit_image(
                    result, f'Размытие: центр + {connectivity} соседей.',
                )
            finally:
                self.root.configure(cursor='')

    def reset(self) -> None:
        if self.need_image():
            self.commit_image(self.original, 'Восстановлено исходное RGB.')

    def undo(self) -> None:
        if self.previous:
            self.current, self.previous = self.previous, []
            self.view.set(self.VIEW_NAMES[0])
            self.refresh()
            self.status.set('Последняя операция отменена.')

    def calculate_map(self) -> None:
        if not self.need_image():
            return
        self.root.configure(cursor='watch')
        self.root.update_idletasks()
        try:
            choices = {'4 соседа': '4', '8 соседей': '8',
                       'Квадратное окно': 'window'}
            neighborhood = choices[self.neighborhood.get()]
            size = (int(self.window_size.get())
                    if neighborhood == 'window' else 11)
            self.map_values, global_contrast = image_ops.contrast_map(
                self.current, neighborhood, size,
            )
            display = []
            for row in self.map_values:
                output_row = []
                for value in row:
                    gray = clamp(value)
                    output_row.append((gray, gray, gray))
                display.append(output_row)
            self.map_viewer.show(display)
            description = self.neighborhood.get()
            if neighborhood == 'window':
                description += f', размер окна={size}'
            self.map_info.set(
                f'{description}; '
                f'C(I)={global_contrast:.4f}. Шкала 0..255 без растяжения.',
            )
        except ValueError as error:
            messagebox.showerror('Ошибка карты', str(error))
        finally:
            self.root.configure(cursor='')

    def map_mouse_move(self, event: tk.Event) -> None:
        if not self.map_values:
            return
        canvas = self.map_viewer.canvas
        mouse_x, mouse_y = canvas.canvasx(event.x), canvas.canvasy(event.y)
        if (0 <= mouse_x < len(self.map_values[0])
                and 0 <= mouse_y < len(self.map_values)):
            x, y = int(mouse_x), int(mouse_y)
            self.status.set(f'Карта контрастности: x={x}, y={y}, '
                            f'C(p)={self.map_values[y][x]:.4f}.')
