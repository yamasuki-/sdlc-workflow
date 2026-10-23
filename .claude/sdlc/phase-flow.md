# 工程内の共通フロー（全工程が同じ型）

```
計画 → タスク分解(DAG) → 並行実行(最大2) → 統合 → レビュー → 人間ゲート
plan    decompose          execute            integrate  review     gate
```

各工程スキル（`phase-*`）はこの型に従い、工程固有の内容（入力・成果物・分解の指針・自己検証）だけを定める。
現在のステップは `state/phase.json` の `step` に記録し、ステップを移るたびに
`scripts/sdlc phase step <step>` を実行する。中断後は記録されたステップから再開する。

`<P>` は工程 ID（例 `02-system-requirements`）を表す。

---

## 0. 開始・再開

1. `scripts/sdlc status` を実行し、`現在工程 == <P>` であることと、再開ステップを確認する。
2. `scripts/sdlc gate check <P>` で前工程ゲートが有効か確認する（無効なら停止して人に報告）。
3. 前工程のゲート記録 `state/gates/<前工程>.md` を **Read ツールで**読み、**条件付き承認の条件**・コメントを把握する。
   条件は本工程の計画に必ず反映する。
4. タスクファイルに `in_progress` が残っていれば中断からの再開である。
   `scripts/sdlc tasks recover` で pending に戻し、`git worktree list` に残った該当タスクの worktree は
   `git worktree remove --force <path>` で破棄してから再実行する。
5. 不具合対応モード（`mode: defect`）なら「差分やり直し」（末尾）を併せて適用する。
   ゲートが差戻し（`revise`）なら「差戻し対応」（末尾）を適用する。

## 1. 計画（plan）

- 入力: 前工程までの**承認済み**成果物（`docs/<前工程>/`）と前工程ゲートのコメント・条件。
- `docs/<P>/plan.md` をテンプレート `.claude/sdlc/templates/plan.md` から作成する:
  作業範囲（対象 ID）、成果物ファイル構成、採番範囲、前工程の条件への対応、リスク・前提。
- 完了したら `scripts/sdlc phase step decompose`。

## 2. タスク分解（decompose）

- `state/tasks.yaml`（不具合対応モードでは `scripts/sdlc status` が示すタスクファイル）を
  テンプレート `.claude/sdlc/templates/tasks.yaml` に従って作成する。
- 規則:
  - 1 タスク = 1 エージェントが 1 回で完了できる大きさ（目安: 成果物ファイル 1〜3 個）。
  - `files` に**担当ファイルをすべて**列挙する。同じファイルを触るタスクは依存関係でつなぐ（並行させない）。
  - `trace_ids` に対象 ID（上流 ID または採番予定の ID）を書く（不具合時の影響判定に使う）。
  - `agent` は工程スキルが指定するもの（analyst / designer / test-writer / implementer）。
  - 実装・テスト工程（05〜07）のコード作成タスクは `worktree: true`。文書工程は `false`。
  - テスト（test-writer）と実装（implementer）は必ず別タスク・別エージェントにする。
- `scripts/sdlc tasks validate` が通るまで直す。
- `git add -A && git commit -m "<P>: 計画・タスク分解"` で**コミットする**（worktree は HEAD から作られるため）。
- `scripts/sdlc phase step execute`。

## 3. 並行実行（execute）

次をタスクが尽きるまで繰り返す。

1. `scripts/sdlc tasks next` で開始できるタスク（最大 2 件、担当ファイル非競合）を得る。
2. 各タスクについて `scripts/sdlc task start <ID>` を実行する。
3. **1 つのメッセージの中で** Agent ツールを最大 2 回呼び出して並行実行する。
   - `subagent_type`: タスクの `agent`
   - `isolation: "worktree"`: タスクの `worktree: true` のときのみ
   - `prompt`: 下の「タスク指示テンプレート」
4. 結果を受け取ったら検証する:
   - 担当ファイル以外を変更していないか（`git status` / worktree の `git diff --stat`）
   - 自己検証結果が「合格」か、トレース記法が守られているか
   - 合格 → `scripts/sdlc task done <ID> --result "<要約・自己検証結果>"`
   - 不合格 → `scripts/sdlc task fail <ID> --result "<理由>"`。1 回だけ指示を補って再実行し、
     再度失敗したら人に報告して停止する。
5. worktree タスクは完了ごとにブランチをメインへ取り込む: `git merge --no-ff <ブランチ>` →
   `git worktree remove <path>`。コンフリクトは担当ファイル設計の誤りなので、解消内容をレビューに報告する。
