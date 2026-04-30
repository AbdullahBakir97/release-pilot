# Release Pilot — System Design

## 1. Overview

**Release Pilot** is a GitHub App that automatically drafts professional GitHub Releases from your conventional commits whenever a release-worthy event occurs (tag push, manual trigger, or merge to main with `release:` prefix).

It is the natural completion of the contribution-quality ecosystem:

```
Commit Craft → PR Coach → Release Pilot
(clean commits) (good PRs)  (great releases)
```

## 2. Trigger Events

| Trigger | When | Action |
|---------|------|--------|
| **Tag push** (`v*.*.*` or `release/*`) | Maintainer pushes a semantic version tag | Draft a release with notes for all commits since the previous tag |
| **Manual workflow_dispatch** | Maintainer clicks "Run workflow" | Same flow with explicit `from`/`to` refs |
| **Push to main with `release:` body** | Squash merge of a release-prep PR | Same flow |
| **Pull request `release:next` label** | Maintainer wants a preview | Posts a comment with the draft notes (read-only preview) |

## 3. Generated Release Notes Format

```markdown
## What's Changed

### ✨ Features
- feat(auth): add OAuth2 login support (#42, abc1234)
- feat(api): introduce /v2/search endpoint (#48, def5678)

### 🐛 Bug Fixes
- fix(parser): handle empty input gracefully (#43, ghi9012)

### 📚 Documentation
- docs(readme): clarify installation steps (#45, jkl3456)

### ♻️ Refactoring
- refactor(core): simplify token caching (#46, mno7890)

### ⚙️ CI / Build
- ci: speed up matrix builds with caching (#47, pqr1234)

### 📦 Dependencies
- chore(deps): bump fastapi from 0.115 to 0.118 (#49, dependabot)

### 💥 Breaking Changes
- feat(auth)!: drop support for legacy basic auth — see migration guide

---

**Contributors:** @user1 @user2 @dependabot

**Full Changelog:** v1.2.0...v1.3.0
```

## 4. Architecture Layers

```
src/
├── domain/                   Pure business logic
│   ├── entities.py          ReleaseDraft, ChangeGroup, CommitDelta, ReleaseSpec
│   ├── enums.py             ChangeType, ReleaseStrategy, BumpKind
│   ├── interfaces.py        IGitHubClient, ITagComparer, INotesGenerator
│   └── exceptions.py
├── analyzers/
│   ├── commit_classifier.py Classifies commits by conventional type
│   ├── version_resolver.py  Determines previous tag, next version
│   └── delta_calculator.py  Computes commit + PR delta between two refs
├── generators/
│   ├── notes_generator.py   Builds the markdown release notes
│   ├── grouping_strategy.py Groups commits by type with emoji headers
│   └── contributor_lister.py Deduplicates contributors with @mentions
├── infrastructure/
│   ├── github/              Auth, client (releases API, compare API)
│   └── config/              Per-repo .github/release-pilot.yml
├── application/
│   ├── orchestrator.py      Coordinates the whole flow
│   └── webhook_handler.py   Routes push/PR events
└── api/                     FastAPI app, /webhook, /preview, /health
```

## 5. Per-Repo Config (`.github/release-pilot.yml`)

```yaml
enabled: true

# How releases are triggered
triggers:
  on_tag: true              # Listen for tag pushes
  on_main: false            # Listen for release: commits on main
  on_pr_label: "release:next"  # Preview when this label is added

# Release strategy
release:
  draft: true               # Always draft, never auto-publish
  prerelease_pattern: ".*-(?:alpha|beta|rc)\\.\\d+$"
  generate_release_name: true
  include_full_changelog_link: true

# How sections are grouped/labeled
sections:
  - title: "✨ Features"
    types: [feat]
    sort: "by_pr_number"
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

# Filtering
exclude:
  authors: []                    # Skip commits from these authors
  bots: false                    # Include dependabot etc by default
  matching: "^Merge branch"      # Skip merge commits
  drafts: true                   # Skip draft PRs

# Breaking changes
breaking_changes:
  separate_section: true
  title: "💥 BREAKING CHANGES"
  detect_via:
    - "!"                        # feat!: ... or feat(scope)!: ...
    - "BREAKING CHANGE"          # body footer
    - "BREAKING-CHANGE"

# Contributors
contributors:
  enabled: true
  exclude_bots: false
  format: "**Contributors:** {mentions}"
```

## 6. Trigger Flow

```
Tag pushed (v1.3.0)
   │
   ▼
[Webhook arrives]
   │
   ▼
[Resolve previous tag] ── git/tags compared with semver sort
   │
   ▼
[List commits between v1.2.0 → v1.3.0] ── compare API
   │
   ▼
[For each commit:]
  - Parse conventional type (feat/fix/docs/...)
  - Find associated PR (search by SHA)
  - Detect breaking change marker
   │
   ▼
[Group commits into sections] ── per .github/release-pilot.yml
   │
   ▼
[Generate markdown] ── header + sections + contributors + changelog link
   │
   ▼
[Create draft release] ── POST /repos/.../releases (draft=true)
   │
   ▼
[Maintainer reviews] ── publishes manually
```

## 7. Why This Completes the Ecosystem

| Bot | Stage | Output |
|-----|-------|--------|
| Issue Triage Bot | **Issue intake** | Categorized + prioritized issues |
| AI Quality Gate | **Contribution quality** | Score + feedback on issues/PRs |
| Commit Craft | **Per-commit quality** | Conventional commits enforced |
| PR Coach | **PR quality** | Score + coaching for PRs |
| RepoDoc AI | **README maintenance** | Auto-updated README on push |
| **Release Pilot** | **Release output** | Draft GitHub Releases from clean commits |

Each bot serves one stage of the contribution lifecycle. Release Pilot is the final output stage — it converts everything the other bots have refined into a publishable artifact.
