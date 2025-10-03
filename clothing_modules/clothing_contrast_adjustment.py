# clothing_modules/clothing_contrast_adjustment.py

import cv2
import numpy as np
import os

# Following your decrease_contrast.py pattern
clothing_input_image = 'clothing_input.jpg'

try:
    print("[CLOTHING CONTRAST] Starting clothing contrast adjustment...")
    
    # Try to read background-removed image first, then fallback
    input_paths = ['images/clothing_remove.jpg', clothing_input_image]
    input_image = None
    
    for path in input_paths:
        if os.path.exists(path):
            input_image = cv2.imread(path)
            if input_image is not None:
                print(f"[CLOTHING CONTRAST] Using input: {path}")
                break
    
    if input_image is None:
        print(f"[CLOTHING CONTRAST] ✗ Could not load any input image")
    else:
        # Apply contrast adjustment (following your pattern)
        adjusted = cv2.convertScaleAbs(input_image, alpha=1.1, beta=5)
        
        # Save adjusted image
        os.makedirs('images', exist_ok=True)
        output_path = 'images/clothing_contrast.jpg'
        cv2.imwrite(output_path, adjusted)
        
        print(f"[CLOTHING CONTRAST] ✓ Contrast adjusted successfully: {output_path}")

except Exception as e:
    print(f"[CLOTHING CONTRAST] ✗ Error: {str(e)}")
    import traceback
    print(f"[CLOTHING CONTRAST] Traceback: {traceback.format_exc()}")
