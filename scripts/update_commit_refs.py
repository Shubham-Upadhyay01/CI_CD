#!/usr/bin/env python3
"""
Update Codebeamer commit references and link commits to work items
"""

import os
import sys
import re
import requests
import base64
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CommitReferenceUpdater:
    def __init__(self):
        self.codebeamer_url = os.environ.get('CODEBEAMER_URL')
        self.username = os.environ.get('CODEBEAMER_USERNAME')
        self.password = os.environ.get('CODEBEAMER_PASSWORD')
        self.project_id = os.environ.get('CODEBEAMER_PROJECT_ID')
        
        # Commit information
        self.commit_message = os.environ.get('COMMIT_MESSAGE', '')
        self.commit_author = os.environ.get('COMMIT_AUTHOR', '')
        self.commit_timestamp = os.environ.get('COMMIT_TIMESTAMP', '')
        self.github_sha = os.environ.get('GITHUB_SHA', '')
        
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
    
    def extract_work_item_references(self):
        """Extract work item references from commit message"""
        # Common patterns for work item references
        patterns = [
            r'#(\d+)',           # #123
            r'CB-(\d+)',         # CB-123
            r'ITEM-(\d+)',       # ITEM-123
            r'(?:fixes?|closes?|resolves?)\s*#(\d+)',  # fixes #123
            r'(?:refs?|references?)\s*#(\d+)',         # refs #123
        ]
        
        work_items = set()
        for pattern in patterns:
            matches = re.findall(pattern, self.commit_message, re.IGNORECASE)
            work_items.update(matches)
        
        return list(work_items)
    
    def link_commit_to_work_item(self, work_item_id):
        """Link commit to a specific work item"""
        try:
            # Create a comment on the work item with commit information
            comment_data = {
                "comment": f"Commit {self.github_sha[:8]} by {self.commit_author}\n\n"
                          f"Message: {self.commit_message}\n"
                          f"Timestamp: {self.commit_timestamp}\n"
                          f"Full SHA: {self.github_sha}",
                "commentFormat": "PlainText"
            }
            
            comment_url = f"{self.codebeamer_url}/rest/v3/items/{work_item_id}/comments"
            response = self.session.post(comment_url, json=comment_data)
            
            if response.status_code in [200, 201]:
                logger.info(f"Linked commit {self.github_sha[:8]} to work item {work_item_id}")
                
                # Also try to update work item status if commit indicates completion
                if any(keyword in self.commit_message.lower() for keyword in ['fixes', 'closes', 'resolves', 'completed']):
                    self.update_work_item_status(work_item_id)
                    
            else:
                logger.warning(f"Failed to link commit to work item {work_item_id}: {response.text}")
                
        except Exception as e:
            logger.error(f"Error linking commit to work item {work_item_id}: {str(e)}")
    
    def update_work_item_status(self, work_item_id):
        """Update work item status based on commit keywords"""
        try:
            # Get current work item to check its status
            item_url = f"{self.codebeamer_url}/rest/v3/items/{work_item_id}"
            response = self.session.get(item_url)
            
            if response.status_code == 200:
                work_item = response.json()
                current_status = work_item.get('status', {}).get('name', '').lower()
                
                # Only update if not already in a final state
                if current_status not in ['closed', 'resolved', 'done', 'completed']:
                    # Determine new status based on commit message
                    new_status = None
                    if any(keyword in self.commit_message.lower() for keyword in ['fixes', 'closes', 'resolves']):
                        new_status = 'Resolved'
                    elif 'completed' in self.commit_message.lower():
                        new_status = 'Done'
                    
                    if new_status:
                        update_data = {
                            "status": {"name": new_status}
                        }
                        
                        update_response = self.session.put(item_url, json=update_data)
                        if update_response.status_code == 200:
                            logger.info(f"Updated work item {work_item_id} status to {new_status}")
                        else:
                            logger.warning(f"Failed to update work item status: {update_response.text}")
            
        except Exception as e:
            logger.error(f"Error updating work item status: {str(e)}")
    
    def create_commit_reference(self):
        """Create a commit reference in Codebeamer"""
        try:
            commit_ref_data = {
                "name": f"Commit {self.github_sha[:8]}",
                "description": f"GitHub commit reference\n\nAuthor: {self.commit_author}\nMessage: {self.commit_message}",
                "type": "Git Commit",
                "externalId": self.github_sha,
                "projectId": int(self.project_id),
                "createdAt": self.commit_timestamp or datetime.now().isoformat()
            }
            
            # Create commit reference as a document or reference item
            refs_url = f"{self.codebeamer_url}/rest/v3/projects/{self.project_id}/items"
            response = self.session.post(refs_url, json=commit_ref_data)
            
            if response.status_code in [200, 201]:
                ref_item = response.json()
                logger.info(f"Created commit reference: {ref_item.get('id')}")
                return ref_item.get('id')
            else:
                logger.warning(f"Failed to create commit reference: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating commit reference: {str(e)}")
            return None
    
    def run(self):
        """Main process to update commit references"""
        logger.info("Starting commit reference update...")
        
        try:
            # Extract work item references from commit message
            work_items = self.extract_work_item_references()
            logger.info(f"Found work item references: {work_items}")
            
            # Link commit to referenced work items
            for work_item_id in work_items:
                self.link_commit_to_work_item(work_item_id)
            
            # Create general commit reference
            commit_ref_id = self.create_commit_reference()
            
            # Log commit information
            logger.info(f"Processed commit: {self.github_sha[:8]}")
            logger.info(f"Author: {self.commit_author}")
            logger.info(f"Message: {self.commit_message}")
            logger.info(f"Linked to {len(work_items)} work items")
            
            return True
            
        except Exception as e:
            logger.error(f"Commit reference update failed: {str(e)}")
            return False

if __name__ == "__main__":
    updater = CommitReferenceUpdater()
    success = updater.run()
    sys.exit(0 if success else 1) 