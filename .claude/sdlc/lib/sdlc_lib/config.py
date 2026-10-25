"""工程定義・プロジェクト固有情報（project.yaml）・ルート解決。"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - 依存不足は呼び出し側でエラーにする
    yaml = None


# 工程定義（V字モデル）。順序が工程番号を表す。
PHASES = [
    {"id": "00-intake", "name": "取り込み", "skill": "phase-intake"},
    {"id": "01-requirements", "name": "要求整理・分析", "skill": "phase-requirements"},
    {"id": "02-system-requirements", "name": "要件定義", "skill": "phase-system-requirements"},
    {"id": "03-basic-design", "name": "基本設計", "skill": "phase-basic-design"},
    {"id": "04-detailed-design", "name": "詳細設計", "skill": "phase-detailed-design"},
    {"id": "05-implementation", "name": "実装", "skill": "phase-implementation"},
    {"id": "06-integration-test", "name": "結合テスト", "skill": "phase-integration-test"},
    {"id": "07-system-test", "name": "システム／受入テスト", "skill": "phase-system-test"},
]
PHASE_IDS = [p["id"] for p in PHASES]
SKILL_TO_PHASE = {p["skill"]: p["id"] for p in PHASES}

# worktree 分離を使う工程（実装・テスト工程のみ）
WORKTREE_PHASES = {"05-implementation", "06-integration-test", "07-system-test"}

# ワークフロー本体を構成するスキル・エージェント（インストーラと保護判定で使う）
SKILL_NAMES = ["sdlc", "sdlc-init", "defect", "change"] + [p["skill"] for p in PHASES]
AGENT_NAMES = ["analyst", "designer", "test-writer", "implementer", "reviewer", "security-reviewer",
               "investigator", "current-analyst", "solution-proposer"]
# .claude/ からの相対パスで表した本体の配置（~/.claude/ にもプロジェクトの .claude/ にも同じ形で置く）
BODY_DIRS = ["sdlc", "hooks/sdlc"] + [f"skills/{n}" for n in SKILL_NAMES]
BODY_FILES = [f"agents/{n}.md" for n in AGENT_NAMES]

# Claude による編集を禁止するパス（SDLC_MAINTENANCE=1 で起動した場合のみ解除。gates は常に禁止）
GATES_DIR = "state/gates"
PROTECTED_PATHS = [
    ".claude/settings.json",
    ".claude/settings.local.json",
    "scripts/sdlc",       # 本体へのランチャ（bash 用と Windows の cmd / PowerShell 用）
    "scripts/approve",
    "scripts/sdlc.cmd",
    "scripts/approve.cmd",
] + [f".claude/{p}" for p in BODY_DIRS + BODY_FILES]

DEFAULT_PROJECT = {
    "workflow": "",           # "sdlc"（~/.claude に置いた本体が、このプロジェクトを SDLC プロジェクトと判定する印）
    "language": "",
    "test_framework": "",
    "commands": {
        "test": "",
        "test_unit": "",
        "test_integration": "",
        "test_system": "",
        "lint": "",
        "coverage": "",
    },
    "coverage_threshold": 0,
    "src_dir": "",
    "test_dir": "",
    "test_dirs": {"unit": "", "integration": "", "system": "", "regression": ""},
    "tdd": {"hook_timeout_sec": 300},
    "parallel": {"max_tasks": 2},
    # 機械チェックゲート: {"common"|<工程ID>: {"must"|"should"|"may": [コマンド or {name, cmd}]}}
    "checks": {},
    "check_timeout_sec": 300,
}

# src_dir / test_dir に使えない（ワークフロー本体と衝突する）パス
RESERVED_DIRS = ["docs", "input", "state", "scripts", ".claude", "spec", "examples", "rules", ".sdlc", ".git"]


class ConfigError(Exception):
    pass


def utf8_stdio() -> None:
    """標準出力・標準エラーを UTF-8 にする（Windows でパイプやファイルに出すとき、既定のコードページでは日本語で落ちる）。"""
    import sys
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def require_yaml():
    if yaml is None:
        raise ConfigError("PyYAML が見つかりません。`pip install -r requirements.txt` を実行してください。")
    return yaml


def phase_index(phase: str) -> int:
    """'02-system-requirements' / '2' / '02' / 'phase-system-requirements' を工程番号に変換する。"""
    s = str(phase).strip()
    if s in SKILL_TO_PHASE:
        s = SKILL_TO_PHASE[s]
    if s in PHASE_IDS:
        return PHASE_IDS.index(s)
    if s.isdigit() and 0 <= int(s) < len(PHASES):
        return int(s)
    for i, pid in enumerate(PHASE_IDS):
        if pid.split("-", 1)[1] == s:
            return i
    raise ConfigError(f"不明な工程: {phase}（指定可能: {', '.join(PHASE_IDS)}）")


def phase_id(phase) -> str:
    return PHASE_IDS[phase_index(phase)]


def phase_name(phase) -> str:
    return PHASES[phase_index(phase)]["name"]


# ---------------------------------------------------------------- ルート解決

def _git(args, cwd) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def _existing_dir(path: Path) -> Path:
    p = Path(os.path.realpath(path))
    while not p.exists() and p != p.parent:
        p = p.parent
    return p if p.is_dir() else p.parent


def worktree_root(path) -> Path | None:
    """path を含む git 作業ツリー（worktree を含む）のルート。"""
    if os.environ.get("SDLC_ROOT"):
        return Path(os.environ["SDLC_ROOT"]).resolve()
    top = _git(["rev-parse", "--show-toplevel"], _existing_dir(Path(path)))
    return Path(os.path.realpath(top)) if top else None


def main_root(path) -> Path | None:
    """worktree から見ても常にメインの作業ツリーを返す（state/ はここに置かれる）。"""
    if os.environ.get("SDLC_ROOT"):
        return Path(os.environ["SDLC_ROOT"]).resolve()
    d = _existing_dir(Path(path))
    common = _git(["rev-parse", "--git-common-dir"], d)
    if not common:
        return None
    cp = Path(common)
    if not cp.is_absolute():
        cp = (d / cp).resolve()
    if cp.name == ".git":
        return cp.parent.resolve()
    return worktree_root(d)


def user_claude_dir() -> Path:
    """ユーザ単位の Claude Code 設定ディレクトリ（~/.claude）。"""
    return Path.home() / ".claude"


def body_dirs(root=None) -> list[Path]:
    """ワークフロー本体（.claude/sdlc）の候補。プロジェクトの .claude/sdlc が ~/.claude/sdlc より優先。"""
    out = []
    if root is not None:
        out.append(Path(root) / ".claude" / "sdlc")
    out.append(user_claude_dir() / "sdlc")
    seen, uniq = set(), []
    for p in out:
        if p.resolve() not in seen:
            seen.add(p.resolve())
            uniq.append(p)
    return uniq


def resolve_body_file(rel: str, root=None) -> Path | None:
    """本体のファイル（templates/・checklists/・phase-flow.md 等）をファイル単位で解決する。"""
    for d in body_dirs(root):
        p = d / rel
        if p.exists():
            return p
    return None


def install_mode(root) -> str:
    """'project'（プロジェクトの .claude/ に本体がある）/ 'user'（~/.claude/ のみ）/ 'none'。"""
    if (Path(root) / ".claude" / "sdlc" / "bin" / "sdlc").exists():
        return "project"
    if (user_claude_dir() / "sdlc" / "bin" / "sdlc").exists():
        return "user"
    return "none"


def is_sdlc_project(root) -> bool:
    """project.yaml に workflow: sdlc がある、またはプロジェクトの .claude/ に本体が置かれている。"""
    root = Path(root)
    if (root / ".claude" / "hooks" / "sdlc").is_dir():
        return True
    p = root / "project.yaml"
    if not p.exists():
        return False
    # PyYAML が無くても判定できるよう、行の形で調べる
    text = p.read_text(encoding="utf-8", errors="replace")
    return re.search(r"^workflow\s*:\s*['\"]?sdlc['\"]?\s*(#.*)?$", text, re.MULTILINE) is not None


def find_root(start=None) -> Path:
    start = start or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    root = main_root(start)
    if root is None:
        raise ConfigError("git リポジトリ内で実行してください。")
    return root


# ---------------------------------------------------------------- project.yaml

def _merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        elif v is not None:
            out[k] = v
    return out


def load_project(root) -> dict | None:
    path = Path(root) / "project.yaml"
    if not path.exists():
        return None
    y = require_yaml()
    data = y.safe_load(path.read_text(encoding="utf-8")) or {}
    proj = _merge(DEFAULT_PROJECT, data)
    proj["src_dir"] = norm_dir(proj.get("src_dir", ""))
    proj["test_dir"] = norm_dir(proj.get("test_dir", ""))
    td = proj.get("test_dirs") or {}
    base = proj["test_dir"]
    proj["test_dirs"] = {
        kind: norm_dir(td.get(kind) or (f"{base}/{kind}" if base else ""))
        for kind in ("unit", "integration", "system", "regression")
    }
    return proj


def norm_dir(p: str) -> str:
    p = str(p or "").strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.rstrip("/")


def project_problems(proj: dict | None) -> list[str]:
    if proj is None:
        return ["project.yaml がありません（/sdlc-init で作成してください）"]
    probs = []
    if proj.get("workflow") != "sdlc":
        probs.append("workflow: sdlc がありません（~/.claude に置いた本体がこのプロジェクトを認識するための印）")
    for key in ("language", "test_framework", "src_dir", "test_dir"):
        if not str(proj.get(key) or "").strip():
            probs.append(f"{key} が未設定です")
    if not str(proj["commands"].get("test") or "").strip():
        probs.append("commands.test が未設定です")
    dirs = {"src_dir": proj.get("src_dir")}
    dirs.update({f"test_dirs.{k}": v for k, v in proj["test_dirs"].items()})
    for name, d in dirs.items():
        if not d:
            continue
        if d in (".", "") or d.startswith("/") or ".." in d.split("/"):
            probs.append(f"{name} はリポジトリ内の相対サブディレクトリにしてください: {d}")
        if d.split("/")[0] in RESERVED_DIRS:
            probs.append(f"{name} にワークフロー予約ディレクトリは使えません: {d}")
    vals = [v for v in dirs.values() if v]
    for i, a in enumerate(vals):
        for b in vals[i + 1:]:
            if a == b:
                probs.append(f"ディレクトリが重複しています: {a}")
    src = proj.get("src_dir")
    if src:
        for k, t in proj["test_dirs"].items():
            if t and (t + "/").startswith(src + "/"):
                probs.append(f"test_dirs.{k}（{t}）を src_dir の配下に置くことはできません")
    try:
        mt = int(proj["parallel"].get("max_tasks", 2))
        if mt < 1:
            probs.append("parallel.max_tasks は 1 以上にしてください")
    except (TypeError, ValueError):
        probs.append("parallel.max_tasks は整数にしてください")
    return probs


def phase_areas(proj: dict) -> dict[str, list[str]]:
    """各工程の成果物領域（パス接頭辞）。ゲートのハッシュ対象と書き込み制御に使う。"""
    td = proj["test_dirs"]
    areas = {
        "00-intake": ["input", "docs/00-intake"],
        "01-requirements": ["docs/01-requirements"],
        "02-system-requirements": ["docs/02-system-requirements"],
        "03-basic-design": ["docs/03-basic-design"],
        "04-detailed-design": ["docs/04-detailed-design", td["unit"]],
        "05-implementation": ["docs/05-implementation", proj["src_dir"]],
        "06-integration-test": ["docs/06-integration-test", td["integration"]],
        "07-system-test": ["docs/07-system-test", td["system"]],
    }
    return {k: [p for p in v if p] for k, v in areas.items()}


def under(rel: str, prefix: str) -> bool:
    return bool(prefix) and (rel == prefix or rel.startswith(prefix + "/"))


def phase_of_path(rel: str, proj: dict) -> str | None:
    """パスがどの工程の成果物か（最長一致）。どこにも属さなければ None。"""
    best, best_len = None, -1
    for pid, prefixes in phase_areas(proj).items():
        for p in prefixes:
            if under(rel, p) and len(p) > best_len:
                best, best_len = pid, len(p)
    return best


def is_protected(rel: str) -> bool:
    return any(under(rel, p) for p in PROTECTED_PATHS)


def is_user_body_path(path) -> bool:
    """~/.claude/ に置いた本体（sdlc・hooks/sdlc・SDLC のスキル/エージェント）か。"""
    try:
        rel = Path(path).resolve().relative_to(user_claude_dir().resolve()).as_posix()
    except ValueError:
        return False
    return any(under(rel, p) for p in BODY_DIRS + BODY_FILES)


def is_user_settings(path) -> bool:
    """~/.claude/settings*.json か（env で SDLC_MAINTENANCE を設定されると全プロジェクトの保護が外れる）。"""
    p = Path(path)
    return is_claude_settings(p) and p.parent.resolve() == user_claude_dir().resolve()


def is_claude_settings(path) -> bool:
    """任意の場所の Claude Code 設定ファイル（hooks や env を変えられるもの）か。

    リポジトリ外（~/.claude/settings.json 等）も対象にする。env で SDLC_MAINTENANCE を
    設定されると保護が外れるため、Claude による編集を禁止する。
    """
    p = Path(path)
    return p.parent.name == ".claude" and p.name in ("settings.json", "settings.local.json")
