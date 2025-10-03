# workers/measurement_worker.py

import os
import sys
import shutil
import threading
import time
from datetime import datetime
import traceback
import json
import tempfile


from image_quality_detector import ImageQualityDetector

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add measurement modules to path
measurement_modules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'measurement_modules')
if os.path.exists(measurement_modules_path):
    sys.path.insert(0, measurement_modules_path)
    print(f"[MEASUREMENT WORKER] Measurement modules path added: {measurement_modules_path}")
else:
    print(f"[MEASUREMENT WORKER] WARNING: Measurement modules not found at: {measurement_modules_path}")

from queue_manager import queue_manager
from firebase_config import get_access_token
import requests

FIREBASE_PROJECT_ID = "fitmatch-1"

class ProfessionalVTONMeasurementCorrector:
    """
    Professional VTON measurement corrector with robust error handling.
    NO XS sizing - only S, M, L, XL, XXL as requested.
    Based on professional inseam sizing standards.
    """
    
    def __init__(self):
        # Professional clothing sizes (NO XS) - only S, M, L, XL, XXL
        self.clothing_sizes = {
            'S': {'chest': (78, 85), 'waist': (62, 69), 'hips': (84, 91)},
            'M': {'chest': (86, 93), 'waist': (70, 77), 'hips': (92, 99)},
            'L': {'chest': (94, 101), 'waist': (78, 85), 'hips': (100, 107)},
            'XL': {'chest': (102, 109), 'waist': (86, 93), 'hips': (108, 115)},
            'XXL': {'chest': (110, 120), 'waist': (94, 102), 'hips': (116, 125)}
        }
        
        # Professional inseam sizing based on industry standards
        self.inseam_sizes = {
            'S': {'inseam_range': (66, 71), 'height_range': (150, 162)},    # 26-28" inseam
            'M': {'inseam_range': (72, 76), 'height_range': (163, 170)},    # 28-30" inseam  
            'L': {'inseam_range': (77, 81), 'height_range': (171, 178)},    # 30-32" inseam
            'XL': {'inseam_range': (82, 86), 'height_range': (179, 185)},   # 32-34" inseam
            'XXL': {'inseam_range': (87, 91), 'height_range': (186, 195)}   # 34-36" inseam
        }
        
        # Conservative limits to prevent over-inflation
        self.conservative_limits = {
            'chest_max_inflation': 1.0,    # Max +1cm from detected
            'hip_max_reduction': 15.0,     # Max -15cm from over-inflated values
            'waist_tolerance': 3.0         # Max ±3cm from detected
        }
        
        self.corrections_applied = []
        self.reliability_score = 100
    
    def correct_measurements_professionally(self, raw_measurements, manual_height=None, is_manual_height=False):
        """
        Professional measurement correction with robust error handling
        """
        self.corrections_applied = []
        self.reliability_score = 100
        
        print(f"\n[PROFESSIONAL VTON CORRECTION] Starting professional measurement correction...")
        print(f"[PROFESSIONAL VTON CORRECTION] Using industry standards (S/M/L/XL/XXL only)")
        
        try:
            # Extract measurements safely
            extracted = self._extract_measurements_safely(raw_measurements)
            
            # Handle height (exact manual height if provided)
            corrected_height = manual_height if is_manual_height and manual_height else extracted.get('height', 170)
            
            # Apply professional corrections with error handling
            corrected_measurements = self._apply_professional_corrections_safely(extracted, corrected_height)
            
            # Get professional legwear sizing
            legwear_info = self._classify_professional_legwear_sizing(
                corrected_measurements['inseam'], corrected_height
            )
            
            # Classify clothing size professionally
            clothing_size = self._classify_professional_clothing_size(corrected_measurements)
            
            return self._format_professional_output(corrected_measurements, clothing_size, legwear_info)
            
        except Exception as e:
            print(f"[PROFESSIONAL CORRECTION] Error in correction: {str(e)}")
            # Return fallback measurements
            return self._create_fallback_measurements(manual_height or 170)
    
    def _extract_measurements_safely(self, raw_measurements):
        """Extract measurements with safe handling of None values"""
        mappings = {
            'height': ['Height', 'height', 'detected_height'],
            'chest': ['Chest Circumference', 'chest_circumference', 'chest_circ', 'chest'],
            'waist': ['Waist Circumference', 'waist_circumference', 'waist_circ', 'waist'],
            'hips': ['Hip Circumference', 'hips_circumference', 'hip_circ', 'hips'],
            'arm_length': ['Right Arm Length', 'arm_length', 'arm_length_cm'],
            'leg_length': ['Inside Leg Height', 'leg_length', 'inseam'],
        }
        
        extracted = {}
        for measurement_type, possible_keys in mappings.items():
            value = None
            for key in possible_keys:
                if key in raw_measurements:
                    raw_value = raw_measurements[key]
                    if isinstance(raw_value, dict):
                        value = raw_value.get('value', 0)
                    elif isinstance(raw_value, (int, float)) and raw_value > 0:
                        value = float(raw_value)
                    break
            # Always set a value (never None to prevent format errors)
            extracted[measurement_type] = value if value and value > 0 else 0.0
        
        print(f"[PROFESSIONAL EXTRACTION] Safely extracted measurements:")
        for key, value in extracted.items():
            print(f"  {key}: {value:.1f} cm")
        
        return extracted
    
    def _apply_professional_corrections_safely(self, extracted, height):
        """Apply professional corrections with safe handling"""
        print(f"\n[PROFESSIONAL CORRECTION] Applying safe professional corrections for {height:.1f}cm...")
        
        corrected = {}
        corrected['height'] = height
        
        # CHEST - Ultra conservative with safe handling
        raw_chest = extracted.get('chest', 0)
        if raw_chest > 75:  # Valid chest measurement
            max_professional_chest = min(raw_chest + self.conservative_limits['chest_max_inflation'], height * 0.52)
            corrected['chest'] = max_professional_chest
            if abs(max_professional_chest - raw_chest) > 0.5:
                self.corrections_applied.append(f"Chest adjusted: {raw_chest:.1f}cm → {max_professional_chest:.1f}cm")
                self.reliability_score -= 5
        else:
            corrected['chest'] = height * 0.50  # Conservative default
            self.corrections_applied.append(f"Chest estimated: {corrected['chest']:.1f}cm (50% of height)")
        
        print(f"[PROFESSIONAL CORRECTION] ✓ Chest: {corrected['chest']:.1f}cm")
        
        # WAIST - Safe handling with defaults
        raw_waist = extracted.get('waist', 0)
        if raw_waist > 50:  # Valid waist measurement
            corrected['waist'] = raw_waist
        else:
            corrected['waist'] = height * 0.42  # Conservative default
            self.corrections_applied.append(f"Waist estimated: {corrected['waist']:.1f}cm (42% of height)")
        
        print(f"[PROFESSIONAL CORRECTION] ✓ Waist: {corrected['waist']:.1f}cm")
        
        # HIPS - MAJOR CONSERVATIVE CORRECTION with safe handling
        raw_hips = extracted.get('hips', 0)
        if raw_hips > 70:  # Valid hip measurement
            # Ultra-conservative hip correction - prevent major over-inflation
            max_professional_hips = min(
                corrected['chest'] * 1.08,  # Max 108% of chest
                corrected['waist'] * 1.12,  # Max 112% of waist
                raw_hips - self.conservative_limits['hip_max_reduction'] if raw_hips > 85 else raw_hips
            )
            corrected['hips'] = max_professional_hips
            if abs(max_professional_hips - raw_hips) > 1.0:
                self.corrections_applied.append(f"Hips corrected: {raw_hips:.1f}cm → {max_professional_hips:.1f}cm (prevent over-inflation)")
                self.reliability_score -= 10
        else:
            corrected['hips'] = corrected['chest'] * 1.05  # Conservative default
            self.corrections_applied.append(f"Hips estimated: {corrected['hips']:.1f}cm (105% of chest)")
        
        print(f"[PROFESSIONAL CORRECTION] ✓ Hips: {corrected['hips']:.1f}cm")
        
        # ARM LENGTH - Professional correction with safe handling
        raw_arm = extracted.get('arm_length', 0)
        professional_arm_min = height * 0.31
        professional_arm_max = height * 0.35
        
        if raw_arm > 0 and professional_arm_min <= raw_arm <= professional_arm_max:
            corrected['arm_length'] = raw_arm
        elif raw_arm > professional_arm_max:
            corrected['arm_length'] = professional_arm_max
            self.corrections_applied.append(f"Arm corrected: {raw_arm:.1f}cm → {corrected['arm_length']:.1f}cm (too long)")
            self.reliability_score -= 5
        else:
            corrected['arm_length'] = height * 0.33  # Professional default
            if raw_arm > 0:
                self.corrections_applied.append(f"Arm corrected: {raw_arm:.1f}cm → {corrected['arm_length']:.1f}cm")
            else:
                self.corrections_applied.append(f"Arm estimated: {corrected['arm_length']:.1f}cm (33% of height)")
        
        print(f"[PROFESSIONAL CORRECTION] ✓ Arm Length: {corrected['arm_length']:.1f}cm")
        
        # INSEAM - Professional conversion with safe handling
        raw_leg = extracted.get('leg_length', 0)
        corrected['inseam'] = self._convert_to_professional_inseam_safely(raw_leg, height)
        
        print(f"[PROFESSIONAL CORRECTION] ✓ Inseam: {corrected['inseam']:.1f}cm")
        
        return corrected
    
    def _convert_to_professional_inseam_safely(self, raw_leg, height):
        """Convert leg measurement to professional inseam with safe handling"""
        print(f"\n[SAFE INSEAM CONVERSION] Converting leg measurement...")
        
        if not raw_leg or raw_leg <= 0:
            # Estimate based on height
            if height <= 158:      # Up to 5'2"
                professional_inseam = 70.0  # Short inseam
            elif height <= 165:    # 5'3" to 5'5"
                professional_inseam = 73.0  # Regular inseam
            elif height <= 175:    # 5'6" to 5'9"
                professional_inseam = 76.0  # Long inseam
            else:
                professional_inseam = 79.0  # Extra long inseam
            
            self.corrections_applied.append(f"Inseam estimated: {professional_inseam:.1f}cm based on {height:.1f}cm height")
            print(f"[SAFE INSEAM CONVERSION] ✓ Estimated professional inseam: {professional_inseam:.1f}cm")
            return professional_inseam
        
        print(f"[SAFE INSEAM CONVERSION] Raw leg measurement: {raw_leg:.1f}cm")
        
        # Determine measurement type safely
        expected_inseam_max = height * 0.50  # 50% maximum for inseam
        expected_total_leg = height * 0.65   # 65% for total leg
        
        if raw_leg <= expected_inseam_max:
            # Already inseam measurement
            professional_inseam = max(raw_leg, height * 0.42)  # Minimum 42% of height
            if professional_inseam != raw_leg:
                self.corrections_applied.append(f"Inseam adjusted: {raw_leg:.1f}cm → {professional_inseam:.1f}cm")
        elif raw_leg <= expected_total_leg:
            # Convert total leg to inseam (80% conversion based on your friend's data: 92cm → ~73.6cm)
            professional_inseam = raw_leg * 0.80
            self.corrections_applied.append(f"Converted total leg {raw_leg:.1f}cm to inseam {professional_inseam:.1f}cm (80% professional ratio)")
            print(f"[SAFE INSEAM CONVERSION] ✓ Converted total leg to inseam using 80% ratio")
        else:
            # Impossible measurement, use height-based estimate
            professional_inseam = height * 0.47
            self.corrections_applied.append(f"Impossible leg measurement {raw_leg:.1f}cm, estimated inseam: {professional_inseam:.1f}cm")
        
        # Final validation
        min_realistic = height * 0.42
        max_realistic = height * 0.52
        professional_inseam = max(min_realistic, min(professional_inseam, max_realistic))
        
        return professional_inseam
    
    def _classify_professional_legwear_sizing(self, inseam, height):
        """Classify legwear size using professional inseam standards"""
        print(f"\n[PROFESSIONAL LEGWEAR] Classification...")
        print(f"  Inseam: {inseam:.1f}cm")
        print(f"  Height: {height:.1f}cm")
        
        # Find best fitting legwear size based on inseam
        best_size = 'M'  # Default
        min_distance = float('inf')
        
        for size, data in self.inseam_sizes.items():
            inseam_min, inseam_max = data['inseam_range']
            
            if inseam_min <= inseam <= inseam_max:
                best_size = size
                min_distance = 0
                break
            elif inseam < inseam_min:
                distance = inseam_min - inseam
            else:
                distance = inseam - inseam_max
            
            if distance < min_distance:
                min_distance = distance
                best_size = size
        
        # Determine legwear type
        legwear_type = "jeans" if inseam >= 73 else "pants"
        fit_quality = 'Perfect' if min_distance == 0 else 'Good' if min_distance < 3 else 'Acceptable'
        
        print(f"[PROFESSIONAL LEGWEAR] ✓ Size: {best_size}")
        print(f"[PROFESSIONAL LEGWEAR] ✓ Type: {legwear_type}")
        print(f"[PROFESSIONAL LEGWEAR] ✓ Fit: {fit_quality}")
        
        return {
            'size': best_size,
            'type': legwear_type,
            'inseam_range': self.inseam_sizes[best_size]['inseam_range'],
            'fit_quality': fit_quality
        }
    
    def _classify_professional_clothing_size(self, measurements):
        """Classify clothing size professionally (S/M/L/XL/XXL only)"""
        chest = measurements.get('chest', 0)
        waist = measurements.get('waist', 0)
        hips = measurements.get('hips', 0)
        
        print(f"\n[PROFESSIONAL CLOTHING SIZE] Classification:")
        print(f"  Chest: {chest:.1f}cm, Waist: {waist:.1f}cm, Hips: {hips:.1f}cm")
        
        best_size = 'M'  # Default
        min_distance = float('inf')
        
        for size, ranges in self.clothing_sizes.items():
            # Calculate weighted distance
            chest_dist = self._calculate_range_distance(chest, ranges['chest'])
            waist_dist = self._calculate_range_distance(waist, ranges['waist'])
            hips_dist = self._calculate_range_distance(hips, ranges['hips'])
            
            # Professional weighting: chest=60%, waist=25%, hips=15%
            total_distance = (chest_dist * 0.60) + (waist_dist * 0.25) + (hips_dist * 0.15)
            
            print(f"    {size}: distance = {total_distance:.1f}")
            
            if total_distance < min_distance:
                min_distance = total_distance
                best_size = size
        
        print(f"[PROFESSIONAL CLOTHING SIZE] ✓ Size: {best_size}")
        return best_size
    
    def _calculate_range_distance(self, value, range_tuple):
        """Calculate distance from value to range"""
        min_val, max_val = range_tuple
        if min_val <= value <= max_val:
            return 0.0
        elif value < min_val:
            return min_val - value
        else:
            return value - max_val
    
    def _create_fallback_measurements(self, height):
        """Create fallback measurements when correction fails"""
        return {
            "Professional_Height": f"{height:.1f} cm",
            "Professional_Chest": f"{height * 0.50:.1f} cm",
            "Professional_Waist": f"{height * 0.42:.1f} cm", 
            "Professional_Hips": f"{height * 0.52:.1f} cm",
            "Professional_Arm_Length": f"{height * 0.33:.1f} cm",
            "Professional_Inseam": f"{height * 0.47:.1f} cm",
            "Clothing_Size": "M",
            "Legwear_Size": "M",
            "Legwear_Type": "pants",
            "Legwear_Fit_Quality": "Estimated",
            "Reliability_Score": 60,
            "Corrections_Applied": ["Fallback measurements applied due to processing error"],
            "VTON_Ready": True,
            "Professional_Standards": "Fallback_Mode"
        }
    
    def _format_professional_output(self, measurements, clothing_size, legwear_info):
        """Format professional output for VTON applications"""
        return {
            "Professional_Height": f"{measurements['height']:.1f} cm",
            "Professional_Chest": f"{measurements['chest']:.1f} cm",
            "Professional_Waist": f"{measurements['waist']:.1f} cm", 
            "Professional_Hips": f"{measurements['hips']:.1f} cm",
            "Professional_Arm_Length": f"{measurements['arm_length']:.1f} cm",
            "Professional_Inseam": f"{measurements['inseam']:.1f} cm",
            "Clothing_Size": clothing_size,
            "Legwear_Size": legwear_info['size'],
            "Legwear_Type": legwear_info['type'],
            "Legwear_Fit_Quality": legwear_info['fit_quality'],
            "Inseam_Size_Range": f"{legwear_info['inseam_range'][0]}-{legwear_info['inseam_range'][1]} cm",
            "Reliability_Score": self.reliability_score,
            "Corrections_Applied": self.corrections_applied,
            "VTON_Ready": True,
            "Professional_Standards": "S_M_L_XL_XXL_Only"
        }

