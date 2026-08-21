# CARE-E — Architecture Proposal (MVP)

> **Status:** PROPOSAL — awaiting review & explicit approval before implementation.
> **Scope of this document:** Architecture planning only (Sections A–Q). No application code is produced in this stage.
> **Data:** All MVP data is **SYNTHETIC / DEMONSTRATION** data. No real patient, hospital, or supplier data.

**CARE-E — Healthcare Supply Resolution Network.** A resolution and coordination layer that sits *above* fragmented hospital and supplier supply systems. Given a supply shortage, CARE-E discovers feasible internal (hospital-to-hospital) and external (supplier) resolution options, verifies hard constraints, ranks feasible options, and presents the **Top 3** for a **human to approve**. CARE-E recommends; authorised humans approve. It never autonomously moves inventory or purchases supplies.

> ## AUTHORITATIVE DECISIONS — Review 1 (APPROVED WITH AMENDMENTS)
> These supersede any conflicting text below.
> 1. **Database:** MongoDB for the MVP. Keep repository/data-access abstraction + PostgreSQL appendix. Do **not** claim Mongo gives identical native relational guarantees as PostgreSQL; achieve **equivalent** integrity in the application/domain layer via JSON-Schema validation, service-layer ownership checks, unique indexes, reference validation, Mongo transactions where appropriate, and explicit consistency checks.
> 2. **Auth transport:** Prefer **HttpOnly cookie** JWT/session (Secure in prod, appropriate SameSite) over localStorage. Follow the Emergent-managed auth platform mechanism where it mandates one.
> 3. **Google org binding:** Google auth identifies the *user only*. It must **never** auto-create or auto-approve an organisation or bypass approval. New Hospital/Supplier orgs still flow PENDING → APPROVED/REJECTED/SUSPENDED.
> 4. **Inventory reservation:** Recommendations are **read-only** — no reservation at recommendation time. Reservation/mutation happens only after explicit human approval, and **immediately before commit** a fresh feasibility check re-validates available qty, reserved qty, safety stock, transfer permission, expiry/usable life, deadline, and policy. If stale/invalid → return a **conflict/stale-recommendation** response and require recalculation (never execute blindly).
> 5. **Visibility:** Server-enforced, organisation-aware, **NEED-TO-KNOW** default. Hospital: own org/facility data + relevant network candidates for resolution; no unrestricted view of unrelated hospital inventory. Supplier: relevant opportunities/requests only; no unrelated hospital data; no competitor data. Admin: broad. Policy model kept configurable.
> 6. **Experiments:** All synthetic assumptions explicit & reproducible (transfer time, supplier lead time, transfer cost, supplier price, safety-stock rules, expiry assumptions, scenario params). Every result labelled **"Synthetic simulation under defined assumptions."** Never presented as validated real-world outcomes.
> 7. **Resolution engine:** `backend/domain/resolution/` — pure, deterministic, LLM-free, independently testable. Hard constraints before ranking. ELIGIBLE/CONDITIONAL/INELIGIBLE with explicit reasons. Infeasible never outranks feasible. Return Top 3 feasible where available.
> 8. **Approval transaction:** recommendation → fresh feasibility validation → transaction → inventory/reservation update → simulated transfer/PO → audit event.
> 9. **Auditability:** Application-level audit trail for important state-changing actions (actor, organisation, action, entity, timestamp, previous state, new state). No Kafka / distributed event architecture.
> 10. **Architecture style:** Modular monolith. No microservices without a concrete requirement.
>
> **Milestone status:** M0 AUTHORIZED (foundation only). M1+ NOT authorized. M0 excludes auth, Google login, org/hospital/supplier workflows, resolution engine, and dashboards beyond a minimal app shell.

Confirmed platform decisions (from product owner):
- **DB:** MongoDB for the MVP (managed by Emergent), with a database-agnostic domain/repository layer + a PostgreSQL future-migration appendix (Section H / Appendix).
- **Auth:** JWT email/password **+** Emergent-managed Google sign-in. Authentication is kept separate from authorization.
- **Build cadence:** Milestone-by-milestone, tested after each milestone, no independent scope expansion.
- **Engine:** Deterministic, explainable, backend-owned, independently testable. **No LLM** in the resolution decision.

