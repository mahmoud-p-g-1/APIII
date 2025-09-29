# workers/measurement_worker.py

import os
import sys
import tempfile
import shutil
from datetime import datetime
import traceback
import json
import threading
import time

# Add measurement modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'measurement_modules'))

from queue_manager import queue_manager

def process_measurement_job(job_data):
    """Process a single measurement job"""
    job_id = job_data['job_id']
    user_id = job_data['user_id']
    job_dir = job_data['job_dir']
    
    try:
        print(f"Processing measurement job: {job_id}")
        
        # Import the save function
        from api.measurements.routes import save_measurement_job
        
        # Update status to processing
        save_measurement_job(job_id, user_id, 'processing')
        
        # Create working directory
        working_dir = os.path.join(job_dir, 'processing')
        os.makedirs(working_dir, exist_ok=True)
        os.makedirs(os.path.join(working_dir, 'distance'), exist_ok=True)
        os.makedirs(os.path.join(working_dir, 'images'), exist_ok=True)
        
        # Copy images to expected locations
        shutil.copy(job_data['front_image'], os.path.join(working_dir, 'distance', 'image 11_no_bg.jpg'))
        shutil.copy(job_data['side_image'], os.path.join(working_dir, 'distance', 'image 12_no_bg.jpg'))
        
        # Change to working directory
        original_dir = os.getcwd()
        os.chdir(working_dir)
        
        # Create photos_height.py
        with open('photos_height.py', 'w') as f:
            f.write(f"""
front_input_image = 'distance/image 11_no_bg.jpg'
side_input_image = 'distance/image 12_no_bg.jpg'
USE_AUTOMATIC_HEIGHT = {job_data.get('use_automatic_height', True)}
MANUAL_HEIGHT = {job_data.get('manual_height', 170)}
height = MANUAL_HEIGHT
""")
        
        # Add to path
        sys.path.insert(0, working_dir)
        
        try:
            # Import measurement modules
            from measurement_config import MeasurementConfig
            from height_measurement import HeightMeasurement
            from measurement_validator import MeasurementValidator
            from measurement_calculator import MeasurementCalculator
            from measurement_confidence import MeasurementConfidence
            
            # Process measurements
            config = MeasurementConfig()
            config.set_height_mode("auto" if job_data.get('use_automatic_height', True) else "manual")
            
            height_measurer = HeightMeasurement('distance/image 11_no_bg.jpg', 'distance/image 12_no_bg.jpg')
            detected_height = height_measurer.measure_height()
            
            if not (90 <= detected_height <= 220):
                detected_height = job_data.get('manual_height', 170)
            
            # Update photos_height
            with open('photos_height.py', 'w') as f:
                f.write(f"""
front_input_image = 'distance/image 11_no_bg.jpg'
side_input_image = 'distance/image 12_no_bg.jpg'
height = {detected_height}
""")
            
            # Run measurement pipeline
            exec(compile(open(os.path.join(sys.path[0], '..', '..', 'measurement_modules', 'medipie_cooordinates.py')).read(), 'medipie_cooordinates.py', 'exec'))
            exec(compile(open(os.path.join(sys.path[0], '..', '..', 'measurement_modules', 'decrease_contrast.py')).read(), 'decrease_contrast.py', 'exec'))
            exec(compile(open(os.path.join(sys.path[0], '..', '..', 'measurement_modules', 'remove_backround.py')).read(), 'remove_backround.py', 'exec'))
            exec(compile(open(os.path.join(sys.path[0], '..', '..', 'measurement_modules', 'add_silhouette.py')).read(), 'add_silhouette.py', 'exec'))
            exec(compile(open(os.path.join(sys.path[0], '..', '..', 'measurement_modules', 'body_segments.py')).read(), 'body_segments.py', 'exec'))
            exec(compile(open(os.path.join(sys.path[0], '..', '..', 'measurement_modules', 'get_height.py')).read(), 'get_height.py', 'exec'))
            
            # Get measurements
            measurements = locals().get('measurements_dict', {})
            
            # Validate measurements
            validator = MeasurementValidator(detected_height)
            corrected_measurements = validator.validate_all_measurements(measurements)
            
            # Calculate confidence
            confidence_analyzer = MeasurementConfidence(detected_height)
            confidence_scores = confidence_analyzer.calculate_confidence_score(corrected_measurements)
            overall_confidence = confidence_analyzer.get_overall_confidence(confidence_scores)
            
            # Save processed images locally
            processed_images = {}
            image_files = [
                ('images/medipipe_output.jpg', 'pose_detection_front'),
                ('images/medipipe_output_side.jpg', 'pose_detection_side'),
                ('images/body_segments.jpg', 'body_segments_front'),
                ('images/body_segments_side.jpg', 'body_segments_side'),
                ('images/get_height.jpg', 'height_measurement_front'),
                ('images/get_height_side.jpg', 'height_measurement_side')
            ]
            
            for src, name in image_files:
                if os.path.exists(src):
                    dest = os.path.join(job_dir, f'{name}.jpg')
                    shutil.copy(src, dest)
                    processed_images[name] = f'measurement_data/{user_id}/{job_id}/{name}.jpg'
            
            # Save results
            result_data = {
                'measurements': json.dumps(corrected_measurements),
                'confidence_scores': json.dumps(confidence_scores),
                'overall_confidence': overall_confidence,
                'height_detection_method': 'automatic' if job_data.get('use_automatic_height') else 'manual',
                'detected_height': detected_height,
                'completed_at': datetime.now().isoformat(),
                'processed_images': json.dumps(processed_images)
            }
            
            save_measurement_job(job_id, user_id, 'completed', result_data)
            
            print(f"Job {job_id} completed successfully")
            
        except Exception as e:
            raise Exception(f"Processing error: {str(e)}\n{traceback.format_exc()}")
        
        finally:
            os.chdir(original_dir)
            sys.path.remove(working_dir)
            
    except Exception as e:
        from api.measurements.routes import save_measurement_job
        save_measurement_job(job_id, user_id, 'failed', {
            'error': str(e),
            'failed_at': datetime.now().isoformat()
        })
        print(f"Job {job_id} failed: {str(e)}")

def measurement_worker_thread():
    """Worker thread for processing measurement jobs"""
    while True:
        try:
            job = queue_manager.get_job(timeout=1)
            if job and job.get('type') == 'measurement':
                process_measurement_job(job)
        except:
            pass
        time.sleep(1)

def start_measurement_worker():
    """Start the measurement worker thread"""
    thread = threading.Thread(target=measurement_worker_thread, daemon=True)
    thread.start()
    print("Measurement worker started")
