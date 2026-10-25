# SDLC ワークフロー 全体ルール

このリポジトリは、要求ドキュメントを入力に V 字モデルの工程（0〜7）で開発を進めるワークフローです。
**進め方に迷ったら `/sdlc` を実行する**（状態を読んで次の工程を起動する）。

## 絶対ルール

1. **人間ゲート必須**: 各工程はレビュー後に人の承認を得るまで次工程に進まない。
   - 承認は人が端末で `scripts/approve <工程>` を実行して `state/gates/` に記録する。
   - Claude は `scripts/approve` を実行しない・`state/gates/` に書き込まない（hook で拒否される）。
   - ワークフロー本体（`.claude/sdlc`・hooks・SDLC のスキル/エージェント・設定ファイル・ランチャ）を、hooks の検査を
     迂回する方法（スクリプト経由の書き換え、コマンドへの `SDLC_MAINTENANCE=1` の付与など）で変更しない。
     人が明示的に指示した場合だけ、USAGE.md「7. ワークフロー本体を変更する」の手順で行う。
   - 承認待ちになったら、提示内容とコマンドを人に伝えて**停止する**。
2. **承認済み成果物は変更しない**: 変更すると成果物ハッシュが変わりゲートが無効になる。
   承認後に誤りが見つかったら `/defect`（不具合対応フロー）、要求を変えたい・機能を足したいなら `/change`（変更要求フロー）で
   該当工程からやり直す。どちらも対応方法の選択肢（あるべき姿 / 最小修正）を示し、人がゲートで選ぶ。
3. **TDD 必須**: 失敗するテスト（Red）が無い状態で `src_dir` を編集しない（hook で拒否される）。
   - V 字の左側の工程で右側のテストを先に作る（要件定義→受入テスト仕様、基本設計→結合テスト仕様、詳細設計→単体テストコード）。
   - テストを書く担当（test-writer）と実装担当（implementer）は別エージェント。実装側はテストを変更しない。
   - 既存テストの削除・期待値の変更は、必ずレビュー報告に明記する。
4. **トレーサビリティ必須**: 全成果物に ID を付け、追跡元を書く（下記）。`scripts/sdlc trace check` が通ること。
5. **言語非依存**: 言語・テストフレームワーク・コマンドは `project.yaml` だけに書く。ワークフロー本体に持ち込まない。
6. **並行度は最大 2**（Claude Pro 前提）。並行させるタスクは担当ファイルが重ならないこと。
7. **状態はファイルに残す**: 進捗は `scripts/sdlc` で `state/` に記録する。中断しても `/sdlc` で再開できるようにする。
8. **機械チェック → レビューの順**: レビューの前に `scripts/sdlc check`（トレース検査＋project.yaml の checks）を通す。
   MUST が失敗している間、またはレビュー判定が「不合格」の間は、人はゲートを承認できない。
9. **決定事項・未解決事項は一元管理**: `state/decisions.md` / `state/open-questions.md` はオーケストレータ（メインセッション）だけが
   `scripts/sdlc decision|question` で追記する。サブエージェントは結果報告で返す。推測で決めず、不明点は未解決事項にする。
10. **設計書にコードを書かない**: 基本設計・詳細設計（テスト仕様を含む）は、処理を文章・表・図（Mermaid）で書く。
    実装コード・擬似コード・テストコードは書かない（コードは実装工程の `src_dir`、テストコードは `test_dirs.*` に書く）。
    書いてよいのは、名前・引数・戻り値・例外の**型レベルの定義**（表や行内の `code` 表記）とデータ形式・スキーマの表まで。
    設計工程の `scripts/sdlc check` は、設計書の図以外のコードブロックを MUST 失敗にする。
11. **プロジェクト固有ルール**: `rules/common.md`・`rules/<工程ID>.md`・`rules/review-<工程ID>.md` があれば従う。

## ID 体系とトレース記法

| 接頭辞 | 工程 | 内容 |
|---|---|---|
| SRC | 0 取り込み | 要求ドキュメントの断片（出典・確信度付き） |
| REQ / Q | 1 要求整理・分析 | 要求 / 質問 |
| SR / NFR / AT | 2 要件定義 | システム要件 / 非機能要件 / 受入・システムテスト仕様 |
| BD / IF / IT | 3 基本設計 | モジュール等の設計要素 / インタフェース / 結合テスト仕様 |
| DD / UT | 4 詳細設計 | モジュール内設計 / 単体テスト仕様 |
| DEF | 不具合 | 不具合票（`/defect`） |
| CR | 変更要求 | 変更要求票（`/change`） |

