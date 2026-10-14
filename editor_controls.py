"""Михаил: элементы управления редактированием и параметрами."""

from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application import Application


def build_controls(app: 'Application', parent: ttk.Frame) -> None:
    ttk.Label(
        parent, text='Редактирование текущего RGB',
        font=('Segoe UI', 10, 'bold'),
    ).pack(anchor='w', pady=5)
    ttk.Label(parent, text='Целевые каналы:').pack(anchor='w')
    ttk.Combobox(
        parent, textvariable=app.channel, values=app.CHANNEL_NAMES,
        state='readonly', width=23,
    ).pack(fill='x', pady=4)
    fields = (
        ('Изменение яркости Δ:', app.delta, 'brightness', 'Изменить яркость'),
        ('Коэффициент контраста k:', app.factor, 'contrast', 'Контраст'),
        ('Собственная идея: гамма γ:', app.gamma, 'gamma', 'Гамма-коррекция'),
    )
    for label, variable, operation, button in fields:
        ttk.Label(parent, text=label).pack(anchor='w', pady=(9, 0))
        ttk.Entry(parent, textvariable=variable, width=12).pack(fill='x')
        ttk.Button(
            parent, text=button,
            command=lambda op=operation: app.apply_point(op),
        ).pack(fill='x', pady=3)
    ttk.Button(
        parent, text='Негатив выбранных каналов',
        command=lambda: app.apply_point('negative'),
    ).pack(fill='x', pady=5)
    ttk.Separator(parent).pack(fill='x', pady=6)
    ttk.Combobox(
        parent, textvariable=app.swap_pair,
        values=('R ↔ G', 'R ↔ B', 'G ↔ B'), state='readonly',
    ).pack(fill='x')
    ttk.Button(
        parent, text='Обменять каналы', command=app.apply_swap,
    ).pack(fill='x', pady=3)
    ttk.Button(
        parent, text='Зеркало: слева ↔ справа',
        command=lambda: app.apply_mirror(True),
    ).pack(fill='x', pady=2)
    ttk.Button(
        parent, text='Зеркало: сверху ↔ снизу',
        command=lambda: app.apply_mirror(False),
    ).pack(fill='x', pady=2)
    ttk.Button(
        parent, text='Размытие: центр + 4 соседа',
        command=lambda: app.apply_blur(4),
    ).pack(fill='x', pady=(9, 2))
    ttk.Button(
        parent, text='Размытие: центр + 8 соседей',
        command=lambda: app.apply_blur(8),
    ).pack(fill='x', pady=2)
    ttk.Separator(parent).pack(fill='x', pady=9)
    ttk.Label(parent, text='Расчёт дисперсии окна:').pack(anchor='w')
    method_box = ttk.Combobox(
        parent, textvariable=app.method,
        values=('Два прохода', 'Один проход'), state='readonly',
    )
    method_box.pack(fill='x', pady=3)
    method_box.bind('<<ComboboxSelected>>', app.change_method)
