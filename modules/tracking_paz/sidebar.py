from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QComboBox, QStackedWidget, QLabel, QFrame
from PyQt6.QtCore import Qt
from config import SIDEBAR_WIDTH
from modules.tracking_paz.sub_views.paz_custom_view import PazCustomView
from modules.tracking_paz.sub_views.paz_plane_view import PazPlaneView


# Импортируем нашу свежую изолированную форму пазировки бани
from modules.tracking_paz.sub_views.paz_banya_view import PazBanyaView

class PazSidebar(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PazSidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        # Базовый контейнер-подложка панели
        content_widget = QWidget()
        content_widget.setObjectName("SidebarContent")
        self.setWidget(content_widget)
        
        # Главный вертикальный слой
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(10, 15, 10, 15)
        main_layout.setSpacing(15)
        
        # =========================================================================
        # 👑 ГЛАВНЫЙ СЕЛЕКТОР ПОДРЕЖИМОВ ПАЗИРОВКИ
        # =========================================================================
        self.combo_main_mode = QComboBox()
        self.combo_main_mode.addItems([
            "Пазировка Бани",
            "Произвольная пазировка",
            "Выравнивание плоскости"
        ])
        # Делаем селектор визуально чуть крупнее и заметнее
        self.combo_main_mode.setStyleSheet("font-weight: bold; color: #FF9F43;")
        main_layout.addWidget(self.combo_main_mode)
        
        # =========================================================================
        # 🔀 МЕНЕДЖЕР ПОДРЕЖИМОВ (STACKED WIDGET)
        # =========================================================================
        self.sub_modes_container = QStackedWidget()
        main_layout.addWidget(self.sub_modes_container)
        
        # 1. Загружаем полноценную форму Пазировки Бани
        self.banya_view = PazBanyaView()
        self.sub_modes_container.addWidget(self.banya_view)
        
        # 2. Загружаем полноценную форму Произвольной пазировки
        self.custom_paz_view = PazCustomView()
        self.sub_modes_container.addWidget(self.custom_paz_view)

        # 3. Загружаем полноценную форму Выравнивания плоскости
        self.plane_view = PazPlaneView()
        self.sub_modes_container.addWidget(self.plane_view)
        
        # Привязываем выбор в комбобоксе к смене активного виджета в стеке сайдбара
        self.combo_main_mode.currentIndexChanged.connect(self.sub_modes_container.setCurrentIndex)
        
        # Прижимаем всё кверху
        main_layout.addStretch()