---

## A. Product Architecture

CARE-E is a **modular monolith**: one React SPA frontend + one FastAPI backend + MongoDB, deployed as a single service. Internally the backend is organised into clean layers so it *behaves* like well-separated services without the operational cost of microservices.

```
                         ┌───────────────────────────────────────┐
                         │            React SPA (frontend)         │
                         │  presentation · UI state · validation   │
                         └───────────────────┬─────────────────────┘
                                             │ HTTPS  /api/v1/*  (JWT)
                         ┌───────────────────▼─────────────────────┐
                         │              API Layer (FastAPI)         │
                         │  routers · request/response schemas      │
                         ├──────────────────────────────────────────┤
                         │      AuthN (JWT/Google)  ·  AuthZ (RBAC   │
                         │      + org ownership + approval status)   │
                         ├──────────────────────────────────────────┤
                         │        Application / Service Layer        │
                         │  orchestration · transactions · policies  │
                         ├──────────────────────────────────────────┤
                         │           Domain / Business Logic         │
                         │  Resolution Engine · constraints · ranking │
                         ├──────────────────────────────────────────┤
                         │        Repository / Data Access Layer     │
                         │        (interface — DB-agnostic)          │
                         ├───────────────┬───────────────┬───────────┤
                         │  MongoRepos   │  Integration Adapters      │
                         │  (impl now)   │  SyntheticDataAdapter(now) │
                         │               │  ERP/WMS/Supplier(future)  │
                         └───────┬───────┴───────────────────────────┘
                                 │
                         ┌───────▼────────┐
                         │    MongoDB      │
                         └─────────────────┘
```

**Layer responsibilities**

| Layer | Owns | Must NOT |
|---|---|---|
| Frontend | Presentation, interaction, local UI state, client-side validation, API calls | Business rules, resolution logic, direct DB access, hardcoded business data |
| API Layer | Routing, (de)serialization, HTTP status, schema validation | Business decisions, persistence details |
| AuthN/AuthZ | Identity verification, role + org-ownership + approval gating | Domain computation |
| Service Layer | Use-case orchestration, transactions, cross-entity policies | Low-level query mechanics, HTTP concerns |
| Domain | Deterministic constraints + ranking (the Resolution Engine) | I/O, DB, HTTP, framework coupling |
| Repository | CRUD + queries behind interfaces | Business rules |
| Adapters | Source data (synthetic now; ERP/WMS/API later) | Leaking source specifics upward |

Core loop the product must demonstrate:
**Shortage → Discover → Verify → Feasibility filter → Rank → Top 3 → Human approval → Simulated transfer/procurement → Resolution tracking → History.**

---

## B. Information Architecture (sections, pages, routes, role nav)

Route prefix for app pages: `/app/*` (SPA). Public: `/`, `/login`, `/register`, `/select-role`.

### Global sections (from spec §17)
- **OPERATIONS:** Dashboard, Shortages, Resolutions
- **NETWORK:** Hospitals, Inventory, Suppliers
- **ANALYSIS:** Experiments, Reports
- **RESEARCH:** Interviews, Competitors
- **SYSTEM:** Settings

The sidebar is **role-filtered** — a role only sees what it is authorised to use. We deliberately keep it lean (no over-population).

### Routes

| Route | Page | Hospital | Supplier | Admin |
|---|---|:--:|:--:|:--:|
| `/` | Marketing / landing (wordmark, "DEMONSTRATION DATA" banner) | ● | ● | ● |
| `/select-role` | Role selector (Hospital / Supplier / Administration) | ● | ● | ● |
| `/login`, `/register` | Auth (role-aware) | ● | ● | ○(no self-reg for admin) |
| `/app/dashboard` | Role dashboard | ● | ● | ● |
| `/app/shortages` | Shortage list | ● | – | ● |
| `/app/shortages/:id` | Shortage detail + Resolve workspace (candidates, Top 3) | ● | – | ● |
| `/app/resolutions` | Resolutions list | ● | – | ● |
| `/app/resolutions/:id` | Resolution detail + status timeline | ● | – | ● |
| `/app/hospitals` | Hospitals directory | scoped | – | ● |
| `/app/inventory` | Inventory (scoped by visibility policy) | scoped | – | ● |
| `/app/suppliers` | Suppliers directory | ● (view) | – | ● |
| `/app/opportunities` | Supply opportunities / open requests | – | ● | ● |
| `/app/fulfilments` | Pending fulfilments / simulated POs | – | ● | ● |
| `/app/products` | Supplier product catalog & availability | – | ● | ● |
| `/app/performance` | Supplier performance | – | ● | ● |
| `/app/experiments` | Experiment runner (baseline vs CARE-E) | – | – | ● |
| `/app/reports` | Reports | read | – | ● |
| `/app/research/interviews` | Interviews | – | – | ● |
| `/app/research/competitors` | Competitors | – | – | ● |
| `/app/admin/organisations` | Approvals (pending/approved/rejected/suspended) | – | – | ● |
| `/app/settings` | Profile / org settings | ● | ● | ● |

