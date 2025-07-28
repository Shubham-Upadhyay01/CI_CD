#!/usr/bin/env python3
"""
Notify on synchronization failure
"""

import os
import sys
import requests
import base64
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FailureNotifier:
    def __init__(self):
        self.codebeamer_url = os.environ.get('CODEBEAMER_URL')
        self.username = os.environ.get('CODEBEAMER_USERNAME')
        self.password = os.environ.get('CODEBEAMER_PASSWORD')
        self.project_id = os.environ.get('CODEBEAMER_PROJECT_ID')
        
        # GitHub event information
        self.github_repo = os.environ.get('GITHUB_REPOSITORY', 'Unknown')
        self.github_sha = os.environ.get('GITHUB_SHA', 'Unknown')
        self.github_ref = os.environ.get('GITHUB_REF', 'Unknown')
        self.github_actor = os.environ.get('GITHUB_ACTOR', 'Unknown')
        self.github_run_id = os.environ.get('GITHUB_RUN_ID', 'Unknown')
        
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
    
    def create_failure_ticket(self):
        """Create a failure ticket in Codebeamer"""
        try:
            ticket_data = {
                "name": f"GitHub Sync Failure - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "description": f"""GitHub to Codebeamer synchronization failed.

**Details:**
- Repository: {self.github_repo}
- Commit SHA: {self.github_sha}
- Branch/Ref: {self.github_ref}
- Triggered by: {self.github_actor}
- GitHub Run ID: {self.github_run_id}
- Failure Time: {datetime.now().isoformat()}

**Action Required:**
Please investigate the synchronization failure and ensure proper connectivity between GitHub and Codebeamer.

**GitHub Actions Log:**
https://github.com/{self.github_repo}/actions/runs/{self.github_run_id}
""",
                "priority": {"name": "High"},
                "status": {"name": "New"},
                "assignedTo": [{"name": self.username}],
                "projectId": int(self.project_id)
            }
            
            # Create ticket
            tickets_url = f"{self.codebeamer_url}/rest/v3/projects/{self.project_id}/items"
            response = self.session.post(tickets_url, json=ticket_data)
            
            if response.status_code in [200, 201]:
                ticket = response.json()
                logger.info(f"Created failure ticket: {ticket.get('id')}")
                return ticket.get('id')
            else:
                logger.error(f"Failed to create failure ticket: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating failure ticket: {str(e)}")
            return None
    
    def send_notification_comment(self, ticket_id=None):
        """Send notification comment to existing items or create new one"""
        try:
            if not ticket_id:
                ticket_id = self.create_failure_ticket()
            
            if ticket_id:
                comment_data = {
                    "comment": f"""🚨 **GitHub Synchronization Failure Alert**

The automated synchronization from GitHub repository `{self.github_repo}` to Codebeamer has failed.

**Failed Commit:** {self.github_sha[:8]}
**Branch:** {self.github_ref.replace('refs/heads/', '')}
**Triggered by:** {self.github_actor}
**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Please check the GitHub Actions logs for detailed error information and resolve the synchronization issue promptly.
""",
                    "commentFormat": "Wiki"
                }
                
                comment_url = f"{self.codebeamer_url}/rest/v3/items/{ticket_id}/comments"
                response = self.session.post(comment_url, json=comment_data)
                
                if response.status_code in [200, 201]:
                    logger.info(f"Added failure notification comment to ticket {ticket_id}")
                else:
                    logger.warning(f"Failed to add notification comment: {response.text}")
            
        except Exception as e:
            logger.error(f"Error sending notification comment: {str(e)}")
    
    def log_failure_details(self):
        """Log comprehensive failure details"""
        logger.error("="*60)
        logger.error("GITHUB TO CODEBEAMER SYNCHRONIZATION FAILURE")
        logger.error("="*60)
        logger.error(f"Repository: {self.github_repo}")
        logger.error(f"Commit SHA: {self.github_sha}")
        logger.error(f"Branch/Ref: {self.github_ref}")
        logger.error(f"Actor: {self.github_actor}")
        logger.error(f"Run ID: {self.github_run_id}")
        logger.error(f"Timestamp: {datetime.now().isoformat()}")
        logger.error(f"Codebeamer URL: {self.codebeamer_url}")
        logger.error(f"Project ID: {self.project_id}")
        logger.error("="*60)
    
    def run(self):
        """Main notification process"""
        logger.info("Processing synchronization failure notification...")
        
        try:
            # Log detailed failure information
            self.log_failure_details()
            
            # Create failure ticket and notification
            ticket_id = self.create_failure_ticket()
            
            if ticket_id:
                self.send_notification_comment(ticket_id)
                logger.info("Failure notification process completed")
            else:
                logger.error("Failed to create failure notification")
            
            return True
            
        except Exception as e:
            logger.error(f"Failure notification process failed: {str(e)}")
            return False

if __name__ == "__main__":
    notifier = FailureNotifier()
    notifier.run()
    # Always exit with 0 for notification script - don't fail the pipeline
    sys.exit(0) 