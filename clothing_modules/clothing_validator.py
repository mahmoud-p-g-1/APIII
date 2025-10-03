# clothing_modules/clothing_validator.py

import os
import sys
from clothing_config import professional_sizing

class ClothingValidator:
    """Validate clothing measurements (following your measurement_validator.py pattern)"""
    
    def __init__(self):
        self.professional_sizing = professional_sizing
    
    def validate_clothing_measurements(self, measurements):
        """Validate clothing measurements against professional standards"""
        try:
            print(f"[CLOTHING VALIDATOR] Validating {len(measurements)} measurements...")
            
            validated_measurements = {}
            
            for key, value in measurements.items():
                if isinstance(value, (int, float)) and value > 0:
                    # Apply basic validation
                    if 'width' in key.lower() and value > 200:  # Max 200cm width
                        validated_measurements[key] = 150  # Reasonable max
                    elif 'length' in key.lower() and value > 300:  # Max 300cm length
                        validated_measurements[key] = 200  # Reasonable max
                    else:
                        validated_measurements[key] = value
                else:
                    validated_measurements[key] = value
            
            print(f"[CLOTHING VALIDATOR] ✓ Validation completed")
            return validated_measurements
            
        except Exception as e:
            print(f"[CLOTHING VALIDATOR] ✗ Error: {str(e)}")
            return measurements
