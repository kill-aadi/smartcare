# 0006. Keep app logins in Django (no Entra External ID)

- **Status:** Accepted
- **Date:** 2026-11-24

## Context
An earlier Azure-first skeleton validated Microsoft Entra External ID tokens for all five roles.

## Decision
App users log in with Django: session cookies for the web dashboards and JWTs (simplejwt) for the patient app, in
both v1 and v2. Entra ID is still used in v2 for *infrastructure* identity (managed identity to PostgreSQL, Key Vault
and the container registry).

## Consequences
- The app runs fully offline with `docker compose up`; demo logins are simple.
- No dependency on an External ID tenant for demos or tests.
- Moving end-user login to Entra External ID remains a possible future step.

## Alternatives considered
- **Entra External ID for all users:** realistic for production, but adds a tenant, app registrations and token
  configuration that are hard to demo and explain in a two-minute answer.
