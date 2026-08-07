import os
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QGraphicsLineItem, QGraphicsRectItem, QGraphicsPathItem
from PyQt6.QtGui import QPen, QColor, QPainterPath, QTransform

# Импортируем все компоненты нашей файловой фабрики из папки io_system/
from modules.cad_editor.io_system.cam_project import CamProjectManager
from modules.cad_editor.io_system.dxf_exchange import DxfExchangeManager
from modules.cad_editor.io_system.tap_export import TapExportManager
from modules.cad_editor.io_system.pdf_exchange import PdfExchangeManager
from modules.cad_editor.io_system.img_import import ImageImportDialog
from modules.cad_editor.toolbar import CadToolbar
from modules.cad_editor.canvas import CadCanvas
from modules.cad_editor.statusbar import CadStatusbar
from modules.cad_editor.io_system.cam_project import CamProjectManager

class CadEditorController(QObject):
    """
    Главный диспетчер графического редактора CAD/CAM.
    Связывает сигналы кнопок тулбара, интерактивного холста и нижней панели состояния.
    Управляет файловой фабрикой и технологическими параметрами ЧПУ.
    """
    def __init__(self):
        super().__init__()
        # Инициализируем живые компоненты редактора
        self.toolbar = CadToolbar()
        self.canvas = CadCanvas(self)
        self.statusbar = CadStatusbar()

        # Инициализируем менеджеры файловой фабрики io_system/
        self.project_io = CamProjectManager()
        self.dxf_io = DxfExchangeManager()
        self.tap_io = TapExportManager()
        self.pdf_io = PdfExchangeManager()

        # Глобальные технологические настройки ЧПУ проекта (блок cnc_settings по умолчанию)
        self.cnc_settings = self.project_io.default_cnc_settings.copy()

        # Регистр пути к открытому файлу (None — значит чертеж еще не сохранялся)
        self.current_project_path = None

        # --- СВЯЗЫВАНИЕ СИГНАЛОВ ТУЛБАРА ---
        self.toolbar.tool_changed.connect(self.canvas.set_current_tool)
        self.toolbar.action_triggered.connect(self._on_toolbar_action)

        # --- СВЯЗЫВАНИЕ СИГНАЛОВ ИНТЕРАКТИВНОГО ХОЛСТА ---
        self.canvas.mouse_moved.connect(self.statusbar.update_coordinates)
        self.canvas.zoom_changed.connect(self.statusbar.update_zoom)
        self.canvas.hint_changed.connect(self.statusbar.update_hint)

    def get_widgets(self):
        """Возвращает готовую триаду виджетов для вертикального монтажа в MainWindow"""
        return self.toolbar, self.canvas, self.statusbar

    def _collect_geometry_data(self) -> list:
        """Собирает все чистые векторы с холста, сохраняя ссылки на живые графические объекты Qt"""
        geometry_list = []
        for item in self.canvas.cad_scene.items():
            if not item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
                continue
            if item == self.canvas.snap_marker:
                continue
                
            item_data = item.data(0) if item.data(0) else {"type": "unknown", "depth": 0.0}
            
            # Упаковываем паспорт ЧПУ И саму ссылку на графический объект сцены для расчета матриц поворота
            pack = {
                "raw_item": item,
                "data": item_data.copy()
            }
            
            # Сохраняем дополнительные базовые плоские координаты для совместимости с JSON (.cam)
            if isinstance(item, QGraphicsLineItem):
                line = item.line()
                pack.update({"type": "line", "x1": line.x1(), "y1": line.y1(), "x2": line.x2(), "y2": line.y2(), "depth": item_data.get("depth", 0.0)})
            elif isinstance(item, QGraphicsRectItem):
                r = item.rect()
                pack.update({"type": "rect", "x": r.x(), "y": r.y(), "width": r.width(), "height": r.height(), "depth": item_data.get("depth", 0.0)})
            elif isinstance(item, QGraphicsPathItem):
                pack.update({"type": item_data.get("type", "path"), "path": QPainterPath(item.path()), "depth": item_data.get("depth", 0.0)})
                
            geometry_list.append(pack)
        return geometry_list

    def _on_toolbar_action(self, action_id: str):
        """Диспетчер для системных кнопок тулбара (Файлы, Буфер обмена, Настройки)"""
        
        # --- ГРУППА 3: МОДИФИКАТОРЫ БУФЕРА ОБМЕНА И ИСТОРИИ ---
        if action_id == "edit_copy":
            self.canvas.copy_selected_to_buffer()
        elif action_id == "edit_paste":
            self.canvas.paste_from_buffer()
        elif action_id == "edit_cut":
            self.canvas.copy_selected_to_buffer()
            selected_items = self.canvas.scene().selectedItems()
            for item in selected_items:
                if item != self.canvas.snap_marker:
                    self.canvas.scene().removeItem(item)
            self.canvas.save_history_snapshot()
            self.canvas.hint_changed.emit(f"Элементы вырезаны в буфер обмена. Объектов: {len(selected_items)}")
        elif action_id == "edit_undo":
            self.canvas.trigger_undo()
        elif action_id == "edit_redo":
            self.canvas.trigger_redo()
        elif action_id == "edit_undo_all":
            self.canvas.trigger_clear_all()
            
        # --- ГРУППА 7: ПРОЧИЕ ---
        elif action_id == "view_center":
            self.canvas.centerOn(0, 0)
            self.canvas.current_zoom = 1.0
            self.canvas.resetTransform()
            self.statusbar.update_zoom(1.0)
            self.statusbar.update_hint("Экран успешно отцентрирован в ноль осей X/Y")

        # --- 🔥 ВНЕДРЕНО: ОЖИВЛЕНИЕ КНОПОК ГРУППЫ 1 (ФАЙЛЫ) ---
        elif action_id == "file_new":
            # 1.1 Новый файл
            self.canvas.trigger_clear_all()
            self.canvas.undo_stack.clear()
            self.canvas.redo_stack.clear()
            self.canvas.save_history_snapshot() # Фиксируем чистый стартовый срез истории
            self.current_project_path = None
            self.cnc_settings = self.project_io.default_cnc_settings.copy()
            self.statusbar.update_hint("Создан новый пустой проект ЧПУ (.cam)")
            
        elif action_id == "file_open":
            # 1.2 Открыть файл проекта
            file_path, _ = QFileDialog.getOpenFileName(self.canvas, "Открыть проект ЧПУ", "", "Проекты ЧПУ (*.cam)")
            if file_path:
                project_data = self.project_io.load_project(file_path)
                if project_data is not None:
                    self.current_project_path = file_path
                    self.cnc_settings = project_data["cnc_settings"]
                    
                    # Накатываем считанную геометрию обратно на сцену через холст
                    self.canvas._restore_snapshot(project_data["geometry"])
                    self.canvas.undo_stack.clear()
                    self.canvas.redo_stack.clear()
                    self.canvas.save_history_snapshot() # Перезаписываем точку истории
                    self.statusbar.update_hint(f"Проект успешно загружен: {os.path.basename(file_path)}")
                else:
                    QMessageBox.critical(self.canvas, "Ошибка ЧПУ", "Не удалось прочитать файл проекта. Возможно, структура повреждена.")

        elif action_id == "file_save":
            # 1.3 Сохранить файл
            if self.current_project_path:
                # Если файл уже имеет путь на диске, перезаписываем тихо без вызова диалогов
                geometry_data = self._collect_geometry_data()
                if self.project_io.save_project(self.current_project_path, geometry_data, self.cnc_settings):
                    self.statusbar.update_hint(f"Изменения успешно сохранены: {os.path.basename(self.current_project_path)}")
                else:
                    QMessageBox.critical(self.canvas, "Ошибка записи", "Не удалось перезаписать файл на диске.")
            else:
                # Если файл новый, автоматически перенаправляем на "Сохранить как..."
                self._on_toolbar_action("file_save_as")

        elif action_id == "file_save_as":
            # 1.4 Сохранить как...
            file_path, _ = QFileDialog.getSaveFileName(self.canvas, "Сохранить проект как...", "", "Проекты ЧПУ (*.cam)")
            if file_path:
                # Принудительно проверяем расширение .cam
                if not file_path.lower().endswith('.cam'):
                    file_path += '.cam'
                
                geometry_data = self._collect_geometry_data()
                if self.project_io.save_project(file_path, geometry_data, self.cnc_settings):
                    self.current_project_path = file_path
                    self.statusbar.update_hint(f"Проект успешно сохранен на диск: {os.path.basename(file_path)}")
                else:
                    QMessageBox.critical(self.canvas, "Ошибка записи", "Не удалось записать файл проекта.")
        # --- 🔥 ВНЕДРЕНО: ОЖИВЛЕНИЕ КНОПОК ГРУППЫ 2 (ИМПОРТ / ЭКСПОРТ) ---
        elif action_id == "import_img":
            # 2.1 Импорт из изображения (Векторизатор)
            dialog = ImageImportDialog(self.canvas)
            if dialog.exec() == ImageImportDialog.DialogCode.Accepted:
                # Извлекаем полученные горизонтальные растровые линии ЧПУ
                vector_lines = dialog.get_vectorized_lines()
                if vector_lines:
                    final_pen = QPen(QColor("#E0E0E6"), 1.5, Qt.PenStyle.SolidLine)
                    # Построчно высыпаем линии гравировки на холст
                    for line_data in vector_lines:
                        item = self.canvas.cad_scene.addLine(
                            line_data["x1"], line_data["y1"], 
                            line_data["x2"], line_data["y2"], final_pen
                        )
                        item.setData(0, {"type": "line", "depth": line_data["depth"]})
                        item.setFlag(item.GraphicsItemFlag.ItemIsSelectable)
                    
                    self.canvas.save_history_snapshot() # Фиксируем срез в историю
                    self.statusbar.update_hint(f"Успешная векторизация: добавлено {len(vector_lines)} линий гравировки")
                else:
                    self.statusbar.update_hint("Векторизатор закрыт: линии не обнаружены")

        elif action_id == "import_dxf":
            # 2.2 Импорт из DXF AutoCAD
            file_path, _ = QFileDialog.getOpenFileName(self.canvas, "Импорт чертежа AutoCAD DXF", "", "Чертежи DXF (*.dxf)")
            if file_path:
                imported_lines = self.dxf_io.import_from_dxf(file_path)
                if imported_lines:
                    final_pen = QPen(QColor("#E0E0E6"), 1.5, Qt.PenStyle.SolidLine)
                    for line_data in imported_lines:
                        item = self.canvas.cad_scene.addLine(
                            line_data["x1"], line_data["y1"], 
                            line_data["x2"], line_data["y2"], final_pen
                        )
                        item.setData(0, {"type": "line", "depth": line_data["depth"]})
                        item.setFlag(item.GraphicsItemFlag.ItemIsSelectable)
                    
                    self.canvas.save_history_snapshot()
                    self.statusbar.update_hint(f"Успешный импорт DXF: восстановлено {len(imported_lines)} векторов LINE")
                else:
                    QMessageBox.warning(self.canvas, "Импорт DXF", "В файле не найдено поддерживаемых примитивов LINE или файл пуст.")

        elif action_id == "export_tap":
            # 2.3 Экспорт в TAP (Послойный G-код для станка с M7)
            file_path, _ = QFileDialog.getSaveFileName(self.canvas, "Экспорт управляющей программы ЧПУ", "", "Файлы ЧПУ (*.tap *.txt)")
            if file_path:
                if not (file_path.lower().endswith('.tap') or file_path.lower().endswith('.txt')):
                    file_path += '.tap'
                
                geometry_data = self._collect_geometry_data()
                # Передаем массив векторов холста нашему послойному CAM-процессору
                if self.tap_io.generate_tap_file(file_path, geometry_data, self.cnc_settings):
                    self.statusbar.update_hint(f"G-код УП успешно сгенерирован: {os.path.basename(file_path)}")
                else:
                    QMessageBox.critical(self.canvas, "CAM Ошибка", "Не удалось скомпилировать G-код управляющей программы.")

        elif action_id == "export_dxf":
            # 2.4 Экспорт в DXF AutoCAD
            file_path, _ = QFileDialog.getSaveFileName(self.canvas, "Экспорт векторов в DXF", "", "Чертежи DXF (*.dxf)")
            if file_path:
                if not file_path.lower().endswith('.dxf'):
                    file_path += '.dxf'
                
                geometry_data = self._collect_geometry_data()
                if self.dxf_io.export_to_dxf(file_path, geometry_data):
                    self.statusbar.update_hint(f"Векторы чертежа успешно экспортированы в DXF: {os.path.basename(file_path)}")
                else:
                    QMessageBox.critical(self.canvas, "Ошибка экспорта", "Не удалось сохранить DXF файл.")

        elif action_id == "export_pdf":
            # 2.5 Экспорт чертежа в PDF альбом А4 для цеха
            file_path, _ = QFileDialog.getSaveFileName(self.canvas, "Экспорт цеховой карты в PDF", "", "Документы PDF (*.pdf)")
            if file_path:
                if not file_path.lower().endswith('.pdf'):
                    file_path += '.pdf'
                
                geometry_data = self._collect_geometry_data()
                # Запускаем движок QPdfWriter с авторасчетом масштаба и простановкой габаритов
                if self.pdf_io.export_to_pdf(file_path, geometry_data, self.cnc_settings):
                    self.statusbar.update_hint(f"Цеховой PDF чертеж успешно сформирован: {os.path.basename(file_path)}")
                else:
                    QMessageBox.critical(self.canvas, "Ошибка PDF", "Не удалось сгенерировать PDF документ.")

        # --- ГРУППА 6: НАСТРОЙКИ (🔥 ИСПРАВЛЕНО: ОЖИВЛЕНИЕ ПАРАМЕТРОВ ЧПУ) ---
        elif action_id == "settings_canvas":
            # 🔥 ИСПРАВЛЕНО: Оживление кнопки 6.1 (Настройки холста и сетки)
            from modules.cad_editor.canvas_dialog import CanvasSettingsDialog
            
            # Вызываем диалог, передавая ему текущие параметры из нашего CAD-движка привязок
            dialog = CanvasSettingsDialog(self.canvas.cad_engine.grid_size, self.canvas.cad_engine.snap_radius, self.canvas)
            if dialog.exec() == CanvasSettingsDialog.DialogCode.Accepted:
                new_grid, new_radius = dialog.get_values()
                
                # Мгновенно перенастраиваем математическое ядро привязок станка
                self.canvas.cad_engine.grid_size = new_grid
                self.canvas.cad_engine.snap_radius = new_radius
                
                # Принудительно заставляем холст перерисовать фоновую сетку под новый шаг (5мм, 50мм и т.д.)
                self.canvas.viewport().update()
                
                self.statusbar.update_hint(f"Среда черчения обновлена: шаг сетки {new_grid} мм.")
            
        elif action_id == "settings_cnc":
            # Импортируем наше новое диалоговое окно ЧПУ-параметров
            from modules.cad_editor.cnc_dialog import CncSettingsDialog
            
            # Открываем окно, передавая ему текущий словарь настроек из памяти контроллера
            dialog = CncSettingsDialog(self.cnc_settings, self.canvas)
            if dialog.exec() == CncSettingsDialog.DialogCode.Accepted:
                # Если оператор нажал "Сохранить", забираем обновленный технологический паспорт станка
                self.cnc_settings = dialog.get_settings()
                
                # Выводим красивое инженерное уведомление в статусбар
                msg = f"Параметры ЧПУ обновлены: Фреза {self.cnc_settings['tool_diameter']}мм | Проход {self.cnc_settings['step_down']}мм"
                self.statusbar.update_hint(msg)
