# get_height.py

import numpy as np
import math
from body_segments import *
from photos_height import *
from measurement_validator import MeasurementValidator
from measurement_calculator import MeasurementCalculator

# Use the height from photos_height (which may have been updated by runprogram.py)
height = height  # cm

# Initialize validators and calculators
validator = MeasurementValidator(height)
calc = MeasurementCalculator()

image_front_silhouette_path = 'images/add_silhouette.jpg'
image_front_silhouette = cv2.imread(image_front_silhouette_path)

image_side_silhouette_path = 'images/add_silhouette_side.jpg'
image_side_silhouette = cv2.imread(image_side_silhouette_path)

def mid_point_chest():
    mid_hip = [((right_hip[0] + left_hip[0]) / 2), ((right_hip[1] + left_hip[1]) / 2)]
    mid_shoulder = [((right_shoulder[0] + left_shoulder[0]) / 2), ((right_shoulder[1] + left_shoulder[1]) / 2)]
    chest_height = (abs(mid_hip[0] - mid_shoulder[0]) ** 2 + (mid_hip[1] - mid_shoulder[1]) ** 2) ** 0.5
    cv2.line(image_front_silhouette, (int(mid_hip[0]), int(mid_hip[1])), (int(mid_shoulder[0]), int(mid_shoulder[1])),
             (0, 255, 0), 2)
    return mid_shoulder, chest_height

def mid_point_chest_side():
    mid_hip_side = [((right_hip_side[0] + left_hip_side[0]) / 2), ((right_hip_side[1] + left_hip_side[1]) / 2)]
    mid_shoulder_side = [((right_shoulder_side[0] + left_shoulder_side[0]) / 2),
                         ((right_shoulder_side[1] + left_shoulder_side[1]) / 2)]
    chest_height_side = (abs(mid_hip_side[0] - mid_shoulder_side[0]) ** 2 + (
            mid_hip_side[1] - mid_shoulder_side[1]) ** 2) ** 0.5
    return mid_shoulder_side, chest_height_side, mid_hip_side

def get_height_head():
    global current_distance_up, x_perp1, y_perp1
    middle_eye_inner = [((right_eye_inner[0] + left_eye_inner[0]) / 2), ((right_eye_inner[1] + left_eye_inner[1]) / 2)]
    mid_point_shoulder = mid_point_chest()[0]
    slope = (middle_eye_inner[1] - mid_point_shoulder[1]) / (middle_eye_inner[0] - mid_point_shoulder[0])

    x_mid, y_mid = int(mid_point_shoulder[0]), int(mid_point_shoulder[1])
    current_distance = 0
    max_length = 5000
    current_x = x_mid
    color_background = 5
    while current_distance < max_length:
        current_x -= 1
        current_y = int(y_mid + slope * (current_x - x_mid))
        if image_front_silhouette[current_y, current_x].sum() < color_background:
            x_perp1 = current_x
            y_perp1 = current_y
            break
        current_distance_up = sqrt((y_mid - current_y) ** 2 + (x_mid - current_x) ** 2)

    cv2.line(image_front_silhouette, (x_perp1, y_perp1), (x_mid, y_mid), (0, 255, 0), 2)
    return current_distance_up

def get_height_head_side():
    global current_distance_up_side, x_perp1_side, y_perp1_side
    mid_point_shoulder_side = mid_point_chest_side()[0]
    mid_hip_side = mid_point_chest_side()[2]

    slope = (mid_hip_side[1] - mid_point_shoulder_side[1]) / (mid_hip_side[0] - mid_point_shoulder_side[0])

    x_mid_side, y_mid_side = int(mid_point_shoulder_side[0]), int(mid_point_shoulder_side[1])
    current_distance_side = 0
    max_length = 5000
    current_x = x_mid_side
    color_background = 5
    while current_distance_side < max_length:
        current_x -= 1
        current_y = int(y_mid_side + slope * (current_x - x_mid_side))
        if image_side_silhouette[current_y, current_x].sum() < color_background:
            x_perp1_side = current_x
            y_perp1_side = current_y
            break
        current_distance_up_side = sqrt((y_mid_side - current_y) ** 2 + (x_mid_side - current_x) ** 2)

    cv2.line(image_side_silhouette, (x_perp1_side, y_perp1_side), (x_mid_side, y_mid_side), (0, 255, 0), 2)
    return current_distance_up_side

