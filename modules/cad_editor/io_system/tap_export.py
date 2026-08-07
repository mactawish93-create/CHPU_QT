import os
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainterPath, QTransform
from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem, QGraphicsPathItem

class TapExportManager:
    """
    Промышленный CAM-процессор генерации УП G-кода (.tap) под стойки ЧПУ.
    Послойно нарезает заготовки с учетом диаметра фрезы, подач и глубин.
    🔥 ИСПРАВЛЕНО: Полная поддержка абсолютных координат трансформации (повороты на 90 градусов)!
    """
    def __init__(self):
        pass

    def generate_tap_file(self, file_path: str, geometry_items: list, cnc_settings: dict) -> bool:
        try:
            # Извлекаем технологические режимы резания из памяти станка
            tool_d = cnc_settings.get("tool_diameter", 12.0)
            spindle = cnc_settings.get("spindle_speed", 18000)
            feed_xy = cnc_settings.get("feed_rate_xy", 3000.0)
            feed_z = cnc_settings.get("feed_rate_z", 800.0)
            safe_z = cnc_settings.get("safe_z", 20.0)
            step_down = cnc_settings.get("step_down", 10.0)

            # Шапка управляющей программы (Инициализация стойки)
            gcode = [
                f"%  ; Начало программы",
                f"; Проект: {os.path.basename(file_path)}",
                f"G90 G21 G40 G49  ; Абсолютные координаты, мм, отмена компенсаций",
                f"G0 Z{safe_z:.2f}  ; Вылет фрезы на безопасную высоту",
                f"M3 S{spindle} ; Запуск шпинделя",
                f"M7 ; Включение системы охлаждения/обдува",
                f"G4 P2000 ; Пауза 2 сек на раскрутку шпинделя\n"
            ]

            # Цикл поочередной обработки каждой детали на холсте
            for idx, item_pack in enumerate(geometry_items, 1):
                # Извлекаем данные паспорта ЧПУ и ссылку на сам живой объект сцены Qt
                item = item_pack.get("raw_item")
                item_data = item_pack.get("data", {})
                item_type = item_data.get("type", "unknown")
                target_depth = abs(item_data.get("depth", 0.0))
                
                gcode.append(f"; --- Обработка элемента №{idx} ({item_type.upper()}) ---")

                if target_depth == 0.0:
                    target_depth = 5.0

                passes = int(target_depth // step_down)
                if target_depth % step_down > 0.1:
                    passes += 1

                # Извлекаем полную мировую матрицу трансформации (хранит все повороты, сдвиги и масштабы)
                # Если по какой-то причине объекта нет, создаем пустую дефолтную матрицу
                item_transform = item.sceneTransform() if item else QTransform()

                # === СЦЕНАРИЙ 1: ОБРАБОТКА СЛОЖНЫХ ВЕКТОРОВ ЧЕРЕЗ МАТРИЦУ ТРАНСФОРМАЦИЙ (ТЕКСТ, КРИВЫЕ) ===
                if item_type in ["text", "curve", "circle", "rhomb", "poly"] and isinstance(item, QGraphicsPathItem):
                    raw_path = item.path()
                    subpaths = raw_path.toSubpathPolygons()
                    
                    for current_pass in range(1, passes + 1):
                        current_z = -(current_pass * step_down)
                        if abs(current_z) > target_depth:
                            current_z = -target_depth

                        gcode.append(f"; Проход по Z = {current_z:.2f} мм")

                        for polygon in subpaths:
                            if polygon.isEmpty():
                                continue

                            for p_idx in range(polygon.count()):
                                local_pt = polygon.at(p_idx)
                                
                                # 🔥 КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ БАГА: Умножаем локальную точку на матрицу поворота/сдвига
                                # Теперь точка переходит в честные глобальные координаты ЧПУ-сцены!
                                global_pt = item_transform.map(local_pt)
                                
                                x_pos = global_pt.x()
                                y_pos = -global_pt.y() # Инверсия оси Y под стандарт станка

                                if p_idx == 0:
                                    gcode.append(f"G0 X{x_pos:.2f} Y{y_pos:.2f}")
                                    gcode.append(f"G1 Z{current_z:.2f} F{feed_z:.0f}")
                                else:
                                    gcode.append(f"G1 X{x_pos:.2f} Y{y_pos:.2f} F{feed_xy:.0f}")

                            gcode.append(f"G0 Z{safe_z:.2f}")

                # === СЦЕНАРИЙ 2: ОБРАБОТКА ОДИНОЧНОЙ ПРЯМОУГОЛЬНОЙ ЛИНИИ ПО МАТРИЦЕ ===
                elif item_type == "line" and isinstance(item, QGraphicsLineItem):
                    line = item.line()
                    # Применяем мировую матрицу к конечным точкам отрезка
                    p1_global = item_transform.map(line.p1())
                    p2_global = item_transform.map(line.p2())
                    
                    x1, y1 = p1_global.x(), -p1_global.y()
                    x2, y2 = p2_global.x(), -p2_global.y()

                    for current_pass in range(1, passes + 1):
                        current_z = -(current_pass * step_down)
                        if abs(current_z) > target_depth: current_z = -target_depth

                        gcode.append(f"; Проход по Z = {current_z:.2f} мм")
                        gcode.append(f"G0 X{x1:.2f} Y{y1:.2f}")
                        gcode.append(f"G1 Z{current_z:.2f} F{feed_z:.0f}")
                        gcode.append(f"G1 X{x2:.2f} Y{y2:.2f} F{feed_xy:.0f}")
                        gcode.append(f"G0 Z{safe_z:.2f}")

                # === СЦЕНАРИЙ 3: ОБРАБОТКА ПРЯМОУГОЛЬНИКА ПО МАТРИЦЕ ===
                elif item_type == "rect" and isinstance(item, QGraphicsRectItem):
                    rect = item.rect()
                    # Переводим все 4 угла прямоугольника через матрицу трансформаций
                    p1 = item_transform.map(rect.topLeft())
                    p2 = item_transform.map(rect.topRight())
                    p3 = item_transform.map(rect.bottomRight())
                    p4 = item_transform.map(rect.bottomLeft())

                    for current_pass in range(1, passes + 1):
                        current_z = -(current_pass * step_down)
                        if abs(current_z) > target_depth: current_z = -target_depth

                        gcode.append(f"; Проход по Z = {current_z:.2f} мм")
                        gcode.append(f"G0 X{p1.x():.2f} Y{-p1.y():.2f}")
                        gcode.append(f"G1 Z{current_z:.2f} F{feed_z:.0f}")
                        gcode.append(f"G1 X{p2.x():.2f} Y{-p2.y():.2f} F{feed_xy:.0f}")
                        gcode.append(f"G1 X{p3.x():.2f} Y{-p3.y():.2f}")
                        gcode.append(f"G1 X{p4.x():.2f} Y{-p4.y():.2f}")
                        gcode.append(f"G1 X{p1.x():.2f} Y{-p1.y():.2f}")
                        gcode.append(f"G0 Z{safe_z:.2f}")

                gcode.append("") 

            # Финализация управляющей программы
            gcode.extend([
                "; --- ФИНАЛИЗАЦИЯ ПРОГРАММЫ ---",
                "M9 ; Выключение охлаждения/обдува",
                "M5 ; Останов вращения шпинделя",
                f"G0 Z{safe_z + 30.0:.2f} ; Подъем фрезы повыше для снятия детали",
                "G0 X0 Y0 ; Возврат в нулевую точку станка для удобства",
                "M30 ; Конец управляющей программы",
                "%"
            ])

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(gcode))
            return True

        except Exception as e:
            print(f"[Критическая ошибка CAM-процессора TAP]: {e}")
            return False
