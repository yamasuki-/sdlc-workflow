# sdlc-workflow

Claude Code 上で動く、V 字モデルのソフトウェア開発ワークフローです。
要求ドキュメント（Excel / Word / PowerPoint / Markdown）を入力に、
**工程単位・タスク単位の並行処理・人間ゲート・TDD** で開発を進めます。

仕様の原典: [`spec/sdlc-workflow-proposal.md`](spec/sdlc-workflow-proposal.md) /
採否判定: [`spec/adoption-report.md`](spec/adoption-report.md)

## 全体像

```
/sdlc（最上位）… state/ を読んで次の工程スキルを起動するだけ
 ├─ 工程スキル phase-*（全工程が同じ型）
 │    計画 → タスク分解(DAG) → 並行実行(最大2) → 統合 → レビュー → 人間ゲート
 ├─ /defect … 不具合対応（原因工程から差分やり直し）
 └─ サブエージェント analyst / designer / test-writer / implementer / reviewer / investigator
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

## 使い方

```bash
pip install -r requirements.txt     # ワークフロー本体の依存（Python 3.9+）
claude                              # このリポジトリで Claude Code を起動
> /sdlc-init                        # project.yaml（言語・テスト FW・コマンド）を対話作成
# input/ に要求ドキュメントを置く
> /sdlc                             # 工程 0 から実行。ゲートで停止する
```

ゲートで停止したら、**人が端末で**承認します（Claude からは実行できません）:

```bash
scripts/approve 00                  # 承認 / 条件付き承認 / 差戻し を対話で記録
git add state/gates && git commit -m "gate: 00-intake"
```

その後 `/sdlc` を再実行すると次工程に進みます。中断（使用量上限など）しても `/sdlc` で続きから再開します。

状態の確認: `scripts/sdlc status`（`-h` で全コマンド）

## 強制の仕組み（hooks）

| 仕組み | 内容 |
|---|---|
| ゲート（`guard_write.py`） | 工程 k の成果物領域へは、工程 0..k-1 のゲートがすべて有効なときだけ書き込める。承認済み工程の成果物は変更不可 |
| ゲートの有効性 | 判定が承認／条件付き承認 **かつ** 成果物の SHA-256 が承認時と一致 **かつ** 不具合による無効化なし |
| 自己承認の防止 | `state/gates/` への書き込みは常に拒否。`scripts/approve` は TTY 必須（Claude の Bash は TTY なし）。Bash からの実行も拒否 |
| TDD（`guard_write.py`） | `src_dir` の編集前に `commands.test` を実行し、失敗テストが無ければ拒否（そのタスクで Red を観測後の Refactor は可） |
| テスト改ざん防止 | test-writer / implementer を分離。単体テストは工程 4 の承認で凍結され、実装工程では変更不可 |
| 工程スキル起動（`guard_skill.py`） | 前工程のゲートが無効なら `phase-*` スキルの起動を拒否 |
| Bash（`guard_bash.py`） | 成果物・ゲート・ワークフロー本体を Bash で書き換えるコマンドを拒否（ヒューリスティック） |

### 限界

- Bash 経由の改変検出はヒューリスティックです。すり抜けても、工程成果物の改変はゲートのハッシュ不一致で検知され、
  承認は TTY 必須の `scripts/approve` でしか記録できません。監査証跡としてゲート記録は人が commit してください。
- テストを `src_dir` 配下に置く言語慣習（Go の `_test.go` など）には対応していません（テストは別ディレクトリ）。
- `test_dir` 直下（`unit/` 等の外）のファイル（共有ヘルパー等）はどの工程のゲートにも含まれません。

## ワークフロー本体の保守

`.claude/hooks/`・`.claude/settings.json`・`scripts/approve`・`scripts/sdlc_lib/` は、
Claude による編集が hook で禁止されています（ゲートの強制機構を守るため）。
変更するときは、人が環境変数を付けて Claude Code を起動してください:

```bash
SDLC_MAINTENANCE=1 claude
```

（`state/gates/` はこのモードでも書き込めません。）

自己テスト:

```bash
python3 -m unittest discover -s scripts/tests -v
```

## ディレクトリ

```
CLAUDE.md                     全体ルール（TDD 必須、ゲート必須、ID 体系）
project.yaml                  プロジェクト固有情報（/sdlc-init で作成）
input/                        要求ドキュメント原本
docs/<工程>/                  各工程の成果物（plan.md / summary.md / review.md を含む）
state/
  phase.json                  現在工程・ステップ、通常／不具合対応モード
  tasks.yaml                  タスク DAG と進捗（再開用）。完了工程分は state/tasks/ に保管
  gates/<工程>.md             工程ゲートの承認記録（成果物ハッシュ付き）
  gates/defect-DEF-xxx.md     やり直し範囲の承認記録
  defects/DEF-xxx.md          不具合票（DEF-xxx/ に差分やり直しのタスク）
.claude/
  settings.json               hooks
  hooks/                      ゲート・TDD・Bash・スキル起動のガード
  skills/                     sdlc, sdlc-init, phase-*（8 工程）, defect
  agents/                     analyst, designer, test-writer, implementer, reviewer, investigator
  sdlc/phase-flow.md          工程内共通フロー
  sdlc/templates/             成果物テンプレート
  sdlc/checklists/            工程別レビューチェックリスト（不具合由来の観点を追記していく）
scripts/
  sdlc                        状態管理 CLI
  approve                     人が実行する承認スクリプト
  intake/convert.py           形式別アダプタ（adapters/ にモジュールを足せば形式を追加できる）
  sdlc_lib/                   共通ライブラリ（ゲート・タスク・トレース・TDD・不具合）
  tests/                      ワークフロー自己テスト
examples/                     動作確認用のサンプル要求ドキュメント
```
