# Commit messages: Conventional Commits 1.0.0

Every commit in this repo follows [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/).
Humans and AI agents alike. Messages are in **English**.

## Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

- **type** (lowercase, required), then an optional **scope** in parentheses, an optional `!`, then `: ` and the description.
- **description**: imperative, lowercase start, no final period, about 72 characters max. Says *what* changes.
- **body** (optional, one blank line after the description): *why* the change was needed. Wrap at ~72 characters.
- **footers** (optional, one blank line after the body): `Token: value`, tokens use `-` instead of spaces
  (`Co-Authored-By`, `Refs`, `Reviewed-by`). Breaking changes: `BREAKING CHANGE: <description>` in a footer, or `!` before the `:`.

## Types we use

| Type | When | SemVer |
|---|---|---|
| `feat` | A new feature for the user | MINOR |
| `fix` | A bug fix | PATCH |
| `docs` | Documentation only | — |
| `style` | Formatting, no code meaning change (not CSS design work: that is `feat` or `fix`) | — |
| `refactor` | Code change that neither fixes a bug nor adds a feature | — |
| `perf` | Faster or lighter | — |
| `test` | Adding or fixing tests | — |
| `build` | Dependencies, Vite config, `setup.sh` | — |
| `ci` | CI / deploy configuration | — |
| `chore` | Repo housekeeping (`.gitignore`, moving files) | — |
| `data` | Downloading or regenerating datasets and data scripts' outputs (our addition) | — |
| `revert` | Reverts earlier commits; add `Refs: <sha>` | — |

## Scopes we use

`web`, `map`, `panel`, `rotations`, `years`, `sprout` (the cat), `design`, `data`, `pipeline`, `docs`, `deps`.

## Examples

```
feat(map): add GIBS IMERG and SMAP image layers

Both layers load straight from NASA GIBS with no key, so the map shows
real rain and soil moisture anywhere on Earth.
```

```
fix(panel): show "cooler" when the warming trend is negative
```

```
data(pipeline): build the Lambayeque 0.1° grid from IMERG, NASADEM and GRACE
```

```
feat(web)!: switch the map from Leaflet to MapLibre

BREAKING CHANGE: map overlays are now MapLibre sources; Leaflet layer code was removed.
```

## Rules of thumb

- One logical change per commit. If a change fits two types, split it into two commits.
- Never commit secrets (API keys, `.netrc`), `node_modules/`, `.venv/`, build output or raw NASA files in `data/manual/`.
- Before committing: `cd web && npx vite build` must pass.
