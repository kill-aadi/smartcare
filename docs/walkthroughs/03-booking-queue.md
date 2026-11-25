# Walkthrough 03 — Sessions, booking tokens, the live queue and payments

## What was built

- **Consulting sessions** (`bookings` app):
  - A doctor adds sessions at `/dashboard/doctor/sessions/`: date, start and end time, fee, capacity, and average
    minutes per patient.
  - `create_session()` refuses sessions that would already be over, and ones that overlap another session of the same
    doctor on that day. Back-to-back sessions (09–11 then 11–12) are fine.
  - The database also enforces end > start, capacity ≥ 1 and fee ≥ 0 (`CheckConstraint`s).
- **Booking with token numbers:**
  - `book_session()` gives each booking the next token in its session: 1, 2, 3…
  - It rejects a full session (409 `session_full`), a session that has ended, a second active booking by the same
    patient (409 `already_booked`), and sessions of hidden doctors (404).
  - Cancelling frees the seat but **never reuses the token**: if token 1 cancels, the next patient gets 3, not 1.
  - Two database constraints back this up: a token is unique per session, and a patient has at most one non-cancelled
    booking per session.
- **The live queue:**
  - The doctor's **Today** page (`/dashboard/doctor/today/`) shows one card per session today: "Now serving N", the
    patient being seen, and the next five tokens.
  - **Call next** jumps to the next *active* booking, skipping cancelled tokens. It refuses while the patient being
    seen is still open ("Mark token 2 complete or no-show before calling the next one"), so no booking is left
    half-finished.
  - **Mark consultation complete** and **No-show** close the current patient.
  - Each card refreshes itself every 5 seconds with HTMX, and every button swaps in a fresh card from the server.
- **Queue status for the patient:** `queue_status()` returns token, current token, how many active bookings are
  ahead, an ETA (tokens to go × average minutes) and a state: waiting, now_serving, done or cancelled. A booking
  whose session ended before it was called reports `done`, not a never-ending "~30 min".
- **Simulated payments** (`payments` app):
  - `pay_booking()` creates a `Payment` with a `SIM-XXXXXXXXXXXX` reference and marks the booking paid.
  - A double tap gets 409 `already_paid`. See [ADR 0008](../adr/0008-simulated-payments.md).
- **Patient API:**
  - `GET /api/doctors/<id>/sessions/` lists sessions that haven't ended, with `seats_left`.
  - `POST /api/bookings/` books, and `GET /api/bookings/` lists your bookings.
  - Per booking: `GET /api/bookings/<id>/`, and `POST …/cancel/`, `POST …/pay/`, `GET …/queue/`.
- **Hospital bookings page:** `/dashboard/hospital/bookings/?date=` lists every booking with the hospital's doctors
  on one day.
- **Demo data:**
  - `seed_demo` now adds sessions for today, tomorrow and the day after.
  - Today is split into 08:00–15:00 and 15:00–22:00, so there's an open session at any hour of the demo day.
  - `doctor@` has a live queue: token 1 seen, now serving 2, 6 booked. `patient@` holds token 5 in it.

## How one request flows

**A patient books a session:** `POST /api/bookings/` with `{"session": 42, "description": "Dry cough"}` and a bearer
token.

1. `config/api_urls.py` maps `bookings/` to `bookings.api.BookingListCreateView`.
2. DRF authenticates the JWT, then `IsPatient` lets only patients through. A doctor gets 403.
3. `post()` validates the body with `BookingCreateSerializer`:
   - `session` must be a positive integer
   - `description` can be at most 500 characters
   - anything else → 400
