# Supply-Chain Pins

> Tracks the pinned digests of base Docker images that
> `openclaw-embeddings-service` builds against. The pin is to a
> content-addressable digest, not a floating tag, so the build is
> reproducible and immune to upstream image re-pushes or silent rebuilds.

## Current Pins

| Component | Version label | Digest | Source |
|---|---|---|---|
| `python:3.12-slim` | Python 3.12 (slim) | `sha256:090ba77e2958f6af52a5341f788b50b032dd4ca28377d2893dcf1ecbdfdfe203` | `docker pull python:3.12-slim` + `docker images --digests python:3.12-slim` |

> The version label is human-readable; the digest is the integrity guarantee.
> The digest in the `Dockerfile` and the value recorded here must always match.

## Where the Pins Live in the Code

| File | Line(s) | What it pins |
|---|---|---|
| `Dockerfile` | line 1 `FROM` | `python:3.12-slim` digest |

## Bump Procedure

For each pin: `docker pull` + `docker images --digests` to discover the new digest, update the `FROM` line in the `Dockerfile`, update the **Current Pins** table, add a row to the **History** table. PR title: `chore(supply-chain): bump <image>:<tag> digest`.

## Pre-Merge Checklist

- [ ] `docker build -t embeddings-service:pin-test .` succeeds locally.
- [ ] `spec/SUPPLY_CHAIN.md` is updated and committed in the **same** PR.

## Out of Scope (for this file)

- `openclaw-shared-base` SHA pin: not consumed by this repo's Dockerfiles (the
  embeddings service uses local-only Python packages, no shared-base path-dep).
  The Wave 2 `openclaw-shared-base` v0.2.0/v0.2.1 fleet-wide pin wave is tracked in
  `r3dlex/openclaw-gitrepo-agent/spec/SUPPLY_CHAIN.md`.

## History

| Date | Component | Old pin | New pin | PR |
|---|---|---|---|---|
| 2026-06-06 | `python:3.12-slim` | floating tag | `sha256:090ba77e2958f6af52a5341f788b50b032dd4ca28377d2893dcf1ecbdfdfe203` | (initial pin PR) |
