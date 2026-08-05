# Upstream Hermes Non-Voice Adoption Review — 2026-08-05

This review looks beyond Herald voice features and identifies upstream Hermes changes from the last several monthly releases that are relevant to this hosted template. It is based on the upstream release feed checked on 2026-08-05.

## Sources reviewed

- Hermes Agent v0.20.0 / Herald, released 2026-08-03: https://github.com/NousResearch/hermes-agent/releases
- Hermes Agent v0.19.1, released 2026-07-30: https://github.com/NousResearch/hermes-agent/releases
- Hermes Agent v0.19.0 / Quicksilver, released 2026-07-20: https://github.com/NousResearch/hermes-agent/releases
- Hermes Agent v0.18.0 / Judgment, released 2026-07-01: https://github.com/NousResearch/hermes-agent/releases
- Hermes Agent v0.17.0 / Reach, released 2026-06-19: https://github.com/NousResearch/hermes-agent/releases
- Hermes Agent v0.16.0 / Surface, released 2026-06-05: https://github.com/NousResearch/hermes-agent/releases

## Recommended adoption order

### 1. Promote gateway lifecycle and delivery reliability first

Adopt upstream gateway lifecycle primitives before convenience UI. v0.18.0 calls out scale-to-zero and drain coordination as part of making the gateway deployable at scale, and v0.19.0 adds a durable delivery-obligation ledger so completed responses are redelivered after gateway crashes instead of silently disappearing on Telegram, Discord, Slack, and other channels.

Template adoption:

- Add a dashboard-visible drain/busy state once upstream exposes a stable command or status endpoint.
- Prefer graceful drain/restart over direct subprocess kills.
- Add smoke tests for “turn completed but platform send interrupted” before promoting a newer `HERMES_REF`.

Priority: **highest**, because it directly protects hosted messaging reliability.

### 2. Add outbound webhook configuration, but keep verification server-side

Herald adds signed outbound webhooks for session activity, turn completions, and tool events. This is a strong hosted-template fit because it lets users connect Hermes to automation systems without polling.

Template adoption:

- Add dashboard fields for webhook URL, enabled event types, and signing secret only when upstream environment names/config schema are confirmed.
- Show last-delivery status and signature-verification guidance without exposing the signing secret.
- Do not implement a parallel event bus in this template; configure and observe upstream Hermes instead.

Priority: **high**, because webhooks are useful for hosted deployments and do not require browser audio or privileged client code.

### 3. Surface profile routing and multi-profile health

Recent releases add stronger profile support: v0.17.0 introduced a full profile builder and secure login, while v0.19.0 describes one gateway routing guilds, channels, or threads to different isolated profiles.

Template adoption:

- Add read-only profile inventory once upstream exposes stable profile listing.
- Show which channel/guild/thread is routed to which profile.
- Keep secrets scoped by profile and avoid flattening all profile variables into one global `.env` if upstream now supports scoped secrets.

Priority: **high** for team or multi-channel deployments; **medium** for single-user Telegram deployments.

### 4. Adopt secret-source awareness before adding more plaintext fields

v0.19.0 introduced Bitwarden and 1Password secret sources through a pluggable `SecretSource` interface, including provenance and conflict handling. This is directly relevant to this template because the current dashboard stores many values in `.env`.

Template adoption:

- Detect and display secret references such as `op://...` as configured without trying to resolve them in the browser.
- Add status copy that distinguishes plaintext `.env` values from external secret references.
- Defer any browser-side vault integration; let upstream Hermes resolve vault secrets server-side.

Priority: **high** for security posture, especially before expanding credential UI further.

### 5. Expose grounded-citation and fact-checking skill readiness

Herald adds a grounded-citations skill for evidence-backed research and fact-checking. For a hosted agent, this is more immediately useful than desktop-only features because it can improve answers through existing messaging channels.

Template adoption:

- Add a Skills/Research readiness card only after confirming the upstream skill name and required search/browser dependencies.
- Report whether required search tools are configured, not whether citations are guaranteed correct.
- Add a short README recipe for enabling research-grade responses once verified in staging.

Priority: **medium-high** for research-heavy users.

### 6. Track provider/model catalog expansion without hardcoding every model

v0.19.0 adds Fireworks AI, DeepInfra, updated model catalogs, LM Studio JIT local loading, and finer reasoning-effort controls. The template should avoid hardcoding fast-changing model names.

Template adoption:

- Prefer upstream-discovered provider/model metadata over static dropdowns.
- Add missing provider credential variables only when they are stable upstream names.
- If reasoning-effort settings become stable config, expose them as advanced controls with provider-specific validation.

Priority: **medium**; useful, but easy to overfit to fast-moving model catalogs.

### 7. Treat desktop-only improvements as documentation, not template scope

The desktop app gained native installers, remote gateway login, artifacts, plugin SDK, quick-entry, live subagent panes, better themes, and large performance work. These are important upstream improvements, but most should not be reimplemented in this Railway template.

Template adoption:

- Document that users can connect the upstream desktop app to this hosted gateway when the pinned release supports it.
- Keep this dashboard focused on deployment config, health, logs, pairing, and safe operational controls.
- Do not clone desktop artifacts, plugin UI, multiple windows, or quick-entry in the hosted admin panel.

Priority: **low for implementation**, **medium for docs**.

### 8. Consider CLI/TUI power features only where they improve hosted operations

Herald adds CLI commands such as shell mode, `/init`, `/diff`, `/context`, `/focus`, import tooling, and mid-turn redirects. These are valuable upstream, but most are interactive-agent features rather than Railway admin features.

Template adoption:

- Document useful commands for operators who shell into the container.
- Do not expose arbitrary shell execution in the Basic Auth dashboard.
- Consider a safe read-only “context/status” panel only if upstream has a non-executing status API.

Priority: **low-medium**.

## Keep deferring

- Reimplementing upstream desktop UI features in this template.
- Running arbitrary shell commands from the admin dashboard.
- Browser-side vault authentication or direct secret retrieval.
- Hardcoded model catalog churn.
- A release-pin jump to Herald without a clean Docker build, config migration check, and Telegram/Discord/Slack channel smoke tests.

## Practical next PRs

1. Add a read-only “Upstream capabilities” status block that can display gateway drain, delivery ledger, webhook, profile routing, and secret-source support when upstream exposes stable signals.
2. Add webhook configuration fields only after confirming exact upstream variable names.
3. Add secret-reference display support so `op://` or Bitwarden references are treated as configured without exposing secret values.
4. Add a staging checklist that tests gateway restart/delivery reliability before promoting `HERMES_REF` beyond `v2026.7.7.2`.
