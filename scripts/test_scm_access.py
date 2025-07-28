#!/usr/bin/env python3
"""
Test Codebeamer SCM Git Access
This script tests if we can access the Codebeamer SCM repository via Git
"""

import os
import sys
import requests
import subprocess
from urllib.parse import urlparse, urlunparse

# Configuration
CODEBEAMER_URL = "https://www.sandbox.codebeamer.plm.philips.com"
CODEBEAMER_USERNAME = "Shubham.Upadhyay"
CODEBEAMER_PASSWORD = "cbpass"
CODEBEAMER_PROJECT_ID = "68"
REPO_NAME = "GitHub-CI_CD"
REPO_ID = "218057"

def test_git_urls():
    """Test different Git URL patterns for Codebeamer SCM"""
    
    print("🔍 Testing Codebeamer SCM Git Access")
    print("=" * 50)
    print(f"Repository: {REPO_NAME} (ID: {REPO_ID})")
    print(f"Project: {CODEBEAMER_PROJECT_ID}")
    print("=" * 50)
    
    # Possible Git URL patterns
    url_patterns = [
        f"{CODEBEAMER_URL}/cb/repository/{REPO_ID}.git",
        f"{CODEBEAMER_URL}/cb/repository/{REPO_NAME}.git", 
        f"{CODEBEAMER_URL}/cb/project/{CODEBEAMER_PROJECT_ID}/scm/{REPO_NAME}.git",
        f"{CODEBEAMER_URL}/cb/project/{CODEBEAMER_PROJECT_ID}/repository/{REPO_NAME}.git",
        f"{CODEBEAMER_URL}/cb/scm/{CODEBEAMER_PROJECT_ID}/{REPO_NAME}.git",
        f"{CODEBEAMER_URL}/cb/scm/{REPO_ID}.git",
        f"{CODEBEAMER_URL}/scm/{CODEBEAMER_PROJECT_ID}/{REPO_NAME}.git",
        f"{CODEBEAMER_URL}/git/{CODEBEAMER_PROJECT_ID}/{REPO_NAME}.git"
    ]
    
    print(f"🧪 Testing {len(url_patterns)} URL patterns...\n")
    
    working_urls = []
    
    for i, git_url in enumerate(url_patterns, 1):
        print(f"🔄 Test {i}/{len(url_patterns)}: {git_url}")
        
        # Create authenticated URL
        auth_url = create_auth_url(git_url)
        
        # Test with git ls-remote (lightweight test)
        try:
            result = subprocess.run(
                ['git', 'ls-remote', auth_url],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"   ✅ SUCCESS: Git repository accessible")
                print(f"   📋 Remote refs found: {len(result.stdout.splitlines())} refs")
                working_urls.append(git_url)
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                print(f"   ❌ FAILED: {error_msg[:100]}...")
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ TIMEOUT: Git operation timed out")
        except FileNotFoundError:
            print(f"   ❌ ERROR: Git command not found")
            break
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
        
        print()
    
    print("=" * 50)
    print("📊 RESULTS")
    print("=" * 50)
    
    if working_urls:
        print(f"✅ Found {len(working_urls)} working Git URL(s):")
        for url in working_urls:
            print(f"   - {url}")
        print("\n🎯 Use these URLs for Git operations!")
    else:
        print("❌ No working Git URLs found!")
        print("\n💡 Possible reasons:")
        print("   1. Git access not enabled for this repository")
        print("   2. Different authentication method required")
        print("   3. Repository not configured for Git operations")
        print("   4. Network/firewall restrictions")
        
        print(f"\n🌐 Try accessing the web interface:")
        print(f"   Repository page: {CODEBEAMER_URL}/cb/repository/{REPO_ID}")
        print(f"   Project page: {CODEBEAMER_URL}/cb/project/{CODEBEAMER_PROJECT_ID}")

def create_auth_url(git_url):
    """Create an authenticated Git URL"""
    parsed = urlparse(git_url)
    auth_netloc = f"{CODEBEAMER_USERNAME}:{CODEBEAMER_PASSWORD}@{parsed.netloc}"
    
    return urlunparse((
        parsed.scheme,
        auth_netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))

def test_web_repository_access():
    """Test if we can access the repository via web interface"""
    print("\n🌐 Testing Web Repository Access")
    print("-" * 30)
    
    session = requests.Session()
    
    # Test repository web page
    repo_url = f"{CODEBEAMER_URL}/cb/repository/{REPO_ID}"
    
    try:
        response = session.get(repo_url)
        print(f"Repository page ({repo_url}): {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Repository web page accessible")
            
            # Look for Git-related information
            content = response.text.lower()
            if 'git' in content:
                print("   📋 Page mentions 'git' - Git support likely available")
            if 'clone' in content:
                print("   📋 Page mentions 'clone' - Clone operations likely supported")
            if '.git' in content:
                print("   📋 Page contains '.git' references")
                
        else:
            print(f"   ❌ Repository page not accessible: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error accessing repository page: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting Codebeamer SCM Git Access Test")
    print()
    
    test_git_urls()
    test_web_repository_access()
    
    print("\n" + "=" * 50)
    print("🔚 Test completed!")
    print("If no Git URLs work, the repository may not support Git operations.")
    print("In that case, use web-based logging instead of Git push.") 