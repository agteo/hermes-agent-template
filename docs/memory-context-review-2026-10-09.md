# Memory and context review — 2026-10-09

## Findings

The template was pinned to `v2026.7.7.2`. The suggested `v2026.7.20` tag exists
and resolves to commit `3ef6bbd201263d354fd83ec55b3c306ded2eb72a` (Hermes 0.19.0).
Python 3.12 is within its supported range. This is a controlled upgrade, not an
upgrade to current upstream main. Tags through `v2026.9.24` were present at review
time. A move to those releases needs a separate compatibility/build review.

The repository's generated config lacked memory settings. It also replaced the
entire config on dashboard saves and gateway starts, discarding custom memory
providers, compression routes, and other upstream settings. The update merges
dashboard-owned model/provider/data-directory settings, supplies absent terminal
and agent defaults, and defaults absent memory caps to 4000/2000. Explicit caps
and all other settings survive repeated saves. Invalid YAML/section shapes fail
without overwriting the YAML file. Explicit Reset Config still restores defaults.
Saving normalizes YAML formatting and comments.

No production filesystem was inspected: the reported live-only patch and current
live caps cannot be independently confirmed here. The actual remote branch is
`main`, not `master`.

## What each memory mechanism solves

- **Persistent memory:** `memories/MEMORY.md` and `memories/USER.md` hold concise
  facts injected into the system prompt. Limits are characters, not tokens.
  Larger limits add prompt cost on every request and will eventually fill again.
  Confirm a successful `memory` tool write; a textual promise is not persistence.
  Keep entries compact and consolidate stale facts when near capacity.
- **Session boundaries:** memory snapshots are frozen at session start. Use
  `/new` after finishing a task or changing topics to reload saved facts and
  shorten context. Restarting a gateway is not a reliable session boundary.
- **Historical recall:** `session_search` retrieves stored conversations from
  `state.db` on demand. Use it for older details instead of cramming transcripts
  into always-loaded notes. Put reusable procedures in skills.
- **Active context:** compression summarizes long conversations; it is lossy.
  `/compress` helps an active thread but does not increase persistent-note caps.
  Preserve and tune `compression`, `auxiliary.compression`, and `context` only
  against documentation for the installed release. No guessed thresholds or
  auxiliary models are enabled by this patch.
- **External memory:** current docs describe additive provider plugins and
  per-turn recall. Consider one only if built-in notes plus session search are
  insufficient. Current plugin installation instructions may differ from July's
  release; do not assume setting an API key alone activates a provider.

## Deployment and rollback

1. Review the changes together, then merge/push to the Railway-linked branch.
   Confirm Railway is actually linked to `main` and automatic deploys are enabled.
2. Back up the `/data/.hermes` volume before upgrading. Include configuration,
   memories, `state.db`, cron data, sessions, skills, and any provider databases.
   Use an application-consistent database backup or stop writers while copying.
3. Build/deploy `v2026.7.20`. Verify the generated `config.yaml` contains
   `memory.memory_char_limit: 4000` and `memory.user_char_limit: 2000`.
   Explicit existing limits are preserved; adjust them deliberately if different.
4. Verify an authenticated model/API request, a real Telegram and Slack response,
   pairing, and cron registration. Inspect for memory-write failures and test a
   saved fact after `/new`. Health alone does not validate gateway connectivity.
5. Revert the version pin to `v2026.7.7.2` to roll back the image if necessary,
   retaining the memory/config fix. Confirm the old image can read the volume;
   image rollback does not undo database/config migrations. Restore the backup
   if data compatibility requires it.

The volume normally survives image redeploys, but this does not guarantee that
every older release can read data written by a newer one. No push or Railway
deployment is performed by this review.

## Validation

- 29 template tests passed, including new caps, repeated config saves, invalid
  config preservation, and explicit reset. The reusable installation script
  passed twice with Python 3.12 and Hermes's `[all]` dependencies.
- The actual July `MemoryStore` accepted 3,000-character agent notes and
  1,600-character user notes, persisted them across reload, and rejected writes
  exceeding 4000/2000.
- Native HTTP checks passed for health, authentication, dashboard rendering,
  and configuration save/read including generated caps.
- A complete image built and booted via `/app/start.sh`; its HTTP dashboard and
  generated caps passed. The cloud validation used a temporary Dockerfile to add
  the supplied proxy CA trust and resolve the proxy hostname. TLS verification
  and Debian package verification stayed enabled. No cloud-specific trust changes
  were added to the production Dockerfile.
- Production provider API calls, Telegram/Slack connectivity, and cron
  registration remain unverified. No production credentials or volume were used.

## Official sources reviewed

Current documentation was read from official upstream main at
`0670ba45240b734c1e6f6d1d5ead87233f37df49`; relevant behavior and configuration
were also checked in the proposed July tag.

- [Current persistent-memory documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- [Current session documentation](https://hermes-agent.nousresearch.com/docs/user-guide/sessions)
- [Current context-compression documentation](https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching)
- [Current memory-provider documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers)
- [July release memory documentation](https://github.com/NousResearch/hermes-agent/blob/v2026.7.20/website/docs/user-guide/features/memory.md)
- [July release package and Python requirements](https://github.com/NousResearch/hermes-agent/blob/v2026.7.20/pyproject.toml)
- [Immutable current-memory source](https://github.com/NousResearch/hermes-agent/blob/0670ba45240b734c1e6f6d1d5ead87233f37df49/website/docs/user-guide/features/memory.md)
