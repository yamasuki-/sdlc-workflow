---
name: change
description: 変更要求フロー（割り込み）。承認済みの成果物に対する要求の変更・機能の追加を、起票→現行解析→対応方法の提案→人間ゲート（案の選定・やり直し範囲の承認）→変更開始工程からの差分やり直し→検証・クローズで扱う。「仕様を変えたい」「機能を追加したい」と言われたとき、要求ドキュメント（input/）が改訂されたときに使う。
argument-hint: "[CR-ID | 変更内容の説明]"
---

# /change — 変更要求フロー

> **配置と上書き**: このスキルのディレクトリは `${CLAUDE_SKILL_DIR}`。これが `~/.claude/skills/` 配下で、
> プロジェクトに `.claude/skills/change/SKILL.md` がある場合は、そちらを Read してその指示に従い、以下は使わない
> （Claude Code は同名スキルを `~/.claude` 側で解決するため、プロジェクト版はこの方法で優先させる）。
> `<SDLC>/…` はワークフロー本体のファイル。`scripts/sdlc path <…>` で実際のパスを得てから読む。

不具合（`/defect`）と同じ「影響範囲を算出 → 人が承認 → 該当工程から差分やり直し」の仕組みで、
**承認済みの成果物に対する意図的な変更**を扱う。不具合と違い、起点は「誤り」ではなく「要求の変更」である。

```
起票 → ①現行解析 → ②対応方法の提案 → ★人間ゲート（案の選定・やり直し範囲）
     → ③変更開始工程から差分やり直し（工程ごとにゲート）→ ④検証・クローズ → 本線に復帰
```

## /change と /defect の使い分け

| 状況 | 使うフロー |
|---|---|
| 成果物が要求・上流と食い違っている（作り間違い） | `/defect` |
| 要求そのものが変わった・機能を足したい・input/ の要求ドキュメントが改訂された | `/change` |
| 調べたら原因は要求ドキュメント原文の誤りだった（injected_phase: external） | `/defect` から人に確認し、要求変更なら `/change` に切り替える |

まだどの工程のゲートも承認されていない範囲の変更なら、このフローは不要（その工程の作業として直す）。

## 0. 状況把握と起票

`scripts/sdlc status` と `scripts/sdlc change list` を確認する。新規なら:

```
scripts/sdlc change new --title "<変更の要約>" [--severity 致命|高|中|低]
```
`state/changes/CR-xxx.md` の「変更内容」「現行の動作」「変更後の期待動作・受入条件」を、依頼者の言葉で記入する。
**この 3 点のどれかが欠けていれば、先に人に確認する**（AskUserQuestion）。

## ① 現行解析 — current-analyst

**current-analyst** エージェントに依頼する（読み取り専用）。渡すもの: 変更要求票のパス。
- 関連 ID・関連ファイル・既存テストのカバー状況・影響範囲候補が `state/changes/CR-xxx/current-analysis.md` に書かれ、
  票に `cause_ids`（起点 ID）・`start_phase`（変更開始工程）が記入される。
- **依頼者の認識とコード実態の食い違い**が報告されたら、提案に進む前に人に確認する。
- 解析の結果、そもそも何を作るかの再定義が必要（要求整理からやり直すべき規模）と分かったら、その旨を人に提案する。

## ② 対応方法の提案 — solution-proposer

**solution-proposer** エージェントに依頼する。渡すもの: 変更要求票・現行解析書。
- 「あるべき姿（理想設計）」案と「最小修正」案を含む 2〜4 案と推奨案が `state/changes/CR-xxx/proposal.md` に書かれ、
  票の `options` / `recommended` / `rework_phases` が記入される。
- `scripts/sdlc change impact CR-xxx --write` の結果と提案の `rework_phases` が整合しているか確認する。
- 必要に応じて **reviewer** に `<SDLC>/checklists/change.md` で解析と提案をレビューさせる。
- `scripts/sdlc change analyzed CR-xxx`。

## ★ 人間ゲート（案の選定・やり直し範囲の承認）

次を提示して**停止する**:
```
## 変更要求 <CR> の承認依頼
- 変更内容 / 重要度:
- 現行解析の要点（食い違いの有無）:
- 対応方法の選択肢: A) 理想 … / B) 最小修正 … （推奨: A、理由: あるべき姿との乖離・技術的負債）
- やり直し工程: <rework_phases>（承認すると該当工程のゲートは「再承認要」になります）
- 影響範囲: <impact_ids / impact_files の要約>（範囲外の作業は継続します）
承認と案の選定は端末で: scripts/approve change <CR>
```
理想案を選ばなかった場合、先送りにした技術的負債を `scripts/sdlc decision add` で記録する。

## ③ 変更開始工程から差分やり直し

1. `scripts/sdlc change start CR-xxx` — 変更対応モードに切り替わり、影響範囲内の本線タスクは停止される。
2. `/sdlc` の指示どおり、やり直し工程の工程スキルを順に実行する。工程スキルは
   `<SDLC>/phase-flow.md` の「差分やり直し」に従い、**選定された案の範囲・影響範囲の ID だけ**を対象にする。
3. V 字左側でテストを先に変更・追加する（要件変更 → AT、IF 変更 → IT、モジュール変更 → UT）。TDD の規律は通常どおり。
4. 各やり直し工程は通常どおり機械チェック → レビュー → 人間ゲート（`scripts/approve <工程>`）→ `scripts/sdlc phase advance`。

## ④ 検証・クローズ

1. `commands.test` で全テストが成功することを確認する。
2. 票の「経緯」に結果を記入し、`scripts/sdlc change close CR-xxx` — 本線の工程・停止タスクが復帰する。
3. `git add -A && git commit -m "<CR>: クローズ"`。`/sdlc` で本線を再開する。
