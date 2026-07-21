import math
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsTextItem
from PyQt6.QtGui import QPainter, QTransform, QMouseEvent, QWheelEvent, QPen, QBrush, QColor, QFont
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPolygonF

class DisksCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Создаем бесконечную математическую сцену для векторов
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # 2. Аппаратная оптимизация под цеховой ПК
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        # Флаги для панорамирования (ПКМ или СКМ-колесико)
        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_y = 0
        
        # 3. НАСТРОЙКА ОСЕЙ ЧПУ ДЛЯ ДИСКОВ (X — вправо горизонтально, Y — вверх вертикально)
        transform = QTransform()
        transform.scale(1, -1)  # Отражаем вертикаль сцены, чтобы ось Y смотрела вверх
        self.setTransform(transform)

    def draw_disks_layout(self, geo: dict):
        """
        Принимает пакет чистой геометрии от модели и рендерит 
        структурный чертеж диска с шахматными размерами ламелей.
        """
        self.scene.clear()
        
        radius = geo.get("radius", 0.0)
        diameter = geo.get("diameter", 2000.0)
        lamels = geo.get("lamels", [])
        main_mode_idx = geo.get("main_mode_idx", 0)
        shape_instance = geo.get("shape_instance") # Получаем объект активной формы бани
        
        if radius <= 0 or not shape_instance:
            return

        # =========================================================================
        # 🪵 ШАГ 1: ОТРИСОВКА ВЕРТИКАЛЬНЫХ ДОСОК-ЛАМЕЛЕЙ ПО 135 ММ
        # =========================================================================
        if lamels:
            wood_brush = QBrush(QColor("#25252B"))  # Матовая темная текстура доски
            wood_pen = QPen(QColor("#353540"), 1)   # Тонкий шов стыка ламелей
            
            for lamel in lamels:
                x1 = lamel["x_start"]
                x2 = lamel["x_end"]
                length = lamel["length"]
                
                half_len = length / 2.0
                rect = QRectF(x1, -half_len, x2 - x1, length)
                self.scene.addRect(rect, wood_pen, wood_brush)

        # =========================================================================
        # 🎯 ШАГ 2: ДЕЛИГИРОВАНИЕ ОТРИСОВКИ КОНТУРА В СУБМОДУЛЬ ФОРМЫ (SHAPES)
        # =========================================================================
        contour_pen = QPen(QColor("#FF9F43"), 2, Qt.PenStyle.SolidLine) # Янтарный контур заготовки
        shape_instance.draw_contour(self.scene, contour_pen) # Объект сам рисует свой круг или Квадро-бочку!

        # =========================================================================
        # 👁️ ШАГ 2.5: ОТОБРАЖЕНИЕ ТЕКУЩЕГО ДИАМЕТРА ПО ЦЕНТРУ ЧЕРТЕЖА
        # =========================================================================
        if lamels: # Выводим Ø только если есть чертеж ламелей (не на заглушках)
            center_label = f"Ø {diameter:.0f} мм" if main_mode_idx == 0 else f"КВАДРО {diameter:.0f} мм"
            center_text = QGraphicsTextItem(center_label)
            font_center = QFont("Segoe UI", 32)
            font_center.setBold(True)
            center_text.setFont(font_center)
            center_text.setDefaultTextColor(QColor(255, 159, 67, 45)) # Полупрозрачный брендовый янтарный
            
            t_center = QTransform()
            t_center.scale(1, -1)
            center_text.setTransform(t_center)
            self.scene.addItem(center_text)
            
            cx = -center_text.boundingRect().width() / 2.0
            cy = center_text.boundingRect().height() / 2.0
            center_text.setPos(cx, cy)

        # =========================================================================
        # 🚪 ШАГ 3: ВИЗУАЛИЗАЦИЯ ДВЕРНОГО ПРОЕМА И ЧЕТВЕРТИ (ИЗ ПРОЦЕССОРА ДВЕРЕЙ)
        # =========================================================================
        if geo.get("has_door"):
            outer_pts = geo.get("door_outer", [])
            inner_pts = geo.get("door_inner", [])
            
            outer_pen = QPen(QColor("#FF4500"), 1.5, Qt.PenStyle.DashLine)
            outer_poly = QPolygonF([QPointF(x, y) for x, y in outer_pts])
            self.scene.addPolygon(outer_poly, outer_pen, QBrush(Qt.BrushStyle.NoBrush))
            
            inner_pen = QPen(QColor("#00FFFF"), 1.0, Qt.PenStyle.DotLine)
            inner_poly = QPolygonF([QPointF(x, y) for x, y in inner_pts])
            self.scene.addPolygon(inner_poly, inner_pen, QBrush(Qt.BrushStyle.NoBrush))

        # Построение размерной шахматной сетки ламелей
        if lamels:
            self._continue_drawing_disks_sizes(geo, radius, lamels)
        else:
            # Если это пустая заглушка — ставим дефолтный фокус камеры
            self.scene.setSceneRect(-200, -200, 400, 400)
            self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
    def _continue_drawing_disks_sizes(self, geo: dict, radius: float, lamels: list):
        """Построение внешней шахматной гребенки и внутренних мятных размеров обрезков"""
        dim_pen = QPen(QColor("#FF9F43"), 1)
        has_door = geo.get("has_door", False)
        y_door_top = geo.get("y_door_top", 886.0)
        y_door_bottom = geo.get("y_door_bottom", -886.0)
        
        t = QTransform()
        t.scale(1, -1)
        
        for index, lamel in enumerate(lamels):
            x1 = lamel["x_start"]
            x2 = lamel["x_end"]
            length = lamel["length"]
            is_cut = lamel.get("is_cut", False)
            top_len = lamel.get("top_len", 0.0)
            bottom_len = lamel.get("bottom_len", 0.0)
            
            center_x = (x1 + x2) / 2.0
            half_len = length / 2.0
            is_even = (index % 2 == 0)
            
            # 📐 1. ВНЕШНЯЯ ШАХМАТНАЯ ГРЕБЕНКА (ОБЩИЕ ГАБАРИТЫ ДОСОК)
            if is_even:
                y_base = half_len + 15.0
                y_dim = radius + 80.0
            else:
                y_base = -half_len - 15.0
                y_dim = -radius - 80.0
                
            self.scene.addLine(center_x, y_base, center_x, y_dim, dim_pen)
            self.scene.addLine(center_x - 5.0, y_dim, center_x + 5.0, y_dim, dim_pen)
            
            arrow_w, arrow_h = 3.5, 10.0
            if is_even:
                self.scene.addLine(center_x, y_dim, center_x - arrow_w, y_dim - arrow_h, dim_pen)
                self.scene.addLine(center_x, y_dim, center_x + arrow_w, y_dim - arrow_h, dim_pen)
            else:
                self.scene.addLine(center_x, y_dim, center_x - arrow_w, y_dim + arrow_h, dim_pen)
                self.scene.addLine(center_x, y_dim, center_x + arrow_w, y_dim + arrow_h, dim_pen)

            text_item = QGraphicsTextItem(f"{length:.0f}")
            font_ext = QFont("Segoe UI", 42, QFont.Weight.Bold)
            text_item.setFont(font_ext)
            text_item.setDefaultTextColor(QColor("#E0E0E6"))
            text_item.setTransform(t)
            self.scene.addItem(text_item)
            
            text_w = text_item.boundingRect().width()
            text_h = text_item.boundingRect().height()
            pos_x = center_x - (text_w / 2.0)
            pos_y = (y_dim + text_h + 10.0) if is_even else (y_dim - 10.0)
            text_item.setPos(pos_x, pos_y)

            # 🪓 2. ВНУТРЕННИЕ МЯТНЫЕ РАЗМЕРЫ ОБРЕЗКОВ ДЛЯ БЕЗОТХОДНОГО РАСКРОЯ
            if has_door and is_cut:
                font_int = QFont("Segoe UI", 32, QFont.Weight.Bold)
                mint_color = QColor("#2ECC71")

                if top_len > 10.0:
                    text_top = QGraphicsTextItem(f"{top_len:.0f}")
                    text_top.setFont(font_int)
                    text_top.setDefaultTextColor(mint_color)
                    text_top.setTransform(t)
                    self.scene.addItem(text_top)
                    tw_t, th_t = text_top.boundingRect().width(), text_top.boundingRect().height()
                    center_y_top = (half_len + y_door_top) / 2.0
                    text_top.setPos(center_x - (tw_t / 2.0), center_y_top + (th_t / 2.0))

                if bottom_len > 10.0:
                    text_bot = QGraphicsTextItem(f"{bottom_len:.0f}")
                    text_bot.setFont(font_int)
                    text_bot.setDefaultTextColor(mint_color)
                    text_bot.setTransform(t)
                    self.scene.addItem(text_bot)
                    tw_b, th_b = text_bot.boundingRect().width(), text_bot.boundingRect().height()
                    center_y_bot = (-half_len + y_door_bottom) / 2.0
                    text_bot.setPos(center_x - (tw_b / 2.0), center_y_bot + (th_b / 2.0))

        # Автофокус камеры под габариты заготовки
        self.scene.setSceneRect(-radius - 150, -radius - 200, radius * 2.0 + 300, radius * 2.0 + 400)
        self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    # --- CAD-НАВИГАЦИЯ МЫШИ (Панорамирование ПРАВОЙ кнопкой или зажатием колесика СКМ) ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() in [Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton]:
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
        if event.button() in [Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton]:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        zoom_factor = 1.15
        if event.angleDelta().y() < 0:
            zoom_factor = 1.0 / zoom_factor
        current_zoom = self.transform().m11()
        if (current_zoom < 0.05 and zoom_factor < 1.0) or (current_zoom > 100.0 and zoom_factor > 1.0):
            return
        self.scale(zoom_factor, zoom_factor)
        event.accept()
