from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

class CadStatusbar(QFrame):
    """
    Нижняя панель состояния графического редактора.
    Выводит текущие ЧПУ-координаты X/Y, живые подсказки привязок и масштаб холста.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame { background-color: #1A1A1E; border-top: 1px solid #25252D; min-height: 22px; max-height: 22px; }
            QLabel { color: #B0B0B8; font-size: 10px; font-family: 'Segoe UI', 'Arial'; }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        
        # Три зоны вывода параметров
        self.lbl_coords = QLabel("X: 0.00 mm  |  Y: 0.00 mm  |  Сетка: 10 мм")
        self.lbl_hint = QLabel("Готов к работе. Инструмент: УКАЗАТЕЛЬ")
        self.lbl_zoom = QLabel("Масштаб: 100%")
        
        layout.addWidget(self.lbl_coords)
        layout.addSpacing(30)
        layout.addWidget(self.lbl_hint)
        layout.addStretch()
        layout.addWidget(self.lbl_zoom)

    def update_coordinates(self, x: float, y: float, grid_size: float = 10.0):
        """🔥 ИСПРАВЛЕНО: Выводит живые ЧПУ-координаты мыши и актуальный шаг сетки"""
        self.lbl_coords.setText(f"X: {x:.2f} mm  |  Y: {y:.2f} mm  |  Сетка: {grid_size:.0f} мм")

    def update_zoom(self, zoom_factor: float):
        """Выводит текущий масштаб в процентах"""
        self.lbl_zoom.setText(f"Масштаб: {int(zoom_factor * 100)}%")

    def update_hint(self, text: str):
        """Выводит оперативную подсказку или тип объектного снаппинга"""
        self.lbl_hint.setText(text)
