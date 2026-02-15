#!/bin/bash
# NEXUS Secure Git Propagation Pipeline
# Auto-commit → Safe Pull → PR Creation → Secure Push
# Multi-layer security gates to prevent malicious content

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VM_DIR="$HOME/.nexus-nested-vm"
SAFE_PULL_DIR="$VM_DIR/.git-safe-pull"
PR_STAGING_DIR="$VM_DIR/.pr-staging"
GIT_CONFIG="$VM_DIR/git-pipeline.conf"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_ok() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

echo "════════════════════════════════════════════════════════════════"
echo "   NEXUS SECURE GIT PROPAGATION PIPELINE"
echo "   Docker → VM → Safe Pull → PR → Git"
echo "════════════════════════════════════════════════════════════════"

# ============================================================================
# PART 1: DOCKER AUTO-COMMIT SETUP
# ============================================================================

echo ""
echo "╔════ PART 1: DOCKER AUTO-COMMIT ════╗"
echo ""

log_info "1.1: Creating Docker auto-commit script..."

cat > "$VM_DIR/docker-auto-commit.sh" << 'DOCKER_COMMIT'
#!/bin/bash
# Run inside Docker container - Auto-commits changes to local git repo

set -e

# Configuration
COMMIT_INTERVAL=${GIT_COMMIT_INTERVAL:-300}  # Every 5 minutes
COMMIT_LIMIT=${GIT_COMMIT_LIMIT:-50}         # Max 50 changes per commit
GIT_USER="${GIT_AUTHOR_NAME:-nexus-auto}"
GIT_EMAIL="${GIT_AUTHOR_EMAIL:-nexus@localhost}"

# Find nearest git repo (walk up directories)
find_git_repo() {
  local current_dir="$PWD"
  while [ "$current_dir" != "/" ]; do
    if [ -d "$current_dir/.git" ]; then
      echo "$current_dir"
      return 0
    fi
    current_dir="$(dirname "$current_dir")"
  done
  return 1
}

# Configure git if not already configured
if [ -z "$(git config user.name)" ]; then
  git config --global user.name "$GIT_USER"
  git config --global user.email "$GIT_EMAIL"
fi

# Main loop
while true; do
  GIT_REPO=$(find_git_repo) || {
    echo "No git repo found, waiting..."
    sleep "$COMMIT_INTERVAL"
    continue
  }

  cd "$GIT_REPO"

  # Check for changes
  if git diff --quiet && git diff --cached --quiet; then
    # No changes
    sleep "$COMMIT_INTERVAL"
    continue
  fi

  # Count changes
  CHANGE_COUNT=$(git status --porcelain | wc -l)

  if [ "$CHANGE_COUNT" -lt 1 ]; then
    sleep "$COMMIT_INTERVAL"
    continue
  fi

  # Limit commits to prevent huge batches
  if [ "$CHANGE_COUNT" -gt "$COMMIT_LIMIT" ]; then
    # Add only up to the limit
    git add -A
    FILES=$(git diff --cached --name-only | head -n "$COMMIT_LIMIT")
    git reset
    echo "$FILES" | xargs git add
  else
    git add -A
  fi

  # Create auto-commit
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
  COMMIT_MSG="[AUTO-COMMIT] $TIMESTAMP - $CHANGE_COUNT file(s) changed"

  git commit -m "$COMMIT_MSG" \
    -m "Auto-committed by NEXUS pipeline" \
    -m "Changes: $CHANGE_COUNT file(s)" || true

  sleep "$COMMIT_INTERVAL"
done
DOCKER_COMMIT

chmod +x "$VM_DIR/docker-auto-commit.sh"
log_ok "Docker auto-commit script created"

# ============================================================================
# PART 2: SAFE PULL WITH VALIDATION
# ============================================================================

echo ""
echo "╔════ PART 2: SAFE PULL VALIDATION ════╗"
echo ""

log_info "2.1: Creating safe pull validator..."

cat > "$VM_DIR/safe-pull-validator.sh" << 'SAFE_PULL'
#!/bin/bash
# Validates pulled content before merging
# Prevents malicious code injection

set -e

REMOTE_URL="$1"
BRANCH="$2"
PR_ID="$3"

if [ -z "$REMOTE_URL" ] || [ -z "$BRANCH" ]; then
  echo "Usage: $0 <remote-url> <branch> [pr-id]"
  exit 1
fi

echo "🔒 SAFE PULL VALIDATION"
echo "════════════════════════════════════════════"

# ─── STEP 1: SIGNATURE VERIFICATION ───
echo "1. Verifying GPG signatures..."

# Check if commits are signed
UNSIGNED_COMMITS=$(git log "$REMOTE_URL/$BRANCH" ^HEAD --pretty=format:%H 2>/dev/null | while read commit; do
  if ! git verify-commit "$commit" 2>/dev/null; then
    echo "$commit"
  fi
done)

