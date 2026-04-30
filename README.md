# Release Pilot

[![CI](https://github.com/AbdullahBakir97/release-pilot/actions/workflows/ci.yml/badge.svg)](https://github.com/AbdullahBakir97/release-pilot/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A GitHub App that drafts professional GitHub Releases from your conventional commits the moment you push a tag.

## The Problem

Writing release notes by hand is tedious. Maintainers either skip them entirely, dump the raw `git log`, or spend twenty minutes shaping the same kind of changelog they wrote last week. Across a project's lifetime that's hours lost, and the result is still inconsistent: every release looks slightly different and small fixes get buried next to breaking changes.

## The Solution

Release Pilot turns the conventional commits you already write into beautiful, sectioned release notes -- automatically. Push a tag, and a draft release appears on GitHub with features, fixes, docs, dependencies, breaking changes, and contributors all neatly grouped, linked to their PRs, and ready to publish.

## Where It Fits

```
Commit Craft  →  PR Coach  →  Release Pilot
clean commits   good PRs     great releases
```

Release Pilot is the final stage of the contribution-quality ecosystem. Commit Craft enforces conventional commits, PR Coach coaches contributors on PR quality, and Release Pilot turns all that polished work into a publishable artifact.

## Features

- **Conventional commit aware** -- parses `type(scope)!: subject` and `BREAKING CHANGE:` footers
- **Smart grouping** -- features, fixes, docs, refactors, tests, CI, dependencies, chores
- **Breaking-change callouts** -- separate, prominent section for `!` and `BREAKING CHANGE:` commits
- **Contributor mentions** -- deduplicated `@user` list, optional bot exclusion
- **PR linking** -- resolves the PR for each commit and links it inline
- **Full Changelog link** -- automatic `previous...current` compare URL
- **Per-repo config** -- `.github/release-pilot.yml` to customise sections, filters, triggers
- **Drafts only by default** -- you review and publish; nothing ships unattended

## Trigger Types

| Trigger | When | Action |
|---------|------|--------|
| **Tag push** (`v*.*.*`) | A semantic version tag is pushed | Draft a release with notes for everything since the previous tag |
| **Manual `workflow_dispatch`** | A maintainer clicks "Run workflow" | Same flow with explicit `tag` / `base` inputs |
| **PR label `release:next`** | A maintainer labels a PR | Posts a preview comment on the PR with the would-be notes |

## Per-Repo Configuration

Add `.github/release-pilot.yml` to your repository:

```yaml
enabled: true

triggers:
  on_tag: true
  on_main: false
  on_pr_label: "release:next"

release:
  draft: true
  prerelease_pattern: ".*-(?:alpha|beta|rc)\\.\\d+$"
  generate_release_name: true
  include_full_changelog_link: true

sections:
  - title: "✨ Features"
    types: [feat]
  - title: "🐛 Bug Fixes"
    types: [fix]
  - title: "📚 Documentation"
    types: [docs]
  - title: "♻️ Refactoring"
    types: [refactor, perf]
  - title: "🧪 Tests"
    types: [test]
  - title: "⚙️ CI / Build"
    types: [ci, build]
  - title: "📦 Dependencies"
    types: [chore]
    only_if_scope_matches: "deps|deps-dev"
  - title: "🔧 Chores"
    types: [chore]
    excluding_scope: "deps|deps-dev"

exclude:
  authors: []
  bots: false
  matching: "^Merge branch"
  drafts: true

breaking_changes:
  separate_section: true
  title: "💥 BREAKING CHANGES"

contributors:
  enabled: true
  exclude_bots: false
  format: "**Contributors:** {mentions}"
```

## Quick Start

1. **Install the GitHub App** from the marketplace and grant it access to your repo.
2. **Push a tag** that matches the default pattern (`v?MAJOR.MINOR.PATCH`):
   ```bash
   git tag v1.3.0
   git push origin v1.3.0
   ```
3. **Open the Releases tab.** Your draft is already there, sectioned and ready to publish.

That's it. No workflow files, no scripts.

## Tech Stack

- **Python 3.12+** with full type hints
- **FastAPI** for the webhook server
- **Pydantic v2** for settings and per-repo config validation
- **httpx** async client for the GitHub REST API
- **PyJWT** for GitHub App authentication
- **packaging** for semver-aware tag ordering
- **Clean Architecture** -- domain, analyzers, generators, application, infrastructure, api

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the server locally
python -m src.main

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Run tests
pytest
```

## License

MIT -- see [LICENSE](./LICENSE).
