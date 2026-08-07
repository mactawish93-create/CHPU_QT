from PyQt6.QtCore import Qt

def handle_wheel_zoom(canvas, event):
    # 1. ОСОБЫЙ СЦЕНАРИЙ: Меняем количество граней многоугольника (Shift + Колесико)
    if canvas.is_drawing and canvas.current_tool == "draw_poly" and canvas.shift_pressed:
        delta = event.angleDelta().y()
        if delta > 0:
            canvas.poly_sides = min(24, canvas.poly_sides + 1) # Максимум 24 грани
        else:
            canvas.poly_sides = max(3, canvas.poly_sides - 1)  # Минимум Треугольник (3 грани)
        
        canvas.hint_changed.emit(f"Количество граней многоугольника: {canvas.poly_sides}")
        # Принудительно вызываем обновление мыши, чтобы фигура перерисовалась прямо на лету
        canvas.update_current_cursor_position()
        return # Блокируем стандартный зум экрана, чтобы лист не прыгал!

    # 2. СТАНДАРТНЫЙ СЦЕНАРИЙ: ВЫСОКОТОЧНЫЙ CAD-ЗУМ ОТНОСИТЕЛЬНО КУРСОРA
    zoom_in_factor = 1.15
    zoom_out_factor = 1.0 / zoom_in_factor
    
    # Запоминаем текущую миллиметровую точку под мышкой в сцене
    old_scene_pos = canvas.mapToScene(event.position().toPoint())
    
    if event.angleDelta().y() > 0:
        factor = zoom_in_factor
    else:
        factor = zoom_out_factor
        
    new_zoom = canvas.current_zoom * factor
    
    # Ограничиваем масштаб станка (от 10% до 2000%), чтобы оператор не потерялся на холсте
    if 0.1 <= new_zoom <= 20.0:
        canvas.current_zoom = new_zoom
        canvas.scale(factor, factor)
        
        # Сдвигаем экран так, чтобы точка под мышкой осталась на месте после зума
        new_scene_pos = canvas.mapToScene(event.position().toPoint())
        delta_pos = new_scene_pos - old_scene_pos
        canvas.translate(delta_pos.x(), delta_pos.y())
        
        canvas.zoom_changed.emit(canvas.current_zoom)
