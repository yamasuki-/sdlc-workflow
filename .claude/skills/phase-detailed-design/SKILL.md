---
name: phase-detailed-design
description: 工程4「詳細設計」。モジュール内設計（DD）と単体テスト仕様（UT）を作成し、TDD の先行作成として単体テストコードを Red（失敗）の状態で test-writer が作成する。
---

# 工程 4: 詳細設計（04-detailed-design）

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/phase-detailed-design/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

まず `<SDLC>/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

## 入力 / 成果物
- 入力: `docs/03-basic-design/`（BD・IF）
- 成果物:
  - `docs/04-detailed-design/dd-<モジュール>.md` … `### DD-xxx` と `### UT-xxx`（テンプレート `detailed-design.md`。
    概要・トレーサビリティ・サブ機能・IF・シーケンス・状態遷移の構成。該当しない章は「該当なし」と理由を書く）
  - 画面・DB を持つモジュールは `ui-<モジュール>.md` / `db-<モジュール>.md`（テンプレート `ui-design.md` / `db-design.md`）
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
- **Red の確認**: `scripts/sdlc test-run --expect red`（`commands.test_unit` があれば `--cmd test_unit`）を実行する。
  証跡が `docs/04-detailed-design/test-run-red.md` に残る。終了コード 5（Red にならない）なら test-writer に差し戻す。
  出力を見て、新規の単体テストが**1 件ずつ**想定どおりの理由（未実装・未定義）で失敗しているかを確認し、
  成功してしまうテスト（意味が無い）があれば見直す。結果を summary.md に記録する。
- `scripts/sdlc trace check`（BD→DD、DD→UT、UT→テストコード）。
