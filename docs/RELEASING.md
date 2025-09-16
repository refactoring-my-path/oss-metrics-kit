## Releasing to PyPI

This document describes how maintainers cut a new release and publish it to PyPI (or TestPyPI).

### Prerequisites

- PyPI account with permissions for the project
- Prefer Trusted Publishing (OIDC) via GitHub Actions. If not available, create an API token (Upload scope).

### Versioning and tagging

1) Bump the version in `pyproject.toml` (SemVer)
2) Commit and tag the release:

```
git commit -am "release: vX.Y.Z"
git tag vX.Y.Z
git push --tags
```

### CI-based publish (recommended)

The workflow `.github/workflows/publish.yml` runs on GitHub Release published:

- Builds sdist + wheel
- Validates with `twine check`
- Publishes
  - Pre-release → TestPyPI
  - Regular release → PyPI

Notes:
- For Trusted Publishing, register this repository and `publish.yml` in the PyPI project settings.
- If using tokens instead, set `PYPI_API_TOKEN`/`TEST_PYPI_API_TOKEN` secrets and uncomment the password lines in the workflow.

### GitHub Release UI (what to enter)

- Release title: `vX.Y.Z` (match the tag). Optionally add a short name, e.g., `v1.2.0 – Scoring tweaks`.
- Release notes: include at least these sections:
  - Highlights: 2–5 bullets of what matters.
  - Changes: user‑visible changes, new commands/options.
  - Breaking changes: what to do to upgrade.
  - Installation: reminder (pip install / extras if changed).
  - Thanks: contributors (optional).

Template:

```
## Highlights
- ...

## Changes
- ...

## Breaking changes
- ...

## Installation
pip install -U oss-metrics-kit

## Thanks
@user1 @user2
```

- Pre‑release checkbox:
  - Check it for rc/beta/preview builds you don’t want on production PyPI (workflow will publish to TestPyPI).
  - Leave it unchecked for stable releases (workflow will publish to PyPI).

### Manual publish (alternative)

#### Using uv

```
uv build   # produces sdist(.tar.gz) + wheel(.whl) into dist/

# TestPyPI (recommended first)
export PYPI_TOKEN_TEST=...
uv publish --repository testpypi --token "$PYPI_TOKEN_TEST"

# PyPI
export PYPI_TOKEN=...
uv publish --token "$PYPI_TOKEN"
```

#### Using build + twine

```
python -m pip install --upgrade build twine
python -m build           # sdist + wheel to dist/
python -m twine check dist/*

# TestPyPI
twine upload --repository testpypi -u __token__ -p "$PYPI_TOKEN_TEST" dist/*
# PyPI
twine upload -u __token__ -p "$PYPI_TOKEN" dist/*
```

### Notes

- Versions are immutable on PyPI; bump SemVer for every release
- `pyproject.toml` metadata (URLs/license/description) appears on the project page
- Ship both sdist and wheel to maximize install success across environments
- Validate on TestPyPI first, then promote to PyPI

### Verification

- Check the workflow run includes the “Publish to TestPyPI/PyPI” step
- Confirm the new version appears on PyPI/TestPyPI
- Install test:

```
# TestPyPI
python -m pip install -i https://test.pypi.org/simple/ oss-metrics-kit==X.Y.Z
# PyPI
python -m pip install oss-metrics-kit==X.Y.Z
```
