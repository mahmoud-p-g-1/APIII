# measurement_modules/ai_measurement_validator.py

import math
import json
from datetime import datetime

class AIBodyMeasurementValidator:
    """
    AI body measurement validator and corrector that transforms raw measurements
    into clean, consistent, and realistic human body measurements.
    """
    
    def __init__(self):
        # Anthropometric ratios for validation
        self.body_ratios = {
            'leg_length': 0.45,      # 45% of height
            'arm_length': 0.32,      # 32% of height
            'chest_width': 0.18,     # 18% of height
            'waist_width': 0.15,     # 15% of height
            'hip_width': 0.19,       # 19% of height
            'shoulder_width': 0.25,  # 25% of height
        }
        
        # Circumference multipliers (width to circumference conversion)
        self.circumference_multipliers = {
            'chest': 3.2,    # Chest circumference ≈ 3.2 × chest width
            'waist': 3.1,    # Waist circumference ≈ 3.1 × waist width
            'hips': 3.3,     # Hip circumference ≈ 3.3 × hip width
        }
        
        # Clothing size ranges (chest, waist, hip in cm)
        self.size_ranges = {
            'XS': {'chest': (76, 83), 'waist': (60, 67), 'hip': (84, 91)},
            'S': {'chest': (84, 92), 'waist': (68, 75), 'hip': (92, 99)},
            'M': {'chest': (93, 101), 'waist': (76, 83), 'hip': (100, 107)},
            'L': {'chest': (102, 110), 'waist': (84, 91), 'hip': (108, 115)},
            'XL': {'chest': (111, 119), 'waist': (92, 99), 'hip': (116, 123)},
            'XXL': {'chest': (120, 128), 'waist': (100, 107), 'hip': (124, 131)}
        }
    
    def validate_and_correct_measurements(self, raw_data, detected_height=None):
        """
        Main validation function that processes raw measurement data
        
        Args:
            raw_data: Dict containing raw measurements from processing pipeline
            detected_height: Detected height in cm (optional)
            
        Returns:
            Dict with corrected measurements in JSON format
        """
        try:
            # Step 1: Extract and validate height
            height_cm = self._extract_and_validate_height(raw_data, detected_height)
            
            # Step 2: Extract raw measurements with error handling
            raw_measurements = self._extract_raw_measurements(raw_data, height_cm)
            
            # Step 3: Convert pixel measurements to centimeters
            cm_measurements = self._convert_to_centimeters(raw_measurements, height_cm)
            
            # Step 4: Apply anthropometric validation
            validated_measurements = self._apply_anthropometric_validation(cm_measurements, height_cm)
            
            # Step 5: Calculate circumferences from widths
            final_measurements = self._calculate_circumferences(validated_measurements)
            
            # Step 6: Classify clothing size
            clothing_size = self._classify_clothing_size(final_measurements)
            
            # Step 7: Calculate confidence score
            confidence_score = self._calculate_confidence_score(final_measurements, raw_measurements)
            
            # Step 8: Format final output
            return self._format_final_output(final_measurements, clothing_size, confidence_score)
            
        except Exception as e:
            print(f"[AI VALIDATOR] Error in validation: {str(e)}")
            # Return fallback measurements
            return self._create_fallback_measurements(detected_height or 170)
    
    def _extract_and_validate_height(self, raw_data, detected_height):
        """Extract and validate height from raw data"""
        # Priority: detected_height > raw_data height > default
        if detected_height and 90 <= detected_height <= 220:
            return detected_height
        
        # Try to extract from raw_data
        height_sources = ['height', 'Height', 'detected_height', 'height_cm']
        for source in height_sources:
            if source in raw_data:
                height = raw_data[source]
                if isinstance(height, (int, float)) and 90 <= height <= 220:
                    return height
        
        # Default fallback
        return 170.0
    
    def _extract_raw_measurements(self, raw_data, height_cm):
        """Extract raw measurements with error handling"""
        measurements = {}
        
        # Define measurement mappings with multiple possible keys
        measurement_mappings = {
            'chest': ['Chest Circumference', 'chest_circumference', 'chest_circ', 'chest'],
            'waist': ['Waist Circumference', 'waist_circumference', 'waist_circ', 'waist'],
            'hips': ['Hip Circumference', 'hips_circumference', 'hip_circ', 'hips'],
            'arm_length': ['Right Arm Length', 'arm_length', 'arm_length_cm'],
            'leg_length': ['Inside Leg Height', 'leg_length', 'leg_length_cm'],
            'shoulder_breadth': ['Shoulder Breadth', 'shoulder_breadth', 'shoulder_width'],
            'neck': ['Neck Circumference', 'neck_circumference', 'neck'],
            'head': ['Head Circumference', 'head_circumference', 'head']
        }
        
        # Extract measurements with fallbacks
        for measurement, possible_keys in measurement_mappings.items():
            value = None
            for key in possible_keys:
                if key in raw_data and isinstance(raw_data[key], (int, float)):
                    value = raw_data[key]
                    break
            
            # If not found, estimate from height
            if value is None:
                value = self._estimate_from_height(measurement, height_cm)
            
            measurements[measurement] = value
        
        return measurements
    
    def _estimate_from_height(self, measurement, height_cm):
        """Estimate measurement from height using anthropometric ratios"""
        estimations = {
            'chest': height_cm * 0.55,      # 55% of height
            'waist': height_cm * 0.42,      # 42% of height
            'hips': height_cm * 0.57,       # 57% of height
            'arm_length': height_cm * 0.32, # 32% of height
            'leg_length': height_cm * 0.45, # 45% of height
            'shoulder_breadth': height_cm * 0.25, # 25% of height
            'neck': height_cm * 0.20,       # 20% of height
            'head': height_cm * 0.35        # 35% of height
        }
        
        return estimations.get(measurement, height_cm * 0.3)
    
    def _convert_to_centimeters(self, raw_measurements, height_cm):
        """Convert pixel measurements to centimeters using height scaling"""
        cm_measurements = {}
        
        for measurement, value in raw_measurements.items():
            if isinstance(value, (int, float)) and value > 0:
                # If value seems to be in pixels (> 300), scale it
                if value > 300:
                    # Assume height in pixels is proportional
                    height_px = value * (1 / self.body_ratios.get(measurement.replace('_length', '').replace('_breadth', ''), 0.5))
                    scale_factor = height_cm / height_px
                    cm_measurements[measurement] = value * scale_factor
                else:
                    # Already in cm
                    cm_measurements[measurement] = value
            else:
                # Estimate from height
                cm_measurements[measurement] = self._estimate_from_height(measurement, height_cm)
        
        return cm_measurements
    
    def _apply_anthropometric_validation(self, measurements, height_cm):
        """Apply anthropometric validation rules"""
        validated = measurements.copy()
        
        # Validate arm length (30-36% of height)
        arm_min, arm_max = height_cm * 0.30, height_cm * 0.36
        validated['arm_length'] = max(arm_min, min(validated['arm_length'], arm_max))
        
        # Validate leg length (42-52% of height)
        leg_min, leg_max = height_cm * 0.42, height_cm * 0.52
        validated['leg_length'] = max(leg_min, min(validated['leg_length'], leg_max))
        
        # Validate shoulder breadth (20-30% of height)
        shoulder_min, shoulder_max = height_cm * 0.20, height_cm * 0.30
        validated['shoulder_breadth'] = max(shoulder_min, min(validated['shoulder_breadth'], shoulder_max))
        
        # Validate body circumferences (as widths for now)
        chest_min, chest_max = height_cm * 0.50, height_cm * 0.65
        validated['chest'] = max(chest_min, min(validated['chest'], chest_max))
        
        waist_min, waist_max = height_cm * 0.38, height_cm * 0.50
        validated['waist'] = max(waist_min, min(validated['waist'], waist_max))
        
        hip_min, hip_max = height_cm * 0.50, height_cm * 0.70
        validated['hips'] = max(hip_min, min(validated['hips'], hip_max))
        
        # Ensure waist < chest and waist < hips
        if validated['waist'] >= validated['chest']:
            validated['waist'] = validated['chest'] * 0.85
        
        if validated['waist'] >= validated['hips']:
            validated['waist'] = validated['hips'] * 0.90
        
        return validated
    
    def _calculate_circumferences(self, measurements):
        """Calculate circumferences from widths/diameters"""
        final_measurements = {
            'height_cm': measurements.get('height', 170),
            'arm_length_cm': measurements['arm_length'],
            'leg_length_cm': measurements['leg_length'],
            'shoulder_width_cm': measurements['shoulder_breadth']
        }
        
        # Convert widths to circumferences
        if measurements['chest'] < 150:  # Likely a width/diameter
            final_measurements['chest_circumference_cm'] = measurements['chest'] * self.circumference_multipliers['chest']
        else:  # Already a circumference
            final_measurements['chest_circumference_cm'] = measurements['chest']
        
        if measurements['waist'] < 150:  # Likely a width/diameter
            final_measurements['waist_circumference_cm'] = measurements['waist'] * self.circumference_multipliers['waist']
        else:  # Already a circumference
            final_measurements['waist_circumference_cm'] = measurements['waist']
        
        if measurements['hips'] < 150:  # Likely a width/diameter
            final_measurements['hips_circumference_cm'] = measurements['hips'] * self.circumference_multipliers['hips']
        else:  # Already a circumference
            final_measurements['hips_circumference_cm'] = measurements['hips']
        
        return final_measurements
    
    def _classify_clothing_size(self, measurements):
        """Classify clothing size based on measurements"""
        chest = measurements['chest_circumference_cm']
        waist = measurements['waist_circumference_cm']
        hips = measurements['hips_circumference_cm']
        
        best_size = 'M'
        min_distance = float('inf')
        
        for size, ranges in self.size_ranges.items():
            # Calculate distance from ideal ranges
            chest_dist = self._calculate_range_distance(chest, ranges['chest'])
            waist_dist = self._calculate_range_distance(waist, ranges['waist'])
            hip_dist = self._calculate_range_distance(hips, ranges['hip'])
            
            # Weighted distance (chest=40%, waist=35%, hips=25%)
            total_distance = (chest_dist * 0.4) + (waist_dist * 0.35) + (hip_dist * 0.25)
            
            if total_distance < min_distance:
                min_distance = total_distance
                best_size = size
        
        return best_size
    
    def _calculate_range_distance(self, value, range_tuple):
        """Calculate distance from value to range"""
        min_val, max_val = range_tuple
        if min_val <= value <= max_val:
            return 0
        elif value < min_val:
            return min_val - value
        else:
            return value - max_val
    
    def _calculate_confidence_score(self, final_measurements, raw_measurements):
        """Calculate confidence score based on measurement quality"""
        confidence = 100.0
        
        # Reduce confidence for estimated values
        for measurement in ['chest', 'waist', 'hips', 'arm_length', 'leg_length']:
            if measurement not in raw_measurements or raw_measurements[measurement] <= 0:
                confidence -= 10  # -10 for each estimated measurement
        
        # Reduce confidence for extreme corrections
        if 'chest' in raw_measurements and raw_measurements['chest'] > 0:
            chest_change = abs(final_measurements['chest_circumference_cm'] - raw_measurements['chest'])
            if chest_change > 20:  # More than 20cm change
                confidence -= 15
        
        return max(60.0, min(100.0, confidence))  # Clamp between 60-100
    
    def _format_final_output(self, measurements, clothing_size, confidence_score):
        """Format the final output in JSON format"""
        return {
            "height_cm": round(measurements['height_cm'], 1),
            "chest_circumference_cm": round(measurements['chest_circumference_cm'], 1),
            "waist_circumference_cm": round(measurements['waist_circumference_cm'], 1),
            "hips_circumference_cm": round(measurements['hips_circumference_cm'], 1),
            "arm_length_cm": round(measurements['arm_length_cm'], 1),
            "leg_length_cm": round(measurements['leg_length_cm'], 1),
            "shoulder_width_cm": round(measurements['shoulder_width_cm'], 1),
            "clothing_size": clothing_size,
            "confidence_score": round(confidence_score, 1),
            "processed_at": datetime.now().isoformat(),
            "validation_method": "ai_anthropometric"
        }
    
    def _create_fallback_measurements(self, height):
        """Create fallback measurements when processing fails"""
        return {
            "height_cm": height,
            "chest_circumference_cm": height * 0.55,
            "waist_circumference_cm": height * 0.42,
            "hips_circumference_cm": height * 0.57,
            "arm_length_cm": height * 0.32,
            "leg_length_cm": height * 0.45,
            "shoulder_width_cm": height * 0.25,
            "clothing_size": "M",
            "confidence_score": 60.0,
            "processed_at": datetime.now().isoformat(),
            "validation_method": "fallback_estimation"
        }

# Global validator instance
ai_validator = AIBodyMeasurementValidator()

def validate_measurements(raw_data, detected_height=None):
    """Convenience function for measurement validation"""
    return ai_validator.validate_and_correct_measurements(raw_data, detected_height)
