"""hooks 共通処理。終了コード 2 + stderr でツール呼び出しを拒否する（Claude に理由が返る）。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "scripts"))


def read_input() -> dict:
    try:
        return json.load(sys.stdin)
    except ValueError:
        return {}


def deny(msg: str):
    print(f"[SDLC ガード] {msg}", file=sys.stderr)
    sys.exit(2)


def allow():
    sys.exit(0)


def maintenance() -> bool:
    """人が SDLC_MAINTENANCE=1 で Claude Code を起動した場合のみワークフロー本体の編集を許可する。"""
    return os.environ.get("SDLC_MAINTENANCE") == "1"


def run(fn):
    """ガード本体を実行する。内部エラー時は安全側（拒否）に倒す。"""
    try:
        fn(read_input())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        if maintenance():
            allow()
        deny(f"ガードの内部エラーのため拒否しました: {type(e).__name__}: {e}\n"
             "依存関係（pip install -r requirements.txt）と project.yaml を確認してください。")
