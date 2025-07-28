#!/usr/bin/env python3
"""
GitHub Webhook Handler for Real-time Codebeamer Synchronization
This script can be deployed as a standalone service to handle GitHub webhooks
"""

import os
import sys
import json
import hashlib
import hmac
import requests
import base64
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitHubWebhookHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.codebeamer_url = os.environ.get('CODEBEAMER_URL')
        self.username = os.environ.get('CODEBEAMER_USERNAME')
        self.password = os.environ.get('CODEBEAMER_PASSWORD')
        self.project_id = os.environ.get('CODEBEAMER_PROJECT_ID')
        self.webhook_secret = os.environ.get('WEBHOOK_SECRET')
        
        self.session = requests.Session()
        self._setup_auth()
        
        super().__init__(*args, **kwargs)
    
    def _setup_auth(self):
        """Setup authentication for Codebeamer API"""
        if self.username and self.password:
            auth_string = f"{self.username}:{self.password}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            self.session.headers.update({
                'Authorization': f'Basic {auth_b64}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
    
    def verify_signature(self, payload_body, signature_header):
        """Verify GitHub webhook signature"""
        if not self.webhook_secret:
            logger.warning("No webhook secret configured - skipping signature verification")
            return True
        
        if not signature_header:
            logger.error("No signature header found")
            return False
        
        # GitHub sends signature as 'sha256=<hash>'
        if not signature_header.startswith('sha256='):
            logger.error("Invalid signature format")
            return False
        
        expected_signature = signature_header[7:]  # Remove 'sha256=' prefix
        
        # Calculate expected signature
        secret = self.webhook_secret.encode('utf-8')
        calculated_signature = hmac.new(
            secret, 
            payload_body, 
            hashlib.sha256
        ).hexdigest()
        
        # Secure compare
        return hmac.compare_digest(expected_signature, calculated_signature)
    
    def sync_repository_to_codebeamer(self, repo_data):
        """Sync repository information to Codebeamer"""
        try:
            # Check if SCM repository exists
            scm_repos_url = f"{self.codebeamer_url}/rest/v3/projects/{self.project_id}/scmRepositories"
            response = self.session.get(scm_repos_url)
            
            repo_url = repo_data.get('clone_url') or repo_data.get('html_url')
            existing_repo_id = None
            
            if response.status_code == 200:
                repositories = response.json()
                for repo in repositories:
                    if repo.get('repositoryUrl') == repo_url:
                        existing_repo_id = repo['id']
                        break
            
            if not existing_repo_id:
                # Create new SCM repository
                new_repo_data = {
                    "name": f"GitHub-{repo_data.get('name', 'Unknown')}",
                    "description": f"Auto-synced from {repo_url}\n\n{repo_data.get('description', '')}",
                    "repositoryUrl": repo_url,
                    "type": "GIT",
                    "projectId": int(self.project_id)
                }
                
                create_response = self.session.post(scm_repos_url, json=new_repo_data)
                if create_response.status_code in [200, 201]:
                    new_repo = create_response.json()
                    logger.info(f"Created new SCM repository: {new_repo['id']}")
                    return new_repo['id']
                else:
                    logger.error(f"Failed to create SCM repository: {create_response.text}")
                    return None
            else:
                logger.info(f"Using existing SCM repository: {existing_repo_id}")
                return existing_repo_id
                
        except Exception as e:
            logger.error(f"Error syncing repository: {str(e)}")
            return None
    
    def handle_push_event(self, payload):
        """Handle GitHub push events"""
        try:
            repository = payload.get('repository', {})
            commits = payload.get('commits', [])
            ref = payload.get('ref', '')
            pusher = payload.get('pusher', {})
            
            logger.info(f"Processing push to {ref} with {len(commits)} commits")
            
            # Sync repository
            scm_repo_id = self.sync_repository_to_codebeamer(repository)
            if not scm_repo_id:
                return False
            
            # Sync commits
            for commit in commits:
                commit_data = {
                    "revision": commit.get('id', ''),
                    "message": commit.get('message', ''),
                    "author": commit.get('author', {}).get('name', ''),
                    "authorEmail": commit.get('author', {}).get('email', ''),
                    "date": commit.get('timestamp', datetime.now().isoformat()),
                    "repositoryId": scm_repo_id
                }
                
                commits_url = f"{self.codebeamer_url}/rest/v3/scmRepositories/{scm_repo_id}/commits"
                response = self.session.post(commits_url, json=commit_data)
                
                if response.status_code in [200, 201]:
                    logger.info(f"Synced commit: {commit.get('id', '')[:8]}")
                elif response.status_code == 409:
                    logger.info(f"Commit already exists: {commit.get('id', '')[:8]}")
                else:
                    logger.warning(f"Failed to sync commit: {response.text}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling push event: {str(e)}")
            return False
    
    def handle_create_event(self, payload):
        """Handle branch/tag creation events"""
        try:
            ref_type = payload.get('ref_type')
            ref = payload.get('ref')
            repository = payload.get('repository', {})
            
            logger.info(f"Processing {ref_type} creation: {ref}")
            
            scm_repo_id = self.sync_repository_to_codebeamer(repository)
            if not scm_repo_id:
                return False
            
            if ref_type == 'branch':
                branch_data = {
                    "name": ref,
                    "created": datetime.now().isoformat(),
                    "creator": payload.get('sender', {}).get('login', 'Unknown')
                }
                
                branches_url = f"{self.codebeamer_url}/rest/v3/scmRepositories/{scm_repo_id}/branches"
                response = self.session.post(branches_url, json=branch_data)
                
                if response.status_code in [200, 201]:
                    logger.info(f"Notified about new branch: {ref}")
                else:
                    logger.warning(f"Failed to notify about branch creation: {response.text}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling create event: {str(e)}")
            return False
    
    def handle_delete_event(self, payload):
        """Handle branch/tag deletion events"""
        try:
            ref_type = payload.get('ref_type')
            ref = payload.get('ref')
            repository = payload.get('repository', {})
            
            logger.info(f"Processing {ref_type} deletion: {ref}")
            
            scm_repo_id = self.sync_repository_to_codebeamer(repository)
            if not scm_repo_id:
                return False
            
            if ref_type == 'branch':
                delete_url = f"{self.codebeamer_url}/rest/v3/scmRepositories/{scm_repo_id}/branches/{ref}"
                response = self.session.delete(delete_url)
                
                if response.status_code in [200, 204]:
                    logger.info(f"Notified about deleted branch: {ref}")
                else:
                    logger.warning(f"Failed to notify about branch deletion: {response.text}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling delete event: {str(e)}")
            return False
    
    def handle_pull_request_event(self, payload):
        """Handle pull request events"""
        try:
            action = payload.get('action')
            pull_request = payload.get('pull_request', {})
            repository = payload.get('repository', {})
            
            logger.info(f"Processing pull request {action}: #{pull_request.get('number')}")
            
            # For now, just log the event - could be extended to create work items
            scm_repo_id = self.sync_repository_to_codebeamer(repository)
            
            if action in ['opened', 'synchronize', 'reopened']:
                # Could create work items or comments for PR tracking
                logger.info(f"Pull request tracking: {pull_request.get('title', 'No title')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling pull request event: {str(e)}")
            return False
    
    def do_POST(self):
        """Handle POST requests from GitHub webhooks"""
        try:
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'No content')
                return
            
            # Read payload
            payload_body = self.rfile.read(content_length)
            
            # Verify signature
            signature = self.headers.get('X-Hub-Signature-256')
            if not self.verify_signature(payload_body, signature):
                logger.error("Invalid webhook signature")
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'Invalid signature')
                return
            
            # Parse JSON payload
            try:
                payload = json.loads(payload_body.decode('utf-8'))
            except json.JSONDecodeError:
                logger.error("Invalid JSON payload")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'Invalid JSON')
                return
            
            # Get event type
            event_type = self.headers.get('X-GitHub-Event')
            logger.info(f"Received {event_type} event")
            
            # Handle different event types
            success = False
            if event_type == 'push':
                success = self.handle_push_event(payload)
            elif event_type == 'create':
                success = self.handle_create_event(payload)
            elif event_type == 'delete':
                success = self.handle_delete_event(payload)
            elif event_type == 'pull_request':
                success = self.handle_pull_request_event(payload)
            elif event_type == 'ping':
                logger.info("Webhook ping received")
                success = True
            else:
                logger.warning(f"Unhandled event type: {event_type}")
                success = True  # Don't fail for unhandled events
            
            # Send response
            if success:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'OK')
            else:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'Sync failed')
                
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Internal error')
    
    def do_GET(self):
        """Handle GET requests (health check)"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            health_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "codebeamer_url": self.codebeamer_url,
                "project_id": self.project_id
            }
            
            self.wfile.write(json.dumps(health_status).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')
    
    def log_message(self, format, *args):
        """Custom log message format"""
        logger.info(f"HTTP: {format % args}")

def run_webhook_server(port=8080):
    """Run the webhook server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, GitHubWebhookHandler)
    
    logger.info(f"Starting webhook server on port {port}")
    logger.info(f"Health check available at: http://localhost:{port}/health")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down webhook server")
        httpd.server_close()

if __name__ == "__main__":
    # Check required environment variables
    required_vars = ['CODEBEAMER_URL', 'CODEBEAMER_USERNAME', 'CODEBEAMER_PASSWORD', 'CODEBEAMER_PROJECT_ID']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    # Get port from environment or use default
    port = int(os.environ.get('WEBHOOK_PORT', 8080))
    
    run_webhook_server(port) 