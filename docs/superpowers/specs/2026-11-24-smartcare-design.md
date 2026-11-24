# SmartCare — Portfolio Rebuild & Azure Migration: Design

Date: 2026-11-24
Status: Draft for approval (updated after builder review)

## 1. Intent and the why

SmartCare was the owner's BSc Computer Science final-year project (University of Calicut, 2025–26): a hospital
management system connecting admins, hospitals, doctors, pharmacies and patients, with symptom-based doctor
suggestion, appointment booking with token numbers, digital prescriptions forwarded to pharmacies, complaints, and
map directions. **The original source code is lost.** Only the project report (PDF) survives.

The owner is a recent graduate applying for **cloud developer roles, Azure preferred**. They want one public GitHub
repo, "everything under one roof", that serves as evidence when an interviewer says *"tell me about your final-year
project"*, and supports a second story: *"…and then I migrated it to Azure."*

The repo tells a two-chapter story, visible in git history and tags:

- **Chapter 1 — `v1.0-fyp`:** SmartCare rebuilt properly. Django monolith + Flutter patient app, runs locally with
  one `docker compose up`.
- **Chapter 2 — `v2.0-azure`:** the same app migrated to Azure the way a real team would: infrastructure as code,
  containers on Azure Container Apps, managed services, CI/CD, monitoring, and a written migration log.

The project also doubles as hands-on prep for **AZ-900** (first) and **AI-200: Developing AI Cloud Solutions on
Azure** (target, the replacement for the retired AZ-204). Azure service choices in chapter 2 are deliberately mapped
to AI-200's four skill areas (containers; AI solutions with Azure data services; connecting to Azure services;
security/monitoring/troubleshooting).

## 2. Audience

- **Primary:** recruiters and interviewers for junior cloud/Azure developer roles. They will spend minutes, not
  hours: README, diagrams, screenshots/demo video, CI badges, commit history, and maybe one or two files.
- **Secondary:** the owner, who must be able to explain every part in an interview. Simplicity and explainability
  beat cleverness everywhere.

## 3. Goals, non-goals, anti-goals

### Goals
1. Faithful to the original FYP concept (same five roles, same core flows, same stack family: Django + Flutter),
   but genuinely better built.
2. Professional engineering evidence: clean git history built feature-by-feature, tests, CI, linting, Docker,
   API docs, architecture/ER diagrams, ADRs, CHANGELOG, tagged releases.
3. A credible, documented Azure migration with Bicep, deployable and destroyable on demand.
4. Honest claims only. Every feature or metric in the README is real and reproducible.

### Non-goals
- A permanently running live app. (Deploy, capture evidence, destroy; redeploy for an interview if needed.)
- Real payments, real SMS, real medical accuracy, regulatory compliance (HIPAA etc.).
- Telemedicine/video, inventory management, multi-factor auth, microservices, Kubernetes.
- Feature parity with every claim in the original report (BERT 92% accuracy, AWS, MFA/TOTP etc. are dropped).

### Anti-goals (would make it a failure even if it works)
- Claims in the README that the code doesn't back up.
- Any real person's data (the original screenshots contained classmates' names) or real hospital names/brands.
- Complexity the owner can't explain in two minutes (e.g. AKS, service mesh, event sourcing).
- A surprise Azure bill.
- Secrets committed to git.

## 4. Constraints

