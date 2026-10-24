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
echo "適用してコミットしました。hooks の場所が変わったため、Claude Code のセッションを開始し直してください（その後 git push）。"
