# Единый стиль интерфейса ЧПУ компании "Бани Бабочки"
QSS_STYLE = """
/* Глобальные настройки окна - фоновый цвет теперь управляется динамически */
QMainWindow {
    background-color: #1A1A1E;
}

/* Верхний Хедер */
QFrame#HeaderFrame {
    background-color: #1F1F24;
    border-bottom: 2px solid #282830;
    max-height: 55px;
    min-height: 55px;
}

QLabel#HeaderLogo {
    color: #FF9F43; /* Брендовый янтарно-древесный цвет */
    font-size: 14px;
    font-weight: bold;
    font-family: "Segoe UI", "Arial";
    padding-left: 10px;
}

/* Кнопки хедера */
QPushButton.HeaderTabButton {
    background-color: #282830;
    color: #C0C0C6;
    border: 1px solid #353540;
    border-radius: 5px;
    font-size: 11px;
    font-weight: bold;
    font-family: "Segoe UI", "Arial";
    padding: 6px 15px;
    min-width: 95px;
}

QPushButton.HeaderTabButton:hover {
    background-color: #32323D;
    border-color: #00A8FF;
    color: #FFFFFF;
}

QPushButton.HeaderTabButton:checked {
    background-color: #00A8FF;
    color: #FFFFFF;
    border-color: #0088CC;
}

/* Стилизация левой панели параметров (Глобальная прозрачность скролл-зон под анимацию фонов) */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea QWidget {
    background-color: transparent;
}

/* Принудительно зачищаем внутренний системный viewport области прокрутки */
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* Стилизация карточек GroupBox */
QGroupBox {
    background-color: #25252D;
    color: #FF9F43;
    font-size: 10px;
    font-weight: bold;
    font-family: "Segoe UI", "Arial";
    border: 1px solid #32323D;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 5px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 4px;
    left: 6px;
}

/* Текст подписей полей */
QLabel {
    color: #B0B0B8;
    font-size: 10px;
    font-family: "Segoe UI", "Arial";
}

/* Поля ввода под Сompack UI */
QDoubleSpinBox, QComboBox {
    background-color: #1A1A1E;
    color: #E0E0E6;
    border: 1px solid #32323D;
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 10px;
    font-family: "Segoe UI", "Arial";
    min-height: 18px;
    max-height: 18px;
}

QDoubleSpinBox:hover, QComboBox:hover {
    border-color: #454552;
}

QDoubleSpinBox:focus, QComboBox:focus {
    border-color: #00A8FF;
    color: #FFFFFF;
}

/* Чекбоксы */
QCheckBox {
    spacing: 3px;
}
QCheckBox::indicator {
    width: 12px;
    height: 12px;
}

/* Стрелочки вверх-вниз у SpinBox */
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #282830;
    width: 14px;
    border-left: 1px solid #32323D;
}

QDoubleSpinBox::up-button { border-top-right-radius: 4px; }
QDoubleSpinBox::down-button { border-bottom-right-radius: 4px; }

QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #32323D;
}

/* Стрелочка выпадающего списка ComboBox */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 16px;
    border-left-width: 1px;
    border-left-color: #32323D;
    border-left-style: solid;
}

QComboBox QAbstractItemView {
    background-color: #1A1A1E;
    color: #E0E0E6;
    selection-background-color: #00A8FF;
    selection-color: #FFFFFF;
    border: 1px solid #32323D;
}

/* Окна чертежей и графики (Правый холст) */
QGraphicsView {
    background-color: #111114;
    border: 1px solid #25252D;
    border-radius: 6px;
}

/* Тонкие современные скроллбары */
QScrollBar:vertical {
    background-color: #16161A;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background-color: #32323D;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00A8FF;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
"""