Legend: ● full · scoped = server-enforced visibility subset · read = read-only · – = hidden **and** blocked server-side · ○ = restricted.

### Role-specific dashboards (spec §18)
- **Hospital:** Active shortages → Resolution opportunities → Pending transfers → Inventory alerts → Supplier procurement → Network insights. Primary CTAs: **Report Shortage**, **Resolve Shortage**.
- **Supplier:** New supply opportunities → Open requests → Pending fulfilments → Available products/inventory → Performance → Org info.
- **Admin:** Active network situation → Hospitals → Suppliers → Inventory → Shortages → Resolutions → Experiments → Research → System controls.

---

## C. User / Organisation Architecture

Model is **Organisation → Users** and **Organisation → Facilities** (never `User → Hospital`).

```
Organisation (type: HOSPITAL_GROUP | SUPPLIER | CARE_E)
 ├── Users        (belong to org; have a role; have a status)
 ├── Facilities   (only for hospital groups; e.g., Hospital A/B/C)
 └── ApprovalStatus (org-level: pending/approved/rejected/suspended)
```

- **Roles (authorization):** `HOSPITAL`, `SUPPLIER`, `ADMIN`. Simple enum now; permission set is data-driven so RBAC can expand later without schema rewrite.
- **Membership:** every user has `organisation_id`; hospital users may have a default/primary `facility_id`.
- **Approval:** organisation-level `status ∈ {pending, approved, rejected, suspended}`. Hospital & supplier self-registration creates a `pending` org; admins approve. Users of a non-`approved` org can authenticate but are gated to a "pending approval" state (no operational access).
- **Admin:** no open self-registration; seeded via a controlled seed/admin-invite mechanism.

**Ownership boundaries (enforced server-side):**
- Supplier users act only within their own supplier org.
- Hospital users act within their own hospital group; cross-org inventory is visible only through the resolution workflow per visibility policy.
- Admin has broad network visibility.

---

## D. Domain Model (entities, relationships, key fields, ownership)

IDs are stable string UUID/ObjectId. All entities carry `created_at`, `updated_at` (UTC ISO). Derived values (e.g., `available_quantity`) are **not persisted**.

```
Organisation 1──* User
Organisation 1──* Facility           (hospital groups)
Facility     1──* InventoryRecord    (hospital inventory, per SKU)
Organisation 1──* SupplierProduct    (supplier availability, per SKU)  [supplier orgs]
Sku          1──* InventoryRecord
Sku          1──* SupplierProduct
Facility     1──* Shortage           (raised by a hospital facility)
Shortage     1──* Candidate          (discovered per resolution run)
Shortage     1──1 Resolution         (once a candidate is approved)
Resolution   1──1 Transfer | ProcurementOrder  (simulated fulfilment)
User         1──* AuditEvent         (append-only trail; future-expandable)
Experiment   1──* ExperimentResult
```

**Key entities & important fields**

