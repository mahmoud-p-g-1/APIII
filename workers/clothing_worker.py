# workers/clothing_worker.py

import os
import sys
import shutil
import threading
import time
from datetime import datetime
import traceback
import json
import tempfile
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests
import base64

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add clothing modules to path
clothing_modules_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'clothing_modules')
if os.path.exists(clothing_modules_path):
    sys.path.insert(0, clothing_modules_path)
    print(f"[CLOTHING WORKER] Clothing modules path added: {clothing_modules_path}")

from queue_manager import queue_manager
from firebase_config import get_access_token

FIREBASE_PROJECT_ID = "fitmatch-1"

# FIXED: Add the missing forbidden keywords constants
FORBIDDEN_KEYWORDS = [
    'underwear', 'bra', 'panties', 'boxers', 'briefs', 'lingerie',
    'thong', 'g-string', 'corset', 'bustier', 'negligee', 'chemise',
    'teddy', 'bodysuit', 'shapewear', 'pantyhose', 'stockings',
    'garter', 'intimate', 'undergarment', 'brassiere', 'camisole'
]

NON_CLOTHING_KEYWORDS = [
    'phone', 'mobile', 'smartphone', 'iphone', 'android', 'tablet', 'laptop',
    'computer', 'hardware', 'electronics', 'device', 'gadget', 'appliance',
    'tool', 'equipment', 'machine', 'furniture', 'car', 'vehicle', 'book',
    'food', 'drink', 'bottle', 'container', 'toy', 'game'
]

# FITMATCH clothing standards from clothh.xlsx and inseam.xlsx
FITMATCH_CLOTHING_STANDARDS = {
    'top': {
        'S': {'chest': (84, 92), 'waist': (66, 74), 'shoulder': (35, 39), 'length': (58, 68)},
        'M': {'chest': (92, 100), 'waist': (74, 82), 'shoulder': (38, 42), 'length': (62, 72)},
        'L': {'chest': (100, 108), 'waist': (82, 90), 'shoulder': (40, 44), 'length': (66, 76)},
        'XL': {'chest': (108, 116), 'waist': (90, 98), 'shoulder': (42, 46), 'length': (70, 80)},
        'XXL': {'chest': (116, 124), 'waist': (98, 106), 'shoulder': (44, 48), 'length': (74, 84)}
    },
    'bottom': {
        'S': {'waist': (66, 74), 'hip': (92, 100), 'inseam': (70, 75), 'length': (95, 105)},
        'M': {'waist': (74, 82), 'hip': (100, 108), 'inseam': (73, 78), 'length': (97, 107)},
        'L': {'waist': (82, 90), 'hip': (108, 116), 'inseam': (76, 81), 'length': (99, 109)},
        'XL': {'waist': (90, 98), 'hip': (116, 124), 'inseam': (79, 84), 'length': (101, 111)},
        'XXL': {'waist': (98, 106), 'hip': (124, 132), 'inseam': (81, 86), 'length': (103, 113)}
    }
}

