import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton, QFileDialog
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QImage, QPixmap, QColor

class ImageImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Векторизатор логотипов и текста")
        self.setFixedSize(700, 450)
        
        self.setStyleSheet("""
            QDialog { background-color: #162421; }
            QLabel { color: #E0E0E6; font-family: 'Segoe UI'; font-size: 11px; }
            QSlider::groove:vertical { background: #1A1A1E; width: 6px; border-radius: 3px; }
            QSlider::handle:vertical { background: #00A8FF; height: 16px; width: 16px; margin-left: -5px; margin-right: -5px; border-radius: 8px; }
            QPushButton { background-color: #282830; color: #FFFFFF; border: 1px solid #353540; border-radius: 4px; padding: 6px 15px; font-size: 11px; }
            QPushButton:hover { background-color: #32323D; border-color: #00A8FF; }
        """)

        self.original_image = None  
        self.preview_image = None   # Облегченная копия для летающего слайдера
        self.processed_image = None 
        self.vector_results = []    

        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        slider_layout = QVBoxLayout()
        self.lbl_slider_title = QLabel("Контраст")
        self.lbl_slider_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setRange(1, 254)
        self.slider.setValue(128) 
        self.slider.valueChanged.connect(self._apply_processing)
        
        slider_layout.addWidget(self.lbl_slider_title)
        slider_layout.addWidget(self.slider, stretch=1)
        main_layout.addLayout(slider_layout)

        right_layout = QVBoxLayout()
        self.lbl_preview = QLabel("Нажмите 'Выбрать картинку' для старта")
        self.lbl_preview.setStyleSheet("border: 1px dashed #353540; background-color: #111114; border-radius: 6px;")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self.lbl_preview, stretch=1)

        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("Выбрать картинку...")
        self.btn_load.clicked.connect(self._open_file_dialog)
        
        self.btn_ok = QPushButton("ОК (Перенести на холст)")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_ok.setEnabled(False) 
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_load)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        right_layout.addLayout(btn_layout)
        main_layout.addLayout(right_layout)

    def _open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть изображение для ЧПУ", "", 
            "Изображения (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            img = QImage(file_path)
            if not img.isNull():
                # Чистовой ЧПУ-размер
                self.original_image = img.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio)
                # Облегченный размер для моментального отклика превью
                self.preview_image = img.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio)
                self.btn_ok.setEnabled(True)
                self._apply_processing()

    def _apply_processing(self):
        """🔥 ПОЛНОСТЬЮ БЕЗОПАСНЫЙ И ЖИВОЙ АЛГОРИТМ КОНТРАСТА"""
        if not self.preview_image:
            return

        threshold = self.slider.value()
        w, h = self.preview_image.width(), self.preview_image.height()

        # Переводим в серые оттенки встроенными средствами
        gray_image = self.preview_image.convertToFormat(QImage.Format.Format_Grayscale8)
        
        # Создаем чистое изображение под превью
        self.processed_image = QImage(w, h, QImage.Format.Format_RGB32)

        # Попиксельная обработка через стандартные безопасные методы PyQt6 (без voidptr)
        for y in range(h):
            for x in range(w):
                gray_val = QColor(gray_image.pixel(x, y)).red()
                if gray_val < threshold:
                    # Пиксель темнее порога — красим в черный
                    self.processed_image.setPixelColor(x, y, QColor(Qt.GlobalColor.black))
                else:
                    # Светлее — красим в белый
                    self.processed_image.setPixelColor(x, y, QColor(Qt.GlobalColor.white))

        # Обновляем превью на экране — ползунок снова чутко гнет контрастность!
        pixmap = QPixmap.fromImage(self.processed_image)
        self.lbl_preview.setPixmap(pixmap.scaled(self.lbl_preview.size(), Qt.AspectRatioMode.KeepAspectRatio))

    def get_vectorized_lines(self) -> list:
        """Трассировка по чистовому изображению в момент нажатия ОК"""
        self.vector_results = []
        if not self.original_image:
            return self.vector_results

        threshold = self.slider.value()
        w, h = self.original_image.width(), self.original_image.height()
        
        gray_image = self.original_image.convertToFormat(QImage.Format.Format_Grayscale8)
        
        pixel_to_mm = 2.0 
        center_x, center_y = w / 2.0, h / 2.0

        for y in range(h):
            in_black_segment = False
            start_x = 0

            for x in range(w):
                gray_val = QColor(gray_image.pixel(x, y)).red()
                is_black_pixel = (gray_val < threshold)

                if is_black_pixel and not in_black_segment:
                    in_black_segment = True
                    start_x = x
                elif not is_black_pixel and in_black_segment:
                    in_black_segment = False
                    x1 = (start_x - center_x) * pixel_to_mm
                    y1 = (center_y - y) * pixel_to_mm 
                    x2 = (x - center_x) * pixel_to_mm
                    y2 = (center_y - y) * pixel_to_mm

                    self.vector_results.append({
                        "type": "line", "x1": round(x1, 2), "y1": round(y1, 2),
                        "x2": round(x2, 2), "y2": round(y2, 2), "depth": 5.0 
                    })

            if in_black_segment:
                x1 = (start_x - center_x) * pixel_to_mm
                y1 = (center_y - y) * pixel_to_mm
                x2 = (w - 1 - center_x) * pixel_to_mm
                y2 = (center_y - y) * pixel_to_mm
                self.vector_results.append({
                    "type": "line", "x1": round(x1, 2), "y1": round(y1, 2),
                    "x2": round(x2, 2), "y2": round(y2, 2), "depth": 5.0
                })

        return self.vector_results