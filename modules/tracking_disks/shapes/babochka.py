from PyQt6.QtWidgets import QGraphicsScene, QGraphicsTextItem
from PyQt6.QtGui import QPen, QBrush, QColor, QFont
from PyQt6.QtCore import Qt

class BabochkaDiskShape:
    """Заглушка-каркас для будущего модуля БаБочка диск"""
    def __init__(self, diameter: float):
        self.diameter = diameter
        self.radius = diameter / 2.0

    def calculate_lamels(self) -> list:
        """Пока возвращаем пустой список до получения формул формы"""
        return []

    def draw_contour(self, scene: QGraphicsScene, contour_pen: QPen):
        """Выводим наглядную оранжевую текстовую плашку"""
        text_stub = QGraphicsTextItem("[ Форма БаБочка диск — Заглушка контура ]")
        font = QFont("Segoe UI", 12)
        font.setItalic(True)
        text_stub.setFont(font)
        text_stub.setDefaultTextColor(QColor("#707078"))
        
        # Контр-трансформация текста, чтобы буквы не были вверх ногами
        import PyQt6.QtGui as QtGui
        t = QtGui.QTransform()
        t.scale(1, -1)
        text_stub.setTransform(t)
        
        scene.addItem(text_stub)
        text_stub.setPos(-text_stub.boundingRect().width() / 2.0, text_stub.boundingRect().height() / 2.0)
