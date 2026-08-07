import os
import math

class PazGCodeGenerator:
    def __init__(self):
        pass

    def generate_banya_tap(self, geo: dict, params: dict) -> str:
        """Генерирует финальный текст управляющей программы (.tap) для Бани"""
        s_spindle = int(params.get("spindle_s", 30000))
        f_xy = int(params.get("feed_xy", 2000))
        f_z = int(params.get("feed_z", 500))
        
        lezhka_x = geo.get("lezhka_x", 2400.0)
        torec_z = geo.get("torec_z", -45.0)
        gcode_passes = geo.get("gcode_passes", [])
        torec_end_y = geo.get("gcode_torec_end", 0.0)
        torec_start_y = geo.get("torec_start_y", 0.0)

        lines = []
        
        # Шапка программы
        lines.append("M7")
        lines.append("G0Z80.000")
        lines.append(f"G0X0.000Y-0.500S{s_spindle}M3")
        lines.append("")

        # Операция 1: Стартовый торец (Бережем жертвенник, послойно пополам)
        z_half = torec_z / 2.0
        lines.append("(Стартовый торец)")
        lines.append("G0Z00.000")
        lines.append(f"G1Z{z_half:.3f}F{f_z}")
        lines.append(f"G1X{lezhka_x:.3f}F{f_xy}")
        lines.append(f"G1Z{torec_z:.3f}F{f_z}")
        lines.append(f"G1X0.000F{f_xy}")
        
        lines.append("(Стартовый торец, Чистовой проход)")
        lines.append(f"Y{torec_start_y:.3f}")
        lines.append(f"G1Z{torec_z:.3f}F{f_z}")
        lines.append(f"G1X{lezhka_x:.3f}F{f_xy}")
        lines.append("G0Z50.000")
        lines.append("")

        # Операция 2: Нарезка змейки пазов и герметика
        for block in gcode_passes:
            name = block["name"]
            passes_y = block["passes"]
            depth_z = block["depth"]
            
            lines.append(f"({name})")
            
            # --- ВНЕДРЕНО: Послойное деление Z по 20 мм для пазов Бани ---
            z_layers = self._calculate_z_layers(depth_z, 20.0)
            
            for z_current in z_layers:
                lines.append(f"(Слой Z = {z_current:.3f})")
                first_y = passes_y[0]
                lines.append(f"G0Z50.000")
                lines.append(f"G0X0.000Y{first_y:.3f}")
                lines.append("G0Z3.000")
                lines.append(f"G1Z{z_current:.3f}F{f_z}")
                
                is_forward = True
                for i, y_coord in enumerate(passes_y):
                    if i > 0:
                        lines.append(f"G1Y{y_coord:.3f}")
                    if is_forward:
                        lines.append(f"G1X{lezhka_x:.3f}F{f_xy}")
                    else:
                        lines.append(f"G1X0.000F{f_xy}")
                    is_forward = not is_forward
                    
                lines.append("G0Z50.000")
            lines.append("")

        # Операция 3: Финальный торец (Бережем жертвенник)
        lines.append("(Финальный торец)")
        lines.append(f"G0X0.000Y{torec_end_y + 0.5:.3f}")
        lines.append("G0Z0.000")
        lines.append(f"G1Z{z_half:.3f}F{f_z}")
        lines.append(f"G1X{lezhka_x:.3f}F{f_xy}")
        lines.append(f"G1Z{torec_z:.3f}F{f_z}")
        lines.append(f"G1X0.000F{f_xy}")
        
        lines.append("(Финальный торец, Чистовой проход)")
        lines.append(f"Y{torec_end_y:.3f}")
        lines.append(f"G1Z{torec_z:.3f}F{f_z}")
        lines.append(f"G1X{lezhka_x:.3f}F{f_xy}")
        lines.append("")

        # Подвал программы
        lines.append("G0Z80.000")
        lines.append("G0X0.000Y0.000")
        lines.append("M30")
        
        return "\n".join(lines)

    def generate_custom_tap(self, geo: dict, params: dict) -> str:
        """
        ИСПРАВЛЕНО: Генерирует финальный текст управляющей программы (.tap) 
        для ПОДРЕЖИМА ПРОИЗВОЛЬНОЙ ПАЗИРОВКИ с послойным резом Z по 10 мм.
        УБРАНЫ внешние торцы бани, чтобы не портить заготовку оператора.
        """
        s_spindle = int(params.get("spindle_s", 30000))
        f_xy = int(params.get("feed_xy", 2000))
        f_z = int(params.get("feed_z", 500))
        
        lezhka_x = geo.get("lezhka_x", 2400.0)
        gcode_passes = geo.get("gcode_passes", [])

        lines = []
        
        # =========================================================================
        # 👑 ШАПКА ПРОГРАММЫ (Старт и вылет на безопасную высоту)
        # =========================================================================
        lines.append("M7")                                      # Включение аспирации
        lines.append("G0Z80.000")                                # Полная безопасная высота
        lines.append(f"G0X0.000Y0.000S{s_spindle}M3")            # Запуск шпинделя в нуле стола
        lines.append("")

        # =========================================================================
        # 🌀 ГЛАВНЫЙ ЦИКЛ: НАРЕЗКА ПРОИЗВОЛЬНЫХ ЭЛЕМЕНТОВ ПО СЛОЯМ Z
        # =========================================================================
        for block in gcode_passes:
            name = block["name"]
            passes_y = block["passes"]
            depth_z = block["depth"]
            length_x = block["length_x"]  # Индивидуальная длина по X
            block_type = block["type"]
            
            lines.append(f"({name})")
            
            # Послойное деление Z по 10 мм (Бережем фрезу и шпиндель)
            z_layers = self._calculate_z_layers(depth_z, 10.0)
            
            for z_current in z_layers:
                lines.append(f"(Слой Z = {z_current:.3f})")
                first_y = passes_y[0]
                lines.append(f"G0Z50.000")
                lines.append(f"G0X0.000Y{first_y:.3f}")
                lines.append("G0Z0.000")
                lines.append(f"G1Z{z_current:.3f}F{f_z}")
                
                if block_type == "custom_slot":
                    # Нарезаем многопроходную змейку произвольного паза
                    is_forward = True
                    for i, y_coord in enumerate(passes_y):
                        if i > 0:
                            lines.append(f"G1Y{y_coord:.3f}")
                        if is_forward:
                            lines.append(f"G1X{length_x:.3f}F{f_xy}")
                        else:
                            lines.append(f"G1X0.000F{f_xy}")
                        is_forward = not is_forward
                else:
                    # Произвольный внутренний торец (отрез) за один проход по X
                    lines.append(f"G1X{length_x:.3f}F{f_xy}")
                    
                lines.append("G0Z50.000")
            lines.append("")

        # =========================================================================
        # 🛑 ПОДВАЛ ПРОГРАММЫ (Завершение и остановка станка)
        # =========================================================================
        lines.append("G0Z80.000")                                # Полный подъем вверх
        lines.append("G0X0.000Y0.000")                          # Возврат в ноль стола
        lines.append("M30")                                      # Конец УП
        
        return "\n".join(lines)

    def _calculate_z_layers(self, target_z: float, max_step: float) -> list:
        """
        Внутренний ЧПУ-калькулятор слоев по Z.
        Дробит целевую глубину на равномерные безопасные шаги не более max_step (10 мм).
        """
        target_abs = abs(target_z)
        if target_abs <= 0.001:
            return [0.0]
            
        # Считаем количество слоев (округление вверх)
        layers_count = math.ceil(target_abs / max_step)
        
        # Рассчитываем точный равномерный шаг для каждого слоя
        actual_step = target_abs / layers_count
        
        # Генерируем массив отрицательных координат по Z
        layers = []
        for i in range(1, layers_count + 1):
            z_val = -(i * actual_step)
            layers.append(round(z_val, 3))
        return layers
    def generate_plane_tap(self, geo: dict, params: dict) -> str:
        """
        Генерирует финальный текст управляющей программы (.tap) 
        для ПОДРЕЖИМА ВЫРАВНИВАНИЯ СТОЛА с послойным резом Z по 10 мм.
        """
        s_spindle = int(params.get("spindle_s", 30000))
        f_xy = int(params.get("feed_xy", 2000))
        f_z = int(params.get("feed_z", 500))
        
        length_y = geo.get("physical_length", 0.0)
        length_x = geo.get("lezhka_x", 2400.0)
        gcode_passes = geo.get("gcode_passes", [])
        strategy = geo.get("strategy", "Зигзаг по Y")

        lines = []
        
        # Шапка программы ЧПУ
        lines.append("M7")
        lines.append("G0Z80.000")
        lines.append(f"G0X0.000Y0.000S{s_spindle}M3")
        lines.append("")

        for block in gcode_passes:
            name = block["name"]
            depth_z = block["depth"]
            step_coordinates = block["step_coordinates"] # Массив шагов по противоположной оси
            main_length = block["main_length"]           # Длина длинного прохода
            
            lines.append(f"({name})")
            
            # Дробим съем по Z на слои не более 10 мм
            z_layers = self._calculate_z_layers(depth_z, 10.0) if depth_z != 0 else [0.0]
            
            for z_current in z_layers:
                lines.append(f"(Слой Z = {z_current:.3f})")
                lines.append("G0Z50.000")
                lines.append("G0X0.000Y0.000")
                lines.append("G0Z0.000")
                lines.append(f"G1Z{z_current:.3f}F{f_z}")
                
                is_forward = True
                
                if strategy == "Зигзаг по Y":
                    # Режем вдоль Y, шагаем по X
                    for i, x_coord in enumerate(step_coordinates):
                        if i > 0:
                            lines.append(f"G1X{x_coord:.3f}F{f_xy}") # Смещение по X на следующий проход
                        
                        y_target = length_y if is_forward else 0.0
                        lines.append(f"G1Y{y_target:.3f}F{f_xy}")    # Рабочий ход по Y
                        is_forward = not is_forward
                else:
                    # Режем вдоль X, шагаем по Y
                    for i, y_coord in enumerate(step_coordinates):
                        if i > 0:
                            lines.append(f"G1Y{y_coord:.3f}F{f_xy}") # Смещение по Y
                        
                        x_target = length_x if is_forward else 0.0
                        lines.append(f"G1X{x_target:.3f}F{f_xy}")    # Рабочий ход по X
                        is_forward = not is_forward
                        
                lines.append("G0Z50.000")
            lines.append("")

        # Подвал программы
        lines.append("G0Z80.000")
        lines.append("G0X0.000Y0.000")
        lines.append("M30")
        
        return "\n".join(lines)

    def generate_round_disk_tap(self, geo: dict, banya_params: dict, disks_payload: dict) -> str:
        """
        Автономный ЧПУ-генератор для нарезки Круглых дисков (2012, 2162, 2312 мм)
        с послойным съемом по Z не более 10 мм и интеграцией оригинальных проемов.
        """
        # 1. Забираем общие подачи и обороты шпинделя из параметров бани
        s_spindle = int(banya_params.get("spindle_s", 30000))
        f_xy = int(banya_params.get("feed_xy", 2000))
        f_z = int(banya_params.get("feed_z", 500))
        
        # 2. Параметры геометрии диска
        diameter_nominal = disks_payload.get("diameter", 2000.0)
        sub_mode = disks_payload.get("sub_mode", "Глухой диск")
        door_offset = disks_payload.get("door_offset", 0.0)
        target_z = disks_payload.get("depth_z", 0.0) # Целевая глубина реза
        
        # Фактический диаметр ЧПУ-траектории сдвигается наружу на диаметр фрезы 12 мм!
        # Радиус для 2000 -> 1006 мм (диам. 2012), для 2150 -> 1081 мм (диам. 2162), для 2300 -> 1156 мм (диам. 2312)
        c_radius = (diameter_nominal / 2.0) + 6.0 
        
        lines = []
        
        # =========================================================================
        # 👑 ШАГ 1: СТАНДАРТНАЯ ЦЕХОВАЯ ШАПКА
        # =========================================================================
        lines.append("M7")                                      # Включение аспирации
        lines.append("G0Z100.000")                               # Безопасная высота вылета
        lines.append(f"G0X0.000Y0.000S{s_spindle}M3")            # Ноль стола в центре, пуск шпинделя
        lines.append("")

        # Рассчитываем динамические слои по Z (правило: не более 10 мм за один проход)
        z_layers = self._calculate_z_layers(target_z, 10.0) if target_z != 0 else [0.0]

        # =========================================================================
        # 🌀 ШАГ 2: ПОСЛОЙНЫЙ ЦИКЛ ОБРАБОТКИ ВСЕГО ЩИТА ПО Z
        # =========================================================================
        for layer_idx, z_current in enumerate(z_layers):
            lines.append(f"(--- СЛОЙ ОБРАБОТКИ №{layer_idx + 1} | Z = {z_current:.3f} ---)")
            
            # --- А) КРУГОВОЙ ОБВОД КОНТУРА ДИСКА (2012, 2162, 2312 мм) ---
            lines.append(f"(Внешний контур диска)")
            lines.append(f"G0X0.000Y{c_radius:.3f}")             # Подлет к верхней пиковой точке
            lines.append("G0Z5.000")                              # Быстрое опускание до припуска
            lines.append(f"G1Z{z_current:.3f}F{f_z}")             # Врезание в материал на текущий слой
            # Полный оборот по часовой стрелке G2. Центр круга в X0 Y0, поэтому J равен минус радиус
            lines.append(f"G2X0.000Y{c_radius:.3f}I0.000J-{c_radius:.3f}F{f_xy}")
            lines.append("G0Z50.000")                             # Безопасный подъем для перелета
            lines.append("")
            
            # --- Б) ИНТЕГРАЦИЯ ИСПРАВЛЕННОГО ЗАВОДСКОГО G-КОДА ДВЕРНОГО ПРОЕМА ---
            if sub_mode == "Диск с проемом":
                lines.append(f"(Внутренний прорез окна двери)")
                
                if diameter_nominal == 2300.0:
                    if door_offset == 100.0:
                        lines.append(f"G0X0.000Y782.000")
                        lines.append(f"G1Z{z_current:.3f}F{f_z}")
                        lines.append(f"G1X0.000Y782.000F{f_xy}\nG1X276.000Y782.000\nG1X276.000Y762.000\nG1X254.000Y762.000\nG1X254.000Y-970.000\nG1X276.000Y-970.000\nG1X276.000Y-990.000\nG1X-476.000Y-990.000\nG1X-476.000Y-970.000\nG1X-454.000Y-970.000\nG1X-454.000Y762.000\nG1X-476.000Y762.000\nG1X-476.000Y782.000\nG1X0.000Y782.000")
                    elif door_offset == 150.0:
                        lines.append(f"G0X0.000Y782.000")
                        lines.append(f"G1Z{z_current:.3f}F{f_z}")
                        lines.append(f"G1X0.000Y782.000F{f_xy}\nG1X236.000Y782.000\nG1X236.000Y762.000\nG1X214.500Y762.000\nG1X214.500Y-970.000\nG1X236.000Y-970.000\nG1X236.000Y-990.000\nG1X-516.000Y-990.000\nG1X-516.000Y-970.000\nG1X-494.500Y-970.000\nG1X-494.500Y762.000\nG1X-516.000Y762.000\nG1X-516.000Y782.000\nG1X0.000Y782.000")
                    else: # Смещение 0
                        lines.append(f"G0X0.000Y782.000")
                        lines.append(f"G1Z{z_current:.3f}F{f_z}")
                        lines.append(f"G1X0.000Y782.000F{f_xy}\nG1X376.000Y782.000\nG1X376.000Y762.000\nG1X354.000Y762.000\nG1X354.000Y-970.000\nG1X376.000Y-970.000\nG1X376.000Y-990.000\nG1X-376.000Y-990.000\nG1X-376.000Y-970.000\nG1X-354.000Y-970.000\nG1X-354.000Y762.000\nG1X-376.000Y762.000\nG1X-376.000Y782.000\nG1X0.000Y782.000")
                
                elif diameter_nominal == 2000.0 and door_offset == 100.0:
                    lines.append(f"G0X0.000Y836.000")
                    lines.append(f"G1Z{z_current:.3f}F{f_z}")
                    lines.append(f"G1X0.000Y836.000F{f_xy}\nG1X276.000Y836.000\nG1X276.000Y816.000\nG1X254.000Y816.000\nG1X254.000Y-816.000\nG1X276.000Y-816.000\nG1X276.000Y-836.000\nG1X-476.000Y-836.000\nG1X-476.000Y-816.000\nG1X-454.000Y-816.000\nG1X-454.000Y816.000\nG1X-476.000Y816.000\nG1X-476.000Y836.000\nG1X0.000Y836.000")
                
                else: # Стандартный проем для 2150 (все смещения) и 2000 без смещения
                    if door_offset == 100.0:
                        lines.append(f"G0X-100.000Y886.000")
                        lines.append(f"G1Z{z_current:.3f}F{f_z}")
                        lines.append(f"G1X-100.000Y886.000F{f_xy}\nG1X276.000Y886.000\nG1X276.000Y866.000\nG1X254.000Y866.000\nG1X254.000Y-866.000\nG1X276.000Y-866.000\nG1X276.000Y-886.000\nG1X-476.000Y-886.000\nG1X-476.000Y-866.000\nG1X-454.000Y-866.000\nG1X-454.000Y866.000\nG1X-476.000Y866.000\nG1X-476.000Y886.000\nG1X0.000Y886.000")
                    elif door_offset == 150.0:
                        lines.append(f"G0X0.000Y886.000")
                        lines.append(f"G1Z{z_current:.3f}F{f_z}")
                        lines.append(f"G1X0.000Y886.000F{f_xy}\nG1X226.000Y886.000\nG1X226.000Y866.000\nG1X204.000Y866.000\nG1X204.000Y-866.000\nG1X226.000Y-866.000\nG1X226.000Y-886.000\nG1X-526.000Y-886.000\nG1X-526.000Y-866.000\nG1X-504.000Y-866.000\nG1X-504.000Y866.000\nG1X-526.000Y866.000\nG1X-526.000Y886.000\nG1X0.000Y886.000")
                    else: # Смещение 0
                        lines.append(f"G0X0.000Y886.000")
                        lines.append(f"G1Z{z_current:.3f}F{f_z}")
                        lines.append(f"G1X0.000Y886.000F{f_xy}\nG1X376.000Y886.000\nG1X376.000Y866.000\nG1X354.000Y866.000\nG1X354.000Y-866.000\nG1X376.000Y-866.000\nG1X376.000Y-886.000\nG1X-376.000Y-886.000\nG1X-376.000Y-866.000\nG1X-354.000Y-866.000\nG1X-354.000Y866.000\nG1X-376.000Y866.000\nG1X-376.000Y886.000\nG1X0.000Y886.000")
                
                lines.append("G0Z50.000")
                lines.append("")
                
        # =========================================================================
        # 🛑 ШАГ 3: ПОДВАЛ ПРОГРАММЫ С ОСТАНОВОМ
        # =========================================================================
        lines.append("G0Z80.000")
        lines.append("G0X0.000Y0.000")
        lines.append("M30")
        
        return "\n".join(lines)
