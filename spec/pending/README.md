# 保留中の変更

`sdlc-update.patch` は次の 2 つをまとめた変更一式です（97 ファイル）。

1. **software_dev_workflow からの補完**（セキュリティレビュー、機械チェックゲート、Red/Green の証跡、テンプレート充実、
   原因調査の規律強化、対応方法の提案、`/change`、決定事項・未解決事項ログ、`rules/`）
2. **配置の見直し**: 本体を `~/.claude/` に置くことを基本とし、プロジェクトの `.claude/` で上書きでき、
   プロジェクトの `.claude/` だけでも使えるようにする（`install.py`、`USAGE.md`）

ワークフロー本体の保護ファイル（hooks・ゲート判定ロジック・approve・settings.json）を含むため、
**保護が外れたメンテナンスモード（`SDLC_MAINTENANCE=1`）のセッションでのみ適用できます**。
作成したセッションでは環境変数が有効でなかったため、リポジトリ外の作業コピーで実装し、
適用後の状態で自己テスト（45 件）を 5 回連続で成功させたうえで、適用を保留しています。

内容の詳細は、適用後の `spec/adoption-report.md`（末尾の 2 節）・`README.md`・`USAGE.md` を参照してください。

## 適用手順

1. 人が環境の設定で環境変数 `SDLC_MAINTENANCE=1` を追加し、ブランチ `claude/dazzling-fermi-4yjwi2` で
   新しいセッションを開始する（ローカルなら `SDLC_MAINTENANCE=1 claude`）。
2. そのセッションで次を **1 回の Bash 呼び出しとして**実行する（パッチ適用 → 自己テスト → `spec/pending` の削除 → コミット）:
   ```bash
   bash spec/pending/apply.sh
   ```
   適用で hooks の場所が変わるため、続けて他の操作をせず、**セッションを開始し直す**。
3. 新しいセッションで `git push` し、`python3 -m unittest discover -s tests` が通ることを確認する。
4. 作業が終わったら環境変数 `SDLC_MAINTENANCE` を外す。
