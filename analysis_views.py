"""Юрий: вкладки просмотра, каналов, профиля, карты и справки."""

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

HELP_TEXT = """Практическая работа 2 — статистика по изображению

Начало координат: слева сверху.
x — столбец, y — строка, индексы от 0.
Яркость по заданию: I = (R + G + B) / 3.
Окно статистики 11×11: центр и по 5 пикселей в каждую сторону.
Внешняя жёлтая рамка занимает 13×13 пикселей.
Само окно она не закрашивает.
На границе берётся пересечение окна с изображением.
Размер N показан.

Среднее: μ = ΣI / N.
Дисперсия: D = Σ(I - μ)² / N = ΣI² / N - μ².
Стандартное отклонение: σ = √D. Делитель N, а не N - 1.
В переключателе можно выбрать любой из двух способов расчёта.
Гистограммы: абсолютные количества пикселей уровней 0..255.
Для отображения серого и гистограммы I округляется до целого.
Статистика, профиль и карта используют неокруглённую яркость.

Яркость: c' = clip(c + Δ). Общая яркость: Δ добавляется всем каналам.
Контраст: c' = clip(μ + k(c - μ)), k≥0. k=1 сохраняет, k=0 выравнивает.
Негатив: c' = 255 - c. Для всех каналов также I' = 255 - I.
Гамма-коррекция (собственная идея): c' = 255(c/255)^γ, γ>0.
γ<1 осветляет, γ>1 затемняет, γ=1 сохраняет изображение.
clip ограничивает 0..255 и округляет до ближайшего целого.
Обмен каналов меняет местами выбранные компоненты
каждого пикселя.
Зеркало слева/справа: x' = width - 1 - x.
Зеркало сверху/снизу: y' = height - 1 - y.
Размытие усредняет центр с соседями: 5 точек для 4-связности,
9 точек для 8-связности; на границе только существующие точки.
Новое изображение хранится отдельно.
Уже изменённые пиксели не читаются.

Карта контрастности (лекция 2_1, слайд 11):
C(p) = |I(p) - μ соседей|, C(I) = ΣC(p) / (width·height).
Центр НЕ включён в соседей.
Окно имеет нечётную сторону не меньше 3.
Если соседей нет (картинка 1×1), контраст принят равным 0.
Карта показана в исходной шкале 0..255, без растяжения для красоты.

Профиль всегда относится к исходному изображению,
даже после обработки.
На вкладке просмотра можно выбрать исходное RGB
или текущий вариант.
Гистограммы, каналы и карта относятся к текущему варианту.
После обработки старую карту нужно рассчитать заново.

Для сравнения областей нажмите «Учебный пример»:
однородная точка (64, 48): μ=128, D=0, σ=0;
полосатая точка (192, 48): μ=128, D=100000/11, σ≈95.35.
Среднее одинаково, но распределения и дисперсии
сильно различаются.
Однородность относительна масштабу окна: узкая гистограмма,
малая дисперсия и малое СКО; неоднородность — широкий разброс
или несколько пиков. Одного среднего для вывода недостаточно.

Загрузка: 8-битное RGB PNG/BMP/TIFF без потерь; TIFF — первый кадр.
Прозрачные и 16-битные изображения не преобразуются молча.
Сохранение: только текущие RGB-пиксели, без рамок и графиков.
Для защиты приготовьте бумагу
или другое удобное средство рисования.
"""


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
    ttk.Label(viewer_tab, textvariable=app.pixel_info, justify='left',
              padding=7).pack(fill='x')

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

    help_tab = ttk.Frame(app.notebook)
    app.notebook.add(help_tab, text='Формулы и пояснения')
    help_box = tk.Text(
        help_tab, wrap='word', font=('Segoe UI', 11), padx=12, pady=8,
    )
    help_scroll = ttk.Scrollbar(help_tab, command=help_box.yview)
    help_box.configure(yscrollcommand=help_scroll.set)
    help_scroll.pack(side='right', fill='y')
    help_box.pack(fill='both', expand=True)
    help_box.insert('1.0', HELP_TEXT)
    help_box.configure(state='disabled')


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
    app.map_viewer.canvas.delete('all')
    app.map_viewer.photo = None
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
