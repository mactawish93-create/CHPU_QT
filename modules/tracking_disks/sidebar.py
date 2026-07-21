# ИСПРАВЛЕНО: Добавлен QPushButton в общий список импортов виджетов
from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QDoubleSpinBox, QComboBox, QStackedWidget, QFrame, QPushButton
from PyQt6.QtCore import Qt
from config import SIDEBAR_WIDTH

# =========================================================================
# 📦 УНИВЕРСАЛЬНЫЙ ВИДЖЕТ НАСТРОЕК (ДЛЯ КРУГЛОГО И КВАДРО ДИСКОВ)
# =========================================================================
class DiskStandardParamView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Сверхплотный внутренний слой виджета
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Главная карточка GroupBox
        self.group_box = QGroupBox("Параметры геометрии диска")
        card_layout = QVBoxLayout(self.group_box)
        card_layout.setSpacing(4) # Жесткий ЧПУ-зазор между полями в 4 пикселя
        card_layout.setContentsMargins(8, 12, 8, 8)
        
        # 1. Выбор подрежима (Глухой / С проемом)
        mode_lay = QHBoxLayout()
        mode_lay.setSpacing(4)
        mode_lay.addWidget(QLabel("Тип диска:"))
        self.combo_sub_mode = QComboBox()
        self.combo_sub_mode.addItems(["Глухой диск", "Диск с проемом"])
        self.combo_sub_mode.setFixedWidth(130)
        mode_lay.addStretch()
        mode_lay.addWidget(self.combo_sub_mode)
        card_layout.addLayout(mode_lay)
        
        # 2. Выбор диаметра
        dia_lay = QHBoxLayout()
        dia_lay.setSpacing(4)
        dia_lay.addWidget(QLabel("Диаметр диска:"))
        self.combo_diameter = QComboBox()
        self.combo_diameter.addItems(["2000 мм", "2150 мм", "2300 мм"])
        self.combo_diameter.setFixedWidth(130)
        dia_lay.addStretch()
        dia_lay.addWidget(self.combo_diameter)
        card_layout.addLayout(dia_lay)
        
        # 3. Смещение проема (Скрываемая строка фрейма)
        self.offset_frame = QFrame()
        self.offset_frame.setFrameShape(QFrame.Shape.NoFrame)
        offset_lay = QHBoxLayout(self.offset_frame)
        offset_lay.setContentsMargins(0, 0, 0, 0)
        offset_lay.setSpacing(4)
        
        offset_lay.addWidget(QLabel("Смещение проема:"))
        self.combo_door_offset = QComboBox()
        self.combo_door_offset.addItems(["0 мм", "100 мм", "150 мм"])
        self.combo_door_offset.setFixedWidth(130)
        offset_lay.addStretch()
        offset_lay.addWidget(self.combo_door_offset)
        card_layout.addWidget(self.offset_frame)
        
        # По умолчанию скрываем смещение проема
        self.offset_frame.setVisible(False)
        
        # 4. Глубина реза Z
        z_lay = QHBoxLayout()
        z_lay.setSpacing(4)
        z_lay.addWidget(QLabel("Глубина реза Z:"))
        self.spin_depth_z = QDoubleSpinBox()
        self.spin_depth_z.setRange(-150.0, 50.0)
        self.spin_depth_z.setValue(0.0)
        self.spin_depth_z.setSuffix(" мм")
        self.spin_depth_z.setFixedWidth(130)
        z_lay.addStretch()
        z_lay.addWidget(self.spin_depth_z)
        card_layout.addLayout(z_lay)
        
        # 🔥 КРИТИЧЕСКИЙ НАДСТРОЙ: Пружина жесткого поджатия элементов кверху
        card_layout.addStretch()
        
        layout.addWidget(self.group_box)
        
        # Подключаем автоматические цеховые триггеры логики полей
        self.combo_sub_mode.currentIndexChanged.connect(self._toggle_offset_visibility)
        self.combo_diameter.currentIndexChanged.connect(self._validate_diameter_and_offset)

    def _toggle_offset_visibility(self, index):
        """Показывает строку смещения только если выбран 'Диск с проемом' (индекс 1)"""
        is_door_mode = (index == 1)
        self.offset_frame.setVisible(is_door_mode)
        # Принудительно вызываем валидацию, чтобы при открытии строки проверить лимиты
        if is_door_mode:
            self._validate_diameter_and_offset(self.combo_diameter.currentIndex())

    def _validate_diameter_and_offset(self, dia_index):
        """УМНАЯ ЧПУ ЗАЩИТА: Блокирует смещение 150 мм, если диаметр диска равен 2000 мм (индекс 0)"""
        # Если выбран диаметр 2000 мм
        if dia_index == 0:
            # Если оператор стоял на запрещенном пункте 150 мм (индекс 2) — принудительно сбрасываем его на 100 мм
            if self.combo_door_offset.currentIndex() == 2:
                self.combo_door_offset.setCurrentIndex(1)
            # Отключаем (скрываем из доступа) третий пункт выпадающего списка
            self.combo_door_offset.model().item(2).setEnabled(False)
        else:
            # Для остальных диаметров (2150 и 2300) — смещение 150 мм полностью доступно
            self.combo_door_offset.model().item(2).setEnabled(True)


