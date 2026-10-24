---
name: sdlc-init
description: プロジェクト固有情報 project.yaml（言語・テストフレームワーク・コマンド・ディレクトリ）を対話的に作成し、state/ と docs/ を初期化する。最初に一度、または project.yaml を直すときに使う。
---

# /sdlc-init — project.yaml の作成

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/sdlc-init/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

ワークフロー本体は言語非依存。言語・テストに関する情報はすべて `project.yaml` に置く。

## 手順

1. 依存関係を確認する: `python3 -c "import yaml, openpyxl, docx, pptx"`。
   失敗したら `pip install -r requirements.txt` を人に依頼する（hook も PyYAML を使う）。
2. **準備**: プロジェクトにランチャ `scripts/sdlc` が無ければ、本体を直接呼んで作る:
   `python3 "${CLAUDE_SKILL_DIR}/../../sdlc/bin/sdlc" init`
   これでランチャ（`scripts/sdlc`・`scripts/approve`）、`state/`・`docs/`、`.gitignore`、
   CLAUDE.md の全体ルール import（`@~/.claude/sdlc/RULES.md`、プロジェクト配置なら `@.claude/sdlc/RULES.md`）、
   `project.yaml` の雛形（`workflow: sdlc` 付き）が用意される。以降は `scripts/sdlc` を使う。
   CLAUDE.md の import は次回の起動から読み込まれる（初回は外部ファイルの読み込み許可を求められることがある）。
   既存の `project.yaml` があれば読む（`workflow: sdlc` が無ければ追加する）。
3. 既存コードやビルド定義（package.json, pyproject.toml, pom.xml, go.mod 等）があれば読み、候補を推定する。
4. AskUserQuestion で次を確認する（推定値があれば推奨として先頭に出す）:
   - 言語 / テストフレームワーク
   - `commands.test`（終了コード 0 = 全成功。**TDD ガードがこのコマンドで Red/Green を判定する**）
   - 任意: `test_unit` / `test_integration` / `test_system` / `lint` / `coverage` / `coverage_threshold`
   - `src_dir` / `test_dir`（既定の `test_dirs`: `<test_dir>/unit|integration|system|regression`）
5. 機械チェックゲート（`checks`）を設定する。スタックに合うツールを MUST / SHOULD / MAY に振り分けて提案し、人に確認する:
   - MUST: 失敗したらレビューに進めない・ゲートを承認できないもの（例: lint、型検査、フォーマット検査、ビルド）
   - SHOULD: 警告扱い（例: 依存脆弱性スキャン、複雑度、シークレットスキャン）
   - MAY: 参考情報（例: リンク切れ、重複コード、mutation testing）
   - `common` は全工程、工程 ID のブロック（例 `05-implementation`）はその工程だけに適用される。
     文書工程向けに Markdown lint や Mermaid 構文検査を common に置いてもよい。
   - 自動修正するコマンド（`--fix` / `--write`）は使わない（検査のみ）。
6. `project.yaml` を書き、`scripts/sdlc project check` が通るまで直す。
   - `src_dir`・テストディレクトリは `docs/` `input/` `state/` `scripts/` `.claude/` 等と重ねない。
   - テストを src_dir 配下に置く言語慣習（Go の `_test.go` 等）はこのワークフローでは使えないため、別ディレクトリにする。
7. `scripts/sdlc init` を再実行する（project.yaml の内容に合わせた初期化。何度実行してもよい）。
8. プロジェクト固有ルールが要るか人に確認し、要るなら `<SDLC>/templates/rules/` を `rules/` にコピーして記入する
   （コーディング規約・工程別の追加ルール・追加のレビュー観点。言語・フレームワーク固有の内容はここに書く）。
9. `src_dir`・各テストディレクトリが無ければ作成し、`commands.test` が実行できること（テスト 0 件で成功または想定どおりの結果）を確認する。
   `scripts/sdlc check 00` で checks のコマンドが動くか（未インストールのツールが無いか）も確認する。
10. `.gitignore` にビルド成果物・キャッシュ（言語に応じて）を追記する（ゲートのハッシュから除外される）。
11. 決めたこと（言語・ツールの選定理由など）を `scripts/sdlc decision add` で記録する。
12. `git add -A && git commit -m "sdlc-init: project.yaml"`。
13. 次の一手を伝える: 「`input/` に要求ドキュメントを置き、`/sdlc` を実行してください」。
