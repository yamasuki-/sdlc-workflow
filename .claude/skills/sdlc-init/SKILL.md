---
name: sdlc-init
description: プロジェクト固有情報 project.yaml（言語・テストフレームワーク・コマンド・ディレクトリ）を対話的に作成し、state/ と docs/ を初期化する。最初に一度、または project.yaml を直すときに使う。
---

# /sdlc-init — project.yaml の作成

ワークフロー本体は言語非依存。言語・テストに関する情報はすべて `project.yaml` に置く。

## 手順

1. 依存関係を確認する: `python3 -c "import yaml, openpyxl, docx, pptx"`。
   失敗したら `pip install -r requirements.txt` を人に依頼する（hook も PyYAML を使う）。
2. 既存の `project.yaml` があれば読む。無ければ `.claude/sdlc/templates/project.yaml` を雛形にする。
3. 既存コードやビルド定義（package.json, pyproject.toml, pom.xml, go.mod 等）があれば読み、候補を推定する。
4. AskUserQuestion で次を確認する（推定値があれば推奨として先頭に出す）:
   - 言語 / テストフレームワーク
   - `commands.test`（終了コード 0 = 全成功。**TDD ガードがこのコマンドで Red/Green を判定する**）
   - 任意: `test_unit` / `test_integration` / `test_system` / `lint` / `coverage` / `coverage_threshold`
   - `src_dir` / `test_dir`（既定の `test_dirs`: `<test_dir>/unit|integration|system|regression`）
5. `project.yaml` を書き、`scripts/sdlc project check` が通るまで直す。
   - `src_dir`・テストディレクトリは `docs/` `input/` `state/` `scripts/` `.claude/` 等と重ねない。
   - テストを src_dir 配下に置く言語慣習（Go の `_test.go` 等）はこのワークフローでは使えないため、別ディレクトリにする。
6. `scripts/sdlc init` で `state/`・`docs/<工程>/` を作成する。
7. `src_dir`・各テストディレクトリが無ければ作成し、`commands.test` が実行できること（テスト 0 件で成功または想定どおりの結果）を確認する。
8. `.gitignore` にビルド成果物・キャッシュ（言語に応じて）を追記する（ゲートのハッシュから除外される）。
9. `git add -A && git commit -m "sdlc-init: project.yaml"`。
10. 次の一手を伝える: 「`input/` に要求ドキュメントを置き、`/sdlc` を実行してください」。
