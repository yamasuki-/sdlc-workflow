#!/bin/bash
# 保留中の変更（spec/pending/sdlc-update.patch）を適用する。
# SDLC_MAINTENANCE=1 で開始したセッションで、1 回の Bash 呼び出しとして実行すること:
#   bash spec/pending/apply.sh
# 適用で hooks の場所が変わる（.claude/hooks/guard_*.py → .claude/hooks/sdlc/）。
# 実行中のセッションは古い hooks の場所を参照し続けることがあるため、実行後はセッションを開始し直す。
set -e
cd "$(git rev-parse --show-toplevel)"
if [ "${SDLC_MAINTENANCE:-}" != "1" ]; then
  echo "SDLC_MAINTENANCE=1 で開始したセッションで実行してください。" >&2
  exit 1
fi
git apply spec/pending/sdlc-update.patch
chmod +x install.py .claude/sdlc/bin/sdlc .claude/sdlc/bin/approve
python3 -m unittest discover -s tests -q
git rm -r -q spec/pending
git add -A
git commit -q -F - <<'MSG'
Supplement from software_dev_workflow; install to ~/.claude with project override

- Supplement: security review, mechanical check gate, Red/Green evidence,
  richer templates, stricter investigation, solution proposals, /change,
  decisions/open-questions logs, project rules (rules/).
- Placement: workflow body lives under .claude/ (sdlc/, hooks/sdlc/, skills,
  agents) and is installed by install.py into ~/.claude (all projects) or
  <project>/.claude (project only / override). Projects get launchers
  scripts/sdlc and scripts/approve plus a CLAUDE.md import of RULES.md.
- Project overrides user: agents natively, skills by delegation, hooks by
  deferring, body files per file via `scripts/sdlc path`.
- User-level hooks act only in projects with `workflow: sdlc`.
- Installer keeps locally modified files (manifest based).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_014yTE67hyTw3Jqv6hJEEFie
MSG
# 実行中のセッションが古い hooks の場所（.claude/hooks/*.py）を参照し続けても止まらないよう、
# 新しい場所へ転送する一時ファイルを置く（このチェックアウト限り。コミットしない）
for f in guard_write guard_bash guard_skill session_start; do
  cat > ".claude/hooks/$f.py" <<'PY'
import os
import sys
from pathlib import Path

new = Path(__file__).resolve().parent / "sdlc" / Path(__file__).name
os.execv(sys.executable, [sys.executable, str(new), *sys.argv[1:]])
PY
  grep -qxF ".claude/hooks/$f.py" .git/info/exclude 2>/dev/null || echo ".claude/hooks/$f.py" >> .git/info/exclude
done
echo "適用してコミットしました。旧 hooks の場所には転送用の一時ファイルを置きました（コミット対象外）。"
echo "新しいセッションでは新しい hooks（.claude/hooks/sdlc/）が使われます。"
