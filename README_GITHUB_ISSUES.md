# 🚀 GitHub Issues Automation for CS2 Analytics

Complete automation suite to create **33 production-ready GitHub issues** with labels, milestones, and detailed documentation for deploying CS2 Analytics to production.

## 📁 Files Included

| File                      | Purpose                                                  |
| ------------------------- | -------------------------------------------------------- |
| `create_github_issues.py` | Main script to create all issues, labels, and milestones |
| `setup_github_issues.py`  | Setup script to install dependencies and create .env     |
| `preflight_check.py`      | Verification script to test everything before running    |
| `create_issues.bat`       | Windows one-click batch script (runs all 3 scripts)      |
| `.env.example`            | Template for environment variables                       |
| `ISSUE_CREATION_GUIDE.md` | Comprehensive usage guide                                |
| `GITHUB_ISSUES_README.md` | Detailed documentation                                   |

## ⚡ Quick Start (Choose One)

### Option 1: Windows One-Click (Easiest)

```cmd
create_issues.bat
```

This will:

1. Install dependencies
2. Create .env file
3. Run pre-flight checks
4. Create all GitHub issues (with confirmation)

### Option 2: Manual Step-by-Step

```bash
# Step 1: Setup
python setup_github_issues.py

# Step 2: Add your GitHub token to .env
# GITHUB_TOKEN=ghp_your_token_here

# Step 3: Verify everything
python preflight_check.py

# Step 4: Create issues
python create_github_issues.py
```

## 🔑 Getting Your GitHub Token

