# test_firebase_connection.py
import os
import json
import base64
from datetime import datetime
import hashlib
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Configuration
FIREBASE_PROJECT_ID = "fitmatch-1"
SERVICE_ACCOUNT_PATH = "firebase-service-account.json"

# Your token
TEST_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjA1NTc3MjZmYWIxMjMxZmEyZGNjNTcyMWExMDgzZGE2ODBjNGE3M2YiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vZml0bWF0Y2gtMSIsImF1ZCI6ImZpdG1hdGNoLTEiLCJhdXRoX3RpbWUiOjE3NTkwNjU4ODMsInVzZXJfaWQiOiJzMG9XTTd4N0daTkFGZkt3ekZBcUtvSzRlS2UyIiwic3ViIjoiczBvV003eDdHWk5BRmZLd3pGQXFLb0s0ZUtlMiIsImlhdCI6MTc1OTA2NTg4MywiZXhwIjoxNzU5MDY5NDgzLCJlbWFpbCI6InNpZGFuMTY0NDBAZ2RkY29ycC5jb20iLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnsiZW1haWwiOlsic2lkYW4xNjQ0MEBnZGRjb3JwLmNvbSJdfSwic2lnbl9pbl9wcm92aWRlciI6InBhc3N3b3JkIn19.GesPMVqfIVbLxNTsWHJa7JL3rG_j8lLCsMmtrUR9foVRkpHzpTzWeqvah9Y4jHMQR5u1x75ZIJ_Lh-fg0LoWjjT3_NEzET7h2bIjXvqCbYyB1Udqcx0EecKcYo0TX-AlCk62rGMZAPRpdzDjA7w1uTV5rPWKNeePzgv8bHoKwdG_GBGG1NUGidsTsBCv0l0XCKoqIiW8hHnCshjeextIVvVQelntLrKCM2eWD5f0l0IGCcU0foJ7XI00DRf6yY9K0AFcPitOnK_Yrs1mrniIh3OZIJ8H7TBBCXp_yAFCp1Lg0a0PO2k0r258ACuuN4QW_6Sswm1uEIt4lyNH-xdf0g"

def decode_token(token):
    """Decode JWT token to get user info"""
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
        
        return token_data
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None

def get_access_token():
    """Get access token for Firestore REST API"""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_PATH,
            scopes=['https://www.googleapis.com/auth/datastore']
        )
        
        credentials.refresh(Request())
        return credentials.token
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None

def test_firestore_connection():
    """Test basic Firestore connection"""
    print("\n" + "="*60)
    print("TESTING FIRESTORE CONNECTION")
    print("="*60)
    
    token = get_access_token()
    if not token:
        print("❌ Failed to get access token")
        return False
    
    print("✅ Successfully obtained access token")
    
    # Test listing collections
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents:listCollectionIds"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, json={})
    
    if response.status_code == 200:
        print("✅ Successfully connected to Firestore")
        collections = response.json().get('collectionIds', [])
        print(f"   Found {len(collections)} collections: {collections[:5]}...")
        return True
    else:
        print(f"❌ Failed to connect to Firestore: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_user_document(user_id):
    """Test if user document exists"""
    print("\n" + "="*60)
    print(f"TESTING USER DOCUMENT: {user_id}")
    print("="*60)
    
    token = get_access_token()
    if not token:
        print("❌ Failed to get access token")
        return False
    
    # Check if user document exists
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print(f"✅ User document exists: users/{user_id}")
        user_data = response.json()
        
        # Extract some fields
        if 'fields' in user_data:
            fields = user_data['fields']
            email = fields.get('email', {}).get('stringValue', 'N/A')
            print(f"   Email: {email}")
        return True
    else:
        print(f"❌ User document not found: {response.status_code}")
        return False

def test_user_subcollections(user_id):
    """Test user subcollections"""
    print("\n" + "="*60)
    print(f"TESTING USER SUBCOLLECTIONS")
    print("="*60)
    
    token = get_access_token()
    if not token:
        print("❌ Failed to get access token")
        return False
    
    # List subcollections for the user
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}:listCollectionIds"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, json={})
    
    if response.status_code == 200:
        subcollections = response.json().get('collectionIds', [])
        print(f"✅ Found {len(subcollections)} subcollections:")
        for collection in subcollections:
            print(f"   - {collection}")
        
        # Check if urlImports exists
        if 'urlImports' not in subcollections:
            print("\n⚠️  'urlImports' subcollection does not exist yet")
            print("   It will be created when you save the first scraping result")
        else:
            print("\n✅ 'urlImports' subcollection exists")
            
            # List documents in urlImports
            url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}/urlImports"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                docs = data.get('documents', [])
                print(f"   Found {len(docs)} documents in urlImports")
        
        return True
    else:
        print(f"❌ Failed to list subcollections: {response.status_code}")
        return False

