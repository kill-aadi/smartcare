# SmartCare: Handover

**Read this first, then read `docs/superpowers/specs/2026-11-24-smartcare-design.md`.** The design doc is the
source of truth: what we're building and why. This handover covers getting set up and how to start.

---

## 1. The project in a few lines

- SmartCare was Marwan's BSc Computer Science final-year project (2025–26): a hospital management system with five
  roles (admin, hospital, doctor, pharmacy, patient).
- Its main features:
  - AI doctor suggestion from symptoms
  - bookings with token numbers and a live queue
  - prescriptions forwarded to pharmacies
  - complaints
  - map directions
- **The original code is lost.** Only the report survives.
- We're rebuilding it as one public GitHub repo for his CV. He's applying for **Azure cloud developer** jobs.
- The repo tells two chapters:
  1. **`v1.0-fyp`:** the FYP rebuilt properly. Django (API + web dashboards) + Flutter patient app + PostgreSQL,
     all running locally with `docker compose up`.
  2. **`v2.0-azure`:** the same app migrated to Azure Container Apps using Bicep, managed identity, Key Vault,
     CI/CD, monitoring and a written migration log.
- Certification path: AZ-900, then AI-200. The Azure services were chosen to match AI-200.

## 2. Decisions already made (don't reopen)

| Topic | Decision |
|---|---|
| App shape | Django serves the web dashboards (templates + Bootstrap + HTMX) **and** a DRF API; Flutter is the **patient-only** mobile app |
| Database | PostgreSQL from v1 (pgvector later for AI) |
| Cloud | Azure, **Azure Container Apps** |
| Infra as code | **Bicep** (not Terraform) |
| Who builds | Mostly AI-assisted (Claude), reviewed milestone by milestone. Each milestone gets a walkthrough note (see §6) |
| Speed | No hard deadline, but ASAP. Keep v1 lean (no Redis in v1) |
| Azure account | **Don't create it until `v1.0-fyp` is tagged.** The free account's $200 credit only lasts 30 days from sign-up |
| Honesty | The README only claims what the code does. Payments are simulated and labelled. No real people's data, no real hospital names |
| Repo | One monorepo: `backend/`, `mobile/`, `ml/`, `infra/`, `functions/`, `docs/` |

## 3. Current state

- No git repo yet. Nothing is committed. The repo hasn't been created on GitHub.
- The zip (`smartcare-handover.zip`) contains:
  - `docs/superpowers/specs/2026-11-24-smartcare-design.md`: the design
  - `docs/HANDOVER.md`: this file
  - `api/` and `infra/main.bicep`: an earlier Azure-first skeleton. **Don't commit it as-is.** Design §8b says
    what to keep. In short:
    - keep `api/core/db/base.py` (passwordless Postgres) and `infra/main.bicep` for v2
    - drop the Entra login
    - `api/` gets replaced by `backend/`
- **Needed from Marwan before the first commit:** GitHub username, repo name (suggested: `smartcare`), and the
  name and email to use on commits.

## 4. Tools to install

### Editor: VS Code
VS Code is the best fit. It handles Python/Django, Flutter, Docker, Bicep and Azure in one editor. Android Studio
is still needed for the Android SDK and emulator, but you don't have to code in it.

**VS Code extensions:**

| Extension | Why |
|---|---|
| Python + Pylance (Microsoft) | Python language support |
| Ruff (Astral) | Lint and format Python |
| Django (Baptiste Darthenay) | Template syntax highlighting |
| Flutter (Dart Code), which installs Dart | Flutter dev, hot reload, debugging |
| Container Tools / Docker (Microsoft) | Manage containers and compose |
| Bicep (Microsoft) | Bicep IntelliSense and validation (needed for v2) |
| Azure Resources + Azure Container Apps (Microsoft) | Browse and deploy Azure resources (needed for v2) |
| GitHub Pull Requests (GitHub) | Review and merge PRs inside VS Code |
| Markdown Preview Mermaid Support | Preview the ER and architecture diagrams in docs |
| EditorConfig | Consistent formatting across editors |
| Claude Code (Anthropic), optional | If you're building with Claude Code |

### Needed now (v1)

