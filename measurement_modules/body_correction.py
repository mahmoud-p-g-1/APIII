# measurement_modules/body_correction.py

import math

class AnthropometricBodyValidator:
    """
    AI system that validates and corrects body measurements extracted from images.
    Relies only on detected values and known human body proportions.
    """
    
    def __init__(self):
        # Anthropometric ratios relative to height (based on research data)
        self.height_ratios = {
            'head_circumference': (0.33, 0.38),      # 33-38% of height
            'neck_circumference': (0.20, 0.25),      # 20-25% of height  
            'chest_circumference': (0.50, 0.65),     # 50-65% of height
            'waist_circumference': (0.38, 0.50),     # 38-50% of height
            'hip_circumference': (0.45, 0.60),       # 45-60% of height
            'arm_length': (0.32, 0.36),              # 32-36% of height
            'leg_length': (0.44, 0.52),              # 44-52% of height
            'foot_length': (0.14, 0.16),             # 14-16% of height
            'shoulder_breadth': (0.22, 0.28),        # 22-28% of height
        }
        
        # Absolute ranges for specific measurements
        self.absolute_ranges = {
            'wrist_circumference_female': (13, 17),   # 13-17 cm for females
            'wrist_circumference_male': (15, 20),     # 15-20 cm for males
            'ankle_circumference': (18, 26),          # 18-26 cm
            'neck_to_chest_ratio': (0.20, 0.25),     # Neck = 20-25% of chest
        }
        
        # Female clothing size ranges (EU standard)
        self.female_sizes = {
            'XS': {'chest': (76, 83), 'waist': (60, 67), 'hip': (84, 91)},
            'S': {'chest': (84, 92), 'waist': (68, 75), 'hip': (92, 99)},
            'M': {'chest': (93, 101), 'waist': (76, 83), 'hip': (100, 107)},
            'L': {'chest': (102, 110), 'waist': (84, 91), 'hip': (108, 115)},
            'XL': {'chest': (111, 119), 'waist': (92, 99), 'hip': (116, 123)},
            'XXL': {'chest': (120, 128), 'waist': (100, 107), 'hip': (124, 131)},
            'XXXL': {'chest': (129, 137), 'waist': (108, 115), 'hip': (132, 139)},
            'XXXXL': {'chest': (138, 999), 'waist': (116, 999), 'hip': (140, 999)}
        }
        
        # Male clothing size ranges
        self.male_sizes = {
            'XS': {'chest': (86, 91), 'waist': (71, 76), 'hip': (86, 91)},
            'S': {'chest': (91, 96), 'waist': (76, 81), 'hip': (91, 96)},
            'M': {'chest': (96, 101), 'waist': (81, 86), 'hip': (96, 101)},
            'L': {'chest': (101, 106), 'waist': (86, 91), 'hip': (101, 106)},
            'XL': {'chest': (106, 111), 'waist': (91, 96), 'hip': (106, 111)},
            'XXL': {'chest': (111, 116), 'waist': (96, 101), 'hip': (111, 116)},
            'XXXL': {'chest': (116, 121), 'waist': (101, 106), 'hip': (116, 121)},
            'XXXXL': {'chest': (121, 999), 'waist': (106, 999), 'hip': (121, 999)}
        }
    
    def clamp_to_range(self, value, min_val, max_val):
        """Clamp value to range instead of overwriting"""
        return max(min_val, min(value, max_val))
    
    def detect_gender(self, measurements):
        """Detect gender from measurement patterns"""
        waist = measurements.get('waist_circumference_cm', 0)
        hip = measurements.get('hips_circumference_cm', 0)
        
        if waist > 0 and hip > 0:
            whr = waist / hip
            # Female WHR typically 0.7-0.8, Male WHR typically 0.85-0.95
            return 'female' if whr < 0.82 else 'male'
        
        return 'female'  # Default assumption
    
    def validate_and_correct_measurements(self, detected_measurements):
        """
        Main validation function that corrects measurements based on anthropometric rules
        
        Args:
            detected_measurements: Dict of detected measurements from image processing
            
        Returns:
            Dict with corrected measurements, sources, clothing size, and confidence
        """
        # Parse and normalize input
        measurements = self._parse_detected_measurements(detected_measurements)
        
        # Detect gender for appropriate corrections
        gender = self.detect_gender(measurements)
        
        # Extract core measurements with defaults based on height
        height = measurements.get('height', 170.0)
        
        # Initialize result structure
        result = {
            'measurements': {},
            'sources': {},
            'gender_detected': gender,
            'confidence_score': 0.0
        }
        
        # Process each measurement type
        corrected_data = self._process_all_measurements(measurements, height, gender)
        
        # Calculate confidence score
        confidence = self._calculate_confidence_score(corrected_data, measurements)
        
        # Classify clothing size
        clothing_size = self._classify_clothing_size(
            corrected_data['chest_circumference_cm']['value'],
            corrected_data['waist_circumference_cm']['value'], 
            corrected_data['hips_circumference_cm']['value'],
            gender
        )
        
        # Format final output
        final_result = self._format_final_output(corrected_data, clothing_size, confidence)
        
        return final_result
    
    def _parse_detected_measurements(self, detected_measurements):
        """Parse and normalize detected measurements"""
        measurements = {}
        
        for key, value in detected_measurements.items():
            if isinstance(value, str):
                try:
                    measurements[key] = float(value)
                except ValueError:
                    measurements[key] = None
            elif isinstance(value, (int, float)):
                measurements[key] = float(value)
            else:
                measurements[key] = None
        
        return measurements
    
    def _process_all_measurements(self, measurements, height, gender):
        """Process all measurements with anthropometric validation"""
        corrected_data = {}
        
        # Height (preserve exactly as given)
        corrected_data['height'] = {
            'value': height,
            'source': 'original'
        }
        
        # Weight validation and estimation
        weight = measurements.get('weight')
        corrected_data['weight'] = self._process_weight(weight, height)
        
        # Head circumference
        head_circ = measurements.get('head_circumference_cm')
        corrected_data['head_circumference_cm'] = self._process_measurement_with_height_ratio(
            head_circ, height, 'head_circumference', 'Head circumference'
        )
        
        # Neck circumference  
        neck_circ = measurements.get('neck_circumference_cm')
        corrected_data['neck_circumference_cm'] = self._process_measurement_with_height_ratio(
            neck_circ, height, 'neck_circumference', 'Neck circumference'
        )
        
        # Chest circumference
        chest_circ = measurements.get('chest_circumference_cm')
        corrected_data['chest_circumference_cm'] = self._process_measurement_with_height_ratio(
            chest_circ, height, 'chest_circumference', 'Chest circumference'
        )
        
        # Waist circumference (with additional proportional checks)
        waist_circ = measurements.get('waist_circumference_cm')
        corrected_data['waist_circumference_cm'] = self._process_waist_measurement(
            waist_circ, height, corrected_data.get('chest_circumference_cm', {}).get('value', height * 0.57)
        )
        
        # Hip circumference (with waist relationship check)
        hip_circ = measurements.get('hips_circumference_cm')
        corrected_data['hips_circumference_cm'] = self._process_hip_measurement(
            hip_circ, height, corrected_data['waist_circumference_cm']['value']
        )
        
        # Arm length
        arm_length = measurements.get('arm_length_cm')
        corrected_data['arm_length_cm'] = self._process_measurement_with_height_ratio(
            arm_length, height, 'arm_length', 'Arm length'
        )
        
        # Leg length
        leg_length = measurements.get('leg_length_cm')
        corrected_data['leg_length_cm'] = self._process_measurement_with_height_ratio(
            leg_length, height, 'leg_length', 'Leg length'
        )
        
        # Foot length
        foot_length = measurements.get('foot_length_cm')
        corrected_data['foot_length_cm'] = self._process_measurement_with_height_ratio(
            foot_length, height, 'foot_length', 'Foot length'
        )
        
        # Wrist circumference (gender-specific)
        wrist_circ = measurements.get('wrist_circumference_cm')
        corrected_data['wrist_circumference_cm'] = self._process_wrist_measurement(wrist_circ, gender)
        
        # Shoulder breadth
        shoulder_breadth = measurements.get('shoulder_breadth_cm')
        corrected_data['shoulder_breadth_cm'] = self._process_measurement_with_height_ratio(
            shoulder_breadth, height, 'shoulder_breadth', 'Shoulder breadth'
        )
        
        return corrected_data
    
    def _process_weight(self, detected_weight, height):
        """Process weight with BMI validation and blending"""
        height_m = height / 100
        
        # Estimate healthy weight using BMI 22 (middle of healthy range)
        estimated_weight = 22 * (height_m ** 2)
        
        if detected_weight is None or detected_weight <= 0:
            return {
                'value': estimated_weight,
                'source': 'estimated'
            }
        
        # Check BMI range (16-32)
        bmi = detected_weight / (height_m ** 2)
        
        if 16 <= bmi <= 32:
            return {
                'value': detected_weight,
                'source': 'original'
            }
        else:
            # Blend detected with estimated (60% detected + 40% estimated)
            blended_weight = (detected_weight * 0.6) + (estimated_weight * 0.4)
            return {
                'value': blended_weight,
                'source': 'corrected'
            }
    
    def _process_measurement_with_height_ratio(self, detected_value, height, ratio_key, description):
        """Process measurement using height ratio validation"""
        if ratio_key not in self.height_ratios:
            # If no ratio defined, estimate from height
            estimated_value = height * 0.5  # Default fallback
        else:
            min_ratio, max_ratio = self.height_ratios[ratio_key]
            min_val = height * min_ratio
            max_val = height * max_ratio
            estimated_value = height * ((min_ratio + max_ratio) / 2)
        
        if detected_value is None or detected_value <= 0:
            return {
                'value': estimated_value,
                'source': 'estimated'
            }
        
        # Check if within valid range
        if ratio_key in self.height_ratios:
            min_ratio, max_ratio = self.height_ratios[ratio_key]
            min_val = height * min_ratio
            max_val = height * max_ratio
            
            if min_val <= detected_value <= max_val:
                return {
                    'value': detected_value,
                    'source': 'original'
                }
            else:
                # Clamp to valid range
                clamped_value = self.clamp_to_range(detected_value, min_val, max_val)
                return {
                    'value': clamped_value,
                    'source': 'corrected'
                }
        
        return {
            'value': detected_value,
            'source': 'original'
        }
    
    def _process_waist_measurement(self, detected_waist, height, chest_value):
        """Process waist with additional chest relationship validation"""
        min_ratio, max_ratio = self.height_ratios['waist_circumference']
        min_val = height * min_ratio
        max_val = height * max_ratio
        estimated_value = height * ((min_ratio + max_ratio) / 2)
        
        if detected_waist is None or detected_waist <= 0:
            return {
                'value': estimated_value,
                'source': 'estimated'
            }
        
        # First clamp to height ratio
        clamped_waist = self.clamp_to_range(detected_waist, min_val, max_val)
        
        # Then ensure waist < chest (waist should be 70-90% of chest)
        max_waist_from_chest = chest_value * 0.90
        min_waist_from_chest = chest_value * 0.70
        
        final_waist = self.clamp_to_range(clamped_waist, min_waist_from_chest, max_waist_from_chest)
        
        if abs(final_waist - detected_waist) < 1.0:  # Within 1cm tolerance
            return {
                'value': detected_waist,
                'source': 'original'
            }
        else:
            return {
                'value': final_waist,
                'source': 'corrected'
            }
    
    def _process_hip_measurement(self, detected_hip, height, waist_value):
        """Process hip with waist relationship validation"""
        min_ratio, max_ratio = self.height_ratios['hip_circumference']
        min_val = height * min_ratio
        max_val = height * max_ratio
        estimated_value = height * ((min_ratio + max_ratio) / 2)
        
        if detected_hip is None or detected_hip <= 0:
            return {
                'value': estimated_value,
                'source': 'estimated'
            }
        
        # First clamp to height ratio
        clamped_hip = self.clamp_to_range(detected_hip, min_val, max_val)
        
        # Ensure hip >= waist (hip should be 100-130% of waist)
        min_hip_from_waist = waist_value * 1.00
        max_hip_from_waist = waist_value * 1.30
        
        final_hip = self.clamp_to_range(clamped_hip, min_hip_from_waist, max_hip_from_waist)
        
        if abs(final_hip - detected_hip) < 1.0:  # Within 1cm tolerance
            return {
                'value': detected_hip,
                'source': 'original'
            }
        else:
            return {
                'value': final_hip,
                'source': 'corrected'
            }
    
    def _process_wrist_measurement(self, detected_wrist, gender):
        """Process wrist measurement with gender-specific ranges"""
        if gender == 'female':
            min_val, max_val = self.absolute_ranges['wrist_circumference_female']
        else:
            min_val, max_val = self.absolute_ranges['wrist_circumference_male']
        
        estimated_value = (min_val + max_val) / 2
        
        if detected_wrist is None or detected_wrist <= 0:
            return {
                'value': estimated_value,
                'source': 'estimated'
            }
        
        if min_val <= detected_wrist <= max_val:
            return {
                'value': detected_wrist,
                'source': 'original'
            }
        else:
            clamped_value = self.clamp_to_range(detected_wrist, min_val, max_val)
            return {
                'value': clamped_value,
                'source': 'corrected'
            }
    
    def _calculate_confidence_score(self, corrected_data, original_measurements):
        """Calculate overall confidence score based on corrections made"""
        total_measurements = len(corrected_data)
        original_count = sum(1 for data in corrected_data.values() 
                           if isinstance(data, dict) and data.get('source') == 'original')
        corrected_count = sum(1 for data in corrected_data.values() 
                            if isinstance(data, dict) and data.get('source') == 'corrected')
        estimated_count = sum(1 for data in corrected_data.values() 
                            if isinstance(data, dict) and data.get('source') == 'estimated')
        
        # Calculate confidence: original=100%, corrected=70%, estimated=40%
        confidence = ((original_count * 100) + (corrected_count * 70) + (estimated_count * 40)) / total_measurements
        
        return min(100, max(0, confidence))
    
    def _classify_clothing_size(self, chest, waist, hip, gender):
        """Classify clothing size using distance scoring"""
        size_ranges = self.female_sizes if gender == 'female' else self.male_sizes
        
        min_distance = float('inf')
        best_size = 'Unknown'
        
        for size, ranges in size_ranges.items():
            # Calculate distance from each measurement to its range
            chest_distance = self._calculate_range_distance(chest, ranges['chest'])
            waist_distance = self._calculate_range_distance(waist, ranges['waist'])
            hip_distance = self._calculate_range_distance(hip, ranges['hip'])
            
            # Weighted distance (chest=40%, waist=35%, hip=25%)
            total_distance = (chest_distance * 0.4) + (waist_distance * 0.35) + (hip_distance * 0.25)
            
            if total_distance < min_distance:
                min_distance = total_distance
                best_size = size
        
        # Return Unknown if distance is too high (>15cm average deviation)
        return best_size if min_distance < 15 else 'Unknown'
    
    def _calculate_range_distance(self, value, range_tuple):
        """Calculate distance from value to range"""
        min_val, max_val = range_tuple
        
        if min_val <= value <= max_val:
            return 0  # Perfect fit
        elif value < min_val:
            return min_val - value  # Distance below range
        else:
            return value - max_val if max_val != 999 else 0  # Distance above range
    
    def _format_final_output(self, corrected_data, clothing_size, confidence):
        """Format the final output according to specifications"""
        result = {}
        
        # Add all measurements with source tracking
        for key, data in corrected_data.items():
            if isinstance(data, dict) and 'value' in data:
                result[key] = {
                    "value": f"{data['value']:.1f}",
                    "source": data['source']
                }
        
        # Add clothing size
        result["clothing_size"] = {
            "value": clothing_size,
            "source": "calculated"
        }
        
        # Add confidence score
        result["confidence_score"] = {
            "value": f"{confidence:.1f}",
            "source": "calculated"
        }
        
        return result

# Global instance for easy import
anthropometric_validator = AnthropometricBodyValidator()

def validate_body_measurements(detected_measurements):
    """Convenience function for measurement validation"""
    return anthropometric_validator.validate_and_correct_measurements(detected_measurements)

# Example usage and testing
if __name__ == "__main__":
    # Test with example data
    test_input = {
        "height": "155.0",
        "weight": "71.5", 
        "chest_circumference_cm": "96.0",
        "waist_circumference_cm": "119.1",  # Too high - will be clamped
        "hips_circumference_cm": "211.7",   # Way too high - will be clamped
        "arm_length_cm": "72.8",            # Too high - will be clamped
        "leg_length_cm": "69.7",            # Good
        "neck_circumference_cm": "71.1"     # Too high - will be clamped
    }
    
    result = validate_body_measurements(test_input)
    print("Validation Result:")
    for key, data in result.items():
        print(f"  {key}: {data}")
