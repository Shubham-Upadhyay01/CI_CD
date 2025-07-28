#!/usr/bin/env python3
"""
Debug Codebeamer Login Response
Examines the exact response from login attempts to understand the error
"""

import requests
import re
from datetime import datetime

CODEBEAMER_URL = "https://www.sandbox.codebeamer.plm.philips.com"
CODEBEAMER_USERNAME = "Shubham.Upadhyay"
CODEBEAMER_PASSWORD = "cbpass"

def debug_login_response():
    """Debug the login response to understand what's happening"""
    print("🔍 Debugging Codebeamer login response...")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        # Step 1: Get login page
        login_url = f"{CODEBEAMER_URL}/cb/login.spr"
        print(f"📄 Getting login page: {login_url}")
        
        login_page = session.get(login_url)
        if login_page.status_code != 200:
            print(f"❌ Failed to get login page: {login_page.status_code}")
            return
        
        print("✅ Login page retrieved")
        
        # Step 2: Prepare login data
        login_data = {
            'user': CODEBEAMER_USERNAME,     # HTML field name is 'user' (not 'accountName')
            'password': CODEBEAMER_PASSWORD
        }
        
        # Get targetURL
        target_url_match = re.search(r'<input[^>]*name=["\']targetURL["\'][^>]*value=["\']([^"\']*)["\']', login_page.text, re.IGNORECASE)
        if target_url_match:
            target_url = target_url_match.group(1)
            login_data['targetURL'] = target_url
            print(f"📍 Found targetURL: '{target_url}'")
        else:
            print("⚠️  No targetURL found")
        
        # Get all hidden fields
        hidden_fields = re.findall(r'<input[^>]*type=["\']hidden["\'][^>]*>', login_page.text)
        for hidden in hidden_fields:
            name_match = re.search(r'name=["\']([^"\']+)["\']', hidden)
            value_match = re.search(r'value=["\']([^"\']*)["\']', hidden)
            if name_match and value_match:
                field_name = name_match.group(1)
                field_value = value_match.group(1)
                if field_name not in login_data:
                    login_data[field_name] = field_value
                    print(f"🔒 Hidden field: {field_name} = '{field_value}'")
        
        print(f"\n📋 Login data to submit: {login_data}")
        
        # Step 3: Submit login
        session.headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': login_url
        })
        
        print(f"\n🚀 Submitting login...")
        login_response = session.post(login_url, data=login_data, allow_redirects=False)
        
        print(f"📊 Login Response Status: {login_response.status_code}")
        print(f"📍 Response URL: {login_response.url}")
        
        # Check headers
        print(f"\n📋 Response Headers:")
        for header, value in login_response.headers.items():
            print(f"   {header}: {value}")
        
        # Check if there's a redirect
        if 'Location' in login_response.headers:
            redirect_url = login_response.headers['Location']
            print(f"\n🔄 Redirect to: {redirect_url}")
            
            # Follow the redirect
            if redirect_url.startswith('/'):
                redirect_url = CODEBEAMER_URL + redirect_url
            
            redirect_response = session.get(redirect_url)
            print(f"📊 Redirect Response Status: {redirect_response.status_code}")
            print(f"📍 Final URL: {redirect_response.url}")
            
            # Save redirect response
            with open('redirect_response.html', 'w', encoding='utf-8') as f:
                f.write(redirect_response.text)
            print("💾 Redirect response saved to 'redirect_response.html'")
            
            response_content = redirect_response.text
        else:
            response_content = login_response.text
        
        # Save the response
        with open('login_response.html', 'w', encoding='utf-8') as f:
            f.write(response_content)
        print("💾 Login response saved to 'login_response.html'")
        
        # Analyze the response content
        print(f"\n🔍 Analyzing response content...")
        content_lower = response_content.lower()
        
        # Look for error messages
        error_indicators = [
            'error', 'invalid', 'incorrect', 'failed', 'denied', 
            'no such group', 'authentication', 'login failed',
            'wrong password', 'user not found', 'access denied'
        ]
        
        found_errors = []
        for indicator in error_indicators:
            if indicator in content_lower:
                found_errors.append(indicator)
        
        if found_errors:
            print(f"❌ Found error indicators: {found_errors}")
            
            # Look for specific error messages
            error_patterns = [
                r'<[^>]*error[^>]*>([^<]+)',
                r'class=["\'][^"\']*error[^"\']*["\'][^>]*>([^<]+)',
                r'(no such group[^<.]*)',
                r'(authentication failed[^<.]*)',
                r'(invalid [^<.]*)',
            ]
            
            for pattern in error_patterns:
                matches = re.findall(pattern, response_content, re.IGNORECASE)
                if matches:
                    print(f"🔍 Error message pattern found: {matches}")
        
        # Look for success indicators
        success_indicators = ['welcome', 'dashboard', 'projects', 'logout', 'main']
        found_success = []
        for indicator in success_indicators:
            if indicator in content_lower:
                found_success.append(indicator)
        
        if found_success:
            print(f"✅ Found success indicators: {found_success}")
        
        # Check if still on login page
        if 'login.spr' in login_response.url or 'login' in content_lower:
            print("⚠️  Still on login page - login likely failed")
        else:
            print("✅ Appears to have left login page")
        
        # Try alternative credentials format
        print(f"\n🔄 Trying alternative login approaches...")
        
        # Test with different username formats
        alternative_usernames = [
            CODEBEAMER_USERNAME.lower(),  # lowercase
            CODEBEAMER_USERNAME.upper(),  # uppercase
            CODEBEAMER_USERNAME.replace('.', ''),  # without dot
            'shubham.upadhyay',  # different case
            'Shubham Upadhyay',  # with space
        ]
        
        for alt_username in alternative_usernames:
            if alt_username == CODEBEAMER_USERNAME:
                continue  # Skip the original
                
            print(f"   Trying username: '{alt_username}'")
            
            alt_login_data = login_data.copy()
            alt_login_data['user'] = alt_username # Changed from 'accountName' to 'user'
            
            alt_response = session.post(login_url, data=alt_login_data, allow_redirects=False)
            
            if alt_response.status_code != login_response.status_code:
                print(f"   📊 Different response: {alt_response.status_code}")
                
                if 'no such group' not in alt_response.text.lower():
                    print(f"   ✅ No 'no such group' error with '{alt_username}'")
                    
                    # Save this response
                    with open(f'alt_response_{alt_username.replace(".", "_")}.html', 'w', encoding='utf-8') as f:
                        f.write(alt_response.text)
            else:
                print(f"   Same response as original")
        
    except Exception as e:
        print(f"❌ Error during debug: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_login_response() 