# --- 🔥 ВНЕДРЕНО: КНОПКИ 4.8 И 4.9 БЫСТРОГО ПОВОРОТА НА 90 ГРАДУСОВ ---
        elif action_id in ["action_rotate_left", "action_rotate_right"]:
            selected_items = self.canvas.scene().selectedItems()
            if not selected_items:
                self.statusbar.update_hint("Поворот заблокирован: выберите фигуры с помощью Указателя.")
                return

            # Определяем угол: влево = -90° (против часовой), вправо = +90° (по часовой)
            angle = -90.0 if action_id == "action_rotate_left" else 90.0

            for item in selected_items:
                if item == self.canvas.snap_marker:
                    continue

                # 1. Извлекаем локальный центр boundingRect фигуры до применения трансформации
                local_rect = item.boundingRect()
                center = local_rect.center()

                # 2. Строим матрицу трансформации QTransform вокруг центра фигуры
                transform = QTransform()
                transform.translate(center.x(), center.y())
                transform.rotate(angle)
                transform.translate(-center.x(), -center.y())

                # 3. Обновляем графическое представление элемента в Qt
                # Метод преобразует путь (перо), сохраняя качество Безье без искажений
                if hasattr(item, "setPath"):
                    # Для Кругов, Ромбов, Многоугольников, Кривых и Текста гнем векторный путь
                    new_path = transform.map(item.path())
                    item.setPath(new_path)
                elif isinstance(item, QGraphicsRectItem):
                    # Прямоугольники переводим в QGraphicsPathItem, так как при повороте на 90°
                    # они могут изменить ориентацию, а нативный drawRect не поддерживает наклонные матрицы
                    path = QPainterPath()
                    path.addRect(item.rect())
                    new_path = transform.map(path)
                    
                    # Создаем новый чистовой Path-элемент взамен прямоугольника
                    final_pen = item.pen()
                    old_data = item.data(0).copy()
                    
                    path_item = self.canvas.scene().addPath(new_path, final_pen)
                    path_item.setData(0, old_data)
                    path_item.setFlag(path_item.GraphicsItemFlag.ItemIsSelectable)
                    path_item.setFlag(path_item.GraphicsItemFlag.ItemIsMovable, True)
                    path_item.setSelected(True)
                    
                    self.canvas.scene().removeItem(item)
                    item = path_item # Подменяем ссылку для обновления ЧПУ-паспорта ниже

                elif isinstance(item, QGraphicsLineItem):
                    # Для одиночных линий пересчитываем координаты точек старта и конца
                    line = item.line()
                    p1_new = transform.map(line.p1())
                    p2_new = transform.map(line.p2())
                    item.setLine(p1_new.x(), p1_new.y(), p2_new.x(), p2_new.y())

                # 4. 🔥 КРИТИЧЕСКИ ВАЖНО ДЛЯ ЧПУ: Обновляем внутренний паспорт геометрии (Data)
                item_data = item.data(0) if item.data(0) else {"type": "unknown", "depth": 0.0}
                
                if item_data.get("type") in ["rect", "text"]:
                    # Переворачиваем габариты: ширина и высота меняются местами
                    if "width" in item_data and "height" in item_data:
                        item_data["width"], item_data["height"] = item_data["height"], item_data["width"]
                
                # Если это линия, перезаписываем повернутые координаты в ЧПУ-словари
                if isinstance(item, QGraphicsLineItem):
                    line = item.line()
                    item_data.update({
                        "x1": round(line.x1(), 2), "y1": round(line.y1(), 2),
                        "x2": round(line.x2(), 2), "y2": round(line.y2(), 2)
                    })

                item.setData(0, item_data)

            # Фиксируем срез в историю Undo/Redo, чтобы поворот можно было отменить по Ctrl+Z!
            self.canvas.save_history_snapshot()
            
            dir_text = "влево" if angle < 0 else "вправо"
            self.statusbar.update_hint(f"Успешный разворот деталей на 90° {dir_text}. Объектов: {len(selected_items)}")