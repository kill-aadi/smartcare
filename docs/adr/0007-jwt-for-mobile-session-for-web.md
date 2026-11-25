# 0007. JWT for the patient app, sessions for the web dashboards

- **Status:** Accepted
- **Date:** 2026-11-25

## Context
Staff (admin, hospital, doctor, pharmacy) use server-rendered dashboards in a browser. Patients use a Flutter app
that calls the REST API. Both need login, and the API must never serve staff.

## Decision
- **Dashboards:** Django session cookies with CSRF protection (`/login/`).
- **Patient app:** short-lived JWT access tokens (15 minutes) plus refresh tokens (7 days) from
  `djangorestframework-simplejwt`, stored in the phone's secure storage.
- `/api/auth/token/` only issues tokens to patients; staff get 401 "This app is for patients. Staff should use the
  web dashboard." Every patient endpoint also checks `IsPatient`.

## Consequences
- Mobile clients don't deal with cookies or CSRF; a stolen access token expires quickly.
- A deactivated account can't refresh its token (simplejwt checks the user is still active).
- Logout on the phone deletes the tokens; refresh tokens aren't blacklisted server-side in v1 (possible later step).

## Alternatives considered
- **Sessions for the app too:** cookies and CSRF are awkward from Flutter.
- **DRF opaque tokens:** never expire unless we add expiry ourselves.
- **Entra External ID:** see [ADR 0006](0006-no-entra-external-id-login.md).
