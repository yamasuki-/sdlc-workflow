---
name: phase-basic-design
description: 工程3「基本設計」。システム要件からアーキテクチャ・モジュール分割（BD）・インタフェース（IF）を設計し、TDD の先行作成として結合テスト仕様（IT）を test-writer が作成する。
---

# 工程 3: 基本設計（03-basic-design）

まず `.claude/sdlc/phase-flow.md`（共通フロー）を読み、その型に従って進める。以下は本工程固有の内容のみ。

## 入力 / 成果物
- 入力: `docs/02-system-requirements/`（SR・NFR・AT）、`project.yaml`（言語・FW）
- 成果物（`docs/03-basic-design/`）:
  - `architecture.md` … 全体構成・技術方針・NFR への手当て（テンプレート `basic-design.md`）
  - `modules.md`（または `bd-<領域>.md`）… `### BD-xxx` モジュール（責務・依存・`src_dir` 内の配置）
  - `interfaces.md` … `### IF-xxx`（テンプレート `interface.md`）
  - `it-<領域>.md` … `### IT-xxx` 結合テスト仕様（テンプレート `integration-test-spec.md`）
  - `plan.md` / `summary.md` / `review.md`

## タスク分解
1. architecture.md とモジュール一覧の骨格（agent: **designer**）— 他の全タスクの前提。
2. 領域ごとの BD 詳細化・IF 定義（designer、担当ファイルを分ける）。IF は提供側・利用側の両方が
   決まってから定義するため、関連モジュールの BD タスクに依存させる。
3. IT 作成（agent: **test-writer**、依存: 対応する IF タスク）。

## 作業内容
- モジュールは後工程で**並行実装できる粒度**に分ける（担当ファイルが重ならない配置にする）。
- IF にはシグネチャ・データ形式・エラーを型レベルで書く。
- IT は IF の正常系とエラー伝播を検証する。

## 統合
- `scripts/sdlc trace check`（SR→BD/IF、IF→IT）。依存関係が循環していないことを確認する。
