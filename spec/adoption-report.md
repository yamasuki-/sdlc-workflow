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

- 自己テスト `python3 -m unittest discover -s scripts/tests`（初版 27 件、補完後 36 件）: ゲートのハッシュ無効化、工程順の書き込み制御、
  保護パス、TDD ガード（Red→Green→Refactor・リセット）、Bash ガード、スキル起動ガード、タスク DAG、
  トレース検査・影響範囲、不具合対応の一連（起票→影響範囲→承認→やり直し→クローズ）、4 形式のアダプタ。
- `examples/sample-requirements.md` と構成図入り pptx で、初期化→取り込み→状態表示→TTY 無し承認の拒否を確認。

---

# software_dev_workflow からの補完

`yamasuki-/software_dev_workflow`（dev-workflow スキルセット）は別の思想（機能単位のフェーズバッチ・Skill 5 / Agent 26・
レビュー pass で前進）で作られているため参照のみとし、sdlc-workflow に足りないものを本ワークフローの型
（V 字工程・ハッシュ付き人間ゲート・hooks による強制）に合わせて取り込んだ。採否は依頼者が選定した。

| 参照元の要素 | 判定 | sdlc-workflow での実現 |
|---|---|---|
| security-review（OWASP Top 10・LLM Top 10・依存脆弱性・IaC） | 採用 | `security-reviewer` エージェント＋`checklists/security.md`。実装工程の reviewer の後段。不合格の間は承認不可 |
| auto-check（MUST/SHOULD/MAY の機械チェック、未インストールは skip） | 採用 | `project.yaml` の `checks`＋`scripts/sdlc check`。組み込み MUST にトレース検査。承認時に approve が再実行し MUST 失敗なら承認不可 |
| testing mode=red/green（Red/Green 確認の分離） | 採用 | `scripts/sdlc test-run --expect red|green` で証跡を工程成果物に残す（言語非依存のため判定は終了コード、件数の確認はレビュアー） |
| 詳細設計 9 章構成・UI/DB 設計・NFR カテゴリ | 採用 | `templates/detailed-design.md`（サブ機能・IF・シーケンス・状態遷移）、`ui-design.md`・`db-design.md`・`nfr.md` |
| bug-investigation（エビデンス必須・修正禁止・一時計装の原状復帰・triage） | 採用 | `investigator` を強化（mode=bug / mode=triage）。不具合票に「調査エビデンス」節 |
| solution-proposal（あるべき姿を起点に複数案、人が選定） | 採用 | `solution-proposer` エージェント。票の `options` / `recommended`、`scripts/approve` で案を選定し `selected_option` に記録 |
| feature-add-workflow（現行解析→提案→設計差分→承認→TDD） | 採用（形を変更） | `/change` スキル＋`current-analyst`。不具合と同じ差分やり直し機構（票 CR-xxx・やり直し範囲ゲート・ゲート無効化）で扱う |
| decisions.md / open-questions.md（オーケストレータ専任で一元追記） | 採用 | `state/decisions.md`・`state/open-questions.md`、`scripts/sdlc decision|question` |
| dev-workflow-overlay（stack/project 2 層ルール・ADD/OVERRIDE/DISABLE） | 採用（簡略化） | `rules/common.md`・`rules/<工程ID>.md`・`rules/review-<工程ID>.md`。言語別プリセットは同梱しない（MUST-7: 言語固有情報はプロジェクト側） |
| reverse-design-workflow（既存コードから設計を復元） | 不採用 | 思想と規模が大きく異なるため別途検討 |
| Git 統合（保護ブランチで開始しない・commit 前確認・履歴改変禁止） | 不採用 | 依頼者の選定外 |
| Cowork 向けフォールバック・進捗報告の粒度 | 一部採用 | タスク指示テンプレートにスコープ規律と出力の長さの規律のみ追加 |
| フェーズバッチ・per_feature/cross の 2 段レビュー・COMMON 擬似機能 | 不採用 | sdlc-workflow は工程単位で全成果物を 1 体の reviewer が横断レビューする（共通化の観点はレビューで扱う） |
| human-checkpoint の skip / 無効化 | 不採用 | 人間ゲートは必須要件（MUST-4）。スキップ手段は設けない |

あわせて、補完作業中に見つかった本体の問題を修正した:

- Bash ガードがコマンド文字列中の `scripts/approve` の言及（コミットメッセージ・grep 引数など）まで拒否していた → 実行位置の呼び出しだけを拒否
- `.claude/settings.local.json` と リポジトリ外の `~/.claude/settings*.json` が保護されておらず、env で `SDLC_MAINTENANCE` を設定して保護を外せた → 編集を拒否
- `state/gates/` の参照（`cat` 等）まで拒否していた → 変更系のコマンドだけを拒否