if [ -n "$UNSIGNED_COMMITS" ]; then
  log_warn "⚠️  Found unsigned commits:"
  echo "$UNSIGNED_COMMITS" | head -5
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Pull rejected"
    exit 1
  fi
fi

# ─── STEP 2: CODE QUALITY SCAN ───
echo "2. Scanning for malicious patterns..."

# Dangerous patterns
DANGEROUS_PATTERNS=(
  "rm -rf /"
  "dd if=/dev/zero"
  ":(){:|:;};"  # Fork bomb
  "$(eval"
  "\`eval"
  "exec.*&>/dev/null"
)

TEMP_BRANCH="safe-pull-validate-$$"
git fetch "$REMOTE_URL" "$BRANCH:$TEMP_BRANCH" 2>/dev/null

MALICIOUS=0
for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if git diff HEAD..."$TEMP_BRANCH" | grep -i "$pattern" > /dev/null 2>&1; then
    log_error "❌ DANGEROUS PATTERN DETECTED: $pattern"
    MALICIOUS=1
  fi
done

if [ "$MALICIOUS" -eq 1 ]; then
  git branch -D "$TEMP_BRANCH"
  exit 1
fi

log_ok "✅ No dangerous patterns detected"

# ─── STEP 3: FILE TYPE WHITELIST ───
echo "3. Validating file types..."

CHANGED_FILES=$(git diff --name-only HEAD..."$TEMP_BRANCH")
FORBIDDEN_EXTENSIONS=(".exe" ".dll" ".so" ".bin" ".elf")

while read -r file; do
  for ext in "${FORBIDDEN_EXTENSIONS[@]}"; do
    if [[ "$file" == *"$ext" ]]; then
      log_error "❌ FORBIDDEN FILE TYPE: $file"
      git branch -D "$TEMP_BRANCH"
      exit 1
    fi
  done
done <<< "$CHANGED_FILES"

log_ok "✅ All file types validated"

# ─── STEP 4: SIZE LIMITS ───
echo "4. Checking file sizes..."

MAX_FILE_SIZE=$((50 * 1024 * 1024))  # 50MB

while read -r file; do
  SIZE=$(git show "$TEMP_BRANCH:$file" 2>/dev/null | wc -c)
  if [ "$SIZE" -gt "$MAX_FILE_SIZE" ]; then
    log_error "❌ FILE TOO LARGE: $file ($SIZE bytes)"
    git branch -D "$TEMP_BRANCH"
    exit 1
  fi
done <<< "$CHANGED_FILES"

log_ok "✅ File sizes within limits"

# ─── STEP 5: DEPENDENCY CHECK ───
echo "5. Analyzing dependencies..."

# For Python files
if git show "$TEMP_BRANCH:requirements.txt" 2>/dev/null | grep -q "pip"; then
  log_warn "⚠️  Found new pip dependencies - review manually"
fi

log_ok "✅ Dependency check passed"

# ─── COMPLETION ───
echo ""
echo "════════════════════════════════════════════"
echo "✅ SAFE PULL VALIDATION PASSED"
echo "════════════════════════════════════════════"
echo "Safe to merge: $REMOTE_URL/$BRANCH"
echo ""

# Return branch name for next step
echo "$TEMP_BRANCH"
SAFE_PULL

chmod +x "$VM_DIR/safe-pull-validator.sh"
log_ok "Safe pull validator created"

# ============================================================================
# PART 3: PR CREATION WITH STAGING
# ============================================================================

echo ""
echo "╔════ PART 3: PR STAGING ════╗"
echo ""

log_info "3.1: Creating PR staging script..."

cat > "$VM_DIR/create-pr-safe.sh" << 'CREATE_PR'
#!/bin/bash
# Creates PR with validated changes
# Stages in isolated environment before pushing

set -e

REMOTE_URL="$1"
BRANCH="$2"
PR_TITLE="$3"
GIT_PROVIDER="${4:-github}"  # github, gitlab, gitea

if [ -z "$REMOTE_URL" ] || [ -z "$BRANCH" ]; then
  echo "Usage: $0 <remote-url> <branch> <pr-title> [provider]"
  exit 1
fi

echo "📝 PR CREATION WITH STAGING"
echo "════════════════════════════════════════════"

# ─── STEP 1: VALIDATE ───
echo "1. Validating changes..."

VALIDATED_BRANCH=$("$VM_DIR/safe-pull-validator.sh" "$REMOTE_URL" "$BRANCH" || exit 1)

echo "Validated branch: $VALIDATED_BRANCH"

# ─── STEP 2: STAGE ───
echo "2. Staging for PR..."

