# Upstream Hermes Agent Review — 2026-05-29

This review compares the Railway template against the current upstream Hermes Agent direction and identifies what this agent template should implement next.

## Sources reviewed

- Upstream releases: <https://github.com/NousResearch/hermes-agent/releases>
- Hermes CLI command reference: <https://hermes-agent.nousresearch.com/docs/reference/cli-commands/>
- Messaging gateway guide: <https://hermes-agent.nousresearch.com/docs/user-guide/messaging>
- Nous Portal integration: <https://hermes-agent.nousresearch.com/docs/integrations/nous-portal>
- Nous Tool Gateway guide: <https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway>
- API server guide: <https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server/>
- Environment variables reference: <https://hermes-agent.nousresearch.com/docs/reference/environment-variables>
- Quickstart/provider matrix: <https://hermes-agent.nousresearch.com/docs/getting-started/quickstart/>

## Current template baseline

The template already provides a thin Starlette admin surface around `hermes gateway`, with configuration persisted in `/data/.hermes/.env` and `/data/.hermes/config.yaml`. It exposes admin configuration, live logs, gateway start/stop/restart, status, personality, and pairing endpoints.

Current support is intentionally key-based and dashboard-first:

- Providers: OpenRouter, DeepSeek, DashScope, GLM / Z.AI, Kimi, MiniMax, Hugging Face.
- Channels: Telegram, Discord, Slack, WhatsApp, Email, Mattermost, Matrix.
- Tools: Parallel, Firecrawl, Tavily, FAL, Browserbase, GitHub, OpenAI voice, Honcho.

## Upstream changes that matter for this template

### 1. Use the latest stable release tag by default

Upstream's latest release is `v2026.5.29` / Hermes Agent v0.15.1, a same-day patch on top of v0.15.0. The release specifically calls out fixes relevant to container/hosted deployments: dashboard reload-loop behavior, Docker `--insecure` semantics, MCP bare-command resolution in Docker, gateway probe-stepdown safety, media-delivery fixes, and `/model` picker consistency.

**Template action:** default Docker builds to `v2026.5.29`, while still allowing `--build-arg HERMES_REF=<tag-or-sha>` for controlled upgrades.

### 2. Expose provider setup that matches upstream's current provider matrix

Upstream now positions `hermes model` as the primary provider setup path and supports many providers that are absent from this dashboard, including Nous Portal, OpenAI/Codex, Anthropic, NovitaAI, GitHub Copilot, NVIDIA, xAI, Arcee, GMI, Kilo Code, OpenCode, Bedrock, and OpenAI-compatible endpoints.

**Template action:** add a provider metadata layer instead of hard-coding a short `ENV_VARS` list. The dashboard should distinguish:

- API-key providers that can be configured in `.env`.
- OAuth/device-flow providers that need an assisted setup flow or instructions.
- Endpoint-based providers that require both key and base URL.

### 3. Add Nous Portal and Tool Gateway onboarding

Upstream documentation recommends Nous Portal as the simplest path because one OAuth setup can cover models plus managed tools. Tool Gateway can route web search/extraction, image generation, TTS, and browser automation without separate Firecrawl/FAL/OpenAI/Browserbase accounts.

**Template action:** add a dashboard onboarding card for `hermes setup --portal` / `hermes model`, explain OAuth limitations in hosted Railway, and surface Tool Gateway status/configuration in `/api/status` where available.

### 4. Expand channel support and show adapter health

Upstream lists a broader gateway surface than this template currently exposes, including Signal, SMS, DingTalk, Feishu, WeCom, BlueBubbles, Home Assistant, Microsoft Teams, an API Server adapter, and Webhooks. Upstream also documents `/platform list`, `/platform pause`, `/platform resume`, and circuit-breaker states for day-2 operations.

**Template action:** implement adapter status controls in the admin UI before adding every channel form. The practical order should be:

1. Run `hermes gateway status` / `hermes gateway list` or parse gateway structured logs.
2. Add read-only platform state to `/api/status`.
3. Add pause/resume controls when upstream exposes stable non-interactive commands for them.
4. Add new channel credential forms one at a time.

### 5. Add first-class API Server management

