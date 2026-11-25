# 0003. Azure Container Apps for hosting (v2)

- **Status:** Accepted
- **Date:** 2026-11-24

## Context
v2 migrates the app to Azure on a free-tier budget. The owner is preparing for AI-200, whose largest skill area is
containers.

## Decision
Run the Django container on Azure Container Apps (Consumption plan, scale to zero), with migrations as a Container
Apps job.

## Consequences
- Idle cost is near zero; the same image runs locally and in Azure.
- Container Apps concepts (revisions, ingress, jobs, managed identity) become part of the story.

## Alternatives considered
- **App Service (code deploy):** simplest, but "I uploaded my code" is a thin migration story.
- **AKS:** expensive and over-engineered for a solo five-role app; hard to justify in an interview.
