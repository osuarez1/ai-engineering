"""Catalog entries migrated from estimation/v1/examples.j2."""

from app.schemas.request_form import DetailLevel, OutputFormat, ProjectType, ReferenceProject

V1_CATALOG_RAW: list[tuple[OutputFormat, DetailLevel, list[ReferenceProject]]] = [
    (
        OutputFormat.PHASES_TABLE,
        DetailLevel.SUMMARY,
        [
            ReferenceProject(
                name='Example 1 — Marketing Landing Page Refresh',
                scope_summary='Redesign and rebuild a single-product marketing landing page with a contact\nform, responsive layout, and basic analytics hooks. Existing brand guidelines apply;\nno CMS or multi-page site.',
                body='**Totals:** 56 hours · 3,400 EUR · Team: 1 frontend developer, 1 designer (3 days) ·\nDuration: 3 weeks',
                project_type=ProjectType.WEB_SAAS,
            ),
            ReferenceProject(
                name='Example 2 — Slack-to-Jira Bug Reporter',
                scope_summary='Internal slash command that posts structured bug reports from Slack channels\ninto a Jira project. Includes OAuth setup and field mapping for title, severity, and\nreporter.',
                body='**Totals:** 72 hours · 4,500 EUR · Team: 1 backend developer · Duration: 4 weeks',
                project_type=ProjectType.INTERNAL_TOOL,
            ),
        ],
    ),
    (
        OutputFormat.PHASES_TABLE,
        DetailLevel.MEDIUM,
        [
            ReferenceProject(
                name='Example 1 — Field Service Mobile App',
                scope_summary='Cross-platform mobile app for HVAC technicians: offline work orders, photo\ncapture, signature collection, and sync on reconnect. Push notifications for urgent\ndispatch plus a read-only supervisor web panel.',
                body='#### Phase 1 — Discovery and design\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Requirements workshops | 12 | 750 |\n| Mobile UI/UX design (8 screens) | 24 | 1,200 |\n\n#### Phase 2 — Core build\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Offline-first sync engine | 40 | 2,500 |\n| Work order CRUD and media upload | 32 | 2,000 |\n| Push notifications (FCM/APNs) | 16 | 1,000 |\n\n#### Phase 3 — Delivery\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Supervisor admin panel | 24 | 1,500 |\n| QA, device testing, store submission | 28 | 1,750 |\n\n**Totals:** 176 hours · 10,700 EUR · Team: 1 senior mobile dev, 1 designer\n(part-time), 1 QA engineer (last 2 weeks) · Duration: 9 weeks',
                project_type=ProjectType.MOBILE_APP,
            ),
            ReferenceProject(
                name='Example 2 — Retail Sales Analytics Pipeline',
                scope_summary='Batch ETL ingesting POS and e-commerce CSV exports into BigQuery, dbt models\nfor daily revenue KPIs, and a Looker Studio dashboard for regional managers.',
                body='#### Phase 1 — Data foundation\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Schema mapping and source audit | 16 | 1,000 |\n| Ingestion jobs (Airflow + S3 → BigQuery) | 32 | 2,000 |\n\n#### Phase 2 — Modelling and reporting\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| dbt staging and mart models | 40 | 2,500 |\n| Looker Studio dashboard (6 pages) | 20 | 1,250 |\n\n#### Phase 3 — Hardening\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Data quality checks and alerting | 16 | 1,000 |\n| Testing and production cutover | 16 | 1,000 |\n\n**Totals:** 140 hours · 8,750 EUR · Team: 1 data engineer (lead), 1 analytics engineer\n(part-time) · Duration: 7 weeks',
                project_type=ProjectType.DATA_PIPELINE,
            ),
        ],
    ),
    (
        OutputFormat.PHASES_TABLE,
        DetailLevel.DETAILED,
        [
            ReferenceProject(
                name='Example 1 — Employee Onboarding Internal Tool',
                scope_summary='Internal web app replacing spreadsheet onboarding: configurable checklists per\ndepartment, document collection, approval workflows, Okta SSO, and email reminders.',
                body='#### Phase 1 — Discovery and design\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Stakeholder workshops and workflow mapping | 16 | 1,000 |\n| UI wireframes and design system setup | 20 | 1,000 |\n| Technical architecture and threat model | 12 | 750 |\n\n#### Phase 2 — Platform and access\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Okta SSO and role-based access control | 24 | 1,500 |\n| Checklist engine and department templates | 36 | 2,250 |\n| Document upload and virus scanning | 16 | 1,000 |\n\n#### Phase 3 — Workflows and notifications\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Multi-step approval workflow | 28 | 1,750 |\n| Email reminder and escalation service | 12 | 750 |\n| Admin reporting (onboarding status) | 16 | 1,000 |\n\n#### Phase 4 — Quality and rollout\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Integration testing with HR systems | 16 | 1,000 |\n| HR pilot, bug fixing, and documentation | 20 | 1,250 |\n| Deployment, monitoring, and handover | 12 | 750 |\n\n**Totals:** 228 hours · 14,250 EUR · Team: 1 full-stack developer (lead), 1 designer\n(part-time), HR stakeholder for UAT · Duration: 11 weeks\n\n**Assumptions:** Okta tenant already provisioned; HR provides checklist templates before\nbuild starts. **Risks:** Legacy employee data export format may require extra mapping.',
                project_type=ProjectType.INTERNAL_TOOL,
            ),
            ReferenceProject(
                name='Example 2 — Multi-tenant Subscription Billing SaaS',
                scope_summary='B2B SaaS module for plan management, Stripe billing, usage metering, and a\ncustomer self-service portal with invoice history.',
                body='#### Phase 1 — Discovery and design\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Billing rules workshops | 16 | 1,000 |\n| Portal UX design (10 screens) | 28 | 1,400 |\n| Data model and Stripe integration design | 16 | 1,000 |\n\n#### Phase 2 — Billing core\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Stripe subscription and webhook handlers | 40 | 2,500 |\n| Usage metering ingestion API | 24 | 1,500 |\n| Plan and entitlement engine | 32 | 2,000 |\n\n#### Phase 3 — Customer portal\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| Self-service portal (plans, invoices, payment method) | 36 | 2,250 |\n| Admin console for support overrides | 20 | 1,250 |\n\n#### Phase 4 — Compliance and launch\n\n| Task | Hours | Cost (EUR) |\n|------|------:|-----------:|\n| PCI-scoped security review and logging | 16 | 1,000 |\n| End-to-end billing scenario testing | 24 | 1,500 |\n| Staged rollout and runbook documentation | 12 | 750 |\n\n**Totals:** 264 hours · 16,650 EUR · Team: 1 senior backend dev, 1 full-stack dev,\n1 designer (part-time) · Duration: 12 weeks\n\n**Assumptions:** Stripe account and tax settings are pre-configured. **Risks:** Proration\nedge cases for mid-cycle plan changes may add 1–2 weeks if not scoped early.',
                project_type=ProjectType.WEB_SAAS,
            ),
        ],
    ),
    (
        OutputFormat.LINE_ITEMS,
        DetailLevel.SUMMARY,
        [
            ReferenceProject(
                name='Example 1 — Podcast RSS Feed Validator',
                scope_summary='CLI tool and small web UI that validates podcast RSS feeds against common\ndirectory requirements and reports fixable errors.',
                body='#### Summary\n\n1. **Feed parser and rule engine** — 32 h · 2,000 EUR — Core validation logic against\n   Apple and Spotify feed specs.\n2. **Web upload UI** — 16 h · 1,000 EUR — Simple drag-and-drop report page.\n\n**Summary block:** 48 hours · 3,000 EUR · Team: 1 full-stack developer · Duration: 3 weeks',
                project_type=ProjectType.WEB_SAAS,
            ),
            ReferenceProject(
                name='Example 2 — Office Room Booking Kiosk',
                scope_summary='Tablet kiosk app mounted outside meeting rooms showing availability and\nallowing walk-up 30-minute bookings synced to Google Calendar.',
                body='#### Summary\n\n1. **Calendar integration** — 24 h · 1,500 EUR — Read/write against Google Calendar API.\n2. **Kiosk touchscreen UI** — 20 h · 1,250 EUR — Large-touch interface for room status.\n\n**Summary block:** 44 hours · 2,750 EUR · Team: 1 frontend developer · Duration: 3 weeks',
                project_type=ProjectType.INTERNAL_TOOL,
            ),
        ],
    ),
    (
        OutputFormat.LINE_ITEMS,
        DetailLevel.MEDIUM,
        [
            ReferenceProject(
                name='Example 1 — Warehouse Barcode Scanner App',
                scope_summary='Android app for warehouse staff to scan barcodes, adjust stock levels, and\nsync counts to an existing REST inventory API.',
                body='#### Discovery\n\n1. **API audit and field mapping** — 8 h · 500 EUR — Document existing inventory endpoints\n   and error codes before mobile work begins.\n2. **UX flows for scan-and-adjust** — 12 h · 600 EUR — Wireframes for scan, quantity edit,\n   and conflict resolution screens.\n\n#### Implementation\n\n3. **Barcode scanning module** — 24 h · 1,500 EUR — Camera integration with offline queue.\n4. **Stock adjustment sync layer** — 28 h · 1,750 EUR — Optimistic UI with retry on reconnect.\n5. **Admin device provisioning** — 12 h · 750 EUR — QR-based device pairing for ten tablets.\n\n#### QA\n\n6. **Field testing and bug fixing** — 16 h · 1,000 EUR — On-site pilot with two warehouse\n   aisles before full rollout.\n\n**Summary block:** 100 hours · 6,100 EUR · Team: 1 mobile developer, 1 designer\n(part-time) · Duration: 6 weeks',
                project_type=ProjectType.MOBILE_APP,
            ),
            ReferenceProject(
                name='Example 2 — Customer Support Ticket Router',
                scope_summary='Service that classifies inbound support emails with a lightweight ML model and\nroutes them to the correct Zendesk group with priority tags.',
                body='#### Discovery\n\n1. **Label taxonomy workshop** — 8 h · 500 EUR — Align support leads on categories and\n   escalation rules.\n2. **Historical ticket sampling** — 8 h · 500 EUR — Export and anonymise 2,000 tickets for\n   training labels.\n\n#### Backend\n\n3. **Email ingestion webhook** — 16 h · 1,000 EUR — Parse MIME payloads from SendGrid.\n4. **Classifier training pipeline** — 24 h · 1,500 EUR — Fine-tune a small text classifier\n   with evaluation metrics.\n5. **Zendesk routing integration** — 20 h · 1,250 EUR — Create/update tickets with group\n   and priority fields.\n\n#### Operations\n\n6. **Monitoring dashboard and retrain job** — 12 h · 750 EUR — Weekly accuracy report and\n   model refresh script.\n\n**Summary block:** 88 hours · 5,500 EUR · Team: 1 ML engineer, 1 backend developer\n(part-time) · Duration: 5 weeks',
                project_type=ProjectType.INTERNAL_TOOL,
            ),
        ],
    ),
    (
        OutputFormat.LINE_ITEMS,
        DetailLevel.DETAILED,
        [
            ReferenceProject(
                name='Example 1 — IoT Cold-Chain Monitoring Dashboard',
                scope_summary='Real-time dashboard for refrigerated logistics: ingest temperature readings\nfrom MQTT sensors, alert on threshold breaches, and provide fleet-wide compliance reports.',
                body='#### Discovery\n\n1. **Sensor protocol and SLA review** — 12 h · 750 EUR — Confirm MQTT topics, sampling\n   intervals, and regulatory retention requirements.\n2. **Alerting rules workshop** — 8 h · 500 EUR — Define escalation paths for minor vs\n   critical temperature deviations.\n3. **Architecture and capacity planning** — 12 h · 750 EUR — Size TimescaleDB cluster for\n   5,000 sensors reporting every 60 seconds.\n\n#### Design\n\n4. **Dashboard wireframes (12 views)** — 20 h · 1,000 EUR — Fleet map, truck detail, alert\n   inbox, and compliance export screens.\n5. **Design system for ops consoles** — 8 h · 400 EUR — High-contrast components for\n   24/7 control-room use.\n\n#### Backend\n\n6. **MQTT ingestion service** — 32 h · 2,000 EUR — Durable subscriber with dead-letter queue.\n7. **TimescaleDB schema and retention jobs** — 24 h · 1,500 EUR — Hypertables and automated\n   archival past 90 days.\n8. **Alert engine and notification fan-out** — 28 h · 1,750 EUR — Email, SMS, and PagerDuty\n   integrations with deduplication.\n9. **Compliance PDF report generator** — 16 h · 1,000 EUR — Scheduled batch exports per depot.\n\n#### Frontend\n\n10. **Real-time fleet map and truck detail** — 36 h · 2,250 EUR — WebSocket-driven UI with\n    five-minute rollups.\n11. **Alert management console** — 20 h · 1,250 EUR — Acknowledge, snooze, and annotate alerts.\n\n#### Quality and deployment\n\n12. **Load testing and failover drill** — 16 h · 1,000 EUR — Simulate broker outage and\n    verify backlog recovery.\n13. **Staging pilot with two depots** — 20 h · 1,250 EUR — On-site validation with operations\n    staff.\n14. **Production cutover and runbooks** — 12 h · 750 EUR — Deployment checklist and on-call\n    playbooks.\n\n**Summary block:** 264 hours · 16,150 EUR · Team: 1 backend lead, 1 frontend developer,\n1 designer (part-time), 1 DevOps engineer (part-time) · Duration: 13 weeks\n\n**Assumptions:** MQTT broker and TLS certificates are provisioned by client infra.\n**Risks:** Sensor firmware inconsistencies may require per-device normalisation layer.',
                project_type=ProjectType.DATA_PIPELINE,
            ),
            ReferenceProject(
                name='Example 2 — Legal Contract Review Copilot',
                scope_summary='Internal tool letting legal analysts upload NDAs, highlight non-standard clauses\nagainst a playbook, and export a redline summary. Uses RAG over an internal clause library.',
                body='#### Discovery\n\n1. **Playbook extraction sessions** — 16 h · 1,000 EUR — Codify acceptable vs flagged\n   clause patterns with legal team.\n2. **Document corpus audit** — 12 h · 750 EUR — Inventory formats (DOCX, PDF) and OCR needs.\n3. **Security and data-residency review** — 8 h · 500 EUR — Confirm on-prem deployment\n   constraints and PII handling.\n\n#### Design\n\n4. **Analyst workflow wireframes** — 16 h · 800 EUR — Upload, review queue, clause diff,\n   and export flows.\n5. **Annotation UI components** — 12 h · 600 EUR — Side-by-side clause comparison patterns.\n\n#### Backend\n\n6. **Document ingestion and OCR pipeline** — 32 h · 2,000 EUR — Normalise uploads to\n   searchable text with page anchors.\n7. **Clause library vector index** — 24 h · 1,500 EUR — Embed playbook clauses for retrieval.\n8. **RAG comparison service** — 40 h · 2,500 EUR — Retrieve similar clauses and score deviations.\n9. **Redline summary export (DOCX/PDF)** — 20 h · 1,250 EUR — Generate analyst-ready reports.\n\n#### Frontend\n\n10. **Review queue and upload portal** — 28 h · 1,750 EUR — Role-based access for analysts\n    and managers.\n11. **Clause diff and override UI** — 32 h · 2,000 EUR — Accept, flag, or annotate model\n    suggestions.\n\n#### Quality and deployment\n\n12. **Accuracy benchmarking on 50 contracts** — 24 h · 1,500 EUR — Measure precision/recall\n    with legal reviewers.\n13. **Penetration test remediation** — 16 h · 1,000 EUR — Address findings before go-live.\n14. **Training sessions and documentation** — 12 h · 750 EUR — Handover to legal ops team.\n\n**Summary block:** 292 hours · 18,200 EUR · Team: 1 ML engineer, 1 full-stack developer,\n1 designer (part-time), legal SME for UAT · Duration: 14 weeks\n\n**Assumptions:** Clause library under 10,000 entries at launch. **Risks:** Scanned PDF\nquality may degrade retrieval accuracy without manual OCR cleanup.',
                project_type=ProjectType.WEB_SAAS,
            ),
        ],
    ),
    (
        OutputFormat.NARRATIVE,
        DetailLevel.SUMMARY,
        [
            ReferenceProject(
                name='Example 1 — Fitness Class Booking Widget',
                scope_summary="A embeddable booking widget for boutique gyms: class schedule display, single-class\ncheckout via Stripe, and confirmation emails. Runs as a JavaScript snippet on the\nclient's existing WordPress site.",
                body="**Effort and cost**\nMost effort sits in Stripe Checkout integration and synchronising class capacity with a\nsimple backend API. Design is limited to matching the gym's existing colours. The work\ntotals roughly 64 hours at blended developer rates, approximately 4,000 EUR.\n\n**Team and timeline**\nOne full-stack developer handles the entire delivery in about four weeks, including a\none-week buffer for payment testing in Stripe's sandbox.\n\n**Risks and assumptions**\nAssumes the gym provides a static class timetable CSV updated weekly. WordPress plugin\nconflicts are out of scope.",
                project_type=ProjectType.WEB_SAAS,
            ),
            ReferenceProject(
                name='Example 2 — Vendor Invoice OCR Portal',
                scope_summary='A lightweight internal portal where accounts-payable staff upload vendor PDF invoices and\nreceive extracted fields (vendor, amount, due date) for entry into the existing ERP.',
                body='**Effort and cost**\nThe project centres on a managed OCR API wrapper and a three-screen upload/review/export\nflow. Estimated effort is 80 hours, roughly 5,000 EUR, with most time spent on validation\nrules and ERP CSV export formatting.\n\n**Team and timeline**\nA single backend-leaning full-stack developer delivers in five weeks, including two weeks\nof parallel UAT with the finance team.\n\n**Risks and assumptions**\nAssumes invoices follow standard European layouts. Handwritten or multi-page consolidated\ninvoices are excluded from v1.',
                project_type=ProjectType.INTERNAL_TOOL,
            ),
        ],
    ),
    (
        OutputFormat.NARRATIVE,
        DetailLevel.MEDIUM,
        [
            ReferenceProject(
                name='Example 1 — Community Marketplace Web App',
                scope_summary='A neighbourhood marketplace where residents list second-hand items, message sellers, and\narrange pickup. Scope covers user profiles, listing CRUD with photo uploads, in-app\nmessaging, and email notifications. Mobile-responsive web only; no native apps in v1.',
                body='**Effort and cost**\nDiscovery and UX design consume the first two weeks, focusing on trust signals (verified\nprofiles, report listing) and a frictionless posting flow. Backend work centres on\nPostgreSQL data modelling, image storage on S3, and a WebSocket messaging layer; this is\nthe largest cost driver at roughly 90 hours. The responsive frontend adds another 70\nhours across listing browse, detail, chat, and profile screens. Testing and a soft launch\nwith one pilot neighbourhood account for the remaining 30 hours. Total effort is about 210\nhours, approximately 13,000 EUR at standard developer rates.\n\n**Team and timeline**\nA full-stack lead and a part-time designer pair for ten weeks. The designer fronts loads\nin weeks 1–3; the developer carries implementation through week 9 with QA and bug fixing\nin week 10.\n\n**Risks and assumptions**\nModeration tooling is manual in v1 (admin ban only). Payment processing is explicitly out\nof scope. Assumes fewer than 5,000 active listings at launch.',
                project_type=ProjectType.WEB_SAAS,
            ),
            ReferenceProject(
                name='Example 2 — Hospital Shift Swap Board',
                scope_summary="An internal web application for nurses to post shift swaps, request coverage, and receive\nmanager approval before schedules sync back to the hospital's existing Kronos export format.",
                body='**Effort and cost**\nWorkflow mapping with nursing managers is essential and takes about 24 hours upfront to\navoid building the wrong approval chain. Core implementation splits between a rules engine\nfor eligibility (skill mix, max consecutive hours) at 48 hours and the swap board UI with\nnotification emails at 40 hours. Kronos CSV import/export is a fixed-format integration\nestimated at 20 hours. End-to-end testing with two wards adds 28 hours. Combined total is\nroughly 160 hours, about 10,000 EUR.\n\n**Team and timeline**\nOne senior full-stack developer plus a part-time UX designer over eight weeks. Manager\nsign-off gates sit at the end of weeks 2, 6, and 8.\n\n**Risks and assumptions**\nAssumes Kronos export schema is stable. Real-time sync is not required; nightly batch is\nacceptable. Union rule changes mid-project would trigger change control.',
                project_type=ProjectType.INTERNAL_TOOL,
            ),
        ],
    ),
    (
        OutputFormat.NARRATIVE,
        DetailLevel.DETAILED,
        [
            ReferenceProject(
                name='Example 1 — Insurance Claims Triage Platform',
                scope_summary="A web platform for first-line claims adjusters to intake motor insurance claims, attach\nevidence photos, run automated fraud signals, and route cases to specialist teams. Integrates\nwith the insurer's legacy policy API (read-only) and document archive. Must support 200\nconcurrent adjusters and retain audit logs for seven years.",
                body='**Effort and cost**\nThe programme opens with three weeks of discovery: adjuster shadowing, fraud-rule workshops,\nand a non-functional requirements pass covering peak-load assumptions and retention policy.\nDesign spans adjuster inbox, claim detail with timeline, and supervisor dashboards—about 60\nhours of UX and UI work at designer rates.\n\nBackend development dominates the budget. Policy lookup caching, claim state machine with\neight statuses, evidence upload to WORM storage, and a rules service evaluating ten fraud\nheuristics together account for roughly 180 hours. The automated signals re-use an existing\nscoring library but need wrapping, batch replay for backtesting, and threshold tuning with\nthe fraud team. Frontend delivery covers responsive adjuster workflows, bulk actions, and\naccessibility (WCAG 2.1 AA) across 14 screens—about 120 hours.\n\nIntegration testing against the legacy policy API sandbox, performance testing at 200\nvirtual users, and security review remediation add 80 hours. Deployment uses blue-green\nreleases with runbooks and adjuster training sessions. Total effort lands near 480 hours,\napproximately 29,500 EUR blended across development and design.\n\n**Team and timeline**\nA backend lead, one full-stack developer, one frontend developer, a part-time designer, and\na QA engineer in the final four weeks. Calendar duration is 18 weeks including two weeks of\nparallel UAT with a 30-adjuster pilot group.\n\n**Risks and assumptions**\nAssumes legacy policy API documentation is accurate; prior projects showed 15% field mismatch\nrisk. Fraud model thresholds are client-owned—engineering delivers plumbing only. Photo EXIF\ntampering detection is out of scope for v1. Contingency of two weeks is recommended if\narchive integration requires custom CMIS adapters.',
                project_type=ProjectType.WEB_SAAS,
            ),
            ReferenceProject(
                name='Example 2 — University Research Grant Management System',
                scope_summary='A SaaS module for university research offices to publish grant calls, collect applicant\nsubmissions with budget breakdowns, run committee review scoring, and export award letters.\nSupports multi-faculty tenancy, SSO via institutional SAML, and PDF generation for legal\nreview. English and Spanish UI required.',
                body='**Effort and cost**\nDiscovery includes compliance workshops (GDPR, public procurement thresholds) and committee\nworkflow mapping across three faculties—approximately 40 hours. Bilingual UX design and a\ncomponent library for forms-heavy screens consume 56 designer hours.\n\nThe submission portal with dynamic budget templates, file uploads up to 50 MB, and\nvalidation rules is the largest single workstream at 100 developer hours. Review committee\nscoring (blinded rounds, conflict-of-interest declarations, aggregate ranking) adds 80 hours.\nSAML SSO integration with test IdP environments is 32 hours. PDF award letter generation with\nmerge fields and digital-signature placeholders is 40 hours. Reporting for research office\nleadership (funnel metrics, award rate by faculty) is 36 hours.\n\nAutomated test coverage for scoring edge cases, accessibility audit remediation, and\nload testing for deadline-day traffic spikes (3× normal) account for 72 hours. Documentation,\nadmin training webinars, and staged faculty rollout add 40 hours. Total effort is about 496\nhours, roughly 30,500 EUR.\n\n**Team and timeline**\nOne technical lead, two full-stack developers, one designer, and a QA engineer from week 10.\nDelivery spans 20 weeks with faculty pilots in weeks 16–18 and general availability in week 20.\n\n**Risks and assumptions**\nAssumes SAML metadata is provided by week 4; late IdP changes have caused two-week slips on\nsimilar projects. Committee scoring rules are frozen after discovery—mid-project rule changes\nare change-order scope. Spanish translations are client-reviewed; engineering supplies i18n\nframework only. Peak submission traffic may require read-replica provisioning not included\nin base estimate.',
                project_type=ProjectType.INTERNAL_TOOL,
            ),
        ],
    ),
]