| Tool | Notes |
|---|---|
| **Git** | Then run `git config --global user.name` / `user.email` with **Marwan's** details (see §3) |
| **GitHub CLI (`gh`)** | Run `gh auth login`. Used to create the repo and open PRs |
| **Docker Desktop** | Runs Postgres and Django. On Windows, enable the **WSL 2** backend. Give it at least 4 GB RAM |
| **Python 3.12** | Install via [uv](https://docs.astral.sh/uv/) (`uv python install 3.12`), which also replaces pip/venv and is fast |
| **pre-commit** | Run `uv tool install pre-commit` |
| **Flutter SDK (stable)** | Install per flutter.dev for your OS |
| **Android Studio** | Only for the Android SDK, command-line tools and an emulator (e.g. a Pixel image). Then run `flutter doctor --android-licenses` |
| **Claude Code**, optional | If you're building with Claude. Install the **superpowers** plugin so the plan/execute workflow is available |

### Needed later (v2, Azure)
- **Azure CLI**, then run `az bicep install`
- **Azure Functions Core Tools v4**, for the notification function

### Check everything works
```bash
git --version && gh --version
docker --version && docker compose version
uv --version && uv run --python 3.12 python --version
flutter doctor            # all ticks except iOS/Xcode (not needed)
pre-commit --version
```

**Windows tip:** keep the repo inside WSL (`~/code/smartcare`) if you run the backend through WSL. Add a
`.gitattributes` with `* text=auto eol=lf` from day one so line endings don't break shell scripts in containers.

## 5. How to start

1. Unzip the files. Create the repo: `gh repo create <user>/smartcare --public`. Clone it, copy `docs/` in, then
   `git init` (if needed).
2. **First commit:** just the design doc and this handover (`docs: add design and handover`). Leave `api/` and
   `infra/` out for now. They get folded in at milestones 1 and 8–9.
3. **Write the build plan.** If you're using Claude Code with superpowers, open the repo and say:
   > "Read docs/HANDOVER.md and docs/superpowers/specs/2026-11-24-smartcare-design.md. The design is approved. Use
   > the writing-plans skill to write the implementation plan for milestones 1–7 (v1.0-fyp)."

   The plan goes in `docs/superpowers/plans/`. Then execute it milestone by milestone.
4. Plan v2 (milestones 8–12) separately, after `v1.0-fyp` is tagged and Marwan has created his Azure account.

## 6. Working agreement

- **Branches:** one branch per milestone or feature (`feat/booking-tokens`). Open a PR into `main` and merge after
  CI passes. No direct pushes to `main` once CI exists.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `ci:`). Small and readable,
  because the history is part of the portfolio. AI-written commits keep the `Co-Authored-By` trailer.
- **End of every milestone:**
  - tests green
  - README updated if behaviour changed
  - a walkthrough note in `docs/walkthroughs/NN-<name>.md` covering: what was built, how one request flows through
    the code, the 3–5 key files, and likely interview questions with answers

  **Marwan reads the walkthrough before the PR is merged.** He has to be able to explain everything.
- **Decisions:** any decision that deviates from or adds to the design gets a one-page ADR in `docs/adr/`.
- **Never commit** `.env`, keys, real names or real patient-like data. Use `.env.example` and `seed_demo`.
- **Evidence as you go:** grab screenshots into `docs/screenshots/` when a feature works. They're needed for the
  README anyway.

## 7. Milestone checklist (from the design)

**v1.0-fyp (local)**
- [ ] 1. Repo foundation: structure, licence (MIT), README skeleton, pre-commit, CI skeleton, docker-compose
  (Postgres + Django)
- [ ] 2. Accounts and roles, hospital registration + admin approval, doctors, pharmacies, `seed_demo`, dashboards shell
- [ ] 3. Consulting sessions, booking with atomic token numbers, "call next" queue, simulated payment
- [ ] 4. Prescriptions, pharmacy requests, complaints
- [ ] 5. AI suggestion (`ml/` notebook + model + Django API, with honest accuracy)
- [ ] 6. Flutter patient app
- [ ] 7. Docs pass (architecture, ERD, ADRs, screenshots, demo video). Tag **`v1.0-fyp`**. GitHub Release with APK

**v2.0-azure (Marwan creates the Azure free account here)**
- [ ] 8. Production container (gunicorn, static files, `/healthz`, cloud settings)
- [ ] 9. Bicep: ACR, Container Apps, PostgreSQL (passwordless), Blob, Key Vault, managed identity
- [ ] 10. CD with GitHub OIDC; migrations as a Container Apps job
- [ ] 11. Redis, Service Bus + Azure Function, Azure Maps, pgvector
- [ ] 12. App Insights/KQL, cost evidence, migration write-up, teardown. Tag **`v2.0-azure`**

## 8. Gotchas

- **Android emulator → local backend:** use `http://10.0.2.2:8000`, not `localhost`. On a real phone, use your PC's
  LAN IP. Pass it with `flutter run --dart-define=API_BASE_URL=...`.
- **Allow the emulator host:** add `10.0.2.2` (and your LAN IP) to Django `ALLOWED_HOSTS` in dev.
- **Token numbers must be assigned inside a transaction with `select_for_update`.** Write a test that books
  concurrently. This is a likely interview question.
- **Azure cost:** once v2 starts, set the £10 budget alert **first**. Delete the resource group when you're not
  demoing.
- **The AI feature is not medical advice.** Keep the disclaimer in the app and README.
