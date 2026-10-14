"""Загрузка, сохранение и отображение через Pillow."""

from pathlib import Path

from PIL import Image

from statistics_ops import RGBImage


def load_rgb(path: str) -> RGBImage:
    """Загрузить 8-битное RGB-изображение PNG/BMP/TIFF без потерь."""
    with Image.open(path) as source:
        if source.format not in ('PNG', 'BMP', 'TIFF'):
            raise ValueError('Нужен PNG, BMP или TIFF без сжатия с потерями.')
        if source.format == 'PNG':
            with open(path, 'rb') as file:
                header = file.read(25)
            if header[24] > 8:
                raise ValueError('Нужны каналы с глубиной 8 бит.')
        if source.format == 'TIFF':
            tags = getattr(source, 'tag_v2', {})
            if tags.get(259, 1) not in (1, 5, 8, 32946, 32773, 34925, 50000):
                raise ValueError('Нужен TIFF с известным сжатием без потерь.')
            bits = tags.get(258, (8,))
            if isinstance(bits, int):
                bits = (bits,)
            if any(value > 8 for value in bits):
                raise ValueError('Нужны каналы с глубиной 8 бит.')
        if source.mode == 'P' and 'transparency' not in source.info:
            source = source.convert('RGB')
        if source.mode != 'RGB' or 'transparency' in source.info:
            raise ValueError('Нужно цветное RGB без прозрачности.')
        source.load()
        image = []
        for y in range(source.height):
            row = []
            for x in range(source.width):
                pixel = source.getpixel((x, y))
                if not isinstance(pixel, tuple) or len(pixel) != 3:
                    raise ValueError('Ожидаются три RGB-компоненты.')
                row.append((int(pixel[0]), int(pixel[1]), int(pixel[2])))
            image.append(row)
        return image


def to_pillow(image: RGBImage) -> Image.Image:
    """Передать уже рассчитанные RGB-пиксели библиотеке для вывода."""
    target = Image.new('RGB', (len(image[0]), len(image)))
    pixels = []
    for row in image:
        for pixel in row:
            pixels.append(pixel)
    target.putdata(pixels)
    return target


def save_rgb(image: RGBImage, path: str) -> None:
    """Сохранить текущий массив без экранных рамок и графиков."""
    formats = {'.png': 'PNG', '.bmp': 'BMP', '.tif': 'TIFF', '.tiff': 'TIFF'}
    suffix = Path(path).suffix.lower()
    if suffix not in formats:
        raise ValueError('Для сохранения выберите .png, .bmp, .tif или .tiff.')
    target = to_pillow(image)
    if formats[suffix] == 'TIFF':
        target.save(path, format='TIFF', compression='raw')
    else:
        target.save(path, format=formats[suffix])
