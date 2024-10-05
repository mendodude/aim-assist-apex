```python
import cv2
import numpy as np
import pyautogui
import time
from pynput.mouse import Button, Controller
from pynput import keyboard

# --- Configuration ---

CAPTURE_WIDTH = 1280  # Adjust based on your GeForce Now game window
CAPTURE_HEIGHT = 720  # Adjust based on your GeForce Now game window
MACBOOK_WIDTH = 2560 
MACBOOK_HEIGHT = 1600

# --- Global Variables ---

learned_highlight_color = None
learned_health_bar_color = None
left_mouse_pressed = False

# --- Functions ---

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
        if w > h and w > max