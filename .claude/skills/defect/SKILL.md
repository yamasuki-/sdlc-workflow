---
name: defect
description: 不具合対応フロー（割り込み）。不具合を起票し、再現テスト作成→原因特定（トレース逆追跡）→混入・流出工程判定→影響範囲分析→人間ゲート→混入工程からの差分やり直し→検証・クローズまでを行う。テスト失敗の自動起票後や、人が不具合を報告したときに使う。
argument-hint: "[DEF-ID | 不具合の説明]"
---

# /defect — 不具合対応フロー

通常の工程フローへの割り込み。原因が混入した工程から、影響範囲だけをやり直す。

```
起票 → ①再現テスト(Red) → ②原因特定 → ③混入/流出工程 → ④影響範囲 → ★人間ゲート
     → ⑤混入工程から差分やり直し（工程ごとにゲート） → ⑥検証・クローズ → 本線に復帰
```

不具合票の状態: 起票 → 原因判定済 → 承認済 → 修正中 → 検証済 → クローズ

## 0. 状況把握

`scripts/sdlc status` と `scripts/sdlc defect list` を実行する。
引数が DEF-ID ならその票を、説明文なら新規起票から始める。票の `status` で再開位置を決める:

| status | 再開位置 |
|---|---|
| 起票 | ① または ②（再現テストの有無で判断） |
| 原因判定済 | ★ 人間ゲート待ち（提示して停止） |
| 承認済 | ⑤ 開始（`defect start`） |
| 修正中 | ⑤ 継続（`/sdlc` の指示どおり工程スキルを実行） |
| （phase.json の step が verify） | ⑥ |

## 起票

```
scripts/sdlc defect new --title "<現象の要約>" --detected-in <工程> --severity <致命|高|中|低> \
  [--by auto] [--test <再現テストのパス>]
```
- テスト工程で失敗を検出した場合は `--by auto` で起票し、失敗したテストを `--test` に指定してよい。
- 票の「現象」「再現手順」を記入する（`state/defects/DEF-xxx.md` は Edit 可）。

## ① 再現テスト（Red）

- 再現テストが無ければ、**test-writer** エージェントに `test_dirs.regression` 配下へ作成させる（`trace:` には原因と思われる ID ではなく関連するテスト仕様 ID を書く）。
- 実行して**失敗すること**を確認し、票の `reproduction_test` に記入する。

## ②〜④ 原因特定・混入/流出工程・影響範囲

- **investigator** エージェントに依頼する（作成者・レビュアーとは別の独立エージェント）。
  渡すもの: 不具合票パス、再現テストパス、`.claude/sdlc/checklists/defect.md`。
- investigator が票に `cause_ids` / `injected_phase` / `escaped_phase` を記入し、
  `scripts/sdlc defect impact <DEF> --write` で `impact_ids` / `impact_files` / `rework_phases` を算出する。
- **reviewer** エージェントに `.claude/sdlc/checklists/defect.md` で原因判定をレビューさせ、結果を票の本文に追記させる。
- 混入工程が `external`（要求ドキュメント原文の誤り）の場合: 人に確認し、要求変更として扱う
  （人が `input/` を更新 → rework_phases は 00 から）。
- `scripts/sdlc defect analyzed <DEF>` を実行する。

## ★ 人間ゲート（原因判定・やり直し範囲の承認）

次を提示して**停止する**:
```
## 不具合 <DEF> の原因判定・やり直し範囲の承認依頼
- 現象 / 重大度:
- 原因（トレース ID・箇所）:
- 混入工程 / 流出工程と見逃し理由:
- やり直し工程: <rework_phases>（承認すると該当工程のゲートは「再承認要」になります）
- 影響範囲: <impact_ids / impact_files の要約>（範囲外の作業は継続します）
承認は端末で: scripts/approve defect <DEF>
```

## ⑤ 混入工程から差分やり直し

1. `scripts/sdlc defect start <DEF>` — 不具合対応モードに切り替わり、影響範囲内の本線タスクは停止（blocked）される。
2. `/sdlc` の指示どおり、やり直し工程の工程スキルを順に実行する。工程スキルは
   `.claude/sdlc/phase-flow.md` の「差分やり直し」に従い、**影響範囲の ID だけ**を対象にする。
3. 各やり直し工程は通常どおりレビュー → 人間ゲート（`scripts/approve <工程>`）→ `scripts/sdlc phase advance`。
4. 実装のやり直しでは、再現テストが Red であることが TDD ガードの条件になる（再現テスト → 修正）。

## ⑥ 検証・クローズ

1. `project.yaml` の `commands.test` で再現テストが Green、回帰テストを含め全件成功を確認する。
2. **再発防止**:
   - 流出工程のチェックリスト `.claude/sdlc/checklists/<流出工程>.md` の「追加観点（不具合由来）」に `- [DEF-xxx] 観点` を追記する。
   - 混入工程と対になるテスト仕様にこの不具合を検出するケースが追加されていることを確認する（⑤で追加済みのはず）。
   - 票の「再発防止」節を記入する。
3. `scripts/sdlc defect close <DEF>` — 全テスト成功を確認してクローズし、本線の工程・停止タスクを復帰させる。
4. `git add -A && git commit -m "<DEF>: クローズ"`。`/sdlc` で本線を再開する。

## 並行中タスクの扱い

- 影響範囲外の本線タスクは継続してよい（`scripts/sdlc tasks next --main`）。書き込みガードは
  承認済みの不具合ゲートがあり、影響ファイル外であれば再開先工程への書き込みを許可する。
- 影響範囲内のタスクは `blocked` のまま、クローズ時に自動で `pending` に戻る。
