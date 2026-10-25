---
name: sdlc
description: SDLC ワークフローの最上位オーケストレーター。state/ を読んで現在工程・ゲート状況を判定し、次の工程スキルを起動する（中断からの再開もこれで行う）。開発を進める・続きから再開するときに使う。
---

# /sdlc — 状態管理とルーティングのみ

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/sdlc/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

このスキルは「何を作るか」を持たない。状態を読み、次に起動すべきスキルを決めるだけである。
工程の中身は各工程スキル、不具合は `/defect` に任せる。

## 手順

0. プロジェクトにランチャ `scripts/sdlc` が無ければ、まだ準備されていないので `/sdlc-init` を起動する。
1. `scripts/sdlc status --json` を実行し、`next.action` を読む。
2. `next.action` に応じて 1 つだけ実行する:

| action | すること |
|---|---|
| `init` | `/sdlc-init` スキルを起動する |
| `need_input` | `input/` に要求ドキュメント（xlsx/docx/pptx/pdf/md）を置くよう人に依頼して停止 |
| `run_phase` / `revise` | `next.skill` のスキルを起動する（再開ステップは `next.step`、差戻しなら差戻し対応） |
| `advance` | `scripts/sdlc phase advance` を実行し、手順 1 に戻る（次工程のスキルを起動する） |
| `await_approval` | 下記「承認待ちの提示」を行って**停止** |
| `blocked_upstream` | `next.message` を人に伝え、承認後の変更なら `/defect` で扱うことを提案して停止 |
| `defect` / `change` / `defect_verify` | `next.skill`（`defect` または `change`）のスキルを `next.defect` を引数に起動する |
| `done` | `scripts/sdlc trace matrix` の結果と全ゲートの状態をまとめて報告して終了 |

3. 起動した工程スキルが人間ゲートで停止したら、このスキルも停止する。
   **自分で `scripts/approve` を実行したり、承認を仮定して先へ進んだりしない。**

## 割り込みの受付

人から「仕様を変えたい・機能を足したい」と言われたら `/change`、「不具合がある」と言われたら `/defect` を起動する。
どちらか迷う場合は人に確認する（作り間違いなら /defect、要求の変更なら /change）。

## 承認待ちの提示

```
工程 <phase> は人による承認待ちです。
- レビュー報告: docs/<phase>/review.md
- 成果物一覧: scripts/sdlc gate artifacts <phase>
- 機械チェック: docs/<phase>/checks.md
- 未解決事項: scripts/sdlc question list（優先度 高があれば先に回答してください）
承認・条件付き承認・差戻しは、端末で次を実行してください:
  scripts/approve <phase>
記録後に /sdlc を実行すると続きから進みます。
```

## 再開について

使用量上限などで中断した場合も、`/sdlc` を実行すれば `state/phase.json`（工程・ステップ）と
タスクファイル（タスク単位の進捗）から続きを判定する。工程スキル側で `tasks recover` を行う。
