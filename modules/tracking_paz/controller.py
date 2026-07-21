from PyQt6.QtWidgets import QFileDialog, QMessageBox
from modules.tracking_paz.sidebar import PazSidebar
from modules.tracking_paz.canvas import PazCanvas
from modules.tracking_paz.model import PazModel
from core.gcode_generator import PazGCodeGenerator

class PazController:
    def __init__(self):
        # 1. Инициализируем изолированные компоненты нашего CAM-модуля
        self.sidebar = PazSidebar()
        self.canvas = PazCanvas()
        self.model = PazModel()
        self.gcode_engine = PazGCodeGenerator()
        
        # 2. Подключаем слушатели сигналов ко всем полям ввода в сайдбаре
        self._connect_ui_signals()
        
        # 3. Делаем первый стартовый расчет и отрисовку геометрии щита
        self.collect_and_update()

    def get_widgets(self):
        """Возвращает пару изолированных виджетов (Левая панель, Правая панель)"""
        return self.sidebar, self.canvas

    def _connect_ui_signals(self):
        """Обновленный метод подключения сигналов: теперь слушаем все три подрежима"""
        banya = self.sidebar.banya_view
        custom = self.sidebar.custom_paz_view
        plane = self.sidebar.plane_view
        
        # --- Сигналы подрежима БАНИ ---
        banya.combo_sub_mode.currentIndexChanged.connect(self.collect_and_update)
        banya.spin_mill_dia.valueChanged.connect(self.collect_and_update)
        banya.spin_torec_z.valueChanged.connect(self.collect_and_update)
        banya.spin_lezhka_x.valueChanged.connect(self.collect_and_update)
        banya.spin_back_vypusk.valueChanged.connect(self.collect_and_update)
        banya.spin_spindle_s.valueChanged.connect(self.collect_and_update)
        banya.spin_feed_xy.valueChanged.connect(self.collect_and_update)
        banya.spin_feed_z.valueChanged.connect(self.collect_and_update)
        
        banya.ch_paz_w.toggled.connect(self.collect_and_update)
        banya.spin_paz_w.valueChanged.connect(self.collect_and_update)
        banya.ch_paz_z.toggled.connect(self.collect_and_update)
        banya.spin_paz_z.valueChanged.connect(self.collect_and_update)
        banya.ch_front.toggled.connect(self.collect_and_update)
        banya.spin_front_vypusk.valueChanged.connect(self.collect_and_update)
        banya.ch_germ_w.toggled.connect(self.collect_and_update)
        banya.spin_germ_w.valueChanged.connect(self.collect_and_update)
        banya.ch_germ_z.toggled.connect(self.collect_and_update)
        banya.spin_germ_z.valueChanged.connect(self.collect_and_update)
        
        for chbox in banya.room_checkboxes:
            chbox.toggled.connect(self.collect_and_update)
        for spin in banya.room_spinboxes:
            spin.valueChanged.connect(self.collect_and_update)
            
        banya.btn_generate_gcode.clicked.connect(self._export_gcode_to_file)

        # --- Сигналы подрежима ПРОИЗВОЛЬНОЙ ПАЗИРОВКИ ---
        custom.btn_add_slot.clicked.connect(self._connect_dynamic_custom_signals)
        custom.btn_add_torec.clicked.connect(self._connect_dynamic_custom_signals)
        custom.btn_generate_gcode.clicked.connect(self._export_custom_gcode_to_file)

        # --- Сигналы подрежима ВЫРАВНИВАНИЯ ПЛОСКОСТИ ---
        plane.combo_strategy.currentIndexChanged.connect(self.collect_and_update)
        plane.spin_length_y.valueChanged.connect(self.collect_and_update)
        plane.spin_length_x.valueChanged.connect(self.collect_and_update)
        plane.spin_mill_dia.valueChanged.connect(self.collect_and_update)
        plane.spin_stepover.valueChanged.connect(self.collect_and_update)
        plane.spin_depth_z.valueChanged.connect(self.collect_and_update)
        plane.btn_generate_gcode.clicked.connect(self._export_plane_gcode_to_file)

        # Слушаем переключение главного оранжевого комбобокса подрежимов сайдбара
        self.sidebar.combo_main_mode.currentIndexChanged.connect(self._on_main_mode_changed)

    def _on_main_mode_changed(self, index):
        self.collect_and_update()

    def _get_banya_payload(self):
        """Собирает паспорт параметров для формы Бани"""
        banya = self.sidebar.banya_view
        rooms_data = []
        for i in range(5):
            is_active = banya.room_checkboxes[i].isChecked()
            length = banya.room_spinboxes[i].value()
            rooms_data.append((is_active, length))
            
        return {
            "mill_dia": banya.spin_mill_dia.value(),
            "torec_z": banya.spin_torec_z.value(),
            "lezhka_x": banya.spin_lezhka_x.value(),
            "back_vypusk": banya.spin_back_vypusk.value(),
            "spindle_s": banya.spin_spindle_s.value(),
            "feed_xy": banya.spin_feed_xy.value(),
            "feed_z": banya.spin_feed_z.value(),
            
            "ch_paz_w": banya.ch_paz_w.isChecked(),
            "paz_w": banya.spin_paz_w.value(),
            "ch_paz_z": banya.ch_paz_z.isChecked(),
            "paz_z": banya.spin_paz_z.value(),
            "ch_front": banya.ch_front.isChecked(),
            "front_vypusk": banya.spin_front_vypusk.value(),
            "sub_mode": banya.combo_sub_mode.currentText(),
            "ch_germ_w": banya.ch_germ_w.isChecked(),
            "germ_w": banya.spin_germ_w.value(),
            "ch_germ_z": banya.ch_germ_z.isChecked(),
            "germ_z": banya.spin_germ_z.value(),
            "rooms": rooms_data
        }
    def _connect_dynamic_custom_signals(self):
        """Фабричный метод: на лету подписывает новые созданные плашки на автообновление чертежа"""
        custom = self.sidebar.custom_paz_view
        
        for row in custom.slots_list:
            try: row.checkbox.toggled.disconnect(self.collect_and_update)
            except: pass
            try: row.spin_width.valueChanged.disconnect(self.collect_and_update)
            except: pass
            try: row.spin_length.valueChanged.disconnect(self.collect_and_update)
            except: pass
            try: row.spin_depth.valueChanged.disconnect(self.collect_and_update)
            except: pass
            try: row.spin_offset.valueChanged.disconnect(self.collect_and_update)
            except: pass
            
            row.checkbox.toggled.connect(self.collect_and_update)
            row.spin_width.valueChanged.connect(self.collect_and_update)
            row.spin_length.valueChanged.connect(self.collect_and_update)
            row.spin_depth.valueChanged.connect(self.collect_and_update)
            row.spin_offset.valueChanged.connect(self.collect_and_update)

        for row in custom.torecs_list:
            try: row.checkbox.toggled.disconnect(self.collect_and_update)
            except: pass
            try: row.spin_depth.valueChanged.disconnect(self.collect_and_update)
            except: pass
            try: row.spin_length.valueChanged.disconnect(self.collect_and_update)
            except: pass
            try: row.spin_offset.valueChanged.disconnect(self.collect_and_update)
            except: pass
            
            row.checkbox.toggled.connect(self.collect_and_update)
            row.spin_depth.valueChanged.connect(self.collect_and_update)
            row.spin_length.valueChanged.connect(self.collect_and_update)
            row.spin_offset.valueChanged.connect(self.collect_and_update)
            
        self.collect_and_update()

    def _get_custom_payload(self):
        """Интеллектуальный сбор данных: сканирует списки плашек и отсеивает только активные"""
        banya = self.sidebar.banya_view  # Базовые фреза и ширина лежки берутся из первой формы
        custom = self.sidebar.custom_paz_view
        
        slots_data = []
        for row in custom.slots_list:
            if row.checkbox.isChecked():
                slots_data.append({
                    "width": row.spin_width.value(),
                    "length": row.spin_length.value(),
                    "depth": row.spin_depth.value(),
                    "offset": row.spin_offset.value()
                })
                
        torecs_data = []
        for row in custom.torecs_list:
            if row.checkbox.isChecked():
                torecs_data.append({
                    "depth": row.spin_depth.value(),
                    "length": row.spin_length.value(),
                    "offset": row.spin_offset.value()
                })
                
        return {
            "mill_dia": banya.spin_mill_dia.value(),
            "lezhka_x": banya.spin_lezhka_x.value(),
            "torec_z": banya.spin_torec_z.value(),
            "slots": slots_data,
            "torecs": torecs_data
        }

    def _get_plane_payload(self):
        """Служебный метод: собирает текущий паспорт параметров формы Калибровки стола"""
        plane = self.sidebar.plane_view
        banya = self.sidebar.banya_view
        
        return {
            "strategy": plane.combo_strategy.currentText(),
            "length_y": plane.spin_length_y.value(),
            "length_x": plane.spin_length_x.value(),
            "mill_dia": plane.spin_mill_dia.value(),
            "stepover": plane.spin_stepover.value(),
            "depth_z": plane.spin_depth_z.value(),
            "torec_z": banya.spin_torec_z.value()
        }

    def collect_and_update(self):
        """Главный мост: определяет активный режим и направляет поток данных в нужный калькулятор"""
        current_mode_index = self.sidebar.combo_main_mode.currentIndex()
        
        if current_mode_index == 0:
            payload = self._get_banya_payload()
            geometry_packet = self.model.calculate_banya_geometry(payload)
            self.canvas.draw_paz_beam(geometry_packet)
            
        elif current_mode_index == 1:
            payload = self._get_custom_payload()
            geometry_packet = self.model.calculate_custom_geometry(payload)
            self.canvas.draw_paz_beam(geometry_packet)
            
        elif current_mode_index == 2:
            payload = self._get_plane_payload()
            geometry_packet = self.model.calculate_plane_geometry(payload)
            self.canvas.draw_paz_beam(geometry_packet)

    def _export_gcode_to_file(self):
        """Экспорт УП для Бани"""
        payload = self._get_banya_payload()
        geometry_packet = self.model.calculate_banya_geometry(payload)
        gcode_text = self.gcode_engine.generate_banya_tap(geometry_packet, payload)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self.sidebar, "Сохранить управляющую программу ЧПУ", "", "Файлы ЧПУ станка (*.tap);;Все файлы (*.*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(gcode_text)
                QMessageBox.information(self.sidebar, "Успешный экспорт", f"Файл УП Бани успешно записан:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self.sidebar, "Ошибка записи", f"Не удалось сохранить файл.\nПричина: {str(e)}")

    def _export_custom_gcode_to_file(self):
        """Экспорт УП для Произвольной пазировки"""
        banya_payload = self._get_banya_payload()
        custom_payload = self._get_custom_payload()
        geometry_packet = self.model.calculate_custom_geometry(custom_payload)
        
        gcode_text = self.gcode_engine.generate_custom_tap(geometry_packet, banya_payload)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self.sidebar, "Сохранить управляющую программу Произвольного реза", "", "Файлы ЧПУ станка (*.tap);;Все файлы (*.*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(gcode_text)
                QMessageBox.information(self.sidebar, "Успешный экспорт", f"Файл УП Произвольной пазировки успешно записан:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self.sidebar, "Ошибка записи", f"Не удалось сохранить файл.\nПричина: {str(e)}")

    def _export_plane_gcode_to_file(self):
        """Экспорт УП для Выравнивания плоскости стола"""
        banya_payload = self._get_banya_payload()
        plane_payload = self._get_plane_payload()
        geometry_packet = self.model.calculate_plane_geometry(plane_payload)
        
        gcode_text = self.gcode_engine.generate_plane_tap(geometry_packet, banya_payload)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self.sidebar, "Сохранить управляющую программу Калибровки стола", "", "Файлы ЧПУ станка (*.tap);;Все файлы (*.*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(gcode_text)
                QMessageBox.information(self.sidebar, "Успешный экспорт", f"Файл УП Выравнивания стола успешно записан:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self.sidebar, "Ошибка записи", f"Не удалось сохранить файл.\nПричина: {str(e)}")
