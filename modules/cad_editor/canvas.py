from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem, QGraphicsRectItem, QGraphicsPathItem
from PyQt6.QtCore import pyqtSignal, QPointF, Qt, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QTransform, QWheelEvent, QMouseEvent, QKeyEvent, QPainterPath, QFont

from modules.cad_editor.engine import CadEngine
# Импортируем события мыши строго из вашей папки mouse_events/
from modules.cad_editor.mouse_events.click import handle_mouse_press
from modules.cad_editor.mouse_events.move import handle_mouse_move
from modules.cad_editor.mouse_events.release import handle_mouse_release
from modules.cad_editor.mouse_events.wheel import handle_wheel_zoom

# Импортируем клавиатуру строго из вашей папки keyboard_system/
from modules.cad_editor.keyboard_system.key_press import handle_key_press
from modules.cad_editor.keyboard_system.key_release import handle_key_release
from modules.cad_editor.keyboard_system.shortcuts import handle_global_shortcuts

# Импортируем контекстное меню ПКМ
from modules.cad_editor.context_menu import show_cad_context_menu

class CadCanvas(QGraphicsView):
    # Сигналы связи с контроллером и статусбаром
    mouse_moved = pyqtSignal(float, float, float)
    zoom_changed = pyqtSignal(float)
    hint_changed = pyqtSignal(str)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.cad_engine = CadEngine()
        
        # Настройка графического рендеринга
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 🔥 ИСПРАВЛЕНО: Включаем постоянное онлайн-отслеживание мыши БЕЗ нажатия кнопок
        self.setMouseTracking(True)
        
        # Настройка CAD-сцены (поле 10х10 метров, центр в 0,0)
        self.cad_scene = QGraphicsScene(-5000, -5000, 10000, 10000)
        self.setScene(self.cad_scene)
        
        # Внутренние состояния черчения
        self.current_tool = "mod_select"  # Инструмент по умолчанию — Указатель
        self.current_zoom = 1.0
        self.is_drawing = False
        self.poly_sides = 6  # Стороны многоугольника по умолчанию
        
        # Координатные регистры векторов
        self.start_scene_pos = QPointF()
        self.snapped_current_pos = QPointF()
        
        # 🔥 ИСПРАВЛЕНО: Безопасная инициализация регистров кривой Безье для защиты от вылетов
        self.curve_start_pt = QPointF(0.0, 0.0)
        self.curve_end_pt = QPointF(0.0, 0.0)
        
        # Временная геометрия ("Резиновые нити")
        self.temp_item = None
        
        # Модификаторы клавиш (Ctrl активирует магнит)
        self.ctrl_pressed = False
        self.shift_pressed = False
        
        # Внутренний изолированный буфер обмена редактора для Ctrl+C/Ctrl+V
        self.internal_clipboard = []
        
        # НЕОНОВЫЙ ЗЕЛЕНЫЙ ПРИЦЕЛ ОБЪЕКТНОГО ЗАХВАТА
        self.snap_marker = QGraphicsRectItem(-3.0, -3.0, 6.0, 6.0)
        self.snap_marker.setPen(QPen(QColor("#00FF66"), 1.5, Qt.PenStyle.SolidLine))
        self.snap_marker.setBrush(QColor(0, 255, 102, 30)) 
        self.snap_marker.setZValue(1000) # Прицел всегда рисуется поверх всех линий на холсте
        self.snap_marker.hide() 
        self.cad_scene.addItem(self.snap_marker)

        # 🔥 ВНЕДРЕНО: Стеки для хранения истории изменений ЧПУ-чертежа
        self.undo_stack = []
        self.redo_stack = []
        
        # Запоминаем самое первое (пустое) состояние холста
        self.save_history_snapshot()
        
        # 🔥 ВНЕДРЕНО: Регистры для интерактивного ввода текста по рамке
        self.active_text_editor = None
        self.active_text_proxy = None
        self.active_text_bounds = None

        # Центрируем экран в ноль осей ЧПУ при старте
        self.centerOn(0, 0)

    def set_current_tool(self, tool_id):
        """Вызывается контроллером при переключении кнопок на тулбаре"""
        self.current_tool = tool_id
        self.is_drawing = False
        
        if self.temp_item:
            self.cad_scene.removeItem(self.temp_item)
            self.temp_item = None
            
        if hasattr(self, "curve_stage"):
            self.curve_stage = 0

        # Настраиваем режим выделения Qt
        if tool_id in ["mod_select", "mod_select_group"]:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.cad_scene.clearSelection()

        # ДИНАМИЧЕСКАЯ БЛОКИРОВКА ПЕРЕМЕЩЕНИЯ ВЕКТОРОВ МЫШКОЙ
        is_select_mode = (tool_id == "mod_select")
        for item in self.cad_scene.items():
            if item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
                item.setFlag(item.GraphicsItemFlag.ItemIsMovable, is_select_mode)

        self.hint_changed.emit(f"Инструмент: {tool_id.upper()}. Зажмите Ctrl для активации магнита, Shift для ОРТО 45°")

    def update_current_cursor_position(self):
        """Вспомогательный метод для обновления фантома на месте при нажатии клавиш"""
        cursor_pos_pixel = self.mapFromGlobal(self.cursor().pos())
        cursor_pos_f = QPointF(cursor_pos_pixel)
        global_pos_f = QPointF(self.cursor().pos())
        
        fake_event = QMouseEvent(
            QMouseEvent.Type.MouseMove, cursor_pos_f, global_pos_f,
            Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier
        )
        handle_mouse_move(self, fake_event)

    # --- СИСТЕМНЫЕ ПЕРЕНАПРАВЛЕНИЯ В ВАШИ ИЗОЛИРОВАННЫЕ ФАЙЛЫ ---
    def mousePressEvent(self, event: QMouseEvent):
        # 🔥 ВНЕДРЕНО: АЛГОРИТМ ЗАПЕКАНИЯ БУКВ ПРИ КЛИКЕ "МИМО" ТЕКСТОВОГО ПОЛЯ
        if getattr(self, "active_text_editor", None) is not None:
            # Считываем финальный многострочный текст из виджета
            raw_text = self.active_text_editor.toPlainText().strip()
            
            # Извлекаем геометрические границы рамки
            bounds = self.active_text_bounds
            proxy = self.active_text_proxy
            
            # Полностью удаляем текстовый виджет-прокси со сцены, освобождая ОЗУ
            self.scene().removeItem(proxy)
            
            # Сбрасываем ссылки в None, чтобы холст знал, что поле закрыто
            self.active_text_editor = None
            self.active_text_proxy = None
            self.active_text_bounds = None

            # Если оператор ничего не ввел, просто выходим
            if raw_text:
                # Настраиваем перо белого цвета для ЧПУ-контура
                final_pen = QPen(QColor("#E0E0E6"), 1.2, Qt.PenStyle.SolidLine)
                
                # Запускаем тригонометрическую формулу сборки шрифта Безье в Qt
                path = QPainterPath()
                font = QFont("Arial")
                
                # Рассчитываем оптимальную высоту букв: пусть высота шрифта подгоняется под высоту рамки
                font_height_mm = max(10.0, bounds.height() * 0.75) # 0.75 — ЧПУ допуск на поля
                font.setPointSizeF(font_height_mm)
                font.setBold(True)
                
                # Добавляем буквы в векторный путь Path относительно левого верхнего угла рамки
                # Смещаем Y на высоту шрифта вниз, так как addText рисует от базовой линии букв
                path.addText(0.0, font_height_mm, font, raw_text)
                
                # Добавляем векторный путь букв на сцену
                item = self.scene().addPath(path, final_pen)
                
                # Важнейший шаг: Применяем физические координаты позиционирования верхнего левого угла
                item.setPos(bounds.topLeft())
                
                # Записываем полный инженерный паспорт текста в кармашек Data
                item.setData(0, {
                    "type": "text", 
                    "raw_text": raw_text, 
                    "font_name": "Arial", 
                    "font_size": font_height_mm, 
                    "depth": 5.0 # Глубина гравировки текста по умолчанию 5мм
                })
                
                # Включаем выбор И мобильность для прецизионного перемещения мышкой
                item.setFlag(item.GraphicsItemFlag.ItemIsSelectable)
                if self.current_tool == "mod_select":
                    item.setFlag(item.GraphicsItemFlag.ItemIsMovable)
                    
                self.save_history_snapshot() # Фиксируем точку в историю отмены Undo
                self.hint_changed.emit("Текст успешно векторизован по формуле Безье и добавлен на чертеж")
            
            # Принудительно завершаем событие клика, чтобы он не провалился в черчение новых фигур
            event.accept()
            return

        # --- СТАНДАРТНЫЙ ОБРАБОТЧИК ОСТАЛЬНЫХ КЛИКОВ МЫШИ ХОЛСТА ---
        if event.button() == Qt.MouseButton.RightButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            show_cad_context_menu(self, event.globalPosition().toPoint(), scene_pos)
        else:
            handle_mouse_press(self, event)
            super().mousePressEvent(event)
    def mouseMoveEvent(self, event: QMouseEvent):
        # Принудительно передаем событие в наш обновленный move.py для онлайн-трекинга
        handle_mouse_move(self, event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        handle_mouse_release(self, event)
        # При отпускании мыши принудительно синхронизируем мобильность деталей под текущий инструмент
        is_select_mode = (self.current_tool == "mod_select")
        for item in self.cad_scene.items():
            if item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
                item.setFlag(item.GraphicsItemFlag.ItemIsMovable, is_select_mode)
        super().mouseReleaseEvent(event)
        self.save_history_snapshot()

    def wheelEvent(self, event: QWheelEvent):
        handle_wheel_zoom(self, event)

    # --- ПЕРЕНАПРАВЛЕНИЕ КЛАВИАТУРЫ В ВАШИ ИЗОЛИРОВАННЫЕ ФАЙЛЫ KEYBOARD_SYSTEM/ ---
    # --- 🔥 ИСПРАВЛЕНО: ЖЕСТКИЙ ПЕРЕХВАТ СТРЕЛОК ДЛЯ СДВИГА ФИГУР КЛАВИАТУРОЙ ---
    def keyPressEvent(self, event: QKeyEvent):
        if handle_global_shortcuts(self, event):
            event.accept()
            return
            
        handle_key_press(self, event)
        
        # Если наш файл key_press.py перехватил стрелку и сделал event.accept(),
        # мы выходим из метода и ЗАПРЕЩАЕМ Qt двигать сам холст!
        if event.isAccepted():
            return
            
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        handle_key_release(self, event)
        
        # Если файл key_release.py обработал отпускание стрелки, блокируем базовый класс
        if event.isAccepted():
            return
            
        super().keyReleaseEvent(event)

    # --- РАБОТА С БУФЕРОМ ОБМЕНА (Ctrl+C / Ctrl+V / Вырезать) ---
    def copy_selected_to_buffer(self):
        self.internal_clipboard = []
        for item in self.cad_scene.selectedItems():
            if item == self.snap_marker:
                continue
            item_data = item.data(0) if item.data(0) else {"type": "unknown", "depth": 0.0}
            copy_pack = {"data": item_data.copy()}
            
            if isinstance(item, QGraphicsLineItem):
                line = item.line()
                copy_pack.update({"x1": line.x1(), "y1": line.y1(), "x2": line.x2(), "y2": line.y2()})
            elif isinstance(item, QGraphicsRectItem):
                r = item.rect()
                copy_pack.update({"x": r.x(), "y": r.y(), "w": r.width(), "h": r.height()})
            elif isinstance(item, QGraphicsPathItem):
                copy_pack.update({"path": QPainterPath(item.path())})
                
            self.internal_clipboard.append(copy_pack)
        self.hint_changed.emit(f"Скопировано элементов в буфер ЧПУ: {len(self.internal_clipboard)}")

    def paste_from_buffer(self):
        if not self.internal_clipboard:
            return
            
        final_pen = QPen(QColor("#E0E0E6"), 1.5, Qt.PenStyle.SolidLine)
        self.cad_scene.clearSelection()
        
        for pack in self.internal_clipboard:
            shift = 10.0
            item_data = pack["data"].copy()
            item = None
            
            if "x1" in pack:
                item = QGraphicsLineItem(pack["x1"] + shift, pack["y1"] - shift, pack["x2"] + shift, pack["y2"] - shift)
                item.setPen(final_pen)
            elif "x" in pack:
                item = QGraphicsRectItem(QRectF(pack["x"] + shift, pack["y"] - shift, pack["w"], pack["h"]))
                item.setPen(final_pen)
            elif "path" in pack:
                trans = QTransform()
                trans.translate(shift, -shift)
                shifted_path = trans.map(pack["path"])
                item = QGraphicsPathItem(shifted_path)
                item.setPen(final_pen)
                
            if item is not None:
                item.setData(0, item_data)
                item.setFlag(item.GraphicsItemFlag.ItemIsSelectable)
                item.setFlag(item.GraphicsItemFlag.ItemIsMovable, (self.current_tool == "mod_select"))
                item.setSelected(True)
                self.cad_scene.addItem(item)
            
        self.hint_changed.emit("Элементы успешно вставлены со смещением +10мм")
        self.save_history_snapshot()

    # --- 🔥 ИСПРАВЛЕНО: ОТРИСОВКА СЕТКИ, ЦВЕТНЫХ ОСЕЙ ЧПУ И МАРКЕРОВ БУКВ X/Y ---
    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QColor("#111114"))
        grid_pen = QPen(QColor("#1F1F24"), 0.5)
        painter.setPen(grid_pen)
        
        # Получаем текущий шаг сетки из нашего CAD-ядра математики
        step = max(1, int(self.cad_engine.grid_size))
        
        left = int(rect.left()) - (int(rect.left()) % step)
        top = int(rect.top()) - (int(rect.top()) % step)
        
        # Направляющие линии координатной сетки с динамическим шагом
        for x in range(left, int(rect.right()), step):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
        for y in range(top, int(rect.bottom()), step):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            
        # ОСЬ X — СТРОГО ЯРКО-КРАСНАЯ
        x_axis_pen = QPen(QColor("#FF4D4D"), 1.2)
        painter.setPen(x_axis_pen)
        painter.drawLine(int(rect.left()), 0, int(rect.right()), 0)
        
        # ОСЬ Y — СТРОГО НЕОНОВО-ЗЕЛЕНАЯ
        y_axis_pen = QPen(QColor("#00FF66"), 1.2)
        painter.setPen(y_axis_pen)
        painter.drawLine(0, int(rect.top()), 0, int(rect.bottom()))
        
        # ШРИФТ ДЛЯ БУКВЕННЫХ МАРКЕРОВ НАПРАВЛЕНИЙ ОСЕЙ ЧПУ
        painter.setPen(QColor("#B0B0B8"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        
        painter.drawText(int(rect.right()) - 40, -10, "X+")
        painter.drawText(10, int(rect.top()) + 25, "Y+")
    # === 🔥 ПОДСИСТЕМА UNDO / REDO / CLEAR ALL (СНИМКИ СОСТОЯНИЯ) ===
    
    def save_history_snapshot(self):
        """Сканирует всю графику на сцене и сохраняет снимок чертежа в историю Undo"""
        snapshot = []
        for item in self.cad_scene.items():
            # Нам нужны только чистовые зафиксированные элементы
            if not item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
                continue
            if item == self.snap_marker:
                continue
                
            item_data = item.data(0) if item.data(0) else {"type": "unknown", "depth": 0.0}
            pack = {"data": item_data.copy()}
            
            if isinstance(item, QGraphicsLineItem):
                line = item.line()
                pack.update({"x1": line.x1(), "y1": line.y1(), "x2": line.x2(), "y2": line.y2()})
            elif isinstance(item, QGraphicsRectItem):
                r = item.rect()
                pack.update({"x": r.x(), "y": r.y(), "w": r.width(), "h": r.height()})
            elif isinstance(item, QGraphicsPathItem):
                pack.update({"path": QPainterPath(item.path())})
                
            snapshot.append(pack)
            
        # Кладем снимок в историю прошлого и очищаем историю будущего (Redo)
        self.undo_stack.append(snapshot)
        # Ограничиваем историю до 50 шагов, чтобы не забивать ОЗУ цехового ПК
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _restore_snapshot(self, snapshot):
        """Внутренний метод: полностью очищает экран и воссоздает геометрию из снимка"""
        # Удаляем все чистовые фигуры, оставляя только неоновый прицел привязки
        for item in list(self.cad_scene.items()):
            if item != self.snap_marker and item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
                self.cad_scene.removeItem(item)
                
        final_pen = QPen(QColor("#E0E0E6"), 1.5, Qt.PenStyle.SolidLine)
        is_select_mode = (self.current_tool == "mod_select")
        
        # Послойно воссоздаем векторы
        for pack in snapshot:
            item = None
            item_data = pack["data"].copy()
            
            if "x1" in pack:
                item = QGraphicsLineItem(pack["x1"], pack["y1"], pack["x2"], pack["y2"])
                item.setPen(final_pen)
            elif "x" in pack:
                # 🔥 ИСПРАВЛЕНО: Ключи синхронизированы с фабрикой сохранения (width и height)
                item = QGraphicsRectItem(QRectF(pack["x"], pack["y"], pack["width"], pack["height"]))
                item.setPen(final_pen)
            elif "path" in pack:
                item = QGraphicsPathItem(pack["path"])
                item.setPen(final_pen)
                
            if item is not None:
                item.setData(0, item_data)
                item.setFlag(item.GraphicsItemFlag.ItemIsSelectable)
                item.setFlag(item.GraphicsItemFlag.ItemIsMovable, is_select_mode)
                self.cad_scene.addItem(item)

    def trigger_undo(self):
        """Отменить последнее действие (Ctrl+Z)"""
        if len(self.undo_stack) > 1: # Один пустой снимок всегда должен оставаться на дне стека
            # Берем текущее состояние и перекидываем его в стек Redo
            current_state = self.undo_stack.pop()
            self.redo_stack.append(current_state)
            
            # Извлекаем предыдущее состояние и накатываем на экран
            prev_state = self.undo_stack[-1]
            self._restore_snapshot(prev_state)
            self.hint_changed.emit("Действие успешно отменено (Undo)")
        else:
            self.hint_changed.emit("История изменений пуста. Отменять нечего.")

    def trigger_redo(self):
        """Вернуть отмененное действие"""
        if self.redo_stack:
            next_state = self.redo_stack.pop()
            self.undo_stack.append(next_state)
            self._restore_snapshot(next_state)
            self.hint_changed.emit("Отмененное действие успешно возвращено (Redo)")
        else:
            self.hint_changed.emit("Будущих действий нет. Возвращать нечего.")

    def trigger_clear_all(self):
        """Полностью стереть весь чертеж (Отменить всё) с возможностью возврата через Undo"""
        # Сначала проверяем, не пустой ли холст и так
        if len(self.cad_scene.items()) > 1: # Больше 1 — значит кроме прицела есть фигуры
            # Очищаем сцену
            for item in list(self.cad_scene.items()):
                if item != self.snap_marker and item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
                    self.cad_scene.removeItem(item)
            # Фиксируем пустоту в историю, чтобы оператор мог вернуть чертеж, если кликнул случайно!
            self.save_history_snapshot()
            self.hint_changed.emit("Чертеж полностью очищен. Вы можете вернуть его, нажав 'Отменить 1 действие'")
