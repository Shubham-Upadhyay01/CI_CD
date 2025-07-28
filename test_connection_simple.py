#!/usr/bin/env python3
"""
Simple Codebeamer Connection Test
Tests basic connectivity using different authentication methods
"""

import requests
import base64
from datetime import datetime

# Philips Codebeamer Configuration
CODEBEAMER_URL = "https://www.sandbox.codebeamer.plm.philips.com"
CODEBEAMER_USERNAME = "Shubham.Upadhyay"
CODEBEAMER_PASSWORD = "cbpass"
CODEBEAMER_PROJECT_ID = "68"

def test_basic_auth():
    """Test using Basic Authentication"""
    print("🔐 Testing Basic Authentication...")
    
    session = requests.Session()
    
    # Setup Basic Auth
    auth_string = f"{CODEBEAMER_USERNAME}:{CODEBEAMER_PASSWORD}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    session.headers.update({
        'Authorization': f'Basic {auth_b64}',
        'User-Agent': 'GitHub-Codebeamer-Integration/1.0'
    })
    
    # Test different endpoints
    test_urls = [
        f"{CODEBEAMER_URL}/cb/",
        f"{CODEBEAMER_URL}/cb/project/{CODEBEAMER_PROJECT_ID}",
        f"{CODEBEAMER_URL}/cb/project/{CODEBEAMER_PROJECT_ID}/repositories",
        f"{CODEBEAMER_URL}/rest/v3/user",
        f"{CODEBEAMER_URL}/cb/rest/v3/user",
    ]
    
    for url in test_urls:
        try:
            print(f"   Testing: {url}")
            response = session.get(url)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS: {url}")
                if 'repository' in response.text.lower():
                    print("   📂 Contains repository content")
                return True
            elif response.status_code == 401:
                print("   ❌ Authentication failed")
            elif response.status_code == 403:
                print("   ❌ Access forbidden")
            elif response.status_code == 404:
                print("   ❌ Not found")
            else:
                print(f"   ⚠️  Unexpected status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    return False

def test_no_auth():
    """Test without authentication"""
    print("\n🌐 Testing without authentication...")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    # Test public endpoints
    test_urls = [
        f"{CODEBEAMER_URL}/cb/",
        f"{CODEBEAMER_URL}/cb/login.spr",
        f"{CODEBEAMER_URL}/cb/project/{CODEBEAMER_PROJECT_ID}",
    ]
    
    for url in test_urls:
        try:
            print(f"   Testing: {url}")
            response = session.get(url)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ Accessible: {url}")
                if 'login' in response.text.lower():
                    print("   🔐 Login form detected")
                if 'project' in response.text.lower():
                    print("   📁 Project content detected")
            else:
                print(f"   ❌ Status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

def test_direct_project_access():
    """Test direct project access with different auth methods"""
    print(f"\n📁 Testing direct project {CODEBEAMER_PROJECT_ID} access...")
    
    # Method 1: Basic Auth
    session1 = requests.Session()
    auth_string = f"{CODEBEAMER_USERNAME}:{CODEBEAMER_PASSWORD}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    session1.headers.update({
        'Authorization': f'Basic {auth_b64}',
        'User-Agent': 'GitHub-Codebeamer-Integration/1.0'
    })
    
    project_urls = [
        f"{CODEBEAMER_URL}/cb/project/{CODEBEAMER_PROJECT_ID}",
        f"{CODEBEAMER_URL}/cb/project/{CODEBEAMER_PROJECT_ID}/repositories",
        f"{CODEBEAMER_URL}/cb/proj/{CODEBEAMER_PROJECT_ID}",
        f"{CODEBEAMER_URL}/cb/projects/{CODEBEAMER_PROJECT_ID}",
    ]
    
    for url in project_urls:
        try:
            print(f"   Testing with Basic Auth: {url}")
            response = session1.get(url)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS with Basic Auth!")
                return True
            elif response.status_code == 401:
                print("   ❌ Authentication required")
            elif response.status_code == 403:
                print("   ❌ Access forbidden")
            elif response.status_code == 404:
                print("   ❌ Project not found")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    return False

def main():
    """Run all simple tests"""
    print("🚀 Simple Codebeamer Connection Test")
    print("=" * 50)
    print(f"URL: {CODEBEAMER_URL}")
    print(f"Username: {CODEBEAMER_USERNAME}")
    print(f"Project: {CODEBEAMER_PROJECT_ID}")
    print("=" * 50)
    
    # Test 1: Basic Auth
    basic_auth_ok = test_basic_auth()
    
    # Test 2: No Auth (public access)
    test_no_auth()
    
    # Test 3: Direct project access
    project_access_ok = test_direct_project_access()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SIMPLE TEST SUMMARY")
    print("=" * 50)
    print(f"Basic Auth: {'✅ Working' if basic_auth_ok else '❌ Failed'}")
    print(f"Project Access: {'✅ Working' if project_access_ok else '❌ Failed'}")
    
    if basic_auth_ok or project_access_ok:
        print("\n✅ SUCCESS! Some authentication method works!")
        print("This suggests the pipeline should work with Basic Auth.")
    else:
        print("\n❌ No authentication methods worked.")
        print("This suggests we need to fix the web-based login approach.")

if __name__ == "__main__":
    main() 