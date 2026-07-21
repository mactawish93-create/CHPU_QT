from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget
from ui.header_widget import HeaderWidget
from config import REGISTERED_MODULES

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Главный центральный контейнер-подложка
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        # Главный вертикальный стек (Хедер сверху, рабочая зона снизу)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Монтируем верхнюю панель управления
        self.header = HeaderWidget(self)
        main_layout.addWidget(self.header)
        
        # 2. Создаем экономичный менеджер вкладок
        self.tabs_container = QStackedWidget(self)
        main_layout.addWidget(self.tabs_container)
        
        # Карты для отслеживания состояния вкладок
        self.tabs_map = {}          # ID модуля -> Индекс в QStackedWidget
        self.loaded_controllers = {} # ID модуля -> Объект контроллера (после загрузки)
        self.layouts_map = {}       # ID модуля -> Ссылка на слой компоновки (Layout) внутри вкладки
        
        # 3. Подготавливаем изолированные пустые каркасы для вкладок
        self._build_empty_skeletons()
        
        # Связываем сигнал хедера с обработчиком переключения и ленивой загрузки
        self.header.tab_changed.connect(self.switch_tab)
        
        # Принудительно инициализируем и показываем первую вкладку при старте
        if REGISTERED_MODULES:
            self.switch_tab(REGISTERED_MODULES[0]["id"])

    def _build_empty_skeletons(self):
        """Создает пустые каркасы-подложки под каждую вкладку на основе конфига"""
        for index, module in enumerate(REGISTERED_MODULES):
            tab_skeleton = QWidget()
            
            # Настраиваем геометрию сетки в зависимости от типа макета
            if module["layout_type"] == "split":
                # Горизонтальный сплиттер (Сайдбар слева, холст справа)
                layout = QHBoxLayout(tab_skeleton)
                layout.setContentsMargins(10, 10, 10, 10)
                layout.setSpacing(10)
            else:
                # Вертикальный стек во весь экран для редактора (Тулбар сверху, холст снизу)
                layout = QVBoxLayout(tab_skeleton)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(0)
            
            # Сохраняем ссылку на слой компоновки, чтобы вставить туда виджеты при клике
            self.layouts_map[module["id"]] = layout
            
            # Добавляем пустой каркас в стек и запоминаем индекс
            self.tabs_container.addWidget(tab_skeleton)
            self.tabs_map[module["id"]] = index

    def switch_tab(self, module_id):
        """Вызывается при клике на вкладку. Лениво загружает модуль и выводит на экран"""
        if module_id not in self.tabs_map:
            return
            
        # ПРОВЕРКА ЛЕНИВОЙ ЗАГРУЗКИ: Если модуль еще ни разу не нажимали, загружаем его из папки
        if module_id not in self.loaded_controllers:
            self._load_module_on_demand(module_id)
            
        # Мгновенно выводим запрашиваемую вкладку на экран цехового ПК
        target_index = self.tabs_map[module_id]
        self.tabs_container.setCurrentIndex(target_index)

    def _load_module_on_demand(self, module_id):
        """Динамическая фабрика: импортирует и монтирует код модуля строго по запросу"""
        
        if module_id == "tracking_paz":
            # Изолированный импорт "внутри функции" — защищает систему от крашей в других папках
            from modules.tracking_paz.controller import PazController
            
            # Создаем объект контроллера
            controller = PazController()
            self.loaded_controllers[module_id] = controller
            
            # Забираем изолированные виджеты
            sidebar_widget, canvas_widget = controller.get_widgets()
            
            # Аккуратно монтируем их в подготовленный горизонтальный макет
            target_layout = self.layouts_map[module_id]
            target_layout.addWidget(sidebar_widget)
            target_layout.addWidget(canvas_widget)
            
        # --- Сюда по аналогии мы добавим блоки для tracking_disks, cad_editor и gcode_viewer ---
        else:
            # Для пока не реализованных вкладок выводим простую временную текстовую заглушку
            from PyQt6.QtWidgets import QLabel
            from PyQt6.QtCore import Qt
            
            target_layout = self.layouts_map[module_id]
            label = QLabel(f"[ Модуль '{module_id}' ожидает подключения в MainWindow ]")
            label.setStyleSheet("color: #606065; font-size: 13px; font-weight: bold;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            target_layout.addWidget(label)
            
            # Чтобы не пытаться загружать заглушку повторно
            self.loaded_controllers[module_id] = True
