# sdlc-workflow（ワークフロー本体のソースリポジトリ）

このリポジトリは SDLC ワークフロー本体の開発用です。利用者向けの使い方は `USAGE.md`、構成は `README.md`。

## 構成

- 本体はすべて `.claude/` 配下にあり、`install.py` がこの形のまま `~/.claude/`（全プロジェクト共通）または
  `<プロジェクト>/.claude/`（プロジェクト単体・上書き）に配置する。
  - `.claude/sdlc/` … 本体（`bin/`・`lib/`・`templates/`・`checklists/`・`phase-flow.md`・`RULES.md`）
  - `.claude/hooks/sdlc/` … ガード（hooks）
  - `.claude/skills/<SDLC のスキル>/`・`.claude/agents/<SDLC のエージェント>.md`
- 置く対象の一覧は `.claude/sdlc/lib/sdlc_lib/config.py` の `SKILL_NAMES`・`AGENT_NAMES`・`BODY_DIRS`・`BODY_FILES`。
  スキル・エージェントを追加・改名したらここも更新する。
- プロジェクトで使うときの全体ルールは `.claude/sdlc/RULES.md`（プロジェクトの CLAUDE.md から import される）。

## 開発のルール

- このリポジトリ自体もプロジェクト配置として hooks が有効なので、本体（`.claude/sdlc`・`.claude/hooks/sdlc` 等）の
  編集は `SDLC_MAINTENANCE=1` で起動したセッションで行う。
- 変更したら自己テストを通す: `python3 -m unittest discover -s tests`
- `.claude/settings.json` はインストーラのプロジェクト配置と同じ内容に保つ（自己テストで検査している）。
- 言語・テストフレームワーク固有の内容を本体に入れない（プロジェクトの `project.yaml`・`rules/` に置く）。
- 利用者に影響する変更は `USAGE.md` と `README.md` に反映する。
