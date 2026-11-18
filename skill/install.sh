#!/bin/bash
# install.sh — Install GitHub HR skill into Claude Code
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"
AGENTS_DIR="$HOME/.claude/agents"

echo "Installing GitHub HR skill..."

# Create directories
mkdir -p "$SKILLS_DIR/github-hr/references"
mkdir -p "$SKILLS_DIR/github-hr-run"
mkdir -p "$AGENTS_DIR"

# Copy master skill
cp "$SCRIPT_DIR/github-hr/SKILL.md" "$SKILLS_DIR/github-hr/SKILL.md"
cp "$SCRIPT_DIR/github-hr/references/"* "$SKILLS_DIR/github-hr/references/"

# Copy sub-skills
cp "$SCRIPT_DIR/skills/github-hr-run/SKILL.md" "$SKILLS_DIR/github-hr-run/SKILL.md"

# Copy agents
cp "$SCRIPT_DIR/agents/github-hr-scorer.md" "$AGENTS_DIR/github-hr-scorer.md"

# Setup Python venv for scripts
echo "Setting up Python environment..."
python3 -m venv "$SCRIPT_DIR/scripts/.venv"
source "$SCRIPT_DIR/scripts/.venv/bin/activate"
pip install -r "$SCRIPT_DIR/scripts/requirements.txt" -q
deactivate

# Optional: render the launchd jobs (daily run + priority poller) for this checkout.
if [ "${1:-}" = "--launchd" ]; then
  PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
  mkdir -p "$SCRIPT_DIR/cron/generated" "$HOME/github-hr-logs"
  for plist in "$SCRIPT_DIR"/cron/*.plist; do
    sed -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" -e "s|__HOME__|$HOME|g" "$plist" \
      > "$SCRIPT_DIR/cron/generated/$(basename "$plist")"
  done
  echo "launchd jobs rendered in skill/cron/generated/. To enable one:"
  echo "  cp skill/cron/generated/com.github-hr.cron.plist ~/Library/LaunchAgents/"
  echo "  launchctl load ~/Library/LaunchAgents/com.github-hr.cron.plist"
fi

echo ""
echo "GitHub HR skill installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Copy skill/scripts/.env.example to skill/scripts/.env"
echo "  2. Fill in CONVEX_SITE_URL and API_SECRET"
echo "  3. Start Claude Code and run: /github-hr run"