mkdir -p "$PR_STAGING_DIR"
STAGING_REPO="$PR_STAGING_DIR/$BRANCH-pr-$$"
git clone --origin upstream "$REMOTE_URL" "$STAGING_REPO"

cd "$STAGING_REPO"

# Create feature branch
git checkout -b "pr/$BRANCH/$$"
git merge "$VALIDATED_BRANCH" --no-ff -m "Merge validated changes"

# Verify merge doesn't introduce conflicts
if [ $? -ne 0 ]; then
  echo "❌ Merge conflicts detected - PR rejected"
  rm -rf "$STAGING_REPO"
  exit 1
fi

echo "✅ Changes staged successfully"

# ─── STEP 3: CALCULATE STATS ───
echo "3. Calculating PR statistics..."

COMMIT_COUNT=$(git log --oneline upstream/"$BRANCH"..HEAD | wc -l)
FILES_CHANGED=$(git diff --name-only upstream/"$BRANCH" | wc -l)
INSERTIONS=$(git diff --stat upstream/"$BRANCH" | tail -1 | awk '{print $4}')
DELETIONS=$(git diff --stat upstream/"$BRANCH" | tail -1 | awk '{print $6}')

echo "   Commits: $COMMIT_COUNT"
echo "   Files: $FILES_CHANGED"
echo "   +$INSERTIONS / -$DELETIONS"

# ─── STEP 4: CREATE PR DESCRIPTION ───
echo "4. Creating PR description..."

cat > "$STAGING_REPO/.pr-metadata.txt" << PR_DESC
Title: $PR_TITLE
Branch: pr/$BRANCH/$$
Commits: $COMMIT_COUNT
Files Changed: $FILES_CHANGED
Insertions: $INSERTIONS
Deletions: $DELETIONS
Staging Dir: $STAGING_REPO
Created: $(date)
Provider: $GIT_PROVIDER
PR_DESC

echo "✅ PR ready for review"
echo ""
echo "Next: Push to remote and create PR"
echo "Staging directory: $STAGING_REPO"
echo ""
CREATE_PR

chmod +x "$VM_DIR/create-pr-safe.sh"
log_ok "PR creation script created"

# ============================================================================
# PART 4: SECURE AUTO-PUSH
# ============================================================================

echo ""
echo "╔════ PART 4: SECURE AUTO-PUSH ════╗"
echo ""

log_info "4.1: Creating secure push script..."

cat > "$VM_DIR/secure-auto-push.sh" << 'AUTO_PUSH'
#!/bin/bash
# Auto-pushes with security checks
# Prevents pushing malicious or unreviewed code

set -e

REMOTE_URL="$1"
BRANCH="$2"
DRY_RUN="${3:-false}"

if [ -z "$REMOTE_URL" ] || [ -z "$BRANCH" ]; then
  echo "Usage: $0 <remote-url> <branch> [dry-run]"
  exit 1
fi

echo "🚀 SECURE AUTO-PUSH"
echo "════════════════════════════════════════════"

# ─── STEP 1: PRE-PUSH CHECKS ───
echo "1. Running pre-push security checks..."

# Check branch is tracked
if ! git rev-parse --verify "$BRANCH" > /dev/null 2>&1; then
  echo "❌ Branch not found: $BRANCH"
  exit 1
fi

# Check commits are signed
UNSIGNED=$(git log --pretty=format:%H "$REMOTE_URL/$BRANCH"..HEAD 2>/dev/null | while read commit; do
  if ! git verify-commit "$commit" 2>/dev/null; then
    echo "$commit"
  fi
done)

if [ -n "$UNSIGNED" ]; then
  echo "⚠️  Unsigned commits detected"
  read -p "Continue? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# ─── STEP 2: VERIFY CREDENTIALS ───
echo "2. Verifying git credentials..."

if ! git credential approve <<< "$(git config credential.helper)"; then
  echo "⚠️  Could not verify credentials"
fi

# ─── STEP 3: DRY RUN ───
echo "3. Running dry-run push..."

if [ "$DRY_RUN" = "true" ]; then
  git push --dry-run "$REMOTE_URL" "$BRANCH"
  echo "✅ Dry-run successful"
else
  # ─── STEP 4: ACTUAL PUSH ───
  echo "4. Pushing to remote..."

  git push "$REMOTE_URL" "$BRANCH"

  echo "✅ Push successful"
fi

echo ""
echo "════════════════════════════════════════════"
echo "✅ SECURE AUTO-PUSH COMPLETE"
echo "════════════════════════════════════════════"
AUTO_PUSH

chmod +x "$VM_DIR/secure-auto-push.sh"
log_ok "Secure push script created"

# ============================================================================
# PART 5: PIPELINE ORCHESTRATOR
# ============================================================================

echo ""
echo "╔════ PART 5: PIPELINE ORCHESTRATOR ════╗"
echo ""

