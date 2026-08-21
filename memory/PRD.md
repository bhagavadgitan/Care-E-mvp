# CARE-E — PRD & Build Log

## Original problem statement
CARE-E (Healthcare Supply Resolution Network): a resolution & coordination layer above fragmented hospital/supplier supply systems. Given a supply shortage, discover feasible internal (hospital) + external (supplier) options, verify hard constraints, rank feasible options, present Top 3, require human approval, simulate transfer/procurement, track resolution. Deterministic, explainable, backend-owned engine (no LLM). Synthetic data now; replaceable by real ERP/WMS/supplier/CSV integrations later without frontend rewrite.

## Architecture source of truth
`/app/memory/ARCHITECTURE.md` (approved directionally + Review-1 amendments recorded at top).

## Confirmed decisions (Review 1)
MongoDB (with DB-agnostic repos + Postgres appendix) · HttpOnly-cookie JWT + Emergent Google (M1) · Google never auto-approves org · recommendations read-only, fresh feasibility re-check before approval commit · need-to-know server-enforced visibility · explicit reproducible experiment assumptions · pure resolution engine · approval transaction with audit · app-level audit trail · modular monolith.

## Personas
Hospital (procurement/inventory/ops), Supplier/Distributor, CARE-E Admin.

## Milestones
- M0 Foundation — **DONE (2026-06)**
- M1 Auth & Org model — NOT STARTED (awaiting authorization)
- M2 Synthetic data · M3 Resolution engine · M4 Hospital core loop · M5 Supplier · M6 Admin/Analysis · M7 Hardening — planned.

## M0 — Implemented (2026-06)
- Backend modular monolith scaffolding: `core/` (config, database, logging, exceptions), `api/v1/` (health), `services/`, `domain/` (BaseDocument + PyObjectId), `repositories/` (interface + Mongo generic impl), `migrations/` (idempotent runner + baseline).
- FastAPI app factory with lifespan (Mongo connect + migrations), CORS, centralized structured error handling, versioned `/api/v1`, health + liveness endpoints, `/api/docs`.
- Frontend institutional shell (burgundy/charcoal/off-white theme), React Query health panel, axios apiClient with error normalization, synthetic-data badge, test-id registry.
- Tests: 10 passing (domain base, exception hierarchy, health API integration, structured 404).

## Backlog (P0 next → M1)
Auth (email/password + Google, HttpOnly cookies, rate limiting) · Organisation/User/Facility models + approval states · role-oriented login/registration · server-side authorization guards.
