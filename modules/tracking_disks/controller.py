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

        # Слушаем форму Бабочки
       # self.sidebar.babochka_view.combo_sub_mode.currentIndexChanged.connect(self.collect_and_update)
        self.sidebar.babochka_view.spin_diameter.valueChanged.connect(self.collect_and_update)
        self.sidebar.babochka_view.spin_depth_z.valueChanged.connect(self.collect_and_update)
        self.sidebar.babochka_view.spin_h_kon.valueChanged.connect(self.collect_and_update)
        self.sidebar.babochka_view.combo_vert_paz.currentIndexChanged.connect(self.collect_and_update)
        self.sidebar.babochka_view.spin_room_y.valueChanged.connect(self.collect_and_update)
        self.sidebar.babochka_view.spin_paz_z.valueChanged.connect(self.collect_and_update)

    def _get_current_active_payload(self):
        """Внутренний хелпер: парсит и собирает текущие параметры заготовки"""
        current_main_idx = self.sidebar.combo_main_mode.currentIndex()
        
        if current_main_idx == 0:
            view = self.sidebar.round_view
        elif current_main_idx == 1:
            view = self.sidebar.quadro_view
        elif current_main_idx == 2:
            view = self.sidebar.babochka_view
        else:
            view = self.sidebar.round_view

        # 🔥 ВНЕДРЕНО: Для Бабочки (2) берем диаметр напрямую из спинбокса, для Круга/Квадро - из текста комбобокса
        if current_main_idx == 2:
            diameter_val = view.spin_diameter.value()
            sub_mode_text = "Глухой диск" # Всегда глухой, проема нет
            offset_val = 0.0
        else:
            dia_text = view.combo_diameter.currentText()
            diameter_val = float(dia_text.split()[0])
            sub_mode_text = view.combo_sub_mode.currentText()
            offset_text = view.combo_door_offset.currentText()
            offset_val = float(offset_text.split()[0])

        payload = {
            "main_mode_idx": current_main_idx,
            "sub_mode": sub_mode_text,
            "diameter": diameter_val,
            "door_offset": offset_val,
            "depth_z": view.spin_depth_z.value()
        }

        if current_main_idx == 2:
            payload["h_kon"] = view.spin_h_kon.value()
            payload["cut_vert_paz"] = (view.combo_vert_paz.currentIndex() == 1)
            payload["room_y"] = view.spin_room_y.value()
            payload["paz_z"] = view.spin_paz_z.value()

        return payload

    def collect_and_update(self):
        """Сбор данных сайдбара дисков и живое обновление чертежа"""
        current_main_idx = self.sidebar.combo_main_mode.currentIndex()
        
        # Разрешаем проход для Круга (0), Квадро (1) и Бабочки (2)
        if current_main_idx > 2:
            return

        payload = self._get_current_active_payload()
        
        # Передаем параметры в модель для геометрического расчета и отрисовки
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
