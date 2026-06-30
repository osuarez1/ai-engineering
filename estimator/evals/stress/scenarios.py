"""Multi-turn stress profiles for CAG memory and cost evaluation.

Each scenario defines 20 turns with transcripts aligned to session heuristics
(anchors, metadata, summary) so MemoryDrift metrics can check recall of prior facts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TurnSpec:
    turn_index: int
    transcript: str
    fact_to_remember: str


@dataclass(frozen=True)
class Scenario:
    name: str
    turns: list[TurnSpec]


def _growing_turns() -> list[TurnSpec]:
    return [
        TurnSpec(
            1,
            "The project is called Nimbus. We need a cloud SaaS for operations teams.",
            "project is called Nimbus",
        ),
        TurnSpec(
            2,
            "Users must sign in with email and password. Auth is required from day one.",
            "auth",
        ),
        TurnSpec(
            3,
            "Each customer organization gets its own isolated tenant. Multi-tenant is mandatory.",
            "multi-tenant",
        ),
        TurnSpec(
            4,
            "Every admin action must write to an audit log with user id and timestamp.",
            "audit log",
        ),
        TurnSpec(
            5,
            "Locked decision: ship MVP with CSV export only for reporting downloads.",
            "CSV export",
        ),
        TurnSpec(
            6,
            "Locked decision: use PostgreSQL for all persistence layers in Nimbus.",
            "PostgreSQL",
        ),
        TurnSpec(
            7,
            "We have 4 full-time engineers available for the initial six-month build.",
            "4",
        ),
        TurnSpec(
            8,
            "The approved budget 45000 EUR covers MVP delivery through the third quarter.",
            "budget 45000 EUR",
        ),
        TurnSpec(
            9,
            "We will add Redis for session caching and rate-limit counters in production.",
            "Redis",
        ),
        TurnSpec(
            10,
            "Agreed scope: MVP with auth, multi-tenant isolation, audit log, and CSV export.",
            "MVP with auth",
        ),
        TurnSpec(
            11,
            "Role-based access control is needed for admin versus member users in Nimbus.",
            "Role-based",
        ),
        TurnSpec(
            12,
            "Email notifications for password resets and weekly usage digests per tenant.",
            "Email",
        ),
        TurnSpec(
            13,
            "Dashboard analytics showing active tenants and usage metrics for admins.",
            "Dashboard",
        ),
        TurnSpec(
            14,
            "Mobile responsive UI for tablet approval workflows used by field teams.",
            "responsive",
        ),
        TurnSpec(
            15,
            "GDPR compliance requires data export and deletion per tenant on request.",
            "GDPR",
        ),
        TurnSpec(
            16,
            "Staging environment must mirror production schema before each release cut.",
            "Staging",
        ),
        TurnSpec(
            17,
            "CI/CD pipeline runs automated tests and deploys to staging on every merge.",
            "CI/CD",
        ),
        TurnSpec(
            18,
            "Documentation portal for customer admins and internal support staff onboarding.",
            "Documentation",
        ),
        TurnSpec(
            19,
            "Admin impersonation for support tickets with full audit trail logging enabled.",
            "impersonation",
        ),
        TurnSpec(
            20,
            "Confirm Nimbus MVP scope is locked: auth, tenants, audit log, and CSV export.",
            "Nimbus",
        ),
    ]


def _pivot_turns() -> list[TurnSpec]:
    return [
        TurnSpec(
            1,
            "The project is called Helix. Frontend will use React with TypeScript initially.",
            "React",
        ),
        TurnSpec(
            2,
            "React component library with shared design tokens across all admin pages.",
            "React",
        ),
        TurnSpec(
            3,
            "React state management via Redux for complex dashboard filter interactions.",
            "React",
        ),
        TurnSpec(
            4,
            "React testing with Jest and integration tests for critical checkout flows.",
            "React",
        ),
        TurnSpec(
            5,
            "We are switching to Flutter for the mobile client. Stack includes Flutter going forward.",
            "stack includes Flutter",
        ),
        TurnSpec(
            6,
            "Flutter widgets will replace the React admin screens on mobile web browsers.",
            "Flutter",
        ),
        TurnSpec(
            7,
            "Flutter uses Riverpod for state and talks to the existing GraphQL API layer.",
            "Flutter",
        ),
        TurnSpec(
            8,
            "Locked decision: Flutter is the sole client stack after the architecture pivot.",
            "Flutter",
        ),
        TurnSpec(
            9,
            "The approved budget 55000 EUR covers the Flutter rewrite in phase two delivery.",
            "budget 55000 EUR",
        ),
        TurnSpec(
            10,
            "PostgreSQL backend unchanged; only the client stack pivoted to Flutter for Helix.",
            "PostgreSQL",
        ),
        TurnSpec(
            11,
            "Agreed scope: Flutter mobile app with auth, offline cache, and push alerts.",
            "Flutter mobile app",
        ),
        TurnSpec(
            12,
            "Four full-time engineers focused on Flutter delivery for the next six months.",
            "4",
        ),
        TurnSpec(
            13,
            "Node.js API layer remains; legacy React code enters maintenance mode only.",
            "Node.js",
        ),
        TurnSpec(
            14,
            "Flutter builds target iOS and Android from a single shared codebase repository.",
            "iOS",
        ),
        TurnSpec(
            15,
            "Design system tokens ported from React to Flutter theme constants this sprint.",
            "Design system",
        ),
        TurnSpec(
            16,
            "Flutter integration tests cover login, checkout, and tenant switching flows.",
            "integration tests",
        ),
        TurnSpec(
            17,
            "Performance budget: Flutter first frame under two seconds on mid-range devices.",
            "Performance",
        ),
        TurnSpec(
            18,
            "Staging Flutter builds deploy via CI for QA sign-off at the end of each sprint.",
            "Staging",
        ),
        TurnSpec(
            19,
            "Documentation updated to describe Flutter architecture and local build steps.",
            "Documentation",
        ),
        TurnSpec(
            20,
            "Confirm Helix stack includes Flutter as the primary client going forward.",
            "stack includes Flutter",
        ),
    ]


def _contradiction_turns() -> list[TurnSpec]:
    return [
        TurnSpec(
            1,
            "The project is called Apex Billing for mid-market finance teams in Europe.",
            "project is called Apex",
        ),
        TurnSpec(
            2,
            "Initial scope covers invoicing, payment reminders, and a customer self-service portal.",
            "invoicing",
        ),
        TurnSpec(
            3,
            "The approved budget 30000 EUR covers phase one MVP delivery only through June.",
            "budget 30000 EUR",
        ),
        TurnSpec(
            4,
            "We will use React for the customer portal and Rails for the billing API backend.",
            "React",
        ),
        TurnSpec(
            5,
            "PostgreSQL for ledger data with strict audit requirements on every state change.",
            "PostgreSQL",
        ),
        TurnSpec(
            6,
            "Three full-time engineers dedicated to the first release cycle for Apex Billing.",
            "3",
        ),
        TurnSpec(
            7,
            "Agreed scope: MVP with invoicing, reminders, portal auth, and basic reporting.",
            "MVP with invoicing",
        ),
        TurnSpec(
            8,
            "Leadership increased the budget 80000 EUR after scope expansion to enterprise tier.",
            "budget 80000 EUR",
        ),
        TurnSpec(
            9,
            "Locked decision: retain both budget figures in planning until finance reconciles.",
            "budget",
        ),
        TurnSpec(
            10,
            "Steering deck lists budget 30000 EUR and budget 80000 EUR for stakeholder review.",
            "budget 30000 EUR",
        ),
        TurnSpec(
            11,
            "Enterprise multi-tenant isolation added to the expanded Apex Billing scope.",
            "multi-tenant",
        ),
        TurnSpec(
            12,
            "SSO via SAML required for enterprise tier customers in the phase two rollout.",
            "SAML",
        ),
        TurnSpec(
            13,
            "Audit log for every invoice state change and payment capture event in the system.",
            "audit log",
        ),
        TurnSpec(
            14,
            "Redis for job queues processing payment webhooks asynchronously under load.",
            "Redis",
        ),
        TurnSpec(
            15,
            "GraphQL API for partner integrations alongside existing REST billing endpoints.",
            "GraphQL",
        ),
        TurnSpec(
            16,
            "Docker containers for all services with Kubernetes planned for production later.",
            "Docker",
        ),
        TurnSpec(
            17,
            "CI/CD with automated regression suite before each staging deploy for Apex Billing.",
            "CI/CD",
        ),
        TurnSpec(
            18,
            "Finance wants confirmation that budget 30000 EUR and budget 80000 EUR are documented.",
            "budget 80000 EUR",
        ),
        TurnSpec(
            19,
            "Staging environment must load synthetic tenant data for enterprise demo accounts.",
            "Staging",
        ),
        TurnSpec(
            20,
            "Final estimate for Apex Billing: track scope growth and both approved budget figures.",
            "Apex",
        ),
    ]


GROWING = Scenario(name="growing", turns=_growing_turns())
PIVOT = Scenario(name="pivot", turns=_pivot_turns())
CONTRADICTION = Scenario(name="contradiction", turns=_contradiction_turns())

SCENARIOS: dict[str, Scenario] = {
    "growing": GROWING,
    "pivot": PIVOT,
    "contradiction": CONTRADICTION,
}

SCENARIO_NAMES: tuple[str, ...] = tuple(SCENARIOS.keys())


def get_scenario(name: str, max_turns: int = 20) -> Scenario:
    """Return a scenario by name, optionally truncated to the first ``max_turns`` turns."""
    try:
        scenario = SCENARIOS[name]
    except KeyError as exc:
        available = ", ".join(SCENARIO_NAMES)
        raise KeyError(f"Unknown scenario {name!r}; choose from: {available}") from exc

    if max_turns < 1:
        raise ValueError("max_turns must be at least 1")

    return Scenario(name=scenario.name, turns=scenario.turns[:max_turns])
