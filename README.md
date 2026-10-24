# sdlc-workflow

Claude Code 上で動く、V 字モデルのソフトウェア開発ワークフローです。
要求ドキュメント（Excel / Word / PowerPoint / Markdown）を入力に、
**工程単位・タスク単位の並行処理・人間ゲート・TDD** で開発を進めます。

本体は `~/.claude/`（全プロジェクト共通）に置いて使うのが基本で、プロジェクトの `.claude/` に置けば
そのプロジェクト単体でも使え、`~/.claude/` 版を上書きできます。**インストールと使い方は [USAGE.md](USAGE.md)**。

対応環境: Linux / macOS / Windows（Git for Windows の Git Bash と Python 3.10 以上。PowerShell・コマンドプロンプトからも
ランチャ `scripts\sdlc.cmd`・`scripts\approve.cmd` で操作できます。詳細は USAGE.md「9. Windows で使う」）。

仕様の原典: [`spec/sdlc-workflow-proposal.md`](spec/sdlc-workflow-proposal.md) /
採否判定: [`spec/adoption-report.md`](spec/adoption-report.md)

## 全体像

```
/sdlc（最上位）… state/ を読んで次の工程スキルを起動するだけ
 ├─ 工程スキル phase-*（全工程が同じ型）
 │    計画 → タスク分解(DAG) → 並行実行(最大2) → 統合 → 機械チェック → レビュー → 人間ゲート
 ├─ /defect … 不具合対応（原因工程から差分やり直し）
 ├─ /change … 変更要求（承認後の要求変更・機能追加を、変更開始工程から差分やり直し）
 └─ サブエージェント analyst / designer / test-writer / implementer / reviewer / security-reviewer /
                    investigator / current-analyst / solution-proposer
```

| 工程 | 主な成果物 | 先行作成するテスト |
|---|---|---|
| 0 取り込み | SRC（出典・確信度付きの中間形式） | — |
| 1 要求整理・分析 | REQ、曖昧・矛盾・欠落、質問 Q | — |
| 2 要件定義 | SR / NFR | AT 受入・システムテスト仕様 |
| 3 基本設計 | BD / IF | IT 結合テスト仕様 |
| 4 詳細設計 | DD | UT 仕様＋単体テストコード（Red） |
| 5 実装 | コード（Red→Green→Refactor） | — |
| 6 結合テスト | IT の実装・実行 | — |
| 7 システム／受入テスト | AT の実装・実行、要件カバレッジ | — |

## 使い方（概要）

```bash
pip install -r requirements.txt     # 本体の依存（Python 3.10+）
python3 install.py --user           # ~/.claude/ に配置（プロジェクト単体なら --project <dir>。Windows は py -3 install.py）
cd <プロジェクト> && claude
> /sdlc-init                        # ランチャ scripts/sdlc・CLAUDE.md の import・project.yaml を準備
# input/ に要求ドキュメントを置く
> /sdlc                             # 工程 0 から実行。ゲートで停止する
scripts/approve 00                  # 人が端末で承認（Claude からは実行できない。Windows は .\scripts\approve.cmd 00）
> /sdlc                             # 次工程へ。中断しても /sdlc で続きから再開
```

詳細（配置の選び方・上書き・更新・クラウド環境・トラブルシュート）は [USAGE.md](USAGE.md)。

## 品質ゲートと割り込みフロー

