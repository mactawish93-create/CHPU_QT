import math
from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QPainterPath

def handle_mouse_move(canvas, event):
    scene_pos = canvas.mapToScene(event.position().toPoint())
    # 🔥 ВНЕДРЕНО: Сбрасываем накопительную дельту клавиатурного сдвига при любом шевелении мыши
    canvas.nudge_dx = 0.0
    canvas.nudge_dy = 0.0

    snapped_pos, snap_msg = canvas.cad_engine.calculate_snap_point(
        scene_pos, canvas.scene().items(), canvas.ctrl_pressed
    )
    
    canvas.snapped_current_pos = snapped_pos
    # 🔥 ИСПРАВЛЕНО: Передаем координаты и актуальный шаг сетки из ядра ЧПУ
    canvas.mouse_moved.emit(snapped_pos.x(), -snapped_pos.y(), canvas.cad_engine.grid_size)
    canvas.hint_changed.emit(snap_msg)

    if canvas.ctrl_pressed and "Захват:" in snap_msg:
        canvas.snap_marker.setPos(snapped_pos)
        canvas.snap_marker.show()
    else:
        canvas.snap_marker.hide()

    if canvas.current_tool == "draw_curve" and hasattr(canvas, "curve_stage"):
        if canvas.curve_stage == 1 and canvas.temp_item:
            snapped_pos = canvas.cad_engine.apply_ortho_45(canvas.curve_start_pt, snapped_pos, canvas.shift_pressed)
            canvas.curve_end_pt = snapped_pos
            canvas.temp_item.setLine(canvas.curve_start_pt.x(), canvas.curve_start_pt.y(), canvas.curve_end_pt.x(), canvas.curve_end_pt.y())
        elif canvas.curve_stage == 2 and canvas.temp_item:
            path = QPainterPath()
            path.moveTo(canvas.curve_start_pt)
            path.quadTo(snapped_pos, canvas.curve_end_pt)
            canvas.temp_item.setPath(path)
        return

    # === СТАНДАРТНЫЙ СЦЕНАРИЙ ЧЕРЧЕНИЯ ФИГУР ===
    if canvas.is_drawing and canvas.temp_item:
        dx = snapped_pos.x() - canvas.start_scene_pos.x()
        dy = snapped_pos.y() - canvas.start_scene_pos.y()
        
        if canvas.current_tool == "line":
            snapped_pos = canvas.cad_engine.apply_ortho_45(canvas.start_scene_pos, snapped_pos, canvas.shift_pressed)
            canvas.temp_item.setLine(canvas.start_scene_pos.x(), canvas.start_scene_pos.y(), snapped_pos.x(), snapped_pos.y())
            
        # 🔥 ВНЕДРЕНО: РАСТЯГИВАНИЕ РАМКИ ДЛЯ ОБЛАСТИ ВВОДА ТЕКСТА
        elif canvas.current_tool in ["rect", "text_area"]:
            # Если это обычный прямоугольник, проверяем Shift на квадрат
            if canvas.current_tool == "rect" and canvas.shift_pressed:
                side = max(abs(dx), abs(dy))
                dx = side if dx >= 0 else -side
                dy = side if dy >= 0 else -side
                
            x = min(canvas.start_scene_pos.x(), canvas.start_scene_pos.x() + dx)
            y = min(canvas.start_scene_pos.y(), canvas.start_scene_pos.y() + dy)
            canvas.temp_item.setRect(QRectF(x, y, abs(dx), abs(dy)))
            
        elif canvas.current_tool == "draw_circle":
            radius = math.hypot(dx, dy)
            path = QPainterPath()
            path.addEllipse(canvas.start_scene_pos, radius, radius)
            canvas.temp_item.setPath(path)
        elif canvas.current_tool == "draw_rhomb":
            if canvas.shift_pressed:
                side = max(abs(dx), abs(dy))
                dx = side if dx >= 0 else -side
                dy = side if dy >= 0 else -side
            path = QPainterPath()
            path.moveTo(canvas.start_scene_pos.x() + dx / 2, canvas.start_scene_pos.y())
            path.lineTo(canvas.start_scene_pos.x() + dx, canvas.start_scene_pos.y() + dy / 2)
            path.lineTo(canvas.start_scene_pos.x() + dx / 2, canvas.start_scene_pos.y() + dy)
            path.lineTo(canvas.start_scene_pos.x(), canvas.start_scene_pos.y() + dy / 2)
            path.closeSubpath()
            canvas.temp_item.setPath(path)
        elif canvas.current_tool == "draw_poly":
            radius = math.hypot(dx, dy)
            base_angle = 0.0 if canvas.shift_pressed else math.atan2(dy, dx)
            path = QPainterPath()
            for i in range(canvas.poly_sides):
                angle = base_angle + (2 * math.pi * i) / canvas.poly_sides
                px = canvas.start_scene_pos.x() + radius * math.cos(angle)
                py = canvas.start_scene_pos.y() + radius * math.sin(angle)
                if i == 0: path.moveTo(px, py)
                else: path.lineTo(px, py)
            path.closeSubpath()
            canvas.temp_item.setPath(path)