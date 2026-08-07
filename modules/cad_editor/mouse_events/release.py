from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem, QGraphicsPathItem, QTextEdit, QGraphicsProxyWidget
from PyQt6.QtGui import QPen, QColor, QFont, QPainterPath

def handle_mouse_release(canvas, event):
    if event.button() == Qt.MouseButton.MiddleButton:
        canvas.setDragMode(canvas.DragMode.NoDrag)
        return

    if event.button() != Qt.MouseButton.LeftButton:
        return

    # === ОСОБЫЙ СЦЕНАРИЙ: ОТПУСКАНИЕ МЫШИ ДЛЯ КРИВОЙ БЕЗЬЕ ===
    if canvas.current_tool == "draw_curve" and hasattr(canvas, "curve_stage"):
        if canvas.curve_stage == 1:
            canvas.curve_stage = 2
            if canvas.temp_item:
                canvas.scene().removeItem(canvas.temp_item)
                canvas.temp_item = None
                
            canvas.temp_item = QGraphicsPathItem()
            pen = QPen(QColor("#00A8FF"), 1.5, Qt.PenStyle.DashLine)
            canvas.temp_item.setPen(pen)
            canvas.scene().addItem(canvas.temp_item)
            canvas.hint_changed.emit("Крайние точки зафиксированы. Двигайте мышь для настройки изгиба дуги.")
            event.accept()
            return

    # === СТАНДАРТНЫЙ СЦЕНАРИЙ ФИКСАЦИИ ГЕОМЕТРИИ ===
    if not canvas.is_drawing:
        return
        
    canvas.is_drawing = False
    saved_path = None
    if canvas.temp_item and hasattr(canvas.temp_item, "path"):
        saved_path = canvas.temp_item.path()

    # Запоминаем габариты рамки-фантома до её удаления с экрана
    rect_bounds = None
    if canvas.temp_item and canvas.current_tool == "text_area":
        rect_bounds = canvas.temp_item.rect()

    if canvas.temp_item:
        canvas.scene().removeItem(canvas.temp_item)
        canvas.temp_item = None

    final_pen = QPen(QColor("#E0E0E6"), 1.5, Qt.PenStyle.SolidLine)
    end_pos = canvas.snapped_current_pos

    if canvas.current_tool == "line":
        end_pos = canvas.cad_engine.apply_ortho_45(canvas.start_scene_pos, end_pos, canvas.shift_pressed)

    dx = end_pos.x() - canvas.start_scene_pos.x()
    dy = end_pos.y() - canvas.start_scene_pos.y()

    # Заводской допуск от микрокликов (для текста сделаем проверку отдельно)
    if abs(dx) < 0.5 and abs(dy) < 0.5 and canvas.current_tool not in ["draw_eraser", "text_area"]:
        return

    # 🔥 ВНЕДРЕНО: СОЗДАНИЕ ИНТЕРАКТИВНОГО ПОЛЯ ВВОДА ТЕКСТА QTEXTEDIT ПРЯМО В РАМКЕ
    if canvas.current_tool == "text_area":
        if rect_bounds is None or rect_bounds.width() < 10 or rect_bounds.height() < 10:
            # Если оператор просто кликнул мимоходом без растягивания, даем дефолтный габарит рамки
            rect_bounds = QRectF(canvas.start_scene_pos.x(), canvas.start_scene_pos.y(), 250, 100)

        # Создаем стандартный многострочный виджет ввода текста
        editor_widget = QTextEdit()
        # Стилизуем его под темную тему, делаем рамку синей, а фон глубоким графитовым
        editor_widget.setStyleSheet("""
            QTextEdit {
                background-color: #111114;
                color: #FFFFFF;
                border: 2px solid #00A8FF;
                border-radius: 4px;
                font-family: 'Arial';
                font-size: 14px;
            }
        """)
        
        # Задаем физический размер виджета в соответствии с натянутой мышкой рамкой
        editor_widget.resize(int(rect_bounds.width()), int(rect_bounds.height()))
        
        # Интегрируем стандартный виджет внутрь векторной CAD-сцены через специальный Прокси-слой Qt
        proxy = canvas.scene().addWidget(editor_widget)
        # Устанавливаем точную позицию верхнего левого угла рамки
        proxy.setPos(rect_bounds.topLeft())
        proxy.setZValue(5000) # Поле ввода всегда поверх всех чертежей бани
        
        # Передаем фокус клавиатуры цехового ПК прямо внутрь поля
        editor_widget.setFocus()
        
        # Сохраняем ссылки в холст, чтобы к ним можно было обратиться при клике мимо
        canvas.active_text_editor = editor_widget
        canvas.active_text_proxy = proxy
        canvas.active_text_bounds = rect_bounds
        
        canvas.hint_changed.emit("Введите текст маркировки бруса. Кликните мышкой ЛКМ в пустое место холста для фиксации.")
        return

    # ЗАПЕКАНИЕ ОСТАЛЬНЫХ СТАНДАРТНЫХ ФИГУР НА СЦЕНУ
    item = None

    if canvas.current_tool == "line":
        item = QGraphicsLineItem(canvas.start_scene_pos.x(), canvas.start_scene_pos.y(), end_pos.x(), end_pos.y())
        item.setPen(final_pen)
        item.setData(0, {"type": "line", "depth": 0.0}) 
        
    elif canvas.current_tool == "rect":
        if canvas.shift_pressed:
            side = max(abs(dx), abs(dy))
            dx = side if dx >= 0 else -side
            dy = side if dy >= 0 else -side
        x = min(canvas.start_scene_pos.x(), canvas.start_scene_pos.x() + dx)
        y = min(canvas.start_scene_pos.y(), canvas.start_scene_pos.y() + dy)
        
        item = QGraphicsRectItem(QRectF(x, y, abs(dx), abs(dy)))
        item.setPen(final_pen)
        item.setData(0, {"type": "rect", "depth": 0.0})
        
    elif canvas.current_tool in ["draw_circle", "draw_rhomb", "draw_poly"] and saved_path:
        item = QGraphicsPathItem(saved_path)
        item.setPen(final_pen)
        item.setData(0, {"type": canvas.current_tool.replace("draw_", ""), "depth": 0.0})

    if item is not None:
        item.setFlag(item.GraphicsItemFlag.ItemIsSelectable)
        if canvas.current_tool == "mod_select":
            item.setFlag(item.GraphicsItemFlag.ItemIsMovable)
        canvas.scene().addItem(item)
        canvas.save_history_snapshot() # Делаем срез истории Undo
        canvas.hint_changed.emit("Фигура успешно добавлена на чертеж.")