def create_test_document(user_id):
    """Create a test document in Firestore"""
    print("\n" + "="*60)
    print("CREATING TEST DOCUMENT IN FIRESTORE")
    print("="*60)
    
    token = get_access_token()
    if not token:
        print("❌ Failed to get access token")
        return False
    
    # Generate a test import ID
    import_id = f"test_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create test data
    test_data = {
        'fields': {
            'importId': {'stringValue': import_id},
            'userId': {'stringValue': user_id},
            'name': {'stringValue': 'Test Product - French Toast Girls Shirt'},
            'category': {'stringValue': 'clothing'},
            'subcategory': {'stringValue': 'tops'},
            'retailer': {'stringValue': 'amazon'},
            'productUrl': {'stringValue': 'https://www.amazon.com/dp/B01N3M8S0K'},
            'imageUrls': {
                'arrayValue': {
                    'values': [
                        {'stringValue': 'https://m.media-amazon.com/images/I/71vUejPcAXL._AC_SL1900_QL100_FMwebp_.jpg'},
                        {'stringValue': 'https://m.media-amazon.com/images/I/71vUejPcAXL._AC_SL1900_QL100_FMwebp_.jpg'}
                    ]
                }
            },
            'createdAt': {'stringValue': datetime.now().isoformat()},
            'testDocument': {'booleanValue': True}
        }
    }
    
    # Save to main urlImports collection
    print(f"\n1. Saving to main collection: urlImports/{import_id}")
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/urlImports?documentId={import_id}"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.patch(url, json=test_data, headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"   ✅ Successfully created: urlImports/{import_id}")
    else:
        print(f"   ❌ Failed to create document: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    # Save to user's subcollection
    print(f"\n2. Saving to user subcollection: users/{user_id}/urlImports/{import_id}")
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}/urlImports?documentId={import_id}"
    
    user_import_data = {
        'fields': {
            'importId': {'stringValue': import_id},
            'name': {'stringValue': 'Test Product - French Toast Girls Shirt'},
            'retailer': {'stringValue': 'amazon'},
            'createdAt': {'stringValue': datetime.now().isoformat()},
            'testDocument': {'booleanValue': True}
        }
    }
    
    response = requests.patch(url, json=user_import_data, headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"   ✅ Successfully created: users/{user_id}/urlImports/{import_id}")
        print(f"\n✅ TEST DOCUMENT CREATED SUCCESSFULLY!")
        print(f"   Check your Firebase Console:")
        print(f"   1. Go to urlImports collection and look for: {import_id}")
        print(f"   2. Go to users/{user_id}/urlImports and look for: {import_id}")
        return True
    else:
        print(f"   ❌ Failed to create user document: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def main():
    """Main test function"""
    print("\n" + "="*60)
    print("FIREBASE FIRESTORE CONNECTION TEST")
    print("="*60)
    
    # Decode token to get user ID
    print("\n1. Decoding token...")
    token_data = decode_token(TEST_TOKEN)
    
    if not token_data:
        print("❌ Failed to decode token")
        return
    
    user_id = token_data.get('user_id') or token_data.get('uid') or token_data.get('sub')
    email = token_data.get('email', 'N/A')
    
    print(f"✅ Token decoded successfully")
    print(f"   User ID: {user_id}")
    print(f"   Email: {email}")
    
    # Test Firestore connection
    print("\n2. Testing Firestore connection...")
    if not test_firestore_connection():
        return
    
    # Test user document
    print("\n3. Testing user document...")
    test_user_document(user_id)
    
    # Test user subcollections
    print("\n4. Testing user subcollections...")
    test_user_subcollections(user_id)
    
    # Ask if user wants to create a test document
    print("\n" + "="*60)
    print("Would you like to create a test document in Firestore?")
    print("This will create a test import in both:")
    print(f"  - urlImports collection")
    print(f"  - users/{user_id}/urlImports subcollection")
    print("="*60)
    
    response = input("\nCreate test document? (yes/no): ").lower()
    
    if response == 'yes':
        create_test_document(user_id)
    else:
        print("\nTest document creation skipped")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
