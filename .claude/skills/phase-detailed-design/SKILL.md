---
name: phase-detailed-design
description: 工程4「詳細設計」。モジュール内設計（DD）と単体テスト仕様（UT）を作成し、TDD の先行作成として単体テストコードを Red（失敗）の状態で test-writer が作成する。
---

# 工程 4: 詳細設計（04-detailed-design）

まず `.claude/sdlc/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

## 入力 / 成果物
- 入力: `docs/03-basic-design/`（BD・IF）
- 成果物:
  - `docs/04-detailed-design/dd-<モジュール>.md` … `### DD-xxx` と `### UT-xxx`（テンプレート `detailed-design.md`）
  - `<test_dirs.unit>/` … 単体テストコード（各テストに `trace: UT-xxx`）。**Red の状態で作成する**
  - `plan.md` / `summary.md` / `review.md`
- 本工程が承認されると単体テストは凍結される（実装工程では変更できない）。

## タスク分解（モジュール単位、worktree は使わない）
- モジュールごとに DD＋UT 仕様作成（agent: **designer** が DD、UT 仕様は **test-writer**。同じ .md を触るため依存でつなぐ）。
  UT 仕様を別ファイル（`ut-<モジュール>.md`）にすれば並行化しやすい。
- モジュールごとに単体テストコード作成（agent: **test-writer**、担当 `<test_dirs.unit>/...`、依存: UT 仕様タスク）。

## 作業内容
- DD は配置ファイル・シグネチャ・処理・事前/事後条件・例外を、テストが書ける具体性で書く。
- テストコードは DD の振る舞いを検証し、内部実装に依存しない。
- `src_dir` は変更しない（コンパイル言語でテストが未定義シンボルでビルドできない場合も、それを Red として扱う）。

## 統合
- `commands.test`（または `test_unit`）を実行し、**新規の単体テストが失敗（Red）していること**、
  失敗理由が未実装・未定義であることを summary.md に記録する（成功してしまうテストは意味が無いので見直す）。
- `scripts/sdlc trace check`（BD→DD、DD→UT、UT→テストコード）。
