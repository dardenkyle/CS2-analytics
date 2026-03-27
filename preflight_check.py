"""
Pre-flight check script to verify everything is ready before creating issues.
"""

import os
import sys


def check_dependencies():
    """Check if required packages are installed."""
    print("📦 Checking dependencies...")
    try:
        import github
        import dotenv

        print("  ✅ PyGithub installed")
        print("  ✅ python-dotenv installed")
        return True
    except ImportError as e:
        print(f"  ❌ Missing dependency: {e}")
        print("\n  Run: python setup_github_issues.py")
        return False


def check_env_file():
    """Check if .env file exists and is properly configured."""
    print("\n🔍 Checking .env file...")

    if not os.path.exists(".env"):
        print("  ❌ .env file not found")
        print("\n  Run: python setup_github_issues.py")
        return False

    print("  ✅ .env file exists")
    return True


def check_github_token():
    """Verify GitHub token is configured."""
    print("\n🔐 Checking GitHub token...")

    from dotenv import load_dotenv

    load_dotenv()

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        print("  ❌ GITHUB_TOKEN not found in .env")
        print("\n  Add your token to .env:")
        print("  GITHUB_TOKEN=ghp_your_token_here")
        return False

    if token == "your_github_token_here":
        print("  ❌ GITHUB_TOKEN not configured (still has default value)")
        print("\n  Replace with your actual token in .env")
        return False

    if not token.startswith("ghp_") and not token.startswith("github_pat_"):
        print(
            "  ⚠️  Token format looks unusual (expected to start with 'ghp_' or 'github_pat_')"
        )
        print("  Token value:", token[:10] + "...")
        response = input("  Continue anyway? (y/N): ")
        if response.lower() != "y":
            return False

    print(f"  ✅ Token found: {token[:7]}...{token[-4:]}")
    return True


def test_github_connection():
    """Test connection to GitHub and repository access."""
    print("\n🌐 Testing GitHub connection...")

    from dotenv import load_dotenv
    from github import Github, GithubException

    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")

    try:
        g = Github(token)
        user = g.get_user()
        print(f"  ✅ Authenticated as: {user.login}")

        # Test repository access
        print("\n📦 Testing repository access...")
        repo = g.get_repo("dardenkyle/CS2-analytics")
        print(f"  ✅ Repository found: {repo.full_name}")
        print(f"  ✅ Repository permissions: {repo.permissions.push}")

        if not repo.permissions.push:
            print(
                "  ⚠️  Warning: No push permission. You may not be able to create issues."
            )
            return False

        return True

    except GithubException as e:
        print(f"  ❌ GitHub API error: {e}")
        if e.status == 401:
            print("  Token is invalid or expired")
        elif e.status == 404:
            print("  Repository not found or no access")
        return False
    except Exception as e:
        print(f"  ❌ Connection error: {e}")
        return False


def show_summary():
    """Show what will be created."""
    print("\n" + "=" * 60)
    print("📋 SUMMARY: What will be created")
    print("=" * 60)
    print("\n  🏷️  44 Labels (priority, category, technology)")
    print("  🎯 10 Milestones (8-week phased roadmap)")
    print("  📝 33 Issues (production deployment tasks)")
    print("\n  Repository: https://github.com/dardenkyle/CS2-analytics")
    print("=" * 60)


def main():
    """Run all pre-flight checks."""
    print("=" * 60)
    print("✈️  CS2 Analytics - Pre-flight Check")
    print("=" * 60)

    all_good = True

    # Run all checks
    all_good &= check_dependencies()
    all_good &= check_env_file()
    all_good &= check_github_token()
    all_good &= test_github_connection()

    print("\n" + "=" * 60)

    if all_good:
        print("✅ ALL CHECKS PASSED!")
        show_summary()
        print("\n🚀 Ready to create issues!")
        print("\nRun: python create_github_issues.py")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease fix the issues above before proceeding.")
        print("\n💡 Quick fixes:")
        print("  1. Run: python setup_github_issues.py")
        print("  2. Add your GitHub token to .env")
        print("  3. Run this check again: python preflight_check.py")

    print("=" * 60)

    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
