"""不具合票（state/defects/DEF-xxx.md）の操作。"""
from __future__ import annotations

import re
from pathlib import Path

from . import fm
from .config import PHASE_IDS, phase_id, phase_index, phase_of_path
from .state import now

STATUSES = ["起票", "原因判定済", "承認済", "修正中", "検証済", "クローズ"]
SEVERITIES = ["致命", "高", "中", "低"]
EXTERNAL = "external"  # 混入工程が外部（要求ドキュメント原文）の場合

TEMPLATE_BODY = """
## 現象

（何が起きたか。期待値と実際の値）

## 再現手順

1.

## 原因

（該当トレース ID・該当箇所。investigator が記入）

## 混入工程・流出工程と見逃し理由

- 混入工程:
- 流出工程:
- 見逃し理由:

## 影響範囲

（`scripts/sdlc defect impact {id} --write` で算出し、確認・補正する）

## 再発防止

- 追加したチェックリスト観点:
- 追加したテストケース:

## 経緯

- {now} 起票
"""


def defects_dir(root) -> Path:
    return Path(root) / "state" / "defects"


def path(root, did: str) -> Path:
    return defects_dir(root) / f"{did}.md"


def all_ids(root) -> list[str]:
    d = defects_dir(root)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("DEF-*.md"))


def next_id(root) -> str:
    nums = [int(m.group(1)) for i in all_ids(root) if (m := re.match(r"DEF-(\d+)$", i))]
    return f"DEF-{(max(nums) + 1 if nums else 1):03d}"


def create(root, title: str, detected_in: str, severity: str, detected_by: str, test: str | None) -> str:
    did = next_id(root)
    meta = {
        "id": did,
        "title": title,
        "status": "起票",
        "severity": severity,
        "detected_in": phase_id(detected_in),
        "detected_by": detected_by,
        "reproduction_test": test or "",
        "cause_ids": [],
        "injected_phase": "",
        "escaped_phase": "",
        "rework_phases": [],
        "impact_ids": [],
        "impact_files": [],
        "created_at": now(),
    }
    fm.write(path(root, did), meta, TEMPLATE_BODY.format(id=did, now=now()))
    return did


def load(root, did: str) -> tuple[dict, str]:
    p = path(root, did)
    if not p.exists():
        raise FileNotFoundError(f"不具合票がありません: {p}")
    return fm.read(p)


def save(root, did: str, meta: dict, body: str) -> None:
    fm.write(path(root, did), meta, body)


def log(body: str, msg: str) -> str:
    return body.rstrip("\n") + f"\n- {now()} {msg}\n"


def problems(meta: dict, need_analysis: bool = True) -> list[str]:
    out = []
    if meta.get("severity") not in SEVERITIES:
        out.append(f"severity は {SEVERITIES} のいずれか")
    if not meta.get("reproduction_test"):
        out.append("reproduction_test（再現テストのパス）が未記入")
    if need_analysis:
        if not meta.get("cause_ids"):
            out.append("cause_ids（原因のトレース ID）が未記入")
        inj = meta.get("injected_phase")
        if inj != EXTERNAL:
            try:
                phase_index(inj)
            except Exception:
                out.append(f"injected_phase は工程 ID か '{EXTERNAL}': {inj!r}")
        try:
            phase_index(meta.get("escaped_phase"))
        except Exception:
            out.append(f"escaped_phase は工程 ID: {meta.get('escaped_phase')!r}")
        if not meta.get("rework_phases"):
            out.append("rework_phases（やり直し対象工程）が空")
        else:
            for p in meta["rework_phases"]:
                try:
                    phase_index(p)
                except Exception:
                    out.append(f"rework_phases に不明な工程: {p}")
    return out


def suggest_rework_phases(meta: dict, impact_files: list[str], proj: dict) -> list[str]:
    """混入工程〜検出工程の手前のうち、影響範囲を含む工程（混入工程は必ず含む）。"""
    inj = meta.get("injected_phase")
    start = 0 if inj == EXTERNAL else phase_index(inj)
    end = phase_index(meta["detected_in"])  # 検出工程そのものは再開時に続行する
    touched = {phase_of_path(f, proj) for f in impact_files}
    out = []
    for k in range(start, max(end, start + 1)):
        pid = PHASE_IDS[k]
        if k == start or pid in touched:
            out.append(pid)
    return out
