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

def test_basic_connectivity(session):
    """Test basic connectivity to Codebeamer"""
    print("🔗 Testing basic connectivity...")
    try:
        response = session.get(f"{CODEBEAMER_URL}/rest/v3/user")
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Connected successfully!")
            print(f"   User: {user_data.get('name', 'Unknown')}")
            print(f"   Email: {user_data.get('email', 'No email')}")
            print(f"   System Admin: {user_data.get('systemAdmin', False)}")
            return True
        else:
            print(f"❌ Connection failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False

def test_project_access(session):
    """Test access to project 68"""
    print("\n📂 Testing project access...")
    try:
        response = session.get(f"{CODEBEAMER_URL}/rest/v3/projects/{CODEBEAMER_PROJECT_ID}")
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

def test_scm_repositories(session):
    """Test SCM repository access"""
    print("\n🔧 Testing SCM repository access...")
    try:
        response = session.get(f"{CODEBEAMER_URL}/rest/v3/projects/{CODEBEAMER_PROJECT_ID}/scmRepositories")
        if response.status_code == 200:
            repos = response.json()
            print(f"✅ SCM repository access confirmed!")
            print(f"   Found {len(repos)} existing repositories in project {CODEBEAMER_PROJECT_ID}")
            for repo in repos[:3]:  # Show first 3
                print(f"   - {repo.get('name', 'Unknown')} (ID: {repo.get('id', 'Unknown')})")
            return True
        else:
            print(f"❌ SCM repository access failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ SCM repository error: {str(e)}")
        return False

def test_create_test_repo(session):
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
        response = session.post(
            f"{CODEBEAMER_URL}/rest/v3/projects/{CODEBEAMER_PROJECT_ID}/scmRepositories",
            json=test_repo_data
        )
        
        if response.status_code in [200, 201]:
            repo = response.json()
            print(f"✅ Test repository created successfully!")
            print(f"   Repository ID: {repo.get('id', 'Unknown')}")
            print(f"   Name: {repo.get('name', 'Unknown')}")
            
            # Clean up - delete the test repository
            print("🧹 Cleaning up test repository...")
            delete_response = session.delete(f"{CODEBEAMER_URL}/rest/v3/scmRepositories/{repo.get('id')}")
            if delete_response.status_code in [200, 204]:
                print("✅ Test repository cleaned up successfully!")
            else:
                print(f"⚠️  Test repository cleanup failed: {delete_response.status_code}")
            
            return True
        else:
            print(f"❌ Repository creation failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Repository creation error: {str(e)}")
        return False

def test_api_endpoints(session):
    """Test various API endpoints that will be used"""
    print("\n🔍 Testing API endpoints...")
    
    endpoints = [
        ("User Info", f"/rest/v3/user"),
        ("Project Info", f"/rest/v3/projects/{CODEBEAMER_PROJECT_ID}"),
        ("SCM Repositories", f"/rest/v3/projects/{CODEBEAMER_PROJECT_ID}/scmRepositories"),
    ]
    
    results = []
    for name, endpoint in endpoints:
        try:
            response = session.get(f"{CODEBEAMER_URL}{endpoint}")
            if response.status_code == 200:
                print(f"   ✅ {name}: OK")
                results.append(True)
            else:
                print(f"   ❌ {name}: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"   ❌ {name}: Error - {str(e)}")
            results.append(False)
    
    return all(results)

def main():
    """Run all tests"""
    print("🚀 Philips Codebeamer Connection Test")
    print("=" * 50)
    print(f"Codebeamer URL: {CODEBEAMER_URL}")
    print(f"Username: {CODEBEAMER_USERNAME}")
    print(f"Project ID: {CODEBEAMER_PROJECT_ID}")
    print("=" * 50)
    
    session = setup_session()
    
    tests = [
        ("Basic Connectivity", lambda: test_basic_connectivity(session)),
        ("Project Access", lambda: test_project_access(session)),
        ("SCM Repository Access", lambda: test_scm_repositories(session)),
        ("API Endpoints", lambda: test_api_endpoints(session)),
        ("Repository Creation", lambda: test_create_test_repo(session)),
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Your Codebeamer configuration is ready for the GitHub pipeline!")
        print("\nNext steps:")
        print("1. Add the GitHub Secrets as shown in SETUP.md")
        print("2. Commit your repository files")
        print("3. Make a test commit to trigger the pipeline")
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) failed. Please check your configuration:")
        print("1. Verify your Codebeamer credentials")
        print("2. Ensure you have system administrator permissions")
        print("3. Check project 68 access permissions")
        print("4. Verify REST API is enabled")

if __name__ == "__main__":
    main() 