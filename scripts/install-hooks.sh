#!/bin/bash

# Script to install git hooks
echo "Installing git hooks..."

# Create scripts directory if it doesn't exist
mkdir -p scripts/git-hooks

# Ensure hooks are executable
chmod +x scripts/git-hooks/pre-commit
chmod +x scripts/git-hooks/commit-msg
chmod +x scripts/git-hooks/pre-push

# Remove old symlinks if they exist
rm -f .git/hooks/pre-commit
rm -f .git/hooks/commit-msg
rm -f .git/hooks/pre-push

# Create symlinks from .git/hooks to scripts/git-hooks - use absolute paths
ln -sf "$(pwd)/scripts/git-hooks/pre-commit" .git/hooks/pre-commit
ln -sf "$(pwd)/scripts/git-hooks/commit-msg" .git/hooks/commit-msg
ln -sf "$(pwd)/scripts/git-hooks/pre-push" .git/hooks/pre-push

# Alternative direct file copy approach if symlinks don't work
echo "Additionally copying hooks directly (as backup)..."
cp -f scripts/git-hooks/pre-commit .git/hooks/pre-commit
cp -f scripts/git-hooks/commit-msg .git/hooks/commit-msg
cp -f scripts/git-hooks/pre-push .git/hooks/pre-push

# Ensure direct copies are executable too
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/commit-msg
chmod +x .git/hooks/pre-push

# Verify installation
echo "Verifying hook installation..."
if [ -x .git/hooks/commit-msg ]; then
    echo "✅ commit-msg hook is executable"
else
    echo "❌ commit-msg hook is not executable"
fi

if [ -x .git/hooks/pre-commit ]; then
    echo "✅ pre-commit hook is executable"
else
    echo "❌ pre-commit hook is not executable"
fi

if [ -x .git/hooks/pre-push ]; then
    echo "✅ pre-push hook is executable"
else
    echo "❌ pre-push hook is not executable"
fi

# Fix Git core.hooksPath configuration
git_hooks_path=$(git config core.hooksPath)
if [ "$git_hooks_path" != ".git/hooks" ]; then
    echo "🔧 Setting Git to use hooks from .git/hooks"
    git config core.hooksPath .git/hooks
else
    echo "✅ Git is correctly configured to use hooks from .git/hooks"
fi

echo "Git hooks installed successfully!"
exit 0 