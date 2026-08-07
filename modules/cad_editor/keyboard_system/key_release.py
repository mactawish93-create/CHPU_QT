from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

def handle_key_release(canvas, event: QKeyEvent):
    """Вызывается холстом, когда оператор отпускает зажатую клавишу"""
    key = event.key()

    if key == Qt.Key.Key_Control:
        canvas.ctrl_pressed = False
        canvas.update_current_cursor_position()
        
    elif key == Qt.Key.Key_Shift:
        canvas.shift_pressed = False
        canvas.update_current_cursor_position()

    # 🔥 ВНЕДРЕНО: Запекаем точку Undo в историю, когда оператор убрал палец со стрелки
    elif key in [Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down]:
        if canvas.scene().selectedItems():
            canvas.save_history_snapshot()
            event.accept()
            return

    event.ignore()
