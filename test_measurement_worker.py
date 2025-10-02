# test_measurement_worker.py

import time
from queue_manager import queue_manager

# Add a test job directly to the queue
test_job = {
    'job_id': 'test_123',
    'user_id': 'test_user',
    'type': 'measurement',
    'front_image': 'measurement_data/test_users/test_user_2aea45d7/2665388c-84c1-4d57-b418-2c3bd5af6b66/front_front_img.jpg',
    'side_image': 'measurement_data/test_users/test_user_2aea45d7/2665388c-84c1-4d57-b418-2c3bd5af6b66/side_side_img.jpg',
    'manual_height': 170,
    'use_automatic_height': True,
    'job_dir': 'measurement_data/test_user/test_123'
}

print(f"Queue size before: {queue_manager.get_queue_size()}")
queue_manager.add_job(test_job)
print(f"Queue size after: {queue_manager.get_queue_size()}")

# Wait and check queue
time.sleep(2)
print(f"Queue size after 2 seconds: {queue_manager.get_queue_size()}")
