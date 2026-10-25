"""機械チェックゲート（LLM レビューの前段）。

project.yaml の checks に、工程ごと（と全工程共通の common）に 3 階層でコマンドを書く:
  MUST   … 失敗したらレビューに進めない・ゲートを承認できない
  SHOULD … 警告。レビュアーが判断する
  MAY    … 参考情報
組み込みの MUST としてトレーサビリティ検査（scripts/sdlc trace check 相当）を常に実行する。
設計工程（基本設計・詳細設計）では、設計書に図以外のコードブロックが無いことも組み込みの MUST として検査する。
コマンドが見つからない（終了コード 127）場合は失敗ではなく skipped（未インストール）として扱う。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from . import trace
from .config import phase_id, phase_index, phase_name
from .shell import run_shell
from .state import now

LEVELS = ("must", "should", "may")
LEVEL_LABEL = {"must": "MUST", "should": "SHOULD", "may": "MAY"}

# 設計書にコードを書かない: 対象工程と、図として許すコードブロックの種類（project.yaml の design_allowed_fences で変更可）
DESIGN_PHASES = ("03-basic-design", "04-detailed-design")
DEFAULT_ALLOWED_FENCES = ("mermaid", "plantuml")
# 設計書ではない工程ファイル（計画・まとめ・レビュー・実行結果の記録）
NON_DESIGN_FILES = re.compile(r"^(plan|summary|review|checks|test-results|test-run-.*)\.md$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*([^\s`{]*)")


def design_code_blocks(root, proj: dict, phase) -> list[str]:
    """設計書の中の、図以外のコードブロック（言語指定なしを含む）を「ファイル:行: 種類」で返す。"""
    d = Path(root) / "docs" / phase_id(phase)
    allowed = {str(x).lower() for x in (proj.get("design_allowed_fences") or DEFAULT_ALLOWED_FENCES)}
    found = []
    for p in sorted(d.rglob("*.md")) if d.is_dir() else []:
        if NON_DESIGN_FILES.match(p.name):
            continue
        opened = None
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            m = FENCE_RE.match(line)
            if not m:
                continue
            if opened is None:
                opened = m.group(1)
                lang = m.group(2).lower()
                if lang not in allowed:
                    found.append(f"{p.relative_to(root).as_posix()}:{n}: {lang or '（言語指定なし）'}")
            elif m.group(1)[0] == opened[0] and len(m.group(1)) >= len(opened) and not m.group(2):
                opened = None
    return found


def _entries(items) -> list[dict]:
    out = []
    for i, it in enumerate(items or [], 1):
        cmd = str((it.get("cmd") if isinstance(it, dict) else it) or "").strip()
        name = str(it.get("name") or "") if isinstance(it, dict) else ""
        name = name or (cmd.split()[0] if cmd else f"check{i}")
        if cmd:
            out.append({"name": name, "cmd": cmd})
    return out


def configured(proj: dict, phase) -> dict[str, list[dict]]:
    cfg = proj.get("checks") or {}
    pid = phase_id(phase)
    out = {lv: [] for lv in LEVELS}
    for key in ("common", pid):
        block = cfg.get(key) or {}
        for lv in LEVELS:
            out[lv] += _entries(block.get(lv))
    return out


def _run_cmd(root, cmd: str, timeout: int) -> tuple[str, int | None, str]:
    try:
        r = run_shell(cmd, root, timeout)
    except subprocess.TimeoutExpired:
        return "fail", None, f"タイムアウト（{timeout} 秒）"
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 127:  # シェルがコマンドを見つけられなかった = 未インストール
        return "skipped", r.returncode, out[-1500:]
    return ("pass" if r.returncode == 0 else "fail"), r.returncode, out[-1500:]


def run(root, proj: dict, phase) -> dict:
    pid = phase_id(phase)
    items = []
    issues = trace.check(trace.build(root, proj), phase_index(pid))
    items.append({"level": "must", "name": "trace", "cmd": f"scripts/sdlc trace check --upto {pid}",
                  "status": "fail" if issues else "pass", "rc": 1 if issues else 0,
                  "output": "\n".join(issues[:50]) or "OK"})
    if pid in DESIGN_PHASES:
        code = design_code_blocks(root, proj, pid)
        items.append({"level": "must", "name": "design-no-code", "cmd": f"（組み込み）docs/{pid} のコードブロック検査",
                      "status": "fail" if code else "pass", "rc": 1 if code else 0,
                      "output": ("設計書にコードを書かない（処理は文章・表・図で書く）。次のコードブロックを除くこと:\n"
                                 + "\n".join(code[:50])) if code else "OK"})
    timeout = int(proj.get("check_timeout_sec") or 300)
    for lv, entries in configured(proj, pid).items():
        for e in entries:
            status, rc, out = _run_cmd(root, e["cmd"], timeout)
            items.append({"level": lv, "name": e["name"], "cmd": e["cmd"], "status": status, "rc": rc, "output": out})
    counts = {lv: {s: sum(1 for i in items if i["level"] == lv and i["status"] == s)
                   for s in ("pass", "fail", "skipped")} for lv in LEVELS}
    return {"phase": pid, "at": now(), "items": items, "counts": counts,
            "must_passed": counts["must"]["fail"] == 0,
            "skipped": [i["name"] for i in items if i["status"] == "skipped"]}


def report_path(root, phase) -> Path:
    return Path(root) / "docs" / phase_id(phase) / "checks.md"


def render(res: dict) -> str:
    pid = res["phase"]
    verdict = "PASS" if res["must_passed"] else "FAIL（MUST 失敗あり）"
    lines = [f"# 機械チェック結果: {pid} {phase_name(pid)}", "", f"- 実行日時: {res['at']}",
             f"- 判定: **{verdict}**", "", "| 階層 | pass | fail | skipped（未インストール） |", "|---|---|---|---|"]
    for lv in LEVELS:
        c = res["counts"][lv]
        lines.append(f"| {LEVEL_LABEL[lv]} | {c['pass']} | {c['fail']} | {c['skipped']} |")
    if res["skipped"]:
        lines += ["", "未インストールのため実行できなかったチェック（CI で必ず実行すること）: "
                  + ", ".join(res["skipped"])]
    for lv in LEVELS:
        its = [i for i in res["items"] if i["level"] == lv]
        if not its:
            continue
        lines += ["", f"## {LEVEL_LABEL[lv]}"]
        for i in its:
            lines += ["", f"### {i['name']} — {i['status']}", "", f"- コマンド: `{i['cmd']}`", f"- 終了コード: {i['rc']}"]
            if i["status"] != "pass" and i["output"]:
                lines += ["", "```", *i["output"].splitlines()[-50:], "```"]
    return "\n".join(lines) + "\n"


def summary_line(res: dict) -> str:
    c = res["counts"]
    return (f"{'PASS' if res['must_passed'] else 'FAIL'}"
            f"（MUST 失敗 {c['must']['fail']}・SHOULD 警告 {c['should']['fail']}・MAY {c['may']['fail']}・"
            f"未インストール {len(res['skipped'])}）")
