# Security Policy

## Supported versions

Security fixes are applied to the latest version on the `main` branch.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability reporting feature for this repository. Include reproduction steps, affected versions, impact, and any suggested mitigation.

If private vulnerability reporting is unavailable, contact the maintainer through the email address listed on the GitHub profile for `sden316` and avoid including sensitive documents in the initial message.

## Local-processing boundary

DSNS PDF Pro binds to `127.0.0.1` by default and processes uploaded files in memory. It is not designed to be exposed directly to untrusted networks. The included Flask development server is for local use only.
