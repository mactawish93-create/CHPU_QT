import os
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPolygonItem, QGraphicsLineItem, QGraphicsTextItem
from PyQt6.QtGui import QPen, QColor, QPolygonF, QFont, QTransform
from PyQt6.QtCore import QPointF, Qt

class BabochkaDiskShape:
    def __init__(self, diameter: float, h_kon: float = 2200.0, 
                 cut_vert_paz: bool = True, room_y: float = 1150.0, paz_z: float = -20.0):
        self.diameter = diameter  # Общая ширина (Y)
        self.h_kon = h_kon        # Высота в коньке (X)
        
        # Параметры вертикального паза перегородки
        self.cut_vert_paz = cut_vert_paz
        self.room_y = room_y
        self.paz_z = paz_z
        
        self.raw_points = []
        self._load_template()

    def _load_template(self):
        """Загрузка эталонных точек купола"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, "templates", "babochka_template.txt")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        parts = line.strip().split(",")
                        self.raw_points.append((float(parts[0]), float(parts[1])))

    def get_cnc_contour_points(self) -> list:
        """Масштабирование базового шаблона бани 3870х2150 на лету"""
        if not self.raw_points:
            return []
        k_x = self.h_kon / 2150.0
        k_y = self.diameter / 3870.0
        return [(rx * k_x, ry * k_y) for rx, ry in self.raw_points]

    def _get_height_at_y(self, target_y: float) -> float:
        """
        Математический поиск высоты купола в любой точке Y (для расчета вылета паза).
        Использует линейную интерполяцию между ближайшими точками шаблона.
        """
        pts = self.get_cnc_contour_points()
        if not pts:
            return 0.0
            
        # Сортируем точки по возрастанию координаты Y (ширины)
        pts = sorted(pts, key=lambda p: p[1])
        
        # Если координата паза вне контура
        if target_y <= pts[0][1]: return pts[0][0]
        if target_y >= pts[-1][1]: return pts[-1][0]
        
        # Ищем отрезок, в который попадает координата паза room_y
        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i+1]
            if p1[1] <= target_y <= p2[1]:
                # Линейная интерполяция высоты X
                if abs(p2[1] - p1[1]) < 0.001:
                    return p1[0]
                t = (target_y - p1[1]) / (p2[1] - p1[1])
                return p1[0] + t * (p2[0] - p1[0])
        return 0.0

    def draw_contour(self, scene: QGraphicsScene, contour_pen: QPen):
        pts = self.get_cnc_contour_points()
        if not pts:
            return

        # Фирменные цвета
        blue_pen = QPen(QColor("#0055ff"), 2)       # Купол
        dim_pen = QPen(QColor("#FF9F43"), 1.5)      # Выносные линии размеров
        arrow_pen = QPen(QColor("#ffffff"), 1.5)    # Белые стрелки
        brown_pen = QPen(QColor("#d35400"), 6)      # Вертикальный паз
        
        # Крупные цеховые шрифты
        font_ext = QFont("Segoe UI", 42, QFont.Weight.Bold)
        font_int = QFont("Segoe UI", 32, QFont.Weight.Bold)
        font_small = QFont("Segoe UI", 24, QFont.Weight.Bold)
        
        def add_text(text: str, x: float, y: float, font_obj: QFont, color="#ffffff"):
            t_item = QGraphicsTextItem(text)
            t_item.setFont(font_obj)
            t_item.setDefaultTextColor(QColor(color))
            t_item.setTransformOriginPoint(t_item.boundingRect().center())
            t_item.setTransform(QTransform().scale(1, -1))
            t_item.setPos(x - t_item.boundingRect().width()/2, y + t_item.boundingRect().height()/2)
            scene.addItem(t_item)

        def draw_arrow_line(x1, y1, x2, y2):
            scene.addLine(x1, y1, x2, y2, arrow_pen)
            if abs(y1 - y2) < 0.001:  # Горизонтальная стрелка
                scene.addLine(x1, y1-15, x1, y1+15, dim_pen)
                scene.addLine(x2, y2-15, x2, y2+15, dim_pen)
            elif abs(x1 - x2) < 0.001:  # Вертикальная стрелка
                scene.addLine(x1-15, y1, x1+15, y1, dim_pen)
                scene.addLine(x2-15, y2, x2+15, y2, dim_pen)

        half_d = self.diameter / 2.0

        # 1. ОТРИСОВКА СИНЕГО КУПОЛА (Центрирован по оси X=0 холста)
        polygon = QPolygonF()
        for cnc_x, cnc_y in pts:
            polygon.append(QPointF(cnc_y - half_d, cnc_x))
        poly_item = QGraphicsPolygonItem(polygon)
        poly_item.setPen(blue_pen)
        scene.addItem(poly_item)

        # Линия пола (горизонтальная база)
        scene.addLine(-half_d, 0.0, half_d, 0.0, blue_pen)

        # 2. РАЗМЕР: ОБЩАЯ ШИРИНА ДИСКА (Y)
        y_dim_bottom = -120.0
        scene.addLine(-half_d, 0.0, -half_d, y_dim_bottom - 20, dim_pen)
        scene.addLine(half_d, 0.0, half_d, y_dim_bottom - 20, dim_pen)
        draw_arrow_line(-half_d, y_dim_bottom, half_d, y_dim_bottom)
        add_text(f"{int(self.diameter)}", 0.0, y_dim_bottom - 45, font_ext, color="#E0E0E6")

        # 3. РАЗМЕР: ВЫСОТА В КОНЬКЕ (X)
        x_dim_left = -half_d - 150.0
        scene.addLine(0.0, self.h_kon, x_dim_left - 20, self.h_kon, dim_pen)
        scene.addLine(-half_d, 0.0, x_dim_left - 20, 0.0, dim_pen)
        draw_arrow_line(x_dim_left, 0.0, x_dim_left, self.h_kon)
        add_text(f"{int(self.h_kon)}", x_dim_left - 70, self.h_kon / 2, font_ext, color="#FF9F43")

        # 4. ВЕРТИКАЛЬНЫЙ ПАЗ И ПОМЕЩЕНИЯ
        if self.cut_vert_paz:
            height_at_paz = self._get_height_at_y(self.room_y)
            
            # Смещаем координату паза относительно отцентрированного нуля холста
            paz_x_canvas = self.room_y - half_d
            
            # Чертим вертикальный паз
            scene.addLine(paz_x_canvas, 0.0, paz_x_canvas, height_at_paz, brown_pen)
            
            # Вылет фрезы
            add_text(f"Вылет: {height_at_paz:.1f} мм", paz_x_canvas, height_at_paz + 50, font_small, color="#2ECC71")
            
            # Гребенка комнат
            y_paz_dim = 80.0
            scene.addLine(paz_x_canvas, 0.0, paz_x_canvas, y_paz_dim + 30, dim_pen)
            
            # Левая комната
            draw_arrow_line(-half_d, y_paz_dim, paz_x_canvas, y_paz_dim)
            add_text(f"{int(self.room_y)}", (-half_d + paz_x_canvas) / 2.0, y_paz_dim + 40, font_int, color="#2ECC71")
            
            # Правая комната
            rest_y = self.diameter - self.room_y
            if rest_y > 50:
                draw_arrow_line(paz_x_canvas, y_paz_dim, half_d, y_paz_dim)
                add_text(f"{int(rest_y)}", (paz_x_canvas + half_d) / 2.0, y_paz_dim + 40, font_int, color="#2ECC71")

        # 5. СЕТКА СЦЕНЫ ДЛЯ ЖЕСТКОЙ ЦЕНТРОВКИ КАМЕРЫ
        scene.setSceneRect(-half_d - 350.0, -300.0, self.diameter + 700.0, self.h_kon + 500.0)

    def calculate_lamels(self) -> list:
        """
        Генерирует горизонтальные ламели шириной 135 мм для Бабочки.
        Они нарастают снизу вверх по высоте конька (ось X).
        """
        lamel_w = 135.0
        lamels_list = []
        
        # Считаем, сколько досок по 135 мм нужно уложить по высоте конька h_kon
        count = int(self.h_kon / lamel_w)
        if self.h_kon % lamel_w > 0:
            count += 1

        for i in range(count):
            x_start = i * lamel_w
            x_end = (i + 1) * lamel_w
            if x_end > self.h_kon:
                x_end = self.h_kon

            # Для Бабочки длина доски — это ее полная ширина по Y (diameter)
            lamels_list.append({
                "x_start": x_start,
                "x_end": x_end,
                "length": self.diameter,
                "is_cut": False
            })
            
        return lamels_list

