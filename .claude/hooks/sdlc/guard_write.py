#!/usr/bin/env python3
"""PreToolUse(Write|Edit|MultiEdit|NotebookEdit): 書き込み先に応じてゲートと TDD を強制する。

どのプロジェクトでも:
  ~/.claude/settings*.json       … 拒否（env で SDLC_MAINTENANCE を設定されると保護が外れるため）
  ~/.claude に置いた本体          … 拒否（~/.claude/sdlc・hooks/sdlc・SDLC のスキル/エージェント）
SDLC プロジェクトでのみ:
  .claude/settings*.json         … 拒否（同上）
  state/gates/**                 … 常に拒否（承認は人が scripts/approve で記録する）
  プロジェクトに置いた本体・ランチャ … 拒否（SDLC_MAINTENANCE=1 で起動時のみ許可）
  工程 k の成果物領域            … 前工程 0..k-1 のゲートがすべて有効、かつ工程 k が未承認のときのみ許可
  src_dir                        … 上記に加え、失敗するテストがあること（TDD）
"""
from __future__ import annotations

import os
from pathlib import Path

from _common import allow, deny, maintenance, run, sdlc_project

from sdlc_lib import defects, gates, state, tdd
from sdlc_lib.config import (GATES_DIR, is_protected, is_user_body_path, is_user_settings, load_project, main_root,
                             phase_index, phase_of_path, project_problems, under, worktree_root)

MAINT_HINT = "変更が必要なら人が編集するか、SDLC_MAINTENANCE=1 で Claude Code を起動してください。"


def target_path(data: dict) -> Path | None:
    ti = data.get("tool_input") or {}
    p = ti.get("file_path") or ti.get("notebook_path") or ti.get("path")
    if not p:
        return None
    p = Path(os.path.expanduser(str(p)))
    if not p.is_absolute():
        p = Path(data.get("cwd") or os.getcwd()) / p
    # シンボリックリンク（macOS の /var → /private/var 等）や Windows の短い名前（RUNNER~1 等）を実体のパスにそろえる。
    # そろえないと git のルートと比べられず、判定の対象外として素通りしてしまう
    return Path(os.path.realpath(p))


def defect_allows(mroot, proj, st, upstream_bad: list[dict], rel: str, phase: str) -> bool:
    """差分やり直し中（不具合・変更要求）、影響範囲外の作業（再開先工程）は継続を許可する。"""
    if st.get("mode") != "defect" or not st.get("defect"):
        return False
    did = st["defect"]
    if phase != st.get("resume_phase") or not gates.defect_gate_valid(mroot, did):
        return False
    if any(s.get("invalidated_by") != did for s in upstream_bad):
        return False
    meta, _ = defects.load(mroot, did)
    return not any(under(rel, f) or under(f, rel) for f in meta.get("impact_files", []))


def check(data: dict):
    path = target_path(data)
    if path is None:
        allow()
    if not maintenance():
        if is_user_settings(path):
            deny(f"{path} は Claude Code の設定ファイル（hooks・env）のため編集できません。{MAINT_HINT}")
        if is_user_body_path(path):
            deny(f"{path} は ~/.claude に置いた SDLC ワークフロー本体のため編集できません。{MAINT_HINT}")
    wroot = worktree_root(path)
    if wroot is None:
        allow()
    try:
        rel = path.relative_to(wroot).as_posix()
    except ValueError:
        allow()
    mroot = main_root(wroot) or wroot
    if not sdlc_project(mroot):
        allow()

    if under(rel, GATES_DIR):
        deny("state/gates/ への書き込みは禁止です。承認は人が端末で `scripts/approve <工程>` を実行して記録します。")
    if is_protected(rel) and not maintenance():
        deny(f"{rel} はワークフロー本体（ゲート・TDD の強制機構）のため編集できません。{MAINT_HINT}")

    proj = load_project(mroot) or load_project(wroot)
    if project_problems(proj):
        if rel.startswith(("docs/", "input/")):
            deny("project.yaml が未作成・不完全です。先に /sdlc-init を実行してください。")
        allow()

    if under(rel, proj["test_dirs"]["regression"]):
        allow()  # 回帰（再現）テストはいつでも追加できる（どの工程ゲートのハッシュにも含めない）

    phase = phase_of_path(rel, proj)
    if phase is None:
        allow()

    files = gates.list_files(mroot)
    k = phase_index(phase)
    st = state.load(mroot)
    bad = [s for s in (gates.gate_status(mroot, proj, j, files) for j in range(k)) if not s["valid"]]
    if bad and not defect_allows(mroot, proj, st, bad, rel, phase):
        lines = "\n".join(f"  ✘ {s['phase']}: {s['reason']}" for s in bad)
        deny(f"{rel} は工程 {phase} の成果物です。前工程のゲートが有効でないため書き込めません:\n{lines}\n"
             "人による承認（scripts/approve）を待つか、承認後の変更なら /defect か /change で該当工程からやり直してください。")
    own = gates.gate_status(mroot, proj, phase, files)
    if own["valid"]:
        deny(f"{rel} は承認済みの工程 {phase} の成果物です。承認後の変更は /defect（不具合）か /change（変更要求）で"
             "やり直し範囲の承認を得てから行ってください。")

    if under(rel, proj["src_dir"]):
        ok, msg = tdd.check_src_edit(wroot, load_project(wroot) or proj)
        if not ok:
            deny(msg)
    allow()


if __name__ == "__main__":
    run(check)
