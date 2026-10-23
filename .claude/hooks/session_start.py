#!/usr/bin/env python3
"""SessionStart: 現在の SDLC 状態をコンテキストに入れる（中断からの再開用）。失敗しても起動は妨げない。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
try:
    r = subprocess.run([sys.executable, str(root / "scripts" / "sdlc"), "status"], cwd=str(root),
                       capture_output=True, text=True, timeout=60)
    out = (r.stdout or r.stderr).strip()
    if out:
        print("## SDLC ワークフローの現在状態（scripts/sdlc status）\n" + out
              + "\n\n続きから進めるには /sdlc を実行してください。")
except Exception:  # noqa: BLE001
    pass
sys.exit(0)
