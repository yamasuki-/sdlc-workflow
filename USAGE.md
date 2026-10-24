# 使い方（USAGE）

SDLC ワークフロー本体は、次の 2 通りに置けます。どちらも同じファイル構成で、同じコマンドで使えます。

| 配置 | 置き場所 | 向いている場面 |
|---|---|---|
| **A. ユーザ配置（基本）** | `~/.claude/` | 自分の複数のプロジェクトで共通に使う |
| **B. プロジェクト配置** | `<プロジェクト>/.claude/` | そのプロジェクト単体で使う（チームでリポジトリごと共有する、クラウド環境で使う）／A の内容をそのプロジェクトだけ変える |

A と B を併用すると、**プロジェクトの `.claude/` が `~/.claude/` より優先**されます（後述「上書きの仕組み」）。

---

## 1. 前提

- Python 3.9 以上、git
- 本体の依存パッケージ（hooks もこれを使うので、Claude Code が呼ぶ `python3` に入れる）:
  ```bash
  pip install -r requirements.txt   # PyYAML, openpyxl, python-docx, python-pptx
  ```
- PowerPoint の図をスライド画像として読み取りたい場合は LibreOffice（`soffice`）と `pdftoppm`（任意）

---

## 2. A. ユーザ配置（~/.claude）

### インストール

```bash
git clone <このリポジトリ> sdlc-workflow
cd sdlc-workflow
python3 install.py --user            # 何が置かれるか先に見るなら --dry-run
```

`~/.claude/` に次が置かれ、`~/.claude/settings.json` に hooks と permissions が追記されます（既存の設定は残ります。再実行しても重複しません）。

```
~/.claude/sdlc/            本体（bin・lib・テンプレート・チェックリスト・共通フロー・全体ルール RULES.md）
~/.claude/hooks/sdlc/      ガード（hooks）
~/.claude/skills/          sdlc, sdlc-init, phase-*, defect, change
~/.claude/agents/          analyst, designer, test-writer, implementer, reviewer, security-reviewer,
                           investigator, current-analyst, solution-proposer
```

hooks はすべてのプロジェクトで起動しますが、**`project.yaml` に `workflow: sdlc` があるプロジェクトでだけ**工程・TDD を検査します。
それ以外のプロジェクトへの影響は、`~/.claude` の設定ファイルと本体を Claude が編集できないこと、
このインストーラ（`install.py --user` 等）を Claude が実行できないことだけです。

### プロジェクトで使い始める

```bash
cd <プロジェクト>          # git リポジトリであること
claude
> /sdlc-init
```

`/sdlc-init` は次を行います（`scripts/sdlc init` を内部で実行）。

- ランチャ `scripts/sdlc`・`scripts/approve`（本体を呼ぶだけの小さなスクリプト）を作る
- `CLAUDE.md` に全体ルールの import `@~/.claude/sdlc/RULES.md` を追加する
- `project.yaml`（`workflow: sdlc` 付き）を対話で作る。言語・テストフレームワーク・テストコマンド・機械チェック
- `state/`・`docs/<工程>/`・`.gitignore` を用意する

> 初回は、CLAUDE.md が `~/.claude` のファイルを import することへの許可ダイアログが出ることがあります。許可してください。
> import は次のセッションから読み込まれます。

ランチャと `CLAUDE.md`・`project.yaml` はコミットしてください。

---

## 3. B. プロジェクト配置（プロジェクト単体で使う）

### インストール

```bash
cd sdlc-workflow
python3 install.py --project /path/to/your-project
```

`/path/to/your-project/.claude/` に A と同じ構成が置かれ、`.claude/settings.json` に
`$CLAUDE_PROJECT_DIR/.claude/hooks/sdlc/...` を呼ぶ hooks が追記されます。
`~/.claude` には何も置きません。

```bash
cd /path/to/your-project
claude
> /sdlc-init
```

`CLAUDE.md` には `@.claude/sdlc/RULES.md` が入ります。`.claude/` 一式をコミットすれば、
リポジトリを取得したチームメンバーは追加のインストールなしで使えます（依存パッケージは各自 `pip install`）。

