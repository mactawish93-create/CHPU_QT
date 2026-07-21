from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QButtonGroup
from PyQt6.QtCore import pyqtSignal, Qt
from config import REGISTERED_MODULES

class HeaderWidget(QFrame):
    # Сигнал, который сообщает Главному окну, что оператор переключил вкладку
    tab_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderFrame")  # Для привязки стилей из styles.py
        
        # Основной горизонтальный слой хедера
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10)
        
        # Левая часть — текстовый брендовый логотип компании
        self.logo_label = QLabel("БАНИ БАБОЧКИ")
        self.logo_label.setObjectName("HeaderLogo")
        layout.addWidget(self.logo_label)
        
        # Добавляем небольшую распорку, чтобы прижать кнопки к центру/левой части
        layout.addSpacing(20)
        
        # Группа для объединения кнопок (гарантирует, что активна всегда только одна)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        # Динамический реестровый генератор кнопок
        for module in REGISTERED_MODULES:
            # Создаем кнопку
            btn = QPushButton(module["name"])
            btn.setCheckable(True)
            
            # ИСПРАВЛЕНО: Используем правильный глобальный класс Qt для политики фокуса
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  
            
            btn.setProperty("class", "HeaderTabButton")   # Для применения стилей QSS
            
            # Сохраняем ID модуля внутри самой кнопки, чтобы знать, кто нажат
            btn.setProperty("module_id", module["id"])
            
            # Добавляем в UI-слой хедера и в логическую группу переключателей
            layout.addWidget(btn)
            self.button_group.addButton(btn)
            
            # Активируем по умолчанию самую первую вкладку из списка
            if module == REGISTERED_MODULES[0]:
                btn.setChecked(True)
        
        # Подключаем событие клика по любой кнопке в группе
        self.button_group.buttonClicked.connect(self._on_button_clicked)
        
        # Пружина в самом конце, чтобы сдвинуть всё меню влево
        layout.addStretch()

    def _on_button_clicked(self, button):
        """Внутренний обработчик: вытаскивает ID модуля и шлет его наверх в MainWindow"""
        module_id = button.property("module_id")
        self.tab_changed.emit(module_id)
