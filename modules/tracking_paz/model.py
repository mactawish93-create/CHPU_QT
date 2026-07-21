import math

class PazModel:
    def __init__(self):
        pass

    def calculate_banya_geometry(self, params: dict) -> dict:
        """
        Чистый математический CAM-процессор для пазировки бани.
        Рассчитывает честные цеховые миллиметры с учетом привязки нуля 
        к ПЕРЕДНЕМУ КРАЮ фрезы.
        """
        # 1. Извлекаем базовые параметры из сайдбара
        mill_dia = params.get("mill_dia", 12.0)
        torec_z = params.get("torec_z", -45.0)
        lezhka_x = params.get("lezhka_x", 2400.0)
        back_vypusk = params.get("back_vypusk", 50.0)
        
        # Защищенные параметры (если чекбокс выключен, берутся заводские дефолты)
        paz_w = params.get("paz_w", 45.0) if params.get("ch_paz_w") else 45.0
        paz_z = params.get("paz_z", -20.0) if params.get("ch_paz_z") else -20.0
        front_vypusk = params.get("front_vypusk", 50.0) if params.get("ch_front") else 50.0
        
        sub_mode = params.get("sub_mode", "Верх трубы") # "Верх трубы" или "Низ трубы"
        
        # Герметик
        germ_w = params.get("germ_w", 5.0) if params.get("ch_germ_w") else 5.0
        germ_z = params.get("germ_z", 5.0) if params.get("ch_germ_z") else 5.0

        # 2. Расчет структуры деревянного щита (Ламели по 135 мм)
        lamels = []
        current_lamel_x = 135.0
        while current_lamel_x < lezhka_x:
            lamels.append(current_lamel_x)
            current_lamel_x += 135.0

        # 3. Динамический расчет цепочки пазов и комнат по оси Y
        # Списки для хранения геометрии (координаты начала и конца элементов на брусе)
        slots_geometry = []
        germetik_geometry = []
        gcode_passes_y = []  # Точные координаты по оси Y для генерации G-кода
        
        # Начинаем строить физическую деталь от нуля щита
        y_current_physical = 0.0
        
        # А) Передний выпуск
        y_current_physical += front_vypusk
        
        # Б) Расчет первого основного паза
        slot_1_start = y_current_physical
        slot_1_end = slot_1_start + paz_w
        slots_geometry.append((slot_1_start, slot_1_end))
        
        # Автоматический расчет змейки для Паза №1
        passes_1 = self._generate_snake_passes(slot_1_start, paz_w, mill_dia)
        gcode_passes_y.append({"type": "slot", "name": "Паз 1", "passes": passes_1, "depth": paz_z})
        
        # Специфика "Низа трубы" для первого паза (Стартовый герметик)
        if sub_mode == "Низ трубы":
            # Центр фрезы герметика идет встык со смещением
            # В старой программе жестко зашито: старт первого прохода змейки минус 4.5 мм
            y_germ_1 = passes_1[0] - 4.5
            germetik_geometry.append((slot_1_start - germ_w, slot_1_start))
            gcode_passes_y.append({"type": "germetik", "name": "Герметик 1", "passes": [y_germ_1], "depth": -abs(germ_z)})

        # Перемещаем указатель за первый паз
        y_current_physical = slot_1_end

        # В) Цикл обработки активных комнат (от 1 до 5)
        active_rooms_data = params.get("rooms", []) # Список кортежей: (is_active, length)
        
        slot_counter = 2
        for is_active, room_length in active_rooms_data:
            if not is_active:
                break # Если чекбокс выключен — цепочка комнат на этом месте прерывается
                
            # Шагаем на длину комнаты
            y_current_physical += room_length
            
            # Строим следующий паз сразу за комнатой
            slot_start = y_current_physical
            slot_end = slot_start + paz_w
            slots_geometry.append((slot_start, slot_end))
            
            # Считаем змейку для этого паза
            passes = self._generate_snake_passes(slot_start, paz_w, mill_dia)
            gcode_passes_y.append({"type": "slot", "name": f"Паз {slot_counter}", "passes": passes, "depth": paz_z})
            
            slot_counter += 1
            y_current_physical = slot_end

        # Г) Специфика "Низа трубы" для ПОСЛЕДНЕГО паза (Конечный герметик)
        if sub_mode == "Низ трубы" and gcode_passes_y:
            # Ищем проходы последнего добавленного основного паза
            last_slot_passes = [p for p in gcode_passes_y if p["type"] == "slot"][-1]["passes"]
            # В старой программе: последний проход змейки плюс 3.5 мм
            y_germ_last = last_slot_passes[-1] + 3.5
            germetik_geometry.append((y_current_physical, y_current_physical + germ_w))
            gcode_passes_y.append({"type": "germetik", "name": f"Герметик {slot_counter-1}", "passes": [y_germ_last], "depth": -abs(germ_z)})

        # Д) Задний выпуск
        y_current_physical += back_vypusk
        
        # 4. ФИНАЛЬНЫЙ РАСЧЕТ ДЛИНЫ И ТОРЦЕВ В УП
        # Физическая чистая длина деревянного щита в миллиметрах
        physical_total_length = y_current_physical
        
        # Передний торец (левый край щита) режется передней кромкой фрезы -> координата Y=0.0
        gcode_torec_start = 0.0
        
        # Задний торец (правый край щита) режется ЗАДНЕЙ кромкой фрезы -> координата Y_физ + Диаметр
        gcode_torec_end = physical_total_length + mill_dia

        # Формируем итоговый пакет геометрии для контроллера и 2D-холста
        return {
            "physical_length": physical_total_length,  # Чистый размер дерева
            "gcode_torec_end": gcode_torec_end,        # Координата финиша в УП (например, 4012.0)
            "lezhka_x": lezhka_x,                      # Ширина щита
            "torec_z": torec_z,                        # Глубина торцевания
            "lamels": lamels,                          # Линии досок по 135 мм
            "slots": slots_geometry,                   # Список пар (y_start, y_end) для основных пазов
            "germetik": list(set(germetik_geometry)),  # Пазы герметика
            "gcode_passes": gcode_passes_y,            # Структурированный массив для G-кода
            "torec_start_y": gcode_torec_start
        }

    def calculate_custom_geometry(self, params: dict) -> dict:
        """
        Математический CAM-процессор для ПОДРЕЖИМА ПРОИЗВОЛЬНОЙ ПАЗИРОВКИ.
        Рассчитывает произвольную геометрию с АДАПТИВНОЙ ВЫСОТОЙ БРУСА по оси X
        и привязкой нуля к ПЕРЕДНЕМУ КРАЮ фрезы.
        """
        mill_dia = params.get("mill_dia", 12.0)
        torec_z = params.get("torec_z", -45.0)
        
        active_slots = params.get("slots", [])    
        active_torecs = params.get("torecs", [])  

        # =========================================================================
        # 📏 ШАГ 1: АВТОМАТИЧЕСКИЙ РАСЧЕТ ГАБАРИТОВ БРУСА (И ДЛИНА Y, И ВЫСОТА X)
        # =========================================================================
        max_y_endpoint = 100.0  # Минимальный стартовый габарит длины по Y
        max_x_height = 150.0    # ИСПРАВЛЕНО: Минимальная стартовая высота бруса по X
        
        for slot in active_slots:
            # Считаем максимальную длину по Y
            end_p = slot["offset"] + slot["width"]
            if end_p > max_y_endpoint:
                max_y_endpoint = end_p
            # ИСПРАВЛЕНО: Ищем максимальную длину паза по оси X
            if slot["length"] > max_x_height:
                max_x_height = slot["length"]
                
        for torec in active_torecs:
            end_p = torec["offset"] + mill_dia
            if end_p > max_y_endpoint:
                max_y_endpoint = end_p
            # ИСПРАВЛЕНО: Ищем максимальную длину торца по оси X
            if torec["length"] > max_x_height:
                max_x_height = torec["length"]
                
        # Добавляем к высоте небольшой технологический запас в 20 мм для красивого визуала
        adaptive_lezhka_x = max_x_height + 20.0
        
        # Полная физическая длина дерева с задним выпуском 50 мм
        physical_total_length = max_y_endpoint + 50.0
        
        gcode_torec_start = 0.0
        gcode_torec_end = physical_total_length + mill_dia

        # =========================================================================
        # 🪵 ШАГ 2: СТРУКТУРА ЩИТА (ЛАМЕЛИ ПО 135 ММ ДО АДАПТИВНОЙ ВЫСОТЫ)
        # =========================================================================
        lamels = []
        current_lamel_x = 135.0
        while current_lamel_x < adaptive_lezhka_x:
            lamels.append(current_lamel_x)
            current_lamel_x += 135.0

        # =========================================================================
        # 🌀 ШАГ 3: РАСЧЕТ ИНДИВИДУАЛЬНЫХ ТРАЕКТОРИЙ И ЗМЕЕК
        # =========================================================================
        slots_geometry = []
        torecs_geometry = []
        gcode_passes_y = []  

        # А) Обработка ручных пазов
        for index, slot in enumerate(active_slots):
            s_width = slot["width"]
            s_length = slot["length"]
            s_depth = slot["depth"]
            s_offset = slot["offset"]
            
            # Если длина вбита как 0 — автоматически расправляем паз на всю адаптивную высоту бруса
            actual_paz_x = s_length if s_length > 0 else max_x_height
            slots_geometry.append((s_offset, s_offset + s_width, actual_paz_x))
            
            passes = self._generate_snake_passes(s_offset, s_width, mill_dia)
            gcode_passes_y.append({
                "type": "custom_slot",
                "name": f"Произв. Паз {index + 1}",
                "passes": passes,
                "depth": -abs(s_depth) if s_depth != 0 else -20.0,
                "length_x": actual_paz_x
            })

        # Б) Обработка ручных торцев
        for index, torec in enumerate(active_torecs):
            t_depth = torec["depth"]
            t_length = torec["length"]
            t_offset = torec["offset"]
            
            actual_torec_x = t_length if t_length > 0 else max_x_height
            torecs_geometry.append((t_offset, actual_torec_x))
            
            y_pass = t_offset + mill_dia
            gcode_passes_y.append({
                "type": "custom_torec",
                "name": f"Произв. Торец {index + 1}",
                "passes": [round(y_pass, 3)],
                "depth": -abs(t_depth) if t_depth != 0 else torec_z,
                "length_x": actual_torec_x
            })

        return {
            "physical_length": physical_total_length,
            "gcode_torec_end": gcode_torec_end,
            "lezhka_x": adaptive_lezhka_x,            # Передаем адаптивную высоту заготовки
            "torec_z": torec_z,
            "lamels": lamels,
            "slots": slots_geometry,
            "custom_torecs": torecs_geometry,
            "gcode_passes": gcode_passes_y,
            "torec_start_y": gcode_torec_start,
            "slots_geometry_type": 1                  # Флаг для холста, что это ручной режим
        }

    def calculate_plane_geometry(self, params: dict) -> dict:
        """
        Математический CAM-процессор для ПОДРЕЖИМА ВЫРАВНИВАНИЯ ПЛОСКОСТИ.
        Рассчитывает траекторию змейки проходов по осям X/Y с учетом 
        процента перекрытия фрезы и послойного съема по Z не более 10 мм.
        """
        # 1. Извлекаем параметры из формы калибровки
        strategy = params.get("strategy", "Зигзаг по Y") # "Зигзаг по Y" или "Зигзаг по X"
        length_y = params.get("length_y", 0.0)
        length_x = params.get("length_x", 0.0)
        mill_dia = params.get("mill_dia", 12.0)
        stepover = params.get("stepover", 0.0)           # Перекрытие в процентах (0-100%)
        depth_z = params.get("depth_z", 0.0)             # Съем по Z
        torec_z = params.get("torec_z", -45.0)

        # Предотвращаем зависания и деление на ноль при пустом вводе
        if length_y <= 0 or length_x <= 0 or mill_dia <= 2.0:
            return {
                "physical_length": 300.0, "lezhka_x": 200.0, "lamels": [], 
                "slots": [], "gcode_passes": [], "slots_geometry_type": 2, "strategy": strategy
            }

        # 2. Расчет шага смещения фрезы с учетом перекрытия (Stepover)
        # Если перекрытие 0% — шаг равен полному диаметру фрезы. Если 50% — половине.
        step_factor = 1.0 - (stepover / 100.0)
        if step_factor <= 0.05: 
            step_factor = 0.05 # Защита от бесконечного цикла, если перекрытие вбили 100%
        actual_step = mill_dia * step_factor

        # 3. Нарезка визуальных ламелей (для имитации текстуры стола по 135 мм)
        lamels = []
        current_lamel_x = 135.0
        while current_lamel_x < length_x:
            lamels.append(current_lamel_x)
            current_lamel_x += 135.0

        # 4. ГЕНЕРАЦИЯ ТРАЕКТОРИИ ДЛЯ G-КОДА И ЧЕРТЕЖА
        gcode_passes = []
        snake_lines_for_canvas = [] # Массив линий для отрисовки змейки на холсте

        if strategy == "Зигзаг по Y":
            # Фреза бегает длинными проходами по Y, смещаясь по оси X
            # Считаем, сколько проходов по X нужно сделать, чтобы закрыть всю ширину стола
            passes_count = math.ceil(length_x / actual_step) + 1
            x_passes = []
            for i in range(passes_count):
                x_coord = i * (length_x / (passes_count - 1 if passes_count > 1 else 1))
                x_passes.append(round(x_coord, 3))

            # Передаем массив смещений по X в пакет проходов
            gcode_passes.append({
                "type": "plane_zigzag_y",
                "name": "Зигзаг по Y",
                "main_length": length_y,   # Длина рабочего прохода по оси Y
                "step_coordinates": x_passes, # Массив координат смещения по X
                "depth": -abs(depth_z) if depth_z != 0 else 0.0
            })

            # Генерируем ломаную линию для 2D-чертежа (визуальный трек центра фрезы)
            is_forward = True
            for i, x_coord in enumerate(x_passes):
                y_start = 0.0 if is_forward else length_y
                y_end = length_y if is_forward else 0.0
                
                # Добавляем рабочий проход по Y
                snake_lines_for_canvas.append((y_start, x_coord, y_end, x_coord))
                
                # Если это не последний проход, добавляем переходной мостик смещения по X
                if i < len(x_passes) - 1:
                    next_x = x_passes[i+1]
                    snake_lines_for_canvas.append((y_end, x_coord, y_end, next_x))
                is_forward = not is_forward

        else:
            # Стратегия "Зигзаг по X": фреза бегает вертикально по X, смещаясь по оси Y
            passes_count = math.ceil(length_y / actual_step) + 1
            y_passes = []
            for i in range(passes_count):
                y_coord = i * (length_y / (passes_count - 1 if passes_count > 1 else 1))
                y_passes.append(round(y_coord, 3))

            gcode_passes.append({
                "type": "plane_zigzag_x",
                "name": "Зигзаг по X",
                "main_length": length_x,   # Длина рабочего прохода по оси X
                "step_coordinates": y_passes, # Массив координат смещения по Y
                "depth": -abs(depth_z) if depth_z != 0 else 0.0
            })

            # Генерируем ломаную линию для 2D-чертежа
            is_forward = True
            for i, y_coord in enumerate(y_passes):
                x_start = 0.0 if is_forward else length_x
                x_end = length_x if is_forward else 0.0
                
                # Добавляем рабочий проход по X
                snake_lines_for_canvas.append((y_coord, x_start, y_coord, x_end))
                
                if i < len(y_passes) - 1:
                    next_y = y_passes[i+1]
                    snake_lines_for_canvas.append((y_coord, x_end, next_y, x_end))
                is_forward = not is_forward

        return {
            "physical_length": length_y,         # По оси Y — длина стола
            "lezhka_x": length_x,                # По оси X — ширина стола
            "torec_z": torec_z,
            "lamels": lamels,
            "slots": [],                         # Основных пазов в этом режиме нет
            "plane_snake_lines": snake_lines_for_canvas, # Векторный трек фрезы для холста
            "gcode_passes": gcode_passes,
            "slots_geometry_type": 2,            # Сигнал для холста, что это режим калибровки стола
            "strategy": strategy
        }

    def _generate_snake_passes(self, slot_start: float, paz_w: float, mill_dia: float) -> list:
        """
        Внутренний CAM-калькулятор автоматической змейки выборки паза.
        Рассчитывает равномерные шаги для любого диаметра фрезы.
        """
        # Первый проход (задней кромкой инструмента):
        y_first = slot_start + mill_dia
        
        # Последний проход (передней кромкой инструмента):
        y_last = slot_start + paz_w
        
        # Если ширина паза слишком мала или фреза огромная и перекрывает всё за один проход
        if y_first >= y_last:
            return [y_last]
            
        # Расстояние свободного хода, которое нужно раскидать на шаги
        y_zone = y_last - y_first
        
        # Безопасный шаг смещения фрезы за раз (максимум 80% от диаметра фрезы)
        max_safe_step = mill_dia * 0.8
        
        # Вычисляем минимальное количество шагов (округление вверх)
        steps_count = math.ceil(y_zone / max_safe_step) + 1
        if steps_count < 2:
            steps_count = 2
            
        # Вычисляем точный равномерный шаг смещения между проходами
        actual_step = y_zone / (steps_count - 1)
        
        # Генерируем точный массив координат по Y
        passes = []
        for i in range(steps_count):
            y_pass = y_first + (i * actual_step)
            passes.append(round(y_pass, 3)) # Округляем до 3 знаков (микроны ЧПУ)
            
        return passes
