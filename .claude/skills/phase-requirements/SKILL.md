---
name: phase-requirements
description: 工程1「要求整理・分析」。取り込み済みの SRC から要求一覧（REQ）を作り、曖昧点・矛盾・欠落を指摘し、発注元への質問リスト（Q）を作成する。
---

# 工程 1: 要求整理・分析（01-requirements）

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/phase-requirements/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

まず `<SDLC>/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

## 入力 / 成果物
- 入力: `docs/00-intake/`（承認済みの SRC、index.md の確信度 低一覧）
- 成果物（`docs/01-requirements/`）:
  - `requirements.md`（または領域別 `requirements-<領域>.md`）… `### REQ-xxx`（テンプレート `requirements.md`）
  - `issues.md` … 曖昧・矛盾・欠落・確信度低の指摘（テンプレート `issues.md`）
  - `questions.md` … `### Q-xxx`（テンプレート `questions.md`）
  - `plan.md` / `summary.md` / `review.md`

## タスク分解 — agent: analyst
- 機能領域（入力ドキュメントの章・シート・スライド群）ごとに REQ 作成タスクを分け、
  担当ファイルを `requirements-<領域>.md` に分ける。REQ の採番範囲をタスクごとに割り当てる（例: 領域 A は REQ-001〜099）。
- `issues.md` / `questions.md` の統合タスクは REQ 作成タスクすべてに依存させる。

## 作業内容（タスク指示に含める）
- すべての SRC を REQ に反映する。要求ではない SRC（表題・目次・注記など）は、SRC 側が承認済みで編集できないため、
  `requirements.md` 末尾の「## 対象外の取り込み項目」に `- 除外: SRC-005, SRC-006（表題・目次のため）` の形で理由付きで列挙する。
- 曖昧（数量・条件・主語）、矛盾（要求間・資料間）、欠落（異常系・権限・データ量・運用・移行）を洗い出す。
- 質問には「回答が無い場合の仮定」と影響を必ず書く。

## 未解決事項ログとの関係
- 発注元への質問は `questions.md`（Q-xxx、成果物の一部）に書く。ワークフロー運用上の確認事項（ツール選定など）は
  `state/open-questions.md`（OQ-xxx、`scripts/sdlc question add`）に記録する。

## ゲートで人に確認してほしい点
- **質問リストへの回答**（人が questions.md の「回答」を記入するか、ゲートのコメントに書く）。
  未回答の質問は仮定で進めてよいかを判断してもらう。
