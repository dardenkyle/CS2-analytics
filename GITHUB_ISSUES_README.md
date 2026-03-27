# GitHub Issues Creation Script

This script automatically creates all production deployment issues for the CS2 Analytics project.

## Prerequisites

1. **Python 3.13+** installed
2. **GitHub Personal Access Token** with `repo` scope

## Setup Instructions

### Step 1: Install Dependencies

```bash
pip install PyGithub python-dotenv
```

### Step 2: Create GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a descriptive name: "CS2 Analytics Issue Creator"
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again!)

### Step 3: Configure Environment Variables

1. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your GitHub token:
   ```
   GITHUB_TOKEN=ghp_your_actual_token_here
   ```

### Step 4: Run the Script

```bash
python create_github_issues.py
```

## What This Script Does

The script will:

1. **Create 44 Labels** including:

   - Priority levels (critical, high, medium, low)
   - Categories (infrastructure, backend, security, api, etc.)
   - Technologies (docker, aws, terraform, github-actions, etc.)

2. **Create 10 Milestones** representing project phases:

   - Phase 1: Infrastructure Foundation (Week 1-2)
   - Phase 2: Security & Configuration (Week 2)
   - Phase 3: Database & Data Quality (Week 3)
   - Phase 4: Pipeline Reliability (Week 3-4)
   - Phase 5: Testing & Quality Assurance (Week 4)
   - Phase 6: Observability & Monitoring (Week 5)
   - Phase 7: CI/CD & Deployment Automation (Week 5-6)
   - Phase 8: AWS Architecture & Scalability (Week 6-7)
   - Phase 9: API Enhancement & Documentation (Week 7-8)
   - Phase 10: Monitoring & Operations (Ongoing)

3. **Create 33 Issues** with:
   - Detailed descriptions
   - Acceptance criteria
   - Implementation notes
   - Dependencies
   - Appropriate labels and milestones

## Expected Output

```
🔐 Authenticating with GitHub...
📦 Accessing repository: dardenkyle/CS2-analytics

🏷️  Creating labels...
  ✅ Created label: infrastructure
  ✅ Created label: priority: critical
  ✅ Created label: docker
  ...

🎯 Creating milestones...
  ✅ Created milestone: Phase 1: Infrastructure Foundation
  ✅ Created milestone: Phase 2: Security & Configuration
  ...

📝 Creating issues...
  ✅ Created issue #1: [Production] Create Multi-Stage Dockerfile for Application
  ✅ Created issue #2: [Production] Create Docker Compose for Local Development Stack
  ...

✨ All done! Issues created successfully.
🔗 View issues at: https://github.com/dardenkyle/CS2-analytics/issues
```

## Troubleshooting

### "GITHUB_TOKEN not found"

- Make sure you created the `.env` file
- Verify the token is in the correct format: `GITHUB_TOKEN=ghp_...`

### "Bad credentials"

- Token may be expired or invalid
- Generate a new token with `repo` scope

### "Resource not accessible by integration"

- Token needs `repo` scope
- Make sure you have write access to the repository

### Issues Already Exist

- The script will skip existing labels and milestones
- To recreate issues, delete them first or modify the script to check for existing issues

## Customization

You can modify the script to:

- Change issue titles, descriptions, or acceptance criteria
- Adjust milestone dates
- Add/remove labels
- Change priority levels
- Customize for your workflow

## Notes

- All issues are prefixed with `[Production]` for easy filtering
- Issues include detailed acceptance criteria for tracking progress
- Dependencies between issues are documented in issue descriptions
- Estimated timeline: 8 weeks to full production readiness

## Support

If you encounter any issues:

1. Check the error message carefully
2. Verify your GitHub token has correct permissions
3. Ensure you have write access to the repository
4. Review the GitHub API documentation: https://docs.github.com/en/rest
