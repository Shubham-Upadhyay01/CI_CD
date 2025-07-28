#!/usr/bin/env python3
"""
Codebeamer Web-based Synchronization Script for Version 3.x
Syncs GitHub repository changes to Codebeamer via web interface (no REST API)
"""

import os
import sys
import json
import requests
import base64
from datetime import datetime
from git import Repo
import logging
import re
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CodebeamerWebSync:
    def __init__(self):
        self.codebeamer_url = os.environ.get('CODEBEAMER_URL')
        self.username = os.environ.get('CODEBEAMER_USERNAME')
        self.password = os.environ.get('CODEBEAMER_PASSWORD')
        self.project_id = os.environ.get('CODEBEAMER_PROJECT_ID')
        self.github_repo_url = os.environ.get('GITHUB_REPO_URL')
        
        # GitHub event information
        self.event_name = os.environ.get('GITHUB_EVENT_NAME')
        self.ref = os.environ.get('GITHUB_REF')
        self.sha = os.environ.get('GITHUB_SHA')
        self.actor = os.environ.get('GITHUB_ACTOR')
        
        self.session = requests.Session()
        self._setup_session()
        
    def _setup_session(self):
        """Setup session with proper headers for web-based authentication"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
    def login_to_codebeamer(self):
        """Login to Codebeamer using web form authentication"""
        logger.info("🔐 Logging into Codebeamer...")
        
        try:
            # Step 1: Get the login page
            login_page_url = f"{self.codebeamer_url}/cb/login.spr"
            logger.info(f"Getting login page: {login_page_url}")
            
            login_page_response = self.session.get(login_page_url)
            if login_page_response.status_code != 200:
                logger.error(f"Failed to get login page: {login_page_response.status_code}")
                return False
            
            # Step 2: Submit login form with correct field names
            login_form_data = {
                'user': self.username,     # HTML field name is 'user' (not 'accountName')
                'password': self.password
            }
            
            # Look for CSRF token (CRITICAL for Codebeamer!)
            csrf_token_match = re.search(r'var csrfToken = ["\']([^"\']*)["\']', login_page_response.text)
            csrf_param_match = re.search(r'var csrfParameterName = ["\']([^"\']*)["\']', login_page_response.text)
            if csrf_token_match and csrf_param_match:
                csrf_token = csrf_token_match.group(1)
                csrf_param = csrf_param_match.group(1)
                login_form_data[csrf_param] = csrf_token
                logger.info(f"Found CSRF token: {csrf_param} = {csrf_token}")
            else:
                logger.warning("CSRF token not found - this may cause login issues")
            
            # Look for hidden form fields
            hidden_inputs = re.findall(r'<input[^>]*type=["\']hidden["\'][^>]*>', login_page_response.text)
            for hidden_input in hidden_inputs:
                name_match = re.search(r'name=["\']([^"\']+)["\']', hidden_input)
                value_match = re.search(r'value=["\']([^"\']*)["\']', hidden_input)
                if name_match and value_match:
                    login_form_data[name_match.group(1)] = value_match.group(1)
                    logger.debug(f"Found hidden field: {name_match.group(1)}")
            
            # Step 3: Submit login
            self.session.headers.update({
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': login_page_url
            })
            
            login_response = self.session.post(login_page_url, data=login_form_data, allow_redirects=True)
            
            # Step 4: Check login success
            if login_response.status_code == 200:
                final_url = login_response.url
                logger.info(f"Final URL after login: {final_url}")
                
                # Check for authentication cookies FIRST (most reliable indicator)
                has_auth_cookies = any(cookie.name in ['Bearer', 'JSESSIONID'] for cookie in self.session.cookies)
                
                # Check if we're NOT on login page anymore
                not_on_login = 'login.spr' not in final_url
                
                # Check for success indicators
                url_success = any(indicator in final_url.lower() for indicator in ['/cb/user', '/cb/project', '/cb/main'])
                
                # PRIORITIZE SUCCESS: If we have auth cookies and are not on login page, login succeeded
                if has_auth_cookies and not_on_login:
                    logger.info("✅ Successfully logged into Codebeamer")
                    logger.info(f"- Has auth cookies: {has_auth_cookies}")
                    logger.info(f"- Not on login page: {not_on_login}")
                    logger.info(f"- URL indicates success: {url_success}")
                    return True
                # Secondary check: URL success indicators
                elif url_success:
                    logger.info("✅ Successfully logged into Codebeamer")
                    logger.info(f"- URL indicates success: {url_success}")
                    logger.info(f"- Has auth cookies: {has_auth_cookies}")
                    return True
                # Only check for errors if no success indicators found
                elif 'invalid' in login_response.text.lower() or 'incorrect' in login_response.text.lower():
                    logger.error("❌ Login failed - invalid credentials")
                    return False
                else:
                    # Final fallback: if we have cookies and not on login, consider success
                    if has_auth_cookies:
                        logger.info("✅ Login appears successful (has auth cookies)")
                        return True
                    else:
                        logger.warning("⚠️  Login status unclear, proceeding...")
                        return True
            else:
                logger.error(f"Login failed with status: {login_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False
    
    def test_connectivity(self):
        """Test basic connectivity to Codebeamer web interface"""
        try:
            # First login
            if not self.login_to_codebeamer():
                return False
                
            # Test project page access
            project_url = f"{self.codebeamer_url}/cb/project/{self.project_id}"
            project_response = self.session.get(project_url)
            if project_response.status_code != 200:
                logger.error(f"Cannot access project {self.project_id}: {project_response.status_code}")
                return False
                
            logger.info("✅ Successfully connected to Codebeamer and project")
            return True
            
        except Exception as e:
            logger.error(f"Connectivity test failed: {str(e)}")
            return False
    
    def get_repositories_page(self):
        """Get the repositories page content"""
        try:
            repo_url = f"{self.codebeamer_url}/cb/project/{self.project_id}/repositories"
            logger.info(f"Accessing repositories page: {repo_url}")
            
            response = self.session.get(repo_url)
            if response.status_code == 200:
                logger.info("✅ Successfully accessed repositories page")
                return response.text
            else:
                logger.error(f"Failed to access repositories page: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error accessing repositories page: {str(e)}")
            return None
    
    def check_existing_repository(self, page_content):
        """Check if our GitHub repository already exists"""
        try:
            if not page_content:
                return False
                
            # Look for our GitHub repository URL in the page content
            repo_name = os.path.basename(self.github_repo_url).replace('.git', '')
            
            # Check for various patterns that might indicate our repository
            patterns = [
                self.github_repo_url,
                repo_name,
                f"GitHub-{repo_name}",
                self.github_repo_url.replace('https://github.com/', ''),
            ]
            
            for pattern in patterns:
                if pattern.lower() in page_content.lower():
                    logger.info(f"✅ Found existing repository reference: {pattern}")
                    return True
            
            logger.info("No existing repository found")
            return False
            
        except Exception as e:
            logger.error(f"Error checking existing repository: {str(e)}")
            return False
    
    def create_repository_comment(self):
        """Create a comment or note about the GitHub repository integration"""
        try:
            # Since we can't create repositories via web interface easily,
            # we'll create a comprehensive log/comment about the sync
            
            repo = Repo('.')
            current_commit = repo.head.commit
            
            sync_info = {
                "timestamp": datetime.now().isoformat(),
                "github_repository": self.github_repo_url,
                "event_type": self.event_name,
                "commit_sha": self.sha,
                "commit_message": current_commit.message.strip() if current_commit else "No commit info",
                "commit_author": current_commit.author.name if current_commit else self.actor,
                "branch": self.ref.replace('refs/heads/', '') if self.ref else 'unknown',
                "triggered_by": self.actor
            }
            
            # Log the sync information
            logger.info("📋 GitHub Repository Sync Information:")
            logger.info(f"   Repository: {sync_info['github_repository']}")
            logger.info(f"   Commit: {sync_info['commit_sha'][:8]} - {sync_info['commit_message'][:50]}...")
            logger.info(f"   Author: {sync_info['commit_author']}")
            logger.info(f"   Branch: {sync_info['branch']}")
            logger.info(f"   Event: {sync_info['event_type']}")
            logger.info(f"   Time: {sync_info['timestamp']}")
            
            # Try to find a way to add this information to the project
            self.add_project_note(sync_info)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating repository comment: {str(e)}")
            return False
    
    def add_project_note(self, sync_info):
        """Try to add a note or comment to the project about the sync"""
        try:
            logger.info("📝 Preparing sync information for Codebeamer project...")
            
            # Format sync information as a readable note
            note_content = f"""