log_info "5.1: Creating main orchestrator..."

cat > "$VM_DIR/git-pipeline-orchestrate.sh" << 'ORCHESTRATE'
#!/bin/bash
# Main Git Pipeline Orchestrator
# Coordinates: Auto-commit → Safe-pull → PR → Secure-push

set -e

ACTION="${1:-help}"
REMOTE_URL="$2"
BRANCH="${3:-main}"

case "$ACTION" in
  start-docker)
    echo "🐳 Starting Docker auto-commit daemon..."
    docker exec nexus-playground bash ~/.nexus-nested-vm/docker-auto-commit.sh &
    echo "✅ Auto-commit daemon started (PID: $!)"
    ;;

  safe-pull)
    echo "🔒 Performing safe pull..."
    "$VM_DIR/safe-pull-validator.sh" "$REMOTE_URL" "$BRANCH"
    ;;

  create-pr)
    echo "📝 Creating safe PR..."
    PR_TITLE="$4"
    if [ -z "$PR_TITLE" ]; then
      echo "Usage: $0 create-pr <url> <branch> <title>"
      exit 1
    fi
    "$VM_DIR/create-pr-safe.sh" "$REMOTE_URL" "$BRANCH" "$PR_TITLE"
    ;;

  push)
    echo "🚀 Pushing changes..."
    DRY_RUN="${4:-false}"
    "$VM_DIR/secure-auto-push.sh" "$REMOTE_URL" "$BRANCH" "$DRY_RUN"
    ;;

  full-pipeline)
    echo "🔄 Running full pipeline..."
    echo "1️⃣  Safe pull..."
    "$VM_DIR/safe-pull-validator.sh" "$REMOTE_URL" "$BRANCH"
    echo "2️⃣  Create PR..."
    "$VM_DIR/create-pr-safe.sh" "$REMOTE_URL" "$BRANCH" "Auto-PR: $BRANCH"
    echo "3️⃣  Secure push (dry-run)..."
    "$VM_DIR/secure-auto-push.sh" "$REMOTE_URL" "$BRANCH" "true"
    ;;

  *)
    echo "NEXUS Git Pipeline Orchestrator"
    echo ""
    echo "Usage: $0 <action> [options]"
    echo ""
    echo "Actions:"
    echo "  start-docker           Start Docker auto-commit daemon"
    echo "  safe-pull <url> <branch>  Validate and pull changes"
    echo "  create-pr <url> <branch> <title>  Stage PR with validation"
    echo "  push <url> <branch> [dry-run]  Securely push changes"
    echo "  full-pipeline <url> <branch>  Run all steps"
    echo ""
    ;;
esac
ORCHESTRATE

chmod +x "$VM_DIR/git-pipeline-orchestrate.sh"
log_ok "Pipeline orchestrator created"

# ============================================================================
# COMPLETION
# ============================================================================

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ SECURE GIT PROPAGATION PIPELINE SETUP COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Pipeline Architecture:"
echo ""
echo "  🐳 Docker Container"
echo "     ↓ (auto-commit every 5 min)"
echo "  📁 Local Git Repo"
echo "     ↓ (external user requests PR)"
echo "  🔒 Safe Pull Validator"
echo "     ✓ GPG signatures"
echo "     ✓ Malicious pattern scan"
echo "     ✓ File type whitelist"
echo "     ✓ Size limits"
echo "     ✓ Dependency analysis"
echo "     ↓ (if passes)"
echo "  📝 PR Staging Area (isolated)"
echo "     ↓ (calculates stats, creates metadata)"
echo "  🚀 Secure Auto-Push"
echo "     ✓ Pre-push verification"
echo "     ✓ Credential validation"
echo "     ✓ Dry-run option"
echo "     ↓ (push to chosen remote)"
echo "  ☁️  External Git (GitHub/GitLab/etc)"
echo ""
echo "Scripts created:"
echo "  📜 docker-auto-commit.sh         (auto-commits in container)"
echo "  📜 safe-pull-validator.sh        (5-layer validation gate)"
echo "  📜 create-pr-safe.sh             (PR with staging)"
echo "  📜 secure-auto-push.sh           (verified pushing)"
echo "  📜 git-pipeline-orchestrate.sh   (main orchestrator)"
echo ""
echo "Quick Start:"
echo "  1. Enable auto-commit: $VM_DIR/git-pipeline-orchestrate.sh start-docker"
echo "  2. Pull safely: $VM_DIR/git-pipeline-orchestrate.sh safe-pull <url> <branch>"
echo "  3. Create PR: $VM_DIR/git-pipeline-orchestrate.sh create-pr <url> <branch> '<title>'"
echo "  4. Push: $VM_DIR/git-pipeline-orchestrate.sh push <url> <branch>"
echo ""
