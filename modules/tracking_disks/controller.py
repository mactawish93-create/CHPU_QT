from PyQt6.QtWidgets import QFileDialog, QMessageBox
from modules.tracking_disks.sidebar import DisksSidebar
from modules.tracking_disks.canvas import DisksCanvas
from modules.tracking_disks.model import DisksModel

class DisksController:
    def __init__(self):
        self.sidebar = DisksSidebar()
        self.canvas = DisksCanvas()
        self.model = DisksModel()
        
        # Подключаем базовые сигналы
        self._connect_signals()
        self.collect_and_update()

    def get_widgets(self):
        """Возвращает пару изолированных виджетов Дисков"""
        return self.sidebar, self.canvas

    def _connect_signals(self):
        """Вешаем слушатели на комбобоксы Круга и Квадро форм"""
        # Слушаем круглую форму
        self.sidebar.round_view.combo_sub_mode.currentIndexChanged.connect(self.collect_and_update)
        self.sidebar.round_view.combo_diameter.currentIndexChanged.connect(self.collect_and_update)
        self.sidebar.round_view.combo_door_offset.currentIndexChanged.connect(self.collect_and_update)
        self.sidebar.round_view.spin_depth_z.valueChanged.connect(self.collect_and_update)
        
        # Слушаем квадро форму
        self.sidebar.quadro_view.combo_sub_mode.currentIndexChanged.connect(self.collect_and_update)
        self.sidebar.quadro_view.combo_diameter.currentIndexChanged.connect(self.collect_and_update)
        self.sidebar.quadro_view.combo_door_offset.currentIndexChanged.connect(self.collect_and_update)
        self.sidebar.quadro_view.spin_depth_z.valueChanged.connect(self.collect_and_update)
        
        # Слушаем переключение главного меню бань
        self.sidebar.combo_main_mode.currentIndexChanged.connect(self.collect_and_update)
        
        # 🔥 ВНЕДРЕНО: Привязываем синюю кнопку экспорта к методу генерации УП
        self.sidebar.btn_generate_gcode.clicked.connect(self._export_disks_gcode_to_file)

    def _get_current_active_payload(self):
        """Внутренний хелпер: парсит и собирает текущие параметры заготовки"""
        current_main_idx = self.sidebar.combo_main_mode.currentIndex()
        view = self.sidebar.round_view if current_main_idx == 0 else self.sidebar.quadro_view
        
        dia_text = view.combo_diameter.currentText()
        diameter_val = float(dia_text.split()[0]) # Извлекаем число из '2000 мм'
        
        offset_text = view.combo_door_offset.currentText()
        offset_val = float(offset_text.split()[0]) # Извлекаем число из '100 мм'
        
        return {
            "main_mode_idx": current_main_idx,
            "sub_mode": view.combo_sub_mode.currentText(),
            "diameter": diameter_val,
            "door_offset": offset_val,
            "depth_z": view.spin_depth_z.value()
        }

    def collect_and_update(self):
        """Сбор данных сайдбара дисков и живое обновление чертежа"""
        current_main_idx = self.sidebar.combo_main_mode.currentIndex()
        
        # Если выбраны заглушки (Бабочка, Викинг и т.д.) — выходим
        if current_main_idx > 1:
            return
            
        payload = self._get_current_active_payload()
        geo_packet = self.model.calculate_disks_geometry(payload)
        self.canvas.draw_disks_layout(geo_packet)

    def _export_disks_gcode_to_file(self):
        """
        🔥 ВНЕДРЕНО: Генерирует УП (.tap) для дискового раскроя по слоям Z
        и открывает стандартный проводник для записи файла.
        """
        current_main_idx = self.sidebar.combo_main_mode.currentIndex()
        if current_main_idx != 0:
            QMessageBox.warning(self.sidebar, "Разработка", "Генерация G-кода для Квадро и остальных бань будет добавлена на следующем шаге!")
            return
            
        # 1. Нам нужны подачи и обороты шпинделя, которые лежат в главном окне в форме Бани
        # Чтобы не тащить тяжелые связи, мы безопасно достучимся до них через родительское окно MainWindow
        try:
            main_window = self.sidebar.window()
            banya_payload = main_window.paz_controller._get_banya_payload()
        except Exception:
            # Запасной аварийный вариант, если пазировка еще не инициализирована
            banya_payload = {"spindle_s": 3000, "feed_xy": 2000, "feed_z": 500}

        # 2. Собираем паспорт параметров диска и его рассчитанную геометрию
        disks_payload = self._get_current_active_payload()
        geometry_packet = self.model.calculate_disks_geometry(disks_payload)
        
        # 3. Запускаем CAM-генератор круга (2012, 2162, 2312 мм) со слоями Z
        gcode_text = main_window.paz_controller.gcode_engine.generate_round_disk_tap(
            geometry_packet, banya_payload, disks_payload
        )
        
        # 4. Вызываем стандартный проводник PyQt6 [1]
        file_path, _ = QFileDialog.getSaveFileName(
            self.sidebar,
            "Сохранить управляющую программу раскроя диска",
            "",
            "Файлы ЧПУ станка (*.tap);;Все файлы (*.*)"
        )
        
        # 5. Пишем готовый послойный G-код на флешку станка
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(gcode_text)
                QMessageBox.information(
                    self.sidebar, 
                    "Успешный экспорт", 
                    f"Файл УП круглого диска успешно записан:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self.sidebar, 
                    "Ошибка записи", 
                    f"Не удалось сохранить файл.\nПричина: {str(e)}"
                )
