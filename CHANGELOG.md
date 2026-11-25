# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Hospital, doctor, specialisation (12 seeded), pharmacy and patient profile models.
- Hospital self-registration with licence upload (PDF/JPG/PNG, max 5 MB) and admin approve/reject with reason.
- Web dashboards: email login, role-based routing, pending/rejected pages, admin hospital review and user list.
- Licence proofs are admin-only; they're never served from the public media URL.
- Hospitals manage their own doctors (add, edit, deactivate) and pharmacies.
- Patient REST API: registration, JWT login (patients only), token refresh, `/api/me/`.
- Catalogue API: specialisations, doctors, approved hospitals with straight-line distance sort.
- `seed_demo` command with fictional, deterministic demo data and documented logins.
- ADR 0007 (JWT for the app, sessions for the web).
- Repository foundation: MIT licence, README skeleton, pre-commit hooks (ruff, whitespace, private-key check).
- Django 5.2 project with an email-login custom user and five roles.
- Service-layer error type (`DomainError`) that the API turns into `{"detail", "code"}` JSON.
- OpenAPI schema and Swagger UI at `/api/docs/`.
- Docker Compose dev environment (PostgreSQL 16 + Django) that runs without a `.env` file.
- GitHub Actions CI: lint, format check, tests with coverage gate, Docker build.
- ADRs 0001–0006 for the upfront decisions.
