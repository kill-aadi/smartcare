# SmartCare v1.0-fyp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the SmartCare FYP as a runnable monorepo (Django API + web dashboards, Flutter patient app, scikit-learn
symptom classifier, PostgreSQL) that starts with one `docker compose up`, and tag it `v1.0-fyp`.

**Architecture:** One Django project in `backend/` serves server-rendered dashboards (templates + Bootstrap 5 + HTMX,
session auth) for admin/hospital/doctor/pharmacy, and a DRF API (simplejwt) for the patient-only Flutter app in
`mobile/`. Business rules live in per-app `services.py` modules that views and API views both call. The AI feature is
a TF-IDF + logistic-regression pipeline trained in `ml/`, saved as a versioned artefact, and loaded by Django.

**Tech Stack:** Python 3.12, uv, Django 5.2, DRF, djangorestframework-simplejwt, drf-spectacular, django-environ,
psycopg 3, pytest + pytest-django + factory_boy + Faker, ruff, pre-commit, PostgreSQL 16, Docker Compose,
scikit-learn + joblib, Flutter stable (Dart 3) with Riverpod, dio, go_router, flutter_secure_storage, geolocator,
url_launcher, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-24-smartcare-design.md` (source of truth) and `docs/HANDOVER.md`
(working agreement). Read both before starting any milestone.

## Global Constraints

- Python 3.12; Django 5.2.x; PostgreSQL 16; pin exact versions in `backend/pyproject.toml` + `uv.lock` (builder picks current releases).
- Must run with Docker only: `docker compose up` works on a fresh clone **without** a `.env` file (defaults in compose; `.env` optional).
- No Redis, no Celery, no Azure SDKs in v1. `api/` and `infra/` from the 17 Nov skeleton are **not** committed in v1.
- Roles are exactly: `admin`, `hospital`, `doctor`, `pharmacy`, `patient`. Email login (no username field).
- Hospital `approval_status` ∈ {`pending`, `approved`, `rejected`}. Booking `payment_status` ∈ {`pending`, `paid`}; `status` ∈ {`booked`, `cancelled`, `completed`, `no_show`}. PharmacyRequest `status` ∈ {`pending`, `accepted`, `rejected`, `paid`}.
- ConsultingSession defaults: `current_token = 0`, `avg_consult_minutes = 10`.
- ETA = (token_no − current_token) × avg_consult_minutes, clamped at 0, always displayed as `~N min`, never as a promise.
- Only approved hospitals' (and active) doctors are visible to patients.
- Payments are simulated: `Payment.provider = "simulated"`. UI copy wherever a Pay button appears: **"Simulated payment — no real money is charged."**
- AI low-confidence copy (top-1 probability < `0.40`): **"We're not sure — consider a General Physician."**
- AI disclaimer copy (app, API response, README): **"Not medical advice. SmartCare suggests which kind of doctor to see; it does not diagnose. In an emergency, contact your local emergency number."**
- Canonical specialisations (data migration, ML mapping and seed all use exactly these names): General Physician, Dermatology, Pulmonology, Cardiology, Neurology, Orthopaedics, Gastroenterology, Urology, Endocrinology, General Surgery, ENT, Gynaecology.
- Money: `DecimalField(max_digits=8, decimal_places=2)`, displayed as INR (`₹`). `TIME_ZONE = "Asia/Kolkata"` (env-overridable), `USE_TZ = True`.
- No real people or real hospital names anywhere. Seed emails use the reserved `.test` domain. Seed is deterministic (`Faker.seed(42)`, `random.seed(42)`).
- Never commit `.env`, keys, keystores, the raw dataset if its licence forbids redistribution, or the original report PDF.
- Commits: Conventional Commits, small, each ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Author is Marwan Ibrahim (already in global git config).
- README claims only what the code does at that commit.

## Review Focus

1. **Patient double-taps "Book"** on the same session → second request is rejected with 409 `already_booked`; still exactly one booking and one token. (Test in Task 3.2.)
2. **A doctor/pharmacy/hospital/admin logs into the mobile app** → token endpoint returns 401 with "This app is for patients. Staff should use the web dashboard." and issues no token. (Test in Task 2.5.)
3. **Patient requests another patient's booking, prescription or pharmacy request by ID** → 404 (not 403, never leaks existence). (Tests in Tasks 3.5 and 4.3.)
4. **A pending or rejected hospital logs into the dashboard** → sees the "awaiting approval"/"rejected" page, cannot add doctors or pharmacies, and nothing of theirs appears in the patient API. (Tests in Tasks 2.3 and 2.6.)
5. **Symptom text that is empty, whitespace, gibberish or very long** → empty/whitespace = 400; > 1000 chars = 400; gibberish ("asdf qwer") = 200 with `confident: false` and the low-confidence copy. (Test in Task 5.5.)

---

## Conventions for every milestone

**Branch:** each milestone runs on its own branch from an up-to-date `main` (names given per milestone).

**Backend test command** (used in every backend verification step):
`docker compose run --rm web pytest <path> -v` — Expected output named per step.
Lint: `docker compose run --rm web sh -c "ruff check . && ruff format --check ."` — Expected: `All checks passed!` and no files to reformat.

**Shared backend interfaces (defined in Task 1.2, used everywhere):**
- `core.exceptions.DomainError(Exception)` with class attributes `code: str = "domain_error"` and `status: int = 400`. Shared subclasses also live in `core/exceptions.py`: `NotAllowed` (`not_allowed`, 403), `InvalidTransition` (`invalid_transition`, 400), `AlreadyPaid` (`already_paid`, 409). App-specific ones live in that app's `services.py` (e.g. `class SessionFull(DomainError): code = "session_full"; status = 409`); `code` is the snake_case of the class name.
- `core.api.domain_exception_handler(exc, context)` (set as DRF `EXCEPTION_HANDLER`): `DomainError` → `Response({"detail": str(exc), "code": exc.code}, status=exc.status)`; everything else → DRF default.
- Dashboard views catch `DomainError` and show `messages.error(request, str(exc))`.
- Object-level access in the API is done by **filtering the queryset by `request.user`**, so other users' objects 404.

**Milestone close (last task of each milestone):**
1. Full suite + lint green (commands above). For mobile: `flutter analyze` → `No issues found!`, `flutter test` → `All tests passed!`.
2. README updated for any behaviour change; CHANGELOG `## [Unreleased]` updated.
3. Write `docs/walkthroughs/NN-<name>.md` with exactly these headings: `## What was built`, `## How one request flows` (one concrete request, file by file), `## The files that matter` (3–5, with one line each), `## Likely interview questions` (≥ 5 Q&A).
4. Screenshots of any new working UI into `docs/screenshots/` (`mNN-<what>.png`).
5. `git push -u origin <branch>` and `gh pr create --base main --title "<conventional title>" --body "<summary + link to walkthrough + test evidence>"` (body ends with the 🤖 Claude Code line).
6. `gh pr checks --watch` → all green.
7. **STOP. Ask Marwan to read the walkthrough and approve.** Merge (`gh pr merge --merge --delete-branch`, a merge commit so the feature-by-feature history stays visible) only after he says so. Then `git checkout main && git pull`.

---

## File Structure (end state of v1)

```
.editorconfig  .gitattributes  .gitignore  .pre-commit-config.yaml
LICENSE  README.md  CHANGELOG.md  docker-compose.yml  .env.example
.github/workflows/ci.yml
backend/
  Dockerfile  pyproject.toml  uv.lock  manage.py  conftest.py
  config/      settings.py urls.py wsgi.py asgi.py
  core/        exceptions.py api.py geo.py permissions.py factories.py (shared test factories)
  accounts/    models.py (User, Role, PatientProfile) managers.py backends.py serializers.py api.py urls.py
  hospitals/   models.py services.py forms.py views.py api.py serializers.py urls.py
  doctors/     models.py (Specialization, Doctor) services.py forms.py views.py api.py serializers.py
               migrations/0002_seed_specializations.py
  pharmacy/    models.py (Pharmacy, PharmacyRequest) services.py forms.py views.py api.py serializers.py
  bookings/    models.py (ConsultingSession, Booking) services.py queue.py forms.py views.py api.py serializers.py
  payments/    models.py (Payment) services.py
  prescriptions/ models.py (Prescription, PrescriptionItem) services.py forms.py views.py api.py serializers.py
  complaints/  models.py services.py forms.py views.py api.py serializers.py
  ai_suggest/  predictor.py ranking.py api.py serializers.py model/ (artefact + metadata.json)
  dashboards/  mixins.py views.py stats.py urls.py
               management/commands/seed_demo.py
  templates/   base.html, registration/, dashboards/<role>/...
  static/vendor/ bootstrap 5.3.x css+js, htmx 2.x, chart.js 4.x (vendored, pinned, so it runs offline)
  */tests/     test_*.py per app
ml/
  pyproject.toml uv.lock README.md (model card) notebook.ipynb
  data/disease_to_specialization.csv  data/raw/ (git-ignored)
  scripts/download_data.py  smartcare_ml/train.py  smartcare_ml/data.py  tests/
mobile/        Flutter app (structure in Milestone 6)
docs/
  architecture.md erd.md api.md original-fyp.md
  adr/ walkthroughs/ screenshots/ demo/ superpowers/{specs,plans}/
```

