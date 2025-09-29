# test_service_account.py
import json
import os
from datetime import datetime

SERVICE_ACCOUNT_PATH = "firebase-service-account.json"

def check_service_account():
    """Check if service account file is valid"""
    try:
        with open(SERVICE_ACCOUNT_PATH, 'r') as f:
            data = json.load(f)
            
        print("Service Account Details:")
        print(f"  Project ID: {data.get('project_id')}")
        print(f"  Client Email: {data.get('client_email')}")
        print(f"  Private Key ID: {data.get('private_key_id')}")
        print(f"  Private Key: {'Present' if data.get('private_key') else 'Missing'}")
        
        # Check system time
        print(f"\nSystem Time: {datetime.now().isoformat()}")
        print(f"Unix Timestamp: {int(datetime.now().timestamp())}")
        
        return True
    except Exception as e:
        print(f"Error reading service account: {e}")
        return False

if __name__ == "__main__":
    check_service_account()
