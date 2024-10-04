import cv2
import numpy as np
import time
import pyautogui
from pynput.mouse import Controller, Listener, Button
import sys

# Updated constants for 1280x720 resolution
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
CAPTURE_WIDTH = SCREEN_WIDTH // 4  # 1/4 of the screen width
CAPTURE_HEIGHT = SCREEN_HEIGHT // 4  # 1/4 of the screen height

# Global variables for learned colors
learned_highlight_color = None
learned_health_bar_color = None

def learn_colors(image):
    global learned_highlight_color, learned_health_bar_color
    
    # Convert BGR to HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Learn highlight color (assuming it's the most prominent color in the middle)
    middle_region = hsv[CAPTURE_HEIGHT//3:2*CAPTURE_HEIGHT//3, CAPTURE_WIDTH//3:2*CAPTURE_WIDTH//3]
    highlight_color = cv2.mean(middle_region)[:3]
    learned_highlight_color = np.array(highlight_color, dtype=np.uint8)
    
    # Learn health bar color (assuming it's white)
    learned_health_bar_color = np.array([0, 0, 255], dtype=np.uint8)  # White in HSV

def detect_enemies(image):
    if learned_highlight_color is None:
        return []
    
    # Convert BGR to HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Create mask for learned highlight color
    color_range = 20
    lower_color = np.array([max(0, learned_highlight_color[0] - color_range), 50, 50])
    upper_color = np.array([min(180, learned_highlight_color[0] + color_range), 255, 255])
    mask = cv2.inRange(hsv, lower_color, upper_color)
    
    # Apply morphological operations to reduce noise
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours based on area and aspect ratio
    min_area = 50
    max_aspect_ratio = 3.0
    
    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(h) / w
            if aspect_ratio < max_aspect_ratio:
                valid_contours.append((x, y, w, h))
    
    return valid_contours

def detect_health_bar(image):
    if learned_health_bar_color is None:
        return None
    
    # Convert BGR to HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Create mask for learned health bar color
    color_range = 10
    lower_color = np.array([max(0, learned_health_bar_color[0] - color_range), 0, 200])
    upper_color = np.array([min(180, learned_health_bar_color[0] + color_range), 30, 255])
    mask = cv2.inRange(hsv, lower_color, upper_color)
    
    # Find contours in the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Find the largest horizontal rectangle (likely to be the health bar)
    max_width = 0
    health_bar = None
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > h and w > max_width:
            max_width = w
            health_bar = (x, y, w, h)
    
    return health_bar

def calculate_damage(health_bar, image):
    if health_bar is None:
        return 0
    
    x, y, w, h = health_bar
    bar_region = image[y:y+h, x:x+w]
    
    # Convert to grayscale
    gray = cv2.cvtColor(bar_region, cv2.COLOR_BGR2GRAY)
    
    # Threshold to separate white (health) from red (damage)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    
    # Calculate the percentage of white pixels (remaining health)
    white_pixels = cv2.countNonZero(binary)
    total_pixels = w * h
    health_percentage = (white_pixels / total_pixels) * 100
    
    return 100 - health_percentage  # Return damage percentage

def draw_highlight(frame, x, y, w, h):
    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
    center_x, center_y = x + w // 2, y + h // 2
    cv2.line(frame, (center_x - 10, center_y), (center_x + 10, center_y), (0, 255, 0), 2)
    cv2.line(frame, (center_x, center_y - 10), (center_x, center_y + 10), (0, 255, 0), 2)

def smooth_move(mouse, start, end, steps=10, duration=0.1):
    for i in range(1, steps + 1):
        t = i / steps
        x = int(start[0] + t * (end[0] - start[0]))
        y = int(start[1] + t * (end[1] - start[1]))
        mouse.position = (x, y)
        time.sleep(duration / steps)

def main():
    print("Improved Aim Assist started. Press Ctrl+C to exit.")
    try:
        last_positions = []
        mouse = Controller()
        
        left_mouse_pressed = False

        def on_click(x, y, button, pressed):
            nonlocal left_mouse_pressed
            if button == Button.left:
                left_mouse_pressed = pressed

        listener = Listener(on_click=on_click)
        listener.start()
        
        while True:
            # Capture the middle 1/4 of the screen
            x = (SCREEN_WIDTH - CAPTURE_WIDTH) // 2
            y = (SCREEN_HEIGHT - CAPTURE_HEIGHT) // 2
            screenshot = pyautogui.screenshot(region=(x, y, CAPTURE_WIDTH, CAPTURE_HEIGHT))
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            if learned_highlight_color is None:
                learn_colors(frame)
            
            detected_enemies = detect_enemies(frame)
            health_bar = detect_health_bar(frame)
            
            if health_bar:
                damage = calculate_damage(health_bar, frame)
                cv2.putText(frame, f"Damage: {damage:.1f}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            if detected_enemies and left_mouse_pressed:
                current_positions = []
                for (ex, ey, w, h) in detected_enemies:
                    draw_highlight(frame, ex, ey, w, h)
                    screen_x = x + ex + w // 2
                    screen_y = y + ey + h // 2
                    current_positions.append((screen_x, screen_y))
                
                if last_positions:
                    last_pos = last_positions[-1]
                    nearest_enemy = min(current_positions, key=lambda pos: ((pos[0] - last_pos[0])**2 + (pos[1] - last_pos[1])**2)**0.5)
                    
                    target_x, target_y = nearest_enemy
                    target_y -= 5
                    
                    smooth_move(mouse, mouse.position, (target_x, target_y))
                    
                    last_positions.append((target_x, target_y))
                else:
                    target_x, target_y = current_positions[0]
                    target_y -= 5
                    smooth_move(mouse, mouse.position, (target_x, target_y))
                    last_positions.append((target_x, target_y))
                
                last_positions = last_positions[-5:]
            else:
                last_positions = []
            
            # Uncomment for debugging
            # cv2.imshow('Improved Aim Assist Debug', frame)
            # if cv2.waitKey(1) &amp; 0xFF == ord('q'):
            #     break
            
            time.sleep(0.05)
    
    except KeyboardInterrupt:
        print("Improved Aim Assist stopped.")
    
    # Uncomment if using cv2.imshow for debugging
    # cv2.destroyAllWindows()

if __name__ == "__main__":
    main()