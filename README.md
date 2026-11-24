# SmartCare

A hospital management system connecting admins, hospitals, doctors, pharmacies and patients — my BSc Computer
Science final-year project, rebuilt properly and then migrated to Azure.

[![CI](https://github.com/kill-aadi/smartcare/actions/workflows/ci.yml/badge.svg)](https://github.com/kill-aadi/smartcare/actions/workflows/ci.yml)

> 🚧 **Rebuild in progress — milestone 1 of 7.** This README only describes what the code does today.

## The story

SmartCare was my final-year project (2025–26). The original source code was lost; only the report survived. This
repository rebuilds it feature by feature (chapter 1, tag `v1.0-fyp`) and then migrates it to Azure Container Apps
with infrastructure as code (chapter 2, tag `v2.0-azure`).

## Architecture

_Coming in milestone 7._

## Features by role

_Added as each milestone lands._

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Django 5.2, Django REST Framework, drf-spectacular (OpenAPI) |
| Database | PostgreSQL 16 |
| Local runtime | Docker Compose |
| Quality | pytest, ruff, pre-commit, GitHub Actions |

_More rows are added as each milestone lands (Flutter app, ML model)._

## Quickstart

You only need [Docker](https://docs.docker.com/get-docker/).

```bash
git clone https://github.com/kill-aadi/smartcare.git
cd smartcare
docker compose up
```

Then open <http://localhost:8000/api/docs/> for the interactive API documentation. No `.env` file is needed; copy
`.env.example` to `.env` if you want to override the defaults.

## What I improved since uni

_Coming in milestone 7._

## Azure

_Chapter 2 (`v2.0-azure`)._

## Testing and CI

```bash
docker compose run --rm web pytest            # tests (against the real Postgres container)
docker compose run --rm web pytest --cov      # with coverage
docker compose run --rm web sh -c "ruff check . && ruff format --check ."
```

Every pull request runs lint, format check, tests with coverage (gate: 80% on business-logic modules) and a Docker
build in GitHub Actions.

## Architecture decisions

Key decisions are recorded as short ADRs in [`docs/adr/`](docs/adr/README.md).

## Licence

[MIT](LICENSE)