---

# Milestone 1 — Repo foundation (branch `feat/m1-foundation`)

### Task 1.1: Repo hygiene, licence, README skeleton, pre-commit

**Files:**
- Create: `.gitignore`, `.gitattributes`, `.editorconfig`, `LICENSE`, `README.md`, `CHANGELOG.md`, `.pre-commit-config.yaml`

**Interfaces:**
- Produces: pre-commit hooks every later commit runs.

- [ ] **Step 1:** `.gitattributes` = `* text=auto eol=lf`. `.gitignore` covers Python, uv `.venv/`, `.env`, `media/`, `staticfiles/`, `.coverage`, `htmlcov/`, Flutter/Dart (`mobile/build/`, `.dart_tool/`), `*.jks`, `*.keystore`, `key.properties`, `ml/data/raw/`, `.DS_Store`, `api/`, `infra/` (the old skeleton must not be committed by accident in v1; `infra/` is un-ignored in M9).
- [ ] **Step 2:** `LICENSE`: MIT, `Copyright (c) 2026 Marwan Ibrahim`. `CHANGELOG.md`: Keep a Changelog format with `## [Unreleased]`.
- [ ] **Step 3:** `README.md` skeleton with the spec §8 section order as headings. Content only for what exists now: hero line, "The story" (2–3 sentences), status line `🚧 Rebuild in progress — milestone 1 of 7`, licence. No feature claims yet.
- [ ] **Step 4:** `.pre-commit-config.yaml` with pinned revs: `pre-commit-hooks` (trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files `--maxkb=2048`, detect-private-key, check-merge-conflict) and `ruff-pre-commit` (`ruff-check --fix`, `ruff-format`) scoped to `^(backend|ml)/`.
- [ ] **Step 5:** Run `pre-commit install && pre-commit run --all-files` → Expected: every hook `Passed` (or `Skipped`).
- [ ] **Step 6: Commit** `chore: add repo hygiene, MIT licence, README skeleton and pre-commit`

### Task 1.2: Django project, core app, custom email User

**Files:**
- Create: `backend/pyproject.toml`, `backend/uv.lock`, `backend/manage.py`, `backend/conftest.py`, `backend/config/{__init__,settings,urls,wsgi,asgi}.py`, `backend/core/{__init__,apps,exceptions,api}.py`, `backend/accounts/{__init__,apps,models,managers,backends,admin}.py`, `backend/accounts/migrations/0001_initial.py`
- Test: `backend/accounts/tests/test_user_model.py`, `backend/core/tests/test_exception_handler.py`

**Interfaces:**
- Produces: `accounts.models.Role(models.TextChoices)` with `ADMIN, HOSPITAL, DOCTOR, PHARMACY, PATIENT` (values lower-case); `accounts.models.User(AbstractUser)` with `username = None`, `email` unique, `USERNAME_FIELD = "email"`, `role` (default `patient`); `User.objects.create_user(email, password=None, **extra) -> User`; `create_superuser(...)` forces `role=admin, is_staff=True, is_superuser=True`. `core.exceptions.DomainError`, `core.api.domain_exception_handler` (see Conventions).

- [ ] **Step 1:** `uv init --app backend` style `pyproject.toml` (name `smartcare-backend`, `requires-python = "==3.12.*"`), runtime deps: django 5.2.x, djangorestframework, djangorestframework-simplejwt, drf-spectacular, django-environ, psycopg[binary], Pillow; dev group: pytest, pytest-django, pytest-cov, factory-boy, Faker, ruff. Ruff config: `line-length = 100`, `select = ["E","F","I","B","UP","DJ"]`. Pytest config: `DJANGO_SETTINGS_MODULE = "config.settings"`, `python_files = ["test_*.py"]`, `addopts = "--reuse-db"`. Coverage: `[tool.coverage.report] include = ["*/services.py","*/permissions.py","*/queue.py","ai_suggest/*.py","*/mixins.py"]`, `fail_under = 80`.
- [ ] **Step 2: Write failing tests** in `test_user_model.py`:
```python
def test_create_user_uses_email_and_lowercases_domain_and_local_part(db):
    u = User.objects.create_user("Ana@Example.TEST", password="x-pass-123")
    assert u.email == "ana@example.test" and u.role == Role.PATIENT and u.check_password("x-pass-123")
def test_email_unique_case_insensitive(db):  # second create with "ANA@example.test" raises IntegrityError
def test_create_superuser_is_admin_role(db):  # role == Role.ADMIN, is_staff, is_superuser
def test_login_backend_is_case_insensitive(db, client):  # client.login(email="ANA@EXAMPLE.TEST", ...) is True
```
`test_exception_handler.py`: a dummy APIView raising `DomainError("nope")` subclass with `code="x"`, `status=409` → response 409, JSON `{"detail": "nope", "code": "x"}`.
- [ ] **Step 3:** Run `cd backend && uv run pytest` → Expected: FAIL (import errors) — the DB isn't up yet, so for this one step run with a temporary local Postgres: `docker run -d --name sc-pg -e POSTGRES_PASSWORD=smartcare -e POSTGRES_USER=smartcare -e POSTGRES_DB=smartcare -p 5432:5432 postgres:16-alpine` (removed in Task 1.3 Step 5).
- [ ] **Step 4: Implement.** Settings read everything via `django-environ` with dev defaults: `DEBUG` (default False; compose sets True), `SECRET_KEY` (dev default only when DEBUG), `DATABASE_URL` (default `postgres://smartcare:smartcare@db:5432/smartcare`), `ALLOWED_HOSTS` (default `localhost,127.0.0.1,10.0.2.2`), `TIME_ZONE`. `AUTH_USER_MODEL = "accounts.User"`. Email normalisation: manager lower-cases the whole address; DB-level `UniqueConstraint(Lower("email"), name="user_email_ci_unique")`. `accounts.backends.EmailBackend` (subclass `ModelBackend`) looks up `email__iexact`. `EMAIL_BACKEND = console`. REST_FRAMEWORK: `DEFAULT_AUTHENTICATION_CLASSES = [JWTAuthentication, SessionAuthentication]`, `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]`, `DEFAULT_SCHEMA_CLASS = drf_spectacular`, `EXCEPTION_HANDLER = "core.api.domain_exception_handler"`. `STORAGES` with default `FileSystemStorage` (so v2 swaps to Blob by config). URLs: `/django-admin/`, `/api/schema/`, `/api/docs/` (Swagger UI).
- [ ] **Step 5:** `uv run python manage.py makemigrations accounts && uv run pytest -v` → Expected: 5 passed.
- [ ] **Step 6: Commit** `feat(backend): add Django project with email-login custom user`

### Task 1.3: Docker Compose dev environment

**Files:**
- Create: `backend/Dockerfile`, `backend/.dockerignore`, `docker-compose.yml`, `.env.example`
- Test: `backend/core/tests/test_api_docs.py`

**Interfaces:**
- Produces: services `db` and `web`; the backend test command in Conventions.

- [ ] **Step 1: Failing test** `test_schema_and_docs_are_served(client)`: `GET /api/schema/` → 200 and `b"openapi"` in body; `GET /api/docs/` → 200.
- [ ] **Step 2: Dockerfile (dev):** `python:3.12-slim`; `COPY --from=ghcr.io/astral-sh/uv:<pinned> /uv /uvx /bin/`; `ENV UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1`; `uv sync --frozen` (dev group included) from copied `pyproject.toml`+`uv.lock` before `COPY . .`; non-root `useradd --uid 10001 app` (pattern from the old skeleton). The venv lives at `/opt/venv` so the source bind-mount over `/app` doesn't hide it.
- [ ] **Step 3: docker-compose.yml:** `db`: `postgres:16-alpine`, env `POSTGRES_USER/PASSWORD/DB=smartcare`, named volume `pgdata`, healthcheck `pg_isready -U smartcare`, port `5432:5432`. `web`: build `./backend`, `env_file: [{path: .env, required: false}]`, `environment: DEBUG: "true"`, command `sh -c "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"`, bind-mount `./backend:/app`, volume `media:/app/media`, port `8000:8000`, `depends_on: db: condition: service_healthy`. `.env.example` lists every setting from Task 1.2 Step 4 with dev values and a comment per line.
- [ ] **Step 4:** `docker rm -f sc-pg; docker compose up -d --build && docker compose run --rm web pytest -v` → Expected: 6 passed. `curl -s -o /dev/null -w "%{http_code}" localhost:8000/api/docs/` → `200`.
- [ ] **Step 5: Commit** `feat: add docker compose dev environment (Postgres + Django)`

### Task 1.4: CI skeleton

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1:** Workflow on `push` to `main` and `pull_request`. Job `backend`: ubuntu-latest, service `postgres:16-alpine` (same creds, health-checked), `astral-sh/setup-uv` pinned, `uv sync --frozen` in `backend/`, `ruff check .`, `ruff format --check .`, `pytest --cov --cov-report=term-missing` with `DATABASE_URL=postgres://smartcare:smartcare@localhost:5432/smartcare`, `SECRET_KEY=ci`, `DEBUG=false`. Job `docker`: `docker build backend`. Add CI badge to README.
- [ ] **Step 2:** Commit `ci: add backend lint, test and docker build workflow`, push branch, `gh run watch` → Expected: both jobs ✓.

