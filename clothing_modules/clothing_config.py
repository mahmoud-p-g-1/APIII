# clothing_modules/clothing_config.py

import os

# Configuration
clothing_input_image = 'clothing_input.jpg'
measurement_mode = 'professional'

# Professional sizing data from your inseam table (hardcoded as requested)
PROFESSIONAL_SIZING_BY_HEIGHT = {
    # Height range 150-158 cm
    (150, 158): {
        'inseam': (66, 75),
        'arm_length': (50, 57),
        'shoulder_width': (34, 39),
        'thigh': (52, 60),
        'hip': (88, 100),
        'waist': (65, 80),
        'chest': (80, 95),
        'neck': (32, 36)
    },
    # Height range 159-165 cm
    (159, 165): {
        'inseam': (70, 78),
        'arm_length': (53, 60),
        'shoulder_width': (36, 41),
        'thigh': (54, 64),
        'hip': (92, 105),
        'waist': (68, 85),
        'chest': (84, 100),
        'neck': (33, 37)
    },
    # Height range 166-172 cm
    (166, 172): {
        'inseam': (74, 82),
        'arm_length': (56, 63),
        'shoulder_width': (38, 43),
        'thigh': (56, 68),
        'hip': (96, 110),
        'waist': (71, 90),
        'chest': (88, 105),
        'neck': (34, 38)
    },
    # Height range 173-180 cm
    (173, 180): {
        'inseam': (78, 86),
        'arm_length': (59, 66),
        'shoulder_width': (40, 45),
        'thigh': (58, 72),
        'hip': (100, 115),
        'waist': (74, 95),
        'chest': (92, 110),
        'neck': (35, 39)
    }
}

# Convert to size-based professional sizing (S/M/L/XL/XXL - NO XS)
PROFESSIONAL_SIZING = {
    'S': {'chest': (78, 85), 'waist': (62, 69), 'hips': (84, 91), 'inseam': (67, 71), 'arm_length': (50, 54)},
    'M': {'chest': (86, 93), 'waist': (70, 77), 'hips': (92, 99), 'inseam': (72, 76), 'arm_length': (55, 59)},
    'L': {'chest': (94, 101), 'waist': (78, 85), 'hips': (100, 107), 'inseam': (77, 81), 'arm_length': (60, 64)},
    'XL': {'chest': (102, 109), 'waist': (86, 93), 'hips': (108, 115), 'inseam': (82, 86), 'arm_length': (65, 69)},
    'XXL': {'chest': (110, 120), 'waist': (94, 102), 'hips': (116, 125), 'inseam': (87, 91), 'arm_length': (70, 74)}
}

class ClothingConfig:
    """Clothing measurement configuration"""
    
    def __init__(self):
        self.measurement_mode = "auto"
        self.professional_sizing = PROFESSIONAL_SIZING
        self.sizing_by_height = PROFESSIONAL_SIZING_BY_HEIGHT
    
    def get_sizing_for_height(self, height):
        """Get sizing ranges for specific height"""
        for height_range, measurements in PROFESSIONAL_SIZING_BY_HEIGHT.items():
            min_height, max_height = height_range
            if min_height <= height <= max_height:
                return measurements
        
        # Default to medium range if height not found
        return PROFESSIONAL_SIZING_BY_HEIGHT[(159, 165)]
