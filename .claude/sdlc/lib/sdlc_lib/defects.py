"""やり直し対象票の操作: 不具合票（state/defects/DEF-xxx.md）と変更要求票（state/changes/CR-xxx.md）。

どちらも「影響範囲を算出 → 人がやり直し範囲（と対応方法）を承認 → 該当工程から差分やり直し」の
同じ仕組みで処理する。違いは起点（不具合の原因 / 要求の変更）と必須項目だけ。
"""
from __future__ import annotations

import re
from pathlib import Path

from . import fm
from .config import PHASE_IDS, phase_id, phase_index, phase_of_path
from .state import item_dir, now

STATUSES = ["起票", "原因判定済", "承認済", "修正中", "検証済", "クローズ"]
SEVERITIES = ["致命", "高", "中", "低"]
EXTERNAL = "external"  # 混入工程が外部（要求ドキュメント原文）の場合
PREFIX = {"defect": "DEF", "change": "CR"}
LABEL = {"defect": "不具合", "change": "変更要求"}

DEFECT_BODY = """
## 現象

（何が起きたか。期待値と実際の値）

## 再現手順

1.

## 調査エビデンス

（investigator が記入。実行したコマンド・ログ・変数値などを生のテキストで残す。推測は書かない）

## 原因

（該当トレース ID・該当箇所（ファイル:行）。investigator が記入）

## 混入工程・流出工程と見逃し理由

- 混入工程:
- 流出工程:
- 見逃し理由:

## 対応方法の選択肢

（solution-proposer が記入。詳細は proposal に記載したファイル。人がゲートで選定する）

## 影響範囲

（`scripts/sdlc defect impact {id} --write` で算出し、確認・補正する）

## 再発防止

- 追加したチェックリスト観点:
- 追加したテストケース:

## 経緯

- {now} 起票
"""

CHANGE_BODY = """
## 変更内容

（何をどう変えたいか・追加したいか。依頼者の言葉で）

## 現行の動作

（依頼者の認識。current-analyst の解析と食い違えば明記する）

## 変更後の期待動作・受入条件

-

## 現行解析

（current-analyst が記入。関連 ID・関連ファイル・既存テストのカバー状況・影響範囲候補）

## 対応方法の選択肢

（solution-proposer が記入。詳細は proposal に記載したファイル。人がゲートで選定する）

## 影響範囲

（`scripts/sdlc change impact {id} --write` で算出し、確認・補正する）

## 経緯

- {now} 起票
"""


def kind_of(item_id: str) -> str:
    return "change" if str(item_id).startswith("CR-") else "defect"


def label(item_id: str) -> str:
    return LABEL[kind_of(item_id)]


def defects_dir(root) -> Path:
    return Path(root) / "state" / "defects"


def path(root, did: str) -> Path:
    return item_dir(root, did) / f"{did}.md"


def all_ids(root, kind: str | None = None) -> list[str]:
    out = []
    for k, pre in PREFIX.items():
        if kind and k != kind:
            continue
        d = item_dir(root, f"{pre}-000")
        if d.exists():
            out += [p.stem for p in d.glob(f"{pre}-*.md")]
    return sorted(out)


def next_id(root, kind: str = "defect") -> str:
    pre = PREFIX[kind]
    nums = [int(m.group(1)) for i in all_ids(root, kind) if (m := re.match(rf"{pre}-(\d+)$", i))]
    return f"{pre}-{(max(nums) + 1 if nums else 1):03d}"


def create(root, title: str, detected_in: str, severity: str, detected_by: str, test: str | None,
           kind: str = "defect") -> str:
    did = next_id(root, kind)
    meta = {"id": did, "kind": kind, "title": title, "status": "起票", "severity": severity,
            "detected_in": phase_id(detected_in), "detected_by": detected_by}
    if kind == "defect":
        meta.update({"reproduction_test": test or "", "cause_ids": [], "injected_phase": "",
                     "escaped_phase": ""})
    else:
        meta.update({"cause_ids": [], "start_phase": ""})
    meta.update({"proposal": "", "options": [], "recommended": "", "selected_option": "",
                 "rework_phases": [], "impact_ids": [], "impact_files": [], "created_at": now()})
    body = (DEFECT_BODY if kind == "defect" else CHANGE_BODY).format(id=did, now=now())
    fm.write(path(root, did), meta, body)
    return did


def load(root, did: str) -> tuple[dict, str]:
    p = path(root, did)
    if not p.exists():
        raise FileNotFoundError(f"{label(did)}票がありません: {p}")
    return fm.read(p)


def save(root, did: str, meta: dict, body: str) -> None:
    fm.write(path(root, did), meta, body)


def log(body: str, msg: str) -> str:
    return body.rstrip("\n") + f"\n- {now()} {msg}\n"


def _phase_ok(v, allow_external=False) -> bool:
    if allow_external and v == EXTERNAL:
        return True
    try:
        phase_index(v)
        return True
    except Exception:
        return False


def start_phase(meta: dict) -> str:
    """やり直しの起点（不具合: 混入工程 / 変更要求: 変更開始工程）。"""
    return meta.get("injected_phase") if meta.get("kind", "defect") == "defect" else meta.get("start_phase")


def problems(meta: dict, need_analysis: bool = True) -> list[str]:
    out = []
    kind = meta.get("kind", "defect")
    if meta.get("severity") not in SEVERITIES:
        out.append(f"severity は {SEVERITIES} のいずれか")
    if kind == "defect" and not meta.get("reproduction_test"):
        out.append("reproduction_test（再現テストのパス）が未記入")
    if not need_analysis:
        return out
    if kind == "defect":
        if not meta.get("cause_ids"):
            out.append("cause_ids（原因のトレース ID）が未記入")
        if not _phase_ok(meta.get("injected_phase"), allow_external=True):
            out.append(f"injected_phase は工程 ID か '{EXTERNAL}': {meta.get('injected_phase')!r}")
        if not _phase_ok(meta.get("escaped_phase")):
            out.append(f"escaped_phase は工程 ID: {meta.get('escaped_phase')!r}")
    else:
        if not _phase_ok(meta.get("start_phase")):
            out.append(f"start_phase（変更が始まる工程）は工程 ID: {meta.get('start_phase')!r}")
    if not meta.get("rework_phases"):
        out.append("rework_phases（やり直し対象工程）が空")
    else:
        for p in meta["rework_phases"]:
            if not _phase_ok(p):
                out.append(f"rework_phases に不明な工程: {p}")
    opts = meta.get("options") or []
    ids = [str(o.get("id")) for o in opts if isinstance(o, dict)]
    if opts and len(ids) != len(opts):
        out.append("options は {id, type, title} の一覧で書く")
    if meta.get("recommended") and meta["recommended"] not in ids:
        out.append(f"recommended（{meta['recommended']}）が options にありません")
    return out


def suggest_rework_phases(meta: dict, impact_files: list[str], proj: dict) -> list[str]:
    """やり直し工程の候補。

    不具合: 混入工程〜検出工程の手前のうち、影響範囲を含む工程（混入工程は必ず含む）
    変更要求: 変更開始工程〜受付工程の手前のすべて（追加・変更は下流すべてに流れるため）
    """
    sp = start_phase(meta)
    start = 0 if sp == EXTERNAL else phase_index(sp)
    end = phase_index(meta["detected_in"])  # 検出・受付工程そのものは再開時に続行する
    touched = {phase_of_path(f, proj) for f in impact_files}
    out = []
    for k in range(start, max(end, start + 1)):
        pid = PHASE_IDS[k]
        if k == start or meta.get("kind") == "change" or pid in touched:
            out.append(pid)
    return out
