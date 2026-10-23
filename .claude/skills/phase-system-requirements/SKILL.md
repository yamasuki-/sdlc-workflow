---
name: phase-system-requirements
description: 工程2「要件定義」。要求（REQ）からシステム要件（SR）・非機能要件（NFR）を定義し、TDD の先行作成として受入／システムテスト仕様（AT）を test-writer が作成する。
---

# 工程 2: 要件定義（02-system-requirements）

まず `.claude/sdlc/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

## 入力 / 成果物
- 入力: `docs/01-requirements/`（REQ・質問への回答・ゲート 1 のコメント）
- 成果物（`docs/02-system-requirements/`）:
  - `sr-<領域>.md` … `### SR-xxx`（テンプレート `system-requirements.md`）
  - `nfr.md` … `### NFR-xxx`（測定可能な基準値）
  - `at-<領域>.md` … `### AT-xxx` 受入／システムテスト仕様（テンプレート `acceptance-test-spec.md`）
  - `plan.md` / `summary.md` / `review.md`

## タスク分解
- 領域ごとに SR 作成タスク（agent: **analyst**、担当 `sr-<領域>.md`）。
- NFR 作成タスク（analyst、`nfr.md`）。
- 領域ごとに AT 作成タスク（agent: **test-writer**、担当 `at-<領域>.md`、依存: 対応する SR タスク）。
  NFR 用の AT（`at-nfr.md`）は NFR タスクに依存。
- 並行例: [SR 領域A, SR 領域B] → [AT 領域A, NFR] → [AT 領域B, AT NFR]

## 作業内容
- SR は「システムは〈条件〉のとき〈振る舞い〉すること」の形で、例外・エラー時の振る舞いを含める。
- 工程 1 の質問の回答と、未回答の場合の仮定を反映し、仮定に基づく SR には `- 仮定: Q-xxx` を付ける。
- AT は SR / NFR だけを見て作る（設計・実装を想定しない）。正常・異常・境界を含め、期待結果は観測可能に。

## 統合
- `scripts/sdlc trace check`（REQ→SR/NFR、SR/NFR→AT が全件つながること）。