> プロジェクト配置では、`project.yaml` を作る前から hooks が有効です（工程成果物・本体は最初から保護されます）。

### クラウド環境（Claude Code on the web など）で使う場合

クラウドのセッションはリポジトリを毎回新しく取得し、`~/.claude` は引き継がれません。次のどちらかにします。

- **B. プロジェクト配置**にして `.claude/` をコミットする（推奨）
- 環境のセットアップスクリプトで毎回 A を入れる:
  ```bash
  git clone <このリポジトリ> /tmp/sdlc-workflow && pip install -r /tmp/sdlc-workflow/requirements.txt \
    && python3 /tmp/sdlc-workflow/install.py --user
  ```

---

## 4. 上書きの仕組み（A と B の併用・部分的な上書き）

| 対象 | 既定（A） | プロジェクトで上書き | 仕組み |
|---|---|---|---|
| エージェント | `~/.claude/agents/<名前>.md` | `.claude/agents/<名前>.md` | Claude Code の標準（プロジェクト優先） |
| スキル | `~/.claude/skills/<名前>/` | `.claude/skills/<名前>/SKILL.md` | Claude Code は同名スキルを `~/.claude` 側で解決するため、`~/.claude` 版の冒頭でプロジェクト版の有無を確認し、あればそちらに従う |
| hooks | `~/.claude/hooks/sdlc/` | `.claude/hooks/sdlc/`（B のインストールで入る） | 両方登録されていても、プロジェクトに hooks があれば `~/.claude` 側は何もしない |
| CLI・ライブラリ | `~/.claude/sdlc/bin`・`lib` | `.claude/sdlc/bin`・`lib` | ランチャ `scripts/sdlc`・`scripts/approve` がプロジェクトを優先して呼ぶ（bin と lib は組で上書き） |
| テンプレート・チェックリスト・共通フロー・全体ルール | `~/.claude/sdlc/...` | `.claude/sdlc/...`（**ファイル単位**） | スキル・エージェントは `<SDLC>/…` と書かれたファイルを `scripts/sdlc path <相対パス>` で解決する。プロジェクトにあればそれ、無ければ `~/.claude` のもの |

### よくある上書きの例

- **このプロジェクトだけ実装工程のチェックリストを変える**:
  `~/.claude/sdlc/checklists/05-implementation.md` を `.claude/sdlc/checklists/05-implementation.md` にコピーして編集する。
- **詳細設計のテンプレートを社内様式にする**: `.claude/sdlc/templates/detailed-design.md` を置く。
- **あるスキルの手順を変える**: `~/.claude/skills/<名前>/` を `.claude/skills/<名前>/` にコピーして編集する。
- **このプロジェクトだけ本体を固定のバージョンにする**: `python3 install.py --project <dir>`（B を併用）。

上書きの状況は次で確認できます。

```bash
scripts/sdlc where                         # 配置（project / user）と、~/.claude を上書きしているファイルの一覧
scripts/sdlc path checklists/05-implementation.md   # 実際に使われるファイル
```

> 上書きファイルは本体の一部として保護されます（SDLC プロジェクトでは Claude が編集できません）。人が編集するか、
> `SDLC_MAINTENANCE=1` で起動したセッションで編集してください。

### 上書きより先に検討すること: `rules/`

言語・フレームワーク・社内規約など**プロジェクト固有の内容は、本体を上書きせず `rules/` に書く**のが基本です
（雛形は `scripts/sdlc path templates/rules/common.md` など）。

| ファイル | 内容 |
|---|---|
| `rules/common.md` | 技術スタック・コーディング規約・テストの作法など（全工程のエージェントが読む） |
| `rules/<工程ID>.md` | その工程の追加ルール（ADD / OVERRIDE / DISABLE / 追加成果物） |
| `rules/review-<工程ID>.md` | その工程の追加レビュー観点。`/defect` の再発防止で追加される観点もここに入る |

---

## 5. 日々の使い方

```
input/ に要求ドキュメント（xlsx / docx / pptx / md）を置く
> /sdlc                  状態を読んで次の工程を実行する（中断しても続きから再開）
```

