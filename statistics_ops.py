Pixel = tuple[int, int, int]
RGBImage = list[list[Pixel]]
ScalarImage = list[list[float]]


def clamp(value: float) -> int:
    """Ограничить канал диапазоном 0..255
    Округлить до ближайшего целого.
    """
    if value <= 0:
        return 0
    if value >= 255:
        return 255
    return int(value + 0.5)


def intensity(pixel: Pixel) -> float:
    """Яркость: (R + G + B) / 3."""
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
    """Абсолютные частоты I, R, G, B; яркость 0..255."""
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
    """Вернуть среднее, дисперсию и СКО; делитель N

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
        # Погрешность float иногда даёт отрицательное число,
        # очень близкое к нулю.
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
    """Простой цветной градиент: R=x, G=y, B=64."""
    image = []
    for y in range(192):
        row = []
        for x in range(256):
            row.append((x, y, 64))
        image.append(row)
    return image


def blur_demo_image() -> RGBImage:
    """Резкие границы и светлая точка на чёрном фоне."""
    image = []
    for y in range(192):
        row = []
        for x in range(256):
            value = 255 if x >= 128 else 0
            if 32 <= x < 48 and 32 <= y < 48:
                value = 255
            row.append((value, value, value))
        image.append(row)
    image[96][64] = (255, 255, 255)
    return image
