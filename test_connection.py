#!/usr/bin/env python3
"""
Test Codebeamer Connection and Configuration
Run this script to verify your Philips Codebeamer setup before deploying the pipeline
"""

import requests
import base64
import json
from datetime import datetime

# Philips Codebeamer Configuration
CODEBEAMER_URL = "https://www.sandbox.codebeamer.plm.philips.com"
CODEBEAMER_USERNAME = "Shubham.Upadhyay"
CODEBEAMER_PASSWORD = "cbpass"
CODEBEAMER_PROJECT_ID = "68"

def setup_session():
    """Setup authenticated session"""
    session = requests.Session()
    
    # Setup Basic Auth
    auth_string = f"{CODEBEAMER_USERNAME}:{CODEBEAMER_PASSWORD}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    session.headers.update({
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    })
    
    return session

def find_working_api_version(session):
    """Find the correct API version for this Codebeamer instance"""
    print("🔍 Finding correct API version...")
    
    api_versions = ['/rest/v3', '/rest/v2', '/cb/rest/v3', '/cb/rest/v2', '/rest/v1']
    
    for api_version in api_versions:
        try:
            test_url = f"{CODEBEAMER_URL}{api_version}/user"
            print(f"   Testing: {test_url}")
            response = session.get(test_url)
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"✅ Found working API version: {api_version}")
                print(f"   User: {user_data.get('name', 'Unknown')}")
                print(f"   Email: {user_data.get('email', 'No email')}")
                print(f"   System Admin: {user_data.get('systemAdmin', False)}")
                return api_version
            else:
                print(f"   ❌ {api_version}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {api_version}: Error - {str(e)}")
    
    return None

def test_basic_connectivity(session):
    """Test basic connectivity to Codebeamer"""
    print("🔗 Testing basic connectivity...")
    
    api_version = find_working_api_version(session)
    if api_version:
        return api_version
    else:
        print("❌ Could not find any working API endpoint")
        return None

def test_project_access(session, api_version):
    """Test access to project 68"""
    print(f"\n📂 Testing project access using {api_version}...")
    try:
        response = session.get(f"{CODEBEAMER_URL}{api_version}/projects/{CODEBEAMER_PROJECT_ID}")
        if response.status_code == 200:
            project_data = response.json()
            print(f"✅ Project access confirmed!")
            print(f"   Project: {project_data.get('name', 'Unknown')}")
            print(f"   ID: {project_data.get('id', 'Unknown')}")
            print(f"   Description: {project_data.get('description', 'No description')[:100]}...")
            return True
        else:
            print(f"❌ Project access failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Project access error: {str(e)}")
        return False

