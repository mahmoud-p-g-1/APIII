from medipie_cooordinates import *
from math import sqrt
import os
import time

# Ensure images directory exists
if not os.path.exists('images'):
    os.makedirs('images')
    print("Created 'images' directory")

image_front_silhouette_path = 'images/add_silhouette.jpg'
image_front_silhouette = cv2.imread(image_front_silhouette_path)

image_side_silhouette_path = 'images/add_silhouette_side.jpg'
image_side_silhouette = cv2.imread(image_side_silhouette_path)


def save_image_with_retry(image, filepath, max_retries=3):
    """Save image with retry logic for permission errors"""
    for attempt in range(max_retries):
        try:
            success = cv2.imwrite(filepath, image)
            if success:
                return True
            else:
                raise Exception("cv2.imwrite returned False")
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Warning: Could not save {filepath}, retrying... (attempt {attempt + 1}/{max_retries})")
                time.sleep(0.5)  # Wait before retry
                
                # Try to close any file handles
                try:
                    import gc
                    gc.collect()
                except:
                    pass
            else:
                print(f"Error: Could not save {filepath} after {max_retries} attempts")
                # Try alternative filename
                alt_filepath = filepath.replace('.jpg', f'_backup.jpg')
                try:
                    if cv2.imwrite(alt_filepath, image):
                        print(f"Saved to alternative path: {alt_filepath}")
                        return True
                except:
                    print(f"Could not save to alternative path either: {alt_filepath}")
                    return False
    return False


def mid_point_chest_segment():
    mid_hip = [((right_hip[0] + left_hip[0]) / 2), ((right_hip[1] + left_hip[1]) / 2)]
    mid_shoulder = [((right_shoulder[0] + left_shoulder[0]) / 2), ((right_shoulder[1] + left_shoulder[1]) / 2)]
    chest_height = (abs(mid_hip[0] - mid_shoulder[0]) ** 2 + (mid_hip[1] - mid_shoulder[1]) ** 2) ** 0.5
    return mid_hip, mid_shoulder, chest_height


def mid_point_chest_segment_side():
    mid_hip_side = [((right_hip_side[0] + left_hip_side[0]) / 2), ((right_hip_side[1] + left_hip_side[1]) / 2)]
    mid_shoulder_side = [((right_shoulder_side[0] + left_shoulder_side[0]) / 2),
                         ((right_shoulder_side[1] + left_shoulder_side[1]) / 2)]
    chest_height_side = (abs(mid_hip_side[0] - mid_shoulder_side[0]) ** 2 + (
            mid_hip_side[1] - mid_shoulder_side[1]) ** 2) ** 0.5
    return mid_hip_side, mid_shoulder_side, chest_height_side


# New helper functions for additional measurements
def get_neck_point():
    # Neck point is between shoulders and ears
    mid_shoulder = mid_point_chest_segment()[1]
    mid_ear = [((right_ear[0] + left_ear[0]) / 2), ((right_ear[1] + left_ear[1]) / 2)]
    neck_point = [((mid_shoulder[0] + mid_ear[0]) / 2), ((mid_shoulder[1] + mid_ear[1]) / 2)]
    return neck_point


def get_chest_point():
    # Chest point is between shoulders and hips (upper third)
    mid_shoulder = mid_point_chest_segment()[1]
    mid_hip = mid_point_chest_segment()[0]
    chest_point = [(mid_shoulder[0] + (mid_hip[0] - mid_shoulder[0]) * 0.3),
                   (mid_shoulder[1] + (mid_hip[1] - mid_shoulder[1]) * 0.3)]
    return chest_point


def get_crotch_point():
    # Crotch point is at hip level
    return mid_point_chest_segment()[0]


mid_hip = mid_point_chest_segment()[0]
mid_shoulder = mid_point_chest_segment()[1]
chest_height = mid_point_chest_segment()[2]

mid_hip_side = mid_point_chest_segment_side()[0]
mid_shoulder_side = mid_point_chest_segment_side()[1]
chest_height_side = mid_point_chest_segment_side()[2]