| 仕組み | 内容 |
|---|---|
| 機械チェック | `scripts/sdlc check`。組み込みのトレース検査＋`project.yaml` の `checks`（工程別・MUST/SHOULD/MAY）。MUST 失敗中はレビューに進まず、承認もできない（`scripts/approve` が承認時に再実行する） |
| レビュー | reviewer（作成者と別コンテキスト・チェックリスト＋`rules/review-*.md`）。実装工程は後段に security-reviewer（OWASP 等。Critical/High で不合格）。判定「不合格」の間は承認できない |
| Red / Green の証跡 | `scripts/sdlc test-run --expect red|green`。詳細設計後の Red、実装後の Green を `docs/<工程>/test-run-*.md` に残す |
| 決定事項・未解決事項 | `state/decisions.md` / `state/open-questions.md`。サブエージェントは報告で返し、オーケストレータが一元追記する |
| プロジェクト固有ルール | `rules/common.md`・`rules/<工程ID>.md`（ADD / OVERRIDE / DISABLE / 追加成果物）・`rules/review-<工程ID>.md` |
| /defect | 再現テスト → エビデンス必須の原因調査（investigator）→ 混入/流出工程 → 影響範囲 → 対応方法の提案（solution-proposer: あるべき姿 / 最小修正）→ 人が案を選んで承認 → 差分やり直し |
| /change | 現行解析（current-analyst）→ 対応方法の提案 → 人が案を選んで承認（`scripts/approve change CR-xxx`）→ 変更開始工程から差分やり直し |

## 強制の仕組み（hooks）

| 仕組み | 内容 |
|---|---|
| ゲート（`guard_write.py`） | 工程 k の成果物領域へは、工程 0..k-1 のゲートがすべて有効なときだけ書き込める。承認済み工程の成果物は変更不可 |
| ゲートの有効性 | 判定が承認／条件付き承認 **かつ** 成果物の SHA-256 が承認時と一致 **かつ** 不具合による無効化なし |
| 自己承認の防止 | `state/gates/` への書き込みは常に拒否。`scripts/approve` は TTY 必須で、Claude Code から起動されたプロセス（`CLAUDECODE`）では動かない。Bash / PowerShell からの呼び出しも拒否 |
| hooks が動かないとき | hooks は bash の入口 `run` 経由で起動し（Python を自動で探す）、`onFailure: block` で登録する。bash・Python が無い等で hooks が動かなければ、SDLC プロジェクトでは操作を拒否する（素通りさせない） |
| 設定ファイル・本体の保護 | `~/.claude/settings*.json` と `~/.claude` に置いた本体は、どのプロジェクトからも Claude は編集できない。SDLC プロジェクトでは、プロジェクトの `.claude/settings*.json`・`.claude` に置いた本体・ランチャ `scripts/sdlc`・`scripts/approve` も編集できない |
| 適用範囲 | `~/.claude` の hooks は、`project.yaml` に `workflow: sdlc` があるプロジェクトでだけ工程・TDD を検査する（他のプロジェクトには影響しない）。プロジェクトに hooks があれば `~/.claude` 側は何もしない |
| TDD（`guard_write.py`） | `src_dir` の編集前に `commands.test` を実行し、失敗テストが無ければ拒否（そのタスクで Red を観測後の Refactor は可） |
| テスト改ざん防止 | test-writer / implementer を分離。単体テストは工程 4 の承認で凍結され、実装工程では変更不可 |
| 工程スキル起動（`guard_skill.py`） | 前工程のゲートが無効なら `phase-*` スキルの起動を拒否 |
| シェル（`guard_bash.py`） | 成果物・ゲート・ワークフロー本体を Bash / PowerShell で書き換えるコマンドを拒否（ヒューリスティック） |

### 限界

- Bash 経由の改変検出はヒューリスティックです。すり抜けても、工程成果物の改変はゲートのハッシュ不一致で検知され、
  承認は TTY 必須の `scripts/approve` でしか記録できません。監査証跡としてゲート記録は人が commit してください。
- テストを `src_dir` 配下に置く言語慣習（Go の `_test.go` など）には対応していません（テストは別ディレクトリ）。
- `test_dir` 直下（`unit/` 等の外）のファイル（共有ヘルパー等）はどの工程のゲートにも含まれません。

## ワークフロー本体の保守

本体（`.claude/sdlc/`・`.claude/hooks/sdlc/`・SDLC のスキル/エージェント・`.claude/settings.json`）は、
Claude による編集が hook で禁止されています（ゲートの強制機構を守るため。このソースリポジトリも同様）。
変更するときは、人が環境変数を付けて Claude Code を起動してください:

