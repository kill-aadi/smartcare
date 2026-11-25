# 0008. Simulated payments in v1

- **Status:** Accepted
- **Date:** 2026-11-25

## Context
Patients pay a consultation fee when they book. A real payment gateway needs a merchant account, KYC, webhooks and
secret keys, none of which a portfolio project can or should hold. Real payments are an explicit non-goal in the
spec, but the flow (book → pay → paid badge) still has to be real enough to demo and test.

## Decision
- "Pay" calls `payments.services.pay_booking()`, which creates a `Payment` with `provider="simulated"` and a
  reference like `SIM-3F9A0C12B7DE`, then marks the booking paid. No money moves.
- The UI and API label it as a simulated payment.
- The booking row is locked (`select_for_update`) while paying, so a double tap gets `409 already_paid` and never
  creates two payments.
- `payments.services` is the **single seam**: views and the API only call `pay_booking()` (and, in milestone 4, the
  pharmacy equivalent). Nothing else creates `Payment` rows or flips `payment_status`.

## Consequences
- Tests and the demo need no network, keys or sandbox accounts.
- Swapping in a gateway means changing one module: create a gateway order, return its checkout details, and mark
  the booking paid from a verified webhook instead of immediately. `Payment.provider` and `reference` already
  have room for a real provider's name and ID.
- There are no refunds: cancelling a paid booking keeps the payment record (fine for a simulation).

## Alternatives considered
- **Razorpay/Stripe test mode:** realistic, but needs account sign-up, secret keys in CI and webhook tunnelling
  for local development: a lot of moving parts for no portfolio value beyond the seam above.
- **No payment step at all:** loses the "paid" state the original project had and the double-tap rule.
