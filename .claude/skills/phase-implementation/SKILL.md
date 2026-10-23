---
name: phase-implementation
description: 工程5「実装」。詳細設計工程で作成済みの失敗テストを通す形で、implementer が worktree 上で Red → Green → Refactor により実装する。テストは変更しない。
---

# 工程 5: 実装（05-implementation）

まず `.claude/sdlc/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

## 入力 / 成果物
- 入力: `docs/04-detailed-design/`（DD・UT）と承認済みの単体テスト（Red）
- 成果物:
  - `<src_dir>/` … 実装コード（各要素に `trace: DD-xxx`）
  - `docs/05-implementation/` … `plan.md` / `summary.md`（テスト・lint・カバレッジ結果）/ `review.md`

## 強制されること（hooks）
- 失敗するテストが無い状態での `src_dir` 編集は拒否される（TDD ガード）。Refactor はそのタスクで Red を観測した後のみ可。
- 単体テスト（工程 4 の成果物）は承認済みのため変更できない。

## タスク分解（agent: **implementer**、`worktree: true`）
- モジュール（DD 群）ごとに 1 タスク。担当ファイル = そのモジュールの `src_dir` 内ファイル。
- 共有されるファイル（共通型・設定）を触るタスクは依存でつなぐ。モジュール間の依存（IF の提供側→利用側）も依存にする。
- タスク指示に、対象 DD・対象単体テストファイル・実行コマンド（`project.yaml`）を明記する。

## 実行時の注意
- 実装中に「テストが誤っている」と報告されたら、テストを直させずにタスクを止め、`/defect`（混入工程: 詳細設計）で扱う。
- worktree のブランチは完了ごとにメインへ `git merge --no-ff` する。

## 統合
- `commands.test` 全件成功、`commands.lint`、`commands.coverage`（`coverage_threshold` 以上）を summary.md に記録する。
- `scripts/sdlc trace check`（DD→コード）。
- `git diff <工程4承認時のコミット>.. -- <test_dirs.unit>` が空であること（テスト改ざんが無いこと）を確認する。