1. Visit: **https://github.com/settings/tokens**
2. Click **"Generate new token (classic)"**
3. Name: `CS2 Analytics Issue Creator`
4. Select scope: ✅ **repo** (Full control)
5. Click **"Generate token"**
6. **Copy immediately** (you won't see it again!)
7. Add to `.env`: `GITHUB_TOKEN=ghp_your_token_here`

## 📊 What Gets Created

### 🏷️ Labels (44 total)

**Priority Tiers:**

- 🔴 `priority: critical` (8 issues) - Blocking production
- 🟠 `priority: high` (11 issues) - Important for production
- 🟡 `priority: medium` (11 issues) - Nice to have
- 🟢 `priority: low` (3 issues) - Future enhancements

**Categories:**
`infrastructure`, `backend`, `security`, `api`, `database`, `pipeline`, `testing`, `observability`, `ci-cd`, `operations`, `documentation`

**Technologies:**
`docker`, `aws`, `terraform`, `github-actions`, `postgresql`, `redis`, `sqs`, `cloudwatch`

### 🎯 Milestones (10 phases over 8 weeks)

| Phase        | Focus                     | Issues | Timeline |
| ------------ | ------------------------- | ------ | -------- |
| **Phase 1**  | Infrastructure Foundation | 4      | Week 1-2 |
| **Phase 2**  | Security & Configuration  | 4      | Week 2   |
| **Phase 3**  | Database & Data Quality   | 4      | Week 3   |
| **Phase 4**  | Pipeline Reliability      | 4      | Week 3-4 |
| **Phase 5**  | Testing & QA              | 3      | Week 4   |
| **Phase 6**  | Observability             | 3      | Week 5   |
| **Phase 7**  | CI/CD & Deployment        | 3      | Week 5-6 |
| **Phase 8**  | AWS Scalability           | 2      | Week 6-7 |
| **Phase 9**  | API Enhancement           | 3      | Week 7-8 |
| **Phase 10** | Operations                | 3      | Ongoing  |

### 📝 Issues (33 total)

Each issue includes:

- ✅ **Clear title** with `[Production]` prefix
- ✅ **Why it's needed** - Business justification
- ✅ **Acceptance criteria** - Testable requirements
- ✅ **Implementation notes** - Code examples & guidance
- ✅ **Dependencies** - Related issues that must be done first
- ✅ **Appropriate labels** - Priority, category, technology
- ✅ **Assigned milestone** - Phase tracking

## 🎯 Critical Path Issues

**Must complete before production launch:**

1. **Create Multi-Stage Dockerfile** - Containerization foundation
2. **Docker Compose for Local Dev** - Consistent development environment
3. **Pydantic Configuration** - Type-safe config management
4. **Health Check Endpoints** - AWS load balancer requirements
5. **Secrets Management** - AWS Secrets Manager integration
6. **Structured Logging** - Request tracing and debugging
7. **Rate Limiting** - API protection and DDoS prevention
8. **Security Headers** - Production API hardening
9. **Database Migrations** - Alembic for schema evolution
10. **Connection Retry Logic** - Database resilience
11. **Queue Table Locking** - Prevent duplicate processing
12. **Exponential Backoff** - Scraper reliability
13. **Request Timeouts** - Resource management
14. **CI/CD Pipeline** - Automated testing and deployment
15. **Terraform IaC** - Infrastructure as code

## 📈 Progress Tracking

### View Issues by Priority

```
https://github.com/dardenkyle/CS2-analytics/issues?q=is:issue+label:"priority:+critical"
https://github.com/dardenkyle/CS2-analytics/issues?q=is:issue+label:"priority:+high"
```

### View Issues by Milestone

```
https://github.com/dardenkyle/CS2-analytics/milestones
```

### Create Project Board

1. Go to **Projects** tab in GitHub
2. Create **"Production Deployment Roadmap"**
3. Add columns: `Backlog`, `In Progress`, `Review`, `Done`
4. Add all 33 issues to the board
5. Track progress visually with drag-and-drop

### Use GitHub CLI (Optional)

```bash
# List all production issues
gh issue list --label "priority: critical"

# View specific milestone
gh issue list --milestone "Phase 1: Infrastructure Foundation"

# Assign issue to yourself
gh issue edit 1 --assignee @me
```

## 🔧 Troubleshooting

### "GITHUB_TOKEN not found"

```bash
# Create .env file
python setup_github_issues.py

# Verify .env exists and has token
python preflight_check.py
```

### "Bad credentials" or "Unauthorized"

- Token is invalid or expired
- Regenerate token with `repo` scope
- Update `.env` with new token

### "Resource not accessible by integration"

- Token needs full `repo` scope (not just `public_repo`)
- Verify you're a member/collaborator on the repository
- Check repository settings allow issue creation

### "Issues already exist"

- Script creates issues with unique titles
- If re-running, consider deleting old issues first
- Or modify script to check for existing issues by title

### Rate Limiting (5000 requests/hour)

- Should not be an issue for 33 issues + labels + milestones
- If hit, wait 1 hour or use different token
- Check remaining: https://api.github.com/rate_limit

## 🎨 Customization

### Modify Issue Content

Edit `create_github_issues.py`:

```python
ISSUES = [
    {
        "title": "Your Custom Issue",
        "body": """
## Why It's Needed
Your description here

## Acceptance Criteria
- [ ] Your criteria
        """,
        "labels": ["your-label"],
        "milestone": 1
    },
]
```

### Add New Labels

```python
LABELS = {
    "your-label": {
        "color": "ff0000",  # Hex color
        "description": "Your description"
    },
}
```

### Adjust Milestones

```python
MILESTONES = {
    1: {
        "title": "Your Phase",
        "description": "Phase description",
        "due_on": "2026-01-01"  # ISO 8601 format
    },
}
```

## 📚 Additional Documentation

- **Quick Start Guide**: `ISSUE_CREATION_GUIDE.md`
- **Detailed Documentation**: `GITHUB_ISSUES_README.md`
- **Environment Template**: `.env.example`

## 🔒 Security

**Important:**

- ✅ `.env` is in `.gitignore` - Your token is safe
- ✅ Never commit `.env` file to Git
- ✅ Keep GitHub token secure and private
- ✅ Rotate tokens periodically (every 90 days)
- ✅ Use minimum required permissions (`repo` scope only)
- ✅ Delete tokens when no longer needed

## ✅ Verification Checklist

Before running the script:

- [ ] Python 3.13+ installed
- [ ] Ran `setup_github_issues.py`
- [ ] Created GitHub Personal Access Token
- [ ] Added token to `.env` file
- [ ] Ran `preflight_check.py` successfully
- [ ] Confirmed repository access

## 🎉 Success Indicators

After running the script, you should see:

- ✅ All 44 labels created/updated
- ✅ All 10 milestones created
- ✅ All 33 issues created with proper labels and milestones
- ✅ Issues viewable at: https://github.com/dardenkyle/CS2-analytics/issues
- ✅ No error messages in console output

## 🚀 Next Steps After Creation

1. **Review all issues** - Ensure alignment with priorities
2. **Assign to team members** - Distribute work
3. **Create project board** - Visualize progress
4. **Set branch protection** - Require PR reviews
5. **Start Phase 1** - Begin critical infrastructure work
6. **Schedule weekly reviews** - Track progress and adjust

## 📞 Support

If you encounter issues:

1. Run `preflight_check.py` to diagnose
2. Check the troubleshooting section above
3. Review GitHub API docs: https://docs.github.com/en/rest
4. Create a discussion in the repository

---

**Ready to transform CS2 Analytics into production! 🎯**

_Total estimated time: 8 weeks to production-ready deployment_