4. It calls `bookings.services.book_session(request.user, 42, "Dry cough")`. Everything below runs in **one database
   transaction**:
   1. `ConsultingSession.objects.select_for_update().get(pk=42, doctor__in=visible doctors)` reads the session
      **and locks its row** until the transaction ends. A session of a pending hospital, or of a deactivated doctor,
      isn't found → `SessionNotFound` (404).
   2. `session.is_past()` → `SessionInPast` (400).
   3. The patient already has a non-cancelled booking here → `AlreadyBooked` (409).
   4. No seats left (cancelled bookings don't count) → `SessionFull` (409).
   5. The new token is the highest token ever issued in this session (cancelled ones included) + 1.
   6. The `Booking` is created and the transaction commits, which releases the lock.
5. If a rule broke, `core.api.domain_exception_handler` turns the `DomainError` into
   `{"detail": "...", "code": "already_booked"}` with its status.
6. Otherwise the view reloads the booking with its doctor and hospital and returns 201 with `BookingSerializer`.

**Then the doctor clicks "Call next":** the button does `hx-post` to `/dashboard/doctor/sessions/42/call-next/`.

1. `CallNextView` looks the session up in `self.doctor.sessions`, so another doctor's session is a 404.
2. `bookings.queue.call_next()` locks the session row and checks that it's this doctor's session, that it's today,
   and that the current patient has been marked complete or no-show. It then moves `current_token` to the smallest
   booked token above it.
3. The view renders `_queue_panel.html` alone (no page layout), and HTMX swaps it in place of the old card.
4. Meanwhile the patient's app polls `GET /api/bookings/<id>/queue/` and sees, for example, `{"token_no": 5,
   "current_token": 3, "ahead": 1, "eta_minutes": 20, "state": "waiting"}`.

## The files that matter

- `backend/bookings/services.py`: `create_session()`, `book_session()` (the locking and token logic),
  `cancel_booking()` and `seats_left()`.
- `backend/bookings/queue.py`: `call_next()`, `complete_booking()`, `mark_no_show()` and `queue_status()`, the whole
  queue in one file.
- `backend/bookings/tests/test_booking_concurrency.py`: ten real threads book five seats at the same instant.
- `backend/bookings/api.py`: the patient endpoints. Every booking lookup is filtered by the patient.
- `backend/payments/services.py`: `pay_booking()`, the one place a real payment gateway would plug in.

## The concurrency story

The test starts 10 threads, one per patient, holds them at a `threading.Barrier`, then releases them all at once to
book the same 5-seat session. Each thread has its own PostgreSQL connection, so this is real concurrency. It expects
tokens exactly `[1, 2, 3, 4, 5]` and five `SessionFull` errors.

To prove the lock matters, I removed `select_for_update()` and ran the test three times. It failed every time:

```
E   Left contains 6 more items, first extra item: 'IntegrityError('duplicate key value violates unique
    constraint "unique_token_per_session"\nDETAIL:  Key (session_id, token_no)=(88, 3) already exists.')'
1 failed in 0.24s
```

Without the lock, several threads read the same "highest token so far" at the same moment and all try to insert the
same next number. The database's unique constraint stops duplicate tokens, but 6 or 7 of the 10 patients got an
error page instead of a booking or a clear "session full". Without that constraint, two patients would share a token
and the session could be overbooked. With the lock back, the threads queue on the session row one at a time, and the
test passed 5 out of 5 runs.

## Likely interview questions

**How do you guarantee two patients never get the same token?**
Two layers. The booking transaction locks the session row with `SELECT … FOR UPDATE`, so bookings for the same session
run one after another and each sees the previous token. The database also has a unique constraint on
`(session, token_no)` as a safety net. The concurrency test proves the lock is what makes it work: without it the
constraint fires and patients get errors.

**Why lock the session row instead of using a sequence or `MAX()+1` alone?**
`MAX()+1` alone is exactly the race in the test. A PostgreSQL sequence would give unique numbers, but they'd be
global, not 1, 2, 3 per session, and wouldn't help with the capacity check. Locking the one session row serialises
only bookings for *that* session; other sessions aren't blocked.

**What happens if a patient double-taps "Book"?**
Both requests reach `book_session()`. The second waits for the first one's lock, then finds an active booking for that
patient and gets 409 `already_booked`. There's still exactly one booking and one token. A partial unique constraint
(one non-cancelled booking per patient per session) backs it up in the database. Paying works the same way:
`pay_booking()` locks the booking row, so a double tap gets 409 `already_paid` and never creates two payments.

**Why aren't cancelled tokens reused?**
Tokens are what patients see and what the doctor calls. If token 3 cancelled and a new patient got 3, someone who
already heard "3" might think it's them, and the queue order would jump. New bookings always take the highest token
ever issued + 1, and `call_next()` skips cancelled tokens.

**How does the patient see the queue move, and how accurate is the ETA?**
The app polls `/api/bookings/<id>/queue/` (every ~15 seconds in milestone 6). The ETA is
`(my token − current token) × the doctor's average minutes`, an estimate shown as "~N min", never a promise. `ahead`
counts only active bookings between the current token and mine, so cancellations don't inflate it.

**Why HTMX polling instead of WebSockets for the doctor's page?**
One doctor, one page, numbers that change every few minutes: polling every 5 seconds is simple, survives reconnects
for free and needs no extra server (Channels, Redis). Every action returns the same fresh panel, so there's only one
template to keep right. In v2, booking events go through Azure Service Bus; the page itself can stay as it is.

**Why can only the token being served be marked complete or no-show?**
`complete_booking()` and `mark_no_show()` require `token_no <= current_token`. You can't mark someone a no-show before
you've called them. Closing an already closed booking is refused too (`InvalidTransition`).

**How did a threaded test break other tests, and how did you fix it?**
The concurrency test needs real commits, so it runs with `transaction=True`, and pytest-django empties the database
afterwards. That also deleted the 12 specialisations a data migration had created, and because the suite reuses its
test database between runs (`--reuse-db`), the next run started without them: 16 tests failed. `conftest.py` now
re-creates them at the start of every test run.
