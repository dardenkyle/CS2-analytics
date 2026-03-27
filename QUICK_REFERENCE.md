# 🚀 Quick Reference Card - GitHub Issues Creation

## ⚡ One-Line Execution

### Windows

```cmd
create_issues.bat
```

### Linux/Mac

```bash
chmod +x create_issues.sh && ./create_issues.sh
```

### Manual

```bash
python create_github_issues.py
```

---

## 📋 Complete Workflow

```bash
# 1. Setup (one time)
python setup_github_issues.py

# 2. Get GitHub Token
https://github.com/settings/tokens
# Scope: ✅ repo

# 3. Add to .env
GITHUB_TOKEN=ghp_your_token_here

# 4. Verify
python preflight_check.py

# 5. Create Issues
python create_github_issues.py
```

---

## 📊 What Gets Created

| Item           | Count | Description                         |
| -------------- | ----- | ----------------------------------- |
| **Labels**     | 44    | Priority, category, technology tags |
| **Milestones** | 10    | 8-week phased roadmap               |
| **Issues**     | 33    | Production deployment tasks         |

---

## 🎯 Priority Breakdown

| Priority    | Count | Timeline                |
| ----------- | ----- | ----------------------- |
| 🔴 Critical | 8     | Week 1-2 (Must have)    |
| 🟠 High     | 11    | Week 2-4 (Important)    |
| 🟡 Medium   | 11    | Week 4-7 (Nice to have) |
| 🟢 Low      | 3     | Week 7+ (Future)        |

---

## 📁 File Reference

| File                      | Purpose                     |
| ------------------------- | --------------------------- |
| `create_github_issues.py` | Main creation script        |
| `setup_github_issues.py`  | One-time setup              |
| `preflight_check.py`      | Pre-run verification        |
| `create_issues.bat`       | Windows automation          |
| `.env`                    | Your GitHub token (private) |
| `.env.example`            | Template                    |

---

## 🔑 GitHub Token Setup

1. **Create**: https://github.com/settings/tokens
2. **Scope**: ✅ `repo` (Full control)
3. **Save**: Add to `.env` as `GITHUB_TOKEN=ghp_...`

---

## 🔍 Verify Success

```bash
# Check if everything is ready
python preflight_check.py

# View created issues
https://github.com/dardenkyle/CS2-analytics/issues

# View milestones
https://github.com/dardenkyle/CS2-analytics/milestones
```

---

## 🚨 Common Errors

| Error             | Fix                                      |
| ----------------- | ---------------------------------------- |
| "Token not found" | Run `setup_github_issues.py`             |
| "Bad credentials" | Check token in `.env`                    |
| "No access"       | Verify `repo` scope on token             |
| "Import error"    | Run `pip install PyGithub python-dotenv` |

---

## 🎯 Critical Path (Must Complete)

1. ✅ Multi-Stage Dockerfile
2. ✅ Docker Compose
3. ✅ Pydantic Config
4. ✅ Health Endpoints
5. ✅ Secrets Manager
6. ✅ Structured Logging
7. ✅ Rate Limiting
8. ✅ Database Migrations
9. ✅ CI/CD Pipeline
10. ✅ Terraform IaC

---

## 📈 Timeline

- **Week 1-2**: Infrastructure (8 issues)
- **Week 3-4**: Database + Pipeline (8 issues)
- **Week 5-6**: Testing + CI/CD (7 issues)
- **Week 7-8**: AWS + API (7 issues)
- **Ongoing**: Operations (3 issues)

**Total: 8 weeks to production**

---

## 🔗 Quick Links

- **Issues**: https://github.com/dardenkyle/CS2-analytics/issues
- **Milestones**: https://github.com/dardenkyle/CS2-analytics/milestones
- **Token Setup**: https://github.com/settings/tokens
- **GitHub API**: https://docs.github.com/en/rest

---

## 💡 Pro Tips

- **Use project board**: Visualize progress
- **Filter by milestone**: Track phase completion
- **Assign issues**: Distribute work
- **Link PRs**: Reference issue numbers in commits
- **Update regularly**: Keep issues current

---

**Save this file for quick reference! 📌**