### Task 1.5: Upfront ADRs + milestone close

**Files:**
- Create: `docs/adr/README.md` (index), `docs/adr/0000-template.md`, `docs/adr/0001-postgresql-over-mysql.md`, `0002-django-templates-htmx-over-spa.md`, `0003-container-apps-over-app-service-aks.md`, `0004-bicep-over-terraform.md`, `0005-ai-assisted-development.md`, `0006-no-entra-external-id-login.md`, `docs/walkthroughs/01-foundation.md`

- [ ] **Step 1:** Each ADR ≤ 1 page: Status (Accepted, 2026-11-24), Context, Decision, Consequences, Alternatives — content taken from spec §5, §6, §8a, §8b.
- [ ] **Step 2:** Commit `docs: add ADRs for upfront decisions`.
- [ ] **Step 3:** Milestone close (Conventions). After merge, enable branch protection on `main` requiring the `backend` check: `gh api -X PUT repos/kill-aadi/smartcare/branches/main/protection` with required status checks `backend`, `docker`, `enforce_admins=false`, `required_pull_request_reviews=null`, `restrictions=null`.

---

# Milestone 2 — Accounts, roles, hospitals, doctors, pharmacies (branch `feat/m2-accounts-roles`)

### Task 2.1: Domain models for hospitals, specialisations, doctors, pharmacies, patients

**Files:**
- Create: `backend/{hospitals,doctors,pharmacy}/` apps (`models.py`, `admin.py`, migrations), `backend/doctors/migrations/0002_seed_specializations.py`, `backend/core/factories.py`
- Modify: `backend/accounts/models.py` (add `PatientProfile`)
- Test: `backend/hospitals/tests/test_models.py`, `backend/doctors/tests/test_models.py`

**Interfaces:**
- Produces:
  - `Hospital`: `user` (1:1, role hospital), `name`, `place`, `phone`, `email`, `photo` (ImageField, optional, `hospitals/photos/`), `licence_proof` (FileField, `licences/`), `latitude`, `longitude` (`DecimalField(9,6)`), `approval_status` (`ApprovalStatus` TextChoices, default pending), `rejection_reason` (blank), `created_at`, `reviewed_at` (null). Manager method `Hospital.objects.approved()`.
  - `Specialization`: `name` (unique), `description`. The data migration exports a module-level `NAMES: list[str]` (the 12 canonical names, in Global Constraints order) that the ML tests import.
  - `Doctor`: `user` (1:1), `hospital` (FK, related `doctors`), `name`, `specialization` (FK PROTECT), `qualification`, `experience_years` (PositiveSmallInteger), `gender` (`Gender` TextChoices: female/male/other), `photo` (optional). Manager method `Doctor.objects.visible_to_patients()` = `user__is_active=True, hospital__approval_status="approved"`.
  - `Pharmacy`: `user` (1:1), `hospital` (FK, related `pharmacies`), `name`, `phone`, `email`.
  - `PatientProfile`: `user` (1:1, related `patient_profile`), `name`, `phone`, `date_of_birth`, `gender`, `place`.
  - `core.factories`: `UserFactory`, `HospitalFactory(approved by default)`, `SpecializationFactory` (uses `get_or_create` on canonical names), `DoctorFactory`, `PharmacyFactory`, `PatientFactory` (returns a `User` with profile). Later tasks add factories here.

- [ ] **Step 1: Failing tests:** `test_specializations_seeded` (all 12 canonical names exist after migrate); `test_visible_to_patients_excludes_pending_rejected_and_inactive` (one doctor each in approved/pending/rejected hospital + one inactive in approved → only the one); `test_approved_manager`; `test_hospital_coordinates_precision` (lat `10.527642` round-trips).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement models, data migration (descriptions one sentence each, plain English, used later for pgvector), factories. **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat: add hospital, doctor, specialisation, pharmacy and patient models`

### Task 2.2: Hospital self-registration and admin approval (services)

**Files:**
- Create: `backend/hospitals/services.py`, `backend/hospitals/forms.py`
- Test: `backend/hospitals/tests/test_services.py`, `backend/hospitals/tests/test_forms.py`

**Interfaces:**
- Produces:
  - `register_hospital(*, email: str, password: str, name: str, place: str, phone: str, latitude: Decimal, longitude: Decimal, licence_proof: File, photo: File | None = None) -> Hospital` — creates `User(role=hospital)` + `Hospital(pending)` in one transaction.
  - `approve_hospital(hospital: Hospital, *, by: User) -> Hospital`; `reject_hospital(hospital: Hospital, *, by: User, reason: str) -> Hospital`. Allowed transitions: pending→approved, pending→rejected, rejected→approved. Otherwise raise `InvalidTransition(DomainError)`. `by` must have role admin, else `NotAllowed(DomainError, status=403)`. Sets `reviewed_at`. Sends a console email to the hospital.
  - `HospitalRegistrationForm` (ModelForm + email/password with Django password validators).

- [ ] **Step 1: Failing tests:** register creates pending hospital + hospital-role user; approve sets status/reviewed_at and emails (`mail.outbox` length 1); reject requires non-empty reason; `approve` of already approved raises `InvalidTransition`; non-admin `by` raises `NotAllowed`. Form tests: licence proof accepts `.pdf/.jpg/.jpeg/.png` only, max 5 MB (6 MB upload → form error "File too large (max 5 MB)."); latitude must be in [-90, 90], longitude in [-180, 180].
- [ ] **Step 2–4:** fail → implement → pass.
- [ ] **Step 5: Commit** `feat(hospitals): add self-registration and admin approval services`

### Task 2.3: Dashboards shell, login, role routing, admin approval pages

**Files:**
- Create: `backend/dashboards/{apps,mixins,views,urls}.py`, `backend/templates/base.html`, `templates/registration/login.html`, `templates/dashboards/{pending,rejected,patient_use_app}.html`, `templates/dashboards/admin/{home,hospitals,hospital_detail,users}.html`, `templates/hospitals/register.html`, `backend/static/vendor/` (Bootstrap 5.3.x css+bundle js, htmx 2.x — pinned versions downloaded from jsdelivr, committed)
- Modify: `backend/config/urls.py`, `backend/hospitals/views.py`, `backend/hospitals/urls.py`
- Test: `backend/dashboards/tests/test_access.py`, `backend/hospitals/tests/test_views.py`

**Interfaces:**
- Produces:
  - `dashboards.mixins.RoleRequiredMixin` (class attr `allowed_roles: tuple[str, ...]`; anonymous → login redirect; wrong role → 403). `ApprovedHospitalRequiredMixin` (hospital role; pending → redirect `dashboards:pending`, rejected → `dashboards:rejected`).
  - URLs: `/login/`, `/logout/` (POST), `/register/hospital/`, `/dashboard/` (redirects by role to `/dashboard/admin/`, `/dashboard/hospital/`, `/dashboard/doctor/`, `/dashboard/pharmacy/`; patient → `patient_use_app` page), `/dashboard/admin/hospitals/` (filter by status), `/dashboard/admin/hospitals/<pk>/` (approve/reject forms POST), `/dashboard/admin/hospitals/<pk>/licence/` (streams licence file, admin only), `/dashboard/admin/users/`.
  - Licence files are **not** served from `MEDIA_URL`; only through the admin-only view. Photos are served from `MEDIA_URL` in DEBUG.

- [ ] **Step 1: Failing tests:** parametrised access matrix — for each role × each dashboard home URL assert 200/302/403 as appropriate; pending hospital at `/dashboard/hospital/` → redirected to pending page; rejected → rejected page showing `rejection_reason`; non-admin GET licence URL → 403; admin → 200 with file bytes; anonymous `/dashboard/` → 302 to `/login/?next=...`; register view POST creates pending hospital and shows "Thanks — an admin will review your registration."
- [ ] **Step 2–4:** fail → implement (Bootstrap navbar shows role + logout; HTMX included in `base.html`) → pass.
- [ ] **Step 5: Commit** `feat(dashboards): add login, role routing and admin hospital approval`

### Task 2.4: Hospital manages its doctors and pharmacies

**Files:**
- Create: `backend/doctors/{services,forms,views}.py`, `backend/pharmacy/{services,forms,views}.py`, templates `dashboards/hospital/{home,doctors,doctor_form,pharmacies,pharmacy_form}.html`
- Test: `backend/doctors/tests/test_services.py`, `backend/pharmacy/tests/test_services.py`, `backend/dashboards/tests/test_hospital_pages.py`

**Interfaces:**
- Produces:
  - `create_doctor(hospital: Hospital, *, email, password, name, specialization: Specialization, qualification, experience_years: int, gender, photo=None) -> Doctor` (creates `User(role=doctor)`).
  - `set_doctor_active(hospital: Hospital, doctor: Doctor, active: bool) -> Doctor` (toggles `user.is_active`; doctor of another hospital → `NotAllowed`).
  - `create_pharmacy(hospital: Hospital, *, email, password, name, phone) -> Pharmacy`.
  - Both create functions raise `HospitalNotApproved(DomainError)` unless hospital approved.
  - Hospital dashboard lists use `hospital.doctors` / `hospital.pharmacies` only; editing another hospital's doctor by pk → 404.

- [ ] **Step 1: Failing tests:** create succeeds for approved; raises for pending; deactivated doctor can't log in and disappears from `visible_to_patients()`; hospital B editing hospital A's doctor URL → 404; duplicate email → form error, no partial user created.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat: let hospitals manage their doctors and pharmacies`