- **Organisation:** `id, name, type(HOSPITAL_GROUP|SUPPLIER|CARE_E), org_subtype, status, created_at, updated_at`
- **Facility:** `id, organisation_id, name, code, address, storage_capabilities[], is_active`
- **User:** `id, organisation_id, primary_facility_id?, name, email(unique), role, password_hash?, google_sub?, is_active, created_at`
- **Sku:** `id, code(unique), name, category, unit, storage_condition(AMBIENT|COLD|FROZEN|CONTROLLED), shelf_life_days`
- **InventoryRecord:** `id, facility_id, sku_id, quantity_on_hand, reserved_quantity, safety_stock, storage_condition, earliest_expiry_date, transfer_allowed(bool), status(AVAILABLE|NON_AVAILABLE), updated_at`
  - **Derived (not stored):** `available_quantity = quantity_on_hand - reserved_quantity`
  - Designed for future batch/lot: `InventoryRecord` can gain a `batches[]` sub-collection without destructive change; expiry uses **remaining usable life**, not just "future date".
- **SupplierProduct:** `id, organisation_id(supplier), sku_id, available_quantity, unit_cost, lead_time_hours, min_order_qty, supplier_preference_rank, is_eligible`
- **Shortage:** `id, facility_id, sku_id, required_quantity, required_by(datetime), priority, status(OPEN|RESOLVING|RESOLVED|CANCELLED|UNRESOLVED), created_by, created_at`
- **Candidate (per resolution run, transient/persisted per run):** `id, shortage_id, source_type(INTERNAL|SUPPLIER), source_id, offered_quantity, est_time_hours, est_cost, classification(ELIGIBLE|CONDITIONAL|INELIGIBLE), reasons[], rank`
- **Resolution:** `id, shortage_id, chosen_candidate_id, source_type, source_id, quantity, est_time_hours, est_cost, status, approved_by, approved_at, reasoning_snapshot, created_at`
- **Transfer** (internal): `id, resolution_id, from_facility_id, to_facility_id, sku_id, quantity, status(DRAFT|REQUESTED|APPROVED|IN_TRANSIT|COMPLETED|REJECTED|CANCELLED), timeline[]`
- **ProcurementOrder** (supplier, simulated): `id, resolution_id, supplier_org_id, sku_id, quantity, unit_cost, status(DRAFT|REQUESTED|CONFIRMED|FULFILLED|CANCELLED), timeline[]`
- **Experiment / ExperimentResult:** run metadata + per-scenario outcomes (success, time, cost, internal transfers, supplier purchases, unresolved) — always labelled *synthetic simulation under defined assumptions*.
- **AuditEvent:** `id, actor_user_id, action, entity_type, entity_id, meta, created_at` (append-only; supports future compliance).

---

## E. Backend Architecture

FastAPI modular monolith. Business logic lives in **domain** and **services**, never in routers.

**Modules (bounded contexts):** `auth`, `organisations`, `facilities`, `catalog(sku)`, `inventory`, `suppliers`, `shortages`, `resolution`, `transfers`, `procurement`, `experiments`, `research`, `synthetic`, `common`.

**Resolution engine placement:** `domain/resolution/` — pure functions, no I/O.
- `constraints.py` — the 7 hard constraints (transfer permitted, sufficient available qty, safety-stock preserved, storage compatible, remaining usable life sufficient, time-window satisfiable, operationally eligible) → returns `(classification, reasons[])`.
- `ranking.py` — Stage-2 lexicographic ranking (feasibility → required-time compliance → speed → cost → inventory preservation → expiry avoidance → supplier preference → distance). Never lets an infeasible option outrank a feasible one.
- `engine.py` — orchestrates discover → verify → filter → rank → top-3, returns explainable result objects.
Services call the engine with data fetched via repositories/adapters; the engine itself is framework- and DB-free → **independently unit-testable**.

**API boundaries:** thin routers under `/api/v1/*`; Pydantic request/response schemas; dependency-injected `current_user` + authorization guards.

**Validation:** Pydantic v2 models at the boundary; domain-level invariants re-checked in services (never trust the client).

**Error handling:** centralized exception handlers → structured `{error: {code, message, details?}}`; correct HTTP codes (400/401/403/404/409/422/429/500); **no stack traces or internals leaked**; safe server-side logging.

**Health/observability:** `GET /api/v1/health`, structured request logging, safe error logging.

---

## F. Frontend Architecture

React SPA (CRA + Tailwind + shadcn/ui, per environment).

