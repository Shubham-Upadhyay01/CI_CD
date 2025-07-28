# GitHub to Codebeamer CI/CD Pipeline Setup Guide
## Philips Sandbox Configuration

This repository contains a complete CI/CD pipeline that automatically synchronizes GitHub repository changes to your Philips Codebeamer sandbox instance in real-time.

## 🎯 Features

- **Real-time synchronization** of commits, branches, and repository changes
- **Automatic SCM repository creation** in Codebeamer
- **Work item linking** through commit message references
- **Branch management** (creation/deletion tracking)
- **Failure notifications** with detailed error reporting
- **Validation checks** to ensure synchronization success

## 📋 Prerequisites

1. **Codebeamer Instance**: Philips Sandbox at `https://www.sandbox.codebeamer.plm.philips.com`
2. **System Administrator Account**: `Shubham.Upadhyay` with system administrator permissions
3. **GitHub Repository**: Repository where you want to enable synchronization
4. **Project ID**: Project 68 in Philips Codebeamer

## 🔧 Setup Instructions

### Step 1: Configure GitHub Secrets

In your GitHub repository, go to **Settings** → **Secrets and variables** → **Actions** and add the following repository secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `CODEBEAMER_URL` | `https://www.sandbox.codebeamer.plm.philips.com` | Philips Codebeamer sandbox URL |
| `CODEBEAMER_USERNAME` | `Shubham.Upadhyay` | Your Codebeamer username |
| `CODEBEAMER_PASSWORD` | `cbpass` | Your Codebeamer password |
| `CODEBEAMER_PROJECT_ID` | `68` | Target project ID in Codebeamer |

### Step 2: Verify Codebeamer Permissions

Ensure your Codebeamer user (`Shubham.Upadhyay`) has:
- ✅ System Administrator permissions
- ✅ Project access to project ID 68
- ✅ SCM repository management permissions
- ✅ REST API access enabled

### Step 3: Enable GitHub Actions

1. Copy the `.github/workflows/codebeamer-sync.yml` file to your repository
2. Copy the `scripts/` directory with all Python files
3. Copy the `requirements.txt` file
4. Commit and push these files to your repository

### Step 4: Test the Pipeline

1. Make a test commit to your repository
2. Check the **Actions** tab in GitHub to see the workflow execution
3. Verify in Codebeamer that:
   - A new SCM repository was created in project 68 (if first run)
   - Your commit appears in the SCM repository
   - Repository metadata is updated

## 🚀 How It Works

### Workflow Triggers

The pipeline is triggered on:
- **Push events** to any branch
- **Pull request** creation/updates
- **Branch creation** events
- **Branch deletion** events

### Synchronization Process

1. **Repository Setup**: Creates or finds existing SCM repository in Codebeamer project 68
2. **Commit Sync**: Transfers commit information including author, message, and timestamp
3. **Branch Management**: Notifies Codebeamer about branch operations
4. **Work Item Linking**: Automatically links commits to referenced work items
5. **Validation**: Verifies synchronization was successful
6. **Failure Handling**: Creates tickets and notifications on errors

### Work Item References

Include work item references in your commit messages to automatically link commits:

```bash
# Examples of supported formats:
git commit -m "Fix authentication bug #123"
git commit -m "Implement feature CB-456"
git commit -m "Resolves #789 - User login issue"
git commit -m "Refs #101 - Update documentation"
```

## 📊 Monitoring and Validation

### GitHub Actions Logs

Monitor synchronization in the **Actions** tab:
- View detailed logs for each synchronization step
- Check validation results
- Review any error messages

### Codebeamer Verification

Check your Philips Codebeamer project 68 for:
- **SCM Repositories**: Navigate to Project 68 → SCM Repositories
- **Commit History**: View synchronized commits and metadata
- **Work Item Links**: Check automatically created comments and references
- **Failure Tickets**: Review any auto-created failure notifications

## 🔍 Troubleshooting

