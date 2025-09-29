# height_measurement.py

import cv2
import numpy as np
import mediapipe as mp
from math import sqrt
from measurement_config import MeasurementConfig

class HeightMeasurement:
    def __init__(self, front_image_path, side_image_path):
        self.front_image = front_image_path
        self.side_image = side_image_path
        self.config = MeasurementConfig()
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        
    def measure_height(self):
        """Main method to get height based on body proportions"""
        mode = self.config.get_height_mode()
        
        if mode == "manual":
            return self.get_manual_height()
        elif mode == "auto":
            height = self.get_automatic_height()
            if height is None or not self.validate_height(height):
                print(f"Invalid height detected: {height} cm" if height else "Height detection failed")
                if self.config.FALLBACK_TO_MANUAL:
                    print("Falling back to manual entry")
                    return self.get_manual_height()
            return height
        elif mode == "hybrid":
            auto_height = self.get_automatic_height()
            if auto_height and self.validate_height(auto_height):
                return self.confirm_height(auto_height)
            else:
                print("Automatic detection failed or invalid")
                return self.get_manual_height()
    
    def validate_height(self, height):
        """Validate if height is within human range"""
        return self.config.MIN_HUMAN_HEIGHT <= height <= self.config.MAX_HUMAN_HEIGHT
    
    def get_automatic_height(self):
        """Calculate height using anthropometric proportions"""
        methods = [
            self.calculate_height_from_proportions,
            self.calculate_height_from_head_ratio,
            self.calculate_height_from_arm_span,
            self.calculate_height_from_leg_ratio,
        ]
        
        heights = []
        for method in methods:
            try:
                height = method()
                if height and self.validate_height(height):
                    heights.append(height)
                    print(f"{method.__name__}: {height:.1f} cm")
            except Exception as e:
                continue
        
        if heights:
            median_height = np.median(heights)
            print(f"Median height from all methods: {median_height:.1f} cm")
            return median_height
        
        return None
    
    def calculate_height_from_proportions(self):
        """Calculate height using standard body proportions"""
        img = cv2.imread(self.front_image)
        image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result = self.pose.process(image_rgb)
        
        if not result.pose_landmarks:
            return None
            
        height, width, _ = img.shape
        landmarks = result.pose_landmarks.landmark
        
        # Get key points in pixels
        nose_y = landmarks[0].y * height
        left_ankle_y = landmarks[27].y * height
        left_heel_y = landmarks[29].y * height
        left_hip_y = landmarks[23].y * height
        left_shoulder_y = landmarks[11].y * height
        
        # Calculate body segments in pixels
        total_height_pixels = abs(left_heel_y - nose_y)
        head_to_nose_pixels = total_height_pixels * 0.05
        leg_length_pixels = abs(left_heel_y - left_hip_y)
        torso_length_pixels = abs(left_hip_y - left_shoulder_y)
        
        # Apply anthropometric ratios
        height_from_legs = (leg_length_pixels / 0.47) * 170 / total_height_pixels
        height_from_torso = (torso_length_pixels / 0.30) * 170 / total_height_pixels
        
        adjusted_total_pixels = total_height_pixels + head_to_nose_pixels
        pixel_to_cm_ratio = self.estimate_pixel_to_cm_ratio(adjusted_total_pixels, img.shape)
        height_from_total = adjusted_total_pixels * pixel_to_cm_ratio
        
        heights = [h for h in [height_from_legs, height_from_torso, height_from_total] 
                  if 90 <= h <= 220]
        
        if heights:
            return np.mean(heights)
        
        return None
    
    def calculate_height_from_head_ratio(self):
        """Calculate height using head-to-body ratio"""
        img = cv2.imread(self.front_image)
        image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result = self.pose.process(image_rgb)
        
        if not result.pose_landmarks:
            return None
            
        height, width, _ = img.shape
        landmarks = result.pose_landmarks.landmark
        
        nose_y = landmarks[0].y * height
        mouth_y = landmarks[10].y * height
        left_eye_y = landmarks[2].y * height
        
        face_height_pixels = abs(mouth_y - left_eye_y)
        head_height_pixels = face_height_pixels * 2
        estimated_height_pixels = head_height_pixels * 7.75
        
        pixel_to_cm_ratio = self.estimate_pixel_to_cm_ratio(estimated_height_pixels, img.shape)
        height_cm = estimated_height_pixels * pixel_to_cm_ratio
        
        return height_cm if 90 <= height_cm <= 220 else None
    
    def calculate_height_from_arm_span(self):
        """Calculate height from arm span"""
        img = cv2.imread(self.front_image)
        image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result = self.pose.process(image_rgb)
        
        if not result.pose_landmarks:
            return None
            
        height, width, _ = img.shape
        landmarks = result.pose_landmarks.landmark
        
        left_wrist_x = landmarks[15].x * width
        right_wrist_x = landmarks[16].x * width
        left_shoulder_x = landmarks[11].x * width
        right_shoulder_x = landmarks[12].x * width
        
        wrist_span_pixels = abs(right_wrist_x - left_wrist_x)
        shoulder_span_pixels = abs(right_shoulder_x - left_shoulder_x)
        
        estimated_hand_length = shoulder_span_pixels * 0.15
        full_arm_span_pixels = wrist_span_pixels + (2 * estimated_hand_length)
        
        pixel_to_cm_ratio = self.estimate_pixel_to_cm_ratio(full_arm_span_pixels, img.shape)
        height_cm = full_arm_span_pixels * pixel_to_cm_ratio
        
        return height_cm if 90 <= height_cm <= 220 else None
    
    def calculate_height_from_leg_ratio(self):
        """Calculate height from leg measurements"""
        img = cv2.imread(self.front_image)
        image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result = self.pose.process(image_rgb)
        
        if not result.pose_landmarks:
            return None
            
        height, width, _ = img.shape
        landmarks = result.pose_landmarks.landmark
        
        left_heel_y = landmarks[29].y * height
        left_hip_y = landmarks[23].y * height
        left_knee_y = landmarks[25].y * height
        
        inseam_pixels = abs(left_heel_y - left_hip_y)
        thigh_pixels = abs(left_hip_y - left_knee_y)
        shin_pixels = abs(left_knee_y - left_heel_y)
        
        height_from_inseam = inseam_pixels / 0.45
        height_from_thigh = thigh_pixels / 0.23
        height_from_shin = shin_pixels / 0.22
        
        pixel_to_cm_ratio = self.estimate_pixel_to_cm_ratio(height_from_inseam, img.shape)
        
        heights = []
        for h in [height_from_inseam, height_from_thigh, height_from_shin]:
            height_cm = h * pixel_to_cm_ratio
            if 90 <= height_cm <= 220:
                heights.append(height_cm)
        
        return np.mean(heights) if heights else None
    
    def estimate_pixel_to_cm_ratio(self, height_pixels, image_shape):
        """Estimate pixel to cm conversion ratio"""
        image_height = image_shape[0]
        fill_ratio = height_pixels / image_height
        
        if fill_ratio < 0.5:
            scale_factor = 0.5 / fill_ratio
        elif fill_ratio > 0.95:
            scale_factor = 0.85 / fill_ratio
        else:
            scale_factor = 1.0
        
        base_ratio = 170 / 1000
        adjusted_ratio = base_ratio * scale_factor
        
        return adjusted_ratio
    
    def get_manual_height(self):
        """Get height manually with validation"""
        while True:
            if self.config.PROMPT_FOR_HEIGHT:
                try:
                    height = float(input("Please enter height in cm (90-220): "))
                    if self.validate_height(height):
                        return height
                    else:
                        print(f"Height {height} cm is outside valid range (90-220 cm)")
                except:
                    print("Invalid input. Please enter a number.")
            else:
                return self.config.MANUAL_HEIGHT_CM
    
    def confirm_height(self, detected_height):
        """Allow user to confirm or adjust detected height"""
        print(f"Detected height: {detected_height:.1f} cm")
        response = input("Is this correct? (y/n/enter new value): ").strip().lower()
        
        if response == 'y':
            return detected_height
        elif response == 'n':
            return self.get_manual_height()
        else:
            try:
                height = float(response)
                if self.validate_height(height):
                    return height
                else:
                    print(f"Invalid height. Using detected: {detected_height:.1f} cm")
                    return detected_height
            except:
                return detected_height
