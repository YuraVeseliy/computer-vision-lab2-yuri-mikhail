"""Загрузка, сохранение и отображение через Pillow."""

from pathlib import Path # пути к файлам

from PIL import Image # работа с изображениям

from statistics_ops import RGBImage


def load_rgb(path: str) -> RGBImage:
    """загрузка 8-бит RGB-изображения PNG/BMP/TIFF"""
    with Image.open(path) as source: # открытие файла и помещение его в source
        if source.format not in ('PNG', 'BMP', 'TIFF'):
            raise ValueError('Нужен PNG, BMP или TIFF без сжатия и потерь.')
        if source.format == 'PNG':
            with open(path, 'rb') as file: # чтение двоичного файла
                header = file.read(25) # чтение первых 25 байтов
            if header[24] > 8: # например 16бит изобр не принимается
                raise ValueError('Нужны каналы с глубиной 8 бит.')
        if source.format == 'TIFF':
            tags = getattr(source, 'tag_v2', {}) # тег - поле с числовым номером и значением
            if tags.get(259, 1) not in (1, 5, 8, 32946, 32773, 34925, 50000): # 259 номер тега - способ сжатия, 1 - без сжатия
                raise ValueError('Нужен TIFF с известным сжатием без потерь.')
            bits = tags.get(258, (8,)) # глубина каналов по 8 rgb
            if isinstance(bits, int):
                bits = (bits,) # превращаем число в кортеж для перебора значений одинаковым способоом
            if any(value > 8 for value in bits):
                raise ValueError('Нужны каналы с глубиной 8 бит.')
        if source.mode == 'P' and 'transparency' not in source.info:
            source = source.convert('RGB') # преобразование в ргб из палитрового изобр.
        if source.mode != 'RGB' or 'transparency' in source.info:
            raise ValueError('Нужно цветное RGB без прозрачности.') # проверка ргб без прозрачности
        source.load()# загрузка данных пикселей
        image = []
        for y in range(source.height):
            row = []
            for x in range(source.width):
                pixel = source.getpixel((x, y)) # возвращаем значение пикселя по координамтам
                if not isinstance(pixel, tuple) or len(pixel) != 3: # так как красный, зеленый и синий
                    raise ValueError('Ожидаются три RGB-компоненты.')
                row.append((int(pixel[0]), int(pixel[1]), int(pixel[2])))
            image.append(row)
        return image


def to_pillow(image: RGBImage) -> Image.Image: # на выходе объект изображения pillow
    """Преобразование списка grb пикселей в объект для вывода."""
    target = Image.new('RGB', (len(image[0]), len(image))) #создание изображения по нужным размерам
    pixels = []
    for row in image:
        for pixel in row:
            pixels.append(pixel) # плоский список пикселей
    target.putdata(pixels) # заполнение изображения плоским списком пикселей
    return target


def save_rgb(image: RGBImage, path: str) -> None:
    """Сохранение картинки в файл."""
    formats = {'.png': 'PNG', '.bmp': 'BMP', '.tif': 'TIFF', '.tiff': 'TIFF'}
    suffix = Path(path).suffix.lower() # получение расширения из пути и к нижнему регистру
    if suffix not in formats:
        raise ValueError('Для сохранения выберите .png, .bmp, .tif или .tiff.')
    target = to_pillow(image)
    if formats[suffix] == 'TIFF':
        target.save(path, format='TIFF', compression='raw') # сохранение тиф без сжатия
    else:
        target.save(path, format=formats[suffix])
