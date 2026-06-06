# Branch protection — openclaw-embeddings-service

This document describes the branch protection rules that should be applied to
`main` (and any release branches) for `openclaw-embeddings-service/`.

Sub-PR 2 of the variant 3-PR sequence (RALPLAN §4.3 Wave 2.PY.C, F3) wires
this up. The rules below mirror the `make ci` local gate.

## Required status checks

The `Tests + coverage ratchet` workflow job in `.github/workflows/ci.yml`
must pass for both Python 3.11 and 3.12 before any PR can be merged.

Specifically:

- `Tests + coverage ratchet (3.11)` — must pass
- `Tests + coverage ratchet (3.12)` — must pass
- `Docker healthcheck` — must pass

## Settings to apply via GitHub UI (or `gh api`)

| Setting | Value |
| --- | --- |
| Require a pull request before merging | ✅ |
| Require approvals | 1 (r3dlex) |
| Dismiss stale pull request approvals when new commits are pushed | ✅ |
| Require review from Code Owners | ✅ (CODEOWNERS file) |
| Require status checks to pass before merging | ✅ |
| Require branches to be up to date before merging | ✅ |
| Require linear history | ✅ |
| Include administrators | ✅ (enforced) |
| Restrict who can push to matching branches | nobody (PR-only) |

## How to apply

```bash
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/r3dlex/openclaw-multi-agent-workspace/branches/main/protection \
  -F required_status_checks[strict]=true \
  -F required_status_checks[contexts][]=Tests + coverage ratchet (3.11) \
  -F required_status_checks[contexts][]=Tests + coverage ratchet (3.12) \
  -F required_status_checks[contexts][]=Docker healthcheck \
  -F enforce_admins=true \
  -F required_pull_request_reviews[dismiss_stale_reviews]=true \
  -F required_pull_request_reviews[require_code_owner_reviews]=true \
  -F required_pull_request_reviews[required_approving_review_count]=1 \
  -F restrictions=null \
  -F required_linear_history=true
```

(Apply with the PAT or admin token; this is a documentation-only change in
this PR — the rule itself is applied in the repo settings as part of the
sub-PR 2 rollout.)

## Sub-PR 3 will tighten this

Sub-PR 3 turns on the 90% coverage gate (`--cov-fail-under=90`) and adds
the `Coverage gate (90%)` check to the required list. Until then, the
`.coverage_baseline` ratchet file is the only coverage floor.

## Sub-PR 3 status (applied in this repo)

Sub-PR 3 turned on the 90% hard gate via `pyproject.toml`:
`addopts = "--cov=. --cov-report=term-missing --cov-fail-under=90"`.
The `.coverage_baseline` ratchet is now at 99% — coverage must be
≥ 90% (gate) AND ≥ 99% (ratchet).
