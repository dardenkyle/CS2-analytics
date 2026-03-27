"""
Quick setup script to install dependencies and verify configuration.
Run this before running create_github_issues.py
"""

import subprocess
import sys
import os


def install_dependencies():
    """Install required Python packages."""
    print("📦 Installing required packages...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "PyGithub", "python-dotenv"]
        )
        print("✅ Dependencies installed successfully!\n")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies.")
        return False


def check_env_file():
    """Check if .env file exists and has GitHub token."""
    print("🔍 Checking for .env file...")

    if not os.path.exists(".env"):
        print("⚠️  .env file not found!")
        print("\n📝 Creating .env from template...")

        if os.path.exists(".env.example"):
            with open(".env.example", "r") as example:
                with open(".env", "w") as env:
                    env.write(example.read())
            print("✅ Created .env file from .env.example")
            print("\n⚠️  IMPORTANT: Edit .env and add your GitHub token!")
            print("   1. Go to: https://github.com/settings/tokens")
            print("   2. Generate new token with 'repo' scope")
            print("   3. Copy token to .env file: GITHUB_TOKEN=your_token_here")
            return False
        else:
            print("❌ .env.example not found. Cannot create .env file.")
            return False

    # Check if token exists in .env
    from dotenv import load_dotenv

    load_dotenv()

    token = os.getenv("GITHUB_TOKEN")
    if not token or token == "your_github_token_here":
        print("⚠️  GitHub token not configured in .env file!")
        print("\n📝 Please edit .env and add your GitHub token:")
        print("   1. Go to: https://github.com/settings/tokens")
        print("   2. Generate new token with 'repo' scope")
        print("   3. Copy token to .env file: GITHUB_TOKEN=your_token_here")
        return False

    print(f"✅ GitHub token found (starts with: {token[:7]}...)\n")
    return True


def main():
    """Main setup function."""
    print("=" * 60)
    print("🚀 CS2 Analytics - GitHub Issues Setup")
    print("=" * 60)
    print()

    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed. Please install dependencies manually:")
        print("   pip install PyGithub python-dotenv")
        return

    # Check environment configuration
    env_ok = check_env_file()

    print("=" * 60)
    if env_ok:
        print("✅ Setup complete! You're ready to create GitHub issues.")
        print("\n🎯 Next step:")
        print("   python create_github_issues.py")
    else:
        print("⚠️  Setup incomplete. Please configure your .env file first.")
        print("\n🎯 After adding your GitHub token to .env, run:")
        print("   python create_github_issues.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
