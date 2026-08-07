import os
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QButtonGroup, QStyle
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon

class CadToolbar(QFrame):
    tool_changed = pyqtSignal(str)    # Сигнал переключения активного инструмента
    action_triggered = pyqtSignal(str) # Сигнал нажатия обычной кнопки действия

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame { background-color: #1F1F24; border-bottom: 1px solid #25252D; min-height: 40px; max-height: 40px; }
            QPushButton { background-color: transparent; border: 1px solid transparent; border-radius: 4px; padding: 2px; }
            QPushButton:hover { background-color: #282830; border-color: #353540; }
            QPushButton:checked { background-color: #00A8FF; border-color: #0088CC; }
            QFrame[frameShape="5"] { background-color: #32323D; width: 1px; margin-top: 4px; margin-bottom: 4px; }
        """)
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(6, 0, 6, 0)
        self.main_layout.setSpacing(4)

        # Группа исключительного выбора (Западать может строго одна кнопка)
        self.drawing_group = QButtonGroup(self)
        self.drawing_group.setExclusive(True)

        # 🔥 ИСПРАВЛЕНО: Заменили os.getcwd() на безопасное определение путей для EXE
        import sys
        if getattr(sys, 'frozen', False) and hasattr(sys, '_meipass'):
            # Если программа запущена из скомпилированного .exe файла,
            # PyInstaller распаковывает ресурсы во временную папку sys._meipass
            base_dir = sys._meipass
        else:
            # Если программа запускается как обычный python-скрипт в редакторе
            # Берем путь от папки, где лежит сам файл toolbar.py, и поднимаемся на 2 уровня вверх к корню
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Жестко фиксируем абсолютный путь к иконкам фабрики
        self.icons_dir = os.path.join(base_dir, "resources", "icons")
        
        self._build_toolbar()

    def reset_to_select_mode(self):
        """Принудительно возвращает визуальное нажатие тулбара на стрелочку Указателя (по клавише Esc)"""
        for button in self.drawing_group.buttons():
            if button.property("action_id") == "mod_select":
                button.setChecked(True)
                # Блокируем сигнальный цикл, просто уведомляем холст о смене режима
                self.tool_changed.emit("mod_select")
                break

    def _create_v_line(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def _add_btn(self, icon_name, action_id, tooltip, is_checkable=False):
        btn = QPushButton()
        btn.setFixedSize(32, 32)
        btn.setToolTip(tooltip)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setProperty("action_id", action_id)
        
        icon_path = os.path.join(self.icons_dir, icon_name)
        if os.path.exists(icon_path):
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(25, 25))
        else:
            default_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DriveHDIcon)
            btn.setIcon(default_icon)

        if is_checkable:
            btn.setCheckable(True)
            self.drawing_group.addButton(btn)
            btn.clicked.connect(self._on_tool_clicked)
        else:
            btn.clicked.connect(self._on_action_clicked)
            
        self.main_layout.addWidget(btn)

    def _on_tool_clicked(self):
        btn = self.sender()
        if btn:
            self.tool_changed.emit(btn.property("action_id"))

    def _on_action_clicked(self):
        btn = self.sender()
        if btn:
            self.action_triggered.emit(btn.property("action_id"))

    def _build_toolbar(self):
        # 1. Группа - Файлы
        self._add_btn("new.png", "file_new", "Новый файл (.cam)")
        self._add_btn("open.png", "file_open", "Открыть файл")
        self._add_btn("save.png", "file_save", "Сохранить файл")
        self._add_btn("save_as.png", "file_save_as", "Сохранить как...")
        self.main_layout.addWidget(self._create_v_line())

        # 2. Группа - Импорт/Экспорт
        self._add_btn("import_img.png", "import_img", "Импорт из изображения (Векторизатор)")
        self._add_btn("import_dxf.png", "import_dxf", "Импорт из DXF")
        self._add_btn("export_tap.png", "export_tap", "Экспорт в TAP (G-код для станка)")
        self._add_btn("export_dxf.png", "export_dxf", "Экспорт в DXF")
        self._add_btn("export_pdf.png", "export_pdf", "Экспорт в PDF чертеж")
        self.main_layout.addWidget(self._create_v_line())

        # 3. Группа - Модификаторы
        self._add_btn("copy.png", "edit_copy", "Копировать (Ctrl+C)")
        self._add_btn("paste.png", "edit_paste", "Вставить (Ctrl+V)")
        self._add_btn("cut.png", "edit_cut", "Вырезать (Ctrl+X)")
        self._add_btn("select_one.png", "mod_select", "Выбрать элемент (Режим по умолчанию)", is_checkable=True)
        self._add_btn("select_group.png", "mod_select_group", "Выбор группы элементов", is_checkable=True)
        self._add_btn("undo.png", "edit_undo", "Отменить 1 действие")
        self._add_btn("undo_all.png", "edit_undo_all", "Отменить всё")
        self._add_btn("redo.png", "edit_redo", "Вернуть отмененное")
        
        # Установим выбор по умолчанию на "Указатель"
        for button in self.drawing_group.buttons():
            if button.property("action_id") == "mod_select":
                button.setChecked(True)
        self.main_layout.addWidget(self._create_v_line())

        # 4. Группа - Черчение
        self._add_btn("draw_line.png", "line", "Линия по заданным точкам", is_checkable=True)
        self._add_btn("draw_curve.png", "draw_curve", "Кривая линия по заданным точкам", is_checkable=True)
        self._add_btn("draw_circle.png", "draw_circle", "Окружность по заданным точкам", is_checkable=True)
        self._add_btn("draw_rect.png", "rect", "Прямоугольник по заданным точкам", is_checkable=True)
        self._add_btn("draw_rhomb.png", "draw_rhomb", "Ромб по заданным точкам", is_checkable=True)
        self._add_btn("draw_poly.png", "draw_poly", "Многоугольник по заданным точкам", is_checkable=True)
        self._add_btn("eraser.png", "draw_eraser", "Ластик (Удаление сегментов векторов)", is_checkable=True)
        # 🔥 ВНЕДРЕНО: Кнопки 4.8 и 4.9 быстрого промышленного разворота деталей на 90 градусов
        self._add_btn("rotate_left.png", "action_rotate_left", "Повернуть выбранное на 90° влево")
        self._add_btn("rotate_right.png", "action_rotate_right", "Повернуть выбранное на 90° вправо")
        self.main_layout.addWidget(self._create_v_line())

        # 5. Группа - Текст
        self._add_btn("text_area.png", "text_area", "Выбор области для текста", is_checkable=True)
        self._add_btn("text_font.png", "text_font", "Настройка шрифта и размера текста")
        self.main_layout.addWidget(self._create_v_line())

        # 6. Группа - Настройки
        self._add_btn("settings_canvas.png", "settings_canvas", "Общие настройки холста")
        self._add_btn("settings_cnc.png", "settings_cnc", "Настройки ЧПУ (Скорость, диаметр фрезы)")
        self._add_btn("stub_1.png", "settings_stub_1", "Параметры (Заглушка)")
        self._add_btn("stub_2.png", "settings_stub_2", "Параметры (Заглушка)")
        self.main_layout.addWidget(self._create_v_line())

        # 7. Группа - Прочие
        self._add_btn("screen_center.png", "view_center", "Центровка экрана (В ноль осей X/Y)")
        self.main_layout.addStretch()
