# Security policy

## Reporting a vulnerability

Please **do not open a public issue**. Use GitHub's private reporting: the **Security** tab of the repository → **Report a vulnerability** (<https://github.com/Hugo-Galley/Numera/security/advisories/new>).

Include the version (or commit), the steps to reproduce and the impact you estimate. Numera is a personal project maintained in spare time: expect a first reply within a week, with no commitment on fix timing.

## Supported versions

Only the **latest published version** receives security fixes (see the [releases](https://github.com/Hugo-Galley/Numera/releases)). A `release/X.Y` branch is opened only for a critical fix on an older version.

## Scope

Numera is a **self-hosted, single-user** application, meant to run behind your own network or a reverse proxy. In scope: authentication (JWT, TOTP, passkeys), MCP tokens (read-only), file import, backup encryption, Docker images. The public demo instance only holds fictitious data.

## What is in place

Non-root, read-only images; dependencies and images scanned by Trivy on every PR and every week; published images signed (cosign) with an SBOM; GitHub Actions and base images pinned by SHA / digest; secrets provided as environment variables, validated at startup in production.
