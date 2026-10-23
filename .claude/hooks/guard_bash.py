#!/usr/bin/env python3
"""PreToolUse(Bash): Bash 経由でのゲート・成果物・ワークフロー本体の改変を検出して拒否する。

シェルの完全な解析はできないためヒューリスティックである。すり抜けた改変も、
工程成果物はゲートのハッシュ不一致で検知され、承認は TTY 必須の scripts/approve でしか記録できない。
"""
from __future__ import annotations

import re

from _common import allow, deny, maintenance, run

from sdlc_lib.config import PROTECTED_PATHS, find_root, load_project, project_problems

WRITE_PATTERNS = [
    r"(?<![0-9&<>-])>{1,2}(?!&)",                    # リダイレクト（2>&1 等は除外）
    r"\btee\b", r"\bsed\b[^|;&]*\s-i", r"\bperl\b[^|;&]*\s-[a-z]*i", r"\bcp\b", r"\bmv\b", r"\brm\b",
    r"\btouch\b", r"\bln\b", r"\bchmod\b", r"\btruncate\b", r"\bdd\b", r"\binstall\b", r"\brsync\b",
    r"\bgit\s+(checkout|restore|reset|rm|mv|apply|stash|clean|revert|cherry-pick)\b",
    r"\bpatch\b", r"\bunzip\b", r"\btar\b[^|;&]*\s-?x",
]
NULL_REDIRECTS = re.compile(r"\d?>{1,2}\s*/dev/null|\d>&\d|&>\s*/dev/null")


def writes(cmd: str) -> bool:
    c = NULL_REDIRECTS.sub(" ", cmd)
    return any(re.search(p, c) for p in WRITE_PATTERNS)


def mentions(cmd: str, prefix: str) -> bool:
    return bool(prefix) and re.search(r"(^|[\s'\"=/:(])(\./)?" + re.escape(prefix) + r"(/|\b|$)", cmd) is not None


def check(data: dict):
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if re.search(r"state/gates", cmd):
        deny("state/gates/ は Bash から参照・変更できません（参照は Read ツール、状態確認は `scripts/sdlc gate status`）。")
    if re.search(r"scripts/approve|(^|[\s;&|(])\.?/?approve\s+(defect\b|\d)", cmd):
        deny("scripts/approve は人が端末で実行する承認スクリプトです。Claude は実行できません。"
             "承認が必要な旨を人に伝えて停止してください。")
    if not writes(cmd):
        allow()
    if not maintenance():
        for p in PROTECTED_PATHS:
            if mentions(cmd, p):
                deny(f"{p} はワークフロー本体のため Bash から変更できません。")
    root = find_root(data.get("cwd"))
    proj = load_project(root)
    areas = ["docs", "input"]
    if not project_problems(proj):
        areas += [proj["src_dir"], *[v for k, v in proj["test_dirs"].items() if k != "regression"]]
    for a in areas:
        if mentions(cmd, a):
            deny(f"工程成果物（{a}/）を Bash で変更しようとしています。ゲート・TDD の検査を通すため "
                 "Write / Edit ツールを使ってください（git merge・テスト実行は可）。")
    allow()


if __name__ == "__main__":
    run(check)
