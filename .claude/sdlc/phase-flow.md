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

- 入力: 前工程までの**承認済み**成果物（`docs/<前工程>/`）と前工程ゲートのコメント・条件、
  `state/decisions.md`（これまでの決定事項）、`state/open-questions.md`（未解決事項）、`rules/`（プロジェクト固有ルール）。
- `docs/<P>/plan.md` をテンプレート `<SDLC>/templates/plan.md` から作成する:
  作業範囲（対象 ID）、成果物ファイル構成、採番範囲、前工程の条件への対応、リスク・前提。
- 完了したら `scripts/sdlc phase step decompose`。

## 2. タスク分解（decompose）

- `state/tasks.yaml`（不具合対応モードでは `scripts/sdlc status` が示すタスクファイル）を
  テンプレート `<SDLC>/templates/tasks.yaml` に従って作成する。
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
   - 報告の「決定事項」「未解決事項」は、**オーケストレータが**記録する（サブエージェントは書かない。並行実行時の競合を防ぐ）:
     `scripts/sdlc decision add "<内容>" --source <タスクID>` /
     `scripts/sdlc question add "<内容>" --priority 高|中|低 --source <タスクID>`。
     優先度「高」（答えで成果物が大きく変わる）は、その場で人に確認する。それ以外はゲートでまとめて提示する。
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
既知の前提: <state/decisions.md の関連決定事項、ユーザの最近の指示など、ファイルに書かれていない補足>
プロジェクト固有ルール: rules/common.md, rules/<工程ID>.md（あれば従う）
作業内容: <工程スキルが定める作業>
テンプレート: <<SDLC>/templates/...>
完了条件: <工程スキルの自己検証項目>
禁止: state/ の変更、scripts/approve の実行、担当外ファイルの変更、承認済み成果物の変更
スコープ: 指示された範囲を指示された粒度で完遂する。依頼が誤っている・より良い方法があると考える場合は
1 文で指摘したうえで指示どおり進める（黙って範囲を狭めたり広げたりしない）。成果物は内容に見合った長さにし、
前段の再掲や定型の結語で水増ししない。
（worktree の場合）作業の最後に担当ファイルを git add してコミットすること。
最後に「結果報告フォーマット」で報告すること。
```

## 4. 統合（integrate）

- 全成果物の整合性を確認する:
  - `scripts/sdlc trace check`（現在工程までのルール）を通す。
  - ID の重複・欠番・用語の揺れ、ファイル間の矛盾を確認する。
  - コードを含む工程は `project.yaml` の `commands.test` / `lint` / `coverage` を実行する。
- 発見した不整合は修正タスクとして tasks.yaml に追加し、3 に戻って実行する。
- **機械チェックゲート**: `scripts/sdlc check` を実行する（`docs/<P>/checks.md` に記録される）。
  組み込みのトレーサビリティ検査と、`project.yaml` の `checks`（common と <P>）の MUST / SHOULD / MAY を実行する。
  - MUST が失敗（終了コード 4）→ 失敗内容を指示に含めた修正タスクを作り 3 に戻る。**MUST が通るまでレビューに進まない**。
    同じ MUST が 3 回続けて失敗したら、環境・設定の問題の可能性があるので人に報告して停止する。
  - 未インストールで skipped のチェックは失敗扱いにしない。「CI で実行が必要」と未解決事項に記録する。
- `docs/<P>/summary.md` に成果物一覧・統合チェック結果・機械チェック結果・テスト結果を記録する。
- `scripts/sdlc phase step review`。

## 5. レビュー（review）

- **reviewer エージェント 1 体**（並行させない）に依頼する。作成者とは別コンテキストであること。
  - 渡すもの: 工程 ID、成果物パス、`<SDLC>/checklists/<P>.md`、上流の承認済み成果物、
    前工程ゲートの条件、`docs/<P>/summary.md`、`docs/<P>/checks.md`（機械チェック結果）
  - 出力先: `docs/<P>/review.md`（テンプレート `<SDLC>/templates/review.md`）
- 指摘があれば、指摘ごとに**元の作成者と同じ種類のエージェント**で修正タスクを作り（reviewer には直させない）、
  実行後に再レビューする。最大 3 往復。残った指摘は `review.md` の「残指摘」に理由付きで残す。
- 既存テストの削除・期待値の変更があれば `review.md` に必ず明記させる。
- 工程スキルが追加のレビュー（例: 実装工程の security-reviewer）を定めている場合は、reviewer の後に**順に**実施する（並行させない）。
- 修正したら `scripts/sdlc check` を再実行してから再レビューする。
- `git add -A && git commit -m "<P>: レビュー完了"`。
- `scripts/sdlc phase step gate`。

## 6. 人間ゲート（gate）

人に次を提示して**停止する**（自分で承認しない・次工程に進まない）:

```
## 工程 <P> のゲート承認依頼
- 成果物: <docs/<P>/ 以下とコード等の一覧>（`scripts/sdlc gate artifacts <P>`）
- レビュー結果: docs/<P>/review.md（判定・残指摘の要約）。追加レビューがあればその判定も
- 機械チェック: docs/<P>/checks.md（MUST/SHOULD/MAY の結果、未インストールで未実行のもの）
- 今工程の決定事項: <state/decisions.md に今工程で追記したもの>
- 未解決事項: <state/open-questions.md の open。優先度 高を先に>
- 人に判断してほしい点: <前提・リスク・受容判断が必要な指摘>

承認・差戻しは端末で次を実行してください（承認時に機械チェックを再実行します。
MUST の失敗やレビュー判定「不合格」が残っていると差戻ししか記録できません）:
  scripts/approve <P>
承認後に /sdlc を実行すると次工程へ進みます。
```

---

## 差戻し対応（ゲートが「差戻し」の場合）

1. `state/gates/<P>.md` のコメント（修正指示）を Read で読む。
2. 指摘ごとに修正タスクを tasks.yaml に追加 → 3 実行 → 4 統合 → 5 レビュー（差戻し指摘が解消したかを観点に追加）→ 6 ゲート。

## 差分やり直し（不具合・変更要求の対応モードの場合）

`<ID>` は不具合票 `state/defects/DEF-xxx.md` または変更要求票 `state/changes/CR-xxx.md`。

1. 票の `impact_ids` / `impact_files` / 原因（変更内容）と、人がゲートで選んだ対応方法（`selected_option` と `proposal` の該当案）を読む。
   **選ばれた案の範囲で**やり直す（他の案の内容を混ぜない）。
2. 計画は `docs/<P>/plan.md` に「## <ID> 差分やり直し」節を追記する。**影響範囲の ID・ファイルだけ**を対象にし、全面やり直しにしない。
   変更要求で新しい項目を追加する場合は、既存 ID の続きで採番し、変更前→変更後の差分表を plan.md に書く。
3. タスクファイルは `scripts/sdlc status` が示すもの（`state/defects/<DEF>/` または `state/changes/<CR>/` の `tasks-<P>.yaml`）。
4. 不具合では、混入工程と対になるテスト仕様に、この不具合を検出するケースを追加する（例: 詳細設計起因 → UT を追加。
   実装起因なら回帰テストがその役割を担う）。変更要求では、変更後の振る舞いを検証するテストを V 字左側で先に変更・追加する。
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
- 決定事項: なし | <作業中に決めたこと（オーケストレータが state/decisions.md に記録する）>
- 未解決事項: なし | <人の確認が必要なこと。優先度 高/中/低 を付ける（オーケストレータが state/open-questions.md に記録する）>
- 懸念: <あれば>
```
