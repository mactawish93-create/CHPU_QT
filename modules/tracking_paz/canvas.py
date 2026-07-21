from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsTextItem
from PyQt6.QtGui import QPainter, QTransform, QMouseEvent, QWheelEvent, QPen, QBrush, QColor, QFont
from PyQt6.QtCore import Qt, QRectF, QLineF

class PazCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Создаем бесконечную математическую сцену для векторов
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # 2. Аппаратная оптимизация под 4 ГБ ОЗУ и встроенную графику
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        # Флаги для панорамирования
        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_y = 0
        
        # 3. НАСТРОЙКА ОСЕЙ ЧПУ ДЛЯ ПАЗИРОВКИ (Y — вправо горизонтально, X — вверх вертикально)
        transform = QTransform()
        transform.scale(1, -1)  # Отражаем вертикаль сцены вверх
        self.setTransform(transform)

    def draw_paz_beam(self, geo: dict):
        """
        Принимает пакет чистой геометрии от модели и рендерит 
        структурный чертеж лежки под любой из выбранных подрежимов.
        """
        self.scene.clear()
        
        physical_length = geo.get("physical_length", 0.0)
        lezhka_x = geo.get("lezhka_x", 2400.0)
        lamels = geo.get("lamels", [])
        slots = geo.get("slots", [])
        germetik = geo.get("germetik", [])
        custom_torecs = geo.get("custom_torecs", [])  # Список ручных торцев
        
        if physical_length <= 0:
            return

        # =========================================================================
        # 🪵 ШАГ 1: ОТРИСОВКА СТРУКТУРЫ ДЕРЕВЯННОГО ЩИТА (ЛАМЕЛИ ПО 135 ММ)
        # =========================================================================
        wood_brush = QBrush(QColor("#25252B"))
        wood_pen = QPen(QColor("#353540"), 1)
        
        prev_x = 0.0
        for current_x in lamels:
            width_lamel = current_x - prev_x
            rect = QRectF(0.0, prev_x, physical_length, width_lamel)
            self.scene.addRect(rect, wood_pen, wood_brush)
            prev_x = current_x
            
        if prev_x < lezhka_x:
            width_lamel = lezhka_x - prev_x
            rect = QRectF(0.0, prev_x, physical_length, width_lamel)
            self.scene.addRect(rect, wood_pen, wood_brush)

        # =========================================================================
        # 🌀 ШАГ 2: УНИВЕРСАЛЬНАЯ ВИЗУАЛИЗАЦИЯ ЧПУ-ВЫБОРОК ОСНОВНЫХ И РУЧНЫХ ПАЗОВ
        # =========================================================================
        slot_brush = QBrush(QColor(0, 168, 255, 60))
        slot_pen = QPen(QColor("#00A8FF"), 1)
        
        for slot in slots:
            # УМНАЯ РАСПАКОВКА: проверяем структуру пакета данных
            if len(slot) == 3:
                # Режим произвольной пазировки: (y_start, y_end, length_x)
                y_start, y_end, length_x = slot
                # Если оператор ввел длину 0 — по умолчанию режем на всю ширину щита
                current_paz_x = length_x if length_x > 0 else lezhka_x
            else:
                # Режим пазировки бани: (y_start, y_end)
                y_start, y_end = slot
                current_paz_x = lezhka_x
                
            paz_width = y_end - y_start
            slot_rect = QRectF(y_start, 0.0, paz_width, current_paz_x)
            self.scene.addRect(slot_rect, slot_pen, slot_brush)

        # =========================================================================
        # 🧪 ШАГ 3: ВИЗУАЛИЗАЦИЯ ПАЗОВ ПОД ГЕРМЕТИК И ПРОИЗВОЛЬНЫХ ТОРЦЕВ
        # =========================================================================
        germ_brush = QBrush(QColor(0, 255, 255, 80))
        germ_pen = QPen(QColor("#00FFFF"), 1)
        
        for y_start, y_end in germetik:
            germ_width = y_end - y_start
            germ_rect = QRectF(y_start, 0.0, germ_width, lezhka_x)
            self.scene.addRect(germ_rect, germ_pen, germ_brush)

        # Отрисовка ручных торцев (внутренних отрезов)
        torec_line_pen = QPen(QColor("#FF4500"), 1.5, Qt.PenStyle.DashLine) # Оранжевый пунктир
        for y_offset, length_x in custom_torecs:
            current_torec_x = length_x if length_x > 0 else lezhka_x
            # Рисуем вертикальный отрезок по X на заданной координате Y
            self.scene.addLine(y_offset, 0.0, y_offset, current_torec_x, torec_line_pen)

        # =========================================================================
        # 🎯 ШАГ 3.5: ОТРИСОВКА ТРАЕКТОРИИ ЗМЕЙКИ (ТОЛЬКО ДЛЯ ВЫРАВНИВАНИЯ СТОЛА)
        # =========================================================================
        plane_snake_lines = geo.get("plane_snake_lines", [])
        # Тонкий неоново-зеленый пунктир для проходов фрезы по плоскости
        snake_pen = QPen(QColor("#00FF66"), 1.2, Qt.PenStyle.DashLine)
        
        for y1, x1, y2, x2 in plane_snake_lines:
            self.scene.addLine(y1, x1, y2, x2, snake_pen)

        # Переход к логике автоматического построения размерных линий (Шаг 4)...
        self._continue_drawing_sizes(geo, physical_length, lezhka_x, slots)
    def _continue_drawing_sizes(self, geo: dict, physical_length: float, lezhka_x: float, slots: list):
        """Продолжение метода отрисовки: построение адаптивных размерных линий ЧПУ"""
        dim_pen = QPen(QColor("#FF9F43"), 1) # Фирменный янтарный цвет для размеров
        
        # Считываем тип геометрии: 0 - Баня, 1 - Ручной, 2 - Калибровка стола
        geom_type = geo.get("slots_geometry_type", 0)
        
        # =========================================================================
        # 🎯 ВАРИАНТ А: ЕСЛИ ПЕРЕД НАМИ РЕЖИМ ВЫРАВНИВАНИЯ ПЛОСКОСТИ (Калибровка)
        # =========================================================================
        if geom_type == 2:
            # Сверху выводим габаритный размер стола по оси Y
            dim_x_top = lezhka_x + 50.0
            self._draw_dimension_line(0.0, physical_length, dim_x_top, f"ДЛИНА ЗОНЫ Y: {physical_length:.0f} мм", dim_pen, is_top=True, is_bold=True)
            
            # Снизу выводим габаритную ширину стола по оси X
            dim_x_total = -60.0
            self._draw_dimension_line(0.0, lezhka_x, dim_x_total, f"ШИРИНА ЗОНЫ X: {lezhka_x:.0f} мм", dim_pen, is_top=False, is_bold=True)
            
            # Мгновенно фокусируем камеру цехового ПК строго на габаритах жертвенного стола!
            self.scene.setSceneRect(-100, -120, physical_length + 200, lezhka_x + 240)
            self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
            return

        # =========================================================================
        # 🪵 ВАРИАНТ Б: ШТАТНЫЙ РЕЖИМ (ДЛЯ БАНИ И ПРОИЗВОЛЬНЫХ ПАЗОВ)
        # =========================================================================
        # --- УРОВЕНЬ А (ВЕРХНИЙ): Размеры комнат и выпусков ---
        dim_x_top = lezhka_x + 50.0
        
        # Безопасно собираем опорные точки переходов по Y
        top_points = [0.0]
        for slot in slots:
            # ИСПРАВЛЕНО: Корректно распаковываем кортеж в зависимости от его длины (2 или 3 элемента)
            y_start = slot[0]
            y_end = slot[1]
            top_points.append(y_start)
            top_points.append(y_end)
        top_points.append(physical_length)
        top_points = sorted(list(set(top_points)))
        
        for i in range(len(top_points) - 1):
            y1 = top_points[i]
            y2 = top_points[i+1]
            segment_len = y2 - y1
            
            if segment_len > 0.1:
                is_inside_slot = False
                for slot in slots:
                    s_start = slot[0]
                    s_end = slot[1]
                    if abs(s_start - y1) < 0.1 and abs(s_end - y2) < 0.1:
                        is_inside_slot = True
                        break
                if not is_inside_slot:
                    self._draw_dimension_line(y1, y2, dim_x_top, f"{segment_len:.0f}", dim_pen, is_top=True)

        # --- УРОВЕНЬ Б (ПЕРВЫЙ НИЖНИЙ): Размеры пазов ---
        dim_x_slots = -40.0
        for slot in slots:
            y_start = slot[0]
            y_end = slot[1]
            paz_width = y_end - y_start
            self._draw_dimension_line(y_start, y_end, dim_x_slots, f"{paz_width:.0f}", dim_pen, is_top=False)

        # --- УРОВЕНЬ В (ВТОРОЙ НИЖНИЙ): Общий размер заготовки ---
        dim_x_total = -90.0
        self._draw_dimension_line(0.0, physical_length, dim_x_total, f"ОБЩАЯ ДЛИНА: {physical_length:.0f} мм", dim_pen, is_top=False, is_bold=True)

        # Автофокус камеры под длинный брус
        self.scene.setSceneRect(-100, -150, physical_length + 200, lezhka_x + 300)
        self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _draw_dimension_line(self, y1: float, y2: float, x_coord: float, text: str, pen: QPen, is_top=True, is_bold=False):
        """Внутренний CAD-метод: строит горизонтальную линию размера, стрелочки и крупный текст"""
        self.scene.addLine(y1, x_coord, y2, x_coord, pen)
        
        tick_size = 6.0
        self.scene.addLine(y1, x_coord - tick_size, y1, x_coord + tick_size, pen)
        self.scene.addLine(y2, x_coord - tick_size, y2, x_coord + tick_size, pen)
        
        arrow_w = 12.0
        arrow_h = 3.5
        self.scene.addLine(y1, x_coord, y1 + arrow_w, x_coord + arrow_h, pen)
        self.scene.addLine(y1, x_coord, y1 + arrow_w, x_coord - arrow_h, pen)
        self.scene.addLine(y2, x_coord, y2 - arrow_w, x_coord + arrow_h, pen)
        self.scene.addLine(y2, x_coord, y2 - arrow_w, x_coord - arrow_h, pen)

        text_item = QGraphicsTextItem(text)
        font = QFont("Segoe UI")
        font.setBold(is_bold)
        font.setPixelSize(65 if is_bold else 45)
        text_item.setFont(font)
        text_item.setDefaultTextColor(QColor("#E0E0E6"))
        
        t = QTransform()
        t.scale(1, -1)
        text_item.setTransform(t)
        self.scene.addItem(text_item)
        
        text_w = text_item.boundingRect().width()
        text_h = text_item.boundingRect().height()
        center_y = (y1 + y2) / 2.0 - (text_w / 2.0)
        
        if is_top:
            center_x = x_coord + text_h + 18.0
        else:
            center_x = x_coord - 18.0
            
        text_item.setPos(center_y, center_x)

    # =========================================================================
    # 🖐 ЛОГИКА КАД-НАВИГАЦИИ (Панорамирование правой кнопкой мыши)
    # =========================================================================
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self._is_panning = True
            self._pan_start_x = event.position().x()
            self._pan_start_y = event.position().y()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            dx = event.position().x() - self._pan_start_x
            dy = event.position().y() - self._pan_start_y
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(dx))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(dy))
            self._pan_start_x = event.position().x()
            self._pan_start_y = event.position().y()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # =========================================================================
    # 🔍 УМНЫЙ ЗУМ (Масштабирование колесиком мыши в точку курсора)
    # =========================================================================
    def wheelEvent(self, event: QWheelEvent):
        zoom_factor = 1.15
        if event.angleDelta().y() < 0:
            zoom_factor = 1.0 / zoom_factor
        current_zoom = self.transform().m11()
        if (current_zoom < 0.05 and zoom_factor < 1.0) or (current_zoom > 100.0 and zoom_factor > 1.0):
            return
        self.scale(zoom_factor, zoom_factor)
        event.accept()
