######import qt_backend


import sys

try:
    # 1. Проверяем, заводится ли родной PyQt6 на текущем CPU
    import PyQt6
    from PyQt6 import QtCore, QtGui, QtWidgets
    from PyQt6.QtCore import Qt
    USING_PYQT6 = True

except (ImportError, RuntimeError, Exception):
    # 2. Если PyQt6 не ставится на J1800 — разворачиваем динамический мост на PyQt5
    USING_PYQT6 = False
    print("[⚙️ ЧПУ ПО] Запущен тотальный прокси-мост импортов PyQt6 -> PyQt5...")
    
    try:
        import PyQt5
        from PyQt5 import QtCore, QtGui, QtWidgets, QtPrintSupport  # Подключаем печать PDF
        from PyQt5.QtCore import Qt
    except ImportError:
        print("[❌ ОШИБКА] На этом ПК отсутствует PyQt5. Выполните в консоли: pip install PyQt5")
        sys.exit(1)

    # Исправление методов запуска Qt
    QtWidgets.QApplication.exec = QtWidgets.QApplication.exec_
    QtWidgets.QDialog.exec = QtWidgets.QDialog.exec_

    # --- ДИНАМИЧЕСКИЙ КЛАСС-ПЕРЕХВАТЧИК ДЛЯ ФЛАГОВ QT ---
    class DynamicQtProxy:
        def __getattr__(self, name):
            if name in ["MouseButton", "PenStyle", "AspectRatioMode", "AlignmentFlag", "FocusPolicy", "ScrollBarPolicy"]:
                return self
            if hasattr(Qt, name):
                return getattr(Qt, name)
            for prefix in ["", "ItemIs", "ScrollBar", "Anchor", "ScrollHand", "RubberBand"]:
                test_name = f"{prefix}{name}"
                if hasattr(Qt, test_name): return getattr(Qt, test_name)
            return getattr(Qt, name, 0)

    proxied_qt = DynamicQtProxy()

    # --- СВЕРХНАДЕЖНЫЙ КЛАСС-ПЕРЕХВАТЧИК ДЛЯ ИМПОРТОВ СИСТЕМЫ ---
    class ModuleProxy:
        def __init__(self, primary_module, fallback_modules):
            self.primary = primary_module
            self.fallbacks = fallback_modules

        def __getattr__(self, name):
            if name == "Qt": return proxied_qt
            
            # 1. Ищем класс в родном подмодуле PyQt5
            if hasattr(self.primary, name):
                return getattr(self.primary, name)
                
            # 2. Перехват переехавших классов (QMouseEvent, QWheelEvent, QAction, QPdfWriter и др.)
            for fb in self.fallbacks:
                if hasattr(fb, name):
                    return getattr(fb, name)
                    
            return getattr(self.primary, name)

    # Создаем прокси-версии трех главных модулей с учетом печати PDF и QAction
    core_proxy = ModuleProxy(QtCore, [QtGui, QtWidgets, QtPrintSupport])
    gui_proxy = ModuleProxy(QtGui, [QtCore, QtWidgets, QtPrintSupport])
    widgets_proxy = ModuleProxy(QtWidgets, [QtCore, QtGui, QtPrintSupport])

    # Патчим классы графики для совместимости методов
    QtGui.QMouseEvent.position = lambda self: self.posF() if hasattr(self, 'posF') else self.pos()
    QtGui.QMouseEvent.globalPosition = lambda self: self.globalPos()
    
    # Эмуляция вложенных Enums для старых свойств
    QtWidgets.QGraphicsView.ViewportAnchor = proxied_qt
    QtWidgets.QGraphicsView.DragMode = proxied_qt
    QtWidgets.QGraphicsItem.GraphicsItemFlag = proxied_qt
    QtGui.QPainter.RenderHint = proxied_qt
    QtGui.QFont.Weight = proxied_qt
    QtCore.QAbstractAnimation.State = proxied_qt
    QtWidgets.QFrame.Shape = proxied_qt
    QtWidgets.QFrame.Shadow = proxied_qt
    QtWidgets.QStyle.StandardPixmap = proxied_qt

    # --- МАСКИРОВКА В СИСТЕМНОМ КЭШЕ PYTHON ---
    sys.modules['PyQt6'] = PyQt5
    sys.modules['PyQt6.QtCore'] = core_proxy
    sys.modules['PyQt6.QtGui'] = gui_proxy
    sys.modules['PyQt6.QtWidgets'] = widgets_proxy
    
    # Принудительно прописываем прокси флагов внутрь ядра
    core_proxy.Qt = proxied_qt