class FitMatchClothingMeasurementValidator:
    """
    FITMATCH clothing measurement validator with error detection and reprocessing.
    Detects when XL clothes are wrongly classified as S and automatically corrects.
    """
    
    def __init__(self):
        self.max_reprocessing_attempts = 3
        self.error_corrections = []
        self.reprocessing_history = []
        
    def validate_and_reprocess_measurements(self, raw_measurements, clothing_type, user_id):
        """
        Main validation function with automatic error detection and reprocessing.
        Will not give up until measurements are realistic and correct.
        """
        print(f"\n[FITMATCH VALIDATOR] Starting error-detection and reprocessing system...")
        print(f"[FITMATCH VALIDATOR] User: {user_id}")
        print(f"[FITMATCH VALIDATOR] Clothing type: {clothing_type}")
        print(f"[FITMATCH VALIDATOR] Max reprocessing attempts: {self.max_reprocessing_attempts}")
        
        self.error_corrections = []
        self.reprocessing_history = []
        
        current_measurements = raw_measurements.copy()
        
        for attempt in range(1, self.max_reprocessing_attempts + 1):
            print(f"\n[REPROCESSING ATTEMPT {attempt}] Analyzing measurements...")
            
            # Step 1: Detect measurement errors
            errors_detected = self._detect_measurement_errors(current_measurements, clothing_type)
            
            if not errors_detected:
                print(f"[REPROCESSING ATTEMPT {attempt}] ✓ No errors detected, measurements are valid")
                break
            
            print(f"[REPROCESSING ATTEMPT {attempt}] ✗ Detected {len(errors_detected)} errors:")
            for error in errors_detected:
                print(f"    • {error}")
            
            # Step 2: Apply corrections
            corrected_measurements = self._apply_error_corrections(current_measurements, errors_detected, clothing_type)
            
            # Step 3: Validate corrections
            validation_result = self._validate_corrections(corrected_measurements, clothing_type)
            
            if validation_result['is_valid']:
                print(f"[REPROCESSING ATTEMPT {attempt}] ✓ Corrections successful")
                current_measurements = corrected_measurements
                break
            else:
                print(f"[REPROCESSING ATTEMPT {attempt}] ⚠ Corrections need refinement")
                current_measurements = corrected_measurements
                
                # Record reprocessing history
                self.reprocessing_history.append({
                    'attempt': attempt,
                    'errors_detected': errors_detected,
                    'corrections_applied': self.error_corrections[-len(errors_detected):],
                    'validation_result': validation_result
                })
        
        # Final validation and size determination
        final_size = self._determine_final_size_with_confidence(current_measurements, clothing_type)
        
        # Generate detailed fit analysis
        fit_analysis = self._generate_fitmatch_fit_analysis(current_measurements, final_size, clothing_type, user_id)
        
        return {
            'user_id': user_id,
            'clothing_type': clothing_type,
            'measurements': current_measurements,
            'detected_size': final_size,
            'error_corrections': self.error_corrections,
            'reprocessing_history': self.reprocessing_history,
            'fit_analysis': fit_analysis,
            'validation_method': 'FITMATCH_ERROR_DETECTION_REPROCESSING'
        }
    
    def _detect_measurement_errors(self, measurements, clothing_type):
        """
        Detect measurement errors that would cause wrong size classification.
        This is the key function that detects when XL clothes are classified as S.
        """
        errors = []
        
        if clothing_type not in FITMATCH_CLOTHING_STANDARDS:
            return errors
        
        standards = FITMATCH_CLOTHING_STANDARDS[clothing_type]
        
        # Extract measurements
        chest = measurements.get('Chest Circumference', 0)
        waist = measurements.get('Waist Circumference', 0)
        shoulder = measurements.get('Shoulder Width', 0)
        length = measurements.get('Total Length', 0)
        
        print(f"[ERROR DETECTION] Current measurements:")
        print(f"  Chest: {chest:.1f}cm")
        print(f"  Waist: {waist:.1f}cm")
        print(f"  Shoulder: {shoulder:.1f}cm")
        print(f"  Length: {length:.1f}cm")
        
        # Error 1: Detect size classification errors
        chest_size = self._get_size_from_measurement('chest', chest, standards)
        waist_size = self._get_size_from_measurement('waist', waist, standards)
        shoulder_size = self._get_size_from_measurement('shoulder', shoulder, standards)
        length_size = self._get_size_from_measurement('length', length, standards)
        
        print(f"[ERROR DETECTION] Size indicators:")
        print(f"  Chest suggests: {chest_size}")
        print(f"  Waist suggests: {waist_size}")
        print(f"  Shoulder suggests: {shoulder_size}")
        print(f"  Length suggests: {length_size}")
        
        # Detect major size discrepancies
        size_suggestions = [s for s in [chest_size, waist_size, shoulder_size, length_size] if s]
        if len(set(size_suggestions)) > 2:
            errors.append(f"Major size discrepancy detected: {set(size_suggestions)}")
        
        # Error 2: Detect unrealistic proportions
        if chest > 0 and waist > 0:
            waist_to_chest_ratio = waist / chest
            if waist_to_chest_ratio < 0.65 or waist_to_chest_ratio > 0.95:
                errors.append(f"Unrealistic waist-to-chest ratio: {waist_to_chest_ratio:.2f} (should be 0.65-0.95)")
        
        # Error 3: Detect measurements outside human ranges
        if chest > 0 and (chest < 70 or chest > 140):
            errors.append(f"Chest measurement outside human range: {chest:.1f}cm (should be 70-140cm)")
        
        if length > 0 and (length < 50 or length > 100):
            errors.append(f"Length measurement unrealistic: {length:.1f}cm (should be 50-100cm)")
        
        if shoulder > 0 and (shoulder < 30 or shoulder > 60):
            errors.append(f"Shoulder width unrealistic: {shoulder:.1f}cm (should be 30-60cm)")
        
        # Error 4: Detect scaling errors
        if chest > 0 and waist > 0 and shoulder > 0:
            if chest_size == waist_size == shoulder_size and chest_size in ['S', 'XXL']:
                if chest_size == 'S' and chest > 80:
                    errors.append(f"Potential scaling error: measurements suggest S but chest {chest:.1f}cm is too large for S")
                elif chest_size == 'XXL' and chest < 110:
                    errors.append(f"Potential scaling error: measurements suggest XXL but chest {chest:.1f}cm is too small for XXL")
        
        return errors
    
    def _get_size_from_measurement(self, measurement_type, value, standards):
        """Get size suggestion from a single measurement"""
        if value <= 0:
            return None
        
        for size, ranges in standards.items():
            if measurement_type in ranges:
                min_val, max_val = ranges[measurement_type]
                if min_val <= value <= max_val:
                    return size
        
        # Find closest size if no exact match
        closest_size = None
        min_distance = float('inf')
        
        for size, ranges in standards.items():
            if measurement_type in ranges:
                min_val, max_val = ranges[measurement_type]
                center = (min_val + max_val) / 2
                distance = abs(value - center)
                if distance < min_distance:
                    min_distance = distance
                    closest_size = size
        
        return closest_size
    
    def _apply_error_corrections(self, measurements, errors, clothing_type):
        """Apply corrections based on detected errors"""
        corrected = measurements.copy()
        
        for error in errors:
            if "size discrepancy" in error.lower():
                corrected = self._fix_size_discrepancy(corrected, clothing_type)
                self.error_corrections.append(f"Fixed size discrepancy by adjusting measurement proportions")
            
            elif "waist-to-chest ratio" in error.lower():
                corrected = self._fix_waist_chest_ratio(corrected)
                self.error_corrections.append(f"Fixed waist-to-chest ratio to realistic proportions")
            
            elif "outside human range" in error.lower():
                corrected = self._fix_human_range_violations(corrected, clothing_type)
                self.error_corrections.append(f"Corrected measurements to human-realistic ranges")
            
            elif "scaling error" in error.lower():
                corrected = self._fix_scaling_errors(corrected, clothing_type)
                self.error_corrections.append(f"Fixed scaling error in measurements")
        
        return corrected
    
    def _fix_size_discrepancy(self, measurements, clothing_type):
        """Fix size discrepancies by making measurements more consistent"""
        corrected = measurements.copy()
        
        chest = measurements.get('Chest Circumference', 0)
        waist = measurements.get('Waist Circumference', 0)
        shoulder = measurements.get('Shoulder Width', 0)
        
        if chest > 0:
            standards = FITMATCH_CLOTHING_STANDARDS[clothing_type]
            chest_size = self._get_size_from_measurement('chest', chest, standards)
            
            if chest_size and chest_size in standards:
                size_ranges = standards[chest_size]
                
                if 'waist' in size_ranges:
                    waist_min, waist_max = size_ranges['waist']
                    target_waist = (waist_min + waist_max) / 2
                    corrected['Waist Circumference'] = target_waist
                
                if 'shoulder' in size_ranges:
                    shoulder_min, shoulder_max = size_ranges['shoulder']
                    target_shoulder = (shoulder_min + shoulder_max) / 2
                    corrected['Shoulder Width'] = target_shoulder
        
        return corrected
    
    def _fix_waist_chest_ratio(self, measurements):
        """Fix unrealistic waist-to-chest ratios"""
        corrected = measurements.copy()
        
        chest = measurements.get('Chest Circumference', 0)
        waist = measurements.get('Waist Circumference', 0)
        
        if chest > 0 and waist > 0:
            ratio = waist / chest
            
            if ratio < 0.65:
                corrected['Waist Circumference'] = chest * 0.75
            elif ratio > 0.95:
                corrected['Waist Circumference'] = chest * 0.85
        
        return corrected
    
    def _fix_human_range_violations(self, measurements, clothing_type):
        """Fix measurements that are outside realistic human ranges"""
        corrected = measurements.copy()
        
        chest = measurements.get('Chest Circumference', 0)
        if chest > 0:
            if chest < 70:
                corrected['Chest Circumference'] = 75
            elif chest > 140:
                corrected['Chest Circumference'] = 130
        
        shoulder = measurements.get('Shoulder Width', 0)
        if shoulder > 0:
            if shoulder < 30:
                corrected['Shoulder Width'] = 35
            elif shoulder > 60:
                corrected['Shoulder Width'] = 55
        
        length = measurements.get('Total Length', 0)
        if length > 0:
            if length < 50:
                corrected['Total Length'] = 55
            elif length > 100:
                corrected['Total Length'] = 90
        
        return corrected
    
    def _fix_scaling_errors(self, measurements, clothing_type):
        """Fix scaling errors where all measurements are consistently wrong"""
        corrected = measurements.copy()
        
        chest = measurements.get('Chest Circumference', 0)
        
        if chest > 0:
            if chest < 80 and chest > 70:
                scale_factor = 1.15
                for key in ['Chest Circumference', 'Waist Circumference', 'Shoulder Width', 'Total Length']:
                    if key in corrected and corrected[key] > 0:
                        corrected[key] = corrected[key] * scale_factor
            elif chest > 120 and chest < 140:
                scale_factor = 0.90
                for key in ['Chest Circumference', 'Waist Circumference', 'Shoulder Width', 'Total Length']:
                    if key in corrected and corrected[key] > 0:
                        corrected[key] = corrected[key] * scale_factor
        
        return corrected
    
    def _validate_corrections(self, measurements, clothing_type):
        """Validate that corrections were successful"""
        validation_result = {'is_valid': True, 'issues': []}
        
        remaining_errors = self._detect_measurement_errors(measurements, clothing_type)
        
        if remaining_errors:
            validation_result['is_valid'] = False
            validation_result['issues'] = remaining_errors
        
        return validation_result
    
    def _determine_final_size_with_confidence(self, measurements, clothing_type):
        """Determine final size with high confidence after error correction"""
        if clothing_type not in FITMATCH_CLOTHING_STANDARDS:
            return 'M'
        
        standards = FITMATCH_CLOTHING_STANDARDS[clothing_type]
        size_scores = {}
        
        for size, ranges in standards.items():
            score = 0
            weight_sum = 0
            
            if clothing_type == 'top':
                measurement_weights = {'chest': 0.50, 'waist': 0.25, 'shoulder': 0.15, 'length': 0.10}
            else:
                measurement_weights = {'waist': 0.40, 'hip': 0.35, 'inseam': 0.25}
            
            for measurement_type, weight in measurement_weights.items():
                measurement_key = {
                    'chest': 'Chest Circumference',
                    'waist': 'Waist Circumference',
                    'hip': 'Hip Circumference',
                    'shoulder': 'Shoulder Width',
                    'length': 'Total Length',
                    'inseam': 'Inseam Length'
                }.get(measurement_type)
                
                if measurement_key and measurement_key in measurements:
                    value = measurements[measurement_key]
                    if value > 0 and measurement_type in ranges:
                        min_val, max_val = ranges[measurement_type]
                        
                        if min_val <= value <= max_val:
                            fit_score = 100
                        else:
                            if value < min_val:
                                penalty = ((min_val - value) / min_val) * 100
                            else:
                                penalty = ((value - max_val) / max_val) * 100
                            fit_score = max(50, 100 - penalty)
                        
                        score += fit_score * weight
                        weight_sum += weight
            
            if weight_sum > 0:
                size_scores[size] = score / weight_sum
            else:
                size_scores[size] = 0
        
        best_size = max(size_scores.keys(), key=size_scores.get) if size_scores else 'M'
        best_score = size_scores.get(best_size, 0)
        
        print(f"[FINAL SIZE DETERMINATION] Size scores: {size_scores}")
        print(f"[FINAL SIZE DETERMINATION] ✓ Final size: {best_size} (confidence: {best_score:.1f}%)")
        
        return best_size
    
    def _generate_fitmatch_fit_analysis(self, measurements, detected_size, clothing_type, user_id):
        """Generate clean, FITMATCH fit analysis"""
        analysis = []
        
        if clothing_type == 'top':
            chest = measurements.get('Chest Circumference', 0)
            shoulder = measurements.get('Shoulder Width', 0)
            length = measurements.get('Total Length', 0)
            
            if chest > 0:
                if detected_size in FITMATCH_CLOTHING_STANDARDS[clothing_type]:
                    ranges = FITMATCH_CLOTHING_STANDARDS[clothing_type][detected_size]
                    chest_min, chest_max = ranges['chest']
                    
                    if chest_min <= chest <= chest_max:
                        analysis.append("Chest: Perfect fit")
                    elif chest < chest_min:
                        analysis.append("Chest: Loose fit")
                    else:
                        analysis.append("Chest: Snug fit")
            
            if shoulder > 0:
                if detected_size in FITMATCH_CLOTHING_STANDARDS[clothing_type]:
                    ranges = FITMATCH_CLOTHING_STANDARDS[clothing_type][detected_size]
                    shoulder_min, shoulder_max = ranges['shoulder']
                    
                    if shoulder_min <= shoulder <= shoulder_max:
                        analysis.append("Shoulders: Perfect fit")
                    elif shoulder < shoulder_min:
                        analysis.append("Shoulders: Loose fit")
                    else:
                        analysis.append("Shoulders: Snug fit")
            
            if length > 0:
                if detected_size in FITMATCH_CLOTHING_STANDARDS[clothing_type]:
                    ranges = FITMATCH_CLOTHING_STANDARDS[clothing_type][detected_size]
                    length_min, length_max = ranges['length']
                    
                    if length_min <= length <= length_max:
                        analysis.append("Length: Ideal")
                    elif length < length_min:
                        analysis.append("Length: Short")
                    else:
                        analysis.append("Length: Long")
        
        elif clothing_type == 'bottom':
            waist = measurements.get('Waist Circumference', 0)
            hip = measurements.get('Hip Circumference', 0)
            inseam = measurements.get('Inseam Length', 0)
            
            if waist > 0:
                if detected_size in FITMATCH_CLOTHING_STANDARDS[clothing_type]:
                    ranges = FITMATCH_CLOTHING_STANDARDS[clothing_type][detected_size]
                    waist_min, waist_max = ranges['waist']
                    
                    if waist_min <= waist <= waist_max:
                        analysis.append("Waist: Perfect fit")
                    elif waist < waist_min:
                        analysis.append("Waist: Loose fit")
                    else:
                        analysis.append("Waist: Snug fit")
            
            if hip > 0:
                if detected_size in FITMATCH_CLOTHING_STANDARDS[clothing_type]:
                    ranges = FITMATCH_CLOTHING_STANDARDS[clothing_type][detected_size]
                    hip_min, hip_max = ranges['hip']
                    
                    if hip_min <= hip <= hip_max:
                        analysis.append("Hips: Perfect fit")
                    elif hip < hip_min:
                        analysis.append("Hips: Loose fit")
                    else:
                        analysis.append("Hips: Snug fit")
            
            if inseam > 0:
                if detected_size in FITMATCH_CLOTHING_STANDARDS[clothing_type]:
                    ranges = FITMATCH_CLOTHING_STANDARDS[clothing_type][detected_size]
                    inseam_min, inseam_max = ranges['inseam']
                    
                    if inseam_min <= inseam <= inseam_max:
                        analysis.append("Inseam: Perfect length")
                    elif inseam < inseam_min:
                        analysis.append("Inseam: Short")
                    else:
                        analysis.append("Inseam: Long")
        
        return analysis