# Updated points list with new measurements
points = [(left_ankle, left_knee),
          (left_knee, left_hip),
          (left_shoulder, left_elbow),
          (left_elbow, left_wrist),
          (right_ankle, right_knee),
          (right_knee, right_hip),
          (right_shoulder, right_elbow),
          (right_elbow, right_wrist),
          (mid_hip, mid_shoulder),
          # New measurements
          (get_neck_point(), get_neck_point()),  # Neck circumference
          (get_chest_point(), get_chest_point()),  # Chest circumference
          (right_wrist, right_wrist),  # Wrist circumference
          (right_elbow, right_elbow),  # Bicep circumference (at elbow level)
          ([(right_elbow[0] + right_wrist[0])/2, (right_elbow[1] + right_wrist[1])/2],
           [(right_elbow[0] + right_wrist[0])/2, (right_elbow[1] + right_wrist[1])/2]),  # Forearm
          (left_ankle, left_ankle),  # Ankle circumference
          (nose, nose),  # Head circumference (at nose level)
          ]

points_names = ["left mid low leg",
                "left mid upper leg",
                "left upper arm",
                "left lower arm",
                "right mid low leg",
                "right mid upper leg",
                "right upper arm",
                "right lower arm",
                "waist front",
                # New measurement names
                "neck front",
                "chest front",
                "right wrist",
                "right bicep",
                "right forearm",
                "left ankle",
                "head",
                ]

points_side = [(left_ankle_side, left_knee_side),
               (left_knee_side, left_hip_side),
               (right_ankle_side, right_knee_side),
               (right_knee_side, right_hip_side),
               (mid_hip_side, mid_shoulder_side),
               # New side measurements
               ([(left_shoulder_side[0] + left_ear_side[0])/2, (left_shoulder_side[1] + left_ear_side[1])/2],
                [(left_shoulder_side[0] + left_ear_side[0])/2, (left_shoulder_side[1] + left_ear_side[1])/2]),  # Neck side
               ([(mid_shoulder_side[0] + mid_hip_side[0])*0.7, (mid_shoulder_side[1] + mid_hip_side[1])*0.7],
                [(mid_shoulder_side[0] + mid_hip_side[0])*0.7, (mid_shoulder_side[1] + mid_hip_side[1])*0.7]),  # Chest side
               (nose_side, nose_side),  # Head side
               ]

points_side_names = ["left mid low leg side",
                     "left mid upper leg side",
                     "right mid low leg side",
                     "right mid upper leg side",
                     "waist side",
                     # New side measurement names
                     "neck side",
                     "chest side",
                     "head side",
                     ]

points_linear_front = [(left_shoulder, right_shoulder),
                       (left_hip, right_hip),
                       # New linear measurements
                       (mid_shoulder, get_crotch_point()),  # Shoulder to crotch
                       (right_foot_index, right_heel),  # Foot length
                       (right_foot_index, right_foot_index),  # Foot width placeholder (will measure perpendicular)
                       ]

points_linear_front_names = ["shoulders front",
                             "hips front",
                             "shoulder to crotch",
                             "right foot length",
                             "right foot width",
                             ]

points_linear_side = [(left_shoulder_side, right_shoulder_side),
                      (left_hip_side, right_hip_side),
                      # Fixed: back to shoulder measurement (using proper tuple format)
                      (left_shoulder_side, [left_shoulder_side[0] - 50, left_shoulder_side[1]]),  
                      ]

points_linear_side_names = ["shoulders side",
                            "hips side",
                            "back to shoulder",
                            ]


