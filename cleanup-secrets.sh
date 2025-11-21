#!/bin/bash

# Script to remove exposed secrets from git history
# WARNING: This will rewrite git history. Backup your repo first!

set -e

echo "🔒 ScholarSphere Security Cleanup Script"
echo "=========================================="
echo ""
echo "⚠️  WARNING: This script will rewrite git history!"
echo "    All team members will need to re-clone the repository."
echo ""
read -p "Have you backed up your repository? (yes/no): " backup_confirm

if [ "$backup_confirm" != "yes" ]; then
    echo "❌ Please backup your repository first!"
    echo "   Run: cd .. && git clone Scholar-sphere-latest Scholar-sphere-backup"
    exit 1
fi

echo ""
echo "📋 This script will:"
echo "  1. Remove hardcoded secrets from git history"
echo "  2. Clean up any remaining sensitive files"
echo "  3. Prepare the repository for a clean push"
echo ""
read -p "Continue? (yes/no): " continue_confirm

if [ "$continue_confirm" != "yes" ]; then
    echo "❌ Aborted by user"
    exit 1
fi

# Check if git-filter-repo is installed
if ! command -v git-filter-repo &> /dev/null; then
    echo ""
    echo "📦 git-filter-repo is not installed. Installing..."
    pip install git-filter-repo || {
        echo "❌ Failed to install git-filter-repo"
        echo "   Please install manually: pip install git-filter-repo"
        exit 1
    }
fi

echo ""
echo "🧹 Cleaning git history..."

# Create a file with strings to replace
cat > /tmp/secrets-to-remove.txt <<EOF
StrongPassword123!
test123!
somethingsomething1
somethingsomething
EOF

# Use BFG Repo-Cleaner if available, otherwise use git-filter-repo
if command -v bfg &> /dev/null; then
    echo "Using BFG Repo-Cleaner..."
    bfg --replace-text /tmp/secrets-to-remove.txt
else
    echo "Using git-filter-repo..."
    
    # Remove specific files from history
    git filter-repo --force --invert-paths \
        --path Frontend-service/target/ \
        --path '*/.env' \
        --path '**/.DS_Store'
    
    # Replace sensitive strings in commit messages and file contents
    git filter-repo --force --replace-text /tmp/secrets-to-remove.txt
fi

# Clean up
rm /tmp/secrets-to-remove.txt

echo ""
echo "✅ Git history cleaned!"
echo ""
echo "📝 Next steps:"
echo "  1. Review the changes: git log"
echo "  2. Force push to remote: git push origin --force --all"
echo "  3. Force push tags: git push origin --force --tags"
echo "  4. Notify all team members to re-clone the repository"
echo "  5. Rotate all exposed credentials immediately!"
echo ""
echo "🔑 Credentials to rotate:"
echo "  - MySQL passwords (was: StrongPassword123!)"
echo "  - Neo4j password (was: test123!)"
echo "  - GROQ API Key"
echo "  - OpenAI API Key"
echo ""
echo "📚 See SECURITY.md for detailed instructions"
