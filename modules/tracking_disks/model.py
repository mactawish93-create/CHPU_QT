from modules.tracking_disks.shapes.round import RoundDiskShape
from modules.tracking_disks.shapes.quadro import QuadroDiskShape
from modules.tracking_disks.shapes.babochka import BabochkaDiskShape
from modules.tracking_disks.shapes.viking import VikingDiskShape
from modules.tracking_disks.shapes.quadrohouse import QuadroHouseDiskShape
from modules.tracking_disks.door_data import DoorDataProcessor
from .shapes.babochka import BabochkaDiskShape

class DisksModel:
    """
    Главный диспетчер раздела 'Диски'. Связывает изолированные формы shapes/
    и процессор дверей door_data в единый CAM-конвейер заготовки.
    """
    def __init__(self):
        # Карта-указатель классов форм бань для мгновенного роутинга по индексу комбобокса
        self.shapes_map = {
            0: RoundDiskShape,
            1: QuadroDiskShape,
            2: BabochkaDiskShape,
            3: VikingDiskShape,
            4: QuadroHouseDiskShape
        }

    def calculate_disks_geometry(self, params: dict) -> dict:
        """Главный расчетный конвейер модуля дисков"""
        main_mode_idx = params.get("main_mode_idx", 0)  # Индекс комбобокса (0 - Круг, 1 - Квадро...)
        diameter = params.get("diameter", 2000.0)
        sub_mode = params.get("sub_mode", "Глухой диск")
        door_offset = params.get("door_offset", 0.0)
        
        radius = diameter / 2.0
        has_door = (sub_mode == "Диск с проемом")
        # =========================================================================
        # 🪵 ШАГ 1: ДИНАМИЧЕСКИЙ ВЫЗОВ АКТИВНОЙ ГЕОМЕТРИИ ФОРМЫ (SHAPES)
        # =========================================================================
        shape_class = self.shapes_map.get(main_mode_idx, RoundDiskShape)
        
        # 🔥 ВНЕДРЕНО: Если выбрана Бабочка, распаковываем все ее новые параметры
        if main_mode_idx == 2:
            shape_instance = shape_class(
                diameter=diameter,
                h_kon=params.get("h_kon", 2200.0),
                cut_vert_paz=params.get("cut_vert_paz", True),
                room_y=params.get("room_y", 1150.0),
                paz_z=params.get("paz_z", -20.0)
            )
        else:
            # Для Круга и Квадро оставляем стандартную инициализацию
            shape_instance = shape_class(diameter)
            
        # Запрашиваем у изолированного подмодуля чистый массив ламелей без дверей
        raw_lamels = shape_instance.calculate_lamels()

        # =========================================================================
        # 🚪 ШАГ 2: ИНИЦИАЛИЗАЦИЯ ИЗОЛИРОВАННОГО ПРОЦЕССОРА ДВЕРЕЙ
        # =========================================================================
        door_processor = DoorDataProcessor(diameter, door_offset)
        door_poly_outer, door_poly_inner = door_processor.get_door_polygons()

        # =========================================================================
        # 🪓 ШАГ 3: ПОСЛОЙНОЕ РАССЕЧЕНИЕ И ОБОГАЩЕНИЕ ЛАМЕЛЕЙ ДАННЫМИ ОБРЕЗКОВ
        # =========================================================================
        final_lamels = []
        for lamel in raw_lamels:
            x1 = lamel["x_start"]
            x2 = lamel["x_end"]
            length = lamel["length"]
            y_peak = length / 2.0  # Полувысота ламели от нуля центра
            
            is_cut = False
            top_len = 0.0
            bottom_len = 0.0
            
            # Если оператор включил проем — просим дверной процессор рассчитать куски доски
            if has_door and raw_lamels:  # Проверяем, что список ламелей не пустой (защита заглушек)
                is_cut, top_len, bottom_len = door_processor.check_and_calculate_lamel_cut(x1, x2, y_peak)
                
            final_lamels.append({
                "x_start": x1,
                "x_end": x2,
                "length": length,
                "is_cut": is_cut,
                "top_len": top_len,
                "bottom_len": bottom_len
            })

        # Возвращаем монолитный, чистый пакет данных для холста
        return {
            "main_mode_idx": main_mode_idx,
            "radius": radius,
            "diameter": diameter,
            "lamels": final_lamels,
            "door_outer": door_poly_outer,
            "door_inner": door_poly_inner,
            "has_door": has_door and len(final_lamels) > 0, # Включаем дверь только если есть ламели
            "y_door_top": door_processor.y_door_top,
            "y_door_bottom": door_processor.y_door_bottom,
            "shape_instance": shape_instance  # Передаем сам объект формы, чтобы холст мог попросить его нарисовать обвод!
        }
