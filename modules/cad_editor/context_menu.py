from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QPoint, QPointF
from modules.cad_editor.properties_dialog import ElementPropertiesDialog

def show_cad_context_menu(canvas, global_pos: QPoint, scene_pos: QPointF):
    """
    Инженерный диспетчер контекстного меню ПКМ.
    Отрабатывает сценарии одиночного клика по детали или групповых ЧПУ-операций.
    """
    # 1. СНАЧАЛА ПРОВЕРЯЕМ, СКОЛЬКО ФИГУР СЕЙЧАС ВЫДЕЛЕНО НА ХОЛСТЕ OPERATOROM
    selected_items = canvas.scene().selectedItems()
    
    # Ищем, есть ли конкретный вектор прямо под острием курсора в момент клика ПКМ
    clicked_item = canvas.scene().itemAt(scene_pos, canvas.transform())
    is_on_clean_figure = clicked_item is not None and clicked_item.flags() & clicked_item.GraphicsItemFlag.ItemIsSelectable

    # Создаем контекстную плашку меню в фирменном Dark Mode стиле
    menu = QMenu(canvas)
    menu.setStyleSheet("""
        QMenu { background-color: #1A1A1E; color: #E0E0E6; border: 1px solid #32323D; padding: 4px 0px; font-family: 'Segoe UI'; font-size: 11px; }
        QMenu::item { padding: 4px 20px; }
        QMenu::item:selected { background-color: #00A8FF; color: #FFFFFF; }
        QMenu::separator { background-color: #32323D; height: 1px; margin: 4px 10px; }
    """)

    # === СЦЕНАРИЙ А: НА ХОЛСТЕ ВЫДЕЛЕНА ГРУППА ФИГУР (БОЛЬШЕ ОДНОЙ) ===
    if len(selected_items) > 1 and is_on_clean_figure and clicked_item in selected_items:
        act_properties = QAction("⚙️ Свойства элемента (Заблокировано для группы)", menu)
        act_properties.setEnabled(False) # Блокируем доступ к миллиметровым правкам одиночной фигуры!
        
        act_cut = QAction("✂️ Вырезать группу", menu)
        act_copy = QAction("📋 Копировать группу (Ctrl+C)", menu)
        act_delete = QAction("❌ Удалить выбранное (Delete)", menu)

        menu.addAction(act_properties)
        menu.addSeparator()
        menu.addAction(act_cut)
        menu.addAction(act_copy)
        menu.addAction(act_delete)

        selected_action = menu.exec(global_pos)

        # Выполняем массовые операции ЧПУ-векторов в цикле
        if selected_action == act_copy:
            canvas.copy_selected_to_buffer()
        elif selected_action == act_cut:
            canvas.copy_selected_to_buffer()
            for item in selected_items:
                canvas.scene().removeItem(item)
            canvas.hint_changed.emit("Выделенная группа векторов вырезана в буфер.")
        elif selected_action == act_delete:
            for item in selected_items:
                canvas.scene().removeItem(item)
            canvas.hint_changed.emit(f"Группа успешно удалена. Объектов: {len(selected_items)}")
        return

    # === СЦЕНАРИЙ Б: ВЫДЕЛЕНА СТРОГО ОДНА ОДИНОЧНАЯ ФИГУРА ===
    if is_on_clean_figure:
        # Если до этого ничего не было выделено, подсвечиваем именно эту деталь
        canvas.scene().clearSelection()
        clicked_item.setSelected(True)

        act_properties = QAction("⚙️ Свойства элемента (Размеры, Z-глубина)...", menu)
        act_cut = QAction("✂️ Вырезать", menu)
        act_copy = QAction("📋 Копировать (Ctrl+C)", menu)
        act_delete = QAction("❌ Удалить (Delete)", menu)

        menu.addAction(act_properties)
        menu.addSeparator()
        menu.addAction(act_cut)
        menu.addAction(act_copy)
        menu.addAction(act_delete)

        selected_action = menu.exec(global_pos)

        if selected_action == act_properties:
            dialog = ElementPropertiesDialog(clicked_item, canvas)
            result = dialog.exec()
            if result == 2:
                canvas.scene().removeItem(clicked_item)
                canvas.hint_changed.emit("Фигура удалена через окно свойств.")
            elif result == dialog.DialogCode.Accepted:
                canvas.hint_changed.emit("Параметры фигуры успешно применены.")
        elif selected_action == act_copy:
            canvas.copy_selected_to_buffer()
        elif selected_action == act_cut:
            canvas.copy_selected_to_buffer()
            canvas.scene().removeItem(clicked_item)
            canvas.hint_changed.emit("Фигура вырезана в буфер.")
        elif selected_action == act_delete:
            canvas.scene().removeItem(clicked_item)
            canvas.hint_changed.emit("Фигура удалена с чертежа.")
        return

    # === СЦЕНАРИЙ В: КЛИКНУЛИ ПКМ ПО ПУСТОМУ МЕСТУ ХОЛСТА ===
    act_paste = QAction("📥 Вставить (Ctrl+V)", menu)
    act_canvas_settings = QAction("📐 Настройки холста...", menu)
    act_cnc_settings = QAction("🛠️ Параметры ЧПУ станка...", menu)

    act_paste.setEnabled(len(canvas.internal_clipboard) > 0)

    menu.addAction(act_paste)
    menu.addSeparator()
    menu.addAction(act_canvas_settings)
    menu.addAction(act_cnc_settings)

    selected_action = menu.exec(global_pos)

    if selected_action == act_paste:
        canvas.paste_from_buffer()
    elif selected_action == act_canvas_settings:
        canvas.controller.toolbar.action_triggered.emit("settings_canvas")
    elif selected_action == act_cnc_settings:
        canvas.controller.toolbar.action_triggered.emit("settings_cnc")
