import os
from PyQt6.QtGui import QPdfWriter, QPainter, QPen, QFont, QColor, QPageSize
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QPageLayout

class PdfExchangeManager:
    """
    Модуль генерации технологических карт и чертежей в формат PDF.
    Использует встроенный движок PyQt6, не требуя сторонних библиотек.
    Формирует лист А4 в альбомной ориентации со штампом ЧПУ и графическим полем.
    """
    def __init__(self):
        pass

    def _draw_tech_table(self, painter: QPainter, cnc_settings: dict, bounds_info: dict, start_y: int):
        """Вспомогательный метод: рисует аккуратную таблицу параметров ЧПУ и габаритов изделия"""
        painter.save()
        
        # Настраиваем шрифты для таблицы
        title_font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        text_font = QFont("Segoe UI", 9, QFont.Weight.Normal)
        
        # Заголовок таблицы
        painter.setFont(title_font)
        painter.setPen(QPen(QColor("#111114"), 2))
        painter.drawText(500, start_y, "ТЕХНОЛОГИЧЕСКИЕ ПАРАМЕТРЫ ЧПУ")
        
        # Собираем данные для вывода из настроек станка
        tech_data = [
            ("Диаметр фрезы:", f"{cnc_settings.get('tool_diameter', 12.0)} мм"),
            ("Обороты шпинделя:", f"{cnc_settings.get('spindle_speed', 18000)} об/мин"),
            ("Подача XY (рез):", f"{cnc_settings.get('feed_rate_xy', 3000.0)} мм/мин"),
            ("Подача Z (врез):", f"{cnc_settings.get('feed_rate_z', 800.0)} мм/мин"),
            ("Безопасная высота Z:", f"{cnc_settings.get('safe_z', 20.0)} мм"),
            ("Шаг за проход (Step):", f"{cnc_settings.get('step_down', 10.0)} мм"),
            ("Габарит заготовки X:", f"{bounds_info['width']:.1f} мм"),
            ("Габарит заготовки Y:", f"{bounds_info['height']:.1f} мм")
        ]
        
        current_y = start_y + 400
        painter.setFont(text_font)
        
        # Отрисовка строк таблицы параметров
        for label, val in tech_data:
            painter.setPen(QPen(QColor("#555555"), 1))
            # Рисуем тонкую разделительную линию под каждой строкой
            painter.drawLine(500, current_y + 100, 3500, current_y + 100)
            
            painter.setPen(QPen(QColor("#111114"), 1))
            painter.drawText(550, current_y, label)
            painter.drawText(2200, current_y, val)
            current_y += 350
            
        painter.restore()
    def export_to_pdf(self, file_path: str, geometry_items: list, cnc_settings: dict) -> bool:
        """
        Основной метод экспорта. Генерирует чистовой чертеж в PDF.
        Автоматически масштабирует векторов под размер листа и проставляет габариты.
        
        :param file_path: Путь для сохранения PDF файла
        :param geometry_items: Массив фигур с холста
        :param cnc_settings: Словарь параметров ЧПУ
        :return: True при успешном сохранении, False при ошибке
        """
        try:
            # 1. Если чертеж пустой, генерировать нечего, но создадим базовые границы
            if not geometry_items:
                bounds = {"min_x": 0, "max_x": 100, "min_y": 0, "max_y": 100, "width": 100, "height": 100}
            else:
                # Вычисляем максимальные и минимальные границы всего чертежа для авторазмеров
                xs = []
                ys = []
                for item in geometry_items:
                    if item.get("type") == "line":
                        xs.extend([item["x1"], item["x2"]])
                        ys.extend([item["y1"], item["y2"]])
                    elif item.get("type") == "rect":
                        xs.extend([item["x"], item["x"] + item["width"]])
                        ys.extend([item["y"], item["y"] + item["height"]])
                
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                bounds = {
                    "min_x": min_x, "max_x": max_x,
                    "min_y": min_y, "max_y": max_y,
                    "width": max(1.0, max_x - min_x),
                    "height": max(1.0, max_y - min_y)
                }

            # 2. Инициализируем движок PDF-печати PyQt6
            writer = QPdfWriter(file_path)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            # Задаем жесткую альбомную ориентацию для цеховых чертежей
            writer.setPageOrientation(QPageLayout.Orientation.Landscape)
            
            # Инициализируем инструмент рисования на PDF
            painter = QPainter(writer)
            
            # Получаем внутреннее разрешение листа в пикселях (у PDF оно очень высокое, например 10000х7000)
            page_w = writer.width()
            page_h = writer.height()
            
            # --- 3. ОТРИСОВКА БРЕНДОВОГО ШТАМПА И ТЕКСТА ---
            # Рисуем рамку вокруг всего листа А4 с отступом
            painter.setPen(QPen(QColor("#25252D"), 3))
            painter.drawRect(200, 200, page_w - 400, page_h - 400)
            
            # Выводим логотип / название компании
            brand_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
            painter.setFont(brand_font)
            painter.setPen(QPen(QColor("#FF9F43"), 1)) # Фирменный янтарный цвет "Бани Бабочки"
            painter.drawText(500, 500, "БАНИ БАБОЧКИ — ЦЕХОВАЯ КАРТА")
            
            # Отрисовываем таблицу параметров ЧПУ (из Части 1)
            self._draw_tech_table(painter, cnc_settings, bounds, start_y=900)
            
            # --- 4. РАСЧЕТ МАСШТАБА ГРАФИЧЕСКОГО ПОЛЯ ---
            # Выделяем под сам чертеж правую половину листа А4
            draw_zone_x = int(page_w * 0.45)
            draw_zone_y = int(page_h * 0.15)
            draw_zone_w = int(page_w * 0.50)
            draw_zone_h = int(page_h * 0.70)
            
            # Считаем, во сколько раз нужно сжать чертеж, чтобы он влез в окно
            scale_x = draw_zone_w / bounds["width"]
            scale_y = draw_zone_h / bounds["height"]
            scale = min(scale_x, scale_y) * 0.85 # 0.85 — запас на поля для авторазмеров
            
            # Вычисляем геометрический центр нашей детали
            center_item_x = (bounds["min_x"] + bounds["max_x"]) / 2.0
            center_item_y = (bounds["min_y"] + bounds["max_y"]) / 2.0
            
            # Вычисляем центр графической зоны на бумаге
            center_zone_x = draw_zone_x + (draw_zone_w / 2.0)
            center_zone_y = draw_zone_y + (draw_zone_h / 2.0)
            
            # --- 5. ВЕКТОРНАЯ ОТРИСОВКА ГЕОМЕТРИИ ---
            painter.save()
            pen_line = QPen(QColor("#111114"), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen_line)
            
            for item in geometry_items:
                item_type = item.get("type")
                
                if item_type == "line":
                    # Переводим ЧПУ-координаты первой точки в пиксели листа А4 с учетом центра и масштаба
                    x1 = center_zone_x + (item["x1"] - center_item_x) * scale
                    y1 = center_zone_y - (item["y1"] - center_item_y) * scale # Инвертируем Y для чертежного стандарта
                    # Переводим вторую точку
                    x2 = center_zone_x + (item["x2"] - center_item_x) * scale
                    y2 = center_zone_y - (item["y2"] - center_item_y) * scale
                    
                    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
                    
                elif item_type == "rect":
                    # Переводим координаты прямоугольника
                    rx = center_zone_x + (item["x"] - center_item_x) * scale
                    ry = center_zone_y - (item["y"] + item["height"] - center_item_y) * scale
                    rw = item["width"] * scale
                    rh = item["height"] * scale
                    
                    painter.drawRect(QRectF(rx, ry, rw, rh))
            
            # --- 6. АВТОМАТИЧЕСКОЕ НАНЕСЕНИЕ ГАБАРИТНЫХ РАЗМЕРОВ ---
            dim_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            painter.setFont(dim_font)
            painter.setPen(QPen(QColor("#00A8FF"), 1)) # Габариты подсветим вашим синим акцентом
            
            # Переводим крайние точки габаритной рамки заготовки
            bx = center_zone_x + (bounds["min_x"] - center_item_x) * scale
            by = center_zone_y - (bounds["max_y"] - center_item_y) * scale
            bw = bounds["width"] * scale
            bh = bounds["height"] * scale
            
            # Рисуем горизонтальную габаритную стрелку-линию сверху детали
            painter.drawLine(QPointF(bx, by - 150), QPointF(bx + bw, by - 150))
            painter.drawText(QRectF(bx, by - 350, bw, 200), Qt.AlignmentFlag.AlignCenter, f"{bounds['width']:.1f} mm")
            
            # Рисуем вертикальную габаритную стрелку-линию слева от детали
            painter.drawLine(QPointF(bx - 150, by), QPointF(bx - 150, by + bh))
            painter.save()
            # Поворачиваем painter для вертикального текста размера, чтобы было по ГОСТу
            painter.translate(bx - 250, by + bh / 2.0)
            painter.rotate(-90)
            painter.drawText(QRectF(-1000, -100, 2000, 200), Qt.AlignmentFlag.AlignCenter, f"{bounds['height']:.1f} mm")
            painter.restore()
            
            painter.restore() # Возвращаем настройки painter
            
            # Закрываем сессию рисования и финализируем запись PDF-файла
            painter.end()
            return True
            
        except Exception as e:
            print(f"[Критическая ошибка экспорта PDF]: {e}")
            if 'painter' in locals() and painter.isActive():
                painter.end()
            return False
