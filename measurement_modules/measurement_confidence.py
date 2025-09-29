# measurement_confidence.py

import numpy as np
from typing import Dict, List

class MeasurementConfidence:
    """Assess confidence in measurements based on various factors"""
    
    def __init__(self, height: float):
        self.height = height
        
    def calculate_confidence_score(self, measurements: Dict) -> Dict:
        """Calculate confidence scores for each measurement"""
        confidence_scores = {}
        
        for key, value in measurements.items():
            if isinstance(value, (int, float)) and value != "N/A":
                score = self.evaluate_measurement(key, value)
                confidence_scores[key] = score
        
        return confidence_scores
    
    def evaluate_measurement(self, measurement_name: str, value: float) -> float:
        """Evaluate confidence in a single measurement"""
        score = 100.0
        
        expected_ranges = {
            'Waist Circumference': (60, 120),
            'Chest Circumference': (75, 130),
            'Hip Circumference': (80, 130),
            'Neck Circumference': (30, 50),
            'Head Circumference': (50, 65),
            'Left Thigh Circumference': (40, 75),
            'Left Calf Circumference': (28, 50),
            'Right Wrist Circumference': (14, 22),
            'Right Bicep Circumference': (25, 45),
            'Right Forearm Circumference': (20, 35),
            'Left Ankle Circumference': (18, 30),
            'Shoulder Breadth': (35, 55),
        }
        
        if measurement_name in expected_ranges:
            min_val, max_val = expected_ranges[measurement_name]
            if value < min_val or value > max_val:
                if value < min_val:
                    deviation = (min_val - value) / min_val
                else:
                    deviation = (value - max_val) / max_val
                score -= min(50, deviation * 100)
        
        height_proportions = {
            'Waist Circumference': (0.38, 0.55),
            'Chest Circumference': (0.50, 0.70),
            'Hip Circumference': (0.50, 0.70),
            'Neck Circumference': (0.20, 0.28),
        }
        
        if measurement_name in height_proportions:
            min_ratio, max_ratio = height_proportions[measurement_name]
            ratio = value / self.height
            if not (min_ratio <= ratio <= max_ratio):
                score -= 20
        
        return max(0, min(100, score))
    
    def get_overall_confidence(self, confidence_scores: Dict) -> float:
        """Calculate overall measurement confidence"""
        if not confidence_scores:
            return 0
        
        scores = list(confidence_scores.values())
        return np.mean(scores)
    
    def get_recommendations(self, confidence_scores: Dict) -> List[str]:
        """Get recommendations for improving measurements"""
        recommendations = []
        
        low_confidence = {k: v for k, v in confidence_scores.items() if v < 70}
        
        if low_confidence:
            recommendations.append("The following measurements have low confidence and should be verified:")
            for measurement, score in low_confidence.items():
                recommendations.append(f"  - {measurement}: {score:.1f}% confidence")
        
        overall = self.get_overall_confidence(confidence_scores)
        if overall < 75:
            recommendations.append(f"\nOverall confidence is {overall:.1f}%. Consider:")
            recommendations.append("  - Ensuring proper lighting and contrast in photos")
            recommendations.append("  - Wearing fitted clothing for better body outline")
            recommendations.append("  - Standing straight with arms slightly away from body")
            recommendations.append("  - Taking photos from consistent distance (2-3 meters)")
        
        return recommendations
