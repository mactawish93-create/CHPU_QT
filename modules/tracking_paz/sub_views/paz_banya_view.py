from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QLabel, QDoubleSpinBox, QComboBox, QCheckBox, QPushButton)
from PyQt6.QtCore import Qt

class PazBanyaView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Сверхплотный главный слой формы
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # Универсальная функция для создания плотной строки "Чекбокс + Заблокированный SpinBox"
        def create_protected_row(container_layout, label_text, default_val, min_v, max_v):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            chbox = QCheckBox()
            lbl = QLabel(label_text)
            spin = QDoubleSpinBox()
            spin.setRange(min_v, max_v)
            spin.setValue(default_val)
            spin.setSuffix(" мм")
            spin.setFixedWidth(85)
            spin.setEnabled(False)
            chbox.toggled.connect(spin.setEnabled)
            row_layout.addWidget(chbox)
            row_layout.addWidget(lbl)
            row_layout.addStretch()
            row_layout.addWidget(spin)
            container_layout.addLayout(row_layout)
            return chbox, spin

        # Универсальная функция для обычной плотной строки (Без чекбокса)
        def create_standard_row(container_layout, label_text, default_val, min_v, max_v, suffix=" мм"):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(4)
            lbl = QLabel(label_text)
            spin = QDoubleSpinBox()
            spin.setRange(min_v, max_v)
            spin.setValue(default_val)
            spin.setSuffix(suffix)
            spin.setFixedWidth(85)
            # Если это обороты или подачи — убираем сотые доли (делаем целыми числами)
            if suffix in [" об/м", " мм/м"]:
                spin.setDecimals(0)
            row_layout.addWidget(lbl)
            row_layout.addStretch()
            row_layout.addWidget(spin)
            container_layout.addLayout(row_layout)
            return spin

        # =========================================================================
        # 📦 БЛОК 1: БАЗОВЫЕ НАСТРОЙКИ (ВШИТЫ ВАШИ ЧПУ-ПОДАЧИ И ОБОРОТЫ)
        # =========================================================================
        base_group = QGroupBox("Базовые настройки")
        base_layout = QVBoxLayout(base_group)
        base_layout.setSpacing(4)
        base_layout.setContentsMargins(8, 12, 8, 8)
        
        mode_lay = QHBoxLayout()
        mode_lay.addWidget(QLabel("Режим реза:"))
        self.combo_sub_mode = QComboBox()
        self.combo_sub_mode.addItems(["Верх трубы", "Низ трубы"])
        self.combo_sub_mode.setFixedWidth(110)
        mode_lay.addStretch()
        mode_lay.addWidget(self.combo_sub_mode)
        base_layout.addLayout(mode_lay)
        
        self.spin_mill_dia = create_standard_row(base_layout, "Диаметр фрезы:", 12.0, 2.0, 32.0)
        self.spin_torec_z = create_standard_row(base_layout, "Глубина торцов Z:", -45.0, -150.0, 0.0)
        self.spin_lezhka_x = create_standard_row(base_layout, "Ширина лежки X:", 2400.0, 100.0, 6000.0)
        self.spin_back_vypusk = create_standard_row(base_layout, "Задний выпуск:", 50.0, 0.0, 500.0)
        
        # НОВЫЕ ПОЛЯ ПО ТЗ ОПЕРАТОРА (Ваши дефолтные уставки)
        self.spin_spindle_s = create_standard_row(base_layout, "Обороты (S):", 30000.0, 500.0, 30000.0, " об/м")
        self.spin_feed_xy = create_standard_row(base_layout, "Подача XY (F):", 2000.0, 100.0, 10000.0, " мм/м")
        self.spin_feed_z = create_standard_row(base_layout, "Подача Z (Fz):", 500.0, 50.0, 3000.0, " мм/м")
        
        layout.addWidget(base_group)
        
        # =========================================================================
        # 📦 БЛОК 2: ЗАЩИЩЕННЫЕ ПАРАМЕТРЫ
        # =========================================================================
        protect_group = QGroupBox("Защищенные параметры")
        protect_layout = QVBoxLayout(protect_group)
        protect_layout.setSpacing(4)
        protect_layout.setContentsMargins(8, 12, 8, 8)
        
        self.ch_paz_w, self.spin_paz_w = create_protected_row(protect_layout, "Ширина паза:", 45.0, 5.0, 150.0)
        self.ch_paz_z, self.spin_paz_z = create_protected_row(protect_layout, "Глубина паза Z:", -20.0, -100.0, 0.0)
        self.ch_front, self.spin_front_vypusk = create_protected_row(protect_layout, "Передний выпуск:", 50.0, 0.0, 500.0)
        
        layout.addWidget(protect_group)
        
        # =========================================================================
        # 📦 БЛОК 3: ГЕРМЕТИК
        # =========================================================================
        self.germetik_group = QGroupBox("Параметры Герметика")
        germetik_group_layout = QVBoxLayout(self.germetik_group)
        germetik_group_layout.setSpacing(4)
        germetik_group_layout.setContentsMargins(8, 12, 8, 8)
        
        self.ch_germ_w, self.spin_germ_w = create_protected_row(germetik_group_layout, "Ширина паза Герметик:", 5.0, 1.0, 50.0)
        self.ch_germ_z, self.spin_germ_z = create_protected_row(germetik_group_layout, "Глубина паза Герметик:", 5.0, 1.0, 50.0)
        
        layout.addWidget(self.germetik_group)
        self.germetik_group.setVisible(False)
        self.combo_sub_mode.currentIndexChanged.connect(self._toggle_germetik_visibility)
        
        # =========================================================================
        # 📦 БЛОК 4: ДЛИНЫ КОМНАТ БАНИ
        # =========================================================================
        rooms_group = QGroupBox("Длины комнат бани")
        rooms_layout = QVBoxLayout(rooms_group)
        rooms_layout.setSpacing(4)
        rooms_layout.setContentsMargins(8, 12, 8, 8)
        
        self.room_checkboxes = []
        self.room_spinboxes = []
        for i in range(1, 6):
            chbox, spin = create_protected_row(rooms_layout, f"Комната {i}:", 0.0, 0.0, 6000.0)
            self.room_checkboxes.append(chbox)
            self.room_spinboxes.append(spin)
        layout.addWidget(rooms_group)
        
        # =========================================================================
        # 💾 БЛОК 5: КНОПКА ЭКСПОРТА УП СТАНКА (.TAP)
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

    def _toggle_germetik_visibility(self, index):
        self.germetik_group.setVisible(index == 1)
