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

# создание вкладок
def build_notebook(app: 'Application', parent: ttk.Frame) -> None:
    app.notebook = ttk.Notebook(parent)
    app.notebook.pack(side='left', fill='both', expand=True) # создание контейнера
    viewer_tab = ttk.Frame(app.notebook)
    app.notebook.add(viewer_tab, text='Просмотр и окно 11×11')
    selector = ttk.Combobox( # создание выпадающего списка r g b и яркости
        viewer_tab, textvariable=app.view,
        values=app.VIEW_NAMES, state='readonly', width=25,
    )
    selector.pack(anchor='w', pady=5) # расположение списка
    selector.bind('<<ComboboxSelected>>', app.change_view) # для показа нужного пункта
    app.viewer = ImagePanel(viewer_tab)
    app.viewer.pack(fill='both', expand=True) # фон панели
    app.viewer.canvas.bind('<Motion>', app.mouse_move)
    app.viewer.canvas.bind('<Leave>', app.mouse_leave)
    app.viewer.canvas.bind('<Button-1>', app.select_profile_row)
    tk.Label(viewer_tab, textvariable=app.pixel_info, justify='left',
             anchor='w', height=2, padx=7, pady=7).pack(fill='x') # текстовая облась снизу

    app.channels_tab = ttk.Frame(app.notebook)
    app.notebook.add(app.channels_tab, text='Каналы и гистограммы')
    app.preview_labels = [] # картинки каналов (элементы интерфейса)
    app.histogram_canvases = [] # где рисуются гистограммы (элементы интерфейса)
    titles = ('Яркость I=(R+G+B)/3', 'Красный канал R',
              'Зелёный канал G', 'Синий канал B')
    for index, title in enumerate(titles):
        panel = ttk.LabelFrame(app.channels_tab, text=title, padding=4)
        panel.grid( # размещение панелей в сетке 2х2
            row=index // 2, column=index % 2,
            sticky='nsew', padx=3, pady=3,
        )
        preview = ttk.Label(panel, anchor='center')
        preview.pack(fill='x') # элемент над графиком
        plot = tk.Canvas(panel, background='white', height=145,
                         highlightthickness=0)
        plot.pack(fill='both', expand=True) # белая область для гистограммы
        plot.bind('<Configure>', app.redraw_histograms) # перерисовка при изменениях
        app.preview_labels.append(preview)
        app.histogram_canvases.append(plot)
    for index in range(2): # доп пространство при увеличении окна для каждого графика
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
    app.profile_canvas = tk.Canvas( # белый фон на котором строится график
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
    app.map_viewer.pack(fill='both', expand=True, pady=6) # создаени панели лоя карты контрастности
    app.map_viewer.canvas.bind('<Motion>', app.map_mouse_move) # значение мышки
    ttk.Label(
        map_tab, textvariable=app.map_info, padding=5,
    ).pack(fill='x') # надпись снизу инфа


def refresh(app: 'Application') -> None: # обновление изображения после изменений
    app.last_pixel = None # сброс последних координат под мышкой
    app.pixel_info.set(
        'Двигайте мышь; щелчок выбирает строку профиля.',
    )
    app.change_view()
    app.distributions = histograms(app.current) # вычисление гистограмм по текузему изображению
    app.thumbnail_photos = [] # сохранение всех картинок на вкладке гистограмм
    for index in range(4):
        preview = to_pillow(component_image(app.current, index - 1)) # картинка над графиками
        preview.thumbnail((320, 145), Image.Resampling.NEAREST)
        photo = ImageTk.PhotoImage(preview)
        app.thumbnail_photos.append(photo)
        app.preview_labels[index].configure(image=photo) # добавляем индекс к каждой картнике
    app.redraw_histograms() # рисование 4 графиков
    app.map_values = [] # удаление карты контрстности при измененях
    app.map_viewer.clear()
    app.map_info.set('C(p)=|I(p)-μ соседей|. Нажмите «Рассчитать карту».')


def change_view(app: 'Application') -> None: # переключтаель изображений
    if not app.current:
        return # пустой список если изображения нет
    index = app.VIEW_NAMES.index(app.view.get())
    if index == 0:
        image = app.current # для ргб текущее выбирается текущая картинка
    elif index == 1:
        image = app.original # исходное
    else:
        image = component_image(app.current, index - 3) # для каждого канала яркость в сером цвете
    app.viewer.show(image)
    app.last_pixel = None
    app.pixel_info.set('Двигайте мышь внутри изображения.')


def redraw_histograms(app: 'Application') -> None: # перерисовка графиков после изменений
    if app.distributions:
        colors = ('#333333', '#d03030', '#208020', '#3050d0')
        for canvas, values, color in zip(app.histogram_canvases,
                                         app.distributions, colors): # объединяем элементы с одинаковыми номерами из трех последовательностей
            draw_plot(canvas, values, color, histogram=True)


def show_profile(app: 'Application') -> None: # получение номера строки и рисование графика по ней
    if not app.need_image():
        return
    try:
        row_y = int(app.profile_row.get()) # значение должно быть int
        app.profile_values = row_profile(app.original, row_y) # должно быть в границах
        app.redraw_profile() # рисование графика по сохраненному списку
    except ValueError as error:
        messagebox.showerror('Ошибка номера строки', str(error))


def redraw_profile(app: 'Application') -> None: # рисование профиля строки по расчитанным яркостям
    if app.profile_values: # проверка на пустоту списка яркостей
        draw_plot(app.profile_canvas, app.profile_values, '#8050b0')


def update_pixel_info( # обновление данных о пикселе под мышкой
    app: 'Application', x: int, y: int, image: RGBImage,
) -> None:
    app.viewer.draw_window(x, y) # рисование рамки вокруг мышки
    pixel = image[y][x] # р г б пикселей
    values = window_values(image, x, y) # яркости пикселей
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