def get_height_front():
    left_knee_hip = (abs(left_knee[0] - left_hip[0]) ** 2 + abs(left_knee[1] - left_hip[1]) ** 2) ** 0.5
    left_heel_ankle = (abs(left_heel[0] - left_ankle[0]) ** 2 + abs(left_heel[1] - left_ankle[1]) ** 2) ** 0.5
    left_ankle_knee = (abs(left_knee[0] - left_ankle[0]) ** 2 + abs(left_knee[1] - left_ankle[1]) ** 2) ** 0.5
    height_front = left_ankle_knee + left_heel_ankle + left_knee_hip + mid_point_chest()[1] + get_height_head()
    cv2.line(image_front_silhouette, (int(left_knee[0]), int(left_knee[1])), (int(left_hip[0]), int(left_hip[1])),
             (0, 255, 0), 2)
    cv2.line(image_front_silhouette, (int(left_knee[0]), int(left_knee[1])), (int(left_ankle[0]), int(left_ankle[1])),
             (0, 255, 0), 2)
    cv2.line(image_front_silhouette, (int(left_heel[0]), int(left_heel[1])), (int(left_ankle[0]), int(left_ankle[1])),
             (0, 255, 0), 2)

    cv2.imwrite("images/get_height.jpg", image_front_silhouette)
    return height_front

def get_height_side():
    mid_shoulder_side = mid_point_chest_side()[0]
    left_heel_shoulder_side = (abs(left_heel_side[1] - mid_shoulder_side[1]))
    height_side = left_heel_shoulder_side + get_height_head_side()

    cv2.line(image_side_silhouette, (int(left_heel_side[0]), int(left_heel_side[1])),
             (int(mid_shoulder_side[0]), int(mid_shoulder_side[1])),
             (0, 255, 0), 2)

    cv2.imwrite("images/get_height_side.jpg", image_side_silhouette)
    return height_side

# Enhanced circumference calculation function
def calculate_circumference(front_width, side_width=None, body_part=None):
    """Calculate circumference using appropriate method from MeasurementCalculator"""
    if side_width is None:
        return calc.calculate_circumference_from_diameter(front_width, body_part)
    else:
        if body_part in ['thigh', 'calf', 'upper_arm', 'forearm']:
            return calc.calculate_limb_circumference(front_width, side_width, body_part)
        elif body_part in ['chest', 'waist', 'hip']:
            return calc.calculate_torso_circumference(front_width, side_width, body_part)
        else:
            return calc.calculate_circumference_from_ellipse(front_width, side_width)

# Calculate heights for scaling
height_front = get_height_front()
height_side = get_height_side()

print("-----------------------------------------------------------------------------")
print("----------------------------Measurements in cm-------------------------------")

# Convert pixel measurements to cm
array_front = np.array(output_front)
front_cm = (height * array_front) / height_front
print("Cm values of pixel distances of front image")
print(front_cm)

array_side = np.array(output_side)
side_cm = (height * array_side) / height_side
print("Cm values of pixel distances side image")
print(side_cm)

array_front_linear = np.array(output_front_linear)
front_linear_cm = (height * array_front_linear) / height_front
print("Cm values of pixel distances front image linear")
print(front_linear_cm)

array_side_linear = np.array(output_side_linear)
side_linear_cm = (height * array_side_linear) / height_side
print("Cm values of pixel distances side image linear")
print(side_linear_cm)

print("---------------------------------------------------------------------------------------")
print("----------------------------Body part measurements in cm-------------------------------")
print(f"height: {height}")
print(f"height front (pixels): {height_front}")
print(f"height side (pixels): {height_side}")

# Enhanced measurements with proper calculations
print("\n--- Leg Measurements ---")
left_calf_circ = calculate_circumference(front_cm[0], side_cm[0] if len(side_cm) > 0 else None, 'calf')
right_calf_circ = calculate_circumference(front_cm[4], side_cm[2] if len(side_cm) > 2 else None, 'calf')
left_thigh_circ = calculate_circumference(front_cm[1], side_cm[1] if len(side_cm) > 1 else None, 'thigh')
right_thigh_circ = calculate_circumference(front_cm[5], side_cm[3] if len(side_cm) > 3 else None, 'thigh')

print(f"left calf circumference (mid low leg): {left_calf_circ}")
print(f"right calf circumference (mid low leg): {right_calf_circ}")
print(f"left thigh circumference (mid upper leg): {left_thigh_circ}")
print(f"right thigh circumference (mid upper leg): {right_thigh_circ}")

print("\n--- Arm Measurements ---")
left_lower_arm_circ = calculate_circumference(front_cm[3], None, 'forearm')
left_upper_arm_circ = calculate_circumference(front_cm[2], None, 'upper_arm')
right_lower_arm_circ = calculate_circumference(front_cm[7], None, 'forearm')
right_upper_arm_circ = calculate_circumference(front_cm[6], None, 'upper_arm')
arm_length = (front_cm[6] + front_cm[7]) * 0.8

