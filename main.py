import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QStackedWidget
from PyQt6.QtCore import Qt, QVariantAnimation, QAbstractAnimation
from PyQt6.QtGui import QColor
from modules.tracking_disks.controller import DisksController
from modules.tracking_gcode.controller import GCodeController


# Импортируем стили и наш готовый контроллер пазировки
from styles import QSS_STYLE
from modules.tracking_paz.controller import PazController

# =========================================================================
# 🧠 1. ДВИЖОК ПЛАВНОГО ПЕРЕТЕКАНИЯ ЦВЕТОВ (АППАРАТНЫЙ АНИМАТОР QT)
# =========================================================================
class BackgroundAnimator:
    """Изолированный движок плавного перетекания цеховых цветов окон"""
    def __init__(self, target_widget):
        self.widget = target_widget
        self.current_color = QColor("#1A1A1E")  # Стартовый угольный цвет пазировки
        
        # Создаем встроенный C++ аниматор Qt
        self.animation = QVariantAnimation()
        self.animation.setDuration(250)  # Плавность перехода: 250 миллисекунд
        self.animation.valueChanged.connect(self._handle_color_change)

    def transition_to(self, target_color_hex: str):
        """Запускает мягкое перетекание в новый брендовый оттенок вкладки"""
        if self.animation.state() == QAbstractAnimation.State.Running:
            self.animation.stop()
            
        target_color = QColor(target_color_hex)
        self.animation.setStartValue(self.current_color)
        self.animation.setEndValue(target_color)
        self.animation.start()
        
        # Запоминаем новый цвет как отправную точку для следующего клика
        self.current_color = target_color

    def _handle_color_change(self, value):
        """Вызывается на каждом микро-шаге таймера Qt и обновляет фон окна"""
        color_rgb = value.name()
        self.widget.setStyleSheet(f"QMainWindow {{ background-color: {color_rgb}; }}")


