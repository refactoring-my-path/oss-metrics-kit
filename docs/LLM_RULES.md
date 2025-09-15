# LLM-Assisted Rules

This package can suggest scoring rules from observed events using an LLM provider.

## Providers and installation

- OpenAI: `pip install "oss-metrics-kit[llm-openai]"`
- Anthropic: `pip install "oss-metrics-kit[llm-anthropic]"`

## Environment

- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`

## CLI usage

Suggest a TOML rules file from events JSON:

```bash
ossmk fetch --provider github --repo owner/name --since 30d --out events.json
ossmk rules-llm --input events.json --provider openai --model gpt-4o-mini --out rules.toml
```

Apply the rules:

```bash
ossmk score --input events.json --rules rules.toml --out scores.json
```

## Notes

- The LLM only sees aggregated counts per event kind to minimize token usage and avoid leaking sensitive contents.
- Always review the suggested rules before applying in production.

