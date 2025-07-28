#!/usr/bin/env python3
"""
Debug Codebeamer Login Form
Examines the actual login form structure to understand field names
"""

import requests
import re
from bs4 import BeautifulSoup

CODEBEAMER_URL = "https://www.sandbox.codebeamer.plm.philips.com"

def analyze_login_form():
    """Analyze the login form structure"""
    print("🔍 Analyzing Codebeamer login form structure...")
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        # Get the login page
        login_url = f"{CODEBEAMER_URL}/cb/login.spr"
        print(f"📄 Getting login page: {login_url}")
        
        response = session.get(login_url)
        if response.status_code != 200:
            print(f"❌ Failed to get login page: {response.status_code}")
            return
        
        print("✅ Login page retrieved successfully")
        content = response.text
        
        # Parse with BeautifulSoup for better form analysis
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find all forms
            forms = soup.find_all('form')
            print(f"\n📋 Found {len(forms)} form(s) on the page:")
            
            for i, form in enumerate(forms, 1):
                print(f"\n--- FORM {i} ---")
                print(f"Action: {form.get('action', 'Not specified')}")
                print(f"Method: {form.get('method', 'GET')}")
                
                # Find all input fields in this form
                inputs = form.find_all('input')
                print(f"Input fields ({len(inputs)}):")
                
                for input_field in inputs:
                    field_name = input_field.get('name', 'NO_NAME')
                    field_type = input_field.get('type', 'text')
                    field_value = input_field.get('value', '')
                    field_id = input_field.get('id', '')
                    
                    print(f"  - {field_name} (type: {field_type})")
                    if field_id:
                        print(f"    ID: {field_id}")
                    if field_value:
                        print(f"    Value: {field_value}")
                
                # Find select fields
                selects = form.find_all('select')
                if selects:
                    print(f"Select fields ({len(selects)}):")
                    for select in selects:
                        select_name = select.get('name', 'NO_NAME')
                        print(f"  - {select_name}")
                        
                        options = select.find_all('option')
                        for option in options:
                            option_value = option.get('value', '')
                            option_text = option.get_text(strip=True)
                            print(f"    Option: {option_value} - {option_text}")
        
        except ImportError:
            print("⚠️  BeautifulSoup not available, using regex parsing...")
            
            # Fallback to regex parsing
            forms = re.findall(r'<form[^>]*>(.*?)</form>', content, re.DOTALL | re.IGNORECASE)
            print(f"\n📋 Found {len(forms)} form(s) using regex:")
            
            for i, form_content in enumerate(forms, 1):
                print(f"\n--- FORM {i} ---")
                
                # Find form attributes
                form_tag = re.search(r'<form([^>]*)>', content, re.IGNORECASE)
                if form_tag:
                    form_attrs = form_tag.group(1)
                    action_match = re.search(r'action=["\']([^"\']*)["\']', form_attrs, re.IGNORECASE)
                    method_match = re.search(r'method=["\']([^"\']*)["\']', form_attrs, re.IGNORECASE)
                    
                    print(f"Action: {action_match.group(1) if action_match else 'Not specified'}")
                    print(f"Method: {method_match.group(1) if method_match else 'GET'}")
                
                # Find input fields
                inputs = re.findall(r'<input[^>]*>', form_content, re.IGNORECASE)
                print(f"Input fields ({len(inputs)}):")
                
                for input_field in inputs:
                    name_match = re.search(r'name=["\']([^"\']*)["\']', input_field, re.IGNORECASE)
                    type_match = re.search(r'type=["\']([^"\']*)["\']', input_field, re.IGNORECASE)
                    value_match = re.search(r'value=["\']([^"\']*)["\']', input_field, re.IGNORECASE)
                    
                    field_name = name_match.group(1) if name_match else 'NO_NAME'
                    field_type = type_match.group(1) if type_match else 'text'
                    field_value = value_match.group(1) if value_match else ''
                    
                    print(f"  - {field_name} (type: {field_type})")
                    if field_value:
                        print(f"    Value: {field_value}")
        
        # Look for any JavaScript that might affect form submission
        print(f"\n🔧 Checking for JavaScript form handling...")
        js_matches = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE)
        for i, js_content in enumerate(js_matches, 1):
            if 'login' in js_content.lower() or 'form' in js_content.lower():
                print(f"Found relevant JavaScript in script {i}")
                # Look for form field references
                field_refs = re.findall(r'["\']([a-zA-Z_][a-zA-Z0-9_]*)["\']', js_content)
                potential_fields = [ref for ref in field_refs if ref.lower() in ['username', 'password', 'user', 'pass', 'account', 'login']]
                if potential_fields:
                    print(f"  Potential field names: {potential_fields}")
        
        # Look for any error messages or hints
        print(f"\n💡 Looking for hints in page content...")
        if 'accountName' in content:
            print("✅ Found 'accountName' in page content")
        if 'username' in content.lower():
            print("✅ Found 'username' in page content")
        if 'password' in content.lower():
            print("✅ Found 'password' in page content")
        
        # Save the login page content for manual inspection
        with open('login_page_debug.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n💾 Login page saved to 'login_page_debug.html' for manual inspection")
        
    except Exception as e:
        print(f"❌ Error analyzing login form: {str(e)}")

if __name__ == "__main__":
    analyze_login_form() 