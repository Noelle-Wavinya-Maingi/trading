#!/usr/bin/env bash
#
# One-time setup: wires tools/pre_commit_check.sh into git's pre-commit hook.
# Not done automatically on clone -- git doesn't version .git/hooks -- so
# every dev who wants the local guardrail runs this once.
#
# Usage: tools/install_hooks.sh
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK="$REPO/.git/hooks/pre-commit"

cat > "$HOOK" <<'EOF'
#!/usr/bin/env bash
exec "$(git rev-parse --show-toplevel)/tools/pre_commit_check.sh"
EOF

chmod +x "$HOOK"
echo "Installed pre-commit hook -> $HOOK"
