from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QListWidget, QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt
from config import SIDEBAR_WIDTH

class GCodeSidebar(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GCodeSidebar")
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
        main_layout.setSpacing(10)
        
        # 👑 ЗАГОЛОВОК МОДУЛЯ
        title_lbl = QLabel("ТЕРМИНАЛ G-КОДА")
        title_lbl.setStyleSheet("font-weight: bold; color: #9B5DE5; font-size: 11px;") # Брендовый фиолетовый цвет терминала
        main_layout.addWidget(title_lbl)
        
        # 🧾 ИНТЕРАКТИВНЫЙ СПИСОК СТРОК ЧПУ-ПРОГРАММЫ
        # Используем QListWidget, так как он идеально перехватывает стрелочки клавиатуры вверх/вниз
        self.list_lines = QListWidget()
        self.list_lines.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.list_lines.setStyleSheet("""
            QListWidget {
                background-color: #1A1A1E;
                color: #A0A0A8;
                border: 1px solid #32323D;
                border-radius: 4px;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 10px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 1px 2px;
            }
            QListWidget::item:hover {
                background-color: #25252D;
                color: #E0E0E6;
            }
            QListWidget::item:selected {
                background-color: #9B5DE5;
                color: #FFFFFF;
                font-weight: bold;
            }
        """)
        main_layout.addWidget(self.list_lines, stretch=1) # Список забирает все свободное пространство по высоте
        
        # 📂 КНОПКА ОТКРЫТИЯ УП С ФЛЕШКИ СТАНКА
        self.btn_load_gcode = QPushButton("📂 Загрузить G-код (.tap)")
        self.btn_load_gcode.setFixedHeight(26)
        self.btn_load_gcode.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_generate_dxf = QPushButton("📐 Экспорт траектории в DXF")
        self.btn_generate_dxf.setFixedHeight(26)
        self.btn_generate_dxf.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        # Стилизация под фирменную палитру терминала УП
        self.btn_load_gcode.setStyleSheet("""
            QPushButton { 
                background-color: #282830; color: #9B5DE5; border: 1px solid #9B5DE5; border-radius: 4px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: #9B5DE5; color: #FFFFFF; }
        """)
        
        self.btn_generate_dxf.setStyleSheet("""
            QPushButton { 
                background-color: #282830; color: #2ECC71; border: 1px solid #2ECC71; border-radius: 4px; font-weight: bold; font-size: 10px;
            }
            QPushButton:hover { background-color: #2ECC71; color: #FFFFFF; }
        """)
        
        main_layout.addWidget(self.btn_load_gcode)
        main_layout.addWidget(self.btn_generate_dxf)
        
    def load_lines_to_view(self, text_lines: list):
        """Служебный метод: мгновенно засыпает массив строк УП в терминал интерфейса"""
        self.list_lines.clear()
        if not text_lines:
            return
        self.list_lines.addItems(text_lines)
        self.list_lines.setCurrentRow(0) # Фокусируемся на первой строчке шапки программы