- **Page structure:** route-based pages under `src/pages/`; role-aware layout shell (`AppShell` with filtered sidebar + top bar with org name + persistent **"DEMONSTRATION / SYNTHETIC DATA"** badge).
- **Component strategy:** small (<50 lines ideal) presentational components in `src/components/`; shadcn primitives from `src/components/ui/`. No business/resolution logic in components.
- **API client strategy:** single `apiClient` (axios) using `REACT_APP_BACKEND_URL`, base path `/api/v1`, JWT attached via interceptor, centralized error normalization + 401 handling. Typed request/response wrappers per module in `src/api/`.
- **State management:** server state via **React Query** (caching, loading/error/success, no unnecessary duplication of server state); minimal global client state (auth/session, UI) via Context/Zustand. Do not mirror server data into global stores.
- **Forms:** react-hook-form + zod client validation *mirroring* server schemas; submit only when valid; server remains source of truth.
- **API feedback:** every request shows loading, success (toast via sonner where relevant), and error states.
- **Accessibility:** semantic HTML, keyboard nav, visible focus, labels, accessible dialogs (shadcn Radix), meaningful `<th>` scope, ARIA only where needed, status announcements (aria-live) — WCAG-oriented.
- **Responsive:** desktop-first, but critical flows (login, report shortage, resolve, approve) fully usable on tablet/mobile; sidebar collapses to sheet on mobile.
- **Design system:** deep institutional red/burgundy accent, charcoal/obsidian, warm off-white background, white surfaces; restrained green(success)/amber(warning); true red reserved for critical. No neon/glass/decorative animation/cartoon imagery. Final visual spec via `design_agent` at build time; CARE-E text wordmark for now.
- **data-testid** on every interactive & critical element.

---

## G. Database Architecture (MongoDB, integrity-first)

Although MongoDB is document-based, we enforce relational-grade integrity in the repository/service layer + JSON Schema validators.

- **Collections:** `organisations, facilities, users, skus, inventory_records, supplier_products, shortages, candidates, resolutions, transfers, procurement_orders, experiments, experiment_results, audit_events`.
- **Referential integrity:** foreign keys stored as string IDs; enforced in services (existence checks + guarded deletes). MongoDB JSON `$jsonSchema` validators enforce required fields, types, and enums at the DB level (stand-in for NOT NULL/CHECK).
- **Uniqueness / indexes:**
  - `users.email` unique; `skus.code` unique; `facilities.code` unique per org.
  - Query indexes: `inventory_records (sku_id, facility_id)`, `inventory_records (sku_id, status, transfer_allowed)`, `supplier_products (sku_id, is_eligible)`, `shortages (facility_id, status)`, `resolutions (shortage_id)`, `audit_events (entity_type, entity_id)`.
- **Transaction integrity:** multi-document writes (approve → create resolution → reserve inventory / create PO) run in MongoDB **multi-document transactions** to keep state consistent.
- **Timestamps:** `created_at`/`updated_at` UTC on every doc.
- **Derived values not persisted:** `available_quantity` computed in query/service layer.
- **"Migration" strategy:** a versioned, idempotent **schema/seed migration runner** (`migrations/` with ordered scripts + a `schema_version` doc) applies JSON Schema validators and indexes reproducibly — version-controlled analog to SQL migrations.
- **Base model conventions:** Pydantic `BaseDocument` with `PyObjectId` mapping `_id ↔ id`, `to_mongo()/from_mongo()`; no raw dicts returned from APIs (ObjectId is not JSON serializable).

---

## H. Integration Architecture (SyntheticDataAdapter → real sources)

A strict **data-source boundary** sits *below* services. Services depend on **repository interfaces**, not on data origin.

```
Service Layer
   │  depends on interfaces:  InventorySource, SupplierSource, FacilitySource ...
   ▼
DataSource / Adapter boundary
   ├── SyntheticDataAdapter        (MVP — reads seeded synthetic collections)
   ├── HospitalErpAdapter (future) │
   ├── WmsAdapter (future)         │ implement same interfaces
   ├── SupplierApiAdapter (future) │
   └── CsvEdiImportAdapter (future)┘
```

- MVP wires `SyntheticDataAdapter` (backed by seeded MongoDB collections) via a single composition/config point.
- Future adapters implement the same interfaces and are swapped by configuration — **the frontend and services never learn where data came from**.
- Adapters translate external shapes into domain models; no external shape leaks upward.

