# Upstream Hermes Agents Compatibility Review — 2026-08-18

## Executive recommendation

Do **not** reproduce the new Hermes dashboard's Agent-creation workflow in this
Railway admin UI yet. The feature is useful, but this template currently manages
one global Hermes home, one `.env`, one `config.yaml`, one `SOUL.md`, and one
`hermes gateway` process. Treating a dashboard-created Agent as one of those
files would collapse agent-scoped identity, credentials, tools, and routing into
the global deployment and could silently change the behavior of existing users.

The safe adoption path is additive:

1. Keep the default image pinned to the last build-verified Hermes tag,
   `v2026.7.7.2`.
2. Let the upstream Hermes dashboard/control plane remain the owner of Agent
   creation, identifiers, schema migrations, and deletion.
3. Add a read-only Agent inventory here only after upstream publishes a stable,
   non-interactive CLI or authenticated API for listing Agents.
4. Add Agent selection/routing only after a staging migration proves that an
   existing single-agent installation maps to an explicit default Agent without
   changing its model, personality, memory, channel pairing, or working
   directory.

This gives users access to upstream Agents without making the template an
independent, incompatible control plane.

## Review basis and confidence

The review uses the template's current implementation and the following
upstream sources as the compatibility contract to verify during staging:

- [Hermes Agent releases](https://github.com/NousResearch/hermes-agent/releases)
- [Hermes Agent repository](https://github.com/NousResearch/hermes-agent)
- [Hermes documentation](https://hermes-agent.nousresearch.com/docs/)
- [CLI command reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands/)
- [Messaging gateway guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)

The reported dashboard Agent-creation capability is newer than the upstream
material previously reviewed in this repository. Its wire format, persistence
layout, authentication model, and self-hosted availability must therefore be
considered **unverified** until checked against a tagged release. In particular,
a feature present in a hosted dashboard is not evidence that the pinned
open-source gateway exposes a compatible management API.

## Current template assumptions that Agents challenge

| Template assumption | Current behavior | Multi-Agent risk |
| --- | --- | --- |
| One Hermes home | `HERMES_HOME` points at `/data/.hermes` | Agent records may live in a new database or per-Agent directories; guessing the layout risks corruption. |
| One provider/model | The admin server writes one global `.env` and a minimal `config.yaml` | Saving the existing form could overwrite the active Agent's model or flatten Agent-specific credentials. |
| One personality | The Personality page reads and writes one global `SOUL.md` | Editing it could affect only the legacy/default Agent, or the wrong Agent, while the UI implies otherwise. |
| One gateway process | The server launches `hermes gateway` without an Agent identifier | A newer gateway may perform routing internally; launching a process per Agent could duplicate channel consumers and deliveries. |
| Global pairing | Pairing files are read directly under `HERMES_HOME/pairing` | Agent-scoped authorization cannot safely be inferred from the legacy directory. |
| Global working directory | `MESSAGING_CWD` is a single environment value | Per-Agent workspaces need path validation, isolation, and explicit routing. |
| Basic Auth control plane | This UI has one administrator credential | Upstream dashboard users, organizations, roles, and Agent ownership may not map to this security model. |

## Compatibility assessment

### Safe now (non-breaking)

- **Document upstream Agents and link to the upstream dashboard/docs.** This
  changes no runtime state.
- **Retain `HERMES_REF` as the upgrade and rollback boundary.** A tag or commit
  can be staged without silently moving production to upstream `main`.
- **Expose capability detection later.** A status response such as
  `agents: {supported, source, count}` is additive if absence/unsupported is a
  normal state and no secrets or Agent configuration are returned.
- **Preserve unknown configuration.** Any future writer must patch only fields
  owned by this template rather than regenerating upstream Agent documents.

### Safe only after upstream contract verification

- A read-only Agent list containing stable ID, display name, health, and routed
  channel count.
- Selecting an Agent as context for logs/status, provided the identifier is
  passed through an upstream-supported command or API and never interpolated
  into a shell command or filesystem path.
- Creating an Agent by calling an authenticated upstream API, provided the API
  is documented for the pinned self-hosted release, supports idempotency, and
  returns structured validation errors.
- Agent-specific personality/model controls, but only with optimistic
  concurrency (revision/ETag) so this UI cannot overwrite edits made in the
  upstream dashboard.

### Breaking or unsafe; do not apply

- Creating directories or editing an assumed Agent registry/database directly.
- Modeling an Agent as a second gateway subprocess.
- Copying the global `.env`, `config.yaml`, or `SOUL.md` for every Agent.
- Reusing channel tokens across Agents without upstream routing guarantees;
  this can create duplicate consumers or responses.
- Mapping Agent deletion to recursive filesystem deletion.
- Automatically migrating the existing global personality, memory, pairing, or
  workspace on first boot.
- Advancing the production pin merely because the hosted dashboard has the
  feature.

## Proposed implementation phases

### Phase 0 — release qualification (required before changing the pin)

Build the exact candidate tag and capture:

```bash
hermes version
hermes --help
hermes gateway --help
hermes doctor
```

Confirm whether Agent management exists in the self-hosted artifact and record
the authoritative command/API, schema version, auth requirements, and data
location. Diff a copy of `/data/.hermes` before and after creating an Agent via
the upstream dashboard; use the diff only to understand migration impact, not
as an unofficial integration API.

### Phase 1 — additive observability

Implement a small adapter around the documented structured interface. If the
candidate release does not support Agents, times out, or returns an unknown
schema, report `supported: false`/`unavailable` and leave all existing status,
configuration, personality, gateway, and pairing behavior intact. Do not make
gateway startup depend on Agent discovery.

### Phase 2 — explicit opt-in management

Only after Phase 1 has run in staging, add creation behind a separate feature
flag that defaults off. Require a stable Agent ID, idempotency key, explicit
profile/workspace choice, and upstream validation. Never send provider secrets
back to the browser. Keep the upstream dashboard as the recovery path.

### Phase 3 — scoped editing and routing

Add model, personality, tools, secrets, and channel routing one scope at a time.
Each control must state whether it is global, deployment-scoped, or
Agent-scoped. Do not reuse today's global save endpoint for an Agent-scoped
form.

## No-break staging gate

The candidate release is promotable only if all of the following pass:

1. Start with a copy of a production-like `v2026.7.7.2` volume and verify the
   candidate's migration is one-way only after a rollback copy has been made.
2. The legacy/default Agent retains the same model, `SOUL.md`, memory, skills,
   working directory, approved users, and channel routes.
3. Telegram, Discord, and Slack (when configured) each produce exactly one
   response before and after an Agent is created.
4. Gateway stop, graceful restart, crash recovery, and completed-message
   redelivery do not duplicate or lose responses.
5. Editing an Agent in the upstream dashboard does not cause this template's
   ordinary config save to overwrite that Agent.
6. Agent names and IDs containing spaces, Unicode, path separators, and shell
   metacharacters cannot escape validation or select filesystem paths.
7. Deleting a test Agent cannot delete shared memory, secrets, channels, or the
   legacy/default Agent.
8. Downgrade behavior is documented. If the migrated volume cannot be read by
   `v2026.7.7.2`, rollback must restore a pre-migration volume snapshot rather
   than only changing `HERMES_REF`.

## Decision

**Can we apply the latest Hermes Agents capability without breaking existing
deployments?** Yes, initially as documentation and later as read-only capability
detection. Full creation and editing are **not yet safe to implement in this
template** without the tagged self-hosted API/CLI contract and migration tests
above. The most important design choice is to integrate with upstream Agent
management rather than infer or duplicate its storage model.

## First implementation step

Phase 1 has started with a non-mutating capability probe. The admin server runs
`hermes dashboard --help`, caches the result for five minutes, and reports only
availability, probe state, management state, and the upstream documentation URL
under `/api/status`. The Status page renders that result and deliberately does
not start, proxy, configure, or write data for the upstream dashboard. Older
Hermes builds degrade to an unavailable state without affecting gateway startup
or the existing configuration UI.
