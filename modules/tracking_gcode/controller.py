import os
import re
import math
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from modules.tracking_gcode.sidebar import GCodeSidebar
from modules.tracking_gcode.canvas import GCodeCanvas

class GCodeController:
    def __init__(self):
        # 1. Инициализируем компоненты верификатора УП
        self.sidebar = GCodeSidebar()
        self.canvas = GCodeCanvas()
        
        # Внутренние базы данных для хранения распарсенной траектории
        self.raw_lines = []        
        self.geometry_blocks = []  
        self.line_to_coord_map = {} 
        
        # Габариты детали по умолчанию
        self.min_x, self.max_x = 0.0, 0.0
        self.min_y, self.max_y = 0.0, 0.0

        # 2. Подключаем слушатели сигналов
        self._connect_signals()

    def get_widgets(self):
        """Возвращает пару виджетов для главного стека приложения"""
        return self.sidebar, self.canvas

    def _connect_signals(self):
        """Привязываем кнопки и навигацию стрелочками к логике"""
        self.sidebar.btn_load_gcode.clicked.connect(self._on_load_file_clicked)
        self.sidebar.btn_generate_dxf.clicked.connect(self._export_trajectory_to_dxf)
        self.sidebar.list_lines.currentRowChanged.connect(self._on_terminal_row_changed)

    def _on_load_file_clicked(self):
        """Слот: открывает проводник Windows и запускает построчный CAM-парсер"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.sidebar, "Открыть управляющую программу ЧПУ", "", "Файлы ЧПУ (*.tap *.txt *.nc);;Все файлы (*.*)"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self._parse_gcode_content(content)
            QMessageBox.information(self.sidebar, "Успех", f"Файл УП успешно загружен и верифицирован!\nСтрок прочитано: {len(self.raw_lines)}")
        except Exception as e:
            QMessageBox.critical(self.sidebar, "Ошибка", f"Не удалось прочитать файл.\nПричина: {str(e)}")

    def _parse_gcode_content(self, text: str):
        """Внутренний CAM-движок: разбирает логику перемещений G0/G1/G2/G3 и аппроксимирует дуги"""
        self.raw_lines = text.splitlines()
        self.geometry_blocks = []
        self.line_to_coord_map = {}
        
        curr_x, curr_y = 0.0, 0.0
        curr_g_mode = "G0" 
        xs, ys = [0.0], [0.0] # Базовый ноль, чтобы избежать пустоты

        # Регулярные выражения для молниеносного выуживания координат и параметров дуг
        x_re = re.compile(r'[XX]([-+]?\d*\.\d+|\d+)')
        y_re = re.compile(r'[YY]([-+]?\d*\.\d+|\d+)')
        i_re = re.compile(r'[II]([-+]?\d*\.\d+|\d+)')
        j_re = re.compile(r'[JJ]([-+]?\d*\.\d+|\d+)')
        g_re = re.compile(r'[GG](\d+)')

        for idx, line in enumerate(self.raw_lines):
            # Отсекаем комментарии в строке (все, что в скобках), чтобы они не мешали парсингу координат
            line_no_comments = re.sub(r'\(.*?\)', '', line)
            clean_line = line_no_comments.strip().upper()
            if not clean_line:
                continue 
                
            g_match = g_re.search(clean_line)
            if g_match:
                g_num = int(g_match.group(1))
                if 0 <= g_num <= 3:
                    curr_g_mode = f"G{g_num}"

            # Парсим координаты текущей строки
            x_match = x_re.search(clean_line)
            y_match = y_re.search(clean_line)
            i_match = i_re.search(clean_line)
            j_match = j_re.search(clean_line)
            
            has_move = x_match or y_match or i_match or j_match
            
            if has_move:
                old_x, old_y = curr_x, curr_y
                
                # Если в кадре не указаны X или Y, они наследуются из предыдущих координат
                if x_match: curr_x = float(x_match.group(1))
                if y_match: curr_y = float(y_match.group(1))
                
                xs.append(curr_x)
                ys.append(curr_y)
                self.line_to_coord_map[idx] = (curr_x, curr_y)
                
                # РОУТЕР ИНТЕРПОЛЯЦИИ: Линейная (G0/G1) или Круговая (G2/G3)
                if curr_g_mode in ["G0", "G1"]:
                    self.geometry_blocks.append({
                        "type": curr_g_mode,
                        "geom_type": "line",
                        "x1": old_x, "y1": old_y,
                        "x2": curr_x, "y2": curr_y
                    })
                # Логика аппроксимации дуг G2/G3 продолжается во второй части...
                elif curr_g_mode in ["G2", "G3"]:
                    # --- ВНЕДРЕНО: Математическая аппроксимация круговой интерполяции I/J ---
                    # I и J — относительные смещения от начальной точки (old_x, old_y) до центра дуги
                    i_val = float(i_match.group(1)) if i_match else 0.0
                    j_val = float(j_match.group(1)) if j_match else 0.0
                    
                    # Координаты центра окружности
                    center_x = old_x + i_val
                    center_y = old_y + j_val
                    
                    # Вычисляем радиус по Пифагору
                    radius = math.hypot(old_x - center_x, old_y - center_y)
                    
                    if radius > 0.1:
                        # Находим углы старта и финиша в радианах относительно центра дуги
                        start_angle = math.atan2(old_y - center_y, old_x - center_x)
                        end_angle = math.atan2(curr_y - center_y, curr_x - center_x)
                        
                        # Если точки старта и финиша совпадают (полный круг 360 градусов, как на обводе диска),
                        # то принудительно задаем полный оборот в зависимости от направления G2/G3
                        if abs(old_x - curr_x) < 0.01 and abs(old_y - curr_y) < 0.01:
                            if curr_g_mode == "G2": # По часовой стрелке
                                end_angle = start_angle - 2.0 * math.pi
                            else: # Против часовой стрелки
                                end_angle = start_angle + 2.0 * math.pi
                                
                        # Нарезаем дугу на 128 микросегментов для идеальной плавной неоновой линии
                        num_segments = 128
                        angle_step = (end_angle - start_angle) / num_segments
                        
                        prev_step_x, prev_step_y = old_x, old_y
                        
                        for s in range(1, num_segments + 1):
                            curr_angle = start_angle + angle_step * s
                            step_x = center_x + radius * math.cos(curr_angle)
                            step_y = center_y + radius * math.sin(curr_angle)
                            
                            # Запоминаем точки для вычисления границ заготовки
                            xs.append(step_x)
                            ys.append(step_y)
                            
                            self.geometry_blocks.append({
                                "type": curr_g_mode,
                                "geom_type": "line",
                                "x1": prev_step_x, "y1": prev_step_y,
                                "x2": step_x, "y2": step_y
                            })
                            prev_step_x, prev_step_y = step_x, step_y

        # Фиксируем пиковые габариты детали по результатам проходов
        if xs and ys:
            self.min_x, self.max_x = min(xs), max(xs)
            self.min_y, self.max_y = min(ys), max(ys)
        else:
            self.min_x, self.max_x, self.min_y, self.max_y = 0.0, 0.0, 0.0, 0.0

        # Обновляем виджеты
        self.sidebar.load_lines_to_view(self.raw_lines)
        self.canvas.draw_gcode_trajectory(self.geometry_blocks, self.min_x, self.max_x, self.min_y, self.max_y)

    def _on_terminal_row_changed(self, current_row_idx):
        """Слот: срабатывает при перемещении по строкам ЧПУ стрелочками клавиатуры"""
        if current_row_idx in self.line_to_coord_map:
            x, y = self.line_to_coord_map[current_row_idx]
            self.canvas.update_tool_marker(x, y)
        else:
            self.canvas.update_tool_marker(None, None)

    def _export_trajectory_to_dxf(self):
        """
        📐 ЧИСТЫЙ СКРИПТ КОНВЕРТАЦИИ G-КОДА В CAD DXF
        """
        if not self.geometry_blocks:
            QMessageBox.warning(self.sidebar, "DXF Экспорт", "Сначала загрузите рабочий G-код программы ЧПУ!")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self.sidebar, "Экспортировать чертеж траектории в DXF", "", "Векторный файл CAD (*.dxf)"
        )
        if not file_path:
            return
            
        dxf_lines = []
        dxf_lines.extend(["  0", "SECTION", "  2", "ENTITIES"])
        
        for block in self.geometry_blocks:
            if block["type"] != "G0":
                dxf_lines.extend(["  0", "LINE"])
                dxf_lines.extend(["  8", "CNC_TRAJECTORY"])
                
                dxf_lines.extend([" 10", f"{block['x1']:.3f}"])
                dxf_lines.extend([" 20", f"{block['y1']:.3f}"])
                
                dxf_lines.extend([" 11", f"{block['x2']:.3f}"])
                dxf_lines.extend([" 21", f"{block['y2']:.3f}"])
                
        dxf_lines.extend(["  0", "ENDSEC", "  0", "EOF"])
        
        try:
            with open(file_path, "w", encoding="ascii") as dxf_file:
                dxf_file.write("\n".join(dxf_lines))
            QMessageBox.information(self.sidebar, "Экспорт успешен", f"Векторный чертеж траектории сохранен в DXF:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self.sidebar, "Ошибка DXF", f"Не удалось записать файл чертежа.\nПричина: {str(e)}")