---

## I. Authentication / Authorization Architecture

**AuthN (identity) — separate from AuthZ (access):**
- **Email/password:** bcrypt-hashed passwords; JWT access tokens (short-lived) with secure secret from env; refresh strategy per integration playbook.
- **Google sign-in:** Emergent-managed Google auth; on first login, links/creates a user pending org association + approval.
- Login is **role-oriented**: `/select-role` → role-specific login/register.

**Registration & approval:**
- Hospital: Organisation + primary facility + user name + role + work email + password → creates `pending` org.
- Supplier: Organisation + org type + user name + work email + password → creates `pending` org.
- Admin: **no self-registration** (seeded/invited).
- Users of `pending/rejected/suspended` orgs are authenticated but gated (limited "status" screen only).

**AuthZ (server-enforced):**
- Guards compose three checks: **role** → **org ownership** → **approval status/visibility policy**.
- Protected-route model on frontend is convenience only; **every** `/api/v1` endpoint enforces authorization server-side.
- Visibility policies (spec §16) implemented as server-side query scoping (e.g., hospital sees only inventory relevant to its resolution workflow; suppliers see only requests/opportunities directed to them).

> Per platform rules, exact auth implementation will follow the `integration_expert` playbook (JWT + Emergent Google) before any auth code is written.

---

## J. Security Model

**MVP baseline:** no hardcoded secrets (env only); bcrypt password storage; controlled CORS (allow-list); ORM/parameterized-style queries (no string-built queries); XSS-safe React rendering; JWT handling appropriate to SPA; input validation at boundary + domain; safe structured error responses (no stack traces); **auth rate limiting / brute-force protection**; security-conscious headers; least-privilege data visibility enforced server-side; append-only `audit_events` for sensitive actions (approvals, resolution approvals).

**Future expansion points (not built now):** MFA, enterprise SSO, fine-grained RBAC/ABAC, full audit/compliance exports, secrets manager, per-field encryption, anomaly detection.

---

## K. Testing Strategy

- **Unit (domain, highest priority):** inventory availability, safety-stock rule, expiry/remaining-usable-life, transfer permission, storage compatibility, deadline feasibility, supplier fallback, candidate classification, ranking order (incl. "infeasible never outranks feasible"). Pure functions → fast & deterministic.
- **Integration (API/service):** auth+approval gating, shortage CRUD, resolution run, approval transaction (reservation/PO), visibility scoping, error contracts.
- **E2E (critical journey):** Login → Hospital dashboard → Create shortage → Resolve → Candidate verification → Top 3 → Human approval → Resolution status/history. Plus supplier opportunity view and admin approval as later milestones.
- **Gate:** do not advance a milestone while its critical tests fail. `testing_agent` runs after each milestone.

---

## L. Folder / Project Structure (proposed)

```
/app
├── backend/
│   ├── server.py                     # FastAPI app factory, /api mount, health, error handlers
│   ├── core/                         # config, security, db client, logging, exceptions
│   ├── api/v1/                       # routers: auth, orgs, facilities, skus, inventory,
│   │                                 #          suppliers, shortages, resolution,
│   │                                 #          transfers, procurement, experiments,
│   │                                 #          research, admin, synthetic
│   ├── schemas/                      # Pydantic request/response models
│   ├── services/                     # application/use-case orchestration + transactions
│   ├── domain/
│   │   ├── models.py                 # domain entities (BaseDocument, PyObjectId)
│   │   └── resolution/               # constraints.py · ranking.py · engine.py  (pure)
│   ├── repositories/
│   │   ├── interfaces.py             # DB-agnostic contracts
│   │   └── mongo/                    # Mongo implementations
│   ├── integrations/
│   │   └── synthetic/                # SyntheticDataAdapter + generators/config
│   ├── migrations/                   # ordered, idempotent schema/index/seed runners
│   ├── tests/                        # unit · integration
│   ├── requirements.txt
│   └── .env
├── frontend/
│   └── src/
│       ├── api/                      # apiClient + per-module typed calls
│       ├── pages/                    # route pages (operations/network/analysis/research/system)
│       ├── components/               # shared + ui/ (shadcn)
│       ├── hooks/  lib/  context/    # react-query, auth context, utils
│       ├── App.js  index.js  index.css
│       └── .env
└── memory/
    ├── ARCHITECTURE.md               # this document (source of truth)
    ├── PRD.md                        # created at first build finish
    └── test_credentials.md
```

