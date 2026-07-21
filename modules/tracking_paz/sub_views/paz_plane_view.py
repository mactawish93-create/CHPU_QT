from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QDoubleSpinBox, QComboBox, QPushButton
from PyQt6.QtCore import Qt

class PazPlaneView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Сверхплотный главный слой формы
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # =========================================================================
        # 📦 КАРТОЧКА: ПАРАМЕТРЫ КАЛИБРОВКИ СТОЛА
        # =========================================================================
        group_plane = QGroupBox("Параметры выравнивания")
        plane_layout = QVBoxLayout(group_plane)
        plane_layout.setSpacing(4)
        plane_layout.setContentsMargins(8, 12, 8, 8)
        
        def create_plane_row(container_layout, label_text, is_percent=False):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            lbl = QLabel(label_text)
            spin = QDoubleSpinBox()
            spin.setRange(-1000.0, 6000.0) if not is_percent else spin.setRange(0.0, 100.0)
            spin.setValue(0.0)
            spin.setSuffix(" %" if is_percent else " мм")
            spin.setFixedWidth(85)
            row_layout.addWidget(lbl)
            row_layout.addStretch()
            row_layout.addWidget(spin)
            container_layout.addLayout(row_layout)
            return spin
            
        strategy_lay = QHBoxLayout()
        strategy_lay.addWidget(QLabel("Стратегия реза:"))
        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems(["Зигзаг по Y", "Зигзаг по X"])
        self.combo_strategy.setFixedWidth(110)
        strategy_lay.addStretch()
        strategy_lay.addWidget(self.combo_strategy)
        plane_layout.addLayout(strategy_lay)
        
        plane_layout.addSpacing(4)
        
        self.spin_length_y = create_plane_row(plane_layout, "Длина зоны Y:")
        self.spin_length_x = create_plane_row(plane_layout, "Длина зоны X:")
        self.spin_mill_dia = create_plane_row(plane_layout, "Диаметр фрезы:")
        self.spin_stepover = create_plane_row(plane_layout, "Перекрытие фрезы:", is_percent=True)
        self.spin_depth_z = create_plane_row(plane_layout, "Съем по оси Z:")
        
        layout.addWidget(group_plane)

        # =========================================================================
        # 💾 БЛОК: КНОПКА ЭКСПОРТА УП КАЛИБРОВКИ СТОЛА (.TAP)
        # =========================================================================
        layout.addSpacing(5)
        self.btn_generate_gcode = QPushButton("💾 Сгенерировать G-код (.tap)")
        self.btn_generate_gcode.setFixedHeight(26)
        self.btn_generate_gcode.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_generate_gcode.setStyleSheet("""
            QPushButton { 
                background-color: #282830; color: #00A8FF; border: 1px solid #00A8FF; border-radius: 4px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: #00A8FF; color: #FFFFFF; }
        """)
        layout.addWidget(self.btn_generate_gcode)
