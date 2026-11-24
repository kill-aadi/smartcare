# 0001. PostgreSQL instead of MySQL

- **Status:** Accepted
- **Date:** 2026-11-24

## Context
The original FYP was built on MySQL; its report also lists PostgreSQL as an option. The rebuild needs row-level
locking for token numbers, a vector extension for the v2 AI feature, and a clean path to a managed Azure database.

## Decision
Use PostgreSQL 16 from v1 onwards, locally in Docker and on Azure Database for PostgreSQL Flexible Server in v2.

## Consequences
- `SELECT … FOR UPDATE` and partial unique indexes are available for the booking rules.
- `pgvector` can be enabled in v2 without changing database.
- This is a documented deviation from the original build.

## Alternatives considered
- **MySQL (original):** works, but no first-class vector extension on Azure's managed MySQL.
- **SQLite for local dev:** different locking behaviour from production would hide the concurrency bug the token
  tests exist to catch.