Upstream exposes Hermes as an OpenAI-compatible API server via `API_SERVER_ENABLED`, `API_SERVER_HOST`, `API_SERVER_PORT`, `API_SERVER_KEY`, CORS settings, and model naming. This is a strong fit for a hosted template because it lets users connect Open WebUI, LibreChat, LobeChat, and other frontends while retaining Hermes tools/memory/skills.

**Template action:** add an “API Server” section to the dashboard that writes the API server env vars, generates `API_SERVER_KEY`, warns about terminal-tool exposure, and reports whether the server is enabled.

### 6. Use upstream logs and diagnostics instead of only subprocess stdout

The template currently streams child-process stdout into an in-memory ring buffer. Upstream now has `hermes logs` with `agent`, `errors`, `gateway`, filtering, rotation, and `hermes dump` / `hermes doctor` diagnostics.

**Template action:** add read-only endpoints that call or tail upstream log files under `HERMES_HOME` and expose `hermes doctor` output. Keep the current ring buffer as a startup/fallback stream.

### 7. Make tool routing real, or remove it from the template layer

The local `tool_routing.py` policy only observes image-like log events and appends a routing note; it does not actually intercept or reroute Hermes tool calls. If upstream has native tool-routing support, the template should configure that instead of implying local enforcement.

**Template action:** either wire routing through upstream-supported configuration/hooks, or rename the feature as “image artifact detection” so the dashboard/logs do not overstate behavior.

## Recommended implementation order

### P0 — Container reliability and release hygiene

- Pin the default Docker build to the current stable upstream release tag.
- Keep the build-arg override documented.
- Add a visible status field showing the installed Hermes version/ref.
- Add a smoke check command to the docs: `hermes version && hermes gateway --help`.

### P1 — Provider model parity

- Refactor provider/channel/tool definitions into metadata that includes labels, env vars, setup mode, docs URL, and dashboard help text.
- Add missing key-based providers first: OpenAI-compatible, OpenAI, Anthropic API-key mode, NovitaAI, NVIDIA, xAI, Arcee, GMI, Kilo Code, OpenCode, Bedrock where practical.
- Add explicit OAuth/manual setup guidance for Nous Portal, OpenAI Codex, Anthropic OAuth, Copilot, and MiniMax OAuth.

### P1 — Hosted API Server toggle

- Add `API_SERVER_*` env vars to the dashboard.
- Generate a random bearer key when enabling the API server.
- Require explicit CORS origins and show a security warning before binding publicly.

### P2 — Gateway operations

- Surface gateway version, profile, adapters, and platform circuit-breaker state.
- Add read-only upstream log views for `agent`, `errors`, and `gateway` logs.
- Add `doctor` / `dump` diagnostics for support bundles, redacting secrets.

### P2 — Tool Gateway / tool configuration

- Add Tool Gateway status for users configured through Nous Portal.
- Let users choose direct-key vs Nous Tool Gateway backends when upstream exposes stable non-interactive config paths.
- Keep direct keys as fallback for users who do not use Nous Portal.

### P3 — Channel expansion

- Add Webhooks and API Server first because they are good hosted-template fits.
- Add Microsoft Teams, Signal/SMS, and regional messaging adapters after their credential requirements are verified against upstream docs.

## Implemented in this pass

- Expanded the dashboard/env registry to cover upstream's current provider matrix much more closely, including direct API-key providers, OpenAI-compatible base URLs, Bedrock credential fields, and OAuth/manual setup entries.
- Added first-class API Server configuration with an enable toggle, generated bearer key, host/port/model/CORS fields, and a security warning.
- Added dashboard support for newly relevant hosted-template channels: Signal, SMS/Twilio, and Webhooks.
- Expanded tool configuration for SearXNG, Exa, Browser Use, Groq, ElevenLabs, Mistral, Supermemory, Daytona, and Nous Tool Gateway.

## Suggested acceptance criteria

- A fresh Railway deploy can build deterministically from `v2026.5.29` and show the installed Hermes version.
- A user can configure at least one API-key provider and Telegram from the dashboard, start the gateway, and approve a pairing request.
- A user can enable API Server mode with an autogenerated bearer token and copy an OpenAI-compatible base URL/key into a frontend.
- The dashboard makes OAuth-based providers discoverable without pretending it can complete browser/device flows entirely inside Railway.
- Logs include both startup stdout and upstream rotated log files.