def process_measurement_job(job_data):
    """Process measurement job with robust error handling and professional correction"""
    job_id = job_data['job_id']
    user_id = job_data['user_id']
    
    print(f"\n{'='*80}")
    print(f"[MEASUREMENT PROCESSING] Starting Job: {job_id}")
    print(f"[MEASUREMENT PROCESSING] User: {user_id}")
    print(f"[MEASUREMENT PROCESSING] Professional Standards: S/M/L/XL/XXL (NO XS)")
    print(f"[MEASUREMENT PROCESSING] Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*80}")
    
    working_dir = None
    original_dir = os.getcwd()
    
    try:
        # Update status to processing
        update_job_status(job_id, 'processing')
        print(f"[STATUS] Updated to: PROCESSING")
        
        # Get image paths
        front_image = job_data['front_image']
        side_image = job_data['side_image']
        manual_height = job_data.get('manual_height', 170)
        use_automatic_height = job_data.get('use_automatic_height', True)
        
        print(f"\n[IMAGE PATHS]")
        print(f"  Front: {front_image}")
        print(f"  Side: {side_image}")
        print(f"  Manual Height: {manual_height} cm")
        print(f"  Use Automatic Height: {use_automatic_height}")
        
        # Check if images exist
        if not os.path.exists(front_image) or not os.path.exists(side_image):
            raise Exception(f"Image files not found")
        
        
        # ADD QUALITY CHECK HERE - BEFORE working directory creation
        print(f"\n[QUALITY CHECK] Analyzing image quality...")
        try:
            quality_detector = ImageQualityDetector()
            quality_results = quality_detector.detect_all_issues(front_image, side_image)
            
            print(f"[QUALITY CHECK] Quality analysis completed")
            if quality_results['has_issues']:
                print(f"[QUALITY CHECK] ⚠️  Primary issue: {quality_results['issue_type']}")
                print(f"[QUALITY CHECK] Description: {quality_results['description']}")
            else:
                print(f"[QUALITY CHECK] ✓ Images are excellent quality")
                
        except Exception as e:
            print(f"[QUALITY CHECK] Error during quality analysis: {str(e)}")
            quality_results = {
                'has_issues': False,
                'issue_type': None,
                'description': f"Quality check failed: {str(e)}",
                'severity': 'none',
                'affected_images': []
            }
        
        # Create working directory
        working_dir = tempfile.mkdtemp(prefix=f"measurement_{job_id}_")
        print(f"\n[SETUP] Creating working directory: {working_dir}")
        
        os.makedirs(os.path.join(working_dir, 'distance'), exist_ok=True)
        os.makedirs(os.path.join(working_dir, 'images'), exist_ok=True)
        
        # Copy images with proper names
        print(f"[SETUP] Copying images to working directory...")
        shutil.copy(front_image, os.path.join(working_dir, 'distance', 'image 11_no_bg.jpg'))
        shutil.copy(side_image, os.path.join(working_dir, 'distance', 'image 12_no_bg.jpg'))
        
        # Change to working directory
        os.chdir(working_dir)
        print(f"[SETUP] Changed to working directory")
        
        # Create comprehensive photos_height.py with all required variables
        photos_height_content = f"""
# Image paths
front_input_image = 'distance/image 11_no_bg.jpg'
side_input_image = 'distance/image 12_no_bg.jpg'

# Configuration
USE_AUTOMATIC_HEIGHT = {use_automatic_height}
MANUAL_HEIGHT = {manual_height}
height = {manual_height if not use_automatic_height else manual_height}

# Additional variables that modules might need
input_front = front_input_image
input_side = side_input_image
"""
        with open('photos_height.py', 'w') as f:
            f.write(photos_height_content)
        print(f"[SETUP] Created comprehensive photos_height.py")
        
        # Add working directory to path
        sys.path.insert(0, working_dir)
        
        try:
            print(f"\n[MEASUREMENT MODULES] Starting robust measurement pipeline...")
            
            # Import measurement modules safely
            try:
                from measurement_config import MeasurementConfig
                from height_measurement import HeightMeasurement
                from measurement_validator import MeasurementValidator
                from measurement_calculator import MeasurementCalculator
                from measurement_confidence import MeasurementConfidence
                print(f"[MODULES] ✓ All modules imported successfully")
            except ImportError as e:
                print(f"[MODULES] ✗ Import error: {str(e)}")
            
            # Handle height measurement
            print(f"\n[HEIGHT DETECTION] Starting height measurement...")
            if use_automatic_height:
                try:
                    height_measurer = HeightMeasurement('distance/image 11_no_bg.jpg', 'distance/image 12_no_bg.jpg')
                    detected_height = height_measurer.measure_height()
                    if not (90 <= detected_height <= 220):
                        detected_height = manual_height
                        print(f"[HEIGHT DETECTION] Invalid height, using manual: {detected_height} cm")
                    else:
                        print(f"[HEIGHT DETECTION] ✓ Detected height: {detected_height} cm")
                except Exception as e:
                    print(f"[HEIGHT DETECTION] Error: {str(e)}")
                    detected_height = manual_height
                    print(f"[HEIGHT DETECTION] Using manual height fallback: {detected_height} cm")
            else:
                detected_height = manual_height
                print(f"[HEIGHT DETECTION] Using manual height: {detected_height} cm")
            
            # Update photos_height.py with detected height and all variables
            comprehensive_config = f"""
# Image paths
front_input_image = 'distance/image 11_no_bg.jpg'
side_input_image = 'distance/image 12_no_bg.jpg'

# Height configuration
height = {detected_height}
USE_AUTOMATIC_HEIGHT = {use_automatic_height}
MANUAL_HEIGHT = {manual_height}

# Additional variables for modules
input_front = front_input_image
input_side = side_input_image
detected_height = {detected_height}

# Default measurements to prevent undefined errors
current_distance_up_side = 100
current_distance_side = 200
"""
            with open('photos_height.py', 'w') as f:
                f.write(comprehensive_config)
            print(f"[SETUP] ✓ Updated comprehensive configuration")
            
            # Run measurement pipeline with error handling
            modules_to_run = [
                ('medipie_cooordinates.py', 'MediaPipe Pose Detection'),
                ('decrease_contrast.py', 'Contrast Adjustment'), 
                ('remove_backround.py', 'Background Removal'),
                ('add_silhouette.py', 'Silhouette Generation'),
                ('body_segments.py', 'Body Segment Detection'),
                ('get_height.py', 'Final Measurements Calculation')
            ]
            
            exec_namespace = {
                '__name__': '__main__',
                'front_input_image': 'distance/image 11_no_bg.jpg',
                'side_input_image': 'distance/image 12_no_bg.jpg',
                'height': detected_height,
                'current_distance_up_side': 100,
                'current_distance_side': 200
            }
            
            successful_modules = 0
            for module_file, description in modules_to_run:
                print(f"\n[PROCESSING] {description}...")
                module_path = os.path.join(measurement_modules_path, module_file)
                
                if os.path.exists(module_path):
                    try:
                        with open(module_path, 'r', encoding='utf-8') as f:
                            module_code = f.read()
                        compiled_code = compile(module_code, module_file, 'exec')
                        exec(compiled_code, exec_namespace)
                        print(f"[PROCESSING] ✓ {description} completed")
                        successful_modules += 1
                    except Exception as e:
                        print(f"[PROCESSING] ✗ Error in {description}: {str(e)}")
                        continue
                else:
                    print(f"[PROCESSING] ✗ Module not found: {module_file}")
            
            print(f"\n[PROCESSING] Successfully ran {successful_modules}/{len(modules_to_run)} modules")
            
            # Extract measurements safely
            measurements = exec_namespace.get('measurements_dict', {})
            if not measurements:
                print(f"[MEASUREMENTS] Extracting from individual variables...")
                measurement_vars = [
                    'height', 'waist_circ', 'hip_circ', 'chest_circ', 
                    'inside_leg_height', 'leg_length', 'shoulder_breadth'
                ]
                for var in measurement_vars:
                    if var in exec_namespace and isinstance(exec_namespace[var], (int, float)):
                        measurements[var] = exec_namespace[var]
                        print(f"  Found {var}: {exec_namespace[var]}")
                
                if not measurements:
                    measurements = {'Height': detected_height}
            
            print(f"[MEASUREMENTS] Extracted {len(measurements)} measurements")
            
            # Validate measurements safely
            try:
                validator = MeasurementValidator(detected_height)
                corrected_measurements = validator.validate_all_measurements(measurements)
                print(f"[VALIDATION] ✓ Measurements validated")
            except Exception as e:
                print(f"[VALIDATION] Error: {str(e)}")
                corrected_measurements = measurements
            
            # Calculate confidence safely
            try:
                confidence_analyzer = MeasurementConfidence(detected_height)
                confidence_scores = confidence_analyzer.calculate_confidence_score(corrected_measurements)
                overall_confidence = confidence_analyzer.get_overall_confidence(confidence_scores)
                print(f"[CONFIDENCE] ✓ Overall confidence: {overall_confidence:.1f}%")
            except Exception as e:
                print(f"[CONFIDENCE] Error: {str(e)}")
                confidence_scores = {}
                overall_confidence = 75.0
            
            # APPLY PROFESSIONAL VTON CORRECTION
            print(f"\n[PROFESSIONAL VTON CORRECTION] Applying professional corrections...")
            try:
                professional_corrector = ProfessionalVTONMeasurementCorrector()
                
                correction_input = {
                    **corrected_measurements,
                    **{k: v for k, v in exec_namespace.items() if isinstance(v, (int, float)) and k not in ['x', 'y', 'alpha', 'beta']},
                    'height': detected_height
                }
                
                is_manual_height = not use_automatic_height
                professional_results = professional_corrector.correct_measurements_professionally(
                    correction_input,
                    manual_height if is_manual_height else detected_height,
                    is_manual_height
                )
                
                print(f"[PROFESSIONAL VTON CORRECTION] ✓ Professional Results:")
                print(f"  Height: {professional_results['Professional_Height']}")
                print(f"  Chest: {professional_results['Professional_Chest']}")
                print(f"  Waist: {professional_results['Professional_Waist']}")
                print(f"  Hips: {professional_results['Professional_Hips']}")
                print(f"  Arms: {professional_results['Professional_Arm_Length']}")
                print(f"  Inseam: {professional_results['Professional_Inseam']}")
                print(f"  Clothing Size: {professional_results['Clothing_Size']} (NO XS policy)")
                print(f"  Legwear Size: {professional_results['Legwear_Size']}")
                print(f"  Legwear Type: {professional_results['Legwear_Type']}")
                print(f"  Fit Quality: {professional_results['Legwear_Fit_Quality']}")
                print(f"  Reliability: {professional_results['Reliability_Score']}%")
                
                if professional_results['Corrections_Applied']:
                    print(f"\n[PROFESSIONAL CORRECTION NOTES]")
                    for note in professional_results['Corrections_Applied'][:5]:  # Show first 5
                        print(f"  • {note}")
                
                # Update measurements with professional results
                corrected_measurements.update({
                    'Professional_VTON_Results': professional_results,
                    'Final_Height': professional_results['Professional_Height'],
                    'Final_Chest': professional_results['Professional_Chest'],
                    'Final_Waist': professional_results['Professional_Waist'],
                    'Final_Hips': professional_results['Professional_Hips'],
                    'Final_Arms': professional_results['Professional_Arm_Length'],
                    'Final_Inseam': professional_results['Professional_Inseam'],
                    'Final_Clothing_Size': professional_results['Clothing_Size'],
                    'Final_Legwear_Size': professional_results['Legwear_Size'],
                    'Final_Legwear_Type': professional_results['Legwear_Type'],
                    'Professional_Reliability': professional_results['Reliability_Score'],
                    'VTON_Ready': professional_results['VTON_Ready']
                })
                
            except Exception as e:
                print(f"[PROFESSIONAL VTON CORRECTION] ✗ Error: {str(e)}")
                print(f"[PROFESSIONAL VTON CORRECTION] Applying fallback corrections...")
                
                # Apply simple fallback corrections
                fallback_results = {
                    'Final_Height': f"{detected_height:.1f} cm",
                    'Final_Chest': f"{detected_height * 0.50:.1f} cm",
                    'Final_Waist': f"{detected_height * 0.42:.1f} cm",
                    'Final_Hips': f"{detected_height * 0.52:.1f} cm",
                    'Final_Arms': f"{detected_height * 0.33:.1f} cm",
                    'Final_Inseam': f"{detected_height * 0.47:.1f} cm",
                    'Final_Clothing_Size': 'M',
                    'Final_Legwear_Size': 'M',
                    'Final_Legwear_Type': 'pants',
                    'Professional_Reliability': 70,
                    'VTON_Ready': True
                }
                corrected_measurements.update(fallback_results)
            
            # Save processed images
            job_dir = job_data.get('job_dir', os.path.dirname(front_image))
            os.makedirs(job_dir, exist_ok=True)
            
            print(f"\n[IMAGES] Saving processed images...")
            processed_images = {}
            image_files = [
                ('images/medipipe_output.jpg', 'pose_detection_front'),
                ('images/body_segments.jpg', 'body_segments_front'),
                ('images/get_height.jpg', 'height_measurement_front'),
                ('images/add_silhouette.jpg', 'silhouette_front')
            ]
            
            saved_count = 0
            for src, name in image_files:
                src_path = os.path.join(working_dir, src)
                if os.path.exists(src_path):
                    dest_path = os.path.join(job_dir, f'{name}.jpg')
                    try:
                        shutil.copy(src_path, dest_path)
                        processed_images[name] = f'measurement_data/{user_id}/{job_id}/{name}.jpg'
                        saved_count += 1
                        print(f"  ✓ Saved: {name}.jpg")
                    except Exception as e:
                        print(f"  ✗ Failed to save {name}.jpg: {e}")
            
            print(f"[IMAGES] Saved {saved_count} processed images")
            
            # Prepare results
            result_data = {
                'measurements': corrected_measurements,
                'confidence_scores': confidence_scores,
                'overall_confidence': overall_confidence,
                'height_detection_method': 'automatic' if use_automatic_height else 'manual',
                'detected_height': detected_height,
                'processed_images': processed_images,
                'image_quality_issues': quality_results.get('issues', []),
                'quality_analysis': quality_results
            }
            
            update_job_status(job_id, 'completed', result_data)
            
            print(f"\n{'='*80}")
            print(f"[SUCCESS] Job {job_id} completed with professional standards!")
            print(f"[SUCCESS] Height: {detected_height:.1f} cm")
            print(f"[SUCCESS] Standards: Professional sizing (S/M/L/XL/XXL)")
            if 'Final_Clothing_Size' in corrected_measurements:
                print(f"[SUCCESS] Clothing size: {corrected_measurements['Final_Clothing_Size']}")
            if 'Final_Legwear_Size' in corrected_measurements:
                print(f"[SUCCESS] Legwear size: {corrected_measurements['Final_Legwear_Size']}")
            if 'Final_Legwear_Type' in corrected_measurements:
                print(f"[SUCCESS] Legwear type: {corrected_measurements['Final_Legwear_Type']}")
            if 'Professional_Reliability' in corrected_measurements:
                print(f"[SUCCESS] Reliability: {corrected_measurements['Professional_Reliability']}%")
            print(f"{'='*80}\n")
            
        finally:
            os.chdir(original_dir)
            if working_dir in sys.path:
                sys.path.remove(working_dir)
            
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        update_job_status(job_id, 'failed', {'error': str(e)})
        try:
            os.chdir(original_dir)
        except:
            pass
    
    finally:
        if working_dir and os.path.exists(working_dir):
            try:
                shutil.rmtree(working_dir, ignore_errors=True)
            except Exception as e:
                print(f"[CLEANUP] Warning: {e}")

