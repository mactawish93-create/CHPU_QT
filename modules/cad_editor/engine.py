import math
from PyQt6.QtCore import QPointF, QLineF, QRectF
from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem, QGraphicsPathItem

class CadEngine:
    """
    Инженерное CAD-ядро графического редактора.
    Отвечает за дискретную математику: объектный снаппинг, шаговую сетку и полярные углы.
    """
    def __init__(self, grid_size=10.0, snap_radius=15.0):
        self.grid_size = grid_size
        self.snap_radius = snap_radius # Радиус притяжения к узлам геометрии (в пикселях сцены)

    def calculate_snap_point(self, current_pos: QPointF, scene_items: list, ctrl_pressed: bool) -> tuple:
        """
        Вычисляет точку привязки. 
        Если Ctrl ЗАЖАТ: сначала ищет концы/центры чужих фигур, если не нашел — магнитит к сетке 10мм.
        Если Ctrl ОТПУЩЕН: выдает абсолютно плавную свободную координату мыши.
        
        :return: (QPointF итоговая_точка, str тип_привязки_для_подсказки)
        """
        if not ctrl_pressed:
            return current_pos, "Свободное рисование (Зажмите Ctrl для привязки)"

        # 1. ОБЪЕКТНЫЙ СНАППИНГ (Концы, углы, центры уже нарисованных фигур)
        best_point = None
        min_dist = self.snap_radius
        snap_type = "Сетка 10мм"

        for item in scene_items:
            # Нам нужны только чистовые зафиксированные элементы, игнорируем временные фантомы и прицел
            if not item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
                continue

            points_to_check = [] # Список потенциальных узлов захвата для этой фигуры

            if isinstance(item, QGraphicsLineItem):
                line = item.line()
                p1, p2 = line.p1(), line.p2()
                points_to_check.append((p1, "Конец линии"))
                points_to_check.append((p2, "Конец линии"))
                mid_p = QPointF((p1.x() + p2.x()) / 2.0, (p1.y() + p2.y()) / 2.0)
                points_to_check.append((mid_p, "Центр линии"))

            elif isinstance(item, QGraphicsRectItem):
                rect = item.rect()
                points_to_check.append((rect.topLeft(), "Угол прямоугольника"))
                points_to_check.append((rect.topRight(), "Угол прямоугольника"))
                points_to_check.append((rect.bottomLeft(), "Угол прямоугольника"))
                points_to_check.append((rect.bottomRight(), "Угол прямоугольника"))
                points_to_check.append((rect.center(), "Центр прямоугольника"))

            elif isinstance(item, QGraphicsPathItem):
                # Для кругов, ромбов и многоугольников сканируем вершины их векторного пути Path
                path = item.path()
                for i in range(path.elementCount()):
                    pt = QPointF(path.elementAt(i).x, path.elementAt(i).y)
                    points_to_check.append((pt, "Узел контура фигуры"))
                points_to_check.append((item.boundingRect().center(), "Центр фигуры"))

            # Проверяем, какая из точек ближе всего к курсору мыши
            for pt, t_name in points_to_check:
                dist = math.hypot(current_pos.x() - pt.x(), current_pos.y() - pt.y())
                if dist < min_dist:
                    min_dist = dist
                    best_point = pt
                    snap_type = t_name

        if best_point is not None:
            return best_point, f"Захват: {snap_type}"

        # 2. ШАГОВАЯ СЕТКА 10 ММ (Если объектных узлов рядом не оказалось)
        gx = round(current_pos.x() / self.grid_size) * self.grid_size
        gy = round(current_pos.y() / self.grid_size) * self.grid_size
        return QPointF(gx, gy), "Привязка: Сетка 10мм"

    def apply_ortho_45(self, start_pt: QPointF, current_pt: QPointF, shift_pressed: bool) -> QPointF:
        """
        Если зажат Shift, принудительно фиксирует вектор линии кратно 45 градусам (0, 45, 90, 135...).
        """
        if not shift_pressed:
            return current_pt

        dx = current_pt.x() - start_pt.x()
        dy = current_pt.y() - start_pt.y()
        
        if dx == 0 and dy == 0:
            return current_pt

        # Переводим смещение в угол в радианах, затем в градусы
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)
        if angle_deg < 0:
            angle_deg += 360.0

        # Округляем угол до ближайшего шага в 45 градусов
        snap_angle = round(angle_deg / 45.0) * 45.0
        if snap_angle >= 360.0:
            snap_angle -= 360.0
        
        # Считаем чистую длину вектора (гипотенузу)
        length = math.hypot(dx, dy)
        
        # Пересчитываем конечную координату по тригонометрическим осям
        new_dx = length * math.cos(math.radians(snap_angle))
        new_dy = length * math.sin(math.radians(snap_angle))
        
        return QPointF(start_pt.x() + new_dx, start_pt.y() + new_dy)
