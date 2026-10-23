# 比較・採否レポート

提案仕様（`sdlc-workflow-proposal.md`）0 章の手順に基づくレポート。
本リポジトリには**現行ワークフローが存在しない**（`.claude/`・`CLAUDE.md`・hooks・スクリプトいずれも無し）ため、
全項目を「本案採用」とし、提案仕様 13 章の構築順で新規に構築した。
依頼者の指示（現行リポジトリは無いものとしてワークフローを作成する）をもって作り直し着手の承認とみなした。

## 12 章 比較チェックリスト

| # | 観点 | 本案 | 現行 | 判定 | 理由・実装箇所 |
|---|---|---|---|---|---|
| 1 | 最上位の役割 | 状態管理とルーティングのみ | なし | 本案 | `/sdlc` は `scripts/sdlc status --json` の `next.action` で分岐するだけ |
| 2 | 工程の区切り | V字 0〜7 工程 | なし | 本案 | `scripts/sdlc_lib/config.py` の `PHASES`、`phase-*` スキル 8 本 |
| 3 | 工程内フローの共通化 | 全工程が同じ型 | なし | 本案 | `.claude/sdlc/phase-flow.md`、`phase.json` の `step` |
| 4 | 入力形式 | xlsx/docx/pptx/md → 共通中間形式 | なし | 本案 | `scripts/intake/adapters/`（拡張子登録で形式追加） |
| 5 | 出典・確信度の記録 | 形式別の出典単位＋確信度 | なし | 本案 | 断片ごとに出典・確信度（高/中/低）・注記 |
| 6 | トレーサビリティ | REQ→SR→設計→テスト→コード | なし | 本案 | `scripts/sdlc trace check/impact/up/matrix` |
| 7 | タスク分解 | tasks.yaml（依存＋担当ファイル） | なし | 本案 | `scripts/sdlc tasks validate/next`（循環・担当ファイル競合を検査） |
| 8 | 並行度 | 最大 2、実装系のみ worktree | なし | 本案 | `parallel.max_tasks: 2`、工程 05〜07 のコード作成タスクは `worktree: true` 必須 |
| 9 | 中断からの再開 | タスク単位で state に記録 | なし | 本案 | `task start/done/fail`、`tasks recover`、SessionStart hook で状態提示 |
| 10 | レビュー | 別コンテキストの reviewer | なし | 本案 | `reviewer` エージェント（1 体・成果物は修正しない）、工程別チェックリスト |
| 11 | 人間ゲートの強制方法 | hook でブロック | なし | 本案 | `guard_write.py`（成果物領域への書き込み）＋`guard_skill.py`（工程スキル起動） |
| 12 | 承認記録 | state/gates/*.md、成果物ハッシュ付き | なし | 本案 | YAML front matter にファイル別・集約 SHA-256、判定履歴を保持 |
| 13 | 自己承認の防止 | gates 書き込み禁止＋人が scripts/approve | なし | 本案 | ＋`scripts/approve` は TTY 必須、Bash からの実行を hook と permissions で拒否 |
| 14 | TDD の位置づけ | V字左側で右側のテストを先行作成 | なし | 本案 | 工程 2→AT、3→IT、4→UT＋単体テストコード（Red） |
| 15 | TDD の強制方法 | 失敗テスト無しの src 編集を拒否 | なし | 本案 | `commands.test` の結果で判定（結果は変更が無ければキャッシュ） |
| 16 | テスト改ざん防止 | test-writer と implementer を分離 | なし | 本案 | ＋単体テストは工程 4 承認で凍結（ハッシュ・書き込みガード） |
| 17 | 言語非依存性 | project.yaml に分離 | なし | 本案 | 本体は `commands.*` を呼ぶだけ。`/sdlc-init` で対話作成 |
| 18 | 不具合の起票 | 自動起票＋/defect | なし | 本案 | テスト工程で `defect new --by auto`、人は `/defect` |
| 19 | 原因特定 | 再現テスト先行＋逆追跡、独立 investigator | なし | 本案 | `investigator` エージェント、`trace up` |
| 20 | 混入工程・流出工程 | 両方を判定、流出側チェックリスト更新 | なし | 本案 | 不具合票の `injected_phase`/`escaped_phase`、チェックリストの「追加観点（不具合由来）」 |
| 21 | やり直し範囲 | 影響範囲のみ差分やり直し、専用ゲート | なし | 本案 | `defect impact --write`、`scripts/approve defect DEF-xxx`、工程別の差分タスクファイル |
| 22 | 承認済みゲートの無効化 | ハッシュ不一致で自動無効＋不具合 ID 記録 | なし | 本案 | 不具合ゲート承認時に対象工程ゲートへ `invalidated_by: DEF-xxx` を記録 |

## 提案仕様からの具体化・追加（判断を要した点）

| 項目 | 内容 | 理由 |
|---|---|---|
| 取り込みの ID | 工程 0 は `SRC-xxx`、工程 1 で `REQ-xxx` | 原文の断片と、整理後の要求を区別して追跡するため |
| テストディレクトリ | `test_dirs.unit/integration/system/regression`（既定は `test_dir` 配下） | 単体テスト（工程 4）と結合・システムテスト（工程 6・7）を別ゲートのハッシュ対象にするため |
| 回帰テスト領域 | `test_dirs.regression` は常に書き込み可・ゲート対象外 | 不具合の再現テストを、工程を巻き戻す前に先に書けるようにするため |
| 書き込みガード | 「次工程の開始時に確認」を、成果物領域への書き込み時の確認に拡張 | 工程スキルを経由しない書き込みも止めるため |
| 不具合対応中の継続 | 承認済み不具合ゲートがあり、影響ファイル外なら再開先工程への書き込みを許可 | 「影響範囲外は継続」を、前工程ゲートの無効化と両立させるため |
| Refactor の許可 | タスク開始後に Red を観測していれば、全テスト成功でも src 編集を許可 | Red→Green→Refactor の Refactor を可能にするため（`task start` でリセット） |
| 除外・手動試験の記法 | `- 除外: SRC-xxx（理由）`、見出し外の `- trace: AT-xxx` | 承認済みで編集できない上流項目の除外と、自動化できない受入試験の証跡のため |
| ワークフロー本体の保護 | hooks・ゲート判定ロジック・approve の編集を禁止（`SDLC_MAINTENANCE=1` で解除） | 強制機構そのものの書き換えによる迂回を防ぐため |
| PowerPoint の図 | 画像は抽出、図形＋コネクタの構成図は soffice でスライドを画像化 | 図形のテキストだけでは関係（矢印）が失われるため |

## 動作確認

- 自己テスト `python3 -m unittest discover -s scripts/tests`（27 件）: ゲートのハッシュ無効化、工程順の書き込み制御、
  保護パス、TDD ガード（Red→Green→Refactor・リセット）、Bash ガード、スキル起動ガード、タスク DAG、
  トレース検査・影響範囲、不具合対応の一連（起票→影響範囲→承認→やり直し→クローズ）、4 形式のアダプタ。
- `examples/sample-requirements.md` と構成図入り pptx で、初期化→取り込み→状態表示→TTY 無し承認の拒否を確認。
