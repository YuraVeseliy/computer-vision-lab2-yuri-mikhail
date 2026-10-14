"""Юрий: Часть 1: яркость, гистограммы и статистики окна.
Профиль строки также рассчитывается здесь.

Математика выполняется вручную.
Импортов библиотек в этом файле нет.
Изображение: image[y][x] == (R, G, B), начало координат слева сверху.
"""

Pixel = tuple[int, int, int]
RGBImage = list[list[Pixel]]
ScalarImage = list[list[float]]


def clamp(value: float) -> int:
    """Ограничить канал диапазоном 0..255.

    Округлить до ближайшего целого.
    """
    if value <= 0:
        return 0
    if value >= 255:
        return 255
    return int(value + 0.5)


def intensity(pixel: Pixel) -> float:
    """Яркость строго по заданию: (R + G + B) / 3, без округления."""
    red, green, blue = pixel
    return (red + green + blue) / 3.0


def intensity_matrix(image: RGBImage) -> ScalarImage:
    """Получить двумерный список точных значений яркости."""
    result = []
    for row in image:
        result_row = []
        for pixel in row:
            result_row.append(intensity(pixel))
        result.append(result_row)
    return result


def component_image(image: RGBImage, channel: int) -> RGBImage:
    """Показать яркость (-1) или канал (0=R, 1=G, 2=B) в полутонах."""
    if channel not in (-1, 0, 1, 2):
        raise ValueError('Неизвестный канал.')
    result = []
    for row in image:
        result_row = []
        for pixel in row:
            value = (clamp(intensity(pixel)) if channel == -1
                     else pixel[channel])
            result_row.append((value, value, value))
        result.append(result_row)
    return result


def histograms(image: RGBImage) -> list[list[int]]:
    """Абсолютные частоты I, R, G, B; яркость округлена до корзин 0..255."""
    result = [[0] * 256 for _ in range(4)]
    for row in image:
        for pixel in row:
            result[0][clamp(intensity(pixel))] += 1
            for channel in range(3):
                result[channel + 1][pixel[channel]] += 1
    return result


def statistics(
    values: list[float], method: str = 'two_pass'
) -> tuple[float, float, float]:
    """Вернуть среднее, дисперсию и СКО; делитель N, как в лекции.

    two_pass: D = sum((u - mean) ** 2) / N, два прохода.
    one_pass: D = sum(u ** 2) / N - mean ** 2, один проход.
    """
    count = len(values)
    if count == 0:
        raise ValueError('Нельзя вычислить статистику пустого списка.')
    if method not in ('two_pass', 'one_pass'):
        raise ValueError('Неизвестный способ расчёта дисперсии.')

    total = 0.0
    square_total = 0.0
    for value in values:
        total += value
        if method == 'one_pass':
            square_total += value * value
    mean = total / count

    if method == 'one_pass':
        variance = square_total / count - mean * mean
        # Погрешность float иногда даёт очень маленькое
        # отрицательное число.
        if variance < 0:
            variance = 0.0
    else:
        deviation_total = 0.0
        for value in values:
            deviation_total += (value - mean) ** 2
        variance = deviation_total / count
    return mean, variance, variance ** 0.5


def window_values(
    image: RGBImage, x: int, y: int, size: int = 11
) -> list[float]:
    """Яркости окна вокруг (x, y).

    У края окно пересекается с изображением.
    """
    height, width = len(image), len(image[0])
    if size < 1 or size % 2 == 0:
        raise ValueError('Размер окна должен быть положительным и нечётным.')
    if not 0 <= x < width or not 0 <= y < height:
        raise ValueError('Точка находится вне изображения.')
    radius = size // 2
    values = []
    for row_y in range(max(0, y - radius), min(height, y + radius + 1)):
        for column_x in range(max(0, x - radius), min(width, x + radius + 1)):
            values.append(intensity(image[row_y][column_x]))
    return values


def row_profile(image: RGBImage, row_y: int) -> list[float]:
    """Профиль яркости одной пиксельной строки.

    Индексы строк начинаются от нуля.
    """
    if not 0 <= row_y < len(image):
        raise ValueError('Номер строки вне изображения.')
    result = []
    for pixel in image[row_y]:
        result.append(intensity(pixel))
    return result


def demo_image() -> RGBImage:
    """Учебное RGB-изображение: однородность, полосы, цвет и шум."""
    image = []
    stripe_levels = [28] * 5 + [128] + [228] * 5
    for y in range(192):
        row = []
        for x in range(256):
            if y < 96 and x < 128:
                pixel = (128, 128, 128)
            elif y < 96:
                value = stripe_levels[(x - 128) % 11]
                pixel = (value, value, value)
            elif x < 128:
                pixel = (x * 2, (y - 96) * 2, 255 - x * 2)
            else:
                value = 128 + ((x * 37 + y * 61) % 161) - 80
                pixel = (value, value, value)
            row.append(pixel)
        image.append(row)
    return image
