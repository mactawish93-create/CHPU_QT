from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

def handle_key_press(canvas, event: QKeyEvent):
    """Вызывается холстом, когда оператор зажимает клавишу на клавиатуре цехового ПК"""
    key = event.key()

    # Инициализируем накопительные регистры дельты в холсте, если их еще нет в памяти
    if not hasattr(canvas, "nudge_dx"): canvas.nudge_dx = 0.0
    if not hasattr(canvas, "nudge_dy"): canvas.nudge_dy = 0.0

    # 1. ОБРАБОТКА СИСТЕМНЫХ МОДИФИКАТОРОВ ЧПУ (Ctrl и Shift)
    if key == Qt.Key.Key_Control:
        canvas.ctrl_pressed = True
        canvas.update_current_cursor_position()
        
    elif key == Qt.Key.Key_Shift:
        canvas.shift_pressed = True
        canvas.update_current_cursor_position()

    # 2. МИКРО-ШАГОВОЕ ПОЗИЦИОНИРОВАНИЕ ДЕТАЛЕЙ СТРЕЛКАМИ (Nudge)
    elif key in [Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down]:
        selected_items = canvas.scene().selectedItems()
        
        # Если оператор выделил фигуры Указателем, двигаем их, а не экран холста
        if selected_items:
            # Если зажат Shift — шаг 10мм, если нет — ювелирные 1мм для точной подгонки
            step = 10.0 if canvas.shift_pressed else 1.0
            dx, dy = 0.0, 0.0

            if key == Qt.Key.Key_Left:    dx = -step
            elif key == Qt.Key.Key_Right: dx = step
            elif key == Qt.Key.Key_Up:    dy = -step # Вверх по сцене Qt — это уменьшение Y
            elif key == Qt.Key.Key_Down:  dy = step

            # Накапливаем общую дельту текущей сессии клавиатурного перемещения
            canvas.nudge_dx += dx
            # Инвертируем dy для вывода человеку (чтобы "Вверх" было со знаком плюс)
            canvas.nudge_dy += (-dy)

            for item in selected_items:
                if item == canvas.snap_marker:
                    continue
                # Сдвигаем физическую позицию вектора на сцене
                item.moveBy(dx, dy)
                
                # Обновляем паспортные ЧПУ-координаты для линий, чтобы G-код не съезжал
                item_data = item.data(0) if item.data(0) else {}
                if item_data.get("type") == "line" and hasattr(item, "line"):
                    line = item.line()
                    item_data.update({
                        "x1": round(line.x1() + item.x(), 2), "y1": round(line.y1() + item.y(), 2),
                        "x2": round(line.x2() + item.x(), 2), "y2": round(line.y2() + item.y(), 2)
                    })
                    item.setData(0, item_data)

            # 🔥 ИСПРАВЛЕНО: Выводим точную живую дельту ЧПУ-перемещения в центр статусбара!
            msg = f"Сдвиг геометрии  ➔  ΔX: {canvas.nudge_dx:+.1f} мм  |  ΔY: {canvas.nudge_dy:+.1f} мм"
            canvas.hint_changed.emit(msg)
            
            event.accept() # Блокируем скроллинг самого холста в Qt
            return

    # Если клавиша не перехвачена нами, разрешаем Qt обработать её стандартно
    event.ignore()
