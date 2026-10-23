"""トレーサビリティ（REQ → SR → 設計 → テスト → コード）の抽出・検査・影響範囲分析。

記法（言語非依存）:
  定義   … Markdown の見出し行  `### SR-001: タイトル`
  追跡元 … 定義ブロック内の行     `- 追跡元: REQ-001, REQ-002`
  コード … 任意のコメント中の     `trace: DD-003, UT-007`
  除外   … 定義ブロック内の行     `- 対象外: 理由`（下流が無くても検査で指摘しない）
           任意の位置の行         `- 除外: SRC-005, SRC-006（理由）`（承認済みで編集できない上流項目を除外する）
  手動試験 … 定義ブロック外の行   `trace: AT-010`（docs 内の手動試験記録。AT の実施証跡として扱う）
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from pathlib import Path

from .config import under
from .gates import list_files

PREFIXES = ["SRC", "REQ", "Q", "SR", "NFR", "AT", "BD", "IF", "IT", "DD", "UT", "DEF"]
ID_PAT = r"(?:%s)-\d{3,}" % "|".join(PREFIXES)
ID_RE = re.compile(r"\b" + ID_PAT + r"\b")
DEF_RE = re.compile(r"^#{1,6}\s+(" + ID_PAT + r")(?=[\s:：]|$)")
REF_RE = re.compile(r"(?:追跡元|trace)\s*[:：]\s*(.*)", re.IGNORECASE)
EXEMPT_RE = re.compile(r"^\s*[-*]?\s*対象外\s*[:：]")
MANUAL_RE = re.compile(r"^\s*[-*|]?\s*trace\s*[:：]\s*(.*)", re.IGNORECASE)
EXCLUDE_RE = re.compile(r"^\s*[-*]?\s*除外\s*[:：]\s*(.*)")

# コードファイルの種別
CODE_KINDS = {"src": "CODE", "unit": "UTC", "integration": "ITC", "system": "ATC", "regression": "RTC"}
KIND_LABEL = {"CODE": "実装コード", "UTC": "単体テストコード", "ITC": "結合テストコード",
              "ATC": "システムテストコード", "RTC": "回帰テストコード"}

# (親種別, 子として必要な種別, 検査を始める工程番号, 説明)
RULES = [
    ("SRC", {"REQ"}, 1, "取り込み項目が要求に反映されていない"),
    ("REQ", {"SR", "NFR"}, 2, "要求がシステム要件に展開されていない"),
    ("SR", {"AT"}, 2, "システム要件に受入／システムテスト仕様が無い"),
    ("NFR", {"AT"}, 2, "非機能要件に受入／システムテスト仕様が無い"),
    ("SR", {"BD", "IF"}, 3, "システム要件が基本設計に展開されていない"),
    ("IF", {"IT"}, 3, "インタフェースに結合テスト仕様が無い"),
    ("BD", {"DD"}, 4, "基本設計が詳細設計に展開されていない"),
    ("DD", {"UT"}, 4, "詳細設計に単体テスト仕様が無い"),
    ("UT", {"UTC"}, 4, "単体テスト仕様にテストコードが無い"),
    ("DD", {"CODE"}, 5, "詳細設計に対応するコードが無い"),
    ("IT", {"ITC"}, 6, "結合テスト仕様にテストコードが無い"),
    ("AT", {"ATC", "MAN"}, 7, "受入／システムテスト仕様にテストコード（または手動試験記録）が無い"),
]

TEXT_SUFFIX_DENY = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".xlsx", ".docx", ".pptx", ".zip",
                    ".jar", ".class", ".pyc", ".so", ".dll", ".exe", ".bin", ".ico"}


def kind_of(node: str) -> str:
    if node.startswith("file:"):
        return node.split(":", 2)[1]
    return node.split("-", 1)[0]


class Graph:
    def __init__(self):
        self.defs: dict[str, dict] = {}          # id → {file, line, title, exempt}
        self.parents: dict[str, set] = defaultdict(set)
        self.children: dict[str, set] = defaultdict(set)
        self.dups: list[tuple[str, str]] = []
        self.excluded: dict[str, str] = {}       # id → 除外を宣言した場所
        self.dangling: list[tuple[str, str, int]] = []

    def link(self, parent: str, child: str):
        self.parents[child].add(parent)
        self.children[parent].add(child)


def _read(path: Path) -> str | None:
    if path.suffix.lower() in TEXT_SUFFIX_DENY:
        return None
    try:
        if path.stat().st_size > 2_000_000:
            return None
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def code_kind(rel: str, proj: dict) -> str | None:
    if proj is None:
        return None
    for k, d in proj["test_dirs"].items():
        if under(rel, d):
            return CODE_KINDS[k]
    if under(rel, proj["src_dir"]):
        return CODE_KINDS["src"]
    return None


def build(root, proj: dict | None) -> Graph:
    root = Path(root)
    g = Graph()
    refs = []  # (from_node, [ids], file, line)
    excludes = []  # (id, where)
    for rel in list_files(root):
        if rel.startswith("docs/") and rel.endswith(".md"):
            text = _read(root / rel)
            if text is None:
                continue
            cur = None
            for n, line in enumerate(text.splitlines(), 1):
                x = EXCLUDE_RE.match(line)
                if x:
                    excludes += [(i, f"{rel}:{n}") for i in ID_RE.findall(x.group(1))]
                    continue
                m = DEF_RE.match(line)
                if m:
                    cur = m.group(1)
                    if cur in g.defs:
                        g.dups.append((cur, f"{rel}:{n}"))
                    else:
                        g.defs[cur] = {"file": rel, "line": n, "title": line.lstrip("#").strip(), "exempt": False}
                    continue
                if line.startswith("#"):
                    cur = None
                    continue
                if cur is None:
                    r = MANUAL_RE.match(line)
                    if r:  # 定義ブロック外の trace: は手動試験記録
                        refs.append((f"file:MAN:{rel}", ID_RE.findall(r.group(1)), rel, n))
                    continue
                if EXEMPT_RE.match(line):
                    g.defs[cur]["exempt"] = True
                r = REF_RE.search(line)
                if r:
                    refs.append((cur, ID_RE.findall(r.group(1)), rel, n))
        else:
            ck = code_kind(rel, proj)
            if ck is None:
                continue
            text = _read(root / rel)
            if text is None:
                continue
            node = f"file:{ck}:{rel}"
            for n, line in enumerate(text.splitlines(), 1):
                r = REF_RE.search(line)
                if r:
                    refs.append((node, ID_RE.findall(r.group(1)), rel, n))
    for i, where in excludes:
        if i in g.defs:
            g.defs[i]["exempt"] = True
            g.excluded[i] = where
        else:
            g.dangling.append((i, *where.rsplit(":", 1)))
    for child, ids, rel, n in refs:
        for pid in ids:
            if pid not in g.defs:
                g.dangling.append((pid, rel, n))
            else:
                g.link(pid, child)
    return g


def check(g: Graph, upto: int) -> list[str]:
    issues = []
    for i, where in g.dups:
        issues.append(f"[重複定義] {i}（{where}、既存: {g.defs[i]['file']}:{g.defs[i]['line']}）")
    for i, rel, n in g.dangling:
        issues.append(f"[未定義の参照] {i}（{rel}:{n}）")
    for parent_kind, need, from_phase, msg in RULES:
        if upto < from_phase:
            continue
        for i, d in sorted(g.defs.items()):
            if kind_of(i) != parent_kind or d["exempt"]:
                continue
            if not any(kind_of(c) in need for c in g.children.get(i, ())):
                issues.append(f"[下流なし] {i}: {msg}（{d['file']}:{d['line']}）")
    # 上流参照の欠落（SRC・Q・DEF 以外の定義は追跡元を持つべき）
    for i, d in sorted(g.defs.items()):
        if kind_of(i) in ("SRC", "Q", "DEF") or d["exempt"]:
            continue
        if not g.parents.get(i):
            issues.append(f"[追跡元なし] {i}（{d['file']}:{d['line']}）")
    return issues


def _bfs(start: list[str], edges: dict) -> list[str]:
    seen, out = set(start), []
    q = deque(start)
    while q:
        n = q.popleft()
        for m in sorted(edges.get(n, ())):
            if m not in seen:
                seen.add(m)
                out.append(m)
                q.append(m)
    return out


def downstream(g: Graph, ids: list[str]) -> list[str]:
    return _bfs(ids, g.children)


def upstream(g: Graph, ids: list[str]) -> list[str]:
    return _bfs(ids, g.parents)


def node_file(g: Graph, node: str) -> str | None:
    if node.startswith("file:"):
        return node.split(":", 2)[2]
    d = g.defs.get(node)
    return d["file"] if d else None


def impact(g: Graph, ids: list[str]) -> dict:
    nodes = list(ids) + downstream(g, ids)
    out_ids = [n for n in nodes if not n.startswith("file:")]
    files = sorted({f for f in (node_file(g, n) for n in nodes) if f})
    return {"ids": out_ids, "files": files}


def matrix(g: Graph) -> str:
    cols = [("SR/NFR", {"SR", "NFR"}), ("AT", {"AT"}), ("BD/IF", {"BD", "IF"}), ("IT", {"IT"}),
            ("DD", {"DD"}), ("UT", {"UT"}), ("コード", {"CODE"}),
            ("テストコード", {"UTC", "ITC", "ATC", "RTC", "MAN"})]
    lines = ["| REQ | " + " | ".join(c for c, _ in cols) + " |",
             "|---|" + "---|" * len(cols)]
    for r in sorted(i for i in g.defs if kind_of(i) == "REQ"):
        desc = downstream(g, [r])
        cells = []
        for _, kinds in cols:
            items = [node_file(g, n) if n.startswith("file:") else n for n in desc if kind_of(n) in kinds]
            cells.append("<br>".join(sorted(set(items))) or "—")
        lines.append(f"| {r} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