```bash
SDLC_MAINTENANCE=1 claude
```

クラウド環境（Claude Code on the web）では、環境の設定で環境変数 `SDLC_MAINTENANCE=1` を追加してから新しいセッションを開始します。
環境変数はセッション開始時に読み込まれるため、実行中のセッションでは切り替わりません。
（`state/gates/` はこのモードでも書き込めません。）

自己テスト:

```bash
python3 -m unittest discover -s tests -v
```

## ディレクトリ

### 本体（`~/.claude/` またはプロジェクトの `.claude/` に置く）

```
sdlc/
  RULES.md                    全体ルール（TDD 必須、ゲート必須、ID 体系）。プロジェクトの CLAUDE.md から import
  phase-flow.md               工程内共通フロー
  templates/                  成果物テンプレート（rules/ の雛形を含む）
  checklists/                 工程別レビューチェックリスト
  bin/sdlc                    状態管理 CLI
  bin/approve                 人が実行する承認スクリプト
  bin/py                      本体を動かす Python を探して実行する（SDLC_PYTHON で指定可）
  lib/sdlc_lib/               共通ライブラリ（ゲート・タスク・トレース・TDD・不具合・機械チェック）
  lib/intake/                 取り込みの形式別アダプタ（adapters/ にモジュールを足せば形式を追加できる）
hooks/sdlc/                   ゲート・TDD・シェル・スキル起動のガード（入口は bash の run）
skills/                       sdlc, sdlc-init, phase-*（8 工程）, defect, change
agents/                       analyst, designer, test-writer, implementer, reviewer, security-reviewer,
                              investigator, current-analyst, solution-proposer
settings.json                 hooks と permissions（インストーラが追記）
```

### プロジェクト

```
CLAUDE.md                     全体ルールの import（@~/.claude/sdlc/RULES.md など。scripts/sdlc init が追加）
project.yaml                  プロジェクト固有情報（workflow: sdlc、言語・テスト・コマンド。/sdlc-init で作成）
scripts/sdlc, scripts/approve 本体へのランチャ（プロジェクトの .claude/sdlc を優先、無ければ ~/.claude/sdlc）
scripts/*.cmd                 Windows の PowerShell / コマンドプロンプト用ランチャ
.gitattributes                ランチャ・bash スクリプトの改行を LF に固定（scripts/sdlc init が追加）
input/                        要求ドキュメント原本
docs/<工程>/                  各工程の成果物（plan.md / summary.md / review.md を含む）
state/
  phase.json                  現在工程・ステップ、通常／不具合対応モード
  tasks.yaml                  タスク DAG と進捗（再開用）。完了工程分は state/tasks/ に保管
  gates/<工程>.md             工程ゲートの承認記録（成果物ハッシュ付き）
  gates/defect-DEF-xxx.md     やり直し範囲の承認記録
  defects/DEF-xxx.md          不具合票（DEF-xxx/ に提案書・差分やり直しのタスク）
  changes/CR-xxx.md           変更要求票（CR-xxx/ に現行解析・提案書・差分やり直しのタスク）
  decisions.md                決定事項ログ
  open-questions.md           未解決事項ログ
rules/                        プロジェクト固有ルール・追加のレビュー観点（不具合の再発防止を含む）
.claude/                      （任意）本体のプロジェクト配置・上書き
```

### このソースリポジトリ

```
.claude/                      本体（上の「本体」と同じ形。プロジェクト配置として hooks も有効）
install.py                    インストーラ（--user / --project <dir> / --uninstall / --dry-run）
tests/                        ワークフロー自己テスト
.github/workflows/tests.yml   自己テストを Linux / Windows / macOS で実行する CI
examples/                     動作確認用のサンプル要求ドキュメント
spec/                         仕様の原典と採否レポート
USAGE.md                      インストールと使い方
```