各工程は「計画 → タスク分解 → 並行実行（最大 2）→ 統合 → 機械チェック → レビュー → 人間ゲート」で進み、
ゲートで停止します。**承認は人が端末で**行います（Claude からは実行できません）。

```bash
scripts/approve 02                 # 承認 / 条件付き承認 / 差戻し を対話で記録（承認時に機械チェックを再実行）
git add state/gates && git commit -m "gate: 02-system-requirements"
```

その後 `/sdlc` で次の工程へ進みます。

| やりたいこと | 方法 |
|---|---|
| 承認済みの成果物に誤りが見つかった | `/defect`（再現テスト → 原因調査 → 対応方法の提案 → `scripts/approve defect DEF-xxx` → 差分やり直し） |
| 要求を変えたい・機能を足したい | `/change`（現行解析 → 対応方法の提案 → `scripts/approve change CR-xxx` → 差分やり直し） |
| 状態を見る | `scripts/sdlc status` |
| 未解決事項・決定事項を見る | `scripts/sdlc question list` / `scripts/sdlc decision list` |
| コマンドの一覧 | `scripts/sdlc -h` |

---

## 6. 更新・アンインストール

```bash
cd sdlc-workflow && git pull
python3 install.py --user                     # A を更新（本体を置き換える。プロジェクト側のファイルは変えない）
python3 install.py --project <dir>            # B を更新
python3 install.py --user --uninstall         # A を取り除く（settings.json の SDLC の hooks も外す）
python3 install.py --project <dir> --uninstall
```

インストーラは置いたファイルを `sdlc/.install-manifest.json` に記録し、1 ファイルずつ更新します。
**インストール後に変更したファイルと、インストーラが置いていないファイル（プロジェクトで追加した上書きファイルなど）は、
変更・削除せずにそのまま残し、一覧を表示します**（置き換えるなら `--force`）。

プロジェクトで `~/.claude` 版を上書きしているファイルは、A を更新しても自動では追従しません。
`scripts/sdlc where` で一覧を確認し、必要なら取り込み直してください。

---

## 7. ワークフロー本体を変更する（メンテナンスモード）

本体・設定ファイル・ランチャは、ゲートの強制機構を守るため Claude が編集できません。
本体を直すときは、人が環境変数を付けて Claude Code を起動します。

```bash
SDLC_MAINTENANCE=1 claude
```

クラウド環境では、環境の設定で環境変数 `SDLC_MAINTENANCE=1` を追加してから**新しいセッション**を開始します
（環境変数はセッション開始時に読み込まれるため、実行中のセッションでは切り替わりません。
`.claude/settings.local.json` や `~/.claude/settings.json` の `env` に書く方法は、Claude が自分で保護を外せないよう hooks で禁止しています）。
作業が終わったら外してください。`state/gates/` はこのモードでも書き込めません。

このソースリポジトリでの開発も同じです（ソースリポジトリ自体がプロジェクト配置になっています）。
変更後は自己テスト `python3 -m unittest discover -s tests` を通し、`python3 install.py ...` で配置し直します。

---

## 8. トラブルシュート

| 症状 | 確認すること |
|---|---|
| `/sdlc` などのスキルが出てこない | A: `~/.claude/skills/` に、B: `.claude/skills/` に置かれているか。Claude Code を再起動する |
| hooks が効いていない | `/hooks` で SDLC の hooks（`hooks/sdlc/guard_*.py`）が登録されているか。A では `project.yaml` に `workflow: sdlc` があるか |
| すべての書き込みが「ガードの内部エラー」で拒否される | hooks が使う `python3` に `requirements.txt` の依存が入っているか |
| `SDLC ワークフロー本体が見つかりません` | A なら `~/.claude/sdlc/bin/sdlc`、B なら `.claude/sdlc/bin/sdlc` があるか（`install.py` を実行したか） |
| 全体ルール（RULES.md）が読み込まれていない | `CLAUDE.md` の import 行（`@~/.claude/sdlc/RULES.md` か `@.claude/sdlc/RULES.md`）と、外部 import の許可。`scripts/sdlc init` を再実行すると配置に合わせて直る |
| A と B のどちらが使われているか分からない | `scripts/sdlc where` |
