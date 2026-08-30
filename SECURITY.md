# Security Policy

## Supported Version

The current `main` branch is the supported portfolio version.

## Reporting a Vulnerability

Please do not open a public issue containing credentials, exploitable vulnerability details, personal data, or other sensitive information. Use GitHub's private vulnerability reporting/security advisory flow when available, or contact the repository owner privately.

When reporting a vulnerability, include:

- the affected component or file;
- reproduction steps;
- potential impact;
- suggested mitigation, when available.

## Security Controls

- This portfolio project uses synthetic/demo data and must not contain production credentials or private customer data.
- Local `.env` files, secrets, caches, and temporary runtime outputs should remain excluded through `.gitignore`.
- CodeQL is used for static application security testing.
- Dependabot is configured for dependency and GitHub Actions updates.
- GitHub Actions runs automated project checks.

