# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Repository foundation: MIT licence, README skeleton, pre-commit hooks (ruff, whitespace, private-key check).
- Django 5.2 project with an email-login custom user and five roles.
- Service-layer error type (`DomainError`) that the API turns into `{"detail", "code"}` JSON.
- OpenAPI schema and Swagger UI at `/api/docs/`.
- Docker Compose dev environment (PostgreSQL 16 + Django) that runs without a `.env` file.
- GitHub Actions CI: lint, format check, tests with coverage gate, Docker build.
- ADRs 0001–0006 for the upfront decisions.
