"""tasks.yaml（タスク DAG と進捗）の操作。

タスクの状態: pending → in_progress → done / failed
            blocked（不具合の影響範囲に入り停止中。blocked_by に DEF-ID）
"""
from __future__ import annotations

from pathlib import Path

from .config import WORKTREE_PHASES, phase_of_path, require_yaml, under
from .state import now

STATUSES = {"pending", "in_progress", "done", "failed", "blocked"}
AGENTS = {"analyst", "designer", "test-writer", "implementer"}


class TaskError(Exception):
    pass


def load(path) -> dict:
    p = Path(path)
    if not p.exists():
        raise TaskError(f"タスクファイルがありません: {p}")
    data = require_yaml().safe_load(p.read_text(encoding="utf-8")) or {}
    data.setdefault("tasks", [])
    for t in data["tasks"]:
        t.setdefault("status", "pending")
        t.setdefault("depends_on", [])
        t.setdefault("files", [])
        t.setdefault("trace_ids", [])
        t.setdefault("attempts", 0)
    return data


def save(path, data: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(require_yaml().safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def by_id(data: dict) -> dict:
    return {t["id"]: t for t in data["tasks"]}


def _overlap(a: list[str], b: list[str]) -> bool:
    return any(under(x, y) or under(y, x) for x in a for y in b)


def validate(data: dict, proj: dict | None = None, phase: str | None = None) -> list[str]:
    errs = []
    ids = [t.get("id") for t in data["tasks"]]
    seen = set()
    for i in ids:
        if not i:
            errs.append("id の無いタスクがあります")
        elif i in seen:
            errs.append(f"タスク ID が重複しています: {i}")
        seen.add(i)
    tasks = by_id(data)
    for t in data["tasks"]:
        tid = t.get("id")
        if t.get("status") not in STATUSES:
            errs.append(f"{tid}: 不正な status: {t.get('status')}")
        if not t.get("files"):
            errs.append(f"{tid}: 担当ファイル（files）が空です")
        if t.get("agent") not in AGENTS:
            errs.append(f"{tid}: agent は {sorted(AGENTS)} のいずれか: {t.get('agent')}")
        for d in t.get("depends_on", []):
            if d not in tasks:
                errs.append(f"{tid}: 依存先が存在しません: {d}")
        if proj and phase:
            for f in t.get("files", []):
                ph = phase_of_path(f, proj)
                if ph != phase and not under(f, proj["test_dirs"]["regression"]):
                    errs.append(f"{tid}: {f} は工程 {phase} の成果物領域外です（{ph or '領域外'}）")
            if phase in WORKTREE_PHASES and t.get("agent") in ("implementer", "test-writer") and not t.get("worktree", False):
                errs.append(f"{tid}: 実装・テスト工程のコード作成タスクは worktree: true にしてください")
    # 循環検出
    color = {}

    def visit(n, path):
        color[n] = 1
        for d in tasks[n].get("depends_on", []):
            if d not in tasks:
                continue
            if color.get(d) == 1:
                errs.append("依存関係が循環しています: " + " → ".join(path + [d]))
            elif color.get(d) is None:
                visit(d, path + [d])
        color[n] = 2

    for n in tasks:
        if color.get(n) is None:
            visit(n, [n])
    return errs


def ready(data: dict, max_parallel: int = 2) -> list[dict]:
    """今すぐ並行実行できるタスク（依存完了・担当ファイル非競合）を最大 max_parallel - 実行中 件返す。"""
    tasks = by_id(data)
    running = [t for t in data["tasks"] if t["status"] == "in_progress"]
    slots = max_parallel - len(running)
    busy = [f for t in running for f in t["files"]]
    picked = []
    for t in data["tasks"]:
        if slots <= 0:
            break
        if t["status"] != "pending":
            continue
        if any(tasks.get(d, {}).get("status") != "done" for d in t["depends_on"]):
            continue
        if _overlap(t["files"], busy):
            continue
        picked.append(t)
        busy.extend(t["files"])
        slots -= 1
    return picked


def set_status(data: dict, tid: str, status: str, result: str | None = None) -> dict:
    t = by_id(data).get(tid)
    if t is None:
        raise TaskError(f"タスクがありません: {tid}")
    if status == "in_progress":
        if t["status"] not in ("pending", "failed"):
            raise TaskError(f"{tid} は {t['status']} のため開始できません")
        t["attempts"] = int(t.get("attempts", 0)) + 1
        t["started_at"] = now()
    if status in ("done", "failed"):
        t["finished_at"] = now()
    t["status"] = status
    if result is not None:
        t["result"] = result
    return t


def recover(data: dict) -> list[str]:
    """中断で in_progress のまま残ったタスクを pending に戻す（再開用）。"""
    out = []
    for t in data["tasks"]:
        if t["status"] == "in_progress":
            t["status"] = "pending"
            t["result"] = (t.get("result") or "") + f"\n[{now()}] 中断から復帰（再実行）"
            out.append(t["id"])
    return out


def block(data: dict, defect_id: str, impact_ids: set[str], impact_files: list[str]) -> list[str]:
    """不具合の影響範囲に入る未完了タスクを停止する。"""
    out = []
    for t in data["tasks"]:
        if t["status"] in ("done",):
            continue
        if set(t.get("trace_ids", [])) & impact_ids or _overlap(t.get("files", []), impact_files):
            t["status"] = "blocked"
            t["blocked_by"] = defect_id
            out.append(t["id"])
    return out


def unblock(data: dict, defect_id: str) -> list[str]:
    out = []
    for t in data["tasks"]:
        if t["status"] == "blocked" and t.get("blocked_by") == defect_id:
            t["status"] = "pending"
            t.pop("blocked_by", None)
            out.append(t["id"])
    return out


def summary(data: dict) -> dict:
    c = {s: 0 for s in sorted(STATUSES)}
    for t in data["tasks"]:
        c[t["status"]] = c.get(t["status"], 0) + 1
    c["total"] = len(data["tasks"])
    return c
