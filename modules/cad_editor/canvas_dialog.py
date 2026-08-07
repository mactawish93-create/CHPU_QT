from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QDoubleSpinBox, QPushButton, QLabel
from PyQt6.QtCore import Qt

class CanvasSettingsDialog(QDialog):
    """
    Окно настроек чертежной среды. 
    Позволяет оператору менять шаг координатной сетки и чувствительность неонового прицела.
    """
    def __init__(self, current_grid, current_radius, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки холста редактора")
        self.setFixedSize(300, 180)
        
        self.setStyleSheet("""
            QDialog { background-color: #162421; }
            QLabel { color: #E0E0E6; font-family: 'Segoe UI'; font-size: 11px; }
            QDoubleSpinBox {
                background-color: #1A1A1E;
                color: #E0E0E6;
                border: 1px solid #32323D;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 11px;
                font-family: "Segoe UI";
                min-height: 20px;
            }
            QPushButton {
                background-color: #282830;
                color: #FFFFFF;
                border: 1px solid #353540;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #32323D; border-color: #00A8FF; }
        """)

        self.form_layout = QFormLayout()
        self.form_layout.setContentsMargins(15, 15, 15, 15)
        self.form_layout.setSpacing(10)

        # Поле ввода шага сетки в мм
        self.sb_grid = QDoubleSpinBox()
        self.sb_grid.setRange(1.0, 500.0)
        self.sb_grid.setValue(current_grid)
        self.form_layout.addRow("Шаг сетки (мм):", self.sb_grid)

        # Поле ввода радиуса захвата магнита
        self.sb_radius = QDoubleSpinBox()
        self.sb_radius.setRange(2.0, 100.0)
        self.sb_radius.setValue(current_radius)
        self.form_layout.addRow("Чувствительность магнита:", self.sb_radius)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(self.form_layout)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Применить")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        main_layout.addLayout(btn_layout)

    def get_values(self) -> tuple:
        """Возвращает кортеж (шаг_сетки, радиус_магнита)"""
        return self.sb_grid.value(), self.sb_radius.value()