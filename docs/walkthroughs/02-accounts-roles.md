# Walkthrough 02 — Accounts, roles, hospitals, doctors and pharmacies

## What was built

- **Domain models:**
  - `Hospital`, with an approval status of pending, approved or rejected.
  - `Specialization`: 12 fixed names, seeded by a data migration.
  - `Doctor` and `Pharmacy`, each belonging to a hospital.
  - `PatientProfile`.
  - Every staff record is 1:1 with a `User`, so each person has exactly one login.
- **Hospital registration and approval:**
  - A hospital signs up at `/register/hospital/`, uploading a licence (PDF, JPG or PNG, up to 5 MB) and its map
    coordinates.
  - It starts as *pending*. An admin opens it, reads the licence and approves, or rejects with a reason.
  - The hospital is emailed either way. v1 prints the email to the console.
- **Web dashboards:**
  - Email login at `/login/`, then `/dashboard/` sends you to your role's home.
  - Wrong role → 403. A pending or rejected hospital sees a status page instead of its dashboard.
  - Patients who try the web are told to use the app.
- **Hospital staff management:** an approved hospital adds, edits and deactivates its own doctors and adds pharmacies.
  It can't see or touch another hospital's (404).
- **Patient API:**
  - `POST /api/auth/register/` and `POST /api/auth/token/` (JWT).
  - Tokens are for patients only: staff get "This app is for patients. Staff should use the web dashboard."
  - `GET /api/me/`.
  - The catalogue: `/api/specializations/`, `/api/doctors/`, and `/api/hospitals/?lat=&lng=` sorted by straight-line
    distance.
- **`seed_demo`:** a fictional, deterministic demo world (5 approved, 1 pending and 1 rejected hospital; 17 doctors;
  5 pharmacies; 10 patients) with documented logins.

## How one request flows

**A patient asks for hospitals near them:** `GET /api/hospitals/?lat=10.5276&lng=76.2144` with
`Authorization: Bearer <access token>`.

1. `config/urls.py` sends `/api/` to `config/api_urls.py`, which maps `hospitals/` to `hospitals.api.HospitalListView`.
2. DRF authenticates the bearer token (`JWTAuthentication`), then checks `IsPatient` (`core/permissions.py`):
   - not logged in → 401
   - a doctor's session → 403
3. `HospitalListView.list()` validates the query string with `LocationQuerySerializer` (`core/serializers.py`):
   - both lat and lng, or neither
   - lat between -90 and 90, lng between -180 and 180
   - `lat=abc` → 400
4. `get_queryset()`:
   - starts from `Hospital.objects.approved()`, so pending and rejected hospitals can never leak
   - applies `search` to name or place
   - takes at most 50 rows
   - computes `haversine_km()` and `straight_line_minutes()` (`core/geo.py`) for each one, then sorts nearest
     first
5. `HospitalSerializer` returns each hospital with `distance_km` (1 decimal place) and `straight_line_minutes`. The app
   must label the time as a straight-line estimate.

**An admin approves a hospital:** POST `/dashboard/admin/hospitals/<id>/` with `action=approve`.

1. `AdminHospitalDetailView` (`dashboards/views.py`) is guarded by `RoleRequiredMixin(allowed_roles=(admin,))`.
2. It calls `hospitals.services.approve_hospital(hospital, by=request.user)`. The service checks:
   - the caller is an admin, otherwise `NotAllowed`
   - the move is allowed (pending → approved, or rejected → approved), otherwise `InvalidTransition`
3. It then sets `reviewed_at`, saves, and sends the email.
4. If the service raises a `DomainError`, the view shows it as a red message. The rule lives in one place and is
   tested without HTTP.

## The files that matter

- `backend/hospitals/services.py`: registration plus the approval state machine (`_ALLOWED`), and
  `require_approved()`, which stops unapproved hospitals adding staff.
- `backend/dashboards/mixins.py`:
  - `RoleRequiredMixin`: login redirect vs 403.
  - `ApprovedHospitalRequiredMixin`: redirects pending and rejected hospitals to their status page.
- `backend/doctors/models.py`: `Doctor.objects.visible_to_patients()`, the single definition of which doctors
  patients may see.
- `backend/accounts/serializers.py`: `PatientTokenSerializer`, which blocks staff from getting app tokens.
- `backend/hospitals/api.py` + `backend/core/geo.py`: nearby sort with the haversine formula.

## Likely interview questions

**How do you stop a pending hospital's doctors showing up in the app?**
There's one definition, `Doctor.objects.visible_to_patients()`: active user *and* approved hospital. Every patient
endpoint starts from it, and from `Hospital.objects.approved()` for hospitals. Hospitals also can't add doctors until
approved (`require_approved()`), and tests cover both pending and rejected hospitals.

**Where are your business rules, and why not in the views?**
In `services.py`, e.g. `approve_hospital()` and `create_doctor()`. Views only translate HTTP into a service call.
That way the same rule serves the dashboard and the API, and it's tested directly. A broken rule raises a
`DomainError` with a code, which the API turns into JSON and the dashboard shows as a message.

**How is the licence file protected?**
It's never served from the public media URL. Dev media serving refuses the `licences/` folder (after normalising the
path, so `./licences/…` or `x/../licences/…` can't trick it). Only `AdminLicenceView`, admin-only, streams it. Tests
try four path tricks and every non-admin role. In v2 it must go to a *private* Blob container.

**Why can't a doctor log into the patient app?**
`PatientTokenSerializer` checks the role after the password check and refuses non-patients with a clear message.
Every API view also uses `IsPatient`. Two layers: even a doctor's browser session gets 403 on `/api/me/`.

**How does "nearby" work without Google Maps?**
The phone sends its coordinates. The server computes great-circle distance with the haversine formula and sorts in
Python. That's fine at demo scale (≤ 50 hospitals) and needs no API key. The time shown is distance ÷ 30 km/h,
labelled as a straight-line estimate. Real travel time is a v2 feature (Azure Maps).

**What's 404 vs 403 here?**
403 means "you're logged in but your role can't use this page". For other people's objects (another hospital's
doctor), we filter the query by the owner, so the object simply isn't found: 404. That way we don't confirm it
exists.

**How is the demo data safe to publish?**
Hospital names contain "Demo", people's names are generated by Faker with a fixed seed, and every email uses the
reserved `.test` domain. Tests assert all three. `--flush` only deletes `@smartcare.test` accounts.

**Why do tests use MD5 for passwords?**
Only in tests (`conftest.py`). Real password hashing is deliberately slow; using a fast hasher cut the suite from
~66 seconds to ~2 seconds. Production settings are unchanged.
