import math
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsTextItem, QGraphicsPathItem
from PyQt6.QtGui import QPainter, QTransform, QMouseEvent, QWheelEvent, QPen, QBrush, QColor, QFont, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPointF

class GCodeCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. Создаем бесконечную математическую сцену для трекинга перемещений
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
        
        # Флаги для панорамирования правой кнопкой мыши
        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_y = 0
        
        # Переменные для динамического трекера-перекрестия фрезы
        self.tool_marker_x = None
        self.tool_marker_y = None
        self.marker_items = []
        
        # 3. НАСТРОЙКА ОСЕЙ СТАНКА ЧПУ (X — вправо горизонтально, Y — вверх вертикально)
        transform = QTransform()
        transform.scale(1, -1)  # Отражаем вертикаль сцены, чтобы ось Y смотрела вверх
        self.setTransform(transform)

    def draw_gcode_trajectory(self, blocks: list, min_x: float, max_x: float, min_y: float, max_y: float):
        """
        Принимает массив предобработанных геометрических блоков от контроллера
        и вычерчивает полный неоновый след траектории фрезы.
        """
        self.scene.clear()
        self.marker_items = [] # Очищаем старые ссылки на курсор шпинделя
        
        # =========================================================================
        # 📐 ШАГ 1: ОТРИСОВКА СИСТЕМЫ КООРДИНАТ СТАНКА (ОСИ +X И +Y)
        # =========================================================================
        axis_len = 300.0
        # Ось X — красная неоновая стрелка
        x_pen = QPen(QColor("#FF4D4D"), 1.5)
        self.scene.addLine(0.0, 0.0, axis_len, 0.0, x_pen)
        self.scene.addLine(axis_len, 0.0, axis_len - 10.0, 3.5, x_pen)
        self.scene.addLine(axis_len, 0.0, axis_len - 10.0, -3.5, x_pen)
        
        # Ось Y — зеленая неоновая стрелка
        y_pen = QPen(QColor("#2ECC71"), 1.5)
        self.scene.addLine(0.0, 0.0, 0.0, axis_len, y_pen)
        self.scene.addLine(0.0, axis_len, 3.5, axis_len - 10.0, y_pen)
        self.scene.addLine(0.0, axis_len, -3.5, axis_len - 10.0, y_pen)
        
        # Буквенные обозначения осей с контр-трансформацией
        font_axis = QFont("Segoe UI", 12, QFont.Weight.Bold)
        t_text = QTransform()
        t_text.scale(1, -1)
        
        txt_x = QGraphicsTextItem("X")
        txt_x.setFont(font_axis)
        txt_x.setDefaultTextColor(QColor("#FF4D4D"))
        txt_x.setTransform(t_text)
        self.scene.addItem(txt_x)
        txt_x.setPos(axis_len + 5.0, txt_x.boundingRect().height() / 2.0)
        
        txt_y = QGraphicsTextItem("Y")
        txt_y.setFont(font_axis)
        txt_y.setDefaultTextColor(QColor("#2ECC71"))
        txt_y.setTransform(t_text)
        self.scene.addItem(txt_y)
        txt_y.setPos(-txt_y.boundingRect().width() / 2.0, axis_len + txt_y.boundingRect().height() + 5.0)

        # =========================================================================
        # 🪵 ШАГ 2: АВТОМАТИЧЕСКИЙ РАСЧЕТ И ВЫВОД ГАБАРИТОВ ЗАГОТОВКИ В ЦЕХУ
        # =========================================================================
        width_wood = max_x - min_x
        height_wood = max_y - min_y
        
        if width_wood > 10.0 and height_wood > 10.0:
            # Отрисовываем тонкий серый матовый прямоугольник габаритов материала
            box_pen = QPen(QColor("#353540"), 1, Qt.PenStyle.DashLine)
            self.scene.addRect(min_x, min_y, width_wood, height_wood, box_pen, QBrush(Qt.BrushStyle.NoBrush))
            
            # Текст габаритных размеров УП в левом верхнем углу холста
            size_text = QGraphicsTextItem(f"ГАБАРИТЫ ДЕТАЛИ: {width_wood:.1f} x {height_wood:.1f} мм\n"
                                           f"МИН КООРДИНАТЫ: X={min_x:.1f} Y={min_y:.1f}\n"
                                           f"МАКС КООРДИНАТЫ: X={max_x:.1f} Y={max_y:.1f}")
            font_size = QFont("Segoe UI", 11)
            font_size.setBold(True)
            size_text.setFont(font_size)
            size_text.setDefaultTextColor(QColor("#9B5DE5")) # Цветовая привязка к терминалу УП
            size_text.setTransform(t_text)
            self.scene.addItem(size_text)
            
            # Позиционируем инфо-блок с отступом от левого верхнего угла детали
            size_text.setPos(min_x, max_y + size_text.boundingRect().height() + 25.0)

        # =========================================================================
        # 🌀 ШАГ 3: РЕНДЕРИНГ ТРАЕКТОРИИ (ПЕРЕЛЕТЫ И РАБОЧИЕ ХОДЫ)
        # =========================================================================
        g0_pen = QPen(QColor("#FF00FF"), 1, Qt.PenStyle.DotLine) # Холостые перелеты по воздуху — фиолетовый пунктир
        g1_pen = QPen(QColor("#00FF66"), 1.2, Qt.PenStyle.SolidLine) # Рабочий рез — неоново-зеленый
        
        for block in blocks:
            b_type = block["type"]
            pen = g0_pen if b_type == "G0" else g1_pen
            
            if block["geom_type"] == "line":
                self.scene.addLine(block["x1"], block["y1"], block["x2"], block["y2"], pen)
            elif block["geom_type"] == "arc":
                # Для дуг G2/G3 используем QPainterPath, чтобы обводы были идеально плавными
                arc_path = QPainterPath()
                arc_path.moveTo(block["x1"], block["y1"])
                # Qt arcTo принимает прямоугольник, углы старта и sweep. На следующем шаге мы пропишем их рендеринг...
                pass

        # Переход к логике динамического перекрестия маркера и CAD-навигации мыши...
        self._continue_drawing_gcode(min_x, max_x, min_y, max_y)
    def _continue_drawing_gcode(self, min_x: float, max_x: float, min_y: float, max_y: float):
        """Продолжение метода отрисовки: автофокус камеры"""
        # Считаем габариты для центрирования камеры
        width_wood = max_x - min_x
        height_wood = max_y - min_y
        
        # Если траектория пустая — ставим стартовый цеховой квадрат
        if width_wood <= 1.0 or height_wood <= 1.0:
            min_x, max_x, min_y, max_y = -300.0, 300.0, -300.0, 300.0
            width_wood, height_wood = 600.0, 600.0

        # Автофокус камеры под габариты заготовки
        self.scene.setSceneRect(min_x - 150, min_y - 200, width_wood + 300, height_wood + 400)
        self.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def update_tool_marker(self, x: float, y: float):
        """
        🔥 ДИНАМИЧЕСКИЙ ТРЕКЕР ФРЕЗЫ
        Вызывается контроллером при перемещении стрелочек на клавиатуре.
        Удаляет старый курсор и рисует яркое оранжевое перекрестие шпинделя в точке X/Y.
        """
        # 1. Стираем старый маркер
        for item in self.marker_items:
            try:
                self.scene.removeItem(item)
            except:
                pass
        self.marker_items.clear()
        
        if x is None or y is None:
            return
            
        # 2. Строим яркое оранжевое перекрестие с прицелом (#FF9F43)
        marker_pen = QPen(QColor("#FF9F43"), 1.5, Qt.PenStyle.SolidLine)
        size = 35.0 # Размер перекрестия в миллиметрах
        
        # Горизонтальная линия прицела
        line_h = self.scene.addLine(x - size, y, x + size, y, marker_pen)
        # Вертикальная линия прицела
        line_v = self.scene.addLine(x, y - size, x, y + size, marker_pen)
        
        # Маленький центрирующий кружок фрезы
        circle = self.scene.addEllipse(x - 6.0, y - 6.0, 12.0, 12.0, marker_pen, QBrush(Qt.BrushStyle.NoBrush))
        
        # Запоминаем ссылки, чтобы стереть их при следующем шаге стрелочки
        self.marker_items.extend([line_h, line_v, circle])

    # =========================================================================
    # 🖐 ЛОГИКА КАД-НАВИГАЦИИ (Панорамирование ПРАВОЙ кнопкой мыши или КОЛЕСИКОМ СКМ)
    # =========================================================================
    def mousePressEvent(self, event: QMouseEvent):
        # Реагируем как на ПРАВУЮ кнопку, так и на СРЕДНЮЮ кнопку (зажатие колесика мыши)
        if event.button() in [Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton]:
            self._is_panning = True
            self._pan_start_x = event.position().x()
            self._pan_start_y = event.position().y()
            self.setCursor(Qt.CursorShape.ClosedHandCursor) # Меняем курсор на руку
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            dx = event.position().x() - self._pan_start_x
            dy = event.position().y() - self._pan_start_y
            
            # Сдвигаем скрытые скроллбары сцены вслед за рукой оператора
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(dx))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(dy))
            
            self._pan_start_x = event.position().x()
            self._pan_start_y = event.position().y()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        # Сбрасываем захват, если отпущена любая из управляющих кнопок панорамирования
        if event.button() in [Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton]:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor) # Возвращаем стандартную стрелочку
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
