#!/usr/bin/env python3
"""
Validate Codebeamer synchronization
"""

import os
import sys
import requests
import base64
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SyncValidator:
    def __init__(self):
        self.codebeamer_url = os.environ.get('CODEBEAMER_URL')
        self.username = os.environ.get('CODEBEAMER_USERNAME')
        self.password = os.environ.get('CODEBEAMER_PASSWORD')
        self.project_id = os.environ.get('CODEBEAMER_PROJECT_ID')
        self.github_sha = os.environ.get('GITHUB_SHA')
        self.github_ref = os.environ.get('GITHUB_REF')
        
        self.session = requests.Session()
        self._setup_auth()
        
    def _setup_auth(self):
        """Setup authentication for Codebeamer API"""
        auth_string = f"{self.username}:{self.password}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.session.headers.update({
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def validate_scm_repository_exists(self):
        """Validate that SCM repository exists in Codebeamer"""
        try:
            scm_repos_url = f"{self.codebeamer_url}/rest/v3/projects/{self.project_id}/scmRepositories"
            response = self.session.get(scm_repos_url)
            
            if response.status_code == 200:
                repositories = response.json()
                if repositories:
                    logger.info(f"✓ Found {len(repositories)} SCM repositories in project")
                    return True
                else:
                    logger.error("✗ No SCM repositories found in project")
                    return False
            else:
                logger.error(f"✗ Failed to retrieve SCM repositories: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error validating SCM repository: {str(e)}")
            return False
    
    def validate_commit_sync(self):
        """Validate that the latest commit was synced"""
        try:
            scm_repos_url = f"{self.codebeamer_url}/rest/v3/projects/{self.project_id}/scmRepositories"
            response = self.session.get(scm_repos_url)
            
            if response.status_code == 200:
                repositories = response.json()
                for repo in repositories:
                    repo_id = repo['id']
                    
                    # Check commits in this repository
                    commits_url = f"{self.codebeamer_url}/rest/v3/scmRepositories/{repo_id}/commits"
                    commits_response = self.session.get(commits_url)
                    
                    if commits_response.status_code == 200:
                        commits = commits_response.json()
                        
                        # Look for the current commit SHA
                        for commit in commits:
                            if commit.get('revision') == self.github_sha:
                                logger.info(f"✓ Found synced commit: {self.github_sha[:8]}")
                                return True
                
                logger.warning(f"⚠ Commit {self.github_sha[:8]} not found in Codebeamer")
                return False
            else:
                logger.error(f"✗ Failed to validate commit sync: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error validating commit sync: {str(e)}")
            return False
    
    def validate_project_connectivity(self):
        """Validate basic connectivity to Codebeamer project"""
        try:
            project_url = f"{self.codebeamer_url}/rest/v3/projects/{self.project_id}"
            response = self.session.get(project_url)
            
            if response.status_code == 200:
                project = response.json()
                logger.info(f"✓ Connected to project: {project.get('name', 'Unknown')}")
                return True
            else:
                logger.error(f"✗ Failed to connect to project: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error validating project connectivity: {str(e)}")
            return False
    
    def validate_user_permissions(self):
        """Validate user has necessary permissions"""
        try:
            user_url = f"{self.codebeamer_url}/rest/v3/user"
            response = self.session.get(user_url)
            
            if response.status_code == 200:
                user = response.json()
                logger.info(f"✓ Authenticated as: {user.get('name', 'Unknown')} ({user.get('email', 'No email')})")
                
                # Check if user has admin permissions
                if user.get('systemAdmin', False):
                    logger.info("✓ User has system administrator permissions")
                    return True
                else:
                    logger.warning("⚠ User does not have system administrator permissions")
                    return True  # Still return True as it might work with project permissions
            else:
                logger.error(f"✗ Failed to validate user permissions: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"✗ Error validating user permissions: {str(e)}")
            return False
    
    def run(self):
        """Run all validation checks"""
        logger.info("Starting Codebeamer synchronization validation...")
        
        validation_results = []
        
        # Run validation checks
        validation_results.append(("Project Connectivity", self.validate_project_connectivity()))
        validation_results.append(("User Permissions", self.validate_user_permissions()))
        validation_results.append(("SCM Repository", self.validate_scm_repository_exists()))
        validation_results.append(("Commit Sync", self.validate_commit_sync()))
        
        # Summary
        passed = sum(1 for _, result in validation_results if result)
        total = len(validation_results)
        
        logger.info(f"\n{'='*50}")
        logger.info(f"VALIDATION SUMMARY: {passed}/{total} checks passed")
        logger.info(f"{'='*50}")
        
        for check_name, result in validation_results:
            status = "✓ PASS" if result else "✗ FAIL"
            logger.info(f"{check_name}: {status}")
        
        if passed == total:
            logger.info("🎉 All validation checks passed!")
            return True
        else:
            logger.error(f"❌ {total - passed} validation check(s) failed")
            return False

if __name__ == "__main__":
    validator = SyncValidator()
    success = validator.run()
    sys.exit(0 if success else 1) 