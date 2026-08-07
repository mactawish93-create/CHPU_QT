import json
import os
from datetime import datetime

class CamProjectManager:
    """
    Класс-фабрика для управления файлами проектов компании 'Бани Бабочки' (.cam).
    Отвечает за сохранение и чтение геометрии чертежа и технологических параметров ЧПУ.
    """
    def __init__(self):
        # 1. Задаем жесткие заводские настройки ЧПУ по умолчанию (блок cnc_settings)
        self.default_cnc_settings = {
            "tool_diameter": 12.0,      # Диаметр фрезы, мм
            "spindle_speed": 18000,    # Обороты шпинделя, об/мин
            "feed_rate_xy": 3000.0,    # Рабочая подача по плоскости XY, мм/мин
            "feed_rate_z": 800.0,      # Подача врезания по оси Z, мм/мин
            "safe_z": 20.0,            # Безопасная высота перелетов по воздуху, мм
            "step_down": 10.0          # Максимальная глубина реза за один проход, мм
        }

    def save_project(self, file_path: str, geometry_items: list, custom_cnc_settings: dict = None) -> bool:
        """
        Упаковывает настройки ЧПУ и массив графических элементов в JSON и сохраняет на диск.
        
        :param file_path: Полный путь к сохраняемому файлу (например, 'banya.cam')
        :param geometry_items: Список словарей с описанием фигур с холста
        :param custom_cnc_settings: Текущие настройки ЧПУ из интерфейса (если менялись)
        :return: True в случае успешного сохранения, False при ошибке
        """
        try:
            # Если пользовательские настройки ЧПУ не переданы, берем дефолтные заводские
            cnc_data = custom_cnc_settings if custom_cnc_settings is not None else self.default_cnc_settings
            
            # Формируем эталонную структуру файла .cam, которую мы обсудили
            project_data = {
                "metadata": {
                    "version": "1.0",
                    "app_name": "CHPU_QT",
                    "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                },
                "cnc_settings": cnc_data,
                "geometry": geometry_items  # Сюда прилетят линии, прямоугольники и их свойства ПКМ
            }
            
            # Записываем данные в файл с красивыми отступами (indent=4) для читаемости в блокноте
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=4)
            return True
            
        except Exception as e:
            print(f"[Ошибка сохранения .cam]: {e}")
            return False
    def load_project(self, file_path: str) -> dict:
        """
        Читает файл .cam с диска и безопасно извлекает настройки ЧПУ и геометрию.
        Если файл поврежден или сохранен в старой версии программы, 
        автоматически подставляет дефолтные параметры, чтобы ЧПУ-система не упала.
        
        :param file_path: Полный путь к открываемому файлу
        :return: Словарь вида {"cnc_settings": ..., "geometry": ...} или None при критической ошибке
        """
        if not os.path.exists(file_path):
            print(f"[Ошибка открытия]: Файл {file_path} не существует.")
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                
            # Безопасное извлечение настроек ЧПУ с подстраховкой (Fallback)
            loaded_cnc = raw_data.get("cnc_settings", {})
            validated_cnc = {}
            
            # Проверяем каждый параметр. Если его нет в файле — берем дефолтный заводской
            for key, default_val in self.default_cnc_settings.items():
                validated_cnc[key] = loaded_cnc.get(key, default_val)
                
            # Извлекаем массив геометрии (если файла пустой, вернет пустой список)
            geometry_items = raw_data.get("geometry", [])
            
            return {
                "cnc_settings": validated_cnc,
                "geometry": geometry_items
            }
            
        except Exception as e:
            print(f"[Ошибка чтения .cam]: {e}")
            return None
