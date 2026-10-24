"""state/phase.json（現在工程・モード）の読み書き。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import PHASE_IDS

STEPS = ["plan", "decompose", "execute", "integrate", "review", "gate"]
STEP_LABELS = {"plan": "計画", "decompose": "タスク分解", "execute": "並行実行",
               "integrate": "統合", "review": "レビュー", "gate": "人間ゲート", "verify": "検証"}

DEFAULT_STATE = {
    "mode": "normal",            # normal / defect（不具合・変更要求による差分やり直し中）
    "current_phase": PHASE_IDS[0],
    "step": "plan",
    "defect": None,              # 差分やり直しの対象（DEF-xxx または CR-xxx）
    "resume_phase": None,        # 不具合対応前に進めていた工程
    "updated_at": None,
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def phase_json(root) -> Path:
    return Path(root) / "state" / "phase.json"


def load(root) -> dict:
    p = phase_json(root)
    st = dict(DEFAULT_STATE)
    if p.exists():
        st.update(json.loads(p.read_text(encoding="utf-8")))
    return st


def save(root, st: dict) -> None:
    st = dict(st)
    st["updated_at"] = now()
    p = phase_json(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main_tasks_file(root) -> Path:
    return Path(root) / "state" / "tasks.yaml"


def item_dir(root, item_id) -> Path:
    """不具合票は state/defects/、変更要求票は state/changes/。"""
    sub = "changes" if str(item_id).startswith("CR-") else "defects"
    return Path(root) / "state" / sub


def defect_tasks_file(root, defect_id, phase) -> Path:
    return item_dir(root, defect_id) / defect_id / f"tasks-{phase}.yaml"


def current_tasks_file(root, st: dict | None = None, main: bool = False) -> Path:
    st = st or load(root)
    if not main and st.get("mode") == "defect" and st.get("defect"):
        return defect_tasks_file(root, st["defect"], st["current_phase"])
    return main_tasks_file(root)
