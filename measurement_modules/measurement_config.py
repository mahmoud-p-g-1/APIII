# config.py

class MeasurementConfig:
    """Configuration for body measurement system"""
    
    # Height measurement settings
    HEIGHT_MODE = "auto"  # Options: "auto", "manual", "hybrid"
    MANUAL_HEIGHT_CM = 170  # Default manual height in cm (average adult)
    
    # Anthropometric ratios for height estimation
    BODY_PROPORTIONS = {
        "head_to_height_ratio": 7.75,  # Height is ~7.75 head lengths
        "leg_to_height_ratio": 0.47,   # Legs are ~47% of height
        "torso_to_height_ratio": 0.30,  # Torso is ~30% of height
        "arm_span_to_height_ratio": 1.0,  # Arm span ≈ height
        "inseam_to_height_ratio": 0.45,  # Inside leg is ~45% of height
        "thigh_to_height_ratio": 0.23,  # Thigh is ~23% of height
        "shin_to_height_ratio": 0.22,   # Shin is ~22% of height
    }
    
    # Valid height range for humans (in cm)
    MIN_HUMAN_HEIGHT = 90   # Minimum realistic human height
    MAX_HUMAN_HEIGHT = 220  # Maximum realistic human height
    
    # Reference object settings (if using reference-based detection)
    REFERENCE_OBJECT = {
        "type": "ruler",  # Options: "ruler", "marker", "checkerboard"
        "height_cm": 30,  # Known height of reference object
        "color_range": {  # HSV color range for detection
            "lower": [40, 40, 40],
            "upper": [80, 255, 255]
        }
    }
    
    # ArUco marker settings
    ARUCO_SETTINGS = {
        "dictionary": "DICT_6X6_250",
        "marker_size_cm": 10
    }
    
    # Fallback options
    FALLBACK_TO_MANUAL = True  # Use manual height if auto fails
    PROMPT_FOR_HEIGHT = True   # Ask user for height if needed
    
    @classmethod
    def get_height_mode(cls):
        """Get the current height measurement mode"""
        return cls.HEIGHT_MODE
    
    @classmethod
    def set_height_mode(cls, mode):
        """Set the height measurement mode"""
        if mode in ["auto", "manual", "hybrid"]:
            cls.HEIGHT_MODE = mode
        else:
            raise ValueError(f"Invalid height mode: {mode}")
