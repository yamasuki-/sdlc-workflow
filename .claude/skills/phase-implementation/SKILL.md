---
name: phase-implementation
description: 工程5「実装」。詳細設計工程で作成済みの失敗テストを通す形で、implementer が worktree 上で Red → Green → Refactor により実装する。テストは変更しない。
---

# 工程 5: 実装（05-implementation）

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/phase-implementation/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

まず `<SDLC>/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

## 入力 / 成果物
- 入力: `docs/04-detailed-design/`（DD・UT）と承認済みの単体テスト（Red）
- 成果物:
  - `<src_dir>/` … 実装コード（各要素に `trace: DD-xxx`）
  - `docs/05-implementation/` … `plan.md` / `summary.md`（テスト・lint・カバレッジ結果）/ `checks.md`（機械チェック）/
    `test-run-green.md`（Green の証跡）/ `review.md` / `security-review.md`（セキュリティレビュー）

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
- **Green の確認**: `scripts/sdlc test-run --expect green` で全テスト成功の証跡を `test-run-green.md` に残す。
  失敗（終了コード 5）なら該当モジュールの implementer に差し戻す。
- `scripts/sdlc check`（lint・型検査・カバレッジ・依存脆弱性スキャン等。project.yaml の checks）。
- テスト・lint・カバレッジ（`coverage_threshold` 以上）の結果を summary.md に記録する。
- `scripts/sdlc trace check`（DD→コード）。
- `git diff <工程4承認時のコミット>.. -- <test_dirs.unit>` が空であること（テスト改ざんが無いこと）を確認する。

## レビュー（2 段・順に実施）
1. **reviewer**（チェックリスト `05-implementation.md`）: 設計どおりか・テスト改ざんが無いか・過剰実装が無いか。
2. **security-reviewer**（チェックリスト `security.md`）: 安全か。reviewer が合格（または条件付き合格）になってから実施する。
   `docs/05-implementation/security-review.md` が「不合格」の間はゲートを承認できない。
   コードの脆弱性は implementer の修正タスクで直し（テストが必要なら test-writer を先に）、`scripts/sdlc check` → 両レビューを再実施する。
   設計レベルの欠陥（承認済みの設計の誤り）なら `/defect` で扱う。
