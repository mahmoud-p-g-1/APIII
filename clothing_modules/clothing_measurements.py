# clothing_modules/clothing_measurements.py

import cv2
import numpy as np
import os
import json
import math

# Professional clothing measurement standards (based on your URLs and clothh.xlsx)
PROFESSIONAL_CLOTHING_STANDARDS = {
    'top': {
        'S': {
            'chest_circumference': (75, 85),
            'chest_width_flat': (37.5, 42.5),  # Half circumference when laid flat
            'shoulder_width': (37, 39),
            'total_length': (58, 68),
            'waist_circumference': (65, 75)
        },
        'M': {
            'chest_circumference': (85, 95),
            'chest_width_flat': (42.5, 47.5),
            'shoulder_width': (40, 42),
            'total_length': (62, 72),
            'waist_circumference': (75, 85)
        },
        'L': {
            'chest_circumference': (95, 105),
            'chest_width_flat': (47.5, 52.5),
            'shoulder_width': (43, 45),
            'total_length': (66, 76),
            'waist_circumference': (85, 95)
        },
        'XL': {
            'chest_circumference': (105, 115),
            'chest_width_flat': (52.5, 57.5),
            'shoulder_width': (46, 48),
            'total_length': (70, 80),
            'waist_circumference': (95, 105)
        },
        'XXL': {
            'chest_circumference': (115, 130),
            'chest_width_flat': (57.5, 65.0),
            'shoulder_width': (49, 52),
            'total_length': (74, 84),
            'waist_circumference': (105, 120)
        }
    },
    'bottom': {
        'S': {
            'waist_circumference': (65, 75),
            'hip_circumference': (85, 95),
            'inseam_length': (70, 74),
            'total_length': (95, 105)
        },
        'M': {
            'waist_circumference': (75, 85),
            'hip_circumference': (95, 105),
            'inseam_length': (72, 76),
            'total_length': (97, 107)
        },
        'L': {
            'waist_circumference': (85, 95),
            'hip_circumference': (105, 115),
            'inseam_length': (74, 78),
            'total_length': (99, 109)
        },
        'XL': {
            'waist_circumference': (95, 105),
            'hip_circumference': (115, 125),
            'inseam_length': (76, 80),
            'total_length': (101, 111)
        },
        'XXL': {
            'waist_circumference': (105, 120),
            'hip_circumference': (125, 140),
            'inseam_length': (78, 82),
            'total_length': (103, 113)
        }
    }
}

def _professional_measurement_analysis(measurements, clothing_type):
    """Professional measurement analysis following your measurement_worker.py approach"""
    print(f"\n[PROFESSIONAL MEASUREMENT ANALYSIS] Analyzing {clothing_type} measurements...")
    
    if clothing_type not in PROFESSIONAL_CLOTHING_STANDARDS:
        raise ValueError(f"Professional standards not available for: {clothing_type}")
    
    standards = PROFESSIONAL_CLOTHING_STANDARDS[clothing_type]
    analysis_results = {}
    
    # Analyze each measurement against professional standards
    for measurement_name, measurement_value in measurements.items():
        if not isinstance(measurement_value, (int, float)) or measurement_value <= 0:
            continue
        
        measurement_analysis = {
            'value': measurement_value,
            'size_fits': {},
            'best_fit_size': None,
            'fit_quality': 'unknown'
        }
        
        # Check fit against each size
        for size, size_standards in standards.items():
            if measurement_name in size_standards:
                min_val, max_val = size_standards[measurement_name]
                
                if min_val <= measurement_value <= max_val:
                    fit_percentage = 100.0
                    fit_quality = 'perfect'
                elif measurement_value < min_val:
                    distance = min_val - measurement_value
                    fit_percentage = max(60.0, 100.0 - (distance / min_val * 100))
                    fit_quality = 'loose' if fit_percentage > 80 else 'very_loose'
                else:
                    distance = measurement_value - max_val
                    fit_percentage = max(60.0, 100.0 - (distance / max_val * 100))
                    fit_quality = 'tight' if fit_percentage > 80 else 'very_tight'
                
                measurement_analysis['size_fits'][size] = {
                    'fit_percentage': fit_percentage,
                    'fit_quality': fit_quality,
                    'range': (min_val, max_val)
                }
        
        # Find best fitting size for this measurement
        if measurement_analysis['size_fits']:
            best_size = max(measurement_analysis['size_fits'].keys(), 
                          key=lambda s: measurement_analysis['size_fits'][s]['fit_percentage'])
            measurement_analysis['best_fit_size'] = best_size
            measurement_analysis['fit_quality'] = measurement_analysis['size_fits'][best_size]['fit_quality']
        
        analysis_results[measurement_name] = measurement_analysis
        
        print(f"[PROFESSIONAL ANALYSIS] {measurement_name}: {measurement_value:.1f}cm")
        for size, fit_data in measurement_analysis['size_fits'].items():
            print(f"  Size {size}: {fit_data['fit_percentage']:.1f}% ({fit_data['fit_quality']})")
    
    return analysis_results

