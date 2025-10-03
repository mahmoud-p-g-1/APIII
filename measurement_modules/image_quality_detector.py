# measurement_modules/image_quality_detector.py

import cv2
import numpy as np
import os
from typing import Dict

class ImageQualityDetector:
    """Smart image quality detector that only flags genuine issues and returns clean JSON"""
    
    def __init__(self):
        self.detected_issue = None
    
    def detect_all_issues(self, front_image_path: str, side_image_path: str) -> Dict:
        """Detect only genuine quality issues and return ONE primary issue in clean JSON format"""
        
        print(f"[IMAGE QUALITY] Analyzing image quality...")
        
        # Analyze both images for SEVERE issues only
        front_issue = self._analyze_image_for_severe_issues(front_image_path, "front")
        side_issue = self._analyze_image_for_severe_issues(side_image_path, "side")
        
        # Determine the PRIMARY issue (only return ONE issue type)
        primary_issue = self._determine_primary_issue(front_issue, side_issue)
        
        if primary_issue:
            result = {
                'has_issues': True,
                'issue_type': primary_issue['type'],
                'description': primary_issue['description'],
                'severity': primary_issue['severity'],
                'affected_images': primary_issue['affected_images']
            }
            print(f"[IMAGE QUALITY]  Primary issue detected: {primary_issue['type']}")
        else:
            result = {
                'has_issues': False,
                'issue_type': None,
                'description': 'Images are excellent quality',
                'severity': 'none',
                'affected_images': []
            }
            print(f"[IMAGE QUALITY] Images are excellent quality - no issues detected")
        
        return result
    
    def _analyze_image_for_severe_issues(self, image_path: str, image_type: str) -> Dict:
        """Analyze image for SEVERE issues only - very strict thresholds"""
        
        if not os.path.exists(image_path):
            return {
                'type': 'File Error',
                'has_issue': True,
                'severity': 'high',
                'description': f'{image_type} image file not found',
                'image': image_type
            }
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return {
                    'type': 'File Error',
                    'has_issue': True,
                    'severity': 'high',
                    'description': f'Cannot read {image_type} image file',
                    'image': image_type
                }
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            height, width = gray.shape
            
            # Check for SEVERE lighting issues ONLY (very strict)
            lighting_issue = self._check_severe_lighting_only(gray, image_type)
            if lighting_issue['has_issue']:
                return lighting_issue
            
            # Check for SEVERE positioning issues ONLY (very strict)
            positioning_issue = self._check_severe_positioning_only(image, gray, image_type)
            if positioning_issue['has_issue']:
                return positioning_issue
            
            # Check for SEVERE body detection issues ONLY (very strict)
            body_issue = self._check_severe_body_detection_only(gray, image_type)
            if body_issue['has_issue']:
                return body_issue
            
            # No issues found
            return {
                'type': 'No Issue',
                'has_issue': False,
                'severity': 'none',
                'description': f'{image_type} image is excellent quality',
                'image': image_type
            }
            
        except Exception as e:
            return {
                'type': 'Processing Error',
                'has_issue': True,
                'severity': 'medium',
                'description': f'Error processing {image_type} image',
                'image': image_type
            }
    
    def _check_severe_lighting_only(self, gray_image: np.ndarray, image_type: str) -> Dict:
        """Only flag EXTREMELY SEVERE lighting problems"""
        mean_brightness = np.mean(gray_image)
        
        # Only flag extreme cases - much stricter than before
        if mean_brightness < 15:  # Almost completely black
            return {
                'type': 'Lighting Issue Detected',
                'has_issue': True,
                'severity': 'high',
                'description': 'Image is extremely dark - increase lighting significantly',
                'image': image_type
            }
        elif mean_brightness > 250:  # Almost completely white
            return {
                'type': 'Lighting Issue Detected',
                'has_issue': True,
                'severity': 'high',
                'description': 'Image is severely overexposed - reduce lighting significantly',
                'image': image_type
            }
        
        return {
            'type': 'Lighting Issue Detected',
            'has_issue': False,
            'severity': 'none',
            'description': f'{image_type} image lighting is good',
            'image': image_type
        }
    
    def _check_severe_positioning_only(self, image: np.ndarray, gray_image: np.ndarray, image_type: str) -> Dict:
        """Only flag EXTREMELY SEVERE positioning problems"""
        height, width = gray_image.shape
        
        # Use edge detection to find subject
        edges = cv2.Canny(gray_image, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return {
                'type': 'Positioning Adjustment Needed',
                'has_issue': True,
                'severity': 'high',
                'description': 'No subject detected - check camera positioning',
                'image': image_type
            }
        
        # Find largest contour (person)
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Only flag EXTREME positioning issues - much stricter
        person_area_ratio = (w * h) / (width * height)
        
        if person_area_ratio < 0.01:  # Person extremely tiny (less than 1% of image)
            return {
                'type': 'Positioning Adjustment Needed',
                'has_issue': True,
                'severity': 'high',
                'description': 'Subject extremely far from camera - move much closer',
                'image': image_type
            }
        elif person_area_ratio > 0.99:  # Person takes up almost entire image
            return {
                'type': 'Positioning Adjustment Needed',
                'has_issue': True,
                'severity': 'medium',
                'description': 'Subject extremely close to camera - step back',
                'image': image_type
            }
        
        return {
            'type': 'Positioning Adjustment Needed',
            'has_issue': False,
            'severity': 'none',
            'description': f'{image_type} image positioning is good',
            'image': image_type
        }
    
    def _check_severe_body_detection_only(self, gray_image: np.ndarray, image_type: str) -> Dict:
        """Only flag EXTREMELY SEVERE body detection problems"""
        height, width = gray_image.shape
        
        # Use edge detection
        edges = cv2.Canny(gray_image, 30, 100)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return {
                'type': 'Full Body Not Detected',
                'has_issue': True,
                'severity': 'high',
                'description': 'No body outline detected in image',
                'image': image_type
            }
        
        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Only flag if EXTREMELY severely cropped - much stricter
        height_coverage = h / height
        
        if height_coverage < 0.15:  # Person covers less than 15% of image height (extremely cropped)
            return {
                'type': 'Full Body Not Detected',
                'has_issue': True,
                'severity': 'high',
                'description': 'Full body extremely cropped - show much more of the person',
                'image': image_type
            }
        
        return {
            'type': 'Full Body Not Detected',
            'has_issue': False,
            'severity': 'none',
            'description': f'{image_type} image shows body well',
            'image': image_type
        }
    
    def _determine_primary_issue(self, front_issue: Dict, side_issue: Dict) -> Dict:
        """Determine the PRIMARY issue to return (only ONE issue) with priority"""
        
        # Priority order: File Error > Lighting > Full Body > Positioning
        issue_priority = {
            'File Error': 4,
            'Lighting Issue Detected': 3,
            'Full Body Not Detected': 2,
            'Positioning Adjustment Needed': 1
        }
        
        issues_found = []
        
        if front_issue['has_issue']:
            issues_found.append(front_issue)
        
        if side_issue['has_issue']:
            # Only add if it's a different type or higher priority
            if not issues_found or side_issue['type'] != front_issue['type']:
                issues_found.append(side_issue)
        
        if not issues_found:
            return None
        
        # Find highest priority issue
        primary_issue = max(issues_found, key=lambda x: issue_priority.get(x['type'], 0))
        
        # Determine affected images
        affected_images = []
        if front_issue['has_issue'] and front_issue['type'] == primary_issue['type']:
            affected_images.append('front')
        if side_issue['has_issue'] and side_issue['type'] == primary_issue['type']:
            affected_images.append('side')
        
        return {
            'type': primary_issue['type'],
            'description': primary_issue['description'],
            'severity': primary_issue['severity'],
            'affected_images': affected_images
        }
