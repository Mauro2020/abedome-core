# ABEDOME Core foundation

## Purpose

This repository is the ABEDOME downstream of Home Assistant Core. It keeps the upstream automation engine intact while providing a controlled place for ABEDOME product identity and approved product changes.

This repository is an independent downstream derivative. ABEDOME is not affiliated with, endorsed by, or sponsored by the Home Assistant project.

## Upstream and attribution

- Upstream: [home-assistant/core](https://github.com/home-assistant/core)
- Upstream development branch: `dev`
- License, copyright notices, contributor credits, and upstream acknowledgements remain in place.
- Every ABEDOME release and product-facing screen must retain appropriate attribution to Home Assistant where required.

## Branch model

- `dev` is the upstream-aligned branch.
- `abedome/develop` is the protected ABEDOME integration base.
- Short-lived `agent/*` or `feature/*` branches target `abedome/develop` through a pull request.
- An upstream update is reviewed in its own pull request before it reaches `abedome/develop`; no upstream change is promoted automatically.

## Brand contract

The configuration in [`brand/abedome.json`](../../brand/abedome.json) is the only approved source for product naming, palette, asset mapping, and attribution metadata in this repository.

This foundation deliberately does **not** alter runtime behavior, telemetry, integrations, or user data. Any Core behavior change must remain separate from visual rebranding and arrive in its own reviewed pull request.

## Release boundary

Core must remain compatible with the ABEDOME Frontend, Supervisor, and OS release train. A branded Core build cannot be published until compatibility and rollback behavior have been validated.