def calculate_distance(point):
    global x_perp1, y_perp1, x_perp2, y_perp2, current_distance_down, current_distance_up
    point_one = point[0]
    point_two = point[1]

    middle_point = [((point_one[0] + point_two[0]) / 2), ((point_one[1] + point_two[1]) / 2)]

    x_mid, y_mid = int(middle_point[0]), int(middle_point[1])
    middle_point_int = [x_mid, y_mid]

    image_front_silhouette_rgb = cv2.cvtColor(image_front_silhouette, cv2.COLOR_BGR2RGB)

    # Handle single point measurements (for circumferences)
    if point_one == point_two:
        # For single points, measure perpendicular width
        current_distance = 0
        max_length = 5000
        current_x = x_mid
        color_background = 5
        current_distance_down = 0
        current_distance_up = 0
        
        # Find border to the right
        while current_distance < max_length:
            current_x += 1
            if current_x >= image_front_silhouette.shape[1]:
                break
            if image_front_silhouette[y_mid, current_x].sum() < color_background:
                x_perp2 = current_x
                y_perp2 = y_mid
                current_distance_down = abs(current_x - x_mid)
                break
            current_distance += 1
            
        # Find border to the left
        current_x = x_mid
        current_distance = 0
        while current_distance < max_length:
            current_x -= 1
            if current_x < 0:
                break
            if image_front_silhouette[y_mid, current_x].sum() < color_background:
                x_perp1 = current_x
                y_perp1 = y_mid
                current_distance_up = abs(x_mid - current_x)
                break
            current_distance += 1
    else:
        if point_one[0] != point_two[0]:
            slope_original = (point_one[1] - point_two[1]) / (point_one[0] - point_two[0])
            slope_perpendicular = -1 / slope_original

            current_distance = 0
            max_length = 5000
            current_x = x_mid
            color_background = 5
            # Find border in one direction
            while current_distance < max_length:
                current_x += 1
                current_y = int(y_mid + slope_perpendicular * (current_x - x_mid))
                if current_y < 0 or current_y >= image_front_silhouette.shape[0]:
                    break
                if current_x >= image_front_silhouette.shape[1]:
                    break
                if image_front_silhouette[current_y, current_x].sum() < color_background:
                    x_perp2 = current_x
                    y_perp2 = current_y
                    break
                current_distance_down = sqrt((y_mid - current_y) ** 2 + (x_mid - current_x) ** 2)
            
            current_x = x_mid
            while current_distance < max_length:
                current_x -= 1
                current_y = int(y_mid + slope_perpendicular * (current_x - x_mid))
                if current_y < 0 or current_y >= image_front_silhouette.shape[0]:
                    break
                if current_x < 0:
                    break
                if image_front_silhouette[current_y, current_x].sum() < color_background:
                    x_perp1 = current_x
                    y_perp1 = current_y
                    break
                current_distance_up = sqrt((y_mid - current_y) ** 2 + (x_mid - current_x) ** 2)

    distance_body_part = current_distance_up + current_distance_down
    cv2.line(image_front_silhouette, (x_perp1, y_perp1), (x_perp2, y_perp2), (0, 255, 0), 2)
    save_image_with_retry(image_front_silhouette, "images/body_segments.jpg")

    cv2.circle(image_front_silhouette, middle_point_int, 5, (0, 0, 255), -1)

    return distance_body_part


def calculate_distance_linear(point):
    global x_perp1, y_perp1, x_perp2, y_perp2, current_distance_down, current_distance_up
    point_one = point[0]
    point_two = point[1]

    middle_point = [((point_one[0] + point_two[0]) / 2), ((point_one[1] + point_two[1]) / 2)]

    x_mid, y_mid = int(middle_point[0]), int(middle_point[1])
    middle_point_int = [x_mid, y_mid]

    image_front_silhouette_rgb = cv2.cvtColor(image_front_silhouette, cv2.COLOR_BGR2RGB)

    # For linear measurements, calculate direct distance or use existing logic
    if point_one == point_two:
        # For foot width, measure perpendicular to foot
        current_distance = 0
        max_length = 5000
        current_x = x_mid
        color_background = 5
        current_distance_down = 0
        current_distance_up = 0
        
        # Find border perpendicular
        while current_distance < max_length:
            current_x += 1
            if current_x >= image_front_silhouette.shape[1]:
                break
            if image_front_silhouette[y_mid, current_x].sum() < color_background:
                x_perp2 = current_x
                y_perp2 = y_mid
                current_distance_down = abs(current_x - x_mid)
                break
            current_distance += 1
            
        current_x = x_mid
        current_distance = 0
        while current_distance < max_length:
            current_x -= 1
            if current_x < 0:
                break
            if image_front_silhouette[y_mid, current_x].sum() < color_background:
                x_perp1 = current_x
                y_perp1 = y_mid
                current_distance_up = abs(x_mid - current_x)
                break
            current_distance += 1
        distance_body_part = current_distance_up + current_distance_down
    elif point_one[0] != point_two[0]:
        slope_original = (point_one[1] - point_two[1]) / (point_one[0] - point_two[0])

        current_distance = 0
        max_length = 5000
        current_x = x_mid
        color_background = 5
        # Find border in one direction
        while current_distance < max_length:
            current_x += 1
            current_y = int(y_mid + slope_original * (current_x - x_mid))
            if current_y < 0 or current_y >= image_front_silhouette.shape[0]:
                break
            if current_x >= image_front_silhouette.shape[1]:
                break
            if image_front_silhouette[current_y, current_x].sum() < color_background:
                x_perp2 = current_x
                y_perp2 = current_y
                break
            current_distance_down = sqrt((y_mid - current_y) ** 2 + (x_mid - current_x) ** 2)
        
        current_x = x_mid
        while current_distance < max_length:
            current_x -= 1
            current_y = int(y_mid + slope_original * (current_x - x_mid))
            if current_y < 0 or current_y >= image_front_silhouette.shape[0]:
                break
            if current_x < 0:
                break
            if image_front_silhouette[current_y, current_x].sum() < color_background:
                x_perp1 = current_x
                y_perp1 = current_y
                break
            current_distance_up = sqrt((y_mid - current_y) ** 2 + (x_mid - current_x) ** 2)

        distance_body_part = current_distance_up + current_distance_down
    else:
        distance_body_part = 0

    cv2.line(image_front_silhouette, (x_perp1, y_perp1), (x_perp2, y_perp2), (0, 255, 0), 2)
    save_image_with_retry(image_front_silhouette, "images/body_segments.jpg")
    cv2.circle(image_front_silhouette, middle_point_int, 5, (0, 0, 255), -1)

    return distance_body_part


