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

## PyPIインストール（利用者向け）

- 安定版のインストール: `pip install oss-metrics-kit`
- Postgres連携込み: `pip install "oss-metrics-kit[exporters-postgres]"`

インストール後に `ossmk --help` が動作すればOKです。

## あなたのGitHubアカウントで試す

前提: GitHubトークンを環境に設定します（read-only 権限で十分）。

```bash
export GITHUB_TOKEN=ghp_xxx   # or GH_TOKEN
```

分析（サマリ＋スコア出力）

```bash
ossmk analyze-user <your_github_login> --out -
```

スコアをPostgresに保存（任意）

```bash
export OSSMK_PG_DSN="postgresql://user:pass@host:5432/db"
ossmk analyze-user <your_github_login> --save-pg
```

プロプライエタリな重み付け（任意）

```bash
export BOOSTBIT_RULES_FILE=/absolute/path/to/private/boostbit_rules.toml
ossmk analyze-user <your_github_login> --out -
```

## 使い方（概要）

- バージョン表示: `ossmk version`
- データ取得: `ossmk fetch --provider github --repo owner/name`
- スコア算出: `ossmk score --input input.json --rules default`

詳細な実装進捗・エラーメモは `DEVLOG.md`（ローカル専用、.gitignore対象）を参照してください。

## PyPI公開手順（メンテナ向け）

準備

- PyPIアカウント作成 → API Token発行（スコープ: Upload）。
- ローカルでビルド&公開に使うツールを準備。

uvを使う場合（推奨）

```bash
# ビルド
uv build

# TestPyPIに公開（推奨）
export PYPI_TOKEN_TEST=...  # pypi- で始まるトークン
uv publish --repository testpypi --token "$PYPI_TOKEN_TEST"

# 本番PyPIに公開
export PYPI_TOKEN=...
uv publish --token "$PYPI_TOKEN"
```

twineを使う場合（代替）

```bash
python -m pip install build twine
python -m build

# TestPyPI
twine upload --repository testpypi -u __token__ -p "$PYPI_TOKEN_TEST" dist/*

# PyPI
twine upload -u __token__ -p "$PYPI_TOKEN" dist/*
```

注意点

- バージョンはSemVerで更新し、同じ版の再アップロードは不可です。
- `pyproject.toml` のメタデータ（URL/ライセンス/説明）が公開ページに反映されます。

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
