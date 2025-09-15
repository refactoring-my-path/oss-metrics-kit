# oss-metrics-kit

OSSの貢献データを「収集 → 正規化 → 指標算出 → 出力」まで一気通貫で扱うための基盤ライブラリ（MVP）。

現状: スタブ実装（CLI/エントリポイント/型モデルのみ）。ここから段階的に機能を追加します。

## インストール（開発モード）

以下はいずれかを実行してください。Conda/venv など任意の仮想環境上で実行を推奨します。

- `pip install -e .` もしくは
- `python -m pip install -e .`

インストール後、以下でCLIのヘルプを確認できます。

- `ossmk --help`

注意: インストールせずに `ossmk` は使えません。開発中に直接実行したい場合は `pip install -e .` を行うか、`PYTHONPATH=src` を設定しつつエントリポイント経由で呼び出してください。

## 開発環境（uv推奨）

超高速パッケージマネージャー「uv」を利用すると、依存解決・仮想環境の同期が簡単になります。

1) uvのインストール（どれか一つ）
- macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Homebrew: `brew install uv`
- pipx: `pipx install uv`

2) 仮想環境の作成と同期
- `uv venv .venv`（任意）→ `source .venv/bin/activate`
- 依存同期（本体＋開発用）: `uv sync --dev`
- すべてのエクストラも入れる場合: `uv sync --dev --extra all`

3) 実行
- `ossmk --help`（アクティベート済みの場合）
- もしくは環境を活性化せずに: `uv run ossmk --help`

## 使い方（MVPスタブ）

- バージョン表示: `ossmk version`
- フェッチ（スタブ）: `ossmk fetch --provider github --repo owner/name`
- スコア（スタブ）: `ossmk score --input - --rules default`

## 設計ハイライト

- `src/` レイアウト＋ `py.typed` による型配布。
- CLIはTyperで薄く、ビジネスロジックは `ossmk.core` に集約。
- providers/exporters/storage/rules はエントリポイントでプラガブル。

## トラブルシューティング

- `pip._vendor.tomli.TOMLDecodeError: Invalid initial character for a key part (at line 1, column 2)`
  - 原因: `pyproject.toml` の先頭セクションが不正（`[build-system]` の直前に余計な文字がある）
  - 対処: 先頭行を `[build-system]` に修正済み。リトライ前にキャッシュを避けるため `pip install -e .` を再実行してください。

- `ossmk: command not found`
  - 原因: パッケージ未インストール、または別環境でインストール。
  - 対処: リポジトリ直下で `pip install -e .` を実行。Conda/venv を使用している場合は、同じ環境を `activate` 済みか確認。
  - uv利用時: `uv sync --dev` 後に `source .venv/bin/activate`、または `uv run ossmk --help` を使用。

## ライセンス

Apache-2.0
