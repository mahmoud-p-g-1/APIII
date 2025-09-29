# test_and_fix_firestore.py
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
SERVICE_ACCOUNT_PATH = "fitmatch-1-firebase-adminsdk-fbsvc-b0c3b89124.json"

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

def create_test_scraping_document():
    """Create a test scraping document in Firestore"""
    print("\n" + "="*60)
    print("CREATING TEST SCRAPING DOCUMENT IN FIRESTORE")
    print("="*60)
    
    token = get_access_token()
    if not token:
        print("❌ Failed to get access token")
        return False
    
    # User ID from your token
    user_id = "s0oWM7x7GZNAFfKwzFAqKoK4eKe2"
    
    # Generate a test import ID
    import_id = f"test_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create test scraping data (like from Amazon)
    test_data = {
        'fields': {
            'importId': {'stringValue': import_id},
            'userId': {'stringValue': user_id},
            'name': {'stringValue': 'French Toast Girls Long Sleeve Woven Shirt'},
            'category': {'stringValue': 'clothing'},
            'subcategory': {'stringValue': 'tops'},
            'brand': {'stringValue': 'French Toast'},
            'retailer': {'stringValue': 'amazon'},
            'productUrl': {'stringValue': 'https://www.amazon.com/dp/B01N3M8S0K'},
            'imageUrls': {
                'arrayValue': {
                    'values': [
                        {'stringValue': 'https://m.media-amazon.com/images/I/71vUejPcAXL._AC_SL1900_QL100_FMwebp_.jpg'},
                        {'stringValue': 'https://m.media-amazon.com/images/I/31539XI4vwL._AC_SL1900_QL100_FMwebp_.jpg'},
                        {'stringValue': 'https://m.media-amazon.com/images/I/317W8MHY1aL._AC_SL1900_QL100_FMwebp_.jpg'}
                    ]
                }
            },
            'extractedData': {
                'mapValue': {
                    'fields': {
                        'platform': {'stringValue': 'amazon'},
                        'scrapedAt': {'stringValue': datetime.now().isoformat()},
                        'imageCount': {'integerValue': '3'}
                    }
                }
            },
            'createdAt': {'stringValue': datetime.now().isoformat()},
            'testDocument': {'booleanValue': True}
        }
    }
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # 1. Create in main urlImports collection using the correct URL format
    print(f"\n1. Creating document in urlImports collection...")
    
    # Use the correct URL format for creating a document with a specific ID
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/urlImports/{import_id}"
    
    # Use PATCH method to create or update
    response = requests.patch(url, json=test_data, headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"   ✅ Successfully created: urlImports/{import_id}")
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    # 2. Create in user's subcollection
    print(f"\n2. Creating document in user's subcollection...")
    
    # For subcollections, use the full path
    user_url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}/urlImports/{import_id}"
    
    user_data = {
        'fields': {
            'importId': {'stringValue': import_id},
            'name': {'stringValue': 'French Toast Girls Long Sleeve Woven Shirt'},
            'retailer': {'stringValue': 'amazon'},
            'imageUrl': {'stringValue': 'https://m.media-amazon.com/images/I/71vUejPcAXL._AC_SL1900_QL100_FMwebp_.jpg'},
            'createdAt': {'stringValue': datetime.now().isoformat()},
            'testDocument': {'booleanValue': True}
        }
    }
    
    response = requests.patch(user_url, json=user_data, headers=headers)
    
    if response.status_code in [200, 201]:
        print(f"   ✅ Successfully created: users/{user_id}/urlImports/{import_id}")
        print(f"\n✅ TEST DOCUMENTS CREATED SUCCESSFULLY!")
        print(f"\n📱 Check your Firebase Console:")
        print(f"   1. Collection: urlImports → Document: {import_id}")
        print(f"   2. Collection: users → {user_id} → urlImports → {import_id}")
        return True
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def list_user_imports(user_id):
    """List existing imports for user"""
    print("\n" + "="*60)
    print("CHECKING EXISTING IMPORTS")
    print("="*60)
    
    token = get_access_token()
    if not token:
        return
    
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/users/{user_id}/urlImports"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        docs = data.get('documents', [])
        print(f"Found {len(docs)} documents in users/{user_id}/urlImports:")
        for doc in docs:
            doc_id = doc['name'].split('/')[-1]
            print(f"  - {doc_id}")
    else:
        print(f"No documents found or error: {response.status_code}")

def verify_document_created(import_id):
    """Verify the document was created"""
    print("\n" + "="*60)
    print("VERIFYING DOCUMENT CREATION")
    print("="*60)
    
    token = get_access_token()
    if not token:
        return
    
    # Check main collection
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents/urlImports/{import_id}"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print(f"✅ Document found in urlImports collection: {import_id}")
        doc_data = response.json()
        if 'fields' in doc_data:
            name = doc_data['fields'].get('name', {}).get('stringValue', 'N/A')
            print(f"   Product Name: {name}")
    else:
        print(f"❌ Document not found in urlImports collection")

def main():
    print("\n" + "="*60)
    print("FIRESTORE SCRAPING DATA TEST")
    print("="*60)
    
    user_id = "s0oWM7x7GZNAFfKwzFAqKoK4eKe2"
    
    # Check existing imports
    list_user_imports(user_id)
    
    # Create test document
    print("\n" + "="*60)
    print("Creating a test scraping document...")
    print("="*60)
    
    if create_test_scraping_document():
        # Get the import ID that was just created
        import_id = f"test_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Wait a moment for Firestore to process
        import time
        time.sleep(2)
        
        # Verify it was created
        verify_document_created(import_id)
        
        print("\n✅ Success! Check your Firebase Console now.")
        print("The test document has been created in both:")
        print("  1. urlImports collection")
        print(f"  2. users/{user_id}/urlImports subcollection")
    else:
        print("\n❌ Failed to create test document")

if __name__ == "__main__":
    main()
