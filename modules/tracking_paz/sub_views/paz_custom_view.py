from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QLabel, QDoubleSpinBox, QCheckBox, QPushButton, QFormLayout)
from PyQt6.QtCore import Qt

# =========================================================================
# 📦 РАСКРЫВАЮЩАЯСЯ ПЛАШКА ДЛЯ ПРОИЗВОЛЬНОГО ПАЗА
# =========================================================================
class CustomSlotRow(QWidget):
    def __init__(self, number, on_delete_callback, parent=None):
        super().__init__(parent)
        self.on_delete_callback = on_delete_callback
        
        # Главный вертикальный слой плашки
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 2, 0, 2)
        self.main_layout.setSpacing(2)
        
        # --- Шапка плашки (Всегда видимая строка) ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)
        
        self.checkbox = QCheckBox(f"Паз №{number}")
        self.checkbox.setStyleSheet("font-weight: bold; color: #E0E0E6;")
        header_layout.addWidget(self.checkbox)
        header_layout.addStretch()
        
        # Маленькая компактная кнопка удаления (корзина)
        self.btn_delete = QPushButton("🗑")
        self.btn_delete.setFixedWidth(24)
        self.btn_delete.setFixedHeight(18)
        self.btn_delete.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_delete.setStyleSheet("""
            QPushButton { 
                background-color: #2D2D35; color: #FF6B6B; border: 1px solid #3E3E48; border-radius: 3px; font-size: 9px; 
            }
            QPushButton:hover { background-color: #FF6B6B; color: #FFFFFF; }
        """)
        self.btn_delete.clicked.connect(self._delete_self)
        header_layout.addWidget(self.btn_delete)
        self.main_layout.addLayout(header_layout)
        
        # --- Нижний скрытый блок параметров (Разъезжается при клике) ---
        self.container_fields = QWidget()
        self.container_fields.setObjectName("FieldsContainer")
        self.container_fields.setStyleSheet("QWidget#FieldsContainer { border-left: 2px solid #3E3E48; padding-left: 6px; }")
        
        fields_layout = QFormLayout(self.container_fields)
        fields_layout.setSpacing(4)
        fields_layout.setContentsMargins(5, 4, 0, 4)
        
        def add_field(layout, text):
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 6000.0)
            spin.setValue(0.0)
            spin.setSuffix(" мм")
            spin.setFixedWidth(85)
            layout.addRow(text, spin)
            return spin
            
        self.spin_width = add_field(fields_layout, "Ширина паза:")
        self.spin_length = add_field(fields_layout, "Длина паза:")
        self.spin_depth = add_field(fields_layout, "Глубина паза Z:")
        self.spin_offset = add_field(fields_layout, "Расстояние до 0:")
        
        self.main_layout.addWidget(self.container_fields)
        
        # Намертво скрываем поля при старте
        self.container_fields.setVisible(False)
        
        # Магия PyQt6: Связываем галочку чекбокса с раскрытием контейнера полей
        self.checkbox.toggled.connect(self.container_fields.setVisible)

    def update_number(self, new_number):
        """Пересчет индексов при удалении"""
        self.checkbox.setText(f"Паз №{new_number}")

    def _delete_self(self):
        """Уничтожает виджет и сообщает родителю"""
        self.setParent(None)
        self.deleteLater()
        self.on_delete_callback(self)
# =========================================================================
# 📦 РАСКРЫВАЮЩАЯСЯ ПЛАШКА ДЛЯ ПРОИЗВОЛЬНОГО ТОРЦА
# =========================================================================
class CustomTorecRow(QWidget):
    def __init__(self, number, on_delete_callback, parent=None):
        super().__init__(parent)
        self.on_delete_callback = on_delete_callback
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 2, 0, 2)
        self.main_layout.setSpacing(2)
        
        # Шапка плашки торца
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)
        
        self.checkbox = QCheckBox(f"Торец №{number}")
        self.checkbox.setStyleSheet("font-weight: bold; color: #E0E0E6;")
        header_layout.addWidget(self.checkbox)
        header_layout.addStretch()
        
        # Кнопка удаления торца
        self.btn_delete = QPushButton("🗑")
        self.btn_delete.setFixedWidth(24)
        self.btn_delete.setFixedHeight(18)
        self.btn_delete.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_delete.setStyleSheet("""
            QPushButton { 
                background-color: #2D2D35; color: #FF6B6B; border: 1px solid #3E3E48; border-radius: 3px; font-size: 9px; 
            }
            QPushButton:hover { background-color: #FF6B6B; color: #FFFFFF; }
        """)
        self.btn_delete.clicked.connect(self._delete_self)
        header_layout.addWidget(self.btn_delete)
        self.main_layout.addLayout(header_layout)
        
        # Скрытый блок полей параметров торца
        self.container_fields = QWidget()
        self.container_fields.setObjectName("FieldsContainer")
        self.container_fields.setStyleSheet("QWidget#FieldsContainer { border-left: 2px solid #3E3E48; padding-left: 6px; }")
        
        fields_layout = QFormLayout(self.container_fields)
        fields_layout.setSpacing(4)
        fields_layout.setContentsMargins(5, 4, 0, 4)
        
        def add_field(layout, text):
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 6000.0)
            spin.setValue(0.0)
            spin.setSuffix(" мм")
            spin.setFixedWidth(85)
            layout.addRow(text, spin)
            return spin
            
        self.spin_depth = add_field(fields_layout, "Глубина торца:")
        self.spin_length = add_field(fields_layout, "Длина торца:")
        self.spin_offset = add_field(fields_layout, "Расстояние до 0:")
        
        self.main_layout.addWidget(self.container_fields)
        self.container_fields.setVisible(False)
        self.checkbox.toggled.connect(self.container_fields.setVisible)

    def update_number(self, new_number):
        """Пересчет индексов при удалении торца"""
        self.checkbox.setText(f"Торец №{new_number}")

    def _delete_self(self):
        """Уничтожение виджета торца"""
        self.setParent(None)
        self.deleteLater()
        self.on_delete_callback(self)# =========================================================================
