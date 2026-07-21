import math
from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtGui import QPen, QBrush, QColor
from PyQt6.QtCore import Qt

class RoundDiskShape:
    """
    Изолированный CAM-субмодуль для Круглого диска фабрики 'Бани Бабочки'.
    Отвечает за чистую тригонометрию хорд и отрисовку внешнего круглого контура.
    """
    def __init__(self, diameter: float):
        self.diameter = diameter
        self.radius = diameter / 2.0
        self.lamel_w = 135.0  # Стандартная ширина доски

    def calculate_lamels(self) -> list:
        """Расчет длин ламелей круглого щита от центра с напуском наружу по Пифагору"""
        lamels_geometry = []
        
        # Набираем стыки досок вправо от центра диска X=0
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
        
        # Нарезаем щит на ламели по пиковым хордам окружности
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
                    
                y_peak = math.sqrt(self.radius**2 - x_peak**2)
                full_length = y_peak * 2.0
                
                if full_length < 350.0:
                    full_length = 350.0
                    
                lamels_geometry.append({
                    "x_start": x1,
                    "x_end": x2,
                    "length": round(full_length, 1)
                })
                
        return lamels_geometry

    def draw_contour(self, scene: QGraphicsScene, contour_pen: QPen):
        """Отрисовка идеального круглого обвода на CAD-холсте"""
        scene.addEllipse(
            -self.radius, -self.radius, 
            self.radius * 2.0, self.radius * 2.0, 
            contour_pen, QBrush(Qt.BrushStyle.NoBrush)
        )