- Solo developer, recent graduate. Budget ≈ free tier / free credits; idle cost must be near zero.
- Public repo: no secrets, no real personal data, licence included (MIT — builder's call).
- Must run locally with Docker only (no local Python/Flutter install needed to run the backend + dashboards).
- Region for Azure resources: UK South (owner is in the UK) unless a service is unavailable there.

## 5. Approaches considered

### Application shape
| Option | Trade-off | Decision |
|---|---|---|
| **A. Django serves web dashboards (templates + Bootstrap + HTMX); DRF API serves the Flutter patient app** | Closest to the original; fewest moving parts; easy to explain. Dashboards are server-rendered rather than SPA. | **Chosen by owner** |
| B. Django API-only; one Flutter codebase for mobile + Flutter-web dashboards | Heavy Flutter showcase; Flutter web is weak for admin tables; drifts from original; more work. | Rejected |
| C. Django API + separate React dashboard + Flutter app | Third technology not in the original; weakens "this is my FYP". | Rejected |

### Azure hosting
| Option | Trade-off | Decision |
|---|---|---|
| **Azure Container Apps** | Container-centric (matches AI-200's largest domain), scale-to-zero, simple to explain. | **Chosen by owner** |
| Azure App Service (code deploy) | Simplest, but "I uploaded my code" is a thin migration story. | Rejected |
| AKS | Expensive and over-engineered for a solo five-role app; hard to justify in interview. | Rejected |

### Database
**PostgreSQL from v1** (chosen by owner). The original report lists PostgreSQL as an option; it enables `pgvector`
for the AI feature and maps to Azure Database for PostgreSQL Flexible Server in v2. This is a documented deviation
from the original MySQL build (record it in an ADR).

## 6. Decided by the owner

- Azure is the cloud; AZ-900 → AI-200 is the certification path.
- Azure Container Apps for hosting.
- App shape A: Django (API + web dashboards) + Flutter patient app.
- PostgreSQL from v1 onwards.
- One monorepo containing everything; two-chapter story with `v1.0-fyp` and `v2.0-azure` tags.
- No permanently live app; evidence (screenshots, demo video, pipeline runs) is what's showcased.
- **Bicep** for infrastructure as code (not Terraform).
- **Claude builds most of the code**; the owner reviews each milestone (see §8a).
- **No hard deadline, but as soon as possible**: get to a showable `v1.0-fyp` fast, keep v1 lean.
- **No Azure account yet; free tier only.** Account is created at the start of v2 (see §9 cost policy).

## 7. Product scope (v1.0-fyp)

### Roles and where they work
| Role | Client | Capabilities |
|---|---|---|
| Admin | Web dashboard | Approve/reject hospital registrations; view users; reply to complaints; system stats (counts, bookings per day chart) |
| Hospital | Web dashboard | Self-register (pending approval) with licence proof upload and map location; manage its doctors and its pharmacy accounts; view its bookings |
| Doctor | Web dashboard | Create consulting sessions (date, start/end, fee, capacity); today's queue; **"Call next"** advances the current token; write prescription for a booking; mark consultation complete |
| Pharmacy | Web dashboard | Inbox of prescription requests; set amount; accept/reject; mark paid/collected |
| Patient | Flutter app (Android primary) | Register/login; symptom check → suggested specialisation + ranked doctors; find hospitals (search, sort by nearby); book a session; pay (simulated); **My Bookings with live token / current token / ETA**; directions; view prescriptions; forward a prescription to a pharmacy and track status; file complaints |

Any role can file a complaint; admin replies. (Patients file from the app; staff roles from their dashboard.)

### Core flow
1. Patient enters symptoms → AI suggests a specialisation (with confidence) → ranked list of doctors.
2. Patient picks a consulting session → booking created with an **atomic, sequential token number** for that
   session → payment (simulated) marks it paid.
3. On the day, doctor clicks "Call next" → session's `current_token` increments → patient app shows
   "Your token 7 · Now serving 4 · ~24 min".
4. Doctor writes the prescription (structured items) → booking completed.
5. Patient forwards prescription to a pharmacy at that hospital → pharmacy prices it, accepts → patient pays
   (simulated) → status paid.

### Domain model (improved from the report's schema)
- `User` — custom Django user with `role` ∈ {admin, hospital, doctor, pharmacy, patient}. Email login.
- `Hospital` — user (1:1), name, place, phone, email, photo, licence_proof, latitude, longitude,
  `approval_status` ∈ {pending, approved, rejected}.
- `Doctor` — user (1:1), hospital (FK), name, specialization (FK to `Specialization`), qualification,
  experience_years, gender, photo.
- `Specialization` — name, description (also used by the AI feature).
- `Pharmacy` — user (1:1), hospital (FK), name, phone, email.
- `PatientProfile` — user (1:1), name, phone, age/DOB, gender, place.
- `ConsultingSession` (report: "Consulting Time") — doctor, date, start_time, end_time, fee, capacity,
  `current_token` (int, default 0), avg_consult_minutes (default 10).
- `Booking` — session, patient, description, `token_no` (unique per session), `payment_status` ∈ {pending, paid},
  `status` ∈ {booked, cancelled, completed, no_show}, created_at.
- `Prescription` — booking (1:1), symptoms, diagnosis, notes; `PrescriptionItem` — medicine, dosage, frequency,
  duration.
- `PharmacyRequest` — prescription, pharmacy, amount, `status` ∈ {pending, accepted, rejected, paid}, timestamps.
- `Payment` — generic record (booking or pharmacy request), amount, provider="simulated", reference, created_at.
- `Complaint` — sender (user), role snapshot, message, reply, created_at, replied_at.

Rules (enforced in the service layer, tested):
- Only approved hospitals' doctors are visible to patients.
- Token assignment uses a DB transaction with `select_for_update` on the session; bookings rejected when capacity
  is full or the session is in the past.
- A booking can only get one prescription, only by its own doctor.
- Pharmacy can only see requests addressed to it; patient only sees their own data (object-level permissions).
- ETA = (token_no − current_token) × avg_consult_minutes; shown as "~N min", never as a promise.

### AI doctor suggestion (honest version)
- `ml/`: a notebook + training script for a **TF-IDF + logistic regression** (or similar scikit-learn) classifier
  mapping free-text symptoms → specialisation, trained on a public, licence-compatible symptom→disease dataset with
  diseases mapped to ~10–15 specialisations (mapping table committed). Report real held-out accuracy and a confusion
  matrix in `ml/README.md`. Model artefact versioned and loaded by Django at startup.
- Returns top-3 specialisations with probabilities; below a confidence threshold the app says "we're not sure —
  consider a General Physician".
- Doctor ranking (explainable): filter by suggested specialisation → score by distance (if location given),
  soonest available session, fee. Weights live in one config dict and are documented.
- Prominent disclaimer: not medical advice.
- v2 adds a **pgvector** path: specialisation descriptions + symptom text embedded and searched by vector
  similarity in Azure Database for PostgreSQL (maps to AI-200's "AI solutions using Azure data services" domain).
  Embedding source is builder's call (prefer a small local sentence-transformers model to avoid Azure OpenAI
  cost/access issues); both paths compared in `ml/README.md`.

### Maps and location
- "Sort by nearby": haversine distance from the phone's GPS to hospital lat/lng (no API key).
- "Directions": opens Google Maps / platform maps via a deep link to the hospital coordinates (no API key).
- v1 travel time: straight-line estimate labelled as such. v2: real travel time via **Azure Maps Route API**
  (key/identity in Key Vault). Original used Google Maps API; the switch is an ADR.

### Payments and notifications
- Payments are **simulated** (a "Pay" action creates a `Payment` and flips status). Clearly labelled in UI and
  README. Interface designed so a real gateway (e.g. Stripe test mode) could be swapped in; not built.
- v1 notifications: in-app status + Django console email backend.
- v2: booking/queue events published to **Azure Service Bus**; an **Azure Function (Python)** consumes them and
  sends email (provider is builder's call, e.g. Azure Communication Services email) or logs if unconfigured.

### Seed data
- `python manage.py seed_demo` creates fictional hospitals (fictional names, Kerala/Thrissur-flavoured places to
  match the original), doctors, pharmacies, patients, sessions, bookings and prescriptions, plus one known login per
  role documented in the README. Uses Faker; deterministic seed.

## 8. Technical design (v1.0-fyp)

### Repo layout
```
smartcare/
├── backend/            Django project (apps: accounts, hospitals, doctors, bookings, prescriptions,
│                       pharmacy, complaints, ai_suggest, dashboards), tests, Dockerfile
├── mobile/             Flutter patient app, tests
├── ml/                 notebook, training script, dataset notes, model card, evaluation
├── infra/              (v2) Bicep (starts from the existing main.bicep)
├── functions/          (v2) Azure Function app
├── docs/
│   ├── architecture.md, erd.md (Mermaid), api.md (links to OpenAPI)
│   ├── adr/            Architecture Decision Records
│   ├── migration/      (v2) migration log, before/after diagrams, costs, incidents
│   ├── original-fyp.md summary of the original report and what changed
│   ├── screenshots/, demo/ (GIF/video links)
│   └── superpowers/    specs and plans
├── .github/workflows/  CI (and v2 CD)
├── docker-compose.yml
├── CHANGELOG.md, LICENSE, README.md
```

### Backend (builder's calls unless stated)
- Python 3.12, Django 5.x LTS-track, DRF, `djangorestframework-simplejwt` (patient app),
  Django session auth (dashboards), `drf-spectacular` (OpenAPI + Swagger UI at `/api/docs/`).
- Dashboards: Django templates + Bootstrap 5 + HTMX (queue view auto-refreshes via HTMX polling).
- Business logic in small service modules (`services.py`) rather than views, so it's testable and explainable.
- Role-based access: per-role mixins/decorators for dashboards, DRF permission classes for the API.
- Settings via environment variables (`django-environ`); `.env.example` committed, `.env` git-ignored.
- Media: local filesystem in v1 via `django-storages`-compatible abstraction so v2 swaps to Blob Storage by config.
- No Redis in v1 (keeps v1 lean for speed). The live queue reads `current_token` from PostgreSQL. Redis is
  introduced in v2 as a cache for the queue endpoint, which also gives the migration log a "measured before/after".

### Flutter app (builder's calls)
- Flutter stable, Dart 3; Riverpod for state, `dio` for HTTP, `flutter_secure_storage` for JWTs,
  `go_router` for navigation, `geolocator`, `url_launcher` for directions.
- API base URL configurable at build time (`--dart-define`), so the same app points at local or Azure.
- My Bookings polls the queue endpoint (e.g. every 15 s while visible) and supports pull-to-refresh.
- Android is the primary target; iOS not required. A release APK attached to GitHub Releases.

### Quality and evidence
- Backend: pytest + pytest-django + factory_boy; coverage ≥ 80% on services/permissions; key flows covered
  (token atomicity under concurrency, permissions per role, pharmacy flow).
- Flutter: `flutter analyze` clean; widget tests for the two most important screens (My Bookings, symptom check)
  in v1; more can follow.
- Lint/format: ruff (+ ruff format) for Python, `dart format`; pre-commit hooks.
- CI (GitHub Actions): backend lint+tests against a Postgres service container; Flutter analyze+test; Docker build.
  Badges in README.
- Git: `main` protected in spirit; feature branches + PRs (even solo) with descriptive titles; Conventional
  Commits; tags `v1.0-fyp`, `v2.0-azure`; GitHub Releases with notes; `CHANGELOG.md`.
- ADRs (short, one page each) for: PostgreSQL over MySQL; Django templates over SPA; simulated payments;
  JWT for mobile/session for web; Google→Azure Maps; Container Apps over App Service/AKS; Bicep over Terraform; AI-assisted development;
  classifier over the original's unbuilt BERT claim.

### README (the most important file)
Hero line + screenshots/GIF → "The story" (FYP → rebuild → Azure) → architecture diagram → features by role →
tech stack table → quickstart (`docker compose up` + `seed_demo` + demo logins) → "What I improved since uni"
(honest list, including dropped claims) → Azure section (v2) with cost notes → testing/CI → ADR links → licence.

## 8a. How the code gets written (owner's decision: Claude builds most of it)
- Claude implements milestone by milestone on feature branches with PRs into `main`.
- Each milestone ends with a **walkthrough note** in `docs/walkthroughs/NN-<milestone>.md`: what was built, how a
  request flows through the code, the 3–5 files that matter, and likely interview questions with answers. The owner
  reads it, asks questions, and approves the merge. Code stays deliberately plain so it can be explained.
- Commits carry a `Co-Authored-By: Claude` trailer; the README has a short, honest "How this was built" note
  (original FYP concept and report by the owner; rebuild AI-assisted, reviewed and understood by the owner).
- Commit author name/email are the owner's (needed from the owner before the first commit).

## 8b. Existing skeleton (found in the folder, dated 17 Nov)
`api/` (Dockerfile, requirements, `core/auth.py` Entra External ID JWT auth, `core/db/base.py` passwordless Postgres
backend) and `infra/main.bicep` (Log Analytics with daily cap, App Insights, user-assigned identity, Key Vault with
RBAC, ACR without admin user, Postgres Flexible with Entra-only auth, Container Apps env + app with Key Vault secret
references, liveness probe, scale 0–3). Disposition:
- `api/` is replaced by `backend/` (spec layout). Its Dockerfile and requirements are the starting point for the
  production image in milestone 8, but migrations move to a Container Apps job (not container start-up).
- `core/db/base.py` (passwordless Postgres via managed identity) is **kept for v2**, enabled only when
  `DB_AUTH=entra`; v1/local uses a normal password from `.env`.
- `infra/main.bicep` is kept as the v2 starting point (see §9) and modularised.
- Entra External ID login (`core/auth.py`) is **not adopted**: app logins stay simplejwt/session in both versions to
  keep the app explainable and runnable offline. Noted in an ADR as a possible future step.
- None of this is committed as-is; it is folded in during milestones 1 and 8–9 so history stays clean.

## 9. Technical design (v2.0-azure)

### Target architecture (UK South)
| Concern | Azure service | Notes |
|---|---|---|
| Images | Azure Container Registry | Use the SKU covered by the free account's 12-month free services at build time; pulled via managed identity (no admin user) |
| Web app (Django API + dashboards) | Azure Container Apps (Consumption) | Scale-to-zero; min replicas 0; ingress HTTPS |
| DB migrations / seed | Container Apps **job** | Run on each deploy (migrate) and manually (seed) |
| Database | Azure Database for PostgreSQL Flexible Server, Burstable B1ms (free 12 months: 750 h, 32 GB) | `pgvector` enabled; **passwordless**: Entra auth only, app signs in with its managed identity (from §8b) |
| Cache / live queue | Azure Cache for Redis (smallest tier) **or** Azure Managed Redis | Builder picks the cheaper valid option at build time; cost noted |
| Media | Azure Blob Storage | `django-storages`; private container, SAS/identity access |
| Secrets | Azure Key Vault | Accessed via **managed identity**; no secrets in env files or GitHub |
| Async events | Azure Service Bus (Basic) queue | Booking created / token called events |
| Notifications | Azure Functions (Python, Flex/Consumption) | Service Bus trigger |
| Travel time | Azure Maps (Route API) | |
| Observability | Application Insights + Log Analytics (OpenTelemetry for Django) | Saved KQL queries committed in `docs/migration/kql/` |
| Cost guard | Azure budget + alert; Log Analytics daily cap | Defined in Bicep |

### Infrastructure as code
- **Bicep** (chosen by owner: Azure-native, closest to the AI-200 exam). No state file to manage; deployments are
  resource-group scoped, so teardown is "delete the resource group".
- Start from the existing `infra/main.bicep` (17 Nov skeleton, §8b) and split into modules per concern
  (`infra/modules/*.bicep`) with a `main.bicep` + `main.bicepparam`.
- `az deployment group what-if` output posted on infra PRs by CI (the Bicep equivalent of a plan).
- One environment (`demo`); drop the skeleton's `dev`/`prod` split. Scripts `infra/up.sh` / `infra/down.sh`
  wrap create-RG + deploy and delete-RG.

### CI/CD
- GitHub Actions authenticates to Azure with **OIDC federated credentials** (no client secrets).
- On merge to `main`: test → build image → push to ACR → deploy new Container Apps revision → run migration job
  → smoke test `/healthz`.
- Infra changes: `what-if` on PR, deploy manually-triggered (workflow_dispatch) to avoid surprise cost.

### Migration narrative (`docs/migration/`)
A dated log, written as it happens: before/after architecture diagrams, each step (containerise for prod →
Bicep base → DB → app → storage → secrets/identity → Redis → Service Bus/Function → monitoring → CD),
what broke and how it was fixed, decisions (linking ADRs), measured costs from Azure Cost Management, and screenshots
(portal resources, pipeline runs, App Insights dashboards). Ends with "how to reproduce in ~30 minutes" and
"teardown".

### Cost policy (free tier only)
- The owner has no Azure account. **Do not create it until v1.0-fyp is tagged**: the Azure free account's $200
  credit only lasts 30 days from sign-up, while the 12-month free services (e.g. PostgreSQL B1ms) and always-free
  amounts (Container Apps grant, Functions, Service Bus Basic is near-free) continue only if the owner upgrades to
  pay-as-you-go afterwards. Sign-up needs a phone and a non-prepaid debit/credit card.
- Plan v2 so the paid-without-free-tier items (Redis, Azure Maps beyond free transactions, ACR if not free) are
  done inside the 30-day credit window; afterwards the steady-state demo should cost ≈ £0 at idle.
- Deploy, capture evidence, then delete the resource group. Budget alert at £10 and Log Analytics daily cap in Bicep.
- The plan must include a short "create your Azure account" checklist for the owner (sign-up, enable MFA on the
  account, install Azure CLI + Bicep, set budget alert) and the one-time GitHub OIDC app-registration step, which the
  owner performs with guidance. Free accounts own their default directory, so creating the app registration is
  expected to be allowed.
- README states measured cost of a running demo per day.

## 10. Milestones (ordering; plan will break these down)
1. Repo foundation: git init, structure, licence, README skeleton, pre-commit, CI skeleton, docker-compose
   (Postgres + Django). Fold the 17 Nov skeleton in per §8b.
2. Accounts & roles, hospital registration + admin approval, doctors, pharmacies, seed data, dashboards shell.
3. Sessions, booking with atomic tokens, queue ("call next"), simulated payment.
4. Prescriptions, pharmacy requests, complaints.
5. AI suggestion (`ml/` + Django integration + API).
6. Flutter patient app.
7. Docs pass (architecture, ERD, ADRs, screenshots, demo video), tag **v1.0-fyp**, GitHub Release with APK.
8. Production-ready container (gunicorn, whitenoise/static, healthz, settings for cloud).
9. Bicep base + ACR + Container Apps + PostgreSQL + Blob + Key Vault + identity.
10. CD pipeline with OIDC; migration job.
11. Redis, Service Bus + Function, Azure Maps, pgvector path.
12. Observability, cost evidence, migration write-up, teardown; tag **v2.0-azure**.

## 11. Left to the builder
Exact library versions; app/module boundaries inside `backend/`; UI styling details; dataset choice (must be
public and licence-compatible, cited); specialisation list; ranking weights; polling intervals; email provider in
v2; Redis SKU; Bicep module structure; test fixtures; exact README wording (owner reviews).

## 12. Open for the owner (needed before the first commit, not before approval)
- GitHub username / repo name, and the name + email to use as commit author and in README/LICENCE.
- Whether to include a redacted copy of the original report PDF (default: summary only in `docs/original-fyp.md`,
  because the PDF's screenshots contain classmates' names).