def calculate_distance_side(point):
    global x_perp1, y_perp1, x_perp2, y_perp2, current_distance_down, current_distance_up
    point_one = point[0]
    point_two = point[1]

    middle_point = [((point_one[0] + point_two[0]) / 2), ((point_one[1] + point_two[1]) / 2)]

    x_mid, y_mid = int(middle_point[0]), int(middle_point[1])
    middle_point_int = [x_mid, y_mid]

    image_side_silhouette_rgb = cv2.cvtColor(image_side_silhouette, cv2.COLOR_BGR2RGB)

    # Handle single point measurements
    if point_one == point_two:
        current_distance = 0
        max_length = 5000
        current_x = x_mid
        color_background = 5
        current_distance_down = 0
        current_distance_up = 0
        
        # Find border to the right
        while current_distance < max_length:
            current_x += 1
            if current_x >= image_side_silhouette.shape[1]:
                break
            if image_side_silhouette[y_mid, current_x].sum() < color_background:
                x_perp2 = current_x
                y_perp2 = y_mid
                current_distance_down = abs(current_x - x_mid)
                break
            current_distance += 1
            
        # Find border to the left
        current_x = x_mid
        current_distance = 0
        while current_distance < max_length:
            current_x -= 1
            if current_x < 0:
                break
            if image_side_silhouette[y_mid, current_x].sum() < color_background:
                x_perp1 = current_x
                y_perp1 = y_mid
                current_distance_up = abs(x_mid - current_x)
                break
            current_distance += 1
    else:
        if point_one[0] != point_two[0]:
            slope_original = (point_one[1] - point_two[1]) / (point_one[0] - point_two[0])
            slope_perpendicular = -1 / slope_original

            current_distance = 0
            max_length = 5000
            current_x = x_mid
            color_background = 5
            # Find border in one direction
            while current_distance < max_length:
                current_x += 1
                current_y = int(y_mid + slope_perpendicular * (current_x - x_mid))
                if current_y < 0 or current_y >= image_side_silhouette.shape[0]:
                    break
                if current_x >= image_side_silhouette.shape[1]:
                    break
                if image_side_silhouette[current_y, current_x].sum() < color_background:
                    x_perp2 = current_x
                    y_perp2 = current_y
                    break
                current_distance_down = sqrt((y_mid - current_y) ** 2 + (x_mid - current_x) ** 2)
            
            current_x = x_mid
            while current_distance < max_length:
                current_x -= 1
                current_y = int(y_mid + slope_perpendicular * (current_x - x_mid))
                if current_y < 0 or current_y >= image_side_silhouette.shape[0]:
                    break
                if current_x < 0:
                    break
                if image_side_silhouette[current_y, current_x].sum() < color_background:
                    x_perp1 = current_x
                    y_perp1 = current_y
                    break
                current_distance_up = sqrt((y_mid - current_y) ** 2 + (x_mid - current_x) ** 2)

    distance_body_part = current_distance_up + current_distance_down
    cv2.line(image_side_silhouette, (x_perp1, y_perp1), (x_perp2, y_perp2), (0, 255, 0), 2)
    
    # Use the retry function for saving
    save_image_with_retry(image_side_silhouette, "images/body_segments_side.jpg")

    cv2.circle(image_side_silhouette, middle_point_int, 5, (0, 0, 255), -1)

    return distance_body_part


