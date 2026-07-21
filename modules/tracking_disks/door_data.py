class DoorDataProcessor:
    """
    Изолированный ЧПУ-процессор дверных проемов фабрики 'Бани Бабочки'.
    Хранит точные пошаговые векторы и высотные лимиты на основе заводских УП.
    """
    def __init__(self, diameter: float, door_offset: float):
        self.diameter = diameter
        self.door_offset = door_offset
        
        # Автоматически вычисляем высотные лимиты Z-крыши и порога проема по G-коду
        if diameter == 2300.0:
            self.y_door_top = 782.0
            self.y_door_bottom = -990.0
        elif diameter == 2000.0 and door_offset == 100.0:
            self.y_door_top = 836.0
            self.y_door_bottom = -836.0
        else:
            self.y_door_top = 886.0
            self.y_door_bottom = -886.0

    def get_door_polygons(self) -> tuple:
        """Возвращает точные замкнутые ломаные линии наружного контура и полки четверти"""
        door_poly_outer = []
        door_poly_inner = []

        if self.diameter == 2300.0:
            # 1. Проём для 2300 круг и квадро (все смещения опущены вниз)
            door_poly_outer = [
                (0.0, 782.0), (376.0 - self.door_offset, 782.0), (376.0 - self.door_offset, 762.0),
                (354.0 - self.door_offset, 762.0), (354.0 - self.door_offset, -970.0), (376.0 - self.door_offset, -970.0),
                (376.0 - self.door_offset, -990.0), (-376.0 - self.door_offset, -990.0), (-376.0 - self.door_offset, -970.0),
                (-354.0 - self.door_offset, -970.0), (-354.0 - self.door_offset, 762.0), (-376.0 - self.door_offset, 762.0),
                (-376.0 - self.door_offset, 782.0), (0.0, 782.0)
            ]
            door_poly_inner = [
                (0.0, 762.0), (354.0 - self.door_offset, 762.0), (354.0 - self.door_offset, -970.0),
                (-354.0 - self.door_offset, -970.0), (-354.0 - self.door_offset, 762.0), (0.0, 762.0)
            ]
        elif self.diameter == 2000.0 and self.door_offset == 100.0:
            # 2. Специальное сжатие по высоте для 2000 со смещением 100
            door_poly_outer = [
                (0.0, 836.0), (276.0, 836.0), (276.0, 816.0),
                (254.0, 816.0), (254.0, -816.0), (276.0, -816.0),
                (276.0, -836.0), (-476.0, -836.0), (-476.0, -816.0),
                (-454.0, -816.0), (-454.0, 816.0), (-476.0, 816.0),
                (-476.0, 836.0), (0.0, 836.0)
            ]
            door_poly_inner = [
                (0.0, 816.0), (254.0, 816.0), (254.0, -816.0),
                (-454.0, -816.0), (-454.0, 816.0), (0.0, 816.0)
            ]
        elif self.diameter == 2150.0 and self.door_offset == 100.0:
            # 3. Проём для 2150 со смещением 100 (Старт в X-100 по УП)
            door_poly_outer = [
                (-100.0, 886.0), (276.0, 886.0), (276.0, 866.0),
                (254.0, 866.0), (254.0, -866.0), (276.0, -866.0),
                (276.0, -886.0), (-476.0, -886.0), (-476.0, -866.0),
                (-454.0, -866.0), (-454.0, 866.0), (-476.0, 866.0),
                (-476.0, 886.0), (-100.0, 886.0)
            ]
            door_poly_inner = [
                (-100.0, 866.0), (254.0, 866.0), (254.0, -866.0),
                (-454.0, -866.0), (-454.0, 866.0), (-100.0, 866.0)
            ]
        else:
            # 4. Базовый стандарт (2150 смещение 0, 150 и 2000 без смещения)
            door_poly_outer = [
                (0.0, 886.0), (376.0 - self.door_offset, 886.0), (376.0 - self.door_offset, 866.0),
                (354.0 - self.door_offset, 866.0), (354.0 - self.door_offset, -866.0), (376.0 - self.door_offset, -866.0),
                (376.0 - self.door_offset, -886.0), (-376.0 - self.door_offset, -886.0), (-376.0 - self.door_offset, -866.0),
                (-354.0 - self.door_offset, -866.0), (-354.0 - self.door_offset, 866.0), (-376.0 - self.door_offset, 866.0),
                (-376.0 - self.door_offset, 886.0), (0.0, 886.0)
            ]
            door_poly_inner = [
                (0.0, 866.0), (354.0 - self.door_offset, 866.0), (354.0 - self.door_offset, -866.0),
                (-354.0 - self.door_offset, -866.0), (-354.0 - self.door_offset, 866.0), (0.0, 866.0)
            ]

        return door_poly_outer, door_poly_inner

    def check_and_calculate_lamel_cut(self, x1: float, x2: float, y_peak: float) -> tuple:
        """Рассчитывает мятно-зеленые длины обрезков доски над и под проемом"""
        # Наружные боковые границы двери для проверки пересечения брусков
        if self.diameter == 2000.0 and self.door_offset == 100.0:
            x_l, x_r = -476.0, 276.0
        else:
            x_l, x_r = -376.0 - self.door_offset, 376.0 - self.door_offset

        is_cut = False
        top_len = 0.0
        bottom_len = 0.0

        # Если тело доски по оси X пересекается с телом двери
        if max(x1, x_l) < min(x2, x_r):
            is_cut = True
            # Верхний кусок (от макушки ламели до крыши двери)
            if y_peak > self.y_door_top:
                top_len = round(y_peak - self.y_door_top, 1)
            # Нижний кусок (от порога двери до нижней макушки ламели -y_peak)
            if -y_peak < self.y_door_bottom:
                bottom_len = round(self.y_door_bottom - (-y_peak), 1)

        return is_cut, top_len, bottom_len