### Task 2.5: Patient API auth (register, token, refresh, me) + ADR 0007

**Files:**
- Create: `backend/accounts/{serializers,api,urls}.py`, `backend/core/permissions.py`, `docs/adr/0007-jwt-for-mobile-session-for-web.md`
- Test: `backend/accounts/tests/test_api_auth.py`

**Interfaces:**
- Produces:
  - `core.permissions.IsPatient` (DRF permission: authenticated and `role == patient`). Every patient API view from now on uses `[IsPatient]`.
  - `POST /api/auth/register/` `{email, password, name, phone, date_of_birth, gender, place}` → 201 `{id, email}` (AllowAny; creates User role patient + PatientProfile).
  - `POST /api/auth/token/` `{email, password}` → 200 `{access, refresh}`; non-patient credentials → 401 `{"detail": "This app is for patients. Staff should use the web dashboard."}`. (Custom `TokenObtainPairSerializer`.)
  - `POST /api/auth/token/refresh/` (simplejwt default; `ACCESS_TOKEN_LIFETIME = 15 min`, `REFRESH_TOKEN_LIFETIME = 7 days`).
  - `GET /api/me/` → `{id, email, name, phone, date_of_birth, gender, place}`.

- [ ] **Step 1: Failing tests:** register → 201 then token works; register with existing email (any case) → 400; weak password → 400; doctor credentials at token endpoint → 401 with the exact copy, and no `access` key; `GET /api/me/` with doctor session cookie → 403; `/api/me/` without auth → 401.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(api): add patient registration and JWT auth`

### Task 2.6: Patient catalogue API (specialisations, hospitals nearby, pharmacies, doctors)

**Files:**
- Create: `backend/core/geo.py`, `backend/hospitals/{api,serializers}.py`, `backend/doctors/{api,serializers}.py`, `backend/pharmacy/{api,serializers}.py`, `backend/config/api_urls.py`
- Test: `backend/core/tests/test_geo.py`, `backend/hospitals/tests/test_api.py`, `backend/doctors/tests/test_api.py`

**Interfaces:**
- Produces:
  - `core.geo.haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float`; `core.geo.straight_line_minutes(km: float) -> int` = `ceil(km / 30 * 60)` (labelled "straight-line estimate" wherever shown).
  - `GET /api/specializations/` → `[{id, name, description}]`.
  - `GET /api/hospitals/?search=&lat=&lng=` → approved only, max 50; `search` icontains name or place; when `lat`&`lng` given, each item has `distance_km` (1 dp) and `straight_line_minutes` and list is sorted ascending by distance; otherwise those fields are `null` and sorted by name. Item: `{id, name, place, phone, email, photo_url, latitude, longitude, distance_km, straight_line_minutes}`. Invalid lat/lng → 400.
  - `GET /api/hospitals/<id>/` (404 if not approved); `GET /api/hospitals/<id>/pharmacies/` → `[{id, name, phone}]`.
  - `GET /api/doctors/?specialization=<id>&hospital=<id>` → `visible_to_patients()`, max 50: `{id, name, specialization: {id, name}, qualification, experience_years, gender, photo_url, hospital: {id, name, place, latitude, longitude}}`.
  - Distance sorting is done in Python over ≤ 50 rows (explainable; no PostGIS).

- [ ] **Step 1: Failing tests:** `haversine_km(51.5074, -0.1278, 48.8566, 2.3522)` ≈ 343.5 (abs diff < 1.0); same point → 0; nearby sort order with three hospitals; pending/rejected hospitals never in list or detail (404) and their doctors not in `/api/doctors/`; `lat=abc` → 400; search matches place case-insensitively.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(api): add hospital, doctor and specialisation catalogue with nearby sort`

### Task 2.7: `seed_demo` (people and places) + milestone close

**Files:**
- Create: `backend/dashboards/management/commands/seed_demo.py`
- Test: `backend/dashboards/tests/test_seed_demo.py`

**Interfaces:**
- Produces: `python manage.py seed_demo [--flush]`. Creates: 1 admin, 5 approved hospitals + 1 pending + 1 rejected (fictional names like "Riverside Demo Hospital", places Thrissur, Irinjalakuda, Chalakudy, Guruvayur, Kodungallur with plausible coordinates near Thrissur), 3–4 doctors per approved hospital covering all 12 specialisations, 1 pharmacy per approved hospital, 10 patients. Known logins (password `demo-pass-123` for all): `admin@smartcare.test`, `hospital@smartcare.test` (an approved one), `pending-hospital@smartcare.test`, `doctor@smartcare.test`, `pharmacy@smartcare.test` (same hospital as `doctor@`), `patient@smartcare.test`. If demo data exists and `--flush` isn't given → prints "Demo data already exists. Use --flush to recreate it." and exits 0 without changes. `--flush` deletes only non-superuser-created rows it owns (all rows whose user email ends `@smartcare.test`) then reseeds. Later milestones extend this command (structure it as `_seed_people()`, `_seed_sessions()`, … called in order).

- [ ] **Step 1: Failing tests:** running twice → same counts, second prints the message; `--flush` → same counts again; every known login authenticates; two runs with `--flush` produce identical hospital names (determinism).
- [ ] **Step 2–4:** fail → implement → pass. README: quickstart (`docker compose up`, `docker compose exec web python manage.py seed_demo`, demo logins table, "all data is fictional").
- [ ] **Step 5:** Commit `feat: add deterministic seed_demo command`. **Step 6:** Milestone close → walkthrough `02-accounts-roles.md`.

---

# Milestone 3 — Sessions, booking with atomic tokens, queue, simulated payment (branch `feat/m3-booking-queue`)

### Task 3.1: Consulting sessions (model, service, doctor dashboard)

**Files:**
- Create: `backend/bookings/{models,services,forms,views,urls}.py`, templates `dashboards/doctor/{home,sessions,session_form}.html`
- Test: `backend/bookings/tests/test_sessions.py`

**Interfaces:**
- Produces:
  - `ConsultingSession`: `doctor` (FK, related `sessions`), `date`, `start_time`, `end_time`, `fee`, `capacity` (PositiveSmallInteger ≥ 1), `current_token` (default 0), `avg_consult_minutes` (default 10), `created_at`. DB `CheckConstraint`s: `end_time > start_time`, `capacity >= 1`, `fee >= 0`. Methods: `starts_at() -> datetime`, `ends_at() -> datetime` (aware, in `TIME_ZONE`), `is_past(now) -> bool` (`ends_at() <= now`).
  - `create_session(doctor: Doctor, *, date, start_time, end_time, fee: Decimal, capacity: int, avg_consult_minutes: int = 10, now: datetime | None = None) -> ConsultingSession`. Raises `SessionInPast` if `ends_at <= now`; `SessionOverlap` if it overlaps another session of the same doctor on that date.
  - Doctor dashboard `/dashboard/doctor/sessions/` (list upcoming + create form).

- [ ] **Step 1: Failing tests:** valid create; past → `SessionInPast`; 09:00–11:00 vs existing 10:00–12:00 → `SessionOverlap`; back-to-back 11:00–12:00 after 09:00–11:00 → allowed; end ≤ start → form error; doctor B can't see doctor A's sessions page items.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(bookings): add consulting sessions for doctors`

### Task 3.2: Booking with atomic, sequential tokens

**Files:**
- Modify: `backend/bookings/models.py`, `backend/bookings/services.py`
- Test: `backend/bookings/tests/test_booking.py`, `backend/bookings/tests/test_booking_concurrency.py`

**Interfaces:**
- Produces:
  - `Booking`: `session` (FK, related `bookings`), `patient` (FK User), `description` (blank, max 500), `token_no` (PositiveSmallInteger), `payment_status` (default pending), `status` (default booked), `created_at`. `UniqueConstraint(session, token_no)`; partial `UniqueConstraint(session, patient, condition=~Q(status="cancelled"), name="one_active_booking_per_patient_session")`.
  - `book_session(patient: User, session_id: int, description: str = "", *, now: datetime | None = None) -> Booking`. Algorithm, all inside `transaction.atomic()`:
    1. `session = ConsultingSession.objects.select_for_update().get(pk=session_id, doctor__in=Doctor.objects.visible_to_patients())` (missing → `SessionNotFound`, 404).
    2. `session.is_past(now)` → `SessionInPast` (400).
    3. Active booking by this patient exists → `AlreadyBooked` (409).
    4. Active (non-cancelled) count ≥ capacity → `SessionFull` (409).
    5. `token_no = (max token_no over ALL bookings of the session, incl. cancelled) + 1` — tokens are never reused.
  - `cancel_booking(patient: User, booking: Booking, *, now=None) -> Booking`: only `status=booked`, only before the session ends, only own booking (else `NotAllowed`); frees capacity, keeps token number unused.
  - `seats_left(session) -> int` helper used by APIs.

- [ ] **Step 1: Failing tests (test_booking.py):** first booking gets token 1, second patient token 2; same patient twice → `AlreadyBooked` and count stays 1 (Review Focus 1); capacity 2 → third patient `SessionFull`; past session → `SessionInPast`; session of a pending hospital's doctor → `SessionNotFound`; cancel then new patient books → gets token 3 (not reused), and cancelled patient may re-book (token 4).
- [ ] **Step 2: Failing concurrency test (test_booking_concurrency.py):**
```python
@pytest.mark.django_db(transaction=True)
def test_concurrent_bookings_get_unique_sequential_tokens_and_respect_capacity():
    session = SessionFactory(capacity=5); patients = PatientFactory.create_batch(10)
    barrier = threading.Barrier(10); results, errors = [], []
    def worker(p):
        try:
            barrier.wait(); results.append(book_session(p, session.pk).token_no)
        except SessionFull: errors.append("full")
        finally: connection.close()
    threads = [threading.Thread(target=worker, args=(p,)) for p in patients]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert sorted(results) == [1, 2, 3, 4, 5] and len(errors) == 5
