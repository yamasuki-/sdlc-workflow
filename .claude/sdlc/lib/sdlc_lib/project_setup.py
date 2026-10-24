"""プロジェクト側の準備（`scripts/sdlc init`）: ランチャ・CLAUDE.md の import・.gitignore。

本体は ~/.claude/sdlc（全プロジェクト共通）またはプロジェクトの .claude/sdlc に置く。
プロジェクトには本体へのランチャ scripts/sdlc・scripts/approve だけを置き、どちらの配置でも同じコマンドで使えるようにする。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .config import install_mode

LAUNCHER = '''#!/usr/bin/env python3
"""SDLC ワークフローのランチャ（scripts/sdlc init が生成。編集しない）。

本体はプロジェクトの .claude/sdlc/bin を優先し、無ければ ~/.claude/sdlc/bin を使う。
"""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
name = Path(__file__).name
for base in (root / ".claude", Path.home() / ".claude"):
    target = base / "sdlc" / "bin" / name
    if target.is_file():
        os.execv(sys.executable, [sys.executable, str(target), *sys.argv[1:]])
sys.exit(f"SDLC ワークフロー本体（.claude/sdlc/bin/{name}）が見つかりません。USAGE.md のインストール手順を参照してください。")
'''

IMPORT_MARK = "<!-- sdlc-workflow: 全体ルール（scripts/sdlc init が管理） -->"
IMPORT_RE = re.compile(r"^@\S*\.claude/sdlc/RULES\.md\s*$", re.MULTILINE)
GITIGNORE_LINES = [".sdlc/", ".claude/settings.local.json"]


def write_launchers(root) -> list[str]:
    out = []
    for name in ("sdlc", "approve"):
        p = Path(root) / "scripts" / name
        if p.exists() and p.read_text(encoding="utf-8") == LAUNCHER:
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(LAUNCHER, encoding="utf-8")
        os.chmod(p, 0o755)
        out.append(p.relative_to(root).as_posix())
    return out


def rules_import_line(root) -> str:
    return "@.claude/sdlc/RULES.md" if install_mode(root) == "project" else "@~/.claude/sdlc/RULES.md"


def ensure_claude_md(root) -> str | None:
    """プロジェクトの CLAUDE.md に全体ルールの import を入れる（配置に合わせて書き換える）。"""
    p = Path(root) / "CLAUDE.md"
    line = rules_import_line(root)
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    if IMPORT_RE.search(text):
        new = IMPORT_RE.sub(line, text, count=1)
    else:
        new = text.rstrip("\n") + ("\n\n" if text.strip() else "") + f"{IMPORT_MARK}\n{line}\n"
    if new == text:
        return None
    p.write_text(new, encoding="utf-8")
    return line


def ensure_gitignore(root) -> list[str]:
    p = Path(root) / ".gitignore"
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    have = {ln.strip() for ln in text.splitlines()}
    add = [ln for ln in GITIGNORE_LINES if ln not in have]
    if add:
        p.write_text(text.rstrip("\n") + ("\n" if text.strip() else "") + "\n".join(add) + "\n", encoding="utf-8")
    return add
