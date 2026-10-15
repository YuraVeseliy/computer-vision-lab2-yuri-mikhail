"""вкладки просмотра, каналов, профиля и карты."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import TYPE_CHECKING

from PIL import Image, ImageTk

from image_io import to_pillow
from statistics_ops import (
    RGBImage, component_image, histograms, intensity, row_profile,
    statistics, window_values,
)
from view_widgets import ImagePanel, draw_plot

if TYPE_CHECKING:
    from application import Application


def build_notebook(app: 'Application', parent: ttk.Frame) -> None:
    app.notebook = ttk.Notebook(parent)
    app.notebook.pack(side='left', fill='both', expand=True)
    viewer_tab = ttk.Frame(app.notebook)
    app.notebook.add(viewer_tab, text='Просмотр и окно 11×11')
    selector = ttk.Combobox(
        viewer_tab, textvariable=app.view,
        values=app.VIEW_NAMES, state='readonly', width=25,
    )
    selector.pack(anchor='w', pady=5)
    selector.bind('<<ComboboxSelected>>', app.change_view)
    app.viewer = ImagePanel(viewer_tab)
    app.viewer.pack(fill='both', expand=True)
    app.viewer.canvas.bind('<Motion>', app.mouse_move)
    app.viewer.canvas.bind('<Leave>', app.mouse_leave)
    app.viewer.canvas.bind('<Button-1>', app.select_profile_row)
    # Высота в две строки постоянна: иначе смена текста меняет
    # размер Canvas, картинка сдвигается, и у края она дёргается.
    tk.Label(viewer_tab, textvariable=app.pixel_info, justify='left',
             anchor='w', height=2, padx=7, pady=7).pack(fill='x')

    app.channels_tab = ttk.Frame(app.notebook)
    app.notebook.add(app.channels_tab, text='Каналы и гистограммы')
    app.preview_labels = []
    app.histogram_canvases = []
    titles = ('Яркость I=(R+G+B)/3', 'Красный канал R',
              'Зелёный канал G', 'Синий канал B')
    for index, title in enumerate(titles):
        panel = ttk.LabelFrame(app.channels_tab, text=title, padding=4)
        panel.grid(
            row=index // 2, column=index % 2,
            sticky='nsew', padx=3, pady=3,
        )
        preview = ttk.Label(panel, anchor='center')
        preview.pack(fill='x')
        plot = tk.Canvas(panel, background='white', height=145,
                         highlightthickness=0)
        plot.pack(fill='both', expand=True)
        plot.bind('<Configure>', app.redraw_histograms)
        app.preview_labels.append(preview)
        app.histogram_canvases.append(plot)
    for index in range(2):
        app.channels_tab.rowconfigure(index, weight=1)
        app.channels_tab.columnconfigure(index, weight=1)

    profile_tab = ttk.Frame(app.notebook, padding=8)
    app.notebook.add(profile_tab, text='Профиль исходного')
    profile_controls = ttk.Frame(profile_tab)
    profile_controls.pack(fill='x')
    ttk.Label(profile_controls, text='Строка y (от 0):').pack(side='left')
    ttk.Entry(
        profile_controls, textvariable=app.profile_row, width=9,
    ).pack(side='left', padx=5)
    ttk.Button(
        profile_controls, text='Показать', command=app.show_profile,
    ).pack(side='left')
    ttk.Label(
        profile_tab, text='Профиль строится по исходному RGB. '
        'Строку можно выбрать щелчком на вкладке просмотра.',
    ).pack(anchor='w', pady=6)
    app.profile_canvas = tk.Canvas(
        profile_tab, background='white', highlightthickness=0,
    )
    app.profile_canvas.pack(fill='both', expand=True)
    app.profile_canvas.bind('<Configure>', app.redraw_profile)

    map_tab = ttk.Frame(app.notebook, padding=6)
    app.notebook.add(map_tab, text='Карта контрастности')
    map_controls = ttk.Frame(map_tab)
    map_controls.pack(fill='x')
    ttk.Combobox(map_controls, textvariable=app.neighborhood, width=15,
                 values=('4 соседа', '8 соседей', 'Квадратное окно'),
                 state='readonly').pack(side='left')
    ttk.Label(map_controls, text='Размер окна:').pack(side='left', padx=5)
    ttk.Entry(
        map_controls, textvariable=app.window_size, width=6,
    ).pack(side='left')
    ttk.Button(map_controls, text='Рассчитать карту',
               command=app.calculate_map).pack(side='left', padx=5)
    app.map_viewer = ImagePanel(map_tab)
    app.map_viewer.pack(fill='both', expand=True, pady=6)
    app.map_viewer.canvas.bind('<Motion>', app.map_mouse_move)
    ttk.Label(
        map_tab, textvariable=app.map_info, padding=5,
    ).pack(fill='x')


def refresh(app: 'Application') -> None:
    app.last_pixel = None
    app.pixel_info.set(
        'Двигайте мышь; щелчок выбирает строку профиля.',
    )
    app.change_view()
    app.distributions = histograms(app.current)
    app.thumbnail_photos = []
    for index in range(4):
        preview = to_pillow(component_image(app.current, index - 1))
        # Уменьшение относится только к экранному превью.
        # Вычисления используют полный массив изображения.
        preview.thumbnail((320, 145), Image.Resampling.NEAREST)
        photo = ImageTk.PhotoImage(preview)
        app.thumbnail_photos.append(photo)
        app.preview_labels[index].configure(image=photo)
    app.redraw_histograms()
    app.map_values = []
    app.map_viewer.clear()
    app.map_info.set('C(p)=|I(p)-μ соседей|. Нажмите «Рассчитать карту».')


def change_view(app: 'Application') -> None:
    if not app.current:
        return
    index = app.VIEW_NAMES.index(app.view.get())
    if index == 0:
        image = app.current
    elif index == 1:
        image = app.original
    else:
        image = component_image(app.current, index - 3)
    app.viewer.show(image)
    app.last_pixel = None
    app.pixel_info.set('Двигайте мышь внутри изображения.')


def redraw_histograms(app: 'Application') -> None:
    if app.distributions:
        colors = ('#333333', '#d03030', '#208020', '#3050d0')
        for canvas, values, color in zip(app.histogram_canvases,
                                         app.distributions, colors):
            draw_plot(canvas, values, color, histogram=True)


def show_profile(app: 'Application') -> None:
    if not app.need_image():
        return
    try:
        row_y = int(app.profile_row.get())
        app.profile_values = row_profile(app.original, row_y)
        app.redraw_profile()
    except ValueError as error:
        messagebox.showerror('Ошибка номера строки', str(error))


def redraw_profile(app: 'Application') -> None:
    if app.profile_values:
        draw_plot(app.profile_canvas, app.profile_values, '#8050b0')


def update_pixel_info(
    app: 'Application', x: int, y: int, image: RGBImage,
) -> None:
    app.viewer.draw_window(x, y)
    pixel = image[y][x]
    values = window_values(image, x, y)
    method = ('two_pass' if app.method.get() == 'Два прохода'
              else 'one_pass')
    mean, variance, deviation = statistics(values, method)
    source_name = ('исходное RGB' if app.view.get() == app.VIEW_NAMES[1]
                   else 'текущее RGB')
    app.pixel_info.set(
        f'{source_name}: x={x}, y={y}; '
        f'R={pixel[0]}, G={pixel[1]}, B={pixel[2]}; '
        f'I(p)={intensity(pixel):.3f}\n'
        f'Окно 11×11, N={len(values)}: μ={mean:.3f}; '
        f'D={variance:.3f}; σ={deviation:.3f}; '
        f'{app.method.get().lower()}.'
    )