6. 使用量上限などで中断しても、`task start/done` の記録から再開できる。こまめに記録すること。

全タスクが done になったら `scripts/sdlc phase step integrate`。

### タスク指示テンプレート

```
あなたは SDLC ワークフローの <agent> として、タスク <ID>「<title>」を担当する。
工程: <P>（<工程名>）
入力（読むもの）: <上流成果物のパス・ID>
担当ファイル（これ以外は変更禁止）: <files>
対象 ID: <trace_ids>
作業内容: <工程スキルが定める作業>
テンプレート: <.claude/sdlc/templates/...>
完了条件: <工程スキルの自己検証項目>
禁止: state/ の変更、scripts/approve の実行、担当外ファイルの変更、承認済み成果物の変更
（worktree の場合）作業の最後に担当ファイルを git add してコミットすること。
最後に「結果報告フォーマット」で報告すること。
```

## 4. 統合（integrate）

- 全成果物の整合性を確認する:
  - `scripts/sdlc trace check`（現在工程までのルール）を通す。
  - ID の重複・欠番・用語の揺れ、ファイル間の矛盾を確認する。
  - コードを含む工程は `project.yaml` の `commands.test` / `lint` / `coverage` を実行する。
- 発見した不整合は修正タスクとして tasks.yaml に追加し、3 に戻って実行する。
- `docs/<P>/summary.md` に成果物一覧・統合チェック結果・テスト結果を記録する。
- `scripts/sdlc phase step review`。

## 5. レビュー（review）

- **reviewer エージェント 1 体**（並行させない）に依頼する。作成者とは別コンテキストであること。
  - 渡すもの: 工程 ID、成果物パス、`.claude/sdlc/checklists/<P>.md`、上流の承認済み成果物、
    前工程ゲートの条件、`docs/<P>/summary.md`
  - 出力先: `docs/<P>/review.md`（テンプレート `.claude/sdlc/templates/review.md`）
- 指摘があれば、指摘ごとに**元の作成者と同じ種類のエージェント**で修正タスクを作り（reviewer には直させない）、
  実行後に再レビューする。最大 3 往復。残った指摘は `review.md` の「残指摘」に理由付きで残す。
- 既存テストの削除・期待値の変更があれば `review.md` に必ず明記させる。
- `git add -A && git commit -m "<P>: レビュー完了"`。
- `scripts/sdlc phase step gate`。

## 6. 人間ゲート（gate）

人に次を提示して**停止する**（自分で承認しない・次工程に進まない）:

```
## 工程 <P> のゲート承認依頼
- 成果物: <docs/<P>/ 以下とコード等の一覧>（`scripts/sdlc gate artifacts <P>`）
- レビュー結果: docs/<P>/review.md（判定・残指摘の要約）
- トレーサビリティ: scripts/sdlc trace check の結果
- 人に判断してほしい点: <未解決の質問・前提・リスク>

承認・差戻しは端末で次を実行してください:
  scripts/approve <P>
承認後に /sdlc を実行すると次工程へ進みます。
```

---

## 差戻し対応（ゲートが「差戻し」の場合）

1. `state/gates/<P>.md` のコメント（修正指示）を Read で読む。
2. 指摘ごとに修正タスクを tasks.yaml に追加 → 3 実行 → 4 統合 → 5 レビュー（差戻し指摘が解消したかを観点に追加）→ 6 ゲート。

## 差分やり直し（不具合対応モードの場合）

1. `state/defects/<DEF>.md` の `impact_ids` / `impact_files` / 原因を読む。
2. 計画は `docs/<P>/plan.md` に「## <DEF> 差分やり直し」節を追記する。**影響範囲の ID・ファイルだけ**を対象にし、全面やり直しにしない。
3. タスクファイルは `state/defects/<DEF>/tasks-<P>.yaml`（`scripts/sdlc` が自動選択する）。
4. 混入工程と対になるテスト仕様に、この不具合を検出するケースを追加する（例: 詳細設計起因 → UT を追加）。
5. レビューでは「不具合原因が解消したか」「影響範囲外を変更していないか」を必ず確認する。
6. 空きスロットがあれば、本線の影響範囲外タスクを `scripts/sdlc tasks next --main` で継続してよい。

## 結果報告フォーマット（全エージェント共通）

```
## 結果報告 <タスクID>
- 状態: 完了 | 失敗 | 要確認
- 変更ファイル: <パス一覧>
- 作成・更新した ID: <ID 一覧>
- 自己検証: <完了条件ごとに 合格/不合格 と根拠>
- テストの変更: なし | <削除・期待値変更の内容と理由>
- 懸念・質問: <あれば>
```