```
- [ ] **Step 3:** Run both → FAIL. **Step 4:** Implement. **Step 5:** Run → PASS. Also run the concurrency test with the `select_for_update()` temporarily removed and confirm it fails (record the failure output in the walkthrough — this is the interview story), then restore.
- [ ] **Step 6: Commit** `feat(bookings): assign atomic sequential token numbers with select_for_update`

### Task 3.3: Live queue — "Call next", no-show, queue status

**Files:**
- Create: `backend/bookings/queue.py`, templates `dashboards/doctor/{today,_queue_panel}.html`
- Modify: `backend/bookings/views.py`, `backend/bookings/urls.py`
- Test: `backend/bookings/tests/test_queue.py`

**Interfaces:**
- Produces:
  - `call_next(doctor: Doctor, session: ConsultingSession, *, today: date | None = None) -> int | None` — `select_for_update` on session; only own session (`NotAllowed`) and only `session.date == today` (`NotToday`); sets `current_token` to the smallest `token_no > current_token` among bookings with `status="booked"`; returns it, or `None` (and no change) when nobody is left.
  - `mark_no_show(doctor: Doctor, booking: Booking) -> Booking` — only own session, only `status=booked`, only `token_no <= session.current_token`.
  - `complete_booking(doctor: Doctor, booking: Booking) -> Booking` — "Mark consultation complete" without a prescription; same guards as `mark_no_show`; sets `status=completed`. (Task 4.1's `write_prescription` also completes the booking.)
  - `@dataclass(frozen=True) class QueueStatus: token_no: int; current_token: int; ahead: int; eta_minutes: int; state: Literal["waiting", "now_serving", "done", "cancelled"]`.
  - `queue_status(booking: Booking) -> QueueStatus`: `eta_minutes = max(token_no - current_token, 0) * avg_consult_minutes`; `ahead` = count of `status="booked"` bookings with `current_token < token_no' < token_no`; `state` = cancelled if booking cancelled; done if booking completed/no_show or `token_no < current_token`; now_serving if `token_no == current_token`; else waiting.
  - Doctor page `/dashboard/doctor/today/`: one card per today's session, HTMX panel `hx-get` polling `every 5s` showing "Now serving N", next 5 waiting tokens, and a "Call next" POST button (`hx-post`, swaps the panel).

- [ ] **Step 1: Failing tests:** `complete_booking` on a called token → completed, on a not-yet-called token → `InvalidTransition`; tokens 1,2,3 with 2 cancelled → call_next goes 0→1→3→None; another doctor's session → `NotAllowed`; tomorrow's session → `NotToday`; queue_status examples: token 7, current 4, avg 10 → `eta_minutes=30`, state waiting; token 4 current 4 → now_serving, eta 0; token 2 current 4 → done; HTMX POST returns the panel fragment (no `<html>`).
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(bookings): add live queue with call next and HTMX polling`

### Task 3.4: Simulated payments + ADR 0008

**Files:**
- Create: `backend/payments/{apps,models,services}.py`, `docs/adr/0008-simulated-payments.md`
- Test: `backend/payments/tests/test_services.py`

**Interfaces:**
- Produces:
  - `Payment`: `booking` (FK null), `pharmacy_request` (added in Task 4.2), `payer` (FK User), `amount`, `provider` (default `"simulated"`), `reference` (unique, `"SIM-" + uuid4().hex[:12].upper()`), `created_at`. CheckConstraint: exactly one target FK set (written in 4.2 when the second FK exists; in 3.4 `booking` is non-null-checked in service).
  - `pay_booking(patient: User, booking: Booking) -> Payment`: own booking only (`NotAllowed`), `status` booked, `payment_status` pending else `AlreadyPaid` (409); amount = `session.fee`; flips `payment_status=paid`; `select_for_update` on booking so a double tap can't create two payments.
  - Interface note (for the ADR): `payments.services` is the single seam a real gateway would replace.

- [ ] **Step 1: Failing tests:** pay → one Payment with amount = fee, reference matches `^SIM-[0-9A-F]{12}$`, booking paid; second pay → `AlreadyPaid`, still one Payment; paying cancelled booking → `InvalidTransition`; paying someone else's → `NotAllowed`.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(payments): add simulated payment for bookings`

### Task 3.5: Patient booking API + hospital bookings page

**Files:**
- Create: `backend/bookings/{api,serializers}.py`, template `dashboards/hospital/bookings.html`
- Modify: `backend/config/api_urls.py`
- Test: `backend/bookings/tests/test_api.py`

**Interfaces:**
- Produces (all `[IsPatient]` except none):
  - `GET /api/doctors/<id>/sessions/` → upcoming (not past) sessions of a visible doctor: `[{id, date, start_time, end_time, fee, capacity, seats_left}]`, sorted by start.
  - `POST /api/bookings/` `{session: id, description}` → 201 booking; DomainErrors map to their status/code.
  - `GET /api/bookings/` (own only, newest session first), `GET /api/bookings/<id>/` (own only else 404). Booking JSON: `{id, token_no, status, payment_status, description, created_at, session: {id, date, start_time, end_time, fee}, doctor: {id, name, specialization}, hospital: {id, name, latitude, longitude}, has_prescription: bool}`.
  - `POST /api/bookings/<id>/cancel/` → 200 booking; `POST /api/bookings/<id>/pay/` → 200 `{reference, amount, provider}`.
  - `GET /api/bookings/<id>/queue/` → `{token_no, current_token, ahead, eta_minutes, state}` (from `queue_status`). This endpoint is what Redis caches in v2 — keep it a single cheap query path.
  - Hospital dashboard `/dashboard/hospital/bookings/?date=` lists its doctors' bookings.

- [ ] **Step 1: Failing tests:** happy path book → pay → queue; patient A GET patient B's booking/queue/pay → 404 (Review Focus 3); double POST same session → second 409 `{"code": "already_booked"}`; full → 409 `session_full`; doctor JWT can't obtain token so test with force_authenticate doctor → 403; sessions endpoint hides past sessions and shows correct `seats_left` after a cancel.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(api): add patient booking, payment and queue endpoints`

### Task 3.6: Seed sessions/bookings + milestone close

- [ ] **Step 1:** Extend `seed_demo` with `_seed_sessions_and_bookings()`: for each doctor, sessions for today (08:00–22:00 split into two sessions so a demo works at any hour in IST), tomorrow and +2 days; bookings for today with a mix of paid/pending; `doctor@smartcare.test` has a today session with 6 bookings and `current_token=2`; `patient@smartcare.test` holds token 5 in it. Test: after seeding, `queue_status` for patient@'s booking is `waiting`, `ahead >= 1`.
- [ ] **Step 2:** Commit `feat(seed): add demo sessions and bookings`. **Step 3:** Milestone close → `03-booking-queue.md` (must include the concurrency story from Task 3.2 Step 5).

---

# Milestone 4 — Prescriptions, pharmacy requests, complaints, admin stats (branch `feat/m4-prescriptions-pharmacy`)

### Task 4.1: Prescriptions (doctor writes, booking completes)

**Files:**
- Create: `backend/prescriptions/{models,services,forms,views,urls}.py`, templates `dashboards/doctor/prescription_form.html`
- Test: `backend/prescriptions/tests/test_services.py`, `backend/prescriptions/tests/test_views.py`

**Interfaces:**
- Produces:
  - `Prescription`: `booking` (1:1, related `prescription`), `symptoms`, `diagnosis`, `notes` (blank), `created_at`. `PrescriptionItem`: `prescription` (FK, related `items`), `medicine`, `dosage`, `frequency`, `duration`.
  - `write_prescription(doctor: Doctor, booking: Booking, *, symptoms: str, diagnosis: str, notes: str = "", items: list[dict[str, str]]) -> Prescription` — own session's booking only (`NotAllowed`); booking `status` must be booked (`InvalidTransition`; cancelled/no_show/completed rejected); existing prescription → `AlreadyPrescribed` (409); `items` ≥ 1 (`NoItems`); in one transaction creates rows and sets `booking.status = completed`.
  - Doctor page `/dashboard/doctor/bookings/<id>/prescribe/` with an item formset (HTMX "add item" row).

- [ ] **Step 1: Failing tests:** happy path → booking completed with 2 items; second write → `AlreadyPrescribed`; other doctor → `NotAllowed`; cancelled booking → `InvalidTransition`; zero items → `NoItems`; view: formset with blank extra row ignored.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(prescriptions): let doctors write structured prescriptions`

