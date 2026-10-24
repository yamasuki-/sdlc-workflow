# 保留中の変更: software_dev_workflow からの補完

`supplement.patch` は、`yamasuki-/software_dev_workflow` を参照して sdlc-workflow に足りない機能を補う変更一式です
（56 ファイル。内容は適用後の `spec/adoption-report.md`「software_dev_workflow からの補完」を参照）。

ワークフロー本体の保護ファイル（`.claude/hooks/`・`scripts/approve`・`scripts/sdlc_lib/`）を含むため、
**保護が外れたメンテナンスモード（`SDLC_MAINTENANCE=1`）のセッションでのみ適用できます**。
作成したセッションでは環境変数が有効にならなかったため、作業コピー上で実装・自己テスト（36 件、5 回連続成功）まで行い、
適用を保留しています。

## 適用手順

1. 人が環境の設定で環境変数 `SDLC_MAINTENANCE=1` を追加し、ブランチ `claude/dazzling-fermi-4yjwi2` で新しいセッションを開始する
   （ローカルなら `SDLC_MAINTENANCE=1 claude`）。
2. そのセッションで次を実行する:
   ```bash
   git apply spec/pending/supplement.patch
   python3 -m unittest discover -s scripts/tests   # 36 件成功すること
   git rm -r spec/pending
   git add -A && git commit -m "software_dev_workflow を参照して不足機能を補完"
   ```
3. 適用後は環境変数 `SDLC_MAINTENANCE` を外す（通常運用ではワークフロー本体を保護する）。

## 主な内容

- 品質ゲート: セキュリティレビュー（security-reviewer）、機械チェックゲート（`scripts/sdlc check`、MUST/SHOULD/MAY）、
  Red/Green の証跡（`scripts/sdlc test-run`）、テンプレート充実（詳細設計・UI/DB 設計・NFR カテゴリ）
- 不具合・変更: 原因調査の規律強化（エビデンス必須・一時計装の原状復帰・トリアージ）、対応方法の提案（solution-proposer、
  人がゲートで案を選定）、変更要求フロー `/change`（current-analyst、CR-xxx）
- 運用: 決定事項・未解決事項ログ（`scripts/sdlc decision|question`）、プロジェクト固有ルール（`rules/`）
- 本体の修正: Bash ガードの `scripts/approve` 誤検知、`.claude/settings.local.json` とリポジトリ外の設定ファイルの保護漏れ
