# Versioning Strategy

## API Versioning

**Current version:** v1  
**URL scheme:** `/api/v1/endpoint`  
**Strategy:** URI versioning (path-based)

### Rules

| Rule | Detail |
|------|--------|
| Breaking changes require a new version | `/api/v2/` |
| Non-breaking additions are backward compatible | New field in v1 response |
| Deprecated endpoints serve v1 with `Deprecation` header | `Deprecation: true; sunset=2027-01-01` |
| Old version supported for ≥ 6 months after v2 launch | Migration period |

### What Constitutes a Breaking Change

- Removing or renaming a response field
- Changing a field's data type
- Removing an endpoint
- Changing required request fields
- Changing HTTP status codes for existing scenarios

### What is NOT a Breaking Change

- Adding new optional response fields
- Adding new optional request fields
- Adding new endpoints
- Adding new enum values (if clients use `ignore_unknown`)

---

## Application Versioning

**Scheme:** [Semantic Versioning 2.0](https://semver.org/) — `MAJOR.MINOR.PATCH`

| Part | Increment When |
|------|----------------|
| MAJOR | Breaking API change, major architecture redesign |
| MINOR | New feature, new endpoint, model upgrade |
| PATCH | Bug fix, performance improvement, dependency update |

**Current version:** `0.5.0`  
**Version location:** `pyproject.toml` → `version = "0.5.0"`

### Release Tagging

```bash
# Tag and push release
git tag v0.5.0
git push origin v0.5.0

# CI picks up tag and deploys to production
```

---

## Model Versioning

See `docs/MODEL_VERSIONING_POLICY.md` for full details.

**Scheme:** `{model_id}-{format}-{YYYYMMDD}`  
**Example:** `m01-t20-20260601`

---

## Database Schema Versioning

Managed by Alembic. Each migration has a sequential ID (`0001`, `0002`...).

```bash
alembic current          # Current revision
alembic history          # All revisions
alembic upgrade head     # Apply all
alembic downgrade -1     # Roll back one
```

---

## Feature List Versioning

`models/FEATURE_LIST.yaml` has a `version` field.  
Models store the feature list version they were trained on.  
Mismatch between active model's feature version and current feature list = deployment blocked.

```yaml
version: "v1.2"    # Increment when features added/removed/renamed
```

---

## Human Rules Versioning

Rules are versioned implicitly via Git history.  
Each rule JSON change is a commit.  
Rule IDs (`RULE-XXXX`) are permanent — never reuse a deleted rule ID.

---

## Changelog Maintenance

Every release updates `CHANGELOG.md` under `## [Unreleased]`:
1. Move `[Unreleased]` entries under the new version heading
2. Update version in `pyproject.toml`
3. Create git tag
4. CI deploys