- 定義: Markdown の見出し `### SR-001: タイトル`（ID は 3 桁以上、工程内で一意）
- 追跡元: 定義ブロック内に `- 追跡元: REQ-001, REQ-002`
- コード・テスト: コメントに `trace: DD-003` / `trace: UT-007`（言語のコメント記法で書く）
- 下流が不要な項目: 定義ブロック内に `- 対象外: 理由`。承認済みで編集できない上流項目は下流の文書に `- 除外: SRC-005（理由）`
- 手動試験の記録: 見出しの外に `- trace: AT-010`（AT の実施証跡になる）

## ディレクトリ

| パス | 内容 | 書き込み |
|---|---|---|
| `input/` | 要求ドキュメント原本（xlsx/docx/pptx/pdf/md） | 工程 0 承認前のみ |
| `docs/<工程>/` | 各工程の成果物（`plan.md`・`review.md` を含む） | その工程の作業中のみ |
| `project.yaml` の `src_dir` / `test_dirs.*` | コード・テスト | 対応する工程の作業中のみ |
| `test_dirs.regression` | 不具合の再現テスト（回帰テスト） | 常に可 |
| `state/` | phase.json・tasks.yaml・defects・changes・decisions.md・open-questions.md（`gates/` 以外） | `scripts/sdlc` 経由で更新 |
| `rules/` | プロジェクト固有ルール・追加のレビュー観点（不具合の再発防止を含む）。雛形は `<SDLC>/templates/rules/` | 人が管理（再発防止の観点は Claude が追記） |
| `scripts/sdlc`・`scripts/approve` | 本体へのランチャ（`scripts/sdlc init` が生成） | 不可 |

## よく使うコマンド

シェルコマンドは **Bash ツール**で実行する（Windows でも Git Bash）。PowerShell で実行する場合はランチャを
`scripts\sdlc.cmd ...` と呼ぶ。`scripts/approve`（`scripts\approve.cmd`）は人だけが実行する。

```
scripts/sdlc status                 # 現在工程・ゲート・タスク・次のアクション
scripts/sdlc tasks next             # 並行実行できるタスク（最大 2）
scripts/sdlc task start|done|fail <ID> [--result "..."]
scripts/sdlc trace check            # トレーサビリティ検査
scripts/sdlc trace impact <ID...>   # 影響範囲（下流）
scripts/sdlc gate status            # ゲートの有効性（承認＋ハッシュ一致）
scripts/sdlc path <相対パス>        # 本体のファイル（<SDLC>/…）の実際のパス
scripts/sdlc where                  # 本体の配置（~/.claude / プロジェクト）と上書きの状況
scripts/sdlc intake <ファイル...>   # 要求ドキュメントの取り込み（工程 0）
scripts/sdlc check [工程]           # 機械チェックゲート（docs/<工程>/checks.md に記録）
scripts/sdlc test-run --expect red|green   # Red / Green の確認と証跡
scripts/sdlc decision add "..."     # 決定事項の記録（オーケストレータのみ）
scripts/sdlc question add|answer|list      # 未解決事項（オーケストレータのみ）
scripts/sdlc change new --title "..."      # 変更要求の起票（/change）
```

工程内の進め方は `<SDLC>/phase-flow.md`（全工程共通の型）に従う。

## ワークフロー本体の配置と `<SDLC>` 表記

本体は `~/.claude/`（全プロジェクト共通）またはプロジェクトの `.claude/`（そのプロジェクト専用・上書き）に置かれている。
スキル・エージェント・この文書の `<SDLC>/…` は本体のファイル（共通フロー・テンプレート・チェックリスト）を表す。
**`scripts/sdlc path <…>` で実際のパスを得てから読む**（例: `scripts/sdlc path templates/review.md`）。
プロジェクトの `.claude/sdlc/` にあればそれ、無ければ `~/.claude/sdlc/` のファイルが返る（ファイル単位で上書きできる）。
本体のファイルは全プロジェクト共通なので編集しない。プロジェクト固有のことは `rules/` に書く。
配置と上書きの状況は `scripts/sdlc where` で確認できる。