# =========================================================================
# 👑 2. ГЛАВНОЕ ОКНО ПРИЛОЖЕНИЯ СТАНКА
# =========================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ЧПУ Бани Бабочки — CAM Модуль v2.0')
        # 🔥 ВНЕДРЕНО: Установка фирменной иконки (favicon) приложения
        from PyQt6.QtGui import QIcon
        self.setWindowIcon(QIcon("assets/icons_3d/favicon.png")) # Укажите точный путь к вашему файлу
        self.setGeometry(100, 100, 1366, 768)  # Строгие габариты цехового монитора
        
        # Инициализируем наш живой лоск интерфейса
        self.bg_animator = BackgroundAnimator(self)
        
        # Главный центральный виджет-подложка
        main_central_widget = QWidget()
        self.setCentralWidget(main_central_widget)
        
        # Главный вертикальный слой всего окна
        root_layout = QVBoxLayout(main_central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        
        # -----------------------------------------------------------------
        # 🧱 ХЕДЕР ПАНЕЛИ (Верхняя планка управления - ИСПРАВЛЕНА ЦЕНТРОВКА)
        # -----------------------------------------------------------------
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 0, 15, 0)
        header_layout.setSpacing(10)
        
        # Брендовый логотип (Остается строго слева)
        logo_label = QLabel("БАНИ БАБОЧКИ ЧПУ")
        logo_label.setObjectName("HeaderLogo")
        header_layout.addWidget(logo_label)
        
        # ПЕРВАЯ ПРУЖИНА: Отталкивает кнопки от логотипа в центр
        header_layout.addStretch()
        
        # Массив для кнопок хедера
        self.tab_buttons = []
        
        # Функция для быстрой генерации кнопок в хедер
        def create_tab_button(text, index):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)  # Кнопки работают как радио-переключатели
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setProperty("class", "HeaderTabButton")
            btn.clicked.connect(lambda: self.on_header_tab_changed(index))
            header_layout.addWidget(btn)
            self.tab_buttons.append(btn)
            return btn
            
        # Генерируем кнопки (Они выстроятся строго по центру хедера)
        self.btn_paz = create_tab_button("Пазировка", 0)
        self.btn_disks = create_tab_button("Диски", 1)
        self.btn_editor = create_tab_button("Редактор", 2)
        self.btn_gcode = create_tab_button("Просмотр G-кода", 3)
        
        # ВТОРАЯ ПРУЖИНА: Зажимает кнопки с правого края, удерживая их по центру
        header_layout.addStretch()
        
        # По умолчанию активируем первую кнопку "Пазировка"
        self.btn_paz.setChecked(True)
        
        root_layout.addWidget(header_frame)
        
        # -----------------------------------------------------------------
        # 🔀 ЦЕНТРАЛЬНЫЙ СТЕК МОДУЛЕЙ (ОСНОВНОЙ КОНТЕНТ)
        # -----------------------------------------------------------------
        self.main_stacked_widget = QStackedWidget()
        root_layout.addWidget(self.main_stacked_widget)
        
        # === МОДУЛЬ 1: ПАЗИРОВКА ===
        self.paz_controller = PazController()
        paz_sidebar, paz_canvas = self.paz_controller.get_widgets()
        
        # Собираем рабочую область пазировки (сайдбар слева, холст справа)
        paz_workspace = QWidget()
        paz_workspace_layout = QHBoxLayout(paz_workspace)
        paz_workspace_layout.setContentsMargins(8, 10, 10, 10)
        paz_workspace_layout.setSpacing(10)
        paz_workspace_layout.addWidget(paz_sidebar)
        paz_workspace_layout.addWidget(paz_canvas, stretch=1)
        
        self.main_stacked_widget.addWidget(paz_workspace) # Индекс 0
        
        # === МОДУЛЬ 2: ДИСКИ ===
        self.disks_controller = DisksController()
        disks_sidebar, disks_canvas = self.disks_controller.get_widgets()
        
        # Собираем рабочую область дисков (сайдбар слева, холст справа)
        disks_workspace = QWidget()
        disks_workspace_layout = QHBoxLayout(disks_workspace)
        disks_workspace_layout.setContentsMargins(8, 10, 10, 10)
        disks_workspace_layout.setSpacing(10)
        disks_workspace_layout.addWidget(disks_sidebar)
        disks_workspace_layout.addWidget(disks_canvas, stretch=1)
        
        self.main_stacked_widget.addWidget(disks_workspace) # Индекс 1
        
        # === МОДУЛЬ 3: РЕДАКТОР (ЗАГЛУШКА) ===
        self.editor_stub = QWidget()
        editor_lay = QHBoxLayout(self.editor_stub)
        editor_lay.addWidget(QLabel("[ Редактор контуров бани ]"))
        self.main_stacked_widget.addWidget(self.editor_stub) # Индекс 2
        
        # === МОДУЛЬ 4: ПРОСМОТР G-КОДА ===
        self.gcode_controller = GCodeController()
        gcode_sidebar, gcode_canvas = self.gcode_controller.get_widgets()
        
        # Собираем рабочую область просмотра кодов (терминал слева, CAD-трекер справа)
        gcode_workspace = QWidget()
        gcode_workspace_layout = QHBoxLayout(gcode_workspace)
        gcode_workspace_layout.setContentsMargins(8, 10, 10, 10)
        gcode_workspace_layout.setSpacing(10)
        gcode_workspace_layout.addWidget(gcode_sidebar)
        gcode_workspace_layout.addWidget(gcode_canvas, stretch=1)
        
        self.main_stacked_widget.addWidget(gcode_workspace) # Индекс 3

    def on_header_tab_changed(self, tab_index):
        """Вызывается при клике оператора на кнопки хедера. Переключает виджет и запускает плавный перелив фона"""
        # 1. Мгновенно переключаем экран в стеке
        self.main_stacked_widget.setCurrentIndex(tab_index)
        
        # 2. ЗАПУСКАЕМ ЖИВОЙ ПЛАВНЫЙ ПЕРЕЛИВ ФОНА ПО КАРТЕ ЦВЕТОВ ЦЕХА:
        if tab_index == 0:
            self.bg_animator.transition_to("#1A1A1E")  # Пазировка: Глубокий угольный
        elif tab_index == 1:
            self.bg_animator.transition_to("#161F33")  # Диски: Благородный тёмно-синий
        elif tab_index == 2:
            self.bg_animator.transition_to("#162421")  # Редактор: Строгий тёмно-графитовый
        elif tab_index == 3:
            self.bg_animator.transition_to("#1F1633")  # Просмотр G-кода: Глубокий фиолетовый

# =========================================================================
# 🚀 ТОЧКА ВХОДА СИСТЕМЫ
# =========================================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Применяем нашу таблицу стилей QSS
    app.setStyleSheet(QSS_STYLE)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
