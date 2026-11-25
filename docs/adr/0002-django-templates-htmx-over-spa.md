# 0002. Server-rendered dashboards (Django templates + HTMX) instead of a SPA

- **Status:** Accepted
- **Date:** 2026-11-24

## Context
Four of the five roles (admin, hospital, doctor, pharmacy) work in a browser; patients use a phone app. The original
FYP was a Django web app plus a Flutter app.

## Decision
Django serves the staff dashboards with templates, Bootstrap 5 and HTMX. A DRF API serves the patient-only Flutter
app. Both call the same service functions.

## Consequences
- One language and one deployable for the web side; no separate frontend build.
- The doctor's live queue refreshes with HTMX polling instead of a JavaScript framework.
- Dashboards are less "app-like" than a SPA, which is fine for admin-style screens.

## Alternatives considered
- **Flutter web for dashboards:** weak for data tables, drifts from the original.
- **React dashboard:** a third technology not in the original project.