def update_job_status(job_id, status, result_data=None):
    """Update job status in Firestore with error handling"""
    try:
        token = get_access_token()
        if not token:
            print("[FIRESTORE] WARNING: No Firebase token available")
            return False
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        job_data = {
            'fields': {
                'status': {'stringValue': status},
                'updated_at': {'stringValue': datetime.now().isoformat()}
            }
        }
        
        if result_data:
            if status == 'completed':
                job_data['fields']['completed_at'] = {'stringValue': datetime.now().isoformat()}
                
                # Store measurements as JSON string with safe handling
                if 'measurements' in result_data:
                    # Clean measurements before storing (remove non-serializable objects)
                    clean_measurements = {}
                    for k, v in result_data['measurements'].items():
                        if isinstance(v, (str, int, float, bool, list)):
                            clean_measurements[k] = v
                        elif isinstance(v, dict):
                            clean_measurements[k] = v
                        else:
                            clean_measurements[k] = str(v)
                    
                    job_data['fields']['measurements'] = {'stringValue': json.dumps(clean_measurements)}
                
                # ADD THESE LINES for quality issues:
                if 'image_quality_issues' in result_data:
                    job_data['fields']['image_quality_issues'] = {
                        'stringValue': json.dumps(result_data['image_quality_issues'])
                    }
                
                # Store other data safely
                if 'overall_confidence' in result_data:
                    job_data['fields']['overall_confidence'] = {'doubleValue': float(result_data['overall_confidence'])}
                
                if 'detected_height' in result_data:
                    job_data['fields']['detected_height'] = {'doubleValue': float(result_data['detected_height'])}
                
                if 'height_detection_method' in result_data:
                    job_data['fields']['height_detection_method'] = {'stringValue': result_data['height_detection_method']}
                
                if 'processed_images' in result_data:
                    job_data['fields']['processed_images'] = {'stringValue': json.dumps(result_data['processed_images'])}
                
                job_data['fields']['test_mode'] = {'booleanValue': True}
                    
            elif status == 'failed':
                job_data['fields']['failed_at'] = {'stringValue': datetime.now().isoformat()}
                if 'error' in result_data:
                    job_data['fields']['error'] = {'stringValue': str(result_data['error'])}
        
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/measurement_jobs/{job_id}"
        response = requests.patch(url, json=job_data, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"[FIRESTORE] ✓ Job status updated successfully")
            return True
        else:
            print(f"[FIRESTORE] ✗ Failed to update status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[FIRESTORE] ✗ Error: {e}")
        return False