---

## M. Initial API Contract (`/api/v1`)

Auth & identity
- `POST /auth/register/hospital` · `POST /auth/register/supplier` — creates pending org+user
- `POST /auth/login` · `POST /auth/google` · `POST /auth/refresh` · `POST /auth/logout`
- `GET /auth/me` — current user, org, role, approval status

Organisations & approvals (admin)
- `GET /organisations` · `GET /organisations/{id}`
- `PATCH /organisations/{id}/status` — approve/reject/suspend
- `GET /facilities` · `POST /facilities` · `GET /facilities/{id}`

Catalog & inventory
- `GET /skus` · `GET /skus/{id}`
- `GET /inventory` (visibility-scoped) · `GET /inventory/{id}` · `PATCH /inventory/{id}` (owner only)

Suppliers
- `GET /suppliers` · `GET /suppliers/{id}` · `GET /supplier-products` (scoped)

Shortages & resolution (core)
- `GET /shortages` · `POST /shortages` · `GET /shortages/{id}` · `PATCH /shortages/{id}`
- `POST /shortages/{id}/resolve` — **runs deterministic engine** → returns candidates + **Top 3** with reasons & trade-offs (no state change)
- `POST /shortages/{id}/approve` — human approval of a chosen candidate → creates Resolution + simulated Transfer/PO in one transaction

Resolutions / transfers / procurement
- `GET /resolutions` · `GET /resolutions/{id}`
- `PATCH /transfers/{id}/status` · `PATCH /procurement-orders/{id}/status` (simulated transitions)

Analysis & research (admin)
- `POST /experiments/run` (baseline vs CARE-E, labelled synthetic) · `GET /experiments/{id}`
- `GET /reports/summary`
- `GET/POST /research/interviews` · `GET/POST /research/competitors`

Synthetic data control
- `POST /synthetic/seed` · `POST /synthetic/reset` · `GET /synthetic/config` (configurable counts: hospitals/SKUs/inventory/suppliers/scenarios)

System
- `GET /health`

All endpoints: authorization enforced, validated payloads, typed responses, structured errors.

---

## N. Critical Business Rules — where they live

**All resolution rules live in `backend/domain/resolution/` and nowhere else.**

- **Hard constraints (`constraints.py`)** — evaluated per internal candidate:
  1. transfer permitted, 2. sufficient `available_quantity` (= `quantity_on_hand - reserved_quantity`), 3. safety-stock preserved (`remaining_quantity >= safety_stock`), 4. storage condition compatible, 5. remaining usable life sufficient, 6. required time window satisfiable, 7. operationally eligible → yields classification **ELIGIBLE / CONDITIONAL / INELIGIBLE** with **explicit reasons[]** for every candidate.
- **Two-stage selection (`engine.py` + `ranking.py`):** Stage 1 filters by feasibility; Stage 2 ranks feasible options **lexicographically** by the §11 priority order. Infeasible options can never outrank feasible ones. Returns **Top 3** with source, source type, quantity, est. time, est. cost, status, reasoning, trade-offs.
- Engine is pure (no DB/HTTP/LLM), called by services which supply data via repositories/adapters → deterministic, transparent, independently testable.
- Human-in-the-loop: engine only recommends; `POST /approve` (a human action) is the only path that changes inventory/creates simulated fulfilment.

---

## O. MVP Implementation Sequence (milestones)

Built one at a time, tested before proceeding, no scope expansion without authorization.