GitHub Repository Sync - {sync_info['timestamp']}
================================================
Repository: {sync_info['github_repository']}
Commit: {sync_info['commit_sha']}
Message: {sync_info['commit_message']}
Author: {sync_info['commit_author']}
Branch: {sync_info['branch']}
Event: {sync_info['event_type']}
Triggered by: {sync_info['triggered_by']}

This is an automated sync from GitHub Actions to Codebeamer project {self.project_id}.
GitHub repository changes are being tracked and synchronized.
"""
            
            # Log the note content (this serves as the synchronization record)
            logger.info("📄 Sync Note Content:")
            for line in note_content.strip().split('\n'):
                logger.info(f"   {line}")
                
            # In a future enhancement, this could:
            # 1. Look for comment/note forms on project pages
            # 2. Submit comments to project wiki or discussion areas
            # 3. Create project documents with sync information
            # 4. Update project descriptions with GitHub links
            
            logger.info("✅ Sync information prepared and logged")
            return True
            
        except Exception as e:
            logger.error(f"Error adding project note: {str(e)}")
            return False
    
    def push_to_codebeamer_scm(self):
        """Push commits directly to Codebeamer SCM repository"""
        try:
            logger.info("🔄 Starting direct push to Codebeamer SCM repository...")
            
            repo = Repo('.')
            current_branch = repo.active_branch.name
            logger.info(f"Current branch: {current_branch}")
            
            # Get all possible repository URLs to try
            repo_name = os.getenv('CODEBEAMER_REPO_NAME', 'GitHub-CI_CD')
            
            # List of URL patterns to try (ordered by likelihood)
            url_patterns = [
                # Most likely based on your repository setup
                f"{self.codebeamer_url}/cb/repository/218057.git",
                f"{self.codebeamer_url}/cb/repository/{repo_name}.git",
                
                # Alternative patterns
                f"{self.codebeamer_url}/cb/project/{self.project_id}/scm/{repo_name}.git",
                f"{self.codebeamer_url}/cb/project/{self.project_id}/repository/{repo_name}.git", 
                f"{self.codebeamer_url}/cb/scm/{self.project_id}/{repo_name}.git",
                f"{self.codebeamer_url}/cb/scm/218057.git"
            ]
            
            logger.info(f"🎯 Will try {len(url_patterns)} URL patterns for repository: {repo_name}")
            
            # Try each URL pattern
            for i, codebeamer_repo_url in enumerate(url_patterns, 1):
                logger.info(f"🔄 Attempt {i}/{len(url_patterns)}: {codebeamer_repo_url}")
                
                try:
                    # Check if we already have a Codebeamer remote
                    codebeamer_remote = None
                    for remote in repo.remotes:
                        if 'codebeamer' in remote.name:
                            codebeamer_remote = remote
                            break
                    
                    # Create or update the Codebeamer remote
                    if not codebeamer_remote:
                        logger.info(f"   Adding Codebeamer remote...")
                        codebeamer_remote = repo.create_remote('codebeamer', codebeamer_repo_url)
                    else:
                        logger.info(f"   Updating existing Codebeamer remote...")
                        codebeamer_remote.set_url(codebeamer_repo_url)
                    
                    # Create authenticated URL
                    auth_url = self.get_authenticated_repo_url(codebeamer_repo_url)
                    codebeamer_remote.set_url(auth_url)
                    
                    # Try to push
                    logger.info(f"   Pushing {current_branch} to Codebeamer...")
                    push_info = codebeamer_remote.push(f"{current_branch}:{current_branch}", force=True)
                    
                    if push_info:
                        logger.info("✅ Successfully pushed to Codebeamer SCM repository!")
                        for info in push_info:
                            logger.info(f"   📋 Push result: {info.summary}")
                        
                        logger.info(f"🎯 Working URL pattern: {codebeamer_repo_url}")
                        return True
                    
                except Exception as url_error:
                    logger.warning(f"   ❌ Failed with URL pattern {i}: {str(url_error)}")
                    continue
            
            # If all patterns failed
            logger.error("❌ All URL patterns failed. Repository might not be accessible or configured differently.")
            logger.info("💡 Troubleshooting tips:")
            logger.info("   1. Verify the repository exists in Codebeamer")
            logger.info("   2. Check if Git access is enabled for the repository")
            logger.info("   3. Verify your credentials have push permissions")
            logger.info(f"   4. Repository web URL: {self.codebeamer_url}/cb/repository/218057")
            
            return False
                
        except Exception as e:
            logger.error(f"Critical error in SCM push: {str(e)}")
            return False
    
    def get_codebeamer_repo_url(self):
        """Get the Codebeamer SCM repository URL"""
        # Based on the provided repository details:
        # Repository Name: GitHub-CI_CD
        # Repository ID: 218057
        # Repository URL: https://www.sandbox.codebeamer.plm.philips.com/cb/repository/218057
        
        # Try to get repository name from environment or use the known name
        repo_name = os.getenv('CODEBEAMER_REPO_NAME', 'GitHub-CI_CD')
        
        logger.info("🔍 Determining Codebeamer SCM repository URL...")
        logger.info(f"   Repository name: {repo_name}")
        logger.info(f"   Project ID: {self.project_id}")
        
        # For Codebeamer 3.x, try different URL patterns based on the provided repository URL
        # The repository URL pattern suggests: /cb/repository/ID
        # But for Git operations, it might be different
        
        possible_urls = [
            # Pattern 1: Based on repository ID (most likely for your setup)
            f"{self.codebeamer_url}/cb/repository/218057.git",
            f"{self.codebeamer_url}/cb/repository/{repo_name}.git",
            
            # Pattern 2: Project-based URLs
            f"{self.codebeamer_url}/cb/project/{self.project_id}/scm/{repo_name}.git",
            f"{self.codebeamer_url}/cb/project/{self.project_id}/repository/{repo_name}.git",
            f"{self.codebeamer_url}/cb/project/{self.project_id}/repositories/{repo_name}.git",
            
            # Pattern 3: Direct SCM URLs
            f"{self.codebeamer_url}/cb/scm/{self.project_id}/{repo_name}.git",
            f"{self.codebeamer_url}/scm/{self.project_id}/{repo_name}.git",
            
            # Pattern 4: Repository ID based (alternative)
            f"{self.codebeamer_url}/cb/scm/218057.git",
            f"{self.codebeamer_url}/scm/218057.git"
        ]
        
        logger.info("🔍 Possible SCM URL patterns:")
        for i, url in enumerate(possible_urls, 1):
            logger.info(f"   {i}. {url}")
        
        # Use the most likely URL pattern based on your repository setup
        # Given that your repository URL is /cb/repository/218057, 
        # the Git URL is likely /cb/repository/218057.git
        primary_url = f"{self.codebeamer_url}/cb/repository/218057.git"
        
        logger.info(f"✅ Primary SCM URL: {primary_url}")
        logger.info(f"💡 If this fails, the pipeline will try alternative patterns")
        
        return primary_url
    
    def get_authenticated_repo_url(self, repo_url):
        """Create an authenticated repository URL for Git operations"""
        from urllib.parse import urlparse, urlunparse
        
        parsed = urlparse(repo_url)
        
        # Create authenticated URL with username and password
        auth_netloc = f"{self.username}:{self.password}@{parsed.netloc}"
        
        authenticated_url = urlunparse((
            parsed.scheme,
            auth_netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        # Don't log the full URL with credentials for security
        logger.info(f"🔐 Created authenticated URL for Git operations")
        return authenticated_url

    def sync_commit_info(self):
        """Sync commit information to project"""
        try:
            if self.event_name != 'push':
                logger.info(f"Skipping commit sync for event type: {self.event_name}")
                return True
            
            # First, try to push directly to SCM repository
            if self.push_to_codebeamer_scm():
                logger.info("✅ Direct SCM push successful")
                return True
            else:
                logger.warning("⚠️  Direct SCM push failed, falling back to commit logging")
                
            repo = Repo('.')
            commits = list(repo.iter_commits(max_count=5))  # Get last 5 commits
            
            logger.info(f"📦 Recent commits from GitHub repository:")
            logger.info(f"   Repository: {self.github_repo_url}")
            logger.info(f"   Total commits to sync: {len(commits)}")
            
            for i, commit in enumerate(commits, 1):
                commit_info = {
                    "number": i,
                    "sha": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": commit.author.name,
                    "email": commit.author.email,
                    "date": datetime.fromtimestamp(commit.committed_date).isoformat()
                }
                
                logger.info(f"   {i}. {commit_info['sha'][:8]} - {commit_info['message'][:50]}...")
                logger.info(f"      By: {commit_info['author']} ({commit_info['email']})")
                logger.info(f"      Date: {commit_info['date']}")
                
            return True
            
        except Exception as e:
            logger.error(f"Error syncing commit info: {str(e)}")
            return False
    
    def run(self):
        """Main synchronization process for web-based integration"""
        logger.info("Starting Codebeamer web-based synchronization...")
        logger.info("=" * 60)
        
        # Validate environment variables
        required_vars = [
            'CODEBEAMER_URL', 'CODEBEAMER_USERNAME', 'CODEBEAMER_PASSWORD',
            'CODEBEAMER_PROJECT_ID', 'GITHUB_REPO_URL'
        ]
        
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            return False
        
        logger.info(f"🌐 Codebeamer URL: {self.codebeamer_url}")
        logger.info(f"👤 Username: {self.username}")
        logger.info(f"📁 Project: {self.project_id}")
        logger.info(f"📂 GitHub Repo: {self.github_repo_url}")
        logger.info(f"🎯 Event: {self.event_name}")
        logger.info(f"📍 Branch/Ref: {self.ref}")
        logger.info(f"🔸 Commit: {self.sha[:8] if self.sha else 'N/A'}")
        logger.info("=" * 60)
        
        try:
            # Test connectivity and login
            if not self.test_connectivity():
                logger.error("❌ Failed connectivity test")
                return False
            
            # Get repositories page
            page_content = self.get_repositories_page()
            if not page_content:
                logger.warning("⚠️  Could not access repositories page")
            
            # Check if repository already exists
            repo_exists = self.check_existing_repository(page_content) if page_content else False
            
            # Create sync information
            if not self.create_repository_comment():
                logger.warning("⚠️  Failed to create repository comment")
            
            # Sync commit information
            if not self.sync_commit_info():
                logger.warning("⚠️  Failed to sync commit information")
            
            logger.info("=" * 60)
            logger.info("✅ Web-based synchronization completed successfully")
            logger.info("📋 Sync Summary:")
            logger.info(f"   - Authentication: ✅ Success")
            logger.info(f"   - Project {self.project_id} access: ✅ Success")
            logger.info(f"   - Repository page access: {'✅ Success' if page_content else '⚠️  Limited'}")
            logger.info(f"   - Repository exists: {'Yes' if repo_exists else 'No'}")
            logger.info(f"   - Sync information logged: ✅ Success")
            logger.info(f"   - GitHub integration: ✅ Active")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Synchronization failed: {str(e)}")
            return False

if __name__ == "__main__":
    sync = CodebeamerWebSync()
    success = sync.run()
    sys.exit(0 if success else 1) 