def measurement_worker_thread():
    """Worker thread for processing measurement jobs with robust error handling"""
    print(f"\n{'='*80}")
    print(f"[MEASUREMENT WORKER] Professional VTON Worker Initialized")
    print(f"[MEASUREMENT WORKER] Standards: Professional sizing (S/M/L/XL/XXL - NO XS)")
    print(f"[MEASUREMENT WORKER] Focus: Accurate inseam-based legwear sizing")
    print(f"[MEASUREMENT WORKER] Error Handling: Robust with fallbacks")
    print(f"[MEASUREMENT WORKER] Waiting for measurement jobs...")
    print(f"{'='*80}\n")
    
    while True:
        try:
            queue_size = queue_manager.get_queue_size()
            if queue_size > 0:
                print(f"\n[QUEUE] Jobs in queue: {queue_size}")
                
                job = queue_manager.get_job(timeout=0.5)
                if job:
                    job_type = job.get('type', 'unknown')
                    job_id = job.get('job_id', 'unknown')
                    
                    print(f"[QUEUE] Retrieved job: {job_id} (type: {job_type})")
                    
                    if job_type == 'measurement':
                        process_measurement_job(job)
                    else:
                        print(f"[QUEUE] Not a measurement job, returning to queue")
                        queue_manager.add_job(job)
            
        except Exception as e:
            if str(e):
                print(f"[WORKER ERROR] {e}")
        
        time.sleep(0.5)

def start_measurement_worker():
    """Start the professional measurement worker thread"""
    thread = threading.Thread(target=measurement_worker_thread, daemon=True)
    thread.start()
    print("[MEASUREMENT WORKER] Professional VTON thread started successfully")
    return thread
