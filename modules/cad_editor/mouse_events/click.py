from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem, QGraphicsPathItem
from PyQt6.QtGui import QPen, QColor

def handle_mouse_press(canvas, event):
    scene_pos = canvas.mapToScene(event.position().toPoint())
    
    # 1. НАЖАТИЕ СРЕДНЕЙ КНОПКИ МЫШИ (СКМ) — РЕЖИМ РУКА ДЛЯ ДВИЖЕНИЯ ЭКРАНА
    if event.button() == Qt.MouseButton.MiddleButton:
        canvas.setDragMode(canvas.DragMode.ScrollHandDrag)
        fake_event = event.__class__(
            event.type(), event.position(), event.globalPosition(),
            Qt.MouseButton.LeftButton, event.buttons() | Qt.MouseButton.LeftButton, event.modifiers()
        )
        super(canvas.__class__, canvas).mousePressEvent(fake_event)
        canvas.hint_changed.emit("Режим 'Рука': Перетаскивание холста")
        return

    # Если кликнули не левой кнопкой мыши, выходим (ПКМ обработается отдельно)
    if event.button() != Qt.MouseButton.LeftButton:
        return

    # Вычисляем точку привязки с учетом объектного снаппинга по Ctrl из CadEngine
    canvas.start_scene_pos, snap_msg = canvas.cad_engine.calculate_snap_point(
        scene_pos, canvas.scene().items(), canvas.ctrl_pressed
    )
    canvas.hint_changed.emit(snap_msg)

    # 2. ИНСТРУМЕНТ "ЛАСТИК" (УНИВЕРСАЛЬНЫЙ СЕГМЕНТНЫЙ НОЖ)
    if canvas.current_tool == "draw_eraser":
        _handle_universal_eraser_cut(canvas, canvas.start_scene_pos)
        return

    # 3. ИНСТРУМЕНТ "КРИВАЯ ЛИНИЯ" (DRAW_CURVE)
    if canvas.current_tool == "draw_curve":
        if not hasattr(canvas, "curve_stage") or canvas.curve_stage == 0:
            canvas.is_drawing = True
            canvas.curve_stage = 1  
            canvas.curve_start_pt = canvas.start_scene_pos
            
            pen = QPen(QColor("#00A8FF"), 1.5, Qt.PenStyle.DashLine)
            canvas.temp_item = QGraphicsLineItem(
                canvas.curve_start_pt.x(), canvas.curve_start_pt.y(),
                canvas.curve_start_pt.x(), canvas.curve_start_pt.y()
            )
            canvas.temp_item.setPen(pen)
            canvas.scene().addItem(canvas.temp_item)
        
        elif canvas.curve_stage == 2:
            canvas.is_drawing = False
            canvas.curve_stage = 0  
            
            if canvas.temp_item and hasattr(canvas.temp_item, "path"):
                saved_path = canvas.temp_item.path()
                canvas.scene().removeItem(canvas.temp_item)
                canvas.temp_item = None
                
                final_pen = QPen(QColor("#E0E0E6"), 1.5, Qt.PenStyle.SolidLine)
                item = canvas.scene().addPath(saved_path, final_pen)
                item.setData(0, {"type": "curve", "depth": 0.0})
                item.setFlag(item.GraphicsItemFlag.ItemIsSelectable)
                canvas.scene().addItem(item)
                canvas.hint_changed.emit("Кривая линия Безье успешно добавлена на чертеж")
        return

    # 4. 🔥 ВНЕДРЕНО: НАЧАЛО НАТЯЖЕНИЯ РАМКИ ДЛЯ ТЕКСТА И ОСТАЛЬНЫХ ФИГУР
    # Добавили "text_area" в список. Его фантомом тоже будет прямоугольник
    if canvas.current_tool in ["line", "rect", "draw_circle", "draw_rhomb", "draw_poly", "text_area"]:
        canvas.is_drawing = True
        pen = QPen(QColor("#00A8FF"), 1.5, Qt.PenStyle.DashLine)
        
        if canvas.current_tool == "line":
            canvas.temp_item = QGraphicsLineItem(
                canvas.start_scene_pos.x(), canvas.start_scene_pos.y(),
                canvas.start_scene_pos.x(), canvas.start_scene_pos.y()
            )
        elif canvas.current_tool in ["rect", "text_area"]:
            # Текстовая область использует прямоугольный фантом
            canvas.temp_item = QGraphicsRectItem(canvas.start_scene_pos.x(), canvas.start_scene_pos.y(), 0, 0)
        elif canvas.current_tool in ["draw_circle", "draw_rhomb", "draw_poly"]:
            canvas.temp_item = QGraphicsPathItem()
            canvas.poly_sides = 6
            
        canvas.temp_item.setPen(pen)
        canvas.scene().addItem(canvas.temp_item)

def _handle_universal_eraser_cut(canvas, click_pos: QPointF):
    """Оставляем неизменным прошлый отлаженный алгоритм ластика"""
    items = canvas.scene().items(QRectF(click_pos.x() - 10, click_pos.y() - 10, 20, 20))
    final_pen = QPen(QColor("#E0E0E6"), 1.5, Qt.PenStyle.SolidLine)
    
    for item in items:
        if not item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
            continue
        old_data = item.data(0) if item.data(0) else {"depth": 0.0}
        target_depth = old_data.get("depth", 0.0)

        if isinstance(item, QGraphicsLineItem):
            line = item.line()
            canvas.scene().removeItem(item)
            _slice_line_segment(canvas, line.p1(), line.p2(), click_pos, target_depth, final_pen)
            break
        elif isinstance(item, QGraphicsRectItem):
            rect = item.rect()
            canvas.scene().removeItem(item)
            edges = [
                (rect.topLeft(), rect.topRight()), (rect.topRight(), rect.bottomRight()),
                (rect.bottomRight(), rect.bottomLeft()), (rect.bottomLeft(), rect.topLeft())
            ]
            for p1, p2 in edges:
                import math
                line_len = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
                if abs((math.hypot(click_pos.x() - p1.x(), click_pos.y() - p1.y()) + math.hypot(click_pos.x() - p2.x(), click_pos.y() - p2.y())) - line_len) < 2.0:
                    _slice_line_segment(canvas, p1, p2, click_pos, target_depth, final_pen)
                else:
                    new_line = canvas.scene().addLine(p1.x(), p1.y(), p2.x(), p2.y(), final_pen)
                    new_line.setData(0, {"type": "line", "depth": target_depth})
                    new_line.setFlag(new_line.GraphicsItemFlag.ItemIsSelectable)
            break