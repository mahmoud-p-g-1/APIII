# clothing_modules/clothing_background_removal.py

import cv2
import numpy as np
from rembg import remove
import os

# Following your remove_backround.py pattern
clothing_input_image = 'clothing_input.jpg'

try:
    print("[CLOTHING BG REMOVAL] Starting clothing background removal...")
    
    # Read input image
    if not os.path.exists(clothing_input_image):
        print(f"[CLOTHING BG REMOVAL] ✗ Input image not found: {clothing_input_image}")
    else:
        print(f"[CLOTHING BG REMOVAL] Processing: {clothing_input_image}")
        
        # Read image data
        with open(clothing_input_image, 'rb') as input_file:
            input_data = input_file.read()
        
        # Remove background using rembg (similar to your approach)
        output_data = remove(input_data)
        
        # Save processed image
        os.makedirs('images', exist_ok=True)
        output_path = 'images/clothing_remove.jpg'
        with open(output_path, 'wb') as output_file:
            output_file.write(output_data)
        
        print(f"[CLOTHING BG REMOVAL] ✓ Background removed successfully: {output_path}")

except Exception as e:
    print(f"[CLOTHING BG REMOVAL] ✗ Error: {str(e)}")
    import traceback
    print(f"[CLOTHING BG REMOVAL] Traceback: {traceback.format_exc()}")
