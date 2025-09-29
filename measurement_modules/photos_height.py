# photos_height.py

import cv2
import numpy as np

front_input_image = 'distance/img1.jpg'
side_input_image = 'distance/img2.jpg'

# Configuration for height measurement
USE_AUTOMATIC_HEIGHT = True  # Set to False to use manual height
MANUAL_HEIGHT = 155  # cm - used when USE_AUTOMATIC_HEIGHT is False

height = MANUAL_HEIGHT

# Reference object configuration (for automatic measurement)
REFERENCE_OBJECT_HEIGHT_CM = 30  # Known height of reference object in cm
REFERENCE_MARKER_COLOR = (0, 255, 0)  # Green marker for reference object

def detect_reference_object(image_path):
    """
    Detect a reference object in the image (e.g., a ruler, known-size marker)
    Returns the pixel height of the reference object
    """
    img = cv2.imread(image_path)
    
    # Convert to HSV for better color detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define range for green color (adjust based on your reference marker)
    lower_green = np.array([40, 40, 40])
    upper_green = np.array([80, 255, 255])
    
    # Create mask for reference object
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Find the largest contour (assumed to be reference object)
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        return h  # Return height in pixels
    
    return None

def calculate_automatic_height(front_image_path, side_image_path):
    """
    Calculate person's height automatically using reference object
    or pose estimation
    """
    # Method 1: Using reference object
    ref_height_pixels = detect_reference_object(front_image_path)
    if ref_height_pixels:
        # Calculate pixels per cm ratio
        pixels_per_cm = ref_height_pixels / REFERENCE_OBJECT_HEIGHT_CM
        
        # Get person's height in pixels (from pose landmarks)
        from medipie_cooordinates import result_front, nose, left_heel
        if result_front and result_front.pose_landmarks:
            person_height_pixels = abs(left_heel[1] - nose[1])
            calculated_height = person_height_pixels / pixels_per_cm
            return calculated_height
    
    # Method 2: Using camera calibration (if available)
    try:
        # Load camera calibration data
        import pickle
        with open('camera_calibration_data.pkl', 'rb') as f:
            calib_data = pickle.load(f)
            # Use calibration data to estimate real-world height
            # This requires known camera distance and focal length
            focal_length = calib_data.get('focal_length', None)
            camera_distance = calib_data.get('distance', None)
            
            if focal_length and camera_distance:
                # Calculate height using similar triangles
                from medipie_cooordinates import result_front, nose, left_heel
                if result_front and result_front.pose_landmarks:
                    person_height_pixels = abs(left_heel[1] - nose[1])
                    # Height = (pixel_height * real_distance) / focal_length
                    calculated_height = (person_height_pixels * camera_distance) / focal_length
                    return calculated_height
    except:
        pass
    
    # Method 3: Using ArUco markers or checkerboard pattern
    try:
        import cv2.aruco as aruco
        img = cv2.imread(front_image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect ArUco markers
        aruco_dict = aruco.Dictionary_get(aruco.DICT_6X6_250)
        parameters = aruco.DetectorParameters_create()
        corners, ids, _ = aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
        
        if ids is not None and len(ids) > 0:
            # Known ArUco marker size (e.g., 10cm x 10cm)
            ARUCO_SIZE_CM = 10
            
            # Get marker height in pixels
            marker_corners = corners[0][0]
            marker_height_pixels = abs(marker_corners[0][1] - marker_corners[2][1])
            
            # Calculate pixels per cm
            pixels_per_cm = marker_height_pixels / ARUCO_SIZE_CM
            
            # Get person's height in pixels
            from medipie_cooordinates import result_front, nose, left_heel
            if result_front and result_front.pose_landmarks:
                person_height_pixels = abs(left_heel[1] - nose[1])
                calculated_height = person_height_pixels / pixels_per_cm
                return calculated_height
    except:
        pass
    
    # If automatic detection fails, return None
    return None

# Determine which height to use
if USE_AUTOMATIC_HEIGHT:
    height = calculate_automatic_height(front_input_image, side_input_image)
    if height is None:
        print("Automatic height detection failed. Using manual height.")
        height = MANUAL_HEIGHT
    else:
        print(f"Automatically detected height: {height:.1f} cm")
else:
    height = MANUAL_HEIGHT
    print(f"Using manual height: {height} cm")