- **M0 — Foundation:** app skeleton, config/env, DB client, base models, error handling, health, migration runner, CI-able test harness. *(dep: none)*
- **M1 — Auth & Org model:** integration_expert playbook → JWT email/password + Google; Organisation/User/Facility; registration + approval states; role-oriented login; server-side guards. *(dep: M0)*
- **M2 — Synthetic data layer:** `SyntheticDataAdapter` + generators + seed/reset endpoints; configurable dataset (5 hospitals / 100 SKUs / 500 inventory / 20 suppliers / 100 scenarios); catalog + inventory + supplier products. *(dep: M0)*
- **M3 — Resolution engine (domain):** constraints + ranking + engine as pure functions with full unit tests **before** any UI. *(dep: M2 data shapes)*
- **M4 — Core hospital loop (frontend+backend):** shortages CRUD, `resolve` (Top 3), candidate verification UI, `approve`, resolution + simulated transfer/PO, resolution history; E2E of the critical journey. *(dep: M1,M2,M3)*
- **M5 — Supplier experience:** opportunities, open requests, fulfilments, products, performance, visibility scoping. *(dep: M1,M2,M4)*
- **M6 — Admin & analysis:** approvals console, network overview, experiments (baseline vs CARE-E), reports, research pages. *(dep: M1–M5)*
- **M7 — Hardening:** rate limiting, accessibility & responsive pass, audit events, security headers, polish. *(dep: prior)*

---

## P. Risks

- **Architectural:** MongoDB modelling a relational domain — mitigated by JSON Schema validators, service-enforced FKs, transactions, and a DB-agnostic repository layer. Risk of business logic leaking into routers/UI — mitigated by strict domain isolation + review gate.
- **Security:** cross-org data leakage; JWT handling; brute-force. Mitigated by server-side visibility scoping, playbook-driven auth, rate limiting, structured errors.
- **Product:** demo mistaken for real outcomes — mitigated by persistent "SYNTHETIC DATA" labelling and "synthetic simulation under defined assumptions" on all experiment output. Risk of feeling like generic inventory CRUD — mitigated by centering the resolution/approval workflow, not tables.
- **Data-model:** future batch/lot & FEFO — mitigated by extensible InventoryRecord (batches[] addable), remaining-usable-life expiry logic, non-persisted derived values.
- **Integration:** frontend coupling to synthetic source — mitigated by adapter boundary + repository interfaces (frontend never learns data origin).
- **Scope-creep:** the spec's future list is large — mitigated by milestone gating, explicit non-goals (§32), and no independent expansion.

---

## Q. Open Decisions (need product/technical sign-off before/at build)

1. **JWT transport:** Authorization header (Bearer) vs httpOnly cookie. Recommendation: Bearer for SPA simplicity; revisit CSRF if cookies chosen. *(finalize in M1 via integration_expert.)*
2. **Google sign-in role/org binding:** how a Google user is associated to an org & role on first login (invite code vs post-login org-claim + admin approval). Recommendation: post-login org-claim → pending approval.
3. **Candidate persistence:** persist candidates per resolution run (audit/replayability) vs compute-on-demand only. Recommendation: persist the run snapshot in `reasoning_snapshot`/candidates for explainability.
4. **Inventory reservation on approval:** decrement `reserved_quantity` at approval vs at transfer completion. Recommendation: reserve at approval, finalize at completion.
5. **Distance/logistics input:** synthetic distance/lead-time model assumptions for ranking factor 8. Needs a defined synthetic assumption set.
6. **Experiment scenario definition:** exact synthetic scenario schema & baseline assumptions ("Immediate Supplier Purchase"). Needs sign-off before M6.
7. **Admin seeding mechanism:** seed script vs one-time bootstrap endpoint. Recommendation: controlled seed script + `test_credentials.md`.
8. **Visibility policy defaults:** precise definition of "inventory relevant to a shortage" for hospital scoping (same SKU + transfer_allowed + network membership?). Needs confirmation.

---

## Appendix — PostgreSQL Future-Migration Path

The domain, services, and **repository interfaces** are database-agnostic. Migrating to PostgreSQL later means:
- Implement `repositories/postgres/` against the same interfaces (SQLAlchemy models mirroring the domain entities; the relationships in Section D map directly to tables + FKs).
- Convert JSON Schema validators → SQL `NOT NULL`/`CHECK`/`UNIQUE`/FK constraints; the `migrations/` runner concept maps to Alembic.
- `available_quantity` stays derived (view or query expression).
- Swap the composition root from Mongo repos to Postgres repos; **services, domain engine, API, and frontend remain unchanged.**
No frontend rewrite is required — consistent with the §21 integration requirement.