# 👑 ГЛАВНАЯ ФОРМА ПОДРЕЖИМА ПРОИЗВОЛЬНОЙ ПАЗИРОВКИ
# =========================================================================
class PazCustomView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Главный вертикальный слой
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Массивы для хранения созданных плашек векторов ЧПУ
        self.slots_list = []
        self.torecs_list = []
        
        # =========================================================================
        # 📦 БЛОК ПАЗОВ
        # =========================================================================
        self.group_slots = QGroupBox("Параметры пазов")
        self.slots_layout = QVBoxLayout(self.group_slots)
        self.slots_layout.setSpacing(6)
        self.slots_layout.setContentsMargins(8, 12, 8, 8)
        
        # Контейнер внутри карточки, куда будут падать новые пазы
        self.slots_container_layout = QVBoxLayout()
        self.slots_container_layout.setSpacing(4)
        self.slots_layout.addLayout(self.slots_container_layout)
        
        # Кнопка добавления паза
        self.btn_add_slot = QPushButton("+ Добавить новый паз")
        self.btn_add_slot.setFixedHeight(20)
        self.btn_add_slot.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_add_slot.setStyleSheet("""
            QPushButton { background-color: #2D2D35; color: #00A8FF; border: 1px dashed #00A8FF; font-weight: bold; font-size: 10px; }
            QPushButton:hover { background-color: #00A8FF; color: #FFFFFF; border-style: solid; }
        """)
        self.btn_add_slot.clicked.connect(self._add_new_slot)
        self.slots_layout.addWidget(self.btn_add_slot)
        
        layout.addWidget(self.group_slots)
        
        # =========================================================================
        # 📦 БЛОК ТОРЦОВ
        # =========================================================================
        self.group_torecs = QGroupBox("Параметры торцов")
        self.torecs_layout = QVBoxLayout(self.group_torecs)
        self.torecs_layout.setSpacing(6)
        self.torecs_layout.setContentsMargins(8, 12, 8, 8)
        
        self.torecs_container_layout = QVBoxLayout()
        self.torecs_container_layout.setSpacing(4)
        self.torecs_layout.addLayout(self.torecs_container_layout)
        
        # Кнопка добавления торца
        self.btn_add_torec = QPushButton("+ Добавить новый торец")
        self.btn_add_torec.setFixedHeight(20)
        self.btn_add_torec.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_add_torec.setStyleSheet("""
            QPushButton { background-color: #2D2D35; color: #FF9F43; border: 1px dashed #FF9F43; font-weight: bold; font-size: 10px; }
            QPushButton:hover { background-color: #FF9F43; color: #FFFFFF; border-style: solid; }
        """)
        self.btn_add_torec.clicked.connect(self._add_new_torec)
        self.torecs_layout.addWidget(self.btn_add_torec)
        
        layout.addWidget(self.group_torecs)

        # =========================================================================
        # 💾 БЛОК 3: КНОПКА ЭКСПОРТА УП ПРОИЗВОЛЬНОГО РЕЖИМА (.TAP)
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

    # --- Обработчики фабрики Пазов ---
    def _add_new_slot(self):
        """Создает и добавляет новую плашку паза на экран"""
        if len(self.slots_list) >= 10:
            return # Ограничение по ТЗ (не более 10)
            
        next_number = len(self.slots_list) + 1
        new_slot_row = CustomSlotRow(next_number, self._on_slot_deleted)
        
        self.slots_container_layout.addWidget(new_slot_row)
        self.slots_list.append(new_slot_row)
        
        # Блокируем кнопку при достижении лимита
        if len(self.slots_list) == 10:
            self.btn_add_slot.setEnabled(False)

    def _on_slot_deleted(self, deleted_row):
        """Вызывается автоматически при удалении паза"""
        if deleted_row in self.slots_list:
            self.slots_list.remove(deleted_row)
            
        # Сдвигаем нумерацию оставшихся
        for index, row in enumerate(self.slots_list):
            row.update_number(index + 1)
            
        self.btn_add_slot.setEnabled(True)

    # --- Обработчики фабрики Торцов ---
    def _add_new_torec(self):
        if len(self.torecs_list) >= 10:
            return
            
        next_number = len(self.torecs_list) + 1
        new_torec_row = CustomTorecRow(next_number, self._on_torec_deleted)
        
        self.torecs_container_layout.addWidget(new_torec_row)
        self.torecs_list.append(new_torec_row)
        
        if len(self.torecs_list) == 10:
            self.btn_add_torec.setEnabled(False)

    def _on_torec_deleted(self, deleted_row):
        if deleted_row in self.torecs_list:
            self.torecs_list.remove(deleted_row)
            
        for index, row in enumerate(self.torecs_list):
            row.update_number(index + 1)
            
        self.btn_add_torec.setEnabled(True)
