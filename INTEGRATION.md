# Integrating the Week 4 overlay into the existing repository

The delivered archive is an overlay because the live WSL checkout was not mounted in the coding
workspace. It contains no `.env`, credentials, `lib`, `out`, cache, or generated evidence.

From the existing `defiagent-x-lite` repository:

```bash
git status --short
git switch -c feat/week4-research-gate
```

Commit or stash any unrelated work before copying the overlay. Extract the archive into a temporary
directory first, inspect it, then copy it over the repository root:

```bash
mkdir -p /tmp/defiagent-week4-review
tar -xzf defiagent-x-lite-week4.tar.gz -C /tmp/defiagent-week4-review
rsync -av --exclude='.git' /tmp/defiagent-week4-review/defiagent-x-lite-week4/ ./
```

The files expected to replace existing scaffolding are `README.md`, `pyproject.toml`,
`foundry.toml`, `.gitignore`, `.python-version`, and `.github/workflows/test.yml`. The overlay does
not delete `Counter.sol` or its tests; remove those later in a separate reviewed commit if they are
no longer useful.

Preserve your existing `lib/forge-std` submodule. Then run:

```bash
chmod +x scripts/*.sh
./scripts/bootstrap.sh
git diff --check
git status --short
```

Review every diff before committing. In particular, confirm that `.env` is still ignored and that
no archive key, GitHub token, mnemonic outside the public Anvil fixture, or generated result was
staged:

```bash
git check-ignore -v .env
git diff --cached --name-only
git grep -nE 'ghp_|alchemy\.com|alch_' -- ':!INTEGRATION.md'
```

The last command should return no match. Rotate any previously exposed credential rather than
trying to remove only the visible message.

