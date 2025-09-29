# measurement_calculator.py

import numpy as np
import math
from typing import Tuple

class MeasurementCalculator:
    """Calculate body measurements using improved formulas"""
    
    @staticmethod
    def calculate_circumference_from_ellipse(width_front: float, width_side: float) -> float:
        """Calculate circumference using Ramanujan's approximation for ellipse perimeter"""
        a = width_front / 2
        b = width_side / 2
        
        h = ((a - b) ** 2) / ((a + b) ** 2)
        perimeter = math.pi * (a + b) * (1 + (3 * h) / (10 + math.sqrt(4 - 3 * h)))
        
        return perimeter
    
    @staticmethod
    def calculate_circumference_from_diameter(diameter: float, body_part: str = None) -> float:
        """Calculate circumference with body-part specific corrections"""
        circumference = diameter * math.pi
        
        corrections = {
            'wrist': 0.95,
            'ankle': 0.93,
            'neck': 0.98,
            'bicep': 1.05,
            'forearm': 1.02,
            'calf': 1.08,
            'thigh': 1.10,
        }
        
        if body_part and body_part in corrections:
            circumference *= corrections[body_part]
        
        return circumference
    
    @staticmethod
    def calculate_limb_circumference(front_width: float, side_width: float, 
                                   limb_type: str) -> float:
        """Calculate limb circumference with anatomical corrections"""
        shape_factors = {
            'upper_arm': {'ellipse_ratio': 0.85, 'muscle_factor': 1.1},
            'forearm': {'ellipse_ratio': 0.75, 'muscle_factor': 1.05},
            'thigh': {'ellipse_ratio': 0.80, 'muscle_factor': 1.15},
            'calf': {'ellipse_ratio': 0.70, 'muscle_factor': 1.12},
        }
        
        if limb_type in shape_factors:
            factors = shape_factors[limb_type]
            avg_diameter = (front_width + side_width * factors['ellipse_ratio']) / 2
            base_circumference = avg_diameter * math.pi
            return base_circumference * factors['muscle_factor']
        
        return MeasurementCalculator.calculate_circumference_from_ellipse(front_width, side_width)
    
    @staticmethod
    def calculate_torso_circumference(front_width: float, side_width: float, 
                                    torso_part: str) -> float:
        """Calculate torso measurements with anatomical considerations"""
        if torso_part == 'chest':
            return MeasurementCalculator.calculate_circumference_from_ellipse(
                front_width * 1.05,
                side_width * 0.95
            )
        elif torso_part == 'waist':
            return MeasurementCalculator.calculate_circumference_from_ellipse(
                front_width,
                side_width * 0.90
            )
        elif torso_part == 'hip':
            return MeasurementCalculator.calculate_circumference_from_ellipse(
                front_width * 1.02,
                side_width * 1.05
            )
        else:
            return MeasurementCalculator.calculate_circumference_from_ellipse(front_width, side_width)
    
    @staticmethod
    def estimate_body_fat_percentage(waist: float, neck: float, height: float, 
                                    hip: float = None, gender: str = 'male') -> float:
        """Estimate body fat percentage using Navy method"""
        if gender == 'male':
            body_fat = 86.010 * math.log10(waist - neck) - 70.041 * math.log10(height) + 36.76
        else:
            if hip:
                body_fat = 163.205 * math.log10(waist + hip - neck) - 97.684 * math.log10(height) - 78.387
            else:
                body_fat = 86.010 * math.log10(waist - neck) - 70.041 * math.log10(height) + 36.76
        
        return max(2, min(50, body_fat))
