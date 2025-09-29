# runprogram.py

# Import configuration and height measurement first
from measurement_config import MeasurementConfig
from height_measurement import HeightMeasurement
from photos_height import front_input_image, side_input_image, USE_AUTOMATIC_HEIGHT, MANUAL_HEIGHT

# Configure height measurement
if USE_AUTOMATIC_HEIGHT:
    config = MeasurementConfig()
    config.set_height_mode("manual") 
    
    height_measurer = HeightMeasurement(front_input_image, side_input_image)
    detected_height = height_measurer.measure_height()
    
    if detected_height and 90 <= detected_height <= 220:
        height = detected_height
        print(f"Using detected height: {height:.1f} cm")
    else:
        print(f"Invalid height detected. Please enter manually.")
        while True:
            try:
                height = float(input("Enter height in cm (90-220): "))
                if 90 <= height <= 220:
                    break
                else:
                    print("Height must be between 90 and 220 cm")
            except:
                print("Please enter a valid number")
        print(f"Using manual height: {height} cm")
else:
    height = MANUAL_HEIGHT
    print(f"Using manual height: {height} cm")

# Update photos_height module with the determined height
import photos_height
photos_height.height = height

# Now import the rest of the modules
from medipie_cooordinates import *
from decrease_contrast import *
from remove_backround import *
from add_silhouette import *
from body_segments import *
from get_height import *

# Import measurement validation and confidence modules
from measurement_validator import MeasurementValidator
from measurement_calculator import MeasurementCalculator
from measurement_confidence import MeasurementConfidence

# Initialize validators and calculators
validator = MeasurementValidator(height)
calc = MeasurementCalculator()

# Enhanced measurement calculations
print("\n--- Enhanced Measurements with Validation ---")

# Create enhanced measurements dictionary
enhanced_measurements = {}

# Leg measurements with improved calculations
if len(front_cm) > 5 and len(side_cm) > 3:
    enhanced_measurements['Left Calf Circumference'] = calc.calculate_limb_circumference(
        front_cm[0], side_cm[0] if len(side_cm) > 0 else front_cm[0], 'calf')
    enhanced_measurements['Right Calf Circumference'] = calc.calculate_limb_circumference(
        front_cm[4], side_cm[2] if len(side_cm) > 2 else front_cm[4], 'calf')
    enhanced_measurements['Left Thigh Circumference'] = calc.calculate_limb_circumference(
        front_cm[1], side_cm[1] if len(side_cm) > 1 else front_cm[1], 'thigh')
    enhanced_measurements['Right Thigh Circumference'] = calc.calculate_limb_circumference(
        front_cm[5], side_cm[3] if len(side_cm) > 3 else front_cm[5], 'thigh')

# Arm measurements
if len(front_cm) > 7:
    enhanced_measurements['Left Lower Arm Circumference'] = calc.calculate_circumference_from_diameter(
        front_cm[3], 'forearm')
    enhanced_measurements['Left Upper Arm Circumference'] = calc.calculate_circumference_from_diameter(
        front_cm[2], 'upper_arm')
    enhanced_measurements['Right Lower Arm Circumference'] = calc.calculate_circumference_from_diameter(
        front_cm[7], 'forearm')
    enhanced_measurements['Right Upper Arm Circumference'] = calc.calculate_circumference_from_diameter(
        front_cm[6], 'upper_arm')
    
    # Improved arm length calculation
    arm_length = (front_cm[6] + front_cm[7]) * 0.8  # Adjusted multiplier for realistic length
    enhanced_measurements['Right Arm Length'] = arm_length

# Torso measurements
if len(front_cm) > 8 and len(side_cm) > 4:
    enhanced_measurements['Waist Circumference'] = calc.calculate_torso_circumference(
        front_cm[8], side_cm[4] if len(side_cm) > 4 else front_cm[8], 'waist')

if len(front_linear_cm) > 1 and len(side_linear_cm) > 1:
    enhanced_measurements['Hip Circumference'] = calc.calculate_torso_circumference(
        front_linear_cm[1], side_linear_cm[1] if len(side_linear_cm) > 1 else front_linear_cm[1], 'hip')

if len(front_linear_cm) > 0:
    enhanced_measurements['Shoulder Breadth'] = front_linear_cm[0]  # Direct linear measurement