print(f"left lower arm circumference: {left_lower_arm_circ}")
print(f"left upper arm circumference: {left_upper_arm_circ}")
print(f"right lower arm circumference: {right_lower_arm_circ}")
print(f"right upper arm circumference: {right_upper_arm_circ}")
print(f"arm right length: {arm_length}")

print("\n--- Torso Measurements ---")
waist_circ = calculate_circumference(front_cm[8], side_cm[4] if len(side_cm) > 4 else None, 'waist')
hip_circ = calculate_circumference(front_linear_cm[1], side_linear_cm[1] if len(side_linear_cm) > 1 else None, 'hip')
shoulder_breadth = front_linear_cm[0]

print(f"waist circumference: {waist_circ}")
print(f"hip circumference: {hip_circ}")
print(f"shoulder breadth: {shoulder_breadth}")

# Additional measurements
print("\n--- New Measurements ---")
if len(front_cm) > 15 and len(side_cm) > 7:
    neck_circ = calculate_circumference(front_cm[9], side_cm[5], 'neck')
    chest_circ = calculate_circumference(front_cm[10], side_cm[6], 'chest')
    wrist_circ = calculate_circumference(front_cm[11], None, 'wrist')
    bicep_circ = calculate_circumference(front_cm[12], None, 'bicep')
    forearm_circ = calculate_circumference(front_cm[13], None, 'forearm')
    ankle_circ = calculate_circumference(front_cm[14], None, 'ankle')
    head_circ = calculate_circumference(front_cm[15], side_cm[7], 'head')
    
    print(f"neck circumference: {neck_circ}")
    print(f"chest circumference: {chest_circ}")
    print(f"right wrist circumference: {wrist_circ}")
    print(f"right bicep circumference: {bicep_circ}")
    print(f"right forearm circumference: {forearm_circ}")
    print(f"left ankle circumference: {ankle_circ}")
    print(f"head circumference: {head_circ}")

# Linear measurements
if len(front_linear_cm) > 2:
    print(f"shoulder to crotch height: {front_linear_cm[2]}")
if len(front_linear_cm) > 3:
    print(f"right foot length: {front_linear_cm[3]}")
if len(front_linear_cm) > 4:
    print(f"right foot width: {front_linear_cm[4]}")
if len(side_linear_cm) > 2:
    print(f"back to shoulder: {side_linear_cm[2]}")

# Calculate inside leg height (inseam)
inside_leg_height = (abs(left_heel[1] - left_hip[1]) * height) / height_front
print(f"inside leg height (inseam): {inside_leg_height}")

# Create comprehensive measurements dictionary
print("\n--- Summary of All Measurements ---")
measurements_dict = {
    "Height": height,
    "Head Circumference": head_circ if 'head_circ' in locals() else "N/A",
    "Neck Circumference": neck_circ if 'neck_circ' in locals() else "N/A",
    "Shoulder to Crotch Height": front_linear_cm[2] if len(front_linear_cm) > 2 else "N/A",
    "Chest Circumference": chest_circ if 'chest_circ' in locals() else "N/A",
    "Waist Circumference": waist_circ,
    "Hip Circumference": hip_circ,
    "Right Wrist Circumference": wrist_circ if 'wrist_circ' in locals() else "N/A",
    "Right Bicep Circumference": bicep_circ if 'bicep_circ' in locals() else "N/A",
    "Right Forearm Circumference": forearm_circ if 'forearm_circ' in locals() else "N/A",
    "Right Arm Length": arm_length,
    "Inside Leg Height": inside_leg_height,
    "Left Thigh Circumference": left_thigh_circ,
    "Left Calf Circumference": left_calf_circ,
    "Left Ankle Circumference": ankle_circ if 'ankle_circ' in locals() else "N/A",
    "Right Foot Length": front_linear_cm[3] if len(front_linear_cm) > 3 else "N/A",
    "Right Foot Width": front_linear_cm[4] if len(front_linear_cm) > 4 else "N/A",
    "Shoulder Breadth": shoulder_breadth,
    "Back to Shoulder": side_linear_cm[2] if len(side_linear_cm) > 2 else "N/A"
}

print("\nFinal Measurements Report:")
for key, value in measurements_dict.items():
    if isinstance(value, (int, float)):
        print(f"{key}: {value:.2f} cm")
    else:
        print(f"{key}: {value}")