def test_scm_repositories(session, api_version):
    """Test SCM repository access with multiple endpoint attempts"""
    print(f"\n🔧 Testing SCM repository access using {api_version}...")
    
    # Try different SCM endpoint patterns
    scm_endpoints = [
        f"{api_version}/projects/{CODEBEAMER_PROJECT_ID}/scmRepositories",
        f"{api_version}/project/{CODEBEAMER_PROJECT_ID}/scmRepositories",
        f"{api_version}/projects/{CODEBEAMER_PROJECT_ID}/repositories",
        f"{api_version}/scmRepositories?projectId={CODEBEAMER_PROJECT_ID}",
        f"{api_version}/repositories?projectId={CODEBEAMER_PROJECT_ID}"
    ]
    
    for endpoint in scm_endpoints:
        try:
            url = f"{CODEBEAMER_URL}{endpoint}"
            print(f"   Trying: {url}")
            response = session.get(url)
            
            if response.status_code == 200:
                repos = response.json()
                print(f"✅ SCM repository access confirmed at: {endpoint}")
                print(f"   Found {len(repos)} existing repositories in project {CODEBEAMER_PROJECT_ID}")
                for repo in repos[:3]:  # Show first 3
                    print(f"   - {repo.get('name', 'Unknown')} (ID: {repo.get('id', 'Unknown')})")
                return endpoint
            else:
                print(f"   ❌ {response.status_code}: {response.reason}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("❌ No working SCM repository endpoint found")
    return None

def test_create_test_repo(session, api_version, scm_endpoint):
    """Test creating a test SCM repository"""
    print("\n🧪 Testing SCM repository creation...")
    
    test_repo_data = {
        "name": f"GitHub-Test-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "description": "Test repository created by GitHub-Codebeamer pipeline setup",
        "repositoryUrl": "https://github.com/test/test-repo",
        "type": "GIT",
        "projectId": int(CODEBEAMER_PROJECT_ID)
    }
    
    try:
        url = f"{CODEBEAMER_URL}{scm_endpoint}"
        print(f"   Creating repository at: {url}")
        print(f"   Data: {json.dumps(test_repo_data, indent=2)}")
        
        response = session.post(url, json=test_repo_data)
        
        if response.status_code in [200, 201]:
            repo = response.json()
            print(f"✅ Test repository created successfully!")
            print(f"   Repository ID: {repo.get('id', 'Unknown')}")
            print(f"   Name: {repo.get('name', 'Unknown')}")
            
            # Clean up - delete the test repository
            print("🧹 Cleaning up test repository...")
            delete_response = session.delete(f"{CODEBEAMER_URL}{api_version}/scmRepositories/{repo.get('id')}")
            if delete_response.status_code in [200, 204]:
                print("✅ Test repository cleaned up successfully!")
            else:
                print(f"⚠️  Test repository cleanup failed: {delete_response.status_code}")
            
            return True
        else:
            print(f"❌ Repository creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Repository creation error: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 Philips Codebeamer Connection Test")
    print("=" * 50)
    print(f"Codebeamer URL: {CODEBEAMER_URL}")
    print(f"Username: {CODEBEAMER_USERNAME}")
    print(f"Project ID: {CODEBEAMER_PROJECT_ID}")
    print("=" * 50)
    
    session = setup_session()
    
    # Test 1: Find working API version
    api_version = test_basic_connectivity(session)
    if not api_version:
        print("\n❌ CRITICAL: Cannot connect to Codebeamer API")
        print("Please check:")
        print("1. URL is correct")
        print("2. Username and password are correct")
        print("3. User has API access permissions")
        return
    
    # Test 2: Project access
    project_ok = test_project_access(session, api_version)
    if not project_ok:
        print(f"\n❌ CRITICAL: Cannot access project {CODEBEAMER_PROJECT_ID}")
        print("Please check:")
        print("1. Project ID is correct")
        print("2. User has access to this project")
        return
    
    # Test 3: SCM repository access
    scm_endpoint = test_scm_repositories(session, api_version)
    if not scm_endpoint:
        print("\n❌ CRITICAL: Cannot access SCM repositories")
        print("Please check:")
        print("1. User has SCM repository permissions")
        print("2. Project supports SCM repositories")
        return
    
    # Test 4: Repository creation
    create_ok = test_create_test_repo(session, api_version, scm_endpoint)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"API Version: {api_version}")
    print(f"SCM Endpoint: {scm_endpoint}")
    print(f"Project Access: {'✅ OK' if project_ok else '❌ FAIL'}")
    print(f"Repository Creation: {'✅ OK' if create_ok else '❌ FAIL'}")
    
    if project_ok and scm_endpoint and create_ok:
        print("\n🎉 All tests passed! Your Codebeamer configuration is ready!")
        print(f"\n📝 Configuration for your pipeline:")
        print(f"   Working API: {api_version}")
        print(f"   SCM Endpoint: {scm_endpoint}")
        print("\nNext steps:")
        print("1. Push the updated pipeline code")
        print("2. Add GitHub Secrets")
        print("3. Make a test commit")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above before proceeding.")

if __name__ == "__main__":
    main() 