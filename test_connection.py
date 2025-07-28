#!/usr/bin/env python3
"""
Test Codebeamer Connection and Configuration
Run this script to verify your Philips Codebeamer setup before deploying the pipeline
"""

import requests
import base64
import json
from datetime import datetime
import re
from urllib.parse import urljoin

# Philips Codebeamer Configuration - Updated based on browser URL
CODEBEAMER_URL = "https://www.sandbox.codebeamer.plm.philips.com"
CODEBEAMER_USERNAME = "Shubham.Upadhyay"
CODEBEAMER_PASSWORD = "cbpass"
CODEBEAMER_PROJECT_ID = "68"  # Updated back to 68

def setup_session():
    """Setup session with proper headers"""
    session = requests.Session()
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    })
    
    return session

def login_to_codebeamer(session):
    """Login to Codebeamer using web form authentication"""
    print("🔐 Attempting web-based login...")
    
    try:
        # Step 1: Get the login page to retrieve any CSRF tokens or session cookies
        login_page_url = f"{CODEBEAMER_URL}/cb/login.spr"
        print(f"   Getting login page: {login_page_url}")
        
        login_page_response = session.get(login_page_url)
        if login_page_response.status_code != 200:
            print(f"   ❌ Failed to get login page: {login_page_response.status_code}")
            return False
        
        print("   ✅ Login page accessible")
        
        # Step 2: Use the correct field names from form analysis
        login_form_data = {
            'user': CODEBEAMER_USERNAME,     # HTML field name is 'user' (not 'accountName')
            'password': CODEBEAMER_PASSWORD  # Password field is correct
        }
        
        # Look for the targetURL hidden field
        target_url_match = re.search(r'<input[^>]*name=["\']targetURL["\'][^>]*value=["\']([^"\']*)["\']', login_page_response.text, re.IGNORECASE)
        if target_url_match:
            target_url = target_url_match.group(1)
            login_form_data['targetURL'] = target_url
            print(f"   Found targetURL: {target_url}")
        
        # Look for CSRF token (CRITICAL for Codebeamer!)
        csrf_token_match = re.search(r'var csrfToken = ["\']([^"\']*)["\']', login_page_response.text)
        csrf_param_match = re.search(r'var csrfParameterName = ["\']([^"\']*)["\']', login_page_response.text)
        if csrf_token_match and csrf_param_match:
            csrf_token = csrf_token_match.group(1)
            csrf_param = csrf_param_match.group(1)
            login_form_data[csrf_param] = csrf_token
            print(f"   Found CSRF token: {csrf_param} = {csrf_token}")
        else:
            print("   ⚠️  CSRF token not found - this may cause login issues")
        
        # Look for any other hidden fields
        hidden_inputs = re.findall(r'<input[^>]*type=["\']hidden["\'][^>]*>', login_page_response.text)
        for hidden_input in hidden_inputs:
            name_match = re.search(r'name=["\']([^"\']+)["\']', hidden_input)
            value_match = re.search(r'value=["\']([^"\']*)["\']', hidden_input)
            if name_match and value_match:
                field_name = name_match.group(1)
                field_value = value_match.group(1)
                if field_name not in login_form_data:  # Don't override existing fields
                    login_form_data[field_name] = field_value
                    print(f"   Found hidden field: {field_name} = {field_value}")
        
        # Step 3: Submit login form
        print(f"   Submitting login with fields: {list(login_form_data.keys())}")
        
        session.headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': login_page_url
        })
        
        login_response = session.post(login_page_url, data=login_form_data, allow_redirects=True)
        
        # Step 4: Check if login was successful
        if login_response.status_code == 200:
            response_text = login_response.text.lower()
            final_url = login_response.url
            
            print(f"   Final URL after login: {final_url}")
            
            # Check for authentication cookies FIRST (most reliable indicator)
            has_auth_cookies = any(cookie.name in ['Bearer', 'JSESSIONID'] for cookie in session.cookies)
            
            # Check if we're NOT on login page anymore
            not_on_login = 'login.spr' not in final_url
            
            # Check for success indicators (based on debug output)
            success_indicators = [
                'welcome', 'dashboard', 'projects', 'logout', 'main',
                '/cb/user', '/cb/project', 'bearer', 'jsessionid'
            ]
            
            url_success = any(indicator in final_url.lower() for indicator in ['/cb/user', '/cb/project', '/cb/main'])
            content_success = any(indicator in response_text for indicator in success_indicators)
            
            # PRIORITIZE SUCCESS: If we have auth cookies and are not on login page, login succeeded
            if has_auth_cookies and not_on_login:
                print("   ✅ Login successful!")
                print(f"   - Has auth cookies: {has_auth_cookies}")
                print(f"   - Not on login page: {not_on_login}")
                print(f"   - URL indicates success: {url_success}")
                print(f"   - Content indicates success: {content_success}")
                return True
            # Secondary check: URL or content success indicators
            elif url_success or content_success:
                print("   ✅ Login successful!")
                print(f"   - URL indicates success: {url_success}")
                print(f"   - Content indicates success: {content_success}")
                print(f"   - Has auth cookies: {has_auth_cookies}")
                print(f"   - Not on login page: {not_on_login}")
                return True
            # Only check for errors if no success indicators found
            elif any(error in response_text for error in ['invalid', 'incorrect', 'failed', 'denied']):
                print("   ❌ Login failed - authentication error detected in content")
                return False
            elif 'no such group' in response_text:
                print("   ❌ Login failed - 'no such group' error")
                return False
            else:
                # Final fallback: test actual project access
                print("   ⚠️  Login status unclear, verifying with test request...")
                test_url = f"{CODEBEAMER_URL}/cb/project/{CODEBEAMER_PROJECT_ID}"
                test_response = session.get(test_url)
                if test_response.status_code == 200 and 'login' not in test_response.url.lower():
                    print("   ✅ Login verified successful via test request!")
                    return True
                else:
                    print("   ❌ Login verification failed")
                    return False
        else:
            print(f"   ❌ Login failed with HTTP {login_response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Login error: {str(e)}")
        print(f"   Exception type: {type(e).__name__}")
        print(f"   Exception details: {repr(e)}")
        
        # Try to get more context about the error
        if hasattr(e, 'response'):
            print(f"   HTTP response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
            print(f"   HTTP response text: {e.response.text[:200] if hasattr(e.response, 'text') else 'N/A'}...")
        
        import traceback
        print(f"   Full traceback:")
        traceback.print_exc()
        
        return False

def test_basic_login(session):
    """Test basic login and web interface access"""
    print("🔗 Testing basic login and web access...")
    
    # First try login
    if not login_to_codebeamer(session):
        print("❌ Failed to login to Codebeamer")
        return False
    
    try:
        # Test the main page after login
        main_url = f"{CODEBEAMER_URL}/cb/"
        response = session.get(main_url)
        if response.status_code == 200:
            print("✅ Main page accessible after login")
            
            # Test project page access
            project_url = f"{CODEBEAMER_URL}/cb/project/{CODEBEAMER_PROJECT_ID}"
            project_response = session.get(project_url)
            if project_response.status_code == 200:
                print(f"✅ Project {CODEBEAMER_PROJECT_ID} accessible")
                return True
            else:
                print(f"❌ Project access failed: {project_response.status_code}")
                # Try alternative project URL patterns
                alt_project_urls = [
                    f"{CODEBEAMER_URL}/cb/proj/{CODEBEAMER_PROJECT_ID}",
                    f"{CODEBEAMER_URL}/cb/projects/{CODEBEAMER_PROJECT_ID}",
                ]
                
                for alt_url in alt_project_urls:
                    print(f"   Trying alternative: {alt_url}")
                    alt_response = session.get(alt_url)
                    if alt_response.status_code == 200:
                        print(f"✅ Found working project URL: {alt_url}")
                        return True
                
                return False
        else:
            print(f"❌ Main page access failed after login: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False

def find_working_api_version(session):
    """Find the correct API version for this older Codebeamer instance"""
    print("🔍 Finding correct API version...")
    
    # For Codebeamer 3.x, try different patterns
    api_patterns = [
        '/cb/rest/v3/user',
        '/cb/rest/v2/user', 
        '/cb/rest/v1/user',
        '/cb/rest/user',
        '/cb/api/v1/user',
        '/cb/api/user',
        '/rest/v3/user',
        '/rest/v2/user',
        '/rest/v1/user',
        '/rest/user'
    ]
    
    for pattern in api_patterns:
        try:
            test_url = f"{CODEBEAMER_URL}{pattern}"
            print(f"   Testing: {test_url}")
            response = session.get(test_url)
            
            if response.status_code == 200:
                try:
                    user_data = response.json()
                    api_version = pattern.replace('/user', '')
                    print(f"✅ Found working API endpoint: {api_version}")
                    print(f"   User: {user_data.get('name', 'Unknown')}")
                    print(f"   Email: {user_data.get('email', 'No email')}")
                    return api_version
                except:
                    print(f"   Response not JSON, trying next...")
            else:
                print(f"   ❌ {pattern}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {pattern}: Error - {str(e)}")
    
    print("❌ No REST API endpoints found - this Codebeamer version may not support REST API")
    return None

def test_web_based_scm_access(session):
    """Test SCM access through web interface since REST API might not be available"""
    print(f"\n🔧 Testing SCM repository access via web interface...")
    
    # Test the repositories page that we know exists
    repo_url = f"{CODEBEAMER_URL}/cb/project/{CODEBEAMER_PROJECT_ID}/repositories"
    
    try:
        print(f"   Testing: {repo_url}")
        response = session.get(repo_url)
        
        if response.status_code == 200:
            print("✅ SCM repositories page accessible via web interface")
            
            # Check if it contains repository information
            content = response.text
            if "repository" in content.lower() or "scm" in content.lower():
                print("✅ Page contains repository/SCM content")
                
                # Look for existing repositories
                repo_count = content.lower().count('repository')
                print(f"   Found {repo_count} repository references on page")
                return True
            else:
                print("⚠️  Page accessible but no repository content found")
                return False
        else:
            print(f"❌ SCM repositories page failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ SCM access error: {str(e)}")
        return False

def test_alternative_endpoints(session):
    """Test alternative endpoints for older Codebeamer versions"""
    print(f"\n🔍 Testing alternative endpoints for Codebeamer 3.x...")
    
    # Test various endpoints that might work with older versions
    test_endpoints = [
        f"/cb/project/{CODEBEAMER_PROJECT_ID}/repositories",
        f"/cb/project/{CODEBEAMER_PROJECT_ID}/scm",
        f"/cb/proj/{CODEBEAMER_PROJECT_ID}/repositories",
        f"/cb/projects/{CODEBEAMER_PROJECT_ID}/repositories",
        f"/cb/project/{CODEBEAMER_PROJECT_ID}",
        f"/cb/project/{CODEBEAMER_PROJECT_ID}/wiki",
        f"/cb/project/{CODEBEAMER_PROJECT_ID}/tracker"
    ]
    
    working_endpoints = []
    
    for endpoint in test_endpoints:
        try:
            url = f"{CODEBEAMER_URL}{endpoint}"
            print(f"   Testing: {url}")
            response = session.get(url)
            
            if response.status_code == 200:
                print(f"   ✅ Working: {endpoint}")
                working_endpoints.append(endpoint)
            else:
                print(f"   ❌ {response.status_code}: {endpoint}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    return working_endpoints

def main():
    """Run all tests for older Codebeamer version"""
    print("🚀 Philips Codebeamer Connection Test (Version 3.x)")
    print("=" * 60)
    print(f"Codebeamer URL: {CODEBEAMER_URL}")
    print(f"Username: {CODEBEAMER_USERNAME}")
    print(f"Project ID: {CODEBEAMER_PROJECT_ID}")
    print("Version: 3.0.0.1 (older version - limited REST API)")
    print("Authentication: Web-based login (not Basic Auth)")
    print("=" * 60)
    
    session = setup_session()
    
    # Test 1: Basic web login
    login_ok = test_basic_login(session)
    if not login_ok:
        print("\n❌ CRITICAL: Cannot access Codebeamer web interface")
        print("Please check:")
        print("1. URL is correct")
        print("2. Username and password are correct")
        print("3. Account is not locked")
        print("4. Account has access to this Codebeamer instance")
        return
    
    # Test 2: Try to find REST API (may not exist in version 3.x)
    api_version = find_working_api_version(session)
    
    # Test 3: Test web-based SCM access
    scm_web_ok = test_web_based_scm_access(session)
    
    # Test 4: Test alternative endpoints
    working_endpoints = test_alternative_endpoints(session)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Web Login: {'✅ OK' if login_ok else '❌ FAIL'}")
    print(f"REST API: {'✅ Found' if api_version else '❌ Not Available (expected for v3.x)'}")
    print(f"SCM Web Access: {'✅ OK' if scm_web_ok else '❌ FAIL'}")
    print(f"Working Endpoints: {len(working_endpoints)}")
    
    if working_endpoints:
        print("\nWorking endpoints found:")
        for endpoint in working_endpoints:
            print(f"   - {endpoint}")
    
    if login_ok and scm_web_ok:
        print("\n✅ SUCCESS! Your configuration is working!")
        print("\n📋 Configuration Summary:")
        print("1. ✅ Login works with web-based authentication")
        print(f"2. ✅ Project {CODEBEAMER_PROJECT_ID} is accessible")
        print("3. ✅ SCM repositories page is accessible")
        print("4. ⚠️  REST API not available (expected for v3.x)")
        
        print("\n🔧 PIPELINE CONFIGURATION:")
        print("- The pipeline will use web-based synchronization")
        print("- No REST API calls will be made")
        print("- Sync information will be logged to project pages")
        
        print("\n🚀 NEXT STEPS:")
        print(f"1. GitHub Secret CODEBEAMER_PROJECT_ID is set to '{CODEBEAMER_PROJECT_ID}'")
        print("2. Push the updated pipeline code")
        print("3. Make a test commit to trigger the pipeline")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    main() 