---

# 配置: ~/.claude を基本とし、プロジェクトの .claude で上書きする

本体を `~/.claude/`（全プロジェクト共通）に置くことを基本とし、プロジェクトの `.claude/` で上書きでき、
プロジェクトの `.claude/` だけでも使えるようにした（使い方は `USAGE.md`）。

| 課題（変更前） | 対応 |
|---|---|
| hooks が `scripts/sdlc_lib` を相対パスで読み、`~/.claude` に置くと動かない | 本体を `.claude/sdlc/{bin,lib}` に集約し、hooks は自分の位置（またはプロジェクトの `.claude/sdlc/lib`）から読む |
| スキル・エージェントが `scripts/sdlc`・`.claude/sdlc/...` をプロジェクト内の固定パスで参照 | プロジェクトにはランチャ `scripts/sdlc`・`scripts/approve` だけを置き（`scripts/sdlc init` が生成）、本体のファイルは `<SDLC>/…` と書いて `scripts/sdlc path` でファイル単位に解決 |
| `~/.claude` の hooks が全プロジェクトで工程の検査をしてしまう | `project.yaml` の `workflow: sdlc` がある SDLC プロジェクトでだけ検査する |
| `~/.claude` とプロジェクトの両方に hooks があると二重に実行される | プロジェクトに hooks があれば `~/.claude` 側は何もしない |
| Claude Code は同名スキルを `~/.claude` 側で解決する（プロジェクト版で上書きできない） | `~/.claude` 版の冒頭で `${CLAUDE_SKILL_DIR}` を確認し、プロジェクト版があればそれに従う |
| 不具合の再発防止観点を本体のチェックリストに追記していた（`~/.claude` だと全プロジェクトに波及） | プロジェクトの `rules/review-<工程ID>.md` に追記する |
| 全体ルールを `CLAUDE.md` として置いていた（`~/.claude/CLAUDE.md` だと全プロジェクトに波及） | `sdlc/RULES.md` とし、プロジェクトの `CLAUDE.md` から import する |
| `~/.claude` に置いた本体・設定を Claude が書き換えられる | どのプロジェクトからでも hooks で拒否（インストーラの実行も人に限る） |

---

# Windows 対応

PowerShell・コマンドプロンプトから bash（Git for Windows）を起動できる前提で、Windows で使えるようにした。

| 問題（変更前） | 対応 |
|---|---|
| hooks を `python3 ...` で呼んでおり、Windows では `python3` が無い・Store のエイリアスのことが多い | hooks は bash の入口 `hooks/sdlc/run` から起動し、`sdlc/bin/py` が `SDLC_PYTHON` → `python3` → `python` → `py -3` の順に実際に動く Python を探す |
| hook が起動できない・異常終了すると Claude Code は**素通り**させる（非ブロッキング） | hooks を `onFailure: block` で登録。Python が無い場合は SDLC プロジェクトでのみ拒否（無関係なプロジェクトは止めない） |
| Windows の Claude Code は既定で PowerShell ツールを使い、Bash ガードが働かない | ガードを `Bash|PowerShell` に適用し、PowerShell の書き込みコマンド・`\` 区切りのパスを検出。プロジェクト配置では PowerShell ツールを無効化して Bash に寄せる |
| ランチャが Python スクリプト（拡張子なし）で、PowerShell / コマンドプロンプトから実行できない | ランチャを bash スクリプトにし、`scripts\sdlc.cmd`・`scripts\approve.cmd` を追加（cp932 でも動くよう ASCII のみ） |
| テスト・機械チェックのコマンドを `shell=True`（Windows では cmd.exe）で実行していた | Git Bash で実行（WSL の bash は除外） |
| 入出力の文字コード（cp932）で日本語・記号が壊れ、hook が異常終了しうる | hooks・CLI を UTF-8 で入出力（`PYTHONUTF8=1`、標準入出力の再設定） |
| `core.autocrlf` で bash スクリプトが CRLF になり動かない／ゲートのハッシュが OS で変わる | `.gitattributes` で LF に固定。成果物ハッシュはテキストの CRLF を LF にそろえて計算 |
| mintty（Git Bash の画面）では TTY と判定されず承認できない／新しいコンソールを開けば Claude でも TTY を得られる | Windows では `scripts\approve.cmd` を案内。`CLAUDECODE` が設定されたプロセスからの承認を拒否。`approve` の間接的な呼び出し（cmd /c・Start-Process・script -c 等）も検出 |
| Windows で動作確認できない | GitHub Actions で Linux / Windows / macOS × Python 3.9 / 3.12 の自己テストを実行 |

あわせて、Bash ガードが `install.py` というファイル名を `install` コマンド（書き込み）と誤認していたのを直した。
