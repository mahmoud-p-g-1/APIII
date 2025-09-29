# measurement_validator.py

import numpy as np
from typing import Dict, Tuple, List

class MeasurementValidator:
    """Validates and corrects body measurements using anthropometric rules"""
    
    def __init__(self, height_cm: float):
        self.height = height_cm
        self.setup_anthropometric_ratios()
        
    def setup_anthropometric_ratios(self):
        """Define standard anthropometric ratios based on research"""
        self.ratios = {
            'head_circumference': (0.31, 0.37),
            'neck_circumference': (0.20, 0.25),
            'chest_circumference': (0.50, 0.65),
            'waist_circumference': (0.38, 0.50),
            'hip_circumference': (0.50, 0.65),
            'shoulder_breadth': (0.23, 0.28),
            'arm_length': (0.43, 0.47),
            'upper_arm_circumference': (0.15, 0.22),
            'forearm_circumference': (0.13, 0.18),
            'wrist_circumference': (0.09, 0.11),
            'thigh_circumference': (0.28, 0.38),
            'calf_circumference': (0.19, 0.25),
            'ankle_circumference': (0.12, 0.15),
            'inseam': (0.43, 0.47),
            'foot_length': (0.14, 0.16),
            'foot_width': (0.05, 0.07),
        }
        
        self.relationships = {
            'waist_to_hip': (0.65, 0.95),
            'chest_to_waist': (1.15, 1.45),
            'thigh_to_calf': (1.4, 1.8),
            'upper_arm_to_forearm': (1.1, 1.3),
        }
    
    def validate_measurement(self, measurement_name: str, value: float) -> Tuple[bool, float]:
        """Validate a single measurement and return corrected value if needed"""
        if measurement_name in self.ratios:
            min_ratio, max_ratio = self.ratios[measurement_name]
            min_val = self.height * min_ratio
            max_val = self.height * max_ratio
            
            if min_val <= value <= max_val:
                return True, value
            else:
                corrected = self.height * (min_ratio + max_ratio) / 2
                return False, corrected
        return True, value
    
    def validate_all_measurements(self, measurements: Dict) -> Dict:
        """Validate and correct all measurements"""
        corrected = {}
        corrections_made = []
        
        for key, value in measurements.items():
            if isinstance(value, (int, float)) and value != "N/A":
                validation_key = self.get_validation_key(key)
                if validation_key:
                    is_valid, corrected_value = self.validate_measurement(validation_key, value)
                    if not is_valid:
                        corrections_made.append(f"{key}: {value:.1f} -> {corrected_value:.1f}")
                        corrected[key] = corrected_value
                    else:
                        corrected[key] = value
                else:
                    corrected[key] = value
            else:
                corrected[key] = value
        
        corrected = self.validate_relationships(corrected)
        
        if corrections_made:
            print("\n--- Measurement Corrections Applied ---")
            for correction in corrections_made:
                print(correction)
        
        return corrected
    
    def get_validation_key(self, measurement_name: str) -> str:
        """Map measurement names to validation keys"""
        mapping = {
            'Head Circumference': 'head_circumference',
            'Neck Circumference': 'neck_circumference',
            'Chest Circumference': 'chest_circumference',
            'Waist Circumference': 'waist_circumference',
            'Hip Circumference': 'hip_circumference',
            'Shoulder Breadth': 'shoulder_breadth',
            'Right Arm Length': 'arm_length',
            'Right Bicep Circumference': 'upper_arm_circumference',
            'Right Forearm Circumference': 'forearm_circumference',
            'Right Wrist Circumference': 'wrist_circumference',
            'Left Thigh Circumference': 'thigh_circumference',
            'Left Calf Circumference': 'calf_circumference',
            'Left Ankle Circumference': 'ankle_circumference',
            'Inside Leg Height': 'inseam',
            'Right Foot Length': 'foot_length',
            'Right Foot Width': 'foot_width',
        }
        return mapping.get(measurement_name, None)
    
    def validate_relationships(self, measurements: Dict) -> Dict:
        """Validate measurement relationships"""
        if 'Waist Circumference' in measurements and 'Hip Circumference' in measurements:
            waist = measurements['Waist Circumference']
            hip = measurements['Hip Circumference']
            ratio = waist / hip if hip > 0 else 0
            
            if not (0.65 <= ratio <= 0.95):
                measurements['Waist Circumference'] = hip * 0.80
        
        if 'Chest Circumference' in measurements and 'Waist Circumference' in measurements:
            chest = measurements['Chest Circumference']
            waist = measurements['Waist Circumference']
            ratio = chest / waist if waist > 0 else 0
            
            if not (1.15 <= ratio <= 1.45):
                measurements['Chest Circumference'] = waist * 1.30
        
        return measurements
