# BoostBit Quickstart (Copy-Paste Ready)

このドキュメントをCodexや自動化に読み込ませるだけで、BoostBitのバックエンドに `oss-metrics-kit` を組み込めます。手順はFastAPI/Express両対応の雛形を提示します。

## 0) 前提
- Python 3.11+（uv推奨）/ Node 18+
- GitHub OAuthアプリ（`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`）
- GitHub APIトークン（`GITHUB_TOKEN` or `GH_TOKEN`）
- PostgreSQL（`OSSMK_PG_DSN` or `DATABASE_URL`）
- （任意）Redis（`REDIS_URL`）

## 1) サーバ起動まで（FastAPI例）

```bash
uv venv .venv && source .venv/bin/activate
uv add "oss-metrics-kit[exporters-postgres]"
uv add fastapi uvicorn redis
export GITHUB_TOKEN=ghp_xxx
export OSSMK_PG_DSN=postgresql://user:pass@host:5432/db
export OSSMK_RULES_FILE=/abs/path/to/private/rules.toml  # 任意
export REDIS_URL=redis://localhost:6379/0               # 任意
```

`app.py`（最小実装）:
```python
from fastapi import FastAPI, Depends, HTTPException, Request
from ossmk.core.services.analyze import analyze_github_user
from ossmk.storage.postgres import connect, ensure_schema, save_scores
from ossmk.security.ratelimit_redis import RedisRateLimiter

app = FastAPI()
rl = RedisRateLimiter(url=os.getenv("REDIS_URL", "redis://localhost:6379/0"), capacity=60, window_seconds=60)

def limit(user_id: str, ip: str):
    key = rl.composite_key(user_id, ip)
    if not rl.try_acquire(key):
        raise HTTPException(429, "Too Many Requests")

@app.get("/oauth/github/callback")
async def callback(code: str, request: Request):
    # 1) GitHub OAuthトークン交換 → 2) /user を叩いて login を得る（INTEGRATION.md参照）
    login = "<resolved_login>"
    return {"login": login}

@app.post("/analyze")
async def analyze(user_id: str, login: str, since: str = "90d", rules: str = "auto", request: Request = None):
    limit(user_id, request.client.host if request and request.client else None)
    result = analyze_github_user(login, since=since, rules=rules, api="auto")
    with connect() as conn:
        ensure_schema(conn)
        scores = [dict(s, user_id=user_id) for s in result.scores]
        save_scores(conn, scores)
    return {"summary": result.summary, "scores": result.scores}
```

起動:
```bash
uvicorn app:app --reload
```

## 2) Express例（抜粋）

- OAuthコールバックと `/analyze` の雛形は `docs/INTEGRATION.md` を参照。
- Python側の `analyze_github_user` をHTTPで叩くか、Node実装で代替の分析レイヤを組む。

## 3) ルール/TOMLとLLM

- 私有ルールは `OSSMK_RULES_FILE` に設定（`rules=auto`で自動ロード）
- LLMで叩き台を作る場合:
```bash
ossmk fetch --provider github --repo owner/name --since 30d --out events.json
ossmk rules-llm --input events.json --provider openai --model gpt-4o-mini --out rules.toml
```

## 4) 防御の仕込み

- sinceクランプ: 既定180日（`OSSMK_MAX_SINCE_DAYS`）
- Bot除外: 既定オン（`OSSMK_EXCLUDE_BOTS=1`）
- 自己リポペナルティ: `OSSMK_SELF_REPO_PENALTY=0.8` などで調整
- レート制限: Redis Lua Token Bucketを推奨（`ossmk.security.ratelimit_redis.RedisRateLimiter`）

## 5) CI/CDと公開

- TestPyPI: `.github/workflows/publish-testpypi.yml`（OIDC）
- PyPI: `.github/workflows/publish.yml`（OIDC）、GitHub Releaseで自動公開

## 6) 追加TODO（Codex向けタスクリスト）

- [ ] OAuthコールバックの実装（FastAPI/Express）
- [ ] レート制限の環境別設定（容量・窓）
- [ ] 定期ジョブの実装（Crontab/Cloud Scheduler）
- [ ] UIへのスコア/サマリ表示（APIレスポンスの接続）
- [ ] ルールのA/Bテスト運用（TOML切替/動的ロード）
- [ ] 監視（ログ/メトリクス/Sentry）とアクセス監査

## 7) よくある質問

- Q: `<login>` は？
  - A: GitHubのユーザー名（プロフィールURLの末尾）。例: `octocat`, `torvalds`。
- Q: Parquetは必要？
  - A: 運用DBはPostgres/SQLiteで十分。横断分析やバッチ集計に使いたいときのみParquetを選択。
- Q: 料金/無料回数の制御は？
  - A: 本パッケージでは提供せず、BoostBit側で実装（本ドキュメントのRateLimit/Usage設計を参考に）。

