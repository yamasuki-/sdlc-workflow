---
name: phase-integration-test
description: 工程6「結合テスト」。基本設計で作成した結合テスト仕様（IT）を test-writer がテストコードとして実装・実行する。失敗は不具合として自動起票し /defect に回す。
---

# 工程 6: 結合テスト（06-integration-test）

まず `.claude/sdlc/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

## 入力 / 成果物
- 入力: `docs/03-basic-design/` の IT 仕様、承認済みの実装コード
- 成果物:
  - `<test_dirs.integration>/` … 結合テストコード（各テストに `trace: IT-xxx`）
  - `docs/06-integration-test/test-results.md`（テンプレート `test-results.md`）/ `plan.md` / `summary.md` / `review.md`

## タスク分解（agent: **test-writer**、`worktree: true`）
- IF（または IT 仕様ファイル）ごとに 1 タスク。担当 = 結合テストファイル。
- 実行と結果記録は統合ステップで行う。

## 作業内容
- IT 仕様の手順・期待結果を忠実に実装する。**期待値を実装の挙動に合わせない**。
- `src_dir` は変更しない（実装工程は承認済みで変更できない）。

## 統合 — テスト実行と不具合の自動起票
1. `commands.test_integration`（無ければ `commands.test`）を実行し、test-results.md に記録する。
2. 失敗したテストごとに不具合を**自動起票**する:
   `scripts/sdlc defect new --title "<IT-xxx 失敗: 要約>" --detected-in 06 --by auto --test <失敗したテストのパス> --severity <重大度>`
   票の「現象」に失敗メッセージ、「再現手順」に実行コマンドを書く。
3. 不具合があれば `/defect` を起動する（影響範囲外の結合テスト作成は継続してよい）。
   全不具合がクローズし、全結合テストが成功してからレビューへ進む。
4. `scripts/sdlc trace check`（IT→テストコード）。
