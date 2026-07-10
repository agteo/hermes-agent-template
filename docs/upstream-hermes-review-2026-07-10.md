# Upstream Hermes Agent Review — 2026-07-10

This review updates the May 29 upstream scan for the Railway template. The template previously tracked `v2026.5.29`; upstream has since published stable release tags through `v2026.7.7.2` / Hermes Agent v0.18.2.

## Sources reviewed

- Upstream releases: <https://github.com/NousResearch/hermes-agent/releases>
- Hermes Agent v0.16.0: <https://github.com/NousResearch/hermes-agent/releases/tag/v2026.6.5>
- Hermes Agent v0.17.0: <https://github.com/NousResearch/hermes-agent/releases/tag/v2026.6.19>
- Hermes Agent v0.18.0: <https://github.com/NousResearch/hermes-agent/releases/tag/v2026.7.1>
- Hermes Agent v0.18.1: <https://github.com/NousResearch/hermes-agent/releases/tag/v2026.7.7>
- Hermes Agent v0.18.2: <https://github.com/NousResearch/hermes-agent/releases/tag/v2026.7.7.2>

## Executive recommendation

Move the default build pin from `v2026.5.29` to `v2026.7.7.2` and then selectively adopt upstream admin/operations features rather than duplicating the entire upstream dashboard. The latest patch specifically fixes tagged-release Docker builds for WhatsApp by switching the Baileys dependency to the published `7.0.0-rc13`, while v0.18.1 rolled up substantial gateway, dashboard, MCP, provider, and stability fixes since v0.18.0.

The biggest template opportunity is to become a clean hosted control plane around upstream Hermes instead of carrying parallel behavior. Upstream now has a much more capable browser admin surface, gateway lifecycle semantics, profile builder, Skills Hub, backup import/export, credential management, and diagnostics. We should integrate or expose those primitives where they help Railway users and avoid reimplementing desktop-only functionality.

## Recent upstream changes worth considering

### 1. P0 — Upgrade the default stable release pin

**Why it matters:** The template still builds from `v2026.5.29`, but upstream now marks `v2026.7.7.2` as latest. The new tag includes the v0.18.1 stability rollup plus a Docker-build reliability patch for the WhatsApp bridge dependency.

**Template action:** Update `Dockerfile` and README defaults to `v2026.7.7.2`, keep `--build-arg HERMES_REF=<tag-or-sha>`, and verify a clean image build before promoting the template.

### 2. P0 — Adopt upstream gateway lifecycle/drain signals

**Why it matters:** v0.18.0 added scale-to-zero idle detection, dormant-quiesce, external drain coordination, persisted in-flight transcripts on restart/shutdown drain timeout, busy/idle readouts for lifecycle actions, and self-healing for gateways stranded in draining/degraded states.

**Template action:** Extend `/api/status` to surface upstream busy/idle/draining/degraded state before enabling dashboard restart/stop actions. Prefer upstream safe-shutdown/drain semantics over raw subprocess termination when stable CLI/API entry points are available.

### 3. P1 — Reconcile with upstream web dashboard capabilities

**Why it matters:** Since v0.16.0, upstream's web dashboard evolved into a full admin panel with channels, MCP catalog, credentials, memory, gateway controls, hooks, system settings, and debug share. v0.17.0 added a full profile builder and Skills Hub rework. v0.18.0 added portal SSO auto-redirect, custom `.env` keys, backup import/create/download, cron execution fields, and event-loop-safe PTY handling.

**Template action:** Decide whether the Railway UI should proxy/link to upstream dashboard routes or remain a simplified setup wizard. If it remains simplified, add explicit affordances for advanced upstream dashboard tasks instead of duplicating them piecemeal.

### 4. P1 — Add profile and Skills Hub visibility

**Why it matters:** Upstream now supports browser-based profile creation/selection, MCP server attachment, connected skills hubs, featured skills, previews, and security scanning. This reduces the need for users to edit `config.yaml` or pre-bake skills in this template.

