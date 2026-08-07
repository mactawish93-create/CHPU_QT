from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QDoubleSpinBox, QPushButton, QLabel, QLineEdit
from PyQt6.QtCore import Qt, QRectF, QLineF, QPointF
from PyQt6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem, QGraphicsPathItem

class ElementPropertiesDialog(QDialog):
    """
    Прецизионное окно точной настройки геометрии, текстов и технологии ЧПУ.
    Динамически перестраивает поля ввода под Линии, Прямоугольники и Текстовые векторы.
    """
    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Параметры элемента чертежа")
        self.setFixedSize(340, 340) # Чуть увеличили высоту под поля координат
        
        self.setStyleSheet("""
            QDialog { background-color: #162421; }
            QLabel { color: #E0E0E6; font-family: 'Segoe UI'; font-size: 11px; }
            QDoubleSpinBox, QLineEdit {
                background-color: #1A1A1E;
                color: #E0E0E6;
                border: 1px solid #32323D;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 11px;
                font-family: "Segoe UI";
                min-height: 20px;
            }
            QPushButton {
                background-color: #282830;
                color: #FFFFFF;
                border: 1px solid #353540;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #32323D; border-color: #00A8FF; }
        """)

        self.form_layout = QFormLayout()
        self.form_layout.setContentsMargins(15, 15, 15, 15)
        self.form_layout.setSpacing(10)

        # Извлекаем скрытый технологический паспорт элемента
        self.item_data = item.data(0) if item.data(0) else {"type": "unknown", "depth": 0.0}
        self.item_type = self.item_data.get("type", "unknown")

        self._build_fields()

    def _create_spinbox(self, min_val=-5000.0, max_val=5000.0, default=0.0):
        sb = QDoubleSpinBox()
        sb.setRange(min_val, max_val)
        sb.setDecimals(1) 
        sb.setSingleStep(1.0)
        sb.setValue(default)
        return sb

    def _build_fields(self):
        # Глобальный параметр для всех типов: Глубина реза по оси Z
        self.sb_depth = self._create_spinbox(0.0, 200.0, self.item_data.get("depth", 0.0))
        self.form_layout.addRow("Глубина реза Z (мм):", self.sb_depth)

        # 1. ПОЛЯ ДЛЯ ОДИНОЧНОЙ ЛИНИИ
        if isinstance(self.item, QGraphicsLineItem):
            line = self.item.line()
            self.sb_x1 = self._create_spinbox(default=line.x1())
            self.sb_y1 = self._create_spinbox(default=-line.y1()) 
            self.sb_x2 = self._create_spinbox(default=line.x2())
            self.sb_y2 = self._create_spinbox(default=-line.y2())

            self.form_layout.addRow("Старт X1 (мм):", self.sb_x1)
            self.form_layout.addRow("Старт Y1 (мм):", self.sb_y1)
            self.form_layout.addRow("Конец X2 (мм):", self.sb_x2)
            self.form_layout.addRow("Конец Y2 (мм):", self.sb_y2)

        # 2. ПОЛЯ ДЛЯ ПРЯМОУГОЛЬНИКА
        elif isinstance(self.item, QGraphicsRectItem):
            rect = self.item.rect()
            self.sb_x = self._create_spinbox(default=rect.x())
            self.sb_y = self._create_spinbox(default=-rect.y())
            self.sb_w = self._create_spinbox(0.1, 5000.0, rect.width())
            self.sb_h = self._create_spinbox(0.1, 5000.0, rect.height())

            self.form_layout.addRow("Позиция X (мм):", self.sb_x)
            self.form_layout.addRow("Позиция Y (мм):", self.sb_y)
            self.form_layout.addRow("Ширина W (мм):", self.sb_w)
            self.form_layout.addRow("Высота H (мм):", self.sb_h)

        # 3. 🔥 ИСПРАВЛЕНО: ПОЛЯ ДЛЯ ЧПУ-ТЕКСТА + ТОЧНЫЕ КООРДИНАТЫ ПОЗИЦИОНИРОВАНИЯ
        elif self.item_type == "text":
            self.txt_input = QLineEdit()
            self.txt_input.setText(self.item_data.get("raw_text", ""))
            
            self.sb_font_size = self._create_spinbox(1.0, 500.0, self.item_data.get("font_size", 24.0))
            
            # Извлекаем текущие физические координаты текста на сцене ЧПУ
            current_x = self.item.x()
            current_y = -self.item.y() # Инверсия Y для человека
            
            self.sb_text_x = self._create_spinbox(default=current_x)
            self.sb_text_y = self._create_spinbox(default=current_y)
            
            self.form_layout.addRow("Редактировать текст:", self.txt_input)
            self.form_layout.addRow("Высота букв (мм):", self.sb_font_size)
            self.form_layout.addRow("Позиция текста X (мм):", self.sb_text_x)
            self.form_layout.addRow("Позиция текста Y (мм):", self.sb_text_y)

        # 4. ПОЛЯ ДЛЯ ОКРУЖНОСТИ
        elif self.item_type == "circle":
            rect = self.item.boundingRect()
            radius = rect.width() / 2.0
            self.sb_cx = self._create_spinbox(default=rect.center().x())
            self.sb_cy = self._create_spinbox(default=-rect.center().y())
            self.sb_r = self._create_spinbox(0.1, 2500.0, radius)

            self.form_layout.addRow("Центр X (мм):", self.sb_cx)
            self.form_layout.addRow("Центр Y (мм):", self.sb_cy)
            self.form_layout.addRow("Радиус R (мм):", self.sb_r)

        # КНОПКИ УПРАВЛЕНИЯ
        main_vbox = QVBoxLayout(self)
        main_vbox.addLayout(self.form_layout)

        btn_hbox = QHBoxLayout()
        self.btn_delete = QPushButton("Удалить элемент")
        self.btn_delete.setStyleSheet("QPushButton { background-color: #721C24; color: #F8D7DA; } QPushButton:hover { background-color: #A93226; }")
        self.btn_delete.clicked.connect(self._delete_item)

        self.btn_save = QPushButton("Применить")
        self.btn_save.clicked.connect(self._save_changes)
        
        btn_hbox.addWidget(self.btn_delete)
        btn_hbox.addStretch()
        btn_hbox.addWidget(self.btn_save)
        main_vbox.addLayout(btn_hbox)

    def _delete_item(self):
        self.done(2) 

    def _save_changes(self):
        self.item_data["depth"] = self.sb_depth.value()

        if isinstance(self.item, QGraphicsLineItem):
            self.item.setLine(self.sb_x1.value(), -self.sb_y1.value(), self.sb_x2.value(), -self.sb_y2.value())
            self.item.setData(0, self.item_data)

        elif isinstance(self.item, QGraphicsRectItem):
            self.item.setRect(QRectF(self.sb_x.value(), -self.sb_y.value(), self.sb_w.value(), self.sb_h.value()))
            self.item.setData(0, self.item_data)

        elif self.item_type == "text":
            self.item_data["raw_text"] = self.txt_input.text()
            self.item_data["font_size"] = self.sb_font_size.value()
            self.item.setData(0, self.item_data)
            
            # 1. Применяем прецизионный сдвиг координат через матрицу позиционирования Qt
            self.item.setPos(self.sb_text_x.value(), -self.sb_text_y.value())
            
            # 2. Пересобираем сам векторный путь букв, если изменился текст или высота
            from PyQt6.QtGui import QPainterPath, QFont
            path = QPainterPath()
            font = QFont(self.item_data.get("font_name", "Arial"))
            font.setPointSizeF(self.sb_font_size.value())
            font.setBold(True)
            
            # Отрисовываем новые буквы в локальный ноль элемента
            path.addText(0.0, 0.0, font, self.txt_input.text())
            self.item.setPath(path)

        elif self.item_type == "circle":
            from PyQt6.QtGui import QPainterPath
            path = QPainterPath()
            r = self.sb_r.value()
            center = QPointF(self.sb_cx.value(), -self.sb_cy.value())
            path.addEllipse(center, r, r)
            self.item.setPath(path)
            self.item.setData(0, self.item_data)

        self.accept()