def calculate_distance_side_linear(point):
    global x_perp1, y_perp1, x_perp2, y_perp2, current_distance_down, current_distance_up
    point_one = point[0]
    point_two = point[1]

    middle_point = [((point_one[0] + point_two[0]) / 2), ((point_one[1] + point_two[1]) / 2)]

    x_mid, y_mid = int(middle_point[0]), int(middle_point[1])
    middle_point_int = [x_mid, y_mid]

    image_side_silhouette_rgb = cv2.cvtColor(image_side_silhouette, cv2.COLOR_BGR2RGB)

    if point_one[0] != point_two[0]:
        slope_original = (point_one[1] - point_two[1]) / (point_one[0] - point_two[0])

        current_distance = 0
        max_length = 5000
        current_x = x_mid
        color_background = 5
        # Find border in one direction
        while current_distance < max_length:
            current_x += 1
            current_y = int(y_mid + slope_original * (current_x - x_mid))
            if current_y < 0 or current_y >= image_side_silhouette.shape[0]:
                break
            if current_x >= image_side_silhouette.shape[1]:
                break
            if image_side_silhouette[current_y, current_x].sum() < color_background:
                x_perp2 = current_x
                y_perp2 = current_y
                break
            current_distance_down = sqrt((y_mid - current_y) ** 2 + (x_mid - current_x) ** 2)
        
        current_x = x_mid
        while current_distance < max_length:
            current_x -= 1
            current_y = int(y_mid + slope_original * (current_x - x_mid))
            if current_y < 0 or current_y >= image_side_silhouette.shape[0]:
                break
            if current_x < 0:
                break
            if image_side_silhouette[current_y, current_x].sum() < color_background:
                x_perp1 = current_x
                y_perp1 = current_y
                break
            current_distance_up = sqrt((y_mid - current_y) ** 2 + (x_mid - current_x) ** 2)

    distance_body_part = current_distance_up + current_distance_down
    cv2.line(image_side_silhouette, (x_perp1, y_perp1), (x_perp2, y_perp2), (0, 255, 0), 2)
    
    # Use the retry function for saving
    save_image_with_retry(image_side_silhouette, "images/body_segments_side.jpg")

    cv2.circle(image_side_silhouette, middle_point_int, 5, (0, 0, 255), -1)

    return distance_body_part


print("-----------------------------------------------------------------------------")
output_front = []
for idx, point in enumerate(points):
    output_front.append(calculate_distance(point))
    print(f"{points_names[idx]}: {output_front[idx]}")
print("Front view measurements array in pixel distance:")
print(output_front)
print("-----------------------------------------------------------------------------")

output_side = []
for idx, point in enumerate(points_side):
    output_side.append(calculate_distance_side(point))
    print(f"{points_side_names[idx]}: {output_side[idx]}")
print("Side view measurements array in pixel distance:")
print(output_side)
print("-----------------------------------------------------------------------------")

output_front_linear = []
for idx, point in enumerate(points_linear_front):
    output_front_linear.append(calculate_distance_linear(point))
    print(f"{points_linear_front_names[idx]}: {output_front_linear[idx]}")
print("Front linear view measurements array in pixel distance:")
print(output_front_linear)
print("-----------------------------------------------------------------------------")

output_side_linear = []
for idx, point in enumerate(points_linear_side):
    output_side_linear.append(calculate_distance_side_linear(point))
    print(f"{points_linear_side_names[idx]}: {output_side_linear[idx]}")
print("Side linear view measurements array in pixel distance:")
print(output_side_linear)