### Task 4.2: Pharmacy requests (forward, price/accept, reject, pay, collected)

**Files:**
- Modify: `backend/pharmacy/models.py`, `backend/pharmacy/services.py`, `backend/payments/models.py` (+ migration), `backend/payments/services.py`
- Create: templates `dashboards/pharmacy/{home,request_detail}.html`, `backend/pharmacy/views.py` additions
- Test: `backend/pharmacy/tests/test_requests.py`

**Interfaces:**
- Produces:
  - `PharmacyRequest`: `prescription` (FK, related `pharmacy_requests`), `pharmacy` (FK, related `requests`), `amount` (null), `status` (default pending), `created_at`, `responded_at` (null), `paid_at` (null), `collected_at` (null). Partial unique: one request per prescription with status in (pending, accepted, paid).
  - `forward_prescription(patient: User, prescription: Prescription, pharmacy: Pharmacy) -> PharmacyRequest` — own prescription only (`NotAllowed`); `pharmacy.hospital` must equal the prescribing doctor's hospital (`WrongHospital`); an open request exists → `AlreadyForwarded` (409). Re-forward allowed after rejection.
  - `accept_request(pharmacy: Pharmacy, req: PharmacyRequest, amount: Decimal) -> PharmacyRequest` (pending only; `amount > 0` else `InvalidAmount`); `reject_request(pharmacy, req) -> PharmacyRequest` (pending only); `mark_paid_at_counter(pharmacy, req) -> Payment` (accepted only; creates Payment with `payer = patient`); `mark_collected(pharmacy, req) -> PharmacyRequest` (paid only).
  - `payments.services.pay_pharmacy_request(patient: User, req: PharmacyRequest) -> Payment` (accepted only; `AlreadyPaid`; sets `status=paid`, `paid_at`). `Payment.pharmacy_request` FK + CheckConstraint "exactly one of booking / pharmacy_request".
  - Pharmacy inbox `/dashboard/pharmacy/` shows only `pharmacy.requests` (other pharmacy's request pk → 404), with prescription items visible.

- [ ] **Step 1: Failing tests:** full flow forward → accept(₹250) → patient pays → collected; pharmacy at a different hospital → `WrongHospital`; forward twice → `AlreadyForwarded`; rejected then forward to the other pharmacy works; accept with 0 → `InvalidAmount`; pharmacy B views A's request → 404; pay twice → `AlreadyPaid`; Payment constraint rejects a row with both FKs (IntegrityError).
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(pharmacy): add prescription forwarding and pharmacy request flow`

### Task 4.3: Patient API for prescriptions and pharmacy requests

**Files:**
- Create: `backend/prescriptions/{api,serializers}.py`, `backend/pharmacy/api.py` additions
- Test: `backend/prescriptions/tests/test_api.py`, `backend/pharmacy/tests/test_api.py`

**Interfaces:**
- Produces (`[IsPatient]`, own-data querysets):
  - `GET /api/prescriptions/`, `GET /api/prescriptions/<id>/` → `{id, booking_id, created_at, doctor: {id, name, specialization}, hospital: {id, name}, symptoms, diagnosis, notes, items: [{medicine, dosage, frequency, duration}], requests: [{id, pharmacy: {id, name}, status, amount}]}`.
  - `POST /api/pharmacy-requests/` `{prescription, pharmacy}` → 201; `GET /api/pharmacy-requests/` and `/<id>/`: `{id, prescription_id, pharmacy: {id, name, phone}, status, amount, created_at, responded_at, paid_at, collected_at}`; `POST /api/pharmacy-requests/<id>/pay/` → `{reference, amount, provider}`.

- [ ] **Step 1: Failing tests:** patient B → A's prescription/request → 404 (Review Focus 3); forward via API to wrong-hospital pharmacy → 400 `wrong_hospital`; pay before accepted → 400 `invalid_transition`.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(api): add prescription and pharmacy request endpoints`

### Task 4.4: Complaints (any role files, admin replies)

**Files:**
- Create: `backend/complaints/{models,services,forms,views,api,serializers,urls}.py`, templates `dashboards/complaints/{list,form}.html`, `dashboards/admin/complaints.html`
- Test: `backend/complaints/tests/test_complaints.py`

**Interfaces:**
- Produces:
  - `Complaint`: `sender` (FK User), `role` (snapshot of `sender.role`), `message` (max 2000), `reply` (blank), `created_at`, `replied_at` (null).
  - `file_complaint(sender: User, message: str) -> Complaint` (strip; empty → `EmptyMessage`); `reply_to_complaint(admin: User, complaint: Complaint, reply: str) -> Complaint` (admin only; empty → `EmptyMessage`; already replied → `AlreadyReplied`; console email to sender).
  - Staff dashboards: `/dashboard/complaints/` (own list + form) for hospital/doctor/pharmacy; `/dashboard/admin/complaints/` (all, unreplied first, reply form). API: `GET/POST /api/complaints/` (patient, own only).

- [ ] **Step 1: Failing tests:** each staff role and patient API can file; role snapshot survives a later role change; non-admin reply → `NotAllowed`; whitespace message → error; patient sees only own complaints.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(complaints): add complaints with admin replies`

### Task 4.5: Admin system stats

**Files:**
- Create: `backend/dashboards/stats.py`, template `dashboards/admin/home.html` (modify), `backend/static/vendor/chart.umd.min.js` (Chart.js 4.x pinned)
- Test: `backend/dashboards/tests/test_stats.py`

**Interfaces:**
- Produces: `system_stats() -> dict[str, int]` keys `hospitals_approved, hospitals_pending, doctors, pharmacies, patients, bookings_today, open_complaints`; `bookings_per_day(*, days: int = 14, today: date) -> list[tuple[date, int]]` — exactly `days` entries, oldest first, zero-filled, counts non-cancelled bookings by `session.date`. Admin home renders counts as cards and the series as a Chart.js bar chart (data via `json_script`).

- [ ] **Step 1: Failing tests:** zero-fill (bookings only on 2 of 14 days → 14 tuples, 12 zeros); cancelled excluded; counts match factories.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(dashboards): add admin system stats and bookings chart`

### Task 4.6: Seed prescriptions/requests/complaints + milestone close

- [ ] **Step 1:** Extend `seed_demo`: past-day completed bookings with prescriptions for `patient@`, one pharmacy request in each status, 4 complaints (2 replied). Test: patient@ has ≥ 2 prescriptions and ≥ 1 accepted request; pharmacy@ inbox has a pending request.
- [ ] **Step 2:** Commit `feat(seed): add demo prescriptions, pharmacy requests and complaints`. **Step 3:** Milestone close → `04-prescriptions-pharmacy.md`.

---

# Milestone 5 — AI doctor suggestion (branch `feat/m5-ai-suggest`)

### Task 5.1: `ml/` project, dataset and specialisation mapping

**Files:**
- Create: `ml/pyproject.toml`, `ml/uv.lock`, `ml/scripts/download_data.py`, `ml/data/disease_to_specialization.csv`, `ml/smartcare_ml/{__init__,data}.py`, `ml/README.md` (stub)
- Test: `ml/tests/test_data.py`

**Interfaces:**
- Produces:
  - Dataset: preferred `gretelai/symptom_to_diagnosis` on Hugging Face (free-text patient symptom descriptions → diagnosis, with train/test splits). **Before using it, open the dataset card and confirm the licence permits use and redistribution; record licence, URL, citation and SHA-256 of downloaded files in `ml/README.md`.** If the licence is unsuitable, stop and ask Marwan (don't silently switch).
  - `download_data.py` fetches over HTTPS into `ml/data/raw/` (git-ignored) and verifies the SHA-256 values hard-coded in the script.
  - `disease_to_specialization.csv` columns `disease,specialization,reason` — every dataset label mapped to one of the 12 canonical names (copy the list from Global Constraints into `smartcare_ml/data.py` as `CANONICAL_SPECIALIZATIONS`).
  - `load_split(split: Literal["train","test"]) -> tuple[list[str], list[str]]` returns `(texts, specialization_labels)` after mapping.

- [ ] **Step 1: Failing tests:** every disease in both raw splits appears in the CSV; every CSV specialisation ∈ `CANONICAL_SPECIALIZATIONS`; `CANONICAL_SPECIALIZATIONS` equals the backend data-migration list (test reads `backend/doctors/migrations/0002_seed_specializations.py`'s exported `NAMES` constant — define it there as a module-level list).
- [ ] **Step 2–4:** fail → implement → pass (`cd ml && uv run pytest -v`). **Step 5: Commit** `feat(ml): add dataset download and disease-to-specialisation mapping`

### Task 5.2: Train, evaluate, model card

**Files:**
- Create: `ml/smartcare_ml/train.py`, `ml/notebook.ipynb`, `backend/ai_suggest/model/specialization_clf.joblib`, `backend/ai_suggest/model/metadata.json`, `ml/reports/{metrics.json,confusion_matrix.png}`
- Modify: `ml/README.md`
- Test: `ml/tests/test_train.py`

**Interfaces:**
- Produces:
  - `python -m smartcare_ml.train --out ../backend/ai_suggest/model` builds `Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)), ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))])`, fits on train split, evaluates on the held-out test split, writes the joblib artefact and `metadata.json` = `{model_version: "1.0.0", trained_at, sklearn_version, dataset, labels, test_accuracy, test_macro_f1, n_train, n_test}`, plus `ml/reports/metrics.json` and the confusion-matrix PNG.
  - `scikit-learn` pinned to the **same exact version** in `ml/pyproject.toml` and `backend/pyproject.toml`.
  - `ml/README.md` model card: dataset + licence + citation, mapping table, real test accuracy and macro-F1 (whatever they are — no rounding up), confusion matrix, limitations (small dataset, English only, not medical advice), how to retrain.

- [ ] **Step 1: Failing test:** `test_train_smoke` trains on a 40-row synthetic fixture in `tmp_path` and asserts the artefact loads, `predict_proba` rows sum to 1, `metadata.json` has every key above.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5:** Run the real training; paste the printed metrics into the model card. **Step 6: Commit** `feat(ml): train symptom-to-specialisation classifier and add model card`

### Task 5.3: Predictor in Django

**Files:**
- Create: `backend/ai_suggest/{__init__,apps,predictor}.py`
- Test: `backend/ai_suggest/tests/test_predictor.py`

**Interfaces:**
- Produces:
  - `CONFIDENCE_THRESHOLD = 0.40`; `MAX_SYMPTOM_CHARS = 1000`.
  - `@dataclass(frozen=True) Suggestion: name: str; probability: float` and `SuggestionResult: suggestions: list[Suggestion]; confident: bool; model_version: str`.
  - `get_model()` — `functools.cache`d `joblib.load` of `settings.AI_MODEL_PATH` (default `BASE_DIR / "ai_suggest/model/specialization_clf.joblib"`); `AiSuggestConfig.ready()` warms it unless `settings.AI_WARM_ON_STARTUP` is False (False in tests). Missing artefact → `ModelUnavailable(DomainError, status=503)`.
  - `suggest_specializations(text: str, k: int = 3) -> SuggestionResult` — top-k by probability, rounded to 3 dp; `confident = top1 >= CONFIDENCE_THRESHOLD`.
  - Warn at load if `metadata.json["sklearn_version"] != sklearn.__version__`.

- [ ] **Step 1: Failing tests:** returns 3 suggestions, descending, each name canonical; a clearly dermatological sentence ("itchy red scaly patches on my elbows and scalp") → top-1 Dermatology (use the real artefact); "asdf qwer zxcv" → `confident is False`; missing path → `ModelUnavailable`.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(ai): load classifier and return top-3 specialisation suggestions`

### Task 5.4: Explainable doctor ranking

**Files:**
- Create: `backend/ai_suggest/ranking.py`
- Test: `backend/ai_suggest/tests/test_ranking.py`

**Interfaces:**
- Produces:
  - `RANKING_WEIGHTS = {"distance": 0.5, "soonest": 0.3, "fee": 0.2}` (documented in a docstring and in `docs/api.md`).
  - `@dataclass(frozen=True) RankedDoctor: doctor: Doctor; score: float; distance_km: float | None; next_session: ConsultingSession | None`.
  - `rank_doctors(specialization_names: list[str], *, lat: float | None, lng: float | None, now: datetime, limit: int = 10) -> list[RankedDoctor]`. Candidates = `visible_to_patients()` with specialisation in names. Per factor compute a value where lower is better — distance (km), hours until next non-full, non-past session, fee of that session — min-max normalise across candidates to [0,1] (all equal → 0), `score = Σ w·(1 − norm)`. Without lat/lng, drop distance and renormalise the remaining weights to sum 1. Doctors with no bookable session get norm 1 for soonest and fee (they sort last but still appear). Ties → name ascending.

- [ ] **Step 1: Failing tests:** closer doctor beats farther when other factors equal; without location the distance factor is ignored (weights 0.6/0.4); doctor with no sessions ranks last; doctors of pending hospitals excluded; `limit` respected.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(ai): add explainable doctor ranking`

### Task 5.5: Suggestion API + ADR 0009 + milestone close

**Files:**
- Create: `backend/ai_suggest/{api,serializers}.py`, `docs/adr/0009-classifier-over-bert-claim.md`
- Test: `backend/ai_suggest/tests/test_api.py`

**Interfaces:**
- Produces: `POST /api/ai/suggest/` (`[IsPatient]`) body `{symptoms: str, lat?: float, lng?: float}` → 200 `{suggestions: [{specialization_id, name, probability}], confident: bool, message: str | null, doctors: [{id, name, specialization, hospital: {id, name}, distance_km, next_session: {id, date, start_time, fee} | null, score}], disclaimer: str, model_version: str}`. When `confident` is false: `message` = the low-confidence copy and doctors are ranked for `["General Physician"]`; else ranked for the top-1 suggestion's specialisation. `disclaimer` = the exact Global Constraints copy.

- [ ] **Step 1: Failing tests (Review Focus 5):** `""` and `"   "` → 400; 1001 chars → 400; `"asdf qwer"` → 200, `confident: false`, exact message copy, doctors all General Physician; dermatology sentence → doctors all Dermatology; disclaimer exact; unauthenticated → 401.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5:** Commit `feat(api): add AI doctor suggestion endpoint with disclaimer`. **Step 6:** README "AI suggestion" section with real accuracy + link to model card + disclaimer. Milestone close → `05-ai-suggest.md`.

---

# Milestone 6 — Flutter patient app (branch `feat/m6-mobile`)

All screens call only the endpoints defined in Milestones 2–5. Models are plain Dart classes with hand-written
`fromJson` (no code generation, so they're explainable). Verification: `cd mobile && flutter analyze` → `No issues
found!`; `flutter test` → `All tests passed!`.

### Task 6.1: Scaffold, API client, token storage, CI job

**Files:**
- Create: `mobile/` via `flutter create --org io.github.killaadi --project-name smartcare_patient --platforms android mobile`; `mobile/lib/core/{config,api_client,token_store,api_error}.dart`, `mobile/analysis_options.yaml` (flutter_lints + `prefer_const_constructors`, `always_declare_return_types`)
- Modify: `.github/workflows/ci.yml` (job `mobile`: `subosito/flutter-action` stable pinned, `flutter pub get`, `dart format --set-exit-if-changed lib test`, `flutter analyze`, `flutter test`), `.pre-commit-config.yaml` (local `dart format` hook on `^mobile/`); after this PR merges, add `mobile` to the required status checks on `main`
- Test: `mobile/test/core/api_client_test.dart`

**Interfaces:**
- Produces:
  - `const apiBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');`
  - `abstract class TokenStore { Future<String?> access(); Future<String?> refresh(); Future<void> save(String access, String refresh); Future<void> clear(); }` + `SecureTokenStore` (flutter_secure_storage) + `MemoryTokenStore` (tests).
  - `Dio buildApiClient(TokenStore store, {HttpClientAdapter? adapter, void Function()? onLoggedOut})` — adds `Authorization: Bearer`; on 401 tries `POST /api/auth/token/refresh/` once (single-flight), retries the original request, and on refresh failure clears the store and calls `onLoggedOut`.
  - `class ApiError implements Exception { final int? status; final String code; final String message; }` + `ApiError.fromDio(DioException)` reading `{detail, code}`; network failure → message "Can't reach SmartCare. Check your connection."
  - Riverpod providers: `tokenStoreProvider`, `dioProvider`.

- [ ] **Step 1: Failing tests** using a fake `HttpClientAdapter`: bearer header attached; 401 → refresh → retry succeeds and new tokens saved; refresh 401 → store cleared and `onLoggedOut` called once even with two concurrent 401s; `ApiError.fromDio` parses `{"detail": "x", "code": "session_full"}`.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(mobile): scaffold Flutter app with authenticated API client`

### Task 6.2: Auth screens and router

**Files:**
- Create: `mobile/lib/app.dart`, `mobile/lib/features/auth/{auth_repository,auth_controller,login_screen,register_screen}.dart`, `mobile/lib/features/home/home_screen.dart`
- Test: `mobile/test/features/auth/login_screen_test.dart`

**Interfaces:**
- Produces: `go_router` routes `/login`, `/register`, `/` (home: tiles Symptom check, Find hospitals, My bookings, Prescriptions, Complaints), `/symptoms`, `/hospitals`, `/hospitals/:id`, `/doctors/:id/sessions`, `/bookings`, `/prescriptions`, `/prescriptions/:id`, `/complaints`. Redirect: no token → `/login`. `AuthRepository { login(email, password); register(RegisterData); logout(); }`. Login shows the server's `detail` on 401 (so staff see the "This app is for patients…" copy).
- [ ] **Step 1: Failing test:** login with a fake repository throwing `ApiError(401, …, 'This app is for patients. Staff should use the web dashboard.')` shows that text; success navigates to home.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(mobile): add login, registration and routing`

### Task 6.3: Symptom check screen

**Files:**
- Create: `mobile/lib/features/symptoms/{ai_repository,symptom_check_screen,suggestion_view}.dart`, `mobile/lib/models/suggestion.dart`
- Test: `mobile/test/features/symptoms/symptom_check_screen_test.dart`

**Interfaces:**
- Produces: `AiRepository.suggest(String symptoms, {double? lat, double? lng}) -> Future<SuggestionResponse>`; screen: multiline field (max 1000, counter), "Suggest a doctor" button disabled while empty/whitespace, disclaimer shown **above** the button at all times; results show top-3 with percentage bars, the `message` banner when not confident, and the ranked doctor list (tap → `/doctors/:id/sessions`).
- [ ] **Step 1: Failing widget tests:** disclaimer copy visible before any input; button disabled for "   "; with fake response `confident: false` → "We're not sure — consider a General Physician." banner and doctors listed; confident response → three bars with "Dermatology 82%" style labels.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(mobile): add symptom check with AI suggestions`

### Task 6.4: Hospitals nearby, directions, sessions, booking and payment

**Files:**
- Create: `mobile/lib/features/hospitals/{hospital_repository,hospital_list_screen,hospital_detail_screen}.dart`, `mobile/lib/features/doctors/doctor_sessions_screen.dart`, `mobile/lib/features/bookings/{booking_repository,book_sheet}.dart`, `mobile/lib/core/{location,directions}.dart`, `mobile/lib/models/{hospital,doctor,session,booking}.dart`
- Modify: `mobile/android/app/src/main/AndroidManifest.xml` (INTERNET, ACCESS_COARSE_LOCATION, ACCESS_FINE_LOCATION, `<queries>` for https VIEW intents), `mobile/android/app/src/debug/AndroidManifest.xml` (`usesCleartextTraffic="true"` — debug builds only)
- Test: `mobile/test/core/directions_test.dart`, `mobile/test/features/bookings/book_sheet_test.dart`

**Interfaces:**
- Produces:
  - `Uri directionsUri(double lat, double lng)` = `https://www.google.com/maps/dir/?api=1&destination=<lat>,<lng>`; opened with `url_launcher` `LaunchMode.externalApplication`.
  - `Future<Position?> currentPositionOrNull()` — asks permission; denied/off → `null` and the list falls back to name order with a "Turn on location to sort by distance" hint.
  - Hospital list: search field + "Nearby" toggle; rows show `distance_km` and "~N min (straight-line estimate)".
  - Book sheet: session list with seats left → description → "Book" → shows token → "Pay ₹<fee>" with the simulated-payment copy under the button. Errors show `ApiError.message`.
- [ ] **Step 1: Failing tests:** `directionsUri(10.5276, 76.2144).toString()` equals the expected URL; book sheet shows the simulated-payment copy and, on fake `already_booked` error, the server message; button disabled while request in flight (double-tap guard, Review Focus 1).
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(mobile): add hospitals nearby, directions and booking with simulated payment`

### Task 6.5: My Bookings with live queue

**Files:**
- Create: `mobile/lib/features/bookings/{my_bookings_screen,queue_card,queue_controller}.dart`, `mobile/lib/models/queue_status.dart`
- Test: `mobile/test/features/bookings/my_bookings_screen_test.dart`

**Interfaces:**
- Produces: `String queueLine(QueueStatus q)` → waiting: `"Your token ${q.tokenNo} · Now serving ${q.currentToken} · ~${q.etaMinutes} min"`; now_serving: `"It's your turn — token ${q.tokenNo}"`; done: `"Consultation finished"`; cancelled: `"Cancelled"`. Queue controller polls `/api/bookings/<id>/queue/` every 15 s only while the screen is visible and the app is resumed (`AppLifecycleListener`), stops on dispose; pull-to-refresh reloads bookings and queues. Each upcoming booking card has Pay (if pending), Cancel (if booked), Directions.
- [ ] **Step 1: Failing widget tests:** fake queue `{token_no: 7, current_token: 4, eta_minutes: 30, state: waiting}` renders `Your token 7 · Now serving 4 · ~30 min`; after advancing fake time 15 s with a changed fake response, text updates; timer cancelled after the widget is disposed (no pending timers at test end).
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(mobile): add My Bookings with live token queue`

### Task 6.6: Prescriptions, forward to pharmacy, complaints

**Files:**
- Create: `mobile/lib/features/prescriptions/{prescription_repository,prescription_list_screen,prescription_detail_screen,forward_sheet}.dart`, `mobile/lib/features/complaints/{complaint_repository,complaints_screen}.dart`, `mobile/lib/models/{prescription,pharmacy_request,complaint}.dart`
- Test: `mobile/test/features/prescriptions/prescription_detail_screen_test.dart`

**Interfaces:**
- Produces: detail shows items table and request history; "Send to a pharmacy" lists `/api/hospitals/<hospital_id>/pharmacies/`; accepted request shows "Pay ₹<amount>" with the simulated copy; complaints screen lists own complaints with reply and a form.
- [ ] **Step 1: Failing test:** accepted request renders Pay with amount; pending shows "Waiting for the pharmacy"; rejected shows "Rejected — you can send it to another pharmacy" and the forward button is enabled again.
- [ ] **Step 2–4:** fail → implement → pass. **Step 5: Commit** `feat(mobile): add prescriptions, pharmacy forwarding and complaints`

### Task 6.7: End-to-end on emulator, ADR 0010, milestone close

**Files:**
- Create: `docs/adr/0010-maps-deep-links-now-azure-maps-later.md`, `mobile/README.md` (run instructions incl. `--dart-define=API_BASE_URL=http://10.0.2.2:8000` and LAN-IP note)
- [ ] **Step 1:** `docker compose up -d && docker compose exec web python manage.py seed_demo`; start emulator `Pixel_API_36`; `flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000`. Walk the core flow (spec §7 steps 1–5) as `patient@smartcare.test` with `doctor@`/`pharmacy@` in the browser. Capture screenshots `docs/screenshots/m06-*.png`. Any bug found → failing test first, then fix.
- [ ] **Step 2:** Commit `docs(mobile): add run instructions and maps ADR`. **Step 3:** Milestone close → `06-mobile.md`.

---

# Milestone 7 — Docs pass, release `v1.0-fyp` (branch `feat/m7-docs-release`)

### Task 7.1: Architecture, ERD, API, original-FYP docs

**Files:**
- Create: `docs/architecture.md` (Mermaid container diagram: phone → DRF, browser → dashboards, Django → Postgres/media/model artefact), `docs/erd.md` (Mermaid `erDiagram` generated from the real models — cross-check with `python manage.py inspectdb`-free manual list against `models.py`), `docs/api.md` (endpoint table, error format `{detail, code}`, ranking weights, link to `/api/docs/`), `docs/original-fyp.md`
- [ ] **Step 1:** `original-fyp.md` needs the original report. **Ask Marwan for the PDF (or his summary) before writing it**; summarise features and stack, then a "What changed and why" table (MySQL→PostgreSQL, BERT 92% claim → TF-IDF+LR with real accuracy, AWS→Azure, MFA dropped, Google Maps API → deep links / Azure Maps). No screenshots from the report (classmates' names).
- [ ] **Step 2:** `pre-commit run --all-files` passes; Mermaid renders in GitHub preview. Commit `docs: add architecture, ERD, API and original FYP summary`.

### Task 7.2: Evidence — screenshots and demo video

- [ ] **Step 1:** Screenshot set in `docs/screenshots/`: each dashboard role home, approval flow, doctor queue, prescription form, pharmacy inbox, admin stats, and the app's symptom check, hospital list, booking, My Bookings queue, prescription. All from seed data only.
- [ ] **Step 2:** Marwan records a ≤ 3-minute demo of the core flow; upload as an unlisted video or a GIF in `docs/demo/` (≤ 10 MB); link from README.
- [ ] **Step 3:** Commit `docs: add screenshots and demo`.

### Task 7.3: README final, CHANGELOG, APK, tag, release

**Files:**
- Modify: `README.md`, `CHANGELOG.md`, `mobile/android/app/build.gradle(.kts)` (release signing from git-ignored `key.properties`)
- [ ] **Step 1:** README in spec §8 order, including "What I improved since uni" (honest list incl. dropped claims), "How this was built" (FYP concept and report by Marwan; rebuild AI-assisted, reviewed and understood by Marwan), testing/CI section with badges and the coverage figure CI actually reports, ADR links, AI disclaimer, "Payments are simulated". Every claim must map to a file or test — check each sentence.
- [ ] **Step 2:** CHANGELOG `## [1.0.0-fyp] - <date>` grouped by Added. Commit `docs: finalise README and changelog for v1.0-fyp`.
- [ ] **Step 3:** Generate a release keystore locally (`keytool -genkey -v -keystore ~/smartcare-release.jks ...`), `key.properties` git-ignored (verify with `git check-ignore -v mobile/android/key.properties`); `flutter build apk --release --dart-define=API_BASE_URL=http://10.0.2.2:8000` → Expected: `✓ Built build/app/outputs/flutter-apk/app-release.apk`. Commit the gradle signing config only: `build(mobile): add release signing from local key.properties`.
- [ ] **Step 4:** Milestone close → `07-docs-release.md` and PR.
- [ ] **Step 5: After Marwan approves and the PR is merged:** `git checkout main && git pull && git tag -a v1.0-fyp -m "SmartCare FYP rebuilt" && git push origin v1.0-fyp && gh release create v1.0-fyp mobile/build/app/outputs/flutter-apk/app-release.apk --title "v1.0-fyp — SmartCare rebuilt" --notes-file <release notes from CHANGELOG>`. Expected: release page lists the APK. Tell Marwan he can now create the Azure free account (v2 plan is written separately).