### Common Issues

#### 1. Authentication Failures
```
Error: Failed to authenticate with Codebeamer
```
**Solution**: Verify username/password and ensure REST API access is enabled for `Shubham.Upadhyay`

#### 2. Project Not Found
```
Error: Failed to connect to project
```
**Solution**: Check project ID 68 and user permissions for the target project

#### 3. SCM Repository Creation Failed
```
Error: Failed to create SCM repository
```
**Solution**: Ensure user has SCM management permissions in project 68

#### 4. Commit Sync Issues
```
Warning: Failed to sync commit
```
**Solution**: Check Codebeamer API logs and verify repository configuration

### Debug Mode

Enable debug logging by adding this environment variable in your workflow:
```yaml
env:
  LOG_LEVEL: DEBUG
```

## 📈 Advanced Configuration

### Custom Work Item Patterns

Modify `scripts/update_commit_refs.py` to support custom work item reference patterns:

```python
patterns = [
    r'#(\d+)',           # #123
    r'TASK-(\d+)',       # TASK-123
    r'YOUR-PATTERN-(\d+)' # YOUR-PATTERN-123
]
```

### Webhook Integration

For real-time synchronization, consider setting up webhooks:

1. Configure webhook URL in GitHub repository settings
2. Point to your Codebeamer instance webhook endpoint
3. Use the webhook secret `secrettest` for secure communication

### Notification Customization

Modify `scripts/notify_failure.py` to integrate with:
- Email notifications
- Slack webhooks
- Microsoft Teams
- Custom notification systems

## 🔒 Security Best Practices

1. **Never commit credentials** to your repository
2. **Use GitHub Secrets** for all sensitive information
3. **Regularly rotate passwords** and update secrets
4. **Limit repository access** to authorized users only
5. **Monitor workflow logs** for suspicious activity
6. **Use webhook secrets** for additional security

## 📚 API Reference

### Codebeamer REST API Endpoints Used

- `GET /rest/v3/projects/68` - Project 68 information
- `GET /rest/v3/projects/68/scmRepositories` - List SCM repositories in project 68
- `POST /rest/v3/projects/68/scmRepositories` - Create SCM repository in project 68
- `POST /rest/v3/scmRepositories/{repoId}/commits` - Add commits
- `GET /rest/v3/user` - User information for `Shubham.Upadhyay`
- `POST /rest/v3/items/{itemId}/comments` - Add work item comments

### GitHub Actions Context Variables

- `github.repository` - Repository name
- `github.sha` - Commit SHA
- `github.ref` - Branch/tag reference
- `github.actor` - User who triggered the action
- `github.event` - Event details and payload

## 🆘 Support

For issues and questions:

1. **Check GitHub Actions logs** for detailed error messages
2. **Review Codebeamer API logs** for server-side issues
3. **Verify network connectivity** between GitHub and Philips Codebeamer
4. **Ensure proper permissions** for `Shubham.Upadhyay` and API access
5. **Contact your Philips Codebeamer administrator** for configuration help

## 🎯 Quick Start Commands

### GitHub CLI Setup (if you have GitHub CLI installed):
```bash
# Add all secrets at once
gh secret set CODEBEAMER_URL --body "https://www.sandbox.codebeamer.plm.philips.com"
gh secret set CODEBEAMER_USERNAME --body "Shubham.Upadhyay"
gh secret set CODEBEAMER_PASSWORD --body "cbpass"
gh secret set CODEBEAMER_PROJECT_ID --body "68"
```

### Docker Deployment:
```bash
# Copy environment file
cp env.example .env

# Build and run with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f codebeamer-webhook
```

## 📄 License

This pipeline is provided as-is for integration purposes. Ensure compliance with your organization's security and operational policies.

---

**Configuration**: Philips Sandbox Environment  
**Last Updated**: 2024  
**Version**: 1.0  
**Compatibility**: Codebeamer 22.04+, GitHub Actions 