# =========================================================================
# 👑 ГЛАВНЫЙ СУПЕР-КАРКАС САЙДБАРA ДИСКОВ (5 РЕЖИМОВ)
# =========================================================================
class DisksSidebar(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DisksSidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # Базовый контейнер панели
        content_widget = QWidget()
        content_widget.setObjectName("SidebarContent")
        self.setWidget(content_widget)
        
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(10, 15, 10, 15)
        main_layout.setSpacing(15)
        
        # 👑 ГЛАВНЫЙ СЕЛЕКТОР ФОРМ БАНЬ
        self.combo_main_mode = QComboBox()
        self.combo_main_mode.addItems([
            "1. Круглый диск",
            "2. Квадро диск",
            "3. БаБочка диск",
            "4. Викинг диск",
            "5. КвадроХаус диск"
        ])
        self.combo_main_mode.setStyleSheet("font-weight: bold; color: #FF9F43;")
        main_layout.addWidget(self.combo_main_mode)
        
        # 🔀 МЕНЕДЖЕР РЕЖИМОВ (STACKED WIDGET)
        self.sub_modes_container = QStackedWidget()
        main_layout.addWidget(self.sub_modes_container)
        
        # 1. Загружаем полноценную рабочую форму для Круглого диска
        self.round_view = DiskStandardParamView()
        self.sub_modes_container.addWidget(self.round_view)
        
        # 2. Загружаем такую же рабочую форму для Квадро диска
        self.quadro_view = DiskStandardParamView()
        self.sub_modes_container.addWidget(self.quadro_view)
        
        # Функции-помощники для быстрой генерации текстовых заглушек остальных бань
        def create_stub_widget(text):
            stub = QWidget()
            lay = QVBoxLayout(stub)
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #707078; font-style: italic; font-size: 11px;")
            lay.addWidget(lbl)
            lay.addStretch()
            return stub
            
        # 3, 4, 5 — Временные чистые заглушки по вашему ТЗ
        self.sub_modes_container.addWidget(create_stub_widget("[ Форма БаБочка диск — Заглушка ]"))
        self.sub_modes_container.addWidget(create_stub_widget("[ Форма Викинг диск — Заглушка ]"))
        self.sub_modes_container.addWidget(create_stub_widget("[ Форма КвадроХаус диск — Заглушка ]"))
        
        # Привязываем выбор в оранжевом комбобоксе к смене активных виджетов в стеке сайдбара
        self.combo_main_mode.currentIndexChanged.connect(self.sub_modes_container.setCurrentIndex)
        
        # =========================================================================
        # 💾 БЛОК: КНОПКА ГЕНЕРАЦИИ G-КОДА ДИСКОВ (.TAP)
        # =========================================================================
        main_layout.addSpacing(5)
        self.btn_generate_gcode = QPushButton("💾 Сгенерировать G-код диска (.tap)")
        self.btn_generate_gcode.setFixedHeight(26)
        self.btn_generate_gcode.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_generate_gcode.setStyleSheet("""
            QPushButton { 
                background-color: #282830; color: #00A8FF; border: 1px solid #00A8FF; border-radius: 4px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: #00A8FF; color: #FFFFFF; }
        """)
        main_layout.addWidget(self.btn_generate_gcode)

        # Прижимаем всё кверху для сохранения плотности интерфейса Compact UI
        main_layout.addStretch()