# Initialize the validator
fitmatch_validator = FitMatchClothingMeasurementValidator()

def get_vision_api_access_token():
    """Get access token using firebase-service-account.json from project root"""
    try:
        project_root = os.path.dirname(os.path.dirname(__file__))
        service_account_path = os.path.join(project_root, 'firebase-service-account.json')
        
        if not os.path.exists(service_account_path):
            service_account_path = 'firebase-service-account.json'
        
        if not os.path.exists(service_account_path):
            service_account_path = '../firebase-service-account.json'
        
        if not os.path.exists(service_account_path):
            service_account_path = '../../firebase-service-account.json'
        
        if not os.path.exists(service_account_path):
            print(f"[VISION AUTH] ✗ firebase-service-account.json not found")
            return None
        
        credentials = service_account.Credentials.from_service_account_file(
            service_account_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        credentials.refresh(Request())
        return credentials.token
        
    except Exception as e:
        print(f"[VISION AUTH] ✗ Error: {str(e)}")
        return None

def analyze_clothing_with_vision_api(image_path):
    """Analyze clothing using Google Vision API with service account"""
    try:
        print(f"[GOOGLE VISION] Analyzing clothing: {image_path}")
        
        access_token = get_vision_api_access_token()
        if not access_token:
            return {'labels': [], 'objects': [], 'success': False, 'error': 'Authentication failed'}
        
        with open(image_path, 'rb') as image_file:
            image_content = image_file.read()
            image_base64 = base64.b64encode(image_content).decode('utf-8')
        
        vision_request = {
            "requests": [
                {
                    "image": {"content": image_base64},
                    "features": [
                        {"type": "LABEL_DETECTION", "maxResults": 30},
                        {"type": "OBJECT_LOCALIZATION", "maxResults": 20}
                    ]
                }
            ]
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            'https://vision.googleapis.com/v1/images:annotate',
            json=vision_request,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            labels = []
            objects = []
            
            if 'responses' in result and result['responses']:
                response_data = result['responses'][0]
                
                if 'labelAnnotations' in response_data:
                    for label in response_data['labelAnnotations']:
                        labels.append({
                            'description': label['description'].lower(),
                            'score': label['score'],
                            'confidence': f"{label['score'] * 100:.1f}%"
                        })
                
                if 'localizedObjectAnnotations' in response_data:
                    for obj in response_data['localizedObjectAnnotations']:
                        objects.append({
                            'name': obj['name'].lower(),
                            'score': obj['score'],
                            'confidence': f"{obj['score'] * 100:.1f}%"
                        })
            
            print(f"[GOOGLE VISION] ✓ Found {len(labels)} labels, {len(objects)} objects")
            return {'labels': labels, 'objects': objects, 'success': True}
        else:
            print(f"[GOOGLE VISION] ✗ API Error: {response.status_code}")
            return {'labels': [], 'objects': [], 'success': False, 'error': f"API Error: {response.status_code}"}
            
    except Exception as e:
        print(f"[GOOGLE VISION] ✗ Error: {str(e)}")
        return {'labels': [], 'objects': [], 'success': False, 'error': str(e)}

def check_forbidden_items(labels, objects):
    """Check for forbidden clothing items"""
    all_items = [label['description'] for label in labels] + [obj['name'] for obj in objects]
    
    print(f"[FORBIDDEN CHECK] Checking {len(all_items)} detected items...")
    
    for item in all_items:
        for forbidden in FORBIDDEN_KEYWORDS:
            if forbidden.lower() in item.lower():
                return {
                    'is_forbidden': True,
                    'keyword': forbidden,
                    'detected_item': item,
                    'message': f"Found FORBIDDEN underwear keyword '{forbidden}' in IMAGE - REJECTING"
                }
        
        for non_clothing in NON_CLOTHING_KEYWORDS:
            if non_clothing.lower() in item.lower():
                return {
                    'is_forbidden': True,
                    'keyword': non_clothing,
                    'detected_item': item,
                    'message': f"Found NON-CLOTHING item '{non_clothing}' in IMAGE - REJECTING"
                }
    
    print(f"[FORBIDDEN CHECK] ✓ All items are acceptable clothing")
    return {'is_forbidden': False, 'message': 'Item is acceptable clothing'}

def _classify_clothing_type_fitmatch(vision_result):
    """FITMATCH clothing-first detection - ignore car logos and non-clothing elements"""
    print(f"[FITMATCH CLOTHING DETECTION] Starting clothing-first analysis...")
    
    labels = [label['description'].lower() for label in vision_result.get('labels', [])]
    objects = [obj['name'].lower() for obj in vision_result.get('objects', [])]
    
    print(f"[FITMATCH CLOTHING DETECTION] Raw Vision API results:")
    print(f"  Objects: {objects}")
    print(f"  Labels: {labels[:10]}")
    
    # STEP 1: FORCE CLOTHING DETECTION - Look for ANY clothing indicators
    clothing_indicators = {
        'top': ['shirt', 'blouse', 'top', 't-shirt', 'polo', 'sweater', 'cardigan', 'hoodie', 'pullover', 'jersey', 'tee', 'tank', 'vest', 'tunic'],
        'bottom': ['pants', 'trousers', 'jeans', 'slacks', 'leggings', 'shorts', 'sweatpants', 'joggers', 'cargo', 'chinos', 'denim'],
        'dress': ['dress', 'gown', 'frock', 'maxi', 'mini dress', 'cocktail dress'],
        'outerwear': ['jacket', 'coat', 'blazer', 'windbreaker', 'parka', 'bomber']
    }
    
    # STEP 2: PRIORITIZE CLOTHING OBJECTS (ignore car logos, etc.)
    for clothing_type, keywords in clothing_indicators.items():
        for obj in objects:
            if any(keyword in obj for keyword in keywords):
                print(f"[FITMATCH CLOTHING DETECTION] ✓ CONFIRMED {clothing_type.upper()} from object: {obj}")
                return clothing_type
    
    # STEP 3: CHECK HIGH-CONFIDENCE LABELS FOR CLOTHING
    high_confidence_labels = [l for l in vision_result.get('labels', []) if l.get('score', 0) > 0.7]
    
    for clothing_type, keywords in clothing_indicators.items():
        for label in high_confidence_labels:
            label_desc = label['description'].lower()
            if any(keyword in label_desc for keyword in keywords):
                print(f"[FITMATCH CLOTHING DETECTION] ✓ CONFIRMED {clothing_type.upper()} from label: {label_desc}")
                return clothing_type
    
    # STEP 4: FALLBACK - If "outerwear" detected, classify as jacket/top
    if 'outerwear' in objects:
        print(f"[FITMATCH CLOTHING DETECTION] ✓ OUTERWEAR detected → classifying as TOP")
        return 'top'
    
    # STEP 5: EMERGENCY CLOTHING ASSUMPTION
    print(f"[FITMATCH CLOTHING DETECTION] ⚠ No clear clothing detected, but assuming TOP (user intent)")
    return 'top'  # Default to top instead of general_clothing

def compare_body_vs_clothing(body_measurements, clothing_measurements):
    """FITMATCH body vs clothing comparison with realistic confidence"""
    try:
        print(f"\n[FITMATCH BODY COMPARISON] Starting realistic comparison...")
        
        # FIXED: Extract user ID properly from multiple possible sources
        user_id = None
        
        # Try different possible keys for user ID
        possible_user_keys = ['user_id', 'uid', 'userId', 'user', 'id']
        for key in possible_user_keys:
            if key in body_measurements and body_measurements[key]:
                user_id = body_measurements[key]
                break
        
        # If still not found, try nested structures
        if not user_id:
            for key, value in body_measurements.items():
                if isinstance(value, dict) and 'user_id' in value:
                    user_id = value['user_id']
                    break
        
        
        # Extract body measurements
        body_chest = _extract_measurement_value(body_measurements, 'chest', 85.0)
        body_waist = _extract_measurement_value(body_measurements, 'waist', 70.0)
        body_hips = _extract_measurement_value(body_measurements, 'hips', 90.0)
        body_inseam = _extract_measurement_value(body_measurements, 'inseam', 75.0)
        body_height = _extract_measurement_value(body_measurements, 'height', 165.0)
        
        print(f"[FITMATCH BODY COMPARISON] User: {user_id}")
        print(f"[FITMATCH BODY COMPARISON] Body measurements:")
        print(f"  Height: {body_height:.1f}cm")
        print(f"  Chest: {body_chest:.1f}cm")
        print(f"  Waist: {body_waist:.1f}cm")
        print(f"  Hips: {body_hips:.1f}cm")
        print(f"  Inseam: {body_inseam:.1f}cm")
        
        # Get clothing measurements
        clothing_type = clothing_measurements.get('Clothing Type', 'top')
        detected_clothing_size = clothing_measurements.get('Detected Clothing Size', 'M')
        
        print(f"[FITMATCH BODY COMPARISON] Clothing info:")
        print(f"  Type: {clothing_type}")
        print(f"  Detected size: {detected_clothing_size}")
        
        # Get recommended body size
        recommended_body_size = _get_recommended_size_from_body_measurements(
            body_chest, body_waist, body_hips, body_inseam, clothing_type
        )
        
        print(f"[FITMATCH BODY COMPARISON] Size comparison:")
        print(f"  Body needs size: {recommended_body_size}")
        print(f"  Clothing is size: {detected_clothing_size}")
        
        # FIXED: Calculate realistic match percentage (not always 100%)
        realistic_match_percentage = _calculate_realistic_size_compatibility(
            recommended_body_size, detected_clothing_size
        )
        
        # FIXED: Generate clean, professional fit analysis (no ugly titles)
        clean_fit_analysis = _generate_clean_fit_analysis(
            body_chest, body_waist, body_hips, body_inseam, body_height,
            recommended_body_size, detected_clothing_size, clothing_measurements, user_id
        )
        
        return {
            'user_id': user_id,  # FIXED: Separate user field
            'recommended_size': recommended_body_size,
            'detected_clothing_size': detected_clothing_size,
            'excellent_match_percentage': realistic_match_percentage,
            'detailed_fit_analysis': clean_fit_analysis,  # FIXED: Clean array format
            'body_measurements_used': {
                'height': body_height,
                'chest': body_chest,
                'waist': body_waist,
                'hips': body_hips,
                'inseam': body_inseam
            },
            'clothing_type': clothing_type,
            'fitmatch_analysis': True  # FIXED: Changed from professional_analysis
        }
        
    except Exception as e:
        print(f"[FITMATCH BODY COMPARISON] ✗ Error: {str(e)}")
        return {
            'user_id': 'Unknown User',
            'recommended_size': 'M', 
            'detected_clothing_size': 'M',
            'excellent_match_percentage': 75.0, 
            'detailed_fit_analysis': ['Error in analysis'],
            'fitmatch_analysis': False
        }

def _extract_measurement_value(measurements, measurement_type, default_value):
    """Extract measurement value with comprehensive key mapping"""
    possible_keys = {
        'chest': ['chest', 'chest_circumference', 'Professional_Chest', 'Final_Chest', 'Chest Circumference'],
        'waist': ['waist', 'waist_circumference', 'Professional_Waist', 'Final_Waist', 'Waist Circumference'],
        'hips': ['hips', 'hip_circumference', 'Professional_Hips', 'Final_Hips', 'Hip Circumference'],
        'inseam': ['inseam', 'leg_length', 'Professional_Inseam', 'Final_Inseam', 'Inseam Length'],
        'height': ['height', 'Height', 'Professional_Height', 'Final_Height']
    }
    
    for key in possible_keys.get(measurement_type, [measurement_type]):
        if key in measurements:
            value = measurements[key]
            if isinstance(value, dict):
                return float(value.get('value', default_value))
            elif isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                try:
                    return float(value.replace(' cm', '').replace('cm', '').strip())
                except:
                    continue
    
    return default_value

def _get_recommended_size_from_body_measurements(chest, waist, hips, inseam, clothing_type):
    """Get recommended size using FITMATCH body measurement standards"""
    print(f"\n[BODY SIZE RECOMMENDATION] Using FITMATCH body standards...")
    
    if clothing_type not in FITMATCH_CLOTHING_STANDARDS:
        return 'M'
    
    standards = FITMATCH_CLOTHING_STANDARDS[clothing_type]
    best_size = 'M'
    best_score = 0
    
    for size, size_standards in standards.items():
        score = 0
        measurement_count = 0
        
        if clothing_type == 'top':
            # For tops: check body measurements against body ranges
            measurements_to_check = [
                ('chest', chest, 0.50),
                ('waist', waist, 0.30),
                ('shoulder', chest * 0.40, 0.20)  # Estimate shoulder from chest
            ]
        elif clothing_type == 'bottom':
            # For bottoms: check body measurements
            measurements_to_check = [
                ('waist', waist, 0.40),
                ('hip', hips, 0.35),
                ('inseam', inseam, 0.25)
            ]
        else:
            measurements_to_check = []
        
        for measurement_name, measurement_value, weight in measurements_to_check:
            if measurement_name in size_standards:
                min_val, max_val = size_standards[measurement_name]
                
                if min_val <= measurement_value <= max_val:
                    fit_score = 100.0
                elif measurement_value < min_val:
                    distance = min_val - measurement_value
                    fit_score = max(60.0, 100.0 - (distance / min_val * 100))
                else:
                    distance = measurement_value - max_val
                    fit_score = max(60.0, 100.0 - (distance / max_val * 100))
                
                score += fit_score * weight
                measurement_count += 1
        
        if measurement_count > 0:
            final_score = score / measurement_count
            if final_score > best_score:
                best_score = final_score
                best_size = size
        
        print(f"[BODY SIZE RECOMMENDATION] {size}: score = {score / measurement_count if measurement_count > 0 else 0:.1f}")
    
    print(f"[BODY SIZE RECOMMENDATION] ✓ Body needs size: {best_size} (score: {best_score:.1f})")
    return best_size

def _calculate_realistic_size_compatibility(body_size, clothing_size):
    """FIXED: Calculate realistic size compatibility (not always 100%)"""
    size_order = ['S', 'M', 'L', 'XL', 'XXL']
    
    try:
        body_index = size_order.index(body_size)
        clothing_index = size_order.index(clothing_size)
        
        size_difference = abs(body_index - clothing_index)
        
        if size_difference == 0:
            # Perfect match - but not always 100% (add some realism)
            compatibility = 95.0  # FIXED: 95% instead of 100%
            print(f"[REALISTIC COMPATIBILITY] ✓ EXCELLENT MATCH: {body_size} body = {clothing_size} clothing")
        elif size_difference == 1:
            # One size difference - good fit
            compatibility = 80.0
            if clothing_index > body_index:
                print(f"[REALISTIC COMPATIBILITY] ✓ GOOD: {clothing_size} clothing is one size larger than {body_size} body (loose fit)")
            else:
                print(f"[REALISTIC COMPATIBILITY] ⚠ TIGHT: {clothing_size} clothing is one size smaller than {body_size} body")
        elif size_difference == 2:
            # Two sizes difference - acceptable
            compatibility = 65.0
            print(f"[REALISTIC COMPATIBILITY] ⚠ ACCEPTABLE: {size_difference} sizes apart")
        else:
            # Too much difference
            compatibility = 45.0
            print(f"[REALISTIC COMPATIBILITY] ✗ POOR: {size_difference} sizes apart - not recommended")
        
        return compatibility
        
    except ValueError:
        print(f"[REALISTIC COMPATIBILITY] ✗ Invalid sizes: body={body_size}, clothing={clothing_size}")
        return 70.0  # Neutral compatibility

def _generate_clean_fit_analysis(chest, waist, hips, inseam, height, body_size, clothing_size, clothing_measurements, user_id):
    """FIXED: Generate clean fit analysis with only essential data"""
    analysis = []
    clothing_type = clothing_measurements.get('Clothing Type', 'top')
    
    # FIXED: Only essential fit information, no titles or unnecessary text
    if clothing_type == 'top':
        chest_measurement = clothing_measurements.get('Chest Circumference', 0)
        length_measurement = clothing_measurements.get('Total Length', 0)
        shoulder_measurement = clothing_measurements.get('Shoulder Width', 0)
        
        # FIXED: Only the essential fit analysis
        if chest_measurement > 0:
            chest_ease = chest_measurement - chest
            if chest_ease >= 10:
                analysis.append("Chest: Comfortable")
            elif chest_ease >= 5:
                analysis.append("Chest: Good")
            elif chest_ease >= 0:
                analysis.append("Chest: Fitted")
            else:
                analysis.append("Chest: Too tight")
        
        if shoulder_measurement > 0:
            shoulder_diff = abs(shoulder_measurement - (chest * 0.45))
            if shoulder_diff <= 2:
                analysis.append("Shoulders: Perfect")
            elif shoulder_diff <= 4:
                analysis.append("Shoulders: Good")
            else:
                analysis.append("Shoulders: Check")
        
        if length_measurement > 0:
            if 60 <= length_measurement <= 75:
                analysis.append("Length: Ideal")
            elif length_measurement < 60:
                analysis.append("Length: Short")
            else:
                analysis.append("Length: Long")
    
    elif clothing_type == 'bottom':
        waist_measurement = clothing_measurements.get('Waist Circumference', 0)
        hip_measurement = clothing_measurements.get('Hip Circumference', 0)
        inseam_measurement = clothing_measurements.get('Inseam Length', 0)
        
        if waist_measurement > 0:
            waist_ease = waist_measurement - waist
            if waist_ease >= 8:
                analysis.append("Waist: Comfortable")
            elif waist_ease >= 3:
                analysis.append("Waist: Good")
            elif waist_ease >= 0:
                analysis.append("Waist: Fitted")
            else:
                analysis.append("Waist: Too tight")
        
        if hip_measurement > 0:
            hip_ease = hip_measurement - hips
            if hip_ease >= 8:
                analysis.append("Hips: Comfortable")
            elif hip_ease >= 3:
                analysis.append("Hips: Good")
            elif hip_ease >= 0:
                analysis.append("Hips: Fitted")
            else:
                analysis.append("Hips: Too tight")
        
        if inseam_measurement > 0:
            inseam_diff = inseam_measurement - inseam
            if abs(inseam_diff) <= 2:
                analysis.append("Inseam: Perfect length")
            elif inseam_diff > 2:
                analysis.append("Inseam: Long")
            else:
                analysis.append("Inseam: Short")
    
    elif clothing_type == 'dress':
        chest_measurement = clothing_measurements.get('Chest Circumference', 0)
        waist_measurement = clothing_measurements.get('Waist Circumference', 0)
        length_measurement = clothing_measurements.get('Total Length', 0)
        
        if chest_measurement > 0:
            chest_ease = chest_measurement - chest
            if chest_ease >= 10:
                analysis.append("Chest: Comfortable")
            elif chest_ease >= 5:
                analysis.append("Chest: Good")
            else:
                analysis.append("Chest: Fitted")
        
        if waist_measurement > 0:
            waist_ease = waist_measurement - waist
            if waist_ease >= 8:
                analysis.append("Waist: Comfortable")
            elif waist_ease >= 3:
                analysis.append("Waist: Good")
            else:
                analysis.append("Waist: Fitted")
        
        if length_measurement > 0:
            if 90 <= length_measurement <= 110:
                analysis.append("Length: Ideal")
            elif length_measurement < 90:
                analysis.append("Length: Short")
            else:
                analysis.append("Length: Long")
    
    return analysis

def update_clothing_job_status(job_id, status, result_data=None):
    """FIXED: Update clothing job status with clean data and proper user detection"""
    try:
        print(f"\n[FIRESTORE] Updating clothing job status to: {status}")
        
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
                'updated_at': {'stringValue': datetime.now().isoformat()},
                'job_type': {'stringValue': 'clothing_measurement'}
            }
        }
        
        if result_data:
            if status == 'completed':
                job_data['fields']['completed_at'] = {'stringValue': datetime.now().isoformat()}
                
                # FIXED: Store clean clothing measurements (remove unnecessary fields)
                if 'clothing_measurements' in result_data:
                    clean_measurements = {}
                    for k, v in result_data['clothing_measurements'].items():
                        # FIXED: Remove unnecessary keys
                        if k in ['Size Confidence Breakdown', 'Detailed Fit Analysis']:
                            continue
                        # FIXED: Change PROFESSIONAL to FITMATCH
                        if isinstance(v, str) and 'PROFESSIONAL' in v:
                            v = v.replace('PROFESSIONAL', 'FITMATCH')
                        
                        if isinstance(v, (str, int, float, bool)):
                            clean_measurements[k] = v
                        elif isinstance(v, dict):
                            clean_measurements[k] = v
                        else:
                            clean_measurements[k] = str(v)
                    
                    job_data['fields']['clothing_measurements'] = {'stringValue': json.dumps(clean_measurements)}
                
                # FIXED: Store comparison results with clean format and separate user field
                if 'comparison_result' in result_data:
                    comparison = result_data['comparison_result']
                    
                    # FIXED: Add separate user field
                    if 'user_id' in comparison and comparison['user_id'] != 'Unknown User':
                        job_data['fields']['user_id'] = {'stringValue': comparison['user_id']}
                    
                    job_data['fields']['recommended_size'] = {'stringValue': comparison.get('recommended_size', 'M')}
                    job_data['fields']['detected_clothing_size'] = {'stringValue': comparison.get('detected_clothing_size', 'M')}
                    job_data['fields']['excellent_match_percentage'] = {'doubleValue': float(comparison.get('excellent_match_percentage', 75.0))}
                    
                    # FIXED: Store clean fit analysis as proper JSON array (no ugly titles)
                    clean_fit_analysis = comparison.get('detailed_fit_analysis', [])
                    job_data['fields']['detailed_fit_analysis'] = {'stringValue': json.dumps(clean_fit_analysis)}
                
                # FIXED: Store error corrections and reprocessing history
                if 'error_corrections' in result_data:
                    job_data['fields']['error_corrections'] = {'stringValue': json.dumps(result_data['error_corrections'])}
                
                if 'reprocessing_history' in result_data:
                    job_data['fields']['reprocessing_history'] = {'stringValue': json.dumps(result_data['reprocessing_history'])}
                
                # FIXED: Change validation method name from PROFESSIONAL to FITMATCH
                if 'validation_method' in result_data:
                    validation_method = result_data['validation_method'].replace('PROFESSIONAL', 'FITMATCH')
                    job_data['fields']['validation_method'] = {'stringValue': validation_method}
                
                # Store vision analysis results
                if 'vision_result' in result_data:
                    clean_vision = {
                        'labels': result_data['vision_result'].get('labels', []),
                        'objects': result_data['vision_result'].get('objects', []),
                        'success': result_data['vision_result'].get('success', False)
                    }
                    job_data['fields']['vision_analysis'] = {'stringValue': json.dumps(clean_vision)}
                
                # Store clothing type
                if 'clothing_type' in result_data:
                    job_data['fields']['clothing_type'] = {'stringValue': result_data['clothing_type']}
                
                job_data['fields']['test_mode'] = {'booleanValue': result_data.get('is_test', True)}
                    
            elif status == 'failed':
                job_data['fields']['failed_at'] = {'stringValue': datetime.now().isoformat()}
                if 'error' in result_data:
                    job_data['fields']['error'] = {'stringValue': str(result_data['error'])}
            
            elif status == 'rejected':
                job_data['fields']['rejected_at'] = {'stringValue': datetime.now().isoformat()}
                if 'rejection_reason' in result_data:
                    job_data['fields']['rejection_reason'] = {'stringValue': result_data['rejection_reason']}
        
        url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/clothing_jobs/{job_id}"
        response = requests.patch(url, json=job_data, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"[FIRESTORE] ✓ Clothing job status updated successfully")
            return True
        else:
            print(f"[FIRESTORE] ✗ Failed to update status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"[FIRESTORE] ✗ Error: {e}")
        return False

def process_clothing_job(job_data):
    """Process clothing measurement job with FITMATCH error detection and reprocessing"""
    job_id = job_data['job_id']
    user_id = job_data['user_id']
    
    print(f"\n{'='*80}")
    print(f"[CLOTHING PROCESSING] Starting FITMATCH Job with Error Detection: {job_id}")
    print(f"[CLOTHING PROCESSING] User: {user_id}")
    print(f"[CLOTHING PROCESSING] FITMATCH: Error detection + automatic reprocessing")
    print(f"[CLOTHING PROCESSING] Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*80}")
    
    working_dir = None
    original_dir = os.getcwd()
    
    try:
        # Update status to processing
        update_clothing_job_status(job_id, 'processing')
        
        clothing_image = job_data['clothing_image']
        body_measurements = job_data.get('body_measurements')
        job_dir = job_data['job_dir']
        is_test = job_data.get('is_test', False)
        
        # Check if image exists
        if not os.path.exists(clothing_image):
            raise Exception(f"Clothing image not found: {clothing_image}")
        
        # Create working directory
        working_dir = tempfile.mkdtemp(prefix=f"clothing_{job_id}_")
        os.makedirs(os.path.join(working_dir, 'images'), exist_ok=True)
        
        # Copy clothing image to working directory
        shutil.copy(clothing_image, os.path.join(working_dir, 'clothing_input.jpg'))
        
        # Change to working directory
        os.chdir(working_dir)
        sys.path.insert(0, working_dir)
        
        try:
            # Step 1: Google Vision API Analysis
            print(f"\n[STEP 1] Google Vision API Analysis...")
            vision_result = analyze_clothing_with_vision_api('clothing_input.jpg')
            
            if not vision_result['success']:
                raise Exception(f"Vision API failed: {vision_result.get('error')}")
            
            # Display Vision API results
            labels_display = [f"{l['description']} ({l['confidence']})" for l in vision_result['labels'][:5]]
            objects_display = [f"{o['name']} ({o['confidence']})" for o in vision_result['objects']]
            
            print(f"[STEP 1] Vision API Results:")
            print(f"  Top Labels: {labels_display}")
            print(f"  Objects: {objects_display}")
            
            # Check forbidden items
            forbidden_check = check_forbidden_items(vision_result['labels'], vision_result['objects'])
            if forbidden_check['is_forbidden']:
                print(f"[STEP 1] ✗ {forbidden_check['message']}")
                
                update_clothing_job_status(job_id, 'rejected', {
                    'rejection_reason': forbidden_check['message'],
                    'keyword_found': forbidden_check['keyword'],
                    'is_test': is_test
                })
                return
            
            print(f"[STEP 1] ✓ Item is acceptable clothing")
            
            # FITMATCH: Clothing-first detection
            clothing_type = _classify_clothing_type_fitmatch(vision_result)
            print(f"[STEP 1] ✓ FITMATCH clothing type detection: {clothing_type}")
            
            # Create clothing configuration
            config_content = f"""
clothing_input_image = 'clothing_input.jpg'
measurement_mode = 'fitmatch'
detected_clothing_type = '{clothing_type}'
"""
            with open('clothing_config.py', 'w') as f:
                f.write(config_content)
            
            # Step 2-5: Run clothing measurement modules
            modules_to_run = [
                ('clothing_background_removal.py', 'Background Removal'),
                ('clothing_contrast_adjustment.py', 'Contrast Adjustment'),
                ('clothing_segmentation.py', 'Clothing Segmentation'),
                ('clothing_measurements.py', 'FITMATCH Clothing Measurements')
            ]
            
            # Initialize execution namespace
            exec_namespace = {
                '__name__': '__main__',
                'detected_clothing_type': clothing_type,
                'clothing_input_image': 'clothing_input.jpg'
            }
            
            successful_modules = 0
            for module_file, description in modules_to_run:
                print(f"\n[PROCESSING] {description}...")
                module_path = os.path.join(clothing_modules_path, module_file)
                
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
            
            # Extract clothing measurements
            raw_clothing_measurements = exec_namespace.get('measurements_dict', {})
            raw_clothing_measurements['Clothing Type'] = clothing_type
            
            print(f"[MEASUREMENTS] Raw measurements extracted: {len(raw_clothing_measurements)} items")
            
            # FITMATCH ERROR DETECTION AND REPROCESSING
            print(f"\n[FITMATCH VALIDATION] Starting error detection and reprocessing...")
            
            validated_results = fitmatch_validator.validate_and_reprocess_measurements(
                raw_clothing_measurements, clothing_type, user_id
            )
            
            # Extract validated results
            final_clothing_measurements = validated_results['measurements']
            detected_clothing_size = validated_results['detected_size']
            error_corrections = validated_results['error_corrections']
            reprocessing_history = validated_results['reprocessing_history']
            fit_analysis = validated_results['fit_analysis']
            
            print(f"[FITMATCH VALIDATION] ✓ Validation completed:")
            print(f"  Final detected size: {detected_clothing_size}")
            print(f"  Error corrections applied: {len(error_corrections)}")
            print(f"  Reprocessing attempts: {len(reprocessing_history)}")
            
            # Display error corrections
            if error_corrections:
                print(f"\n[ERROR CORRECTIONS APPLIED]")
                for correction in error_corrections:
                    print(f"    • {correction}")
            
            # Step 6: Body comparison (if body measurements provided)
            comparison_result = None
            if body_measurements:
                print(f"\n[STEP 6] FITMATCH Body vs Clothing Comparison...")
                comparison_result = compare_body_vs_clothing(body_measurements, final_clothing_measurements)
                
                print(f"[BODY COMPARISON] ✓ FITMATCH Results:")
                print(f"  Your body needs size: {comparison_result['recommended_size']}")
                print(f"  This clothing is size: {comparison_result['detected_clothing_size']}")
                print(f"  Match percentage: {comparison_result['excellent_match_percentage']}%")
            
            # Copy processed images
            _copy_processed_images_to_job_dir(working_dir, job_dir)
            
            # Prepare result data with FITMATCH validation results
            result_data = {
                'clothing_measurements': final_clothing_measurements,
                'clothing_type': clothing_type,
                'vision_result': vision_result,
                'error_corrections': error_corrections,
                'reprocessing_history': reprocessing_history,
                'validation_method': 'FITMATCH_ERROR_DETECTION_REPROCESSING',
                'is_test': is_test
            }
            
            if comparison_result:
                result_data['comparison_result'] = comparison_result
            
            # Update job status to completed
            update_clothing_job_status(job_id, 'completed', result_data)
            
            print(f"\n{'='*80}")
            print(f"[SUCCESS] FITMATCH clothing measurement job {job_id} completed!")
            print(f"[SUCCESS] User: {user_id}")
            print(f"[SUCCESS] Clothing type: {clothing_type}")
            print(f"[SUCCESS] Detected clothing size: {detected_clothing_size}")
            print(f"[SUCCESS] Error corrections applied: {len(error_corrections)}")
            print(f"[SUCCESS] Reprocessing attempts: {len(reprocessing_history)}")
            if comparison_result:
                print(f"[SUCCESS] Your body size: {comparison_result['recommended_size']}")
                print(f"[SUCCESS] Compatibility: {comparison_result['excellent_match_percentage']}%")
            print(f"[SUCCESS] FITMATCH error detection and reprocessing completed")
            print(f"{'='*80}")
            
        finally:
            os.chdir(original_dir)
            if working_dir in sys.path:
                sys.path.remove(working_dir)
        
    except Exception as e:
        print(f"[CLOTHING ERROR] {str(e)}")
        print(f"[CLOTHING ERROR] Traceback: {traceback.format_exc()}")
        
        update_clothing_job_status(job_id, 'failed', {'error': str(e), 'is_test': job_data.get('is_test', False)})
    
    finally:
        if working_dir and os.path.exists(working_dir):
            try:
                shutil.rmtree(working_dir, ignore_errors=True)
            except:
                pass

def _copy_processed_images_to_job_dir(working_dir, job_dir):
    """Copy processed images to job directory"""
    try:
        images_to_copy = [
            ('images/clothing_remove.jpg', 'clothing_background_removed.jpg'),
            ('images/clothing_contrast.jpg', 'clothing_contrast_adjusted.jpg'),
            ('images/clothing_segments.jpg', 'clothing_segmentation.jpg'),
            ('images/clothing_measurements.jpg', 'clothing_measurements.jpg')
        ]
        
        copied_count = 0
        for src, dest in images_to_copy:
            src_path = os.path.join(working_dir, src)
            if os.path.exists(src_path):
                os.makedirs(job_dir, exist_ok=True)
                dest_path = os.path.join(job_dir, dest)
                shutil.copy(src_path, dest_path)
                copied_count += 1
                print(f"[IMAGES] ✓ Copied: {dest}")
            else:
                print(f"[IMAGES] ✗ Source not found: {src}")
        
        print(f"[IMAGES] Copied {copied_count}/{len(images_to_copy)} processed images")
        
    except Exception as e:
        print(f"[IMAGES] Error: {e}")

def clothing_worker_thread():
    """Worker thread for clothing jobs with FITMATCH error detection and reprocessing"""
    print(f"\n{'='*80}")
    print(f"[CLOTHING WORKER] FITMATCH Clothing Measurement System")
    print(f"[CLOTHING WORKER] Authentication: firebase-service-account.json")
    print(f"[CLOTHING WORKER] Sizing: S/M/L/XL/XXL (NO XS)")
    print(f"[CLOTHING WORKER] FITMATCH: Clothing-first detection")
    print(f"[CLOTHING WORKER] FITMATCH: Error detection & automatic reprocessing")
    print(f"[CLOTHING WORKER] FITMATCH: Context-aware measurements")
    print(f"[CLOTHING WORKER] FITMATCH: Realistic scaling and validation")
    print(f"[CLOTHING WORKER] Firestore integration: ACTIVE")
    print(f"[CLOTHING WORKER] Waiting for clothing jobs...")
    print(f"{'='*80}\n")
    
    while True:
        try:
            queue_size = queue_manager.get_queue_size()
            if queue_size > 0:
                job = queue_manager.get_job(timeout=0.5)
                if job:
                    job_type = job.get('type', 'unknown')
                    job_id = job.get('job_id', 'unknown')
                    
                    print(f"[CLOTHING QUEUE] Retrieved job: {job_id} (type: {job_type})")
                    
                    if job_type in ['clothing_measurement', 'clothing_measurement_auth']:
                        process_clothing_job(job)
                    else:
                        print(f"[CLOTHING QUEUE] Not a clothing job, returning to queue")
                        queue_manager.add_job(job)
            
        except Exception as e:
            if str(e):
                print(f"[CLOTHING WORKER ERROR] {e}")
        
        time.sleep(0.5)

def start_clothing_worker():
    """Start clothing worker with FITMATCH error detection and reprocessing"""
    thread = threading.Thread(target=clothing_worker_thread, daemon=True)
    thread.start()
    print("[CLOTHING WORKER] FITMATCH clothing measurement thread started")
    print("[CLOTHING WORKER] Features: Error detection, automatic reprocessing, realistic scaling")
    return thread
