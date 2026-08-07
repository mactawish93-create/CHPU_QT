import os

class DxfExchangeManager:
    """
    Класс для обмена данными с промышленным форматом DXF AutoCAD.
    Успешно читает файлы из SketchUp, AutoCAD и Компас-3D.
    Парсит примитивы LINE и автоматически взрывает полилинии (LWPOLYLINE).
    """
    def __init__(self):
        pass

    def export_to_dxf(self, file_path: str, geometry_items: list) -> bool:
        """Берет геометрические элементы редактора и преобразует их в DXF"""
        try:
            lines_to_write = []

            for item in geometry_items:
                item_type = item.get("type")
                depth = item.get("depth", 0.0)
                layer_name = f"CUT_{depth}mm" if depth > 0 else "BASE_CONTOUR"

                if item_type == "line":
                    lines_to_write.append({
                        "x1": item["x1"], "y1": item["y1"],
                        "x2": item["x2"], "y2": item["y2"],
                        "layer": layer_name
                    })
                elif item_type == "rect":
                    x, y = item["x"], item["y"]
                    w, h = item["width"], item["height"]
                    
                    p1, p2, p3, p4 = (x, y), (x + w, y), (x + w, y + h), (x, y + h)
                    edges = [(p1, p2), (p2, p3), (p3, p4), (p4, p1)]
                    for start, end in edges:
                        lines_to_write.append({
                            "x1": start[0], "y1": start[1],
                            "x2": end[0], "y2": end[1],
                            "layer": layer_name
                        })

            dxf_buffer = ["  0\nSECTION\n  2\nENTITIES\n"]

            for line in lines_to_write:
                dxf_buffer.append("  0\nLINE\n")
                dxf_buffer.append(f"  8\n{line['layer']}\n")
                dxf_buffer.append(f" 10\n{line['x1']:.3f}\n")
                dxf_buffer.append(f" 20\n{line['y1']:.3f}\n")
                dxf_buffer.append(f" 11\n{line['x2']:.3f}\n")
                dxf_buffer.append(f" 21\n{line['y2']:.3f}\n")

            dxf_buffer.append("  0\nENDSEC\n  0\nEOF\n")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write("".join(dxf_buffer))
            return True

        except Exception as e:
            print(f"[Ошибка экспорта DXF]: {e}")
            return False

    def import_from_dxf(self, file_path: str) -> list:
        """
        Всеядный парсер DXF файлов. Читает отрезки line и взрывает lwpolyline.
        Приводит строки к нижнему регистру, страхуя систему от смены стандартов CAD.
        """
        imported_items = []
        
        if not os.path.exists(file_path):
            print(f"[Ошибка импорта DXF]: Файл {file_path} не найден.")
            return imported_items

        try:
            # Читаем файл построчно, принудительно очищая и переводя в нижний регистр (lower)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip().lower() for line in f.readlines()]

            idx = 0
            total_lines = len(lines)
            import math

            while idx < total_lines:
                # Нашли маркер начала одиночного отрезка LINE
                if lines[idx] == "0" and idx + 1 < total_lines and lines[idx + 1] == "line":
                    x1 = y1 = x2 = y2 = 0.0
                    idx += 2

                    while idx < total_lines and lines[idx] != "0":
                        code = lines[idx]
                        if idx + 1 >= total_lines: break
                        val = lines[idx + 1]

                        if code == "10":    x1 = float(val)
                        elif code == "20":  y1 = float(val)
                        elif code == "11":  x2 = float(val)
                        elif code == "21":  y2 = float(val)
                        idx += 2

                    if math.hypot(x2 - x1, y2 - y1) > 0.1:
                        imported_items.append({
                            "type": "line", "x1": round(x1, 3), "y1": round(y1, 3),
                            "x2": round(x2, 3), "y2": round(y2, 3), "depth": 0.0
                        })

                # 🔥 ИСПРАВЛЕНО: Добавлен парсер полилиний LWPOLYLINE (чертежи из SketchUp)
                elif lines[idx] == "0" and idx + 1 < total_lines and lines[idx + 1] == "lwpolyline":
                    poly_points = [] # Массив кортежей координат (x, y) для сборки вершин
                    is_closed = False
                    idx += 2

                    while idx < total_lines and lines[idx] != "0":
                        code = lines[idx]
                        if idx + 1 >= total_lines: break
                        val = lines[idx + 1]

                        # Код 70 указывает, замкнута ли полилиния (1 — замкнута, 0 — разомкнута)
                        if code == "70":
                            is_closed = (int(val) & 1) == 1
                        # Собираем координаты вершин. Код 10 — это координата X. 
                        # Следующий за ней код 20 — координата Y.
                        elif code == "10":
                            curr_x = float(val)
                            curr_y = 0.0
                            # Ищем парный код 20 для Y на следующих строках
                            search_idx = idx + 2
                            while search_idx < total_lines and lines[search_idx] != "0":
                                if lines[search_idx] == "20":
                                    curr_y = float(lines[search_idx + 1])
                                    break
                                search_idx += 2
                            poly_points.append((curr_x, curr_y))
                        
                        idx += 2

                    # Если вершины найдены, последовательно связываем их в ЧПУ-отрезки LINE
                    if len(poly_points) > 1:
                        for i in range(len(poly_points) - 1):
                            pt1 = poly_points[i]
                            pt2 = poly_points[i + 1]
                            imported_items.append({
                                "type": "line", 
                                "x1": round(pt1[0], 3), "y1": round(pt1[1], 3),
                                "x2": round(pt2[0], 3), "y2": round(pt2[1], 3), 
                                "depth": 0.0
                            })
                        
                        # Если SketchUp указал, что полилиния замкнута, соединяем финал со стартом
                        if is_closed:
                            pt_first = poly_points[0]
                            pt_last = poly_points[-1]
                            if math.hypot(pt_first[0] - pt_last[0], pt_first[1] - pt_last[1]) > 0.1:
                                imported_items.append({
                                    "type": "line", 
                                    "x1": round(pt_last[0], 3), "y1": round(pt_last[1], 3),
                                    "x2": round(pt_first[0], 3), "y2": round(pt_first[1], 3), 
                                    "depth": 0.0
                                })
                else:
                    idx += 1

            print(f"[Успешный импорт DXF]: Считано {len(imported_items)} ЧПУ-векторов LINE.")
            return imported_items

        except Exception as e:
            print(f"[Ошибка парсинга DXF]: {e}")
            return imported_items
