"""人間ゲートの判定（承認＋成果物ハッシュ一致）。

ゲートが有効 ⇔ 判定が「承認」または「条件付き承認」
            かつ 記録されたハッシュ == 現在の成果物ハッシュ
            かつ 不具合による無効化（invalidated_by）が無い
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from . import fm
from .config import GATES_DIR, PHASE_IDS, phase_id, phase_index, phase_of_path

DECISIONS = {"approved": "承認", "conditional": "条件付き承認", "rejected": "差戻し"}
PASSING = {"approved", "conditional"}


def list_files(root) -> list[str]:
    """リポジトリ内のファイル（追跡済み＋未追跡、.gitignore 除外）を相対パスで返す。"""
    root = Path(root)
    try:
        r = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=str(root), capture_output=True, timeout=60,
        )
        if r.returncode == 0:
            names = {n for n in r.stdout.decode("utf-8", "surrogateescape").split("\0") if n}
            return sorted(n for n in names if (root / n).is_file())
    except (OSError, subprocess.SubprocessError):
        pass
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != ".git"]
        for f in fns:
            out.append(Path(dp, f).relative_to(root).as_posix())
    return sorted(out)


def sha256_file(path) -> str:
    """成果物のハッシュ。テキスト（NUL を含まない）ファイルは CRLF を LF にそろえてから計算する。

    Windows の git（core.autocrlf）で改行が変わっても、OS をまたいでゲートが無効にならないようにするため。
    """
    data = Path(path).read_bytes()
    if b"\0" not in data[:8192]:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def phase_files(root, proj, phase, files=None) -> list[str]:
    pid = phase_id(phase)
    files = files if files is not None else list_files(root)
    return [f for f in files if phase_of_path(f, proj) == pid]


def artifacts(root, proj, phase, files=None) -> tuple[str, list[dict]]:
    """(集約ハッシュ, [{path, sha256}]) を返す。"""
    items = [{"path": f, "sha256": sha256_file(Path(root) / f)} for f in phase_files(root, proj, phase, files)]
    h = hashlib.sha256()
    for it in items:
        h.update(f"{it['path']}\0{it['sha256']}\n".encode())
    return "sha256:" + h.hexdigest(), items


def gate_path(root, phase) -> Path:
    return Path(root) / GATES_DIR / f"{phase_id(phase)}.md"


def defect_gate_path(root, item_id) -> Path:
    """不具合（DEF-xxx）・変更要求（CR-xxx）のやり直し範囲承認の記録。"""
    kind = "change" if str(item_id).startswith("CR-") else "defect"
    return Path(root) / GATES_DIR / f"{kind}-{item_id}.md"


def read_gate(path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    meta, _ = fm.read(p)
    return meta


def gate_status(root, proj, phase, files=None) -> dict:
    pid = phase_id(phase)
    meta = read_gate(gate_path(root, pid))
    st = {"phase": pid, "exists": meta is not None, "decision": None, "valid": False,
          "reason": "", "invalidated_by": None, "recorded_hash": None, "current_hash": None}
    if meta is None:
        st["reason"] = "未承認（ゲート記録なし）"
        return st
    st["decision"] = meta.get("decision")
    st["invalidated_by"] = meta.get("invalidated_by")
    st["recorded_hash"] = meta.get("artifacts_hash")
    cur, _ = artifacts(root, proj, pid, files)
    st["current_hash"] = cur
    if st["decision"] not in PASSING:
        st["reason"] = f"判定が {DECISIONS.get(st['decision'], st['decision'])}"
    elif st["invalidated_by"]:
        st["reason"] = f"{st['invalidated_by']} により再承認要"
    elif st["recorded_hash"] != cur:
        st["reason"] = "承認後に成果物が変更されている（ハッシュ不一致）"
    else:
        st["valid"] = True
        st["reason"] = DECISIONS[st["decision"]]
    return st


def all_status(root, proj, files=None) -> list[dict]:
    files = files if files is not None else list_files(root)
    return [gate_status(root, proj, pid, files) for pid in PHASE_IDS]


def prerequisites(root, proj, phase, files=None) -> list[dict]:
    """工程 phase の前工程ゲートのうち無効なものを返す（空なら着手可）。"""
    k = phase_index(phase)
    files = files if files is not None else list_files(root)
    return [s for s in (gate_status(root, proj, j, files) for j in range(k)) if not s["valid"]]


def defect_gate_valid(root, defect_id) -> bool:
    meta = read_gate(defect_gate_path(root, defect_id))
    return bool(meta) and meta.get("decision") in PASSING
