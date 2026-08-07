from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QDoubleSpinBox, QSpinBox, QPushButton, QLabel
from PyQt6.QtCore import Qt

class CncSettingsDialog(QDialog):
    """
    Технологическое окно глобальных настроек станка и параметров инструмента по умолчанию.
    Обеспечивает оператора возможностью на лету менять подачи, обороты и шаг прохода.
    """
    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки параметров ЧПУ")
        self.setFixedSize(320, 320)
        
        # Накатываем фирменный стиль Dark Mode
        self.setStyleSheet("""
            QDialog { background-color: #162421; }
            QLabel { color: #E0E0E6; font-family: 'Segoe UI'; font-size: 11px; }
            QDoubleSpinBox, QSpinBox {
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
                padding: 6px 15px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #32323D; border-color: #00A8FF; }
        """)

        # Создаем копию настроек, чтобы не менять оригинал до нажатия кнопки "Сохранить"
        self.settings = current_settings.copy()

        self.form_layout = QFormLayout()
        self.form_layout.setContentsMargins(15, 15, 15, 15)
        self.form_layout.setSpacing(10)

        self._build_ui()

    def _build_ui(self):
        # 1. Диаметр фрезы (мм)
        self.sb_tool_d = QDoubleSpinBox()
        self.sb_tool_d.setRange(0.1, 100.0)
        self.sb_tool_d.setDecimals(1)
        self.sb_tool_d.setValue(self.settings.get("tool_diameter", 12.0))
        self.form_layout.addRow("Диаметр фрезы (мм):", self.sb_tool_d)

        # 2. Обороты шпинделя (об/мин)
        self.sb_spindle = QSpinBox()
        self.sb_spindle.setRange(500, 40000)
        self.sb_spindle.setSingleStep(500)
        self.sb_spindle.setValue(self.settings.get("spindle_speed", 18000))
        self.form_layout.addRow("Обороты шпинделя (об/мин):", self.sb_spindle)

        # 3. Рабочая подача XY (мм/мин)
        self.sb_feed_xy = QDoubleSpinBox()
        self.sb_feed_xy.setRange(10.0, 15000.0)
        self.sb_feed_xy.setSingleStep(100.0)
        self.sb_feed_xy.setDecimals(0)
        self.sb_feed_xy.setValue(self.settings.get("feed_rate_xy", 3000.0))
        self.form_layout.addRow("Подача плоскости XY (мм/мин):", self.sb_feed_xy)

        # 4. Подача врезания Z (мм/мин)
        self.sb_feed_z = QDoubleSpinBox()
        self.sb_feed_z.setRange(10.0, 5000.0)
        self.sb_feed_z.setSingleStep(50.0)
        self.sb_feed_z.setDecimals(0)
        self.sb_feed_z.setValue(self.settings.get("feed_rate_z", 800.0))
        self.form_layout.addRow("Подача врезания Z (мм/мин):", self.sb_feed_z)

        # 5. Безопасная высота Z (мм)
        self.sb_safe_z = QDoubleSpinBox()
        self.sb_safe_z.setRange(1.0, 500.0)
        self.sb_safe_z.setValue(self.settings.get("safe_z", 20.0))
        self.form_layout.addRow("Безопасная высота Z (мм):", self.sb_safe_z)

        # 6. Глубина за один проход Step Down (мм)
        self.sb_step = QDoubleSpinBox()
        self.sb_step.setRange(0.1, 100.0)
        self.sb_step.setValue(self.settings.get("step_down", 10.0))
        self.form_layout.addRow("Шаг за один проход (мм):", self.sb_step)

        # Кнопки Сохранить / Отмена
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(self.form_layout)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Сохранить параметры")
        btn_save.clicked.connect(self._accept_changes)
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        main_layout.addLayout(btn_layout)

    def _accept_changes(self):
        """Собирает новые данные из полей ввода обратно в словарь"""
        self.settings["tool_diameter"] = self.sb_tool_d.value()
        self.settings["spindle_speed"] = self.sb_spindle.value()
        self.settings["feed_rate_xy"] = self.sb_feed_xy.value()
        self.settings["feed_rate_z"] = self.sb_feed_z.value()
        self.settings["safe_z"] = self.sb_safe_z.value()
        self.settings["step_down"] = self.sb_step.value()
        self.accept()

    def get_settings(self) -> dict:
        """Возвращает обновленный словарь технологических настроек"""
        return self.settings