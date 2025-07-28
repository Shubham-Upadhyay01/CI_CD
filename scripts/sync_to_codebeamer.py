#!/usr/bin/env python3
"""
Codebeamer SCM Synchronization Script
Syncs GitHub repository changes to Codebeamer SCM repositories in real-time
"""

import os
import sys
import json
import requests
import base64
from datetime import datetime
from git import Repo
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CodebeamerSync:
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
        
    def get_or_create_scm_repository(self):
        """Get existing SCM repository or create a new one"""
        try:
            # First, try to find existing SCM repository
            scm_repos_url = f"{self.codebeamer_url}/rest/v3/projects/{self.project_id}/scmRepositories"
            response = self.session.get(scm_repos_url)
            
            if response.status_code == 200:
                repositories = response.json()
                for repo in repositories:
                    if repo.get('repositoryUrl') == self.github_repo_url:
                        logger.info(f"Found existing SCM repository: {repo['id']}")
                        return repo['id']
            
            # Create new SCM repository if not found
            repo_data = {
                "name": f"GitHub-{os.path.basename(self.github_repo_url)}",
                "description": f"Auto-synced from GitHub repository {self.github_repo_url}",
                "repositoryUrl": self.github_repo_url,
                "type": "GIT",
                "projectId": int(self.project_id)
            }
            
            create_response = self.session.post(scm_repos_url, json=repo_data)
            
            if create_response.status_code in [200, 201]:
                new_repo = create_response.json()
                logger.info(f"Created new SCM repository: {new_repo['id']}")
                return new_repo['id']
            else:
                logger.error(f"Failed to create SCM repository: {create_response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error managing SCM repository: {str(e)}")
            return None
    
    def sync_commits(self, scm_repo_id):
        """Sync commit information to Codebeamer"""
        try:
            repo = Repo('.')
            
            # Get recent commits (last 10 or since last sync)
            commits = list(repo.iter_commits(max_count=10))
            
            for commit in commits:
                commit_data = {
                    "revision": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": commit.author.name,
                    "authorEmail": commit.author.email,
                    "date": datetime.fromtimestamp(commit.committed_date).isoformat(),
                    "repositoryId": scm_repo_id
                }
                
                # Post commit to Codebeamer
                commits_url = f"{self.codebeamer_url}/rest/v3/scmRepositories/{scm_repo_id}/commits"
                response = self.session.post(commits_url, json=commit_data)
                
                if response.status_code in [200, 201]:
                    logger.info(f"Synced commit: {commit.hexsha[:8]} - {commit.message.strip()[:50]}")
                elif response.status_code == 409:
                    logger.info(f"Commit already exists: {commit.hexsha[:8]}")
                else:
                    logger.warning(f"Failed to sync commit {commit.hexsha}: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error syncing commits: {str(e)}")
    
    def update_repository_status(self, scm_repo_id):
        """Update repository status and metadata"""
        try:
            repo = Repo('.')
            
            # Get current branch information
            current_branch = repo.active_branch.name if not repo.head.is_detached else 'detached'
            
            # Get repository statistics
            total_commits = len(list(repo.iter_commits()))
            branches = [ref.name.replace('origin/', '') for ref in repo.remote().refs]
            
            status_data = {
                "currentBranch": current_branch,
                "totalCommits": total_commits,
                "branches": branches,
                "lastSync": datetime.now().isoformat(),
                "syncedBy": self.actor
            }
            
            # Update repository metadata
            update_url = f"{self.codebeamer_url}/rest/v3/scmRepositories/{scm_repo_id}"
            response = self.session.put(update_url, json=status_data)
            
            if response.status_code == 200:
                logger.info("Updated repository status successfully")
            else:
                logger.warning(f"Failed to update repository status: {response.text}")
                
        except Exception as e:
            logger.error(f"Error updating repository status: {str(e)}")
    
    def handle_branch_events(self, scm_repo_id):
        """Handle branch creation/deletion events"""
        try:
            if self.event_name == 'create':
                branch_name = self.ref.replace('refs/heads/', '')
                logger.info(f"Branch created: {branch_name}")
                
                # Notify Codebeamer about new branch
                branch_data = {
                    "name": branch_name,
                    "sha": self.sha,
                    "created": datetime.now().isoformat(),
                    "creator": self.actor
                }
                
                branches_url = f"{self.codebeamer_url}/rest/v3/scmRepositories/{scm_repo_id}/branches"
                response = self.session.post(branches_url, json=branch_data)
                
                if response.status_code in [200, 201]:
                    logger.info(f"Notified Codebeamer about new branch: {branch_name}")
                    
            elif self.event_name == 'delete':
                branch_name = self.ref.replace('refs/heads/', '')
                logger.info(f"Branch deleted: {branch_name}")
                
                # Notify Codebeamer about deleted branch
                delete_url = f"{self.codebeamer_url}/rest/v3/scmRepositories/{scm_repo_id}/branches/{branch_name}"
                response = self.session.delete(delete_url)
                
                if response.status_code in [200, 204]:
                    logger.info(f"Notified Codebeamer about deleted branch: {branch_name}")
                    
        except Exception as e:
            logger.error(f"Error handling branch events: {str(e)}")
    
    def run(self):
        """Main synchronization process"""
        logger.info("Starting Codebeamer synchronization...")
        
        # Validate environment variables
        required_vars = [
            'CODEBEAMER_URL', 'CODEBEAMER_USERNAME', 'CODEBEAMER_PASSWORD',
            'CODEBEAMER_PROJECT_ID', 'GITHUB_REPO_URL'
        ]
        
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            return False
        
        try:
            # Get or create SCM repository
            scm_repo_id = self.get_or_create_scm_repository()
            if not scm_repo_id:
                logger.error("Failed to get or create SCM repository")
                return False
            
            # Sync commits for push events
            if self.event_name == 'push':
                self.sync_commits(scm_repo_id)
                self.update_repository_status(scm_repo_id)
            
            # Handle branch events
            if self.event_name in ['create', 'delete']:
                self.handle_branch_events(scm_repo_id)
            
            # Handle pull request events
            if self.event_name == 'pull_request':
                logger.info("Pull request event detected - monitoring for merge")
            
            logger.info("Codebeamer synchronization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Synchronization failed: {str(e)}")
            return False

if __name__ == "__main__":
    sync = CodebeamerSync()
    success = sync.run()
    sys.exit(0 if success else 1) 