# Web Dashboard, Agents, and startup-warning guide

This template contains two different dashboard concepts:

- **Railway admin dashboard:** the page served by this repository on `PORT`. It
  configures one Hermes home and manages one `hermes gateway` child process.
- **Upstream Hermes Web Dashboard:** a separate Hermes CLI application. The
  **available** badge on the Status page means only that the installed CLI
  recognizes `hermes dashboard`; it does not mean that application is running,
  exposed, or managed by this template.

## Can I enable the upstream dashboard or Agents here?

There is currently no toggle that safely enables either feature in this admin
page. The container starts `/app/start.sh`, which runs only the template admin
server; the admin server then starts `hermes gateway`. It does not start or
proxy `hermes dashboard`.

**Short answer:** to create Agents today, use an upstream Hermes deployment and
version that explicitly supports Agent management. For an existing production
deployment of this template, the safe first step is a separate **staging**
Railway service with a separate volume. This does not mean that every Agent
needs its own service, and it does not mean that you should run a second gateway
against the same Telegram or Slack tokens. The upstream dashboard/control plane
should own all of its Agents and route them through the topology it documents.

The separate service is an isolation boundary for evaluating the upstream
feature, not necessarily the final production architecture. After the candidate
version, storage migration, authentication, channel routing, and rollback have
been verified, you can choose either to migrate away from this template's
single-agent control plane or to keep the upstream deployment separate. This
template cannot currently be used as the Agent-creation UI in either topology.

Before attempting a separate upstream deployment, inspect the interface in the
exact image being used:

```bash
hermes version
hermes dashboard --help
hermes gateway --help
```

Follow the upstream Web Dashboard documentation linked by the Status card for
that exact version. For the initial Railway test, give the staging service its
own public port, authentication, and volume. Do not mount the live production
volume into both services unless upstream explicitly documents concurrent
access as safe. Do not replace this service's start command with `hermes
dashboard`: doing so removes the template admin server, its health endpoint,
and its gateway process management. Do not expose an unauthenticated dashboard
to the public internet.

The image is pinned to `v2026.7.7.2`. The template has not verified a stable,
self-hosted Agent-management API or CLI contract for that pin. Consequently,
Agents cannot currently be created, edited, listed, or routed from this admin
page. Do not create a second gateway per Agent or copy the global `.env`,
`config.yaml`, or `SOUL.md`; those approaches can duplicate channel consumers
or overwrite global state. Qualify a newer exact tag in staging, back up the
volume, and verify its documented Agent migration and routing behavior before
changing the production pin.

## Interpreting the reported warnings

### Telegram fallback discovery and connection attempts

The DNS-over-HTTPS fallback-discovery line and an early `attempt 1/8` line are
connection-progress warnings, not evidence of a configuration failure by
themselves. If Telegram subsequently connects and messages work, no action is
needed. If all attempts fail, verify outbound HTTPS/DNS access and the bot token,
then inspect the final connection error rather than the first retry line.

### Slack Group DMs and channel discovery

The two Slack warnings identify missing Slack app permissions. Update the app
configuration to include:

- Bot scopes: `groups:read`, `mpim:history`, and `mpim:read`.
- Event subscription: `message.mpim`.

Then **reinstall the Slack app to the workspace** so the installed token receives
the new grants, and update the deployed bot token if Slack issues a replacement.
The existing `groups:history` grant does not satisfy `groups:read`. Regenerating
the app manifest with `hermes slack` is the preferred alternative when an
interactive Hermes environment is available. If Group DMs are not needed, the
`mpim` warning only describes that unavailable channel type; `groups:read` is
still needed for the channel-directory lookup shown in the log.

### Tool requirement checks returning `False`

These lines are capability filtering. Hermes checks every optional tool before
an agent turn and omits tools whose prerequisites or current mode are absent.
They do not mean the gateway crashed.

- Browser/CDP, browser-vision, dialog, and computer-use warnings mean this
  deployment does not currently provide the required browser runtime/session
  and credentials.
- Read/close-terminal warnings mean there is no compatible managed terminal
  session for those tools.
- Kanban warnings mean the current run is not in the required Kanban or Kanban
  orchestrator mode.

Ignore these warnings when those capabilities are not required. If they are
required, configure the corresponding integration in **Setup → Tools**, confirm
the upstream runtime prerequisites for the pinned version, save, and restart
the gateway. Adding an API key alone may not provide a local browser executable,
CDP session, terminal session, or the required orchestration mode.

## Recommended order of operations

1. Fix and reinstall the Slack app scopes/events.
2. Confirm Telegram eventually connects; investigate only if retries exhaust or
   messaging fails.
3. Treat optional-tool checks as informational unless a required tool is absent
   from an actual agent turn.
4. Keep using this template's admin dashboard for the current single-agent
   gateway.
5. Test upstream Dashboard/Agents in an isolated staging service and volume
   before considering a pinned-version upgrade or production exposure.
