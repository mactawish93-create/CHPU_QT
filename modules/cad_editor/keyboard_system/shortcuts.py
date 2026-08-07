from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

def handle_global_shortcuts(canvas, event: QKeyEvent) -> bool:
    """
    Обрабатывает быстрые команды (Ctrl+Z, Esc, Ctrl+C и т.д.).
    :return: True, если хоткей перехвачен и обработан, иначе False
    """
    key = event.key()
    modifiers = event.modifiers()

    # 1. Клавиша ESCAPE — сброс любого черчения и возврат в режим Указателя
    if key == Qt.Key.Key_Escape:
        canvas.is_drawing = False
        if canvas.temp_item:
            canvas.scene().removeItem(canvas.temp_item)
            canvas.temp_item = None
        # Сигнализируем контроллеру принудительно переключить тулбар на стрелочку
        canvas.controller.toolbar.reset_to_select_mode()
        canvas.hint_changed.emit("Режим черчения прерван. Инструмент: УКАЗАТЕЛЬ")
        return True

    # 2. Клавиша DELETE — быстрое удаление выбранных векторов
    elif key == Qt.Key.Key_Delete:
        selected_items = canvas.scene().selectedItems()
        if selected_items:
            for item in selected_items:
                canvas.scene().removeItem(item)
            canvas.hint_changed.emit(f"Удалено элементов: {len(selected_items)}")
            return True

    # 3. Комбинации с зажатым Ctrl
    if modifiers == Qt.KeyboardModifier.ControlModifier:
        if key == Qt.Key.Key_C:
            # Скопировать выбранные фигуры в буфер обмена редактора
            canvas.copy_selected_to_buffer()
            return True
        elif key == Qt.Key.Key_V:
            # Вставить фигуры из буфера со смещением +10мм
            canvas.paste_from_buffer()
            return True
        elif key == Qt.Key.Key_X:
            # Вырезать в буфер
            canvas.copy_selected_to_buffer()
            for item in canvas.scene().selectedItems():
                canvas.scene().removeItem(item)
            return True
        # 🔥 ВНЕДРЕНО: Быстрая отмена действия по Ctrl+Z с клавиатуры
        elif key == Qt.Key.Key_Z:
            canvas.trigger_undo()
            return True

    return False
