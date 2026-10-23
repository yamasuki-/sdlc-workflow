"""TDD の強制: 失敗するテストが無い状態での src_dir 編集を拒否する。

判定（作業ツリー単位。worktree ごとに独立）:
  1. project.yaml の commands.test を実行する（src/test に変更が無ければ前回結果を再利用）
  2. 失敗（終了コード ≠ 0）→ Red/Green 中なので編集可。red_seen を記録する
  3. 全成功 → このタスクで一度でも Red を観測していれば Refactor として編集可、無ければ拒否
red_seen は `scripts/sdlc task start` で（新しい worktree なら最初から）リセットされる。
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

from .state import now

SKIP_DIRS = {".git", "__pycache__", "node_modules", "target", "build", "dist", ".venv", "venv",
             ".pytest_cache", ".mypy_cache", ".gradle", ".idea", ".sdlc", "coverage"}


def state_file(root) -> Path:
    return Path(root) / ".sdlc" / "tdd.json"


def load(root) -> dict:
    p = state_file(root)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {"red_seen": False}


def save(root, st: dict) -> None:
    p = state_file(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def reset(root, task: str | None = None) -> None:
    save(root, {"red_seen": False, "task": task, "reset_at": now()})


def fingerprint(root, dirs: list[str]) -> str:
    h = hashlib.sha256()
    for d in sorted(set(x for x in dirs if x)):
        base = Path(root) / d
        if not base.exists():
            continue
        for dp, dns, fns in os.walk(base):
            dns[:] = sorted(x for x in dns if x not in SKIP_DIRS and not x.startswith("."))
            for f in sorted(fns):
                p = Path(dp, f)
                try:
                    s = p.stat()
                except OSError:
                    continue
                h.update(f"{p.relative_to(root).as_posix()}\0{s.st_mtime_ns}\0{s.st_size}\n".encode())
    return h.hexdigest()


def run_tests(root, proj: dict) -> tuple[bool, str]:
    cmd = proj["commands"]["test"]
    timeout = int(proj.get("tdd", {}).get("hook_timeout_sec", 300))
    try:
        r = subprocess.run(cmd, shell=True, cwd=str(root), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"テストがタイムアウトしました（{timeout}秒）。失敗として扱います。"
    out = (r.stdout + r.stderr)[-2000:]
    return r.returncode == 0, out


def check_src_edit(root, proj: dict) -> tuple[bool, str]:
    if not str(proj["commands"].get("test") or "").strip():
        return False, "project.yaml の commands.test が未設定のため、src_dir の編集を許可できません（/sdlc-init）。"
    st = load(root)
    dirs = [proj["src_dir"], proj["test_dir"], *proj["test_dirs"].values()]
    fp = fingerprint(root, dirs)
    last = st.get("last") or {}
    if last.get("fingerprint") == fp:
        passed, out = last["passed"], last.get("output", "")
    else:
        passed, out = run_tests(root, proj)
        st["last"] = {"fingerprint": fp, "passed": passed, "output": out, "at": now()}
    if not passed:
        st["red_seen"] = True
        save(root, st)
        return True, "Red（失敗するテストあり）"
    save(root, st)
    if st.get("red_seen"):
        return True, "Refactor（このタスクで Red を観測済み）"
    return False, (
        "TDD 違反: 失敗するテストがありません。先に失敗するテスト（Red）を用意してから src_dir を編集してください。\n"
        "・実装工程では詳細設計工程で作成済みの単体テストを対象にします\n"
        "・不具合修正では回帰テスト（test_dirs.regression）に再現テストを先に書きます\n"
        f"（{proj['commands']['test']} は全件成功しました）"
    )
