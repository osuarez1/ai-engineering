"""Catalog entries migrated from estimation/v2/examples.j2."""

from app.schemas.request_form import DetailLevel, OutputFormat, ProjectType, ReferenceProject

V2_CATALOG_RAW: list[tuple[OutputFormat, DetailLevel, list[ReferenceProject]]] = [
    (
        OutputFormat.PHASES_TABLE,
        DetailLevel.SUMMARY,
        [
            ReferenceProject(
                name='Example 1 — Startup MVP Landing Page',
                scope_summary='Single-page marketing site with waitlist form, responsive layout, and Plausible\nanalytics. No CMS; copy provided by the client.',
                body='**Totals:** 48 hours · 2,900 EUR · Team: 1 full-stack dev, designer (2 days) ·\nDuration: 2 weeks',
                project_type=ProjectType.WEB_SAAS,
            ),
            ReferenceProject(
                name='Example 2 — GitHub-to-Slack Deploy Notifier',
                scope_summary='Webhook listener that posts release notes to a Slack channel when a GitHub\nAction completes. Includes secret rotation and retry logic.',
                body='**Totals:** 64 hours · 4,000 EUR · Team: 1 backend developer · Duration: 3 weeks',
                project_type=ProjectType.INTERNAL_TOOL,
            ),
        ],
    ),
    (
        OutputFormat.PHASES_TABLE,
        DetailLevel.MEDIUM,
        [
            ReferenceProject(
                name='Example 1 — Courier Dispatch Mobile App',
                scope_summary='Driver app for same-day couriers: route list, proof-of-delivery photos, GPS\ncheck-in, and offline queue. Ops dashboard for dispatchers (read-only v1).',
                body='#### Phase 1 — Shaping\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Field interviews and flow mapping | 10 | 625 |\n| Mobile UI kit (6 screens) | 20 | 1,000 |\n\n#### Phase 2 — Build\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Offline route sync | 36 | 2,250 |\n| POD capture and upload | 24 | 1,500 |\n| Dispatcher dashboard (MVP) | 20 | 1,250 |\n\n#### Phase 3 — Ship\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Device QA and pilot rollout | 24 | 1,500 |\n\n**Totals:** 134 hours · 8,125 EUR · Team: 1 mobile lead, 1 designer (part-time) ·\nDuration: 8 weeks',
                project_type=ProjectType.MOBILE_APP,
            ),
        ],
    ),
    (
        OutputFormat.PHASES_TABLE,
        DetailLevel.DETAILED,
        [
            ReferenceProject(
                name='Example 1 — Procurement Workflow Portal',
                scope_summary='Internal portal for purchase requests: multi-step approvals, budget caps,\nvendor directory, and export to the finance ERP. Azure AD SSO.',
                body='#### Phase 1 — Discovery\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Process mapping workshops | 16 | 1,000 |\n| UX flows and component library | 24 | 1,200 |\n| Integration spike (ERP API) | 12 | 750 |\n\n#### Phase 2 — Core workflows\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Request intake and routing engine | 40 | 2,500 |\n| Approval chains and notifications | 32 | 2,000 |\n| Vendor management module | 24 | 1,500 |\n\n#### Phase 3 — Compliance and launch\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Audit trail and reporting | 20 | 1,250 |\n| Security review and UAT | 28 | 1,750 |\n\n**Totals:** 196 hours · 12,200 EUR · Team: 2 backend devs, 1 frontend, 1 designer ·\nDuration: 14 weeks',
                project_type=ProjectType.INTERNAL_TOOL,
            ),
        ],
    ),
    (
        OutputFormat.LINE_ITEMS,
        DetailLevel.SUMMARY,
        [
            ReferenceProject(
                name='Example 1 — Webhook Health Monitor',
                scope_summary='Cron job plus dashboard that pings customer webhook URLs and alerts on\nfailures. Single-tenant admin UI.',
                body='**Totals:** 52 hours · 3,250 EUR · Team: 1 backend developer · Duration: 3 weeks',
                project_type=ProjectType.WEB_SAAS,
            ),
        ],
    ),
    (
        OutputFormat.LINE_ITEMS,
        DetailLevel.MEDIUM,
        [
            ReferenceProject(
                name='Example 1 — Restaurant Reservation API',
                scope_summary='REST API for table holds, party size, and SMS confirmations. Postgres backing\nstore; OpenAPI spec for partner integrations.',
                body='1. **Schema and availability engine** — 32 h · 2,000 EUR — slot rules and blackout dates.\n2. **Booking endpoints and idempotency** — 28 h · 1,750 EUR — create, amend, cancel.\n3. **Twilio SMS hooks** — 16 h · 1,000 EUR — confirmation and reminder texts.\n4. **Partner docs and staging environment** — 12 h · 750 EUR — OpenAPI + seed data.\n\n**Totals:** 88 hours · 5,500 EUR · Team: 1 API engineer · Duration: 5 weeks',
                project_type=ProjectType.WEB_SAAS,
            ),
        ],
    ),
    (
        OutputFormat.LINE_ITEMS,
        DetailLevel.DETAILED,
        [
            ReferenceProject(
                name='Example 1 — Multi-tenant Audit Log Service',
                scope_summary='Centralised audit ingestion API with tenant isolation, retention policies, and\nSIEM export. SOC2-friendly access controls.',
                body='1. **Tenant model and authZ** — 40 h · 2,500 EUR — org boundaries and API keys.\n2. **Ingestion pipeline (Kafka → store)** — 48 h · 3,000 EUR — ordering and back-pressure.\n3. **Query API and pagination** — 32 h · 2,000 EUR — filter by actor, resource, time.\n4. **Retention jobs and export adapters** — 24 h · 1,500 EUR — S3 archive + Splunk HEC.\n5. **Load testing and runbooks** — 20 h · 1,250 EUR — capacity baseline and on-call docs.\n\n**Totals:** 164 hours · 10,250 EUR · Team: 2 senior backend engineers · Duration: 10 weeks',
                project_type=ProjectType.WEB_SAAS,
            ),
        ],
    ),
    (
        OutputFormat.NARRATIVE,
        DetailLevel.SUMMARY,
        [
            ReferenceProject(
                name='Example 1 — Personal Finance Tracker PWA',
                scope_summary='Installable PWA that imports bank CSVs, tags transactions, and shows monthly\nburn. No open-banking integrations in v1.',
                body='The build centres on a secure client-side parser and a simple dashboard. We scoped\n**60 hours · 3,750 EUR** with one full-stack developer over **3 weeks**, assuming\nprovided categorisation rules and no multi-currency support.',
                project_type=ProjectType.WEB_SAAS,
            ),
        ],
    ),
    (
        OutputFormat.NARRATIVE,
        DetailLevel.MEDIUM,
        [
            ReferenceProject(
                name='Example 1 — B2B Referral Program Platform',
                scope_summary='Partners generate tracked links, earn commissions on qualified sign-ups, and\nwithdraw via Stripe Connect. Admin console for fraud review.',
                body='Discovery and schema design take the first two weeks, followed by referral attribution\nlogic and the partner portal. Payout automation and admin tooling close the build.\n**Totals:** 152 hours · 9,500 EUR · Team: 1 full-stack lead, 1 frontend contractor ·\nDuration: 9 weeks. Main risk: payment compliance review may add calendar time.',
                project_type=ProjectType.WEB_SAAS,
            ),
        ],
    ),
    (
        OutputFormat.NARRATIVE,
        DetailLevel.DETAILED,
        [
            ReferenceProject(
                name='Example 1 — Clinical Trial Site Portal',
                scope_summary='Sites enrol patients, upload protocol deviations, and message monitors.\n21 CFR Part 11 considerations; role-based access per study arm.',
                body='The programme splits into compliance-heavy foundations (identity, e-signatures, audit\nlogs), study workflows (enrolment, visit scheduling, document uploads), and monitor\ncollaboration (threaded messaging, escalation rules). Integration with the sponsor CTMS\nis the longest pole. We budget **320 hours · 20,000 EUR** across **two full-stack\ndevelopers, a compliance consultant (advisory), and a QA lead in the final month** over\n**18 weeks**. Assumptions include a stable CTMS sandbox; regulatory validation is out\nof scope for this estimate.',
                project_type=ProjectType.INTERNAL_TOOL,
            ),
        ],
    ),
]