def _calculate_professional_size_confidence(analysis_results, clothing_type):
    """Calculate professional size confidence (0-100%) like your measurement system"""
    print(f"\n[PROFESSIONAL SIZE CONFIDENCE] Calculating confidence scores...")
    
    if clothing_type == 'top':
        # Weight measurements by importance (like your measurement_worker.py)
        measurement_weights = {
            'chest_circumference': 0.40,    # 40% - most important
            'chest_width_flat': 0.30,       # 30% - critical for fit
            'shoulder_width': 0.20,         # 20% - important for drape
            'total_length': 0.10            # 10% - style preference
        }
    elif clothing_type == 'bottom':
        measurement_weights = {
            'waist_circumference': 0.35,    # 35% - most important
            'hip_circumference': 0.30,      # 30% - critical for fit
            'inseam_length': 0.25,          # 25% - important for length
            'total_length': 0.10            # 10% - overall length
        }
    else:
        # Equal weighting for unknown types
        measurement_weights = {name: 1.0/len(analysis_results) for name in analysis_results.keys()}
    
    size_confidence_scores = {}
    all_sizes = ['S', 'M', 'L', 'XL', 'XXL']
    
    for size in all_sizes:
        weighted_confidence = 0
        total_weight_used = 0
        
        for measurement_name, weight in measurement_weights.items():
            if measurement_name in analysis_results:
                measurement_data = analysis_results[measurement_name]
                if size in measurement_data['size_fits']:
                    fit_percentage = measurement_data['size_fits'][size]['fit_percentage']
                    weighted_confidence += fit_percentage * weight
                    total_weight_used += weight
        
        if total_weight_used > 0:
            # Normalize to 0-100% range (FIXED: no more 9744.6%)
            final_confidence = (weighted_confidence / total_weight_used)
            size_confidence_scores[size] = min(100.0, max(0.0, final_confidence))
        else:
            size_confidence_scores[size] = 0.0
        
        print(f"[PROFESSIONAL CONFIDENCE] Size {size}: {size_confidence_scores[size]:.1f}%")
    
    return size_confidence_scores

def _determine_professional_size(size_confidence_scores):
    """Determine size based on highest confidence (like your measurement approach)"""
    if not size_confidence_scores:
        raise ValueError("No confidence scores available for professional size determination")
    
    # Find size with highest confidence
    best_size = max(size_confidence_scores.keys(), key=size_confidence_scores.get)
    best_confidence = size_confidence_scores[best_size]
    
    print(f"\n[PROFESSIONAL SIZE DETERMINATION]")
    print(f"  Best size: {best_size}")
    print(f"  Confidence: {best_confidence:.1f}%")
    
    return best_size, best_confidence

def _generate_detailed_fit_analysis(analysis_results, detected_size, clothing_type):
    """Generate detailed fit analysis like your measurement_worker.py"""
    print(f"\n[DETAILED FIT ANALYSIS] Generating professional fit analysis...")
    
    fit_analysis = []
    fit_analysis.append("=== PROFESSIONAL CLOTHING FIT ANALYSIS ===")
    fit_analysis.append(f"Garment Type: {clothing_type.upper()}")
    fit_analysis.append(f"Detected Clothing Size: {detected_size}")
    fit_analysis.append("")
    
    if clothing_type == 'top':
        # Analyze key measurements for tops
        key_measurements = [
            ('chest_circumference', 'CHEST'),
            ('shoulder_width', 'SHOULDERS'),
            ('total_length', 'LENGTH')
        ]
        
        for measurement_name, display_name in key_measurements:
            if measurement_name in analysis_results:
                measurement_data = analysis_results[measurement_name]
                if detected_size in measurement_data['size_fits']:
                    fit_data = measurement_data['size_fits'][detected_size]
                    fit_quality = fit_data['fit_quality']
                    fit_percentage = fit_data['fit_percentage']
                    
                    if fit_quality == 'perfect':
                        fit_analysis.append(f"✓ {display_name}: PERFECT FIT ({fit_percentage:.1f}%)")
                    elif fit_quality == 'loose':
                        fit_analysis.append(f"✓ {display_name}: COMFORTABLE FIT ({fit_percentage:.1f}% - slightly loose)")
                    elif fit_quality == 'tight':
                        fit_analysis.append(f"⚠ {display_name}: FITTED ({fit_percentage:.1f}% - slightly tight)")
                    elif fit_quality == 'very_loose':
                        fit_analysis.append(f"⚠ {display_name}: TOO LOOSE ({fit_percentage:.1f}%)")
                    elif fit_quality == 'very_tight':
                        fit_analysis.append(f"✗ {display_name}: TOO TIGHT ({fit_percentage:.1f}%)")
    
    elif clothing_type == 'bottom':
        # Analyze key measurements for bottoms
        key_measurements = [
            ('waist_circumference', 'WAIST'),
            ('hip_circumference', 'HIPS'),
            ('inseam_length', 'INSEAM LENGTH')
        ]
        
        for measurement_name, display_name in key_measurements:
            if measurement_name in analysis_results:
                measurement_data = analysis_results[measurement_name]
                if detected_size in measurement_data['size_fits']:
                    fit_data = measurement_data['size_fits'][detected_size]
                    fit_quality = fit_data['fit_quality']
                    fit_percentage = fit_data['fit_percentage']
                    
                    if fit_quality == 'perfect':
                        fit_analysis.append(f"✓ {display_name}: PERFECT FIT ({fit_percentage:.1f}%)")
                    elif fit_quality == 'loose':
                        fit_analysis.append(f"✓ {display_name}: COMFORTABLE FIT ({fit_percentage:.1f}%)")
                    elif fit_quality == 'tight':
                        fit_analysis.append(f"⚠ {display_name}: FITTED ({fit_percentage:.1f}%)")
                    else:
                        fit_analysis.append(f"⚠ {display_name}: {fit_quality.upper()} ({fit_percentage:.1f}%)")
    
    fit_analysis.append("")
    fit_analysis.append("--- PROFESSIONAL RECOMMENDATION ---")
    fit_analysis.append(f"Detected Size: {detected_size}")
    fit_analysis.append(f"Analysis Method: Professional garment measurement standards")
    fit_analysis.append(f"Standards Source: Professional sizing charts + clothh.xlsx data")
    
    return fit_analysis

