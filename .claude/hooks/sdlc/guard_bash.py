#!/usr/bin/env python3
"""PreToolUse(Bash): Bash 経由でのゲート・成果物・ワークフロー本体の改変を検出して拒否する。

シェルの完全な解析はできないためヒューリスティックである。すり抜けた改変も、
工程成果物はゲートのハッシュ不一致で検知され、承認は TTY 必須の scripts/approve でしか記録できない。
"""
from __future__ import annotations

import re

from _common import PROJECT_DIR, allow, deny, maintenance, run, sdlc_project

from sdlc_lib.config import AGENT_NAMES, PROTECTED_PATHS, SKILL_NAMES, load_project, main_root, project_problems

WRITE_PATTERNS = [
    r"(?<![0-9&<>-])>{1,2}(?!&)",                    # リダイレクト（2>&1 等は除外）
    r"\btee\b", r"\bsed\b[^|;&]*\s-i", r"\bperl\b[^|;&]*\s-[a-z]*i", r"\bcp\b", r"\bmv\b", r"\brm\b",
    r"\btouch\b", r"\bln\b", r"\bchmod\b", r"\btruncate\b", r"\bdd\b", r"\binstall\b", r"\brsync\b",
    r"\bgit\s+(checkout|restore|reset|rm|mv|apply|stash|clean|revert|cherry-pick)\b",
    r"\bpatch\b", r"\bunzip\b", r"\btar\b[^|;&]*\s-?x",
]
NULL_REDIRECTS = re.compile(r"\d?>{1,2}\s*/dev/null|\d>&\d|&>\s*/dev/null")
# コマンドとして実行される位置の approve（文字列中の言及は対象外）
APPROVE_CALL = re.compile(r"(?:^|[;&|(\n]|\$\()\s*(?:(?:sudo|env|exec|nohup|python3?|bash|sh)\s+)*"
                          r"(?:\S*/)?approve(?:\s|$|[;&|)])")
# ワークフロー本体のインストーラ（~/.claude や .claude/ を書き換える）。他の install.py と区別するためオプションで判定
INSTALL_CALL = re.compile(r"(?:^|[;&|(\n])\s*(?:(?:env|python3?|bash|sh)\s+)*(?:\S*/)?install\.py\b[^;&|\n]*"
                          r"--(user|project|uninstall)\b")
# ~/.claude 配下の本体（どのプロジェクトからでも保護する）
USER_BODY = re.compile(r"(~|\$HOME|\$\{HOME\}|/root|/home/[^/\s]+)/\.claude/(sdlc\b|hooks/sdlc\b|settings"
                       r"|skills/(" + "|".join(map(re.escape, SKILL_NAMES)) + r")\b"
                       r"|agents/(" + "|".join(map(re.escape, AGENT_NAMES)) + r")\.md)")


def writes(cmd: str) -> bool:
    c = NULL_REDIRECTS.sub(" ", cmd)
    return any(re.search(p, c) for p in WRITE_PATTERNS)


def mentions(cmd: str, prefix: str) -> bool:
    return bool(prefix) and re.search(r"(^|[\s'\"=/:(])(\./)?" + re.escape(prefix) + r"(/|\b|$)", cmd) is not None


def check(data: dict):
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not maintenance():
        if INSTALL_CALL.search(cmd):
            deny("ワークフロー本体のインストール・更新（install.py）は人が実行してください。")
        if writes(cmd) and USER_BODY.search(cmd):
            deny("~/.claude の設定ファイルと SDLC ワークフロー本体は Bash から変更できません。")
    root = main_root(data.get("cwd") or str(PROJECT_DIR)) or PROJECT_DIR
    if not sdlc_project(root):
        allow()
    if APPROVE_CALL.search(cmd):
        deny("scripts/approve は人が端末で実行する承認スクリプトです。Claude は実行できません。"
             "承認が必要な旨を人に伝えて停止してください。")
    if not writes(cmd):
        allow()
    if re.search(r"state/gates", cmd):
        deny("state/gates/ は Bash から変更できません（承認は人が scripts/approve で記録します）。")
    if not maintenance():
        for p in PROTECTED_PATHS:
            if mentions(cmd, p):
                deny(f"{p} はワークフロー本体のため Bash から変更できません。")
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
