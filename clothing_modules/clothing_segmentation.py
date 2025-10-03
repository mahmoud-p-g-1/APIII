# clothing_modules/clothing_segmentation.py

import cv2
import numpy as np
import os
import json

# Following your body_segments.py pattern
clothing_input_image = 'clothing_input.jpg'

try:
    print("[CLOTHING SEGMENTATION] Starting clothing segmentation...")
    
    # Try to read processed images first, then fallback
    input_paths = ['images/clothing_contrast.jpg', 'images/clothing_remove.jpg', clothing_input_image]
    input_image = None
    
    for path in input_paths:
        if os.path.exists(path):
            input_image = cv2.imread(path)
            if input_image is not None:
                print(f"[CLOTHING SEGMENTATION] Using input: {path}")
                break
    
    if input_image is None:
        print(f"[CLOTHING SEGMENTATION] ✗ Could not load any input image")
    else:
        # Convert to grayscale for segmentation
        gray = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
        
        # Apply edge detection (following body_segments.py approach)
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Get largest contour (main clothing item)
            main_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(main_contour)
            
            # Create segmented visualization
            segmented_image = input_image.copy()
            
            # Draw main clothing boundary
            cv2.rectangle(segmented_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(segmented_image, "Main Clothing", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Create clothing zones (similar to body zones)
            chest_zone = (x, y, w, int(h * 0.35))  # Top 35% for chest
            waist_zone = (x, y + int(h * 0.35), w, int(h * 0.30))  # Middle 30% for waist
            hip_zone = (x, y + int(h * 0.65), w, int(h * 0.35))   # Bottom 35% for hip/leg
            
            # Draw zones
            zones = [
                (chest_zone, "Chest", (255, 0, 0)),
                (waist_zone, "Waist", (0, 255, 255)),
                (hip_zone, "Hip/Leg", (0, 0, 255))
            ]
            
            for zone, name, color in zones:
                zone_x, zone_y, zone_w, zone_h = zone
                cv2.rectangle(segmented_image, (zone_x, zone_y), (zone_x + zone_w, zone_y + zone_h), color, 1)
                cv2.putText(segmented_image, name, (zone_x, zone_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            # Save segmented image
            os.makedirs('images', exist_ok=True)
            output_path = 'images/clothing_segments.jpg'
            cv2.imwrite(output_path, segmented_image)
            
            # Store segmentation data for measurements (FIXED: Convert numpy array to list)
            clothing_segments = {
                'main_contour': main_contour.tolist(),  # Convert to list for JSON serialization
                'bounding_rect': (int(x), int(y), int(w), int(h)),  # Ensure integers
                'chest_zone': (int(chest_zone[0]), int(chest_zone[1]), int(chest_zone[2]), int(chest_zone[3])),
                'waist_zone': (int(waist_zone[0]), int(waist_zone[1]), int(waist_zone[2]), int(waist_zone[3])),
                'hip_zone': (int(hip_zone[0]), int(hip_zone[1]), int(hip_zone[2]), int(hip_zone[3]))
            }
            
            # Save segmentation data for measurements module
            with open('images/segmentation_data.json', 'w') as f:
                json.dump(clothing_segments, f, indent=2)
            
            print(f"[CLOTHING SEGMENTATION] ✓ Segmentation completed: {output_path}")
            print(f"[CLOTHING SEGMENTATION] ✓ Segmentation data saved: images/segmentation_data.json")
            
        else:
            print(f"[CLOTHING SEGMENTATION] ✗ No clothing contours found")

except Exception as e:
    print(f"[CLOTHING SEGMENTATION] ✗ Error: {str(e)}")
    import traceback
    print(f"[CLOTHING SEGMENTATION] Traceback: {traceback.format_exc()}")
