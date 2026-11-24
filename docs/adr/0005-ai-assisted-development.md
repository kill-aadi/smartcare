# 0005. AI-assisted development, reviewed milestone by milestone

- **Status:** Accepted
- **Date:** 2026-11-24

## Context
The original source code is lost and the rebuild needs to happen quickly. The owner must still be able to explain
every part in an interview.

## Decision
Most code is written with Claude (Anthropic) from an approved design and plan. Each milestone is a pull request with
a walkthrough note in `docs/walkthroughs/`; the owner reads it and approves before merge. AI-written commits carry a
`Co-Authored-By` trailer, and the README says how the project was built.

## Consequences
- Fast progress with tests, CI and documentation from the start.
- Code is kept deliberately plain so it can be explained; walkthroughs double as interview prep.
- Honesty about tooling is part of the portfolio, not hidden.

## Alternatives considered
- **Hand-written only:** slower; the lost code would take months to rebuild alongside job applications.
