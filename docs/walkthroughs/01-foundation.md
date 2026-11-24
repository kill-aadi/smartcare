# Walkthrough 01 — Repo foundation

## What was built

- **Repo hygiene:** MIT licence, README skeleton, CHANGELOG, `.gitignore` (secrets, keystores, the old 17 Nov
  skeleton), `.gitattributes` (LF line endings everywhere), `.editorconfig`.
- **pre-commit:** on every commit it trims whitespace, blocks private keys and large files, and runs `ruff` (lint +
  format) on Python.
- **Django project** in `backend/`, managed with `uv` (exact versions pinned in `pyproject.toml` and `uv.lock`).
  - A **custom user model** with email login (no username) and a `role` field: admin, hospital, doctor, pharmacy,
    patient. It's created before the first migration because Django can't easily switch user models later.
  - Emails are stored lower-case, and the database also enforces "unique ignoring case".
  - **`DomainError`:** the type that business rules will raise from `services.py` files, plus an API handler
    that turns it into JSON.
  - **OpenAPI docs** at `/api/docs/`.
- **Docker Compose:** `docker compose up` starts PostgreSQL 16 and Django with live reload. No `.env` file needed.
- **CI:** GitHub Actions runs lint, format check, tests against a real Postgres, an 80% coverage gate, and a
  Docker build on every pull request.
- **ADRs 0001–0006:** the decisions made before any code (Postgres, HTMX dashboards, Container Apps, Bicep,
  AI-assisted development, no Entra login for users).

## How one request flows

Take a dashboard login with a differently-cased email, `ANA@EXAMPLE.TEST` (the login page itself arrives in
milestone 2, but the code path below exists now and is tested by `test_login_is_case_insensitive`).

1. `docker compose up`: compose waits for the `db` health check (`pg_isready`), then the `web` container runs
   `migrate` and `runserver`. Settings come from environment variables via `django-environ`
   (`backend/config/settings.py`).
2. Django's `authenticate(email="ANA@EXAMPLE.TEST", password=...)` goes through `AUTHENTICATION_BACKENDS`, which
   points to `accounts.backends.EmailBackend`.
3. `EmailBackend.authenticate` looks the user up with `email__iexact`, so case doesn't matter, then checks the
   password hash and that the account is active.
4. The user was created through `UserManager.create_user`, which stored `ana@example.test`. A second account
   `Ana@Example.test` can't exist: the DB constraint `user_email_ci_unique` is a unique index on `LOWER(email)`.

And for the API, when a service later raises `SessionFull("This session is full")` (a `DomainError` subclass with
`code = "session_full"`, `status = 409`), DRF calls `core.api.domain_exception_handler`, which returns
`409 {"detail": "This session is full", "code": "session_full"}`. Views never build error responses by hand.

## The files that matter

- `backend/accounts/models.py`: the `User` model and `Role` choices that every later feature checks.
- `backend/accounts/managers.py` and `accounts/backends.py`: email normalisation and case-insensitive login.
- `backend/core/exceptions.py` and `core/api.py`: how business-rule errors reach the API as JSON.
- `backend/config/settings.py`: all configuration from environment variables; `STORAGES` is the seam for Azure
  Blob in v2.
- `docker-compose.yml` and `.github/workflows/ci.yml`: how it runs locally and in CI.

## Likely interview questions

**Why a custom user model on day one?**
Django ties the user model into the first migrations and foreign keys. Swapping it later means rewriting
migrations, so the docs recommend a custom one from the start. I needed email login and a role field anyway.

**Why is the role a field rather than Django groups?**
Each user has exactly one role, and the role decides which dashboard or app they get. A single field is simpler to
query and explain. Groups suit many overlapping permissions, which we don't have.

**How do you stop duplicate accounts with different capitalisation?**
Two layers. The manager lower-cases emails on create, and the database has a unique index on `LOWER(email)`, so even
code that bypasses the manager can't create a duplicate. The test bypasses the manager on purpose to prove the
constraint holds.

**Why test against PostgreSQL instead of SQLite?**
Later milestones rely on Postgres features: `SELECT ... FOR UPDATE` row locks for token numbers and partial unique
indexes. SQLite behaves differently, so tests could pass locally and fail in production. CI runs a Postgres service
container for the same reason.

**What does `DomainError` give you?**
Business rules live in `services.py` and raise one error type with a machine-readable `code` and an HTTP `status`.
The API turns it into consistent JSON, and the dashboards show it as a message. The rule is written once, it's
testable without HTTP, and the mobile app can switch on `code`.

**Why does the Docker image put the virtualenv in `/opt/venv`?**
In development, compose bind-mounts `./backend` over `/app` for live reload. A venv inside `/app` would be hidden by
the mount, so it lives outside it.

**What does CI check, and what does the coverage gate measure?**
Lint, formatting, the test suite against Postgres, and a Docker build. The 80% gate measures the business-logic
modules (`services.py`, permissions, queue, AI, shared `core/`) rather than every file, so it tracks the code that
matters instead of being padded by settings and migrations.