# Additional measurements
if len(front_cm) > 15 and len(side_cm) > 7:
    enhanced_measurements['Head Circumference'] = calc.calculate_circumference_from_ellipse(
        front_cm[15], side_cm[7])
    enhanced_measurements['Neck Circumference'] = calc.calculate_torso_circumference(
        front_cm[9], side_cm[5], 'neck')
    enhanced_measurements['Chest Circumference'] = calc.calculate_torso_circumference(
        front_cm[10], side_cm[6], 'chest')
    enhanced_measurements['Right Wrist Circumference'] = calc.calculate_circumference_from_diameter(
        front_cm[11], 'wrist')
    enhanced_measurements['Right Bicep Circumference'] = calc.calculate_circumference_from_diameter(
        front_cm[12], 'bicep')
    enhanced_measurements['Right Forearm Circumference'] = calc.calculate_circumference_from_diameter(
        front_cm[13], 'forearm')
    enhanced_measurements['Left Ankle Circumference'] = calc.calculate_circumference_from_diameter(
        front_cm[14], 'ankle')

# Linear measurements
if len(front_linear_cm) > 2:
    enhanced_measurements['Shoulder to Crotch Height'] = front_linear_cm[2]
if len(front_linear_cm) > 3:
    enhanced_measurements['Right Foot Length'] = front_linear_cm[3]
if len(front_linear_cm) > 4:
    enhanced_measurements['Right Foot Width'] = front_linear_cm[4]
if len(side_linear_cm) > 2:
    enhanced_measurements['Back to Shoulder'] = side_linear_cm[2]

# Calculate inside leg height (inseam)
inside_leg_height = (abs(left_heel[1] - left_hip[1]) * height) / height_front
enhanced_measurements['Inside Leg Height'] = inside_leg_height

# Add height to measurements
enhanced_measurements['Height'] = height

# Validate and correct measurements
print("\n--- Validating Measurements ---")
corrected_measurements = validator.validate_all_measurements(enhanced_measurements)

# Calculate confidence scores
print("\n--- Measurement Confidence Analysis ---")
confidence_analyzer = MeasurementConfidence(height)
confidence_scores = confidence_analyzer.calculate_confidence_score(corrected_measurements)

print("\n--- Measurement Confidence Scores ---")
for measurement, score in confidence_scores.items():
    status = "✓" if score >= 80 else "⚠" if score >= 60 else "✗"
    print(f"{status} {measurement}: {score:.1f}%")

overall_confidence = confidence_analyzer.get_overall_confidence(confidence_scores)
print(f"\nOverall Measurement Confidence: {overall_confidence:.1f}%")

# Get recommendations
recommendations = confidence_analyzer.get_recommendations(confidence_scores)
if recommendations:
    print("\n--- Recommendations ---")
    for rec in recommendations:
        print(rec)

# Calculate additional metrics
if isinstance(corrected_measurements.get('Waist Circumference'), (int, float)) and \
   isinstance(corrected_measurements.get('Neck Circumference'), (int, float)):
    body_fat = calc.estimate_body_fat_percentage(
        corrected_measurements['Waist Circumference'],
        corrected_measurements['Neck Circumference'],
        height,
        corrected_measurements.get('Hip Circumference', None)
    )
    print(f"\n--- Additional Metrics ---")
    print(f"Estimated Body Fat Percentage: {body_fat:.1f}%")
    
    # Calculate BMI if weight is available (you can add weight input if needed)
    # bmi = weight / ((height/100) ** 2)

# Print final validated measurements
print("\n--- Final Validated Measurements Report ---")
print("=" * 60)
for key, value in corrected_measurements.items():
    if isinstance(value, (int, float)):
        print(f"{key}: {value:.2f} cm")
    else:
        print(f"{key}: {value}")
print("=" * 60)

# Save measurements to file
import json
import datetime

# Create measurements report
report = {
    "timestamp": datetime.datetime.now().isoformat(),
    "height_detection_method": "automatic" if USE_AUTOMATIC_HEIGHT else "manual",
    "measurements": {k: float(v) if isinstance(v, (int, float)) else v 
                    for k, v in corrected_measurements.items()},
    "confidence_scores": confidence_scores,
    "overall_confidence": overall_confidence,
    "body_fat_percentage": body_fat if 'body_fat' in locals() else None
}

# Save to JSON file
with open('measurements_report.json', 'w') as f:
    json.dump(report, f, indent=2)
    print("\nMeasurements saved to 'measurements_report.json'")

# Create a summary CSV for easy viewing
import csv

csv_filename = f"measurements_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
with open(csv_filename, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Measurement', 'Value (cm)', 'Confidence (%)'])
    for key, value in corrected_measurements.items():
        if isinstance(value, (int, float)):
            confidence = confidence_scores.get(key, 'N/A')
            if isinstance(confidence, float):
                writer.writerow([key, f"{value:.2f}", f"{confidence:.1f}"])
            else:
                writer.writerow([key, f"{value:.2f}", confidence])
    print(f"CSV report saved to '{csv_filename}'")
