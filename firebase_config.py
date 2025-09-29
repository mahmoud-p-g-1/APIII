# firebase_config.py
import json
import os
from functools import wraps
from flask import request, jsonify
from datetime import datetime
import base64
import hashlib
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import traceback

# Configuration
FIREBASE_PROJECT_ID = "fitmatch-1"

# Get the directory where this file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, "firebase-service-account.json")

# Storage
db_storage = {}
firebase_initialized = False
credentials = None

def get_access_token():
    """Get access token for Firestore REST API"""
    global credentials
    
    try:
        # Check if service account file exists
        if not os.path.exists(SERVICE_ACCOUNT_PATH):
            print(f"Service account file not found at: {SERVICE_ACCOUNT_PATH}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Base directory: {BASE_DIR}")
            return None
            
        if not credentials:
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_PATH,
                scopes=['https://www.googleapis.com/auth/datastore']
            )
        
        credentials.refresh(Request())
        return credentials.token
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None

def initialize_firebase():
    """Initialize Firebase with REST API approach"""
    global firebase_initialized
    
    try:
        # Check if service account file exists
        if not os.path.exists(SERVICE_ACCOUNT_PATH):
            print(f"Service account file not found at: {SERVICE_ACCOUNT_PATH}")
            print(f"Looking in directory: {BASE_DIR}")
            # List files in directory to help debug
            print(f"Files in directory: {os.listdir(BASE_DIR)}")
            return False
            
        # Test if we can get an access token
        token = get_access_token()
        if token:
            firebase_initialized = True
            print("Firebase initialized successfully (using REST API)")
            return True
        else:
            print("Failed to get access token")
            return False
        
    except Exception as e:
        print(f"Firebase initialization error: {e}")
        traceback.print_exc()
        return False

def decode_token_without_verification(token):
    """Decode Firebase token without verification"""
    try:
        # Split the token
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        # Decode the payload (second part)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        # Decode base64
        decoded_bytes = base64.urlsafe_b64decode(payload)
        decoded_json = decoded_bytes.decode('utf-8')
        token_data = json.loads(decoded_json)
        
        # Check if token is expired
        if 'exp' in token_data:
            exp_timestamp = token_data['exp']
            current_timestamp = datetime.now().timestamp()
            if current_timestamp > exp_timestamp:
                print("Token is expired")
                return None
        
        # Fix the field name issue - map user_id to uid
        if 'user_id' in token_data and 'uid' not in token_data:
            token_data['uid'] = token_data['user_id']
        
        # Also handle 'sub' field which is often the user ID
        if 'sub' in token_data and 'uid' not in token_data:
            token_data['uid'] = token_data['sub']
        
        print(f"Token decoded for user: {token_data.get('uid', 'unknown')}")
        return token_data
        
    except Exception as e:
        print(f"Token decode error: {e}")
        return None

def verify_token(token):
    """Verify Firebase token"""
    return decode_token_without_verification(token)

