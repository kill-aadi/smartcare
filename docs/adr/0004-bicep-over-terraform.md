# 0004. Bicep for infrastructure as code (v2)

- **Status:** Accepted
- **Date:** 2026-11-24

## Context
v2 must be deployable and destroyable on demand, and the owner is targeting Azure certifications.

## Decision
Describe all Azure resources in Bicep, deployed at resource-group scope, with `what-if` on pull requests.

## Consequences
- Azure-native, no state file to store or lock; teardown is "delete the resource group".
- Skills don't transfer to other clouds as directly as Terraform would.

## Alternatives considered
- **Terraform:** multi-cloud and popular, but adds remote state management and is less aligned with the Azure exams.
