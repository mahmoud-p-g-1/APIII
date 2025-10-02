# measurement_modules/vton_measurement_validator.py

import math
import json
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class VTONMeasurementValidator:
    """
    Professional body measurement validator for Virtual Try-On (VTON) applications.
    Fixes critical issues: oversized measurements, scaling errors, validation problems.
    """
    
    def __init__(self):
        # Human body measurement ranges (in cm)
        self.human_ranges = {
            'wrist_circumference': (13, 22),
            'forearm_circumference': (22, 30),
            'bicep_circumference': (26, 36),
            'chest_circumference': (75, 120),
            'waist_circumference': (60, 110),
            'hip_circumference': (80, 120),
            'thigh_circumference': (45, 70),
            'calf_circumference': (30, 45),
            'neck_circumference': (30, 45),
            'shoulder_breadth': (35, 55),
            'height': (140, 200),
            'arm_length': (50, 85),
            'leg_length': (70, 110)
        }
        
        # Anthropometric ratios (relative to height)
        self.height_ratios = {
            'arm_length': (0.30, 0.32),      # 30-32% of height
            'leg_length': (0.44, 0.48),      # 44-48% of height (inseam)
            'shoulder_breadth': (0.23, 0.27), # 23-27% of height
            'chest_circumference': (0.45, 0.65), # 45-65% of height
            'waist_circumference': (0.35, 0.55), # 35-55% of height
            'hip_circumference': (0.50, 0.70),   # 50-70% of height
        }
        
        # EU Clothing size charts (Female)
        self.female_sizes = {
            'XS': {'chest': (76, 82), 'waist': (60, 66), 'hip': (84, 90)},
            'S': {'chest': (83, 87), 'waist': (67, 71), 'hip': (91, 95)},
            'M': {'chest': (88, 92), 'waist': (72, 76), 'hip': (96, 100)},
            'L': {'chest': (93, 97), 'waist': (77, 81), 'hip': (101, 105)},
            'XL': {'chest': (98, 102), 'waist': (82, 86), 'hip': (106, 110)},
            'XXL': {'chest': (103, 107), 'waist': (87, 91), 'hip': (111, 115)}
        }
        
        # Male clothing sizes
        self.male_sizes = {
            'XS': {'chest': (86, 91), 'waist': (71, 76), 'hip': (86, 91)},
            'S': {'chest': (91, 96), 'waist': (76, 81), 'hip': (91, 96)},
            'M': {'chest': (96, 101), 'waist': (81, 86), 'hip': (96, 101)},
            'L': {'chest': (101, 106), 'waist': (86, 91), 'hip': (101, 106)},
            'XL': {'chest': (106, 111), 'waist': (91, 96), 'hip': (106, 111)},
            'XXL': {'chest': (111, 116), 'waist': (96, 101), 'hip': (111, 116)}
        }
        
        self.validation_notes = []
        self.corrections_applied = 0
        
    def validate_and_correct_measurements(self, raw_measurements: Dict, 
                                        front_height_px: Optional[int] = None,
                                        side_height_px: Optional[int] = None,
                                        detected_height_cm: Optional[float] = None) -> Dict:
        """
        Main validation function that fixes all VTON measurement issues
        
        Args:
            raw_measurements: Dict of raw measurements from processing pipeline
            front_height_px: Height in pixels from front view
            side_height_px: Height in pixels from side view  
            detected_height_cm: Detected height in centimeters
            
        Returns:
            Dict with corrected measurements and validation metadata
        """
        self.validation_notes = []
        self.corrections_applied = 0
        
        print(f"\n[VTON VALIDATOR] Starting professional measurement validation...")
        print(f"[VTON VALIDATOR] Raw measurements received: {len(raw_measurements)} items")
        
        # Step 1: Pre-validation filter - detect impossible measurements
        filtered_measurements = self._pre_validation_filter(raw_measurements)
        
        # Step 2: Unify front-side scaling
        unified_scale_factor = self._calculate_unified_scale_factor(
            front_height_px, side_height_px, detected_height_cm
        )
        
        # Step 3: Apply unified scaling to pixel measurements
        scaled_measurements = self._apply_unified_scaling(filtered_measurements, unified_scale_factor)
        
        # Step 4: Proportional validation and correction
        corrected_measurements = self._apply_proportional_correction(scaled_measurements, detected_height_cm)
        
        # Step 5: Gender detection and clothing size classification
        gender = self._detect_gender(corrected_measurements)
        clothing_size = self._classify_clothing_size(corrected_measurements, gender)
        
        # Step 6: Calculate confidence score
        confidence_score = self._calculate_confidence_score(corrected_measurements, raw_measurements)
        
        # Step 7: Format final output
        return self._format_final_output(
            corrected_measurements, clothing_size, confidence_score, gender
        )
    
    def _pre_validation_filter(self, raw_measurements: Dict) -> Dict:
        """Step 1: Detect and filter impossible measurements"""
        print(f"[VTON VALIDATOR] Step 1: Pre-validation filter")
        
        filtered = {}
        impossible_count = 0
        
        for key, value in raw_measurements.items():
            if not isinstance(value, (int, float)) or value <= 0:
                continue
                
            # Check if measurement is within human ranges
            measurement_type = self._identify_measurement_type(key)
            
            if measurement_type in self.human_ranges:
                min_val, max_val = self.human_ranges[measurement_type]
                
                if value < min_val or value > max_val:
                    impossible_count += 1
                    self.validation_notes.append(
                        f"Filtered impossible {measurement_type}: {value:.1f}cm (human range: {min_val}-{max_val}cm)"
                    )
                    # Mark for recalculation instead of including
                    filtered[key] = None
                else:
                    filtered[key] = value
            else:
                # Unknown measurement type, keep as-is
                filtered[key] = value
        
        print(f"[VTON VALIDATOR] Filtered {impossible_count} impossible measurements")
        return filtered
    
    def _calculate_unified_scale_factor(self, front_height_px: Optional[int], 
                                      side_height_px: Optional[int], 
                                      detected_height_cm: Optional[float]) -> float:
        """Step 2: Calculate unified pixel-to-cm conversion factor"""
        print(f"[VTON VALIDATOR] Step 2: Calculating unified scale factor")
        
        if not detected_height_cm:
            detected_height_cm = 170.0  # Default fallback
        
        scale_factors = []
        
        if front_height_px and front_height_px > 0:
            front_scale = detected_height_cm / front_height_px
            scale_factors.append(front_scale)
            print(f"[VTON VALIDATOR] Front scale factor: {front_scale:.6f} cm/px")
        
        if side_height_px and side_height_px > 0:
            side_scale = detected_height_cm / side_height_px
            scale_factors.append(side_scale)
            print(f"[VTON VALIDATOR] Side scale factor: {side_scale:.6f} cm/px")
        
        if scale_factors:
            # Use mean of available scale factors
            unified_scale = sum(scale_factors) / len(scale_factors)
            print(f"[VTON VALIDATOR] Unified scale factor: {unified_scale:.6f} cm/px")
            
            # Check for large discrepancy between front and side
            if len(scale_factors) == 2:
                discrepancy = abs(scale_factors[0] - scale_factors[1]) / unified_scale * 100
                if discrepancy > 20:  # More than 20% difference
                    self.validation_notes.append(
                        f"Large front-side scaling discrepancy: {discrepancy:.1f}%"
                    )
            
            return unified_scale
        else:
            # Fallback: assume reasonable pixel height
            fallback_scale = detected_height_cm / 1000  # Assume 1000px height
            print(f"[VTON VALIDATOR] Using fallback scale factor: {fallback_scale:.6f} cm/px")
            return fallback_scale
    
    def _apply_unified_scaling(self, measurements: Dict, scale_factor: float) -> Dict:
        """Step 3: Apply unified scaling to convert pixels to centimeters"""
        print(f"[VTON VALIDATOR] Step 3: Applying unified scaling")
        
        scaled = {}
        pixel_conversions = 0
        
        for key, value in measurements.items():
            if value is None:
                scaled[key] = None
                continue
                
            # Detect if value is likely in pixels (> 100 for most body measurements)
            if value > 100:
                # Likely pixel measurement, convert to cm
                scaled_value = value * scale_factor
                scaled[key] = scaled_value
                pixel_conversions += 1
                
                self.validation_notes.append(
                    f"Converted {key}: {value:.0f}px → {scaled_value:.1f}cm"
                )
            else:
                # Already in cm or reasonable range
                scaled[key] = value
        
        print(f"[VTON VALIDATOR] Converted {pixel_conversions} pixel measurements to cm")
        return scaled
    
    def _apply_proportional_correction(self, measurements: Dict, height_cm: float) -> Dict:
        """Step 4: Apply proportional validation and correction"""
        print(f"[VTON VALIDATOR] Step 4: Applying proportional correction")
        
        if not height_cm or height_cm < 140 or height_cm > 200:
            height_cm = 170.0  # Safe default
        
        corrected = {}
        
        for key, value in measurements.items():
            measurement_type = self._identify_measurement_type(key)
            
            if value is None:
                # Recalculate from proportional ratios
                corrected[key] = self._estimate_from_height_ratio(measurement_type, height_cm)
                self.corrections_applied += 1
                self.validation_notes.append(
                    f"Estimated {measurement_type}: {corrected[key]:.1f}cm from height ratio"
                )
            elif measurement_type in self.height_ratios:
                # Validate against height ratios
                min_ratio, max_ratio = self.height_ratios[measurement_type]
                min_val = height_cm * min_ratio
                max_val = height_cm * max_ratio
                
                if value < min_val or value > max_val:
                    # Clamp to valid range with ±10% tolerance
                    tolerance = 0.10
                    clamped_value = max(min_val * (1 - tolerance), 
                                      min(value, max_val * (1 + tolerance)))
                    
                    corrected[key] = clamped_value
                    self.corrections_applied += 1
                    self.validation_notes.append(
                        f"Corrected {measurement_type}: {value:.1f}cm → {clamped_value:.1f}cm (proportional to height)"
                    )
                else:
                    corrected[key] = value
            else:
                # No specific ratio, keep as-is
                corrected[key] = value
        
        # Apply inter-measurement relationships
        corrected = self._apply_inter_measurement_validation(corrected)
        
        print(f"[VTON VALIDATOR] Applied {self.corrections_applied} proportional corrections")
        return corrected
    
    def _apply_inter_measurement_validation(self, measurements: Dict) -> Dict:
        """Apply relationships between measurements (waist < chest < hips, etc.)"""
        corrected = measurements.copy()
        
        # Extract key measurements
        chest = self._get_measurement_value(corrected, 'chest_circumference')
        waist = self._get_measurement_value(corrected, 'waist_circumference') 
        hips = self._get_measurement_value(corrected, 'hip_circumference')
        
        if chest and waist and hips:
            # Ensure waist < chest and waist < hips
            if waist >= chest:
                corrected_waist = chest * 0.85  # 85% of chest
                self._update_measurement(corrected, 'waist_circumference', corrected_waist)
                self.validation_notes.append(
                    f"Corrected waist to be < chest: {waist:.1f}cm → {corrected_waist:.1f}cm"
                )
                waist = corrected_waist
                self.corrections_applied += 1
            
            if waist >= hips:
                corrected_waist = hips * 0.90  # 90% of hips
                self._update_measurement(corrected, 'waist_circumference', corrected_waist)
                self.validation_notes.append(
                    f"Corrected waist to be < hips: {waist:.1f}cm → {corrected_waist:.1f}cm"
                )
                self.corrections_applied += 1
        
        return corrected
    
    def _detect_gender(self, measurements: Dict) -> str:
        """Detect gender from measurement patterns"""
        waist = self._get_measurement_value(measurements, 'waist_circumference')
        hips = self._get_measurement_value(measurements, 'hip_circumference')
        
        if waist and hips:
            whr = waist / hips
            # Female WHR typically 0.7-0.8, Male WHR typically 0.85-0.95
            return 'female' if whr < 0.82 else 'male'
        
        return 'female'  # Default assumption for clothing sizing
    
    def _classify_clothing_size(self, measurements: Dict, gender: str) -> str:
        """Classify clothing size using distance-based matching"""
        chest = self._get_measurement_value(measurements, 'chest_circumference')
        waist = self._get_measurement_value(measurements, 'waist_circumference')
        hips = self._get_measurement_value(measurements, 'hip_circumference')
        
        if not (chest and waist and hips):
            return 'Unknown'
        
        size_chart = self.female_sizes if gender == 'female' else self.male_sizes
        
        best_size = 'M'
        min_distance = float('inf')
        
        for size, ranges in size_chart.items():
            # Calculate weighted distance
            chest_dist = self._calculate_range_distance(chest, ranges['chest'])
            waist_dist = self._calculate_range_distance(waist, ranges['waist'])
            hip_dist = self._calculate_range_distance(hips, ranges['hip'])
            
            # Weighted: chest=40%, waist=35%, hips=25%
            total_distance = (chest_dist * 0.4) + (waist_dist * 0.35) + (hip_dist * 0.25)
            
            if total_distance < min_distance:
                min_distance = total_distance
                best_size = size
        
        # Return Unknown if no reasonable fit (distance > 10cm average)
        return best_size if min_distance < 10 else 'Unknown'
    
    def _calculate_confidence_score(self, corrected_measurements: Dict, 
                                  raw_measurements: Dict) -> float:
        """Calculate confidence score based on validation quality"""
        total_measurements = len([v for v in corrected_measurements.values() if v is not None])
        
        if total_measurements == 0:
            return 0.0
        
        # Base confidence
        confidence = 100.0
        
        # Reduce for corrections applied
        correction_penalty = min(self.corrections_applied * 5, 30)  # Max 30% penalty
        confidence -= correction_penalty
        
        # Reduce for measurements within valid ranges
        valid_measurements = 0
        for key, value in corrected_measurements.items():
            if value is not None:
                measurement_type = self._identify_measurement_type(key)
                if measurement_type in self.human_ranges:
                    min_val, max_val = self.human_ranges[measurement_type]
                    if min_val <= value <= max_val:
                        valid_measurements += 1
        
        validity_score = (valid_measurements / total_measurements) * 100
        confidence = (confidence + validity_score) / 2
        
        return max(60.0, min(100.0, confidence))
    
    def _format_final_output(self, measurements: Dict, clothing_size: str, 
                           confidence_score: float, gender: str) -> Dict:
        """Format the final output with all required information"""
        
        # Create final measurements table (only corrected values)
        final_measurements = {}
        for key, value in measurements.items():
            if value is not None:
                measurement_type = self._identify_measurement_type(key)
                final_measurements[measurement_type] = round(value, 1)
        
        return {
            "final_measurements": final_measurements,
            "clothing_size": clothing_size,
            "confidence_score": round(confidence_score, 1),
            "gender_detected": gender,
            "validation_notes": self.validation_notes,
            "corrections_applied": self.corrections_applied,
            "processed_at": datetime.now().isoformat(),
            "validation_method": "vton_professional"
        }
    
    # Helper methods
    def _identify_measurement_type(self, key: str) -> str:
        """Identify measurement type from key name"""
        key_lower = key.lower()
        
        if 'wrist' in key_lower:
            return 'wrist_circumference'
        elif 'forearm' in key_lower:
            return 'forearm_circumference'
        elif 'bicep' in key_lower or 'upper_arm' in key_lower:
            return 'bicep_circumference'
        elif 'chest' in key_lower or 'bust' in key_lower:
            return 'chest_circumference'
        elif 'waist' in key_lower:
            return 'waist_circumference'
        elif 'hip' in key_lower:
            return 'hip_circumference'
        elif 'thigh' in key_lower:
            return 'thigh_circumference'
        elif 'calf' in key_lower:
            return 'calf_circumference'
        elif 'neck' in key_lower:
            return 'neck_circumference'
        elif 'shoulder' in key_lower:
            return 'shoulder_breadth'
        elif 'height' in key_lower:
            return 'height'
        elif 'arm' in key_lower and 'length' in key_lower:
            return 'arm_length'
        elif 'leg' in key_lower and ('length' in key_lower or 'inseam' in key_lower):
            return 'leg_length'
        else:
            return key.lower()
    
    def _estimate_from_height_ratio(self, measurement_type: str, height_cm: float) -> float:
        """Estimate measurement from height using anthropometric ratios"""
        if measurement_type in self.height_ratios:
            min_ratio, max_ratio = self.height_ratios[measurement_type]
            avg_ratio = (min_ratio + max_ratio) / 2
            return height_cm * avg_ratio
        
        # Fallback estimates
        estimates = {
            'wrist_circumference': 16.0,
            'forearm_circumference': 26.0,
            'bicep_circumference': 30.0,
            'thigh_circumference': 55.0,
            'calf_circumference': 37.0,
            'neck_circumference': 36.0
        }
        
        return estimates.get(measurement_type, height_cm * 0.2)
    
    def _get_measurement_value(self, measurements: Dict, measurement_type: str) -> Optional[float]:
        """Get measurement value by type"""
        for key, value in measurements.items():
            if self._identify_measurement_type(key) == measurement_type:
                return value
        return None
    
    def _update_measurement(self, measurements: Dict, measurement_type: str, new_value: float):
        """Update measurement value by type"""
        for key in measurements.keys():
            if self._identify_measurement_type(key) == measurement_type:
                measurements[key] = new_value
                break
    
    def _calculate_range_distance(self, value: float, range_tuple: Tuple[float, float]) -> float:
        """Calculate distance from value to range"""
        min_val, max_val = range_tuple
        if min_val <= value <= max_val:
            return 0.0
        elif value < min_val:
            return min_val - value
        else:
            return value - max_val

# Global validator instance
vton_validator = VTONMeasurementValidator()

def validate_vton_measurements(raw_measurements: Dict, 
                             front_height_px: Optional[int] = None,
                             side_height_px: Optional[int] = None, 
                             detected_height_cm: Optional[float] = None) -> Dict:
    """Convenience function for VTON measurement validation"""
    return vton_validator.validate_and_correct_measurements(
        raw_measurements, front_height_px, side_height_px, detected_height_cm
    )