**Template action:** Add read-only profile/skills summaries to the admin status page, plus launch instructions for upstream profile builder and Skills Hub. Defer skill installation UI until we can call upstream commands safely and capture failures.

### 5. P1 — Preserve hosted-template security around new auth/admin features

**Why it matters:** Upstream added remote desktop-to-gateway auth, OAuth/username-password remote gateway sign-in, self-hosted OIDC client-secret support, and interactive auth setup for non-loopback binds. These are useful, but Railway deployments already expose a Basic Auth wrapper and API-server key controls.

**Template action:** Document which auth layer protects which surface. Avoid binding upstream admin/API surfaces publicly without explicit credentials, CORS controls, and a generated secret.

### 6. P2 — Expose backup and diagnostics support

**Why it matters:** Upstream dashboard now supports backup import/create/download, and debug/log tooling includes broader support bundles. This is valuable for persistent Railway volumes and production support.

**Template action:** Add a backup/diagnostics section that either calls upstream `hermes` commands or links to upstream dashboard features. Redact `.env`, API keys, bearer tokens, and pairing data before surfacing downloads in the Railway admin UI.

### 7. P2 — Add new provider/model metadata only where hosted setup is practical

**Why it matters:** v0.18.0 adds Google Vertex AI as a first-class Gemini provider with service-account/ADC token refresh, Krea through the managed Nous Subscription gateway, Z.AI endpoint picker variants, Ollama-cloud reasoning-effort wiring, and Nous OAuth base URL override handling.

**Template action:** Add Vertex AI service-account configuration and the Z.AI endpoint picker to provider metadata. Treat Krea/Nous subscription and OAuth-only flows as assisted/manual setup unless upstream exposes non-interactive hosted-friendly commands.

### 8. P2 — Channel expansion: iMessage/Photon and Raft are interesting but not first

**Why it matters:** v0.17.0 introduced iMessage via Photon device-code login and a Raft gateway channel. These broaden Hermes' reach, but both need extra external service setup beyond a simple Railway form.

**Template action:** Add documentation cards for Photon and Raft after the gateway status work lands. Do not prioritize credential forms until the exact non-interactive setup and runtime requirements are verified.

### 9. P3 — Tool improvements relevant to this template

**Why it matters:** v0.17.0 added image-to-image editing through `image_generate`; v0.18.0 improved `web_extract` behavior and tool-result rendering performance. These overlap with this template's local `tool_routing.py` artifact-detection feature.

**Template action:** Revisit the local tool-routing label. If upstream image editing and web extraction cover the intended behavior, rename local logic as log/artifact detection or remove it from the primary feature list.

### 10. P3 — Desktop features are mostly out of scope, but remote gateway docs are useful

**Why it matters:** v0.16.0 introduced the Electron desktop app and remote gateway connection flow. Railway users may want the desktop app as a client for their hosted Hermes instance.

**Template action:** Add a short README section explaining how to connect the Hermes Desktop app to a Railway-hosted gateway once auth, host, and CORS settings are configured. Do not attempt to package or run the desktop app inside this image.

## Implementation order for this template

1. **Release hygiene:** Pin `HERMES_REF` to `v2026.7.7.2`; verify image build; document rollback via build arg.
2. **Lifecycle status:** Surface upstream gateway busy/idle/draining/degraded state and use safe shutdown paths where available.
3. **Dashboard integration decision:** Choose proxy/link vs simplified wrapper for upstream browser admin; document overlap clearly.
4. **Backup/diagnostics:** Add read-only debug/log/backup actions with secret redaction.
5. **Provider metadata refresh:** Add Vertex AI, Z.AI endpoint variants, and clearer Nous/Krea assisted setup notes.
6. **Profiles/Skills visibility:** Surface active profile and installed/available skill summaries.
7. **Channel docs:** Add Photon iMessage and Raft guidance after runtime requirements are verified.

## Implemented in this pass

- Updated the template's default Hermes build ref to `v2026.7.7.2`.
- Updated README examples and version-strategy text to match the new default.
- Added this July 10 upstream review as the next implementation backlog.
