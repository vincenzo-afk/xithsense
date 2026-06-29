# Contributing to XithSense

Thank you for considering contributing. This guide covers everything you need to get started.

---

## Code of Conduct

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## How to Contribute

### Reporting Bugs

Open a [GitHub Issue](https://github.com/your-org/xithsense/issues) with:

- A clear title describing the bug
- Steps to reproduce
- Expected vs actual behaviour
- Environment details (OS, Python version, branch)
- Relevant logs or screenshots

### Requesting Features

Open a GitHub Discussion under **Ideas** before building. Include:

- The problem you are solving
- Proposed solution
- Alternatives you considered
- Impact on existing functionality

### Pull Requests

1. Fork the repository and create a branch off `main`:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. Follow the [Coding Standards](docs/CODING_STANDARDS.md).

3. Write tests for every change:
   - New features: unit + integration tests
   - Bug fixes: regression test that fails before your fix

4. Run the full test suite:
   ```bash
   make test
   ```

5. Run linting:
   ```bash
   make lint
   ```

6. Update documentation if your change affects behaviour, configuration, or APIs.

7. Push and open a PR targeting `main`. Fill in the PR template completely.

---

## Development Setup

See [docs/DEV_SETUP.md](docs/DEV_SETUP.md) for full local environment instructions.

Quick start:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
cp .env.example .env   # fill in your credentials
```

---

## Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feat/<name>` | `feat/captain-engine-v2` |
| Bug fix | `fix/<issue>` | `fix/wide-ball-parsing` |
| Docs | `docs/<topic>` | `docs/feature-engineering` |
| Refactor | `refactor/<area>` | `refactor/optimizer-deap` |
| Test | `test/<scope>` | `test/backtest-accuracy` |
| Hotfix | `hotfix/<name>` | `hotfix/null-venue-crash` |

---

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

Examples:
```
feat(optimizer): add genetic algorithm fallback for large credit spaces
fix(ingestion): handle missing player_of_match field in Cricsheet v1.2.0
docs(api): add WebSocket event payload spec
test(human-rules): add confidence boundary tests
```

---

## Code Review Standards

All PRs require:
- At least **1 approving review** from a maintainer
- All CI checks passing (lint, tests, coverage threshold)
- No reduction in test coverage below module targets
- Documentation updated if public API or behaviour changed

Reviewers will check:
- Correctness of logic (especially ML features and optimizer constraints)
- Test coverage and quality
- Adherence to coding standards
- Backward compatibility
- Performance implications

---

## Adding Human Intelligence Rules

Rules live in `human_rules/`. When adding or modifying rules:

1. Follow the schema in `human_rules/RULE_SCHEMA.json`
2. Include a `source` field referencing the expert analysis or match data that justifies the rule
3. Set a realistic `confidence` between 0.5 and 1.0
4. Add the rule to the appropriate file: `PLAYER_RULES.json`, `VENUE_RULES.json`, `MATCHUP_RULES.json`, or `CONTEXT_RULES.json`
5. Run `python human_rules/validate_rules.py` before committing
6. Document the rule in `human_rules/RULE_SOURCES.md`

---

## Adding ML Features

Features live in `feature_engineering/`. When adding features:

1. Document the feature formula in `docs/FEATURE_ENGINEERING_SPEC.md`
2. Add the feature name and type to `models/FEATURE_LIST.yaml`
3. Write a unit test verifying the feature computation on known data
4. Run backtesting after any feature change: `make backtest`
5. Log the experiment in `evaluation/EXPERIMENT_TRACKING.md`

---

## Release Process

Releases are managed by maintainers:

1. Update `CHANGELOG.md` under `[Unreleased]`
2. Bump version in `pyproject.toml`
3. Create a PR titled `release: vX.Y.Z`
4. After merge, tag the commit: `git tag vX.Y.Z && git push --tags`
5. CI publishes the Docker image automatically

---

## Questions

Use [GitHub Discussions](https://github.com/your-org/xithsense/discussions) for questions.  
For security issues, email security@xithsense.com — do not open a public issue.
