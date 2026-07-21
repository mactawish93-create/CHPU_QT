import math
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPathItem
from PyQt6.QtGui import QPen, QBrush, QPainterPath
from PyQt6.QtCore import Qt, QRectF

class QuadroDiskShape:
    """
    Изолированный CAM-субмодуль для Квадро-диска ("бочки") компании "Бани Бабочки".
    Масштабирует пропорции плоских полок и радиусов углов на основе оригинального G-кода.
    """
    def __init__(self, diameter: float):
        self.diameter = diameter
        self.radius = diameter / 2.0
        self.lamel_w = 135.0  # Стандартная ширина доски
        
        # Динамические коэффициенты масштабирования формы "бочки" по вашему заводскому G-коду
        self.scale_ratio = diameter / 2000.0
        self.x_flat = 145.0 * self.scale_ratio     # Половина длины плоской крыши/дна
        self.y_flat = 142.0 * self.scale_ratio     # Половина высоты плоских боковин ("щек")
        self.r_corner = 855.0 * self.scale_ratio   # Малый радиус скругления угла

    def calculate_lamels(self) -> list:
        """Расчет длин ламелей для Квадро-щита с учетом плоской крыши и спада хорд по углам"""
        lamels_geometry = []
        
        # Набираем сетку стыков ламелей вправо и влево от центра
        x_steps = [0.0]
        current_x = self.lamel_w
        while current_x < self.radius + self.lamel_w:
            x_steps.append(current_x)
            current_x += self.lamel_w
            
        all_x_breaks = []
        half_w = self.lamel_w / 2.0
        all_x_breaks.extend([-half_w, half_w])
        for step in x_steps[1:]:
            all_x_breaks.extend([step - half_w, step + half_w, -(step - half_w), -(step + half_w)])
        all_x_breaks = sorted(list(set(all_x_breaks)))
        
        # Цикл прохода по доскам щита
        for i in range(len(all_x_breaks) - 1):
            x1 = all_x_breaks[i]
            x2 = all_x_breaks[i+1]
            
            if x1 < self.radius and x2 > -self.radius:
                if x1 <= 0 and x2 >= 0:
                    x_peak = 0.0
                else:
                    x_peak = x1 if abs(x1) < abs(x2) else x2
                
                if abs(x_peak) > self.radius:
                    x_peak = self.radius * 0.99
                    
                abs_xp = abs(x_peak)
                
                if abs_xp <= self.x_flat:
                    # Внутри плоской полки доски идут во всю высоту диаметра
                    full_length = self.diameter
                else:
                    # В зоне скругления угла спад идет по смещенной окружности угла
                    dx = abs_xp - self.x_flat
                    if dx > self.r_corner: 
                        dx = self.r_corner * 0.99
                    try:
                        y_peak = math.sqrt(self.r_corner**2 - dx**2) + self.y_flat
                        full_length = y_peak * 2.0
                    except:
                        full_length = 350.0

                if full_length < 350.0:
                    full_length = 350.0
                    
                lamels_geometry.append({
                    "x_start": x1,
                    "x_end": x2,
                    "length": round(full_length, 1)
                })
                
        return lamels_geometry

    def draw_contour(self, scene: QGraphicsScene, contour_pen: QPen):
        """Пошаговая отрисовка контура Квадро-бочки через тригонометрические точки"""
        quadro_path = QPainterPath()
        
        # 1. Стартуем на правом краю верхней плоской крыши
        quadro_path.moveTo(self.x_flat, self.radius)
        # Линия влево по крыше
        quadro_path.lineTo(-self.x_flat, self.radius)
        
        # 2. Верхний левый угол (дуга от 90 до 180 градусов)
        for angle in range(90, 181):
            rad = math.radians(angle)
            cx = -self.x_flat + self.r_corner * math.cos(rad)
            cy = self.y_flat + self.r_corner * math.sin(rad)
            quadro_path.lineTo(cx, cy)
            
        # Линия вниз по левой плоской "щеке" бани
        quadro_path.lineTo(-self.radius, -self.y_flat)
        
        # 3. Нижний левый угол (дуга от 180 до 270 градусов)
        for angle in range(180, 271):
            rad = math.radians(angle)
            cx = -self.x_flat + self.r_corner * math.cos(rad)
            cy = -self.y_flat + self.r_corner * math.sin(rad)
            quadro_path.lineTo(cx, cy)
            
        # Линия вправо по плоскому дну бани
        quadro_path.lineTo(self.x_flat, -self.radius)
        
        # 4. Нижний правый угол (дуга от 270 до 360 градусов)
        for angle in range(270, 361):
            rad = math.radians(angle)
            cx = self.x_flat + self.r_corner * math.cos(rad)
            cy = -self.y_flat + self.r_corner * math.sin(rad)
            quadro_path.lineTo(cx, cy)
            
        # Линия вверх по правой плоской "щеке" бани
        quadro_path.lineTo(self.radius, self.y_flat)
        
        # 5. Верхний правый угол (дуга от 0 до 90 градусов)
        for angle in range(0, 91):
            rad = math.radians(angle)
            cx = self.x_flat + self.r_corner * math.cos(rad)
            cy = self.y_flat + self.r_corner * math.sin(rad)
            quadro_path.lineTo(cx, cy)
            
        quadro_path.closeSubpath()
        
        # Выводим Квадро-обвод на сцену
        path_item = QGraphicsPathItem(quadro_path)
        path_item.setPen(contour_pen)
        path_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        scene.addItem(path_item)