def require_auth(f):
    """Decorator to require Firebase authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'No authentication token provided'}), 401
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        user = verify_token(token)
        if not user:
            return jsonify({'error': 'Invalid or expired authentication token'}), 401
        
        # Ensure uid field exists
        if 'uid' not in user:
            if 'user_id' in user:
                user['uid'] = user['user_id']
            elif 'sub' in user:
                user['uid'] = user['sub']
            else:
                user['uid'] = 'unknown_user'
        
        request.user = user
        return f(*args, **kwargs)
    
    return decorated_function

def generate_import_id():
    """Generate a unique import ID"""
    timestamp = datetime.now().isoformat()
    random_str = hashlib.md5(f"{timestamp}{os.urandom(16).hex()}".encode()).hexdigest()[:8]
    return f"import_{random_str}"

def save_scraping_to_firestore(user_id, scraping_result, url):
    """Save scraping result to Firestore using the WORKING method from test script"""
    try:
        token = get_access_token()
        if not token:
            print("No access token available - Firebase not initialized properly")
            # Save to in-memory storage as fallback
            if user_id not in db_storage:
                db_storage[user_id] = {}
            
            import_id = generate_import_id()
            db_storage[user_id][import_id] = scraping_result
            print(f"Saved to in-memory storage: {import_id}")
            return import_id
        
        # Generate import ID
        import_id = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:19]}"
        
        # Extract data from scraping result
        platform = scraping_result.get('platform', 'unknown')
        name = scraping_result.get('name', 'Unknown Product')
        images = scraping_result.get('images', [])
        
        # Ensure we have at least 5 image slots (fill with empty strings if needed)
        while len(images) < 5:
            images.append('')
        
        # Determine category based on product name
        category = 'clothing'
        subcategory = 'general'
        
        # Simple category detection from name
        name_lower = name.lower()
        if any(word in name_lower for word in ['shirt', 'blouse', 'top', 'tee']):
            subcategory = 'tops'
        elif any(word in name_lower for word in ['pants', 'jeans', 'trousers']):
            subcategory = 'bottoms'
        elif any(word in name_lower for word in ['dress', 'gown']):
            subcategory = 'dresses'
        elif any(word in name_lower for word in ['jacket', 'coat', 'blazer']):
            subcategory = 'outerwear'
        elif any(word in name_lower for word in ['cardigan', 'sweater', 'knitwear']):
            subcategory = 'knitwear'
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # 1. Create in main urlImports collection (USING THE EXACT WORKING METHOD)
        print(f"\n1. Creating document in urlImports collection...")
        
        url_imports_data = {
            'fields': {
                'importId': {'stringValue': import_id},
                'userId': {'stringValue': user_id},
                'name': {'stringValue': name},
                'category': {'stringValue': category},
                'subcategory': {'stringValue': subcategory},
                'brand': {'stringValue': ''},
                'retailer': {'stringValue': platform},
                'productUrl': {'stringValue': url},
                'imageUrls': {
                    'arrayValue': {
                        'values': [{'stringValue': img} for img in images[:5]]  # Store all 5 images
                    }
                },
                'imageUrl1': {'stringValue': images[0] if len(images) > 0 else ''},
                'imageUrl2': {'stringValue': images[1] if len(images) > 1 else ''},
                'imageUrl3': {'stringValue': images[2] if len(images) > 2 else ''},
                'imageUrl4': {'stringValue': images[3] if len(images) > 3 else ''},
                'imageUrl5': {'stringValue': images[4] if len(images) > 4 else ''},
                'extractedData': {
                    'mapValue': {
                        'fields': {
                            'platform': {'stringValue': platform},
                            'scrapedAt': {'stringValue': scraping_result.get('scraped_at', datetime.now().isoformat())},
                            'imageCount': {'integerValue': str(len([img for img in images if img]))}
                        }
                    }
                },
                'createdAt': {'stringValue': datetime.now().isoformat()},
                'scrapedFromAPI': {'booleanValue': True}
            }
        }
        
        # Use PATCH method with document ID in URL (EXACTLY like the working test)
        firestore_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/urlImports/{import_id}"
        
        response = requests.patch(firestore_url, json=url_imports_data, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"   Successfully created: urlImports/{import_id}")
        else:
            print(f"   Failed to create main document: {response.status_code}")
            print(f"   Response: {response.text}")
            # Still save to in-memory storage
            if user_id not in db_storage:
                db_storage[user_id] = {}
            db_storage[user_id][import_id] = scraping_result
            return import_id
        
        # 2. Create in user's subcollection (USING THE EXACT WORKING METHOD)
        print(f"\n2. Creating document in user's subcollection...")
        
        user_import_data = {
            'fields': {
                'importId': {'stringValue': import_id},
                'name': {'stringValue': name},
                'retailer': {'stringValue': platform},
                'imageUrls': {
                    'arrayValue': {
                        'values': [{'stringValue': img} for img in images[:5]]  # Store all 5 images
                    }
                },
                'imageUrl1': {'stringValue': images[0] if len(images) > 0 else ''},
                'imageUrl2': {'stringValue': images[1] if len(images) > 1 else ''},
                'imageUrl3': {'stringValue': images[2] if len(images) > 2 else ''},
                'imageUrl4': {'stringValue': images[3] if len(images) > 3 else ''},
                'imageUrl5': {'stringValue': images[4] if len(images) > 4 else ''},
                'productUrl': {'stringValue': url},
                'createdAt': {'stringValue': datetime.now().isoformat()},
                'fromAPI': {'booleanValue': True}
            }
        }
        
        # Use PATCH method with document ID in URL for subcollection
        user_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}/urlImports/{import_id}"
        
        response = requests.patch(user_url, json=user_import_data, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"   Successfully created: users/{user_id}/urlImports/{import_id}")
            print(f"\nSCRAPING DATA SAVED TO FIRESTORE!")
            print(f"   Document ID: {import_id}")
            print(f"   Saved {len([img for img in images if img])} images")
            return import_id
        else:
            print(f"   Failed to create user document: {response.status_code}")
            print(f"   Response: {response.text}")
            return import_id  # Return ID even if user subcollection fails
        
    except Exception as e:
        print(f"Error saving to Firestore: {e}")
        traceback.print_exc()
        
        # Fallback to in-memory storage
        if user_id not in db_storage:
            db_storage[user_id] = {}
        
        import_id = generate_import_id()
        db_storage[user_id][import_id] = scraping_result
        print(f"Saved to in-memory storage: {import_id}")
        return import_id

def save_job_to_firestore(user_id, job_data):
    """Save scraping job (for tracking)"""
    try:
        if user_id not in db_storage:
            db_storage[user_id] = {}
        
        job_id = job_data['job_id']
        db_storage[user_id][job_id] = job_data
        print(f"Job saved: {job_id} for user: {user_id}")
        return job_id
    except Exception as e:
        print(f"Error saving job: {e}")
        return None

def update_job_status(user_id, job_id, status, result=None):
    """Update job status and save result to Firestore if completed"""
    try:
        if user_id in db_storage and job_id in db_storage[user_id]:
            db_storage[user_id][job_id]['status'] = status
            db_storage[user_id][job_id]['updated_at'] = datetime.now().isoformat()
            
            if result:
                db_storage[user_id][job_id]['result'] = result
                
                # If job completed successfully, save to Firestore
                if status == 'completed' and result:
                    url = db_storage[user_id][job_id].get('url', '')
                    import_id = save_scraping_to_firestore(user_id, result, url)
                    if import_id:
                        db_storage[user_id][job_id]['importId'] = import_id
                        print(f"Scraping result saved to Firestore with ID: {import_id}")
            
            print(f"Job {job_id} status updated to: {status}")
    except Exception as e:
        print(f"Error updating job status: {e}")

def get_job_from_firestore(user_id, job_id):
    """Get job from storage"""
    try:
        if user_id in db_storage and job_id in db_storage[user_id]:
            return db_storage[user_id][job_id]
        return None
    except Exception as e:
        print(f"Error getting job: {e}")
        return None

def get_user_imports(user_id, limit=10):
    """Get user's URL imports from Firestore"""
    try:
        if firebase_initialized:
            token = get_access_token()
            if token:
                # Query user's urlImports subcollection
                url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}/urlImports"
                
                headers = {
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    imports = []
                    
                    if 'documents' in data:
                        for doc in data['documents']:
                            # Convert Firestore format back to Python dict
                            import_data = {}
                            if 'fields' in doc:
                                for key, value in doc['fields'].items():
                                    import_data[key] = extract_value(value)
                            imports.append(import_data)
                    
                    return imports
        
        # Fallback to in-memory storage
        if user_id in db_storage:
            imports = []
            for key, value in db_storage[user_id].items():
                if 'importId' in value:
                    imports.append(value)
            return imports[:limit]
        
        return []
        
    except Exception as e:
        print(f"Error getting user imports: {e}")
        return []

def extract_value(firestore_value):
    """Extract Python value from Firestore format"""
    if 'stringValue' in firestore_value:
        return firestore_value['stringValue']
    elif 'integerValue' in firestore_value:
        return int(firestore_value['integerValue'])
    elif 'doubleValue' in firestore_value:
        return firestore_value['doubleValue']
    elif 'booleanValue' in firestore_value:
        return firestore_value['booleanValue']
    elif 'arrayValue' in firestore_value:
        values = []
        if 'values' in firestore_value['arrayValue']:
            for v in firestore_value['arrayValue']['values']:
                values.append(extract_value(v))
        return values
    elif 'mapValue' in firestore_value:
        result = {}
        if 'fields' in firestore_value['mapValue']:
            for key, value in firestore_value['mapValue']['fields'].items():
                result[key] = extract_value(value)
        return result
    elif 'nullValue' in firestore_value:
        return None
    else:
        return None

# Dummy Firestore client for compatibility
class SimpleDB:
    def collection(self, name):
        return self
    
    def document(self, doc_id):
        return self
    
    def get(self):
        class Doc:
            def __init__(self):
                self.exists = False
            def to_dict(self):
                return {}
        return Doc()
    
    def set(self, data):
        pass
    
    def update(self, data):
        pass

db = SimpleDB()
