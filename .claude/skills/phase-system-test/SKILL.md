---
name: phase-system-test
description: 工程7「システム／受入テスト」。要件定義で作成した受入／システムテスト仕様（AT）を実装・実行し、要件カバレッジ報告（REQ→SR→AT→テストコードのトレースマトリクス）を作成する。
---

# 工程 7: システム／受入テスト（07-system-test）

まず `.claude/sdlc/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

## 入力 / 成果物
- 入力: `docs/02-system-requirements/` の AT 仕様・NFR、全工程の承認済み成果物
- 成果物:
  - `<test_dirs.system>/` … システム／受入テストコード（各テストに `trace: AT-xxx`）
  - `docs/07-system-test/test-results.md` … 実行結果、NFR 測定値と基準値の比較
  - `docs/07-system-test/trace-matrix.md` … `scripts/sdlc trace matrix --out docs/07-system-test/trace-matrix.md`
  - `docs/07-system-test/coverage-report.md` … 要件カバレッジ（全 REQ が AT とテストコードまでつながっているか）とコードカバレッジ
  - `plan.md` / `summary.md` / `review.md`

## タスク分解（agent: **test-writer**、`worktree: true`）
- AT 仕様ファイル（領域）ごとに 1 タスク。NFR の測定テストは別タスク。
- 自動化できない AT は手動試験タスク（agent: test-writer、担当 `docs/07-system-test/manual-tests.md`）にする。
  手順・結果・実施者を記録し、各記録に `- trace: AT-xxx`（見出しの外）を書くと実施証跡としてトレースされる。

## 統合 — 実行・不具合起票・カバレッジ
1. `commands.test_system`（無ければ `commands.test`）と `commands.coverage` を実行して test-results.md に記録する。
2. 失敗は工程 6 と同様に `--detected-in 07 --by auto` で自動起票し `/defect` へ。
3. トレースマトリクスとカバレッジ報告を作成する。`scripts/sdlc trace check --upto 07` が全件 OK であること。

## ゲートで人に確認してほしい点
- 受入可否、未自動化 AT の実施結果、NFR の判定、残存する既知の制約。