# Main measurement execution
clothing_input_image = 'clothing_input.jpg'
detected_clothing_type = globals().get('detected_clothing_type', 'top')

try:
    print("[CLOTHING MEASUREMENTS] Starting PROFESSIONAL clothing measurement analysis...")
    print(f"[CLOTHING MEASUREMENTS] Following measurement_worker.py professional approach")
    print(f"[CLOTHING MEASUREMENTS] Garment type: {detected_clothing_type}")
    
    # Read and process image (same as before)
    input_paths = ['images/clothing_segments.jpg', 'images/clothing_contrast.jpg', 'images/clothing_remove.jpg', clothing_input_image]
    input_image = None
    
    for path in input_paths:
        if os.path.exists(path):
            input_image = cv2.imread(path)
            if input_image is not None:
                print(f"[CLOTHING MEASUREMENTS] Using: {path}")
                break
    
    if input_image is None:
        raise ValueError("No valid input image for professional analysis")
    
    # Find clothing contours
    gray = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        raise ValueError("No clothing contours detected")
    
    main_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(main_contour)
    
    print(f"[PROFESSIONAL MEASUREMENT] Garment dimensions: {w}px × {h}px")
    
    # PROFESSIONAL SCALING (following your measurement_worker.py approach)
    if detected_clothing_type == 'top':
        # Use professional t-shirt scaling
        # Average M size t-shirt: chest width flat = 45cm, length = 67cm
        reference_chest_width = 45.0  # M size reference
        reference_length = 67.0       # M size reference
        
        # Calculate scale factors
        width_scale = reference_chest_width / w
        height_scale = reference_length / h
        
        # Use average scale (like your measurement system)
        pixel_to_cm_ratio = (width_scale + height_scale) / 2
        
        print(f"[PROFESSIONAL SCALING] Width scale: {width_scale:.6f}")
        print(f"[PROFESSIONAL SCALING] Height scale: {height_scale:.6f}")
        print(f"[PROFESSIONAL SCALING] Average scale: {pixel_to_cm_ratio:.6f}")
        
        # Calculate professional measurements
        chest_width_flat = (w * 0.95) * pixel_to_cm_ratio  # 95% of width
        chest_circumference = chest_width_flat * 2          # Convert to full circumference
        shoulder_width = (w * 0.80) * pixel_to_cm_ratio    # 80% of width
        total_length = h * pixel_to_cm_ratio
        waist_circumference = chest_circumference * 0.90   # 90% of chest
        
        professional_measurements = {
            'chest_circumference': chest_circumference,
            'chest_width_flat': chest_width_flat,
            'shoulder_width': shoulder_width,
            'total_length': total_length,
            'waist_circumference': waist_circumference
        }
        
    elif detected_clothing_type == 'bottom':
        # Professional bottom scaling
        reference_hip_width = 50.0    # M size reference
        reference_length = 102.0      # M size reference
        
        width_scale = reference_hip_width / w
        height_scale = reference_length / h
        pixel_to_cm_ratio = (width_scale + height_scale) / 2
        
        # Calculate professional measurements
        hip_circumference = ((w * 0.95) * pixel_to_cm_ratio) * 2
        waist_circumference = ((w * 0.85) * pixel_to_cm_ratio) * 2
        inseam_length = (h * 0.75) * pixel_to_cm_ratio
        total_length = h * pixel_to_cm_ratio
        
        professional_measurements = {
            'waist_circumference': waist_circumference,
            'hip_circumference': hip_circumference,
            'inseam_length': inseam_length,
            'total_length': total_length
        }
    
    else:
        raise ValueError(f"Professional analysis not available for: {detected_clothing_type}")
    
    print(f"[PROFESSIONAL MEASUREMENTS] Calculated measurements:")
    for name, value in professional_measurements.items():
        print(f"  {name}: {value:.1f}cm")
    
    # PROFESSIONAL ANALYSIS (following your measurement_worker.py approach)
    analysis_results = _professional_measurement_analysis(professional_measurements, detected_clothing_type)
    
    # PROFESSIONAL SIZE CONFIDENCE (0-100% like your system)
    size_confidence_scores = _calculate_professional_size_confidence(analysis_results, detected_clothing_type)
    
    # DETERMINE PROFESSIONAL SIZE
    detected_size, size_confidence = _determine_professional_size(size_confidence_scores)
    
    # DETAILED FIT ANALYSIS (like your measurement_worker.py)
    detailed_fit_analysis = _generate_detailed_fit_analysis(analysis_results, detected_size, detected_clothing_type)
    
    # Create final measurements dictionary (following your format)
    measurements_dict = {
        'Clothing Type': detected_clothing_type,
        'Detected Clothing Size': detected_size,
        'Size Confidence': f"{size_confidence:.1f}%",  # FIXED: proper 0-100% range
        'Professional Analysis Method': 'MEASUREMENT_DRIVEN_PROFESSIONAL',
        'Detailed Fit Analysis': detailed_fit_analysis
    }
    
    # Add garment-specific measurements
    for measurement_name, measurement_value in professional_measurements.items():
        display_name = measurement_name.replace('_', ' ').title()
        measurements_dict[display_name] = round(measurement_value, 1)
    
    # Add size confidence breakdown
    measurements_dict['Size Confidence Breakdown'] = {}
    for size, confidence in size_confidence_scores.items():
        measurements_dict['Size Confidence Breakdown'][f'Size_{size}_Confidence'] = f"{confidence:.1f}%"
    
    # Professional visualization
    measurement_vis = input_image.copy()
    cv2.rectangle(measurement_vis, (x, y), (x + w, y + h), (0, 255, 0), 3)
    
    # Professional annotations
    text_lines = [
        f"PROFESSIONAL: {detected_clothing_type.upper()} - SIZE {detected_size}",
        f"Confidence: {size_confidence:.1f}% (Professional Standards)"
    ]
    
    if detected_clothing_type == 'top':
        text_lines.extend([
            f"Chest: {professional_measurements['chest_circumference']:.1f}cm",
            f"Shoulder: {professional_measurements['shoulder_width']:.1f}cm",
            f"Length: {professional_measurements['total_length']:.1f}cm"
        ])
    elif detected_clothing_type == 'bottom':
        text_lines.extend([
            f"Waist: {professional_measurements['waist_circumference']:.1f}cm",
            f"Hip: {professional_measurements['hip_circumference']:.1f}cm",
            f"Inseam: {professional_measurements['inseam_length']:.1f}cm"
        ])
    
    # Draw professional annotations
    for i, text in enumerate(text_lines):
        color = (0, 255, 255) if i < 2 else (255, 255, 255)
        thickness = 2 if i < 2 else 1
        cv2.putText(measurement_vis, text, (10, 35 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, thickness)
    
    cv2.imwrite('images/clothing_measurements.jpg', measurement_vis)
    
    print(f"\n[CLOTHING MEASUREMENTS] ✓ PROFESSIONAL analysis completed:")
    print(f"  Detected size: {detected_size}")
    print(f"  Confidence: {size_confidence:.1f}% (proper 0-100% range)")
    print(f"  Method: Professional garment measurement standards")
    
    # Display detailed fit analysis
    print(f"\n[DETAILED FIT ANALYSIS]")
    for line in detailed_fit_analysis:
        print(f"  {line}")

except Exception as e:
    print(f"[CLOTHING MEASUREMENTS] ✗ Professional analysis failed: {str(e)}")
    import traceback
    print(f"[CLOTHING MEASUREMENTS] Traceback: {traceback.format_exc()}")
    
    # Create error measurements
    measurements_dict = {
        'Clothing Type': detected_clothing_type,
        'Analysis Status': 'FAILED',
        'Error': str(e),
        'Professional_Note': 'Professional analysis failed - manual review required'
    }
