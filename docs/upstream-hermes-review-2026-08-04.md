# Upstream Hermes Agent Review — Herald — 2026-08-04

This pass reviews the upstream **Herald** release with a hosted Railway deployment in mind. It follows the July review rather than replacing it: the image remains pinned to the last build-verified tag (`v2026.7.7.2`) until Herald receives a clean container and channel smoke test.

## Sources

- [Hermes Agent releases](https://github.com/NousResearch/hermes-agent/releases)
- [Upstream repository](https://github.com/NousResearch/hermes-agent)
- [Hermes documentation](https://hermes-agent.nousresearch.com/docs/)
- [Previous template review](upstream-hermes-review-2026-07-10.md)

## Recommendation

Adopt Herald's voice direction first at the **configuration and observability boundary**, without duplicating upstream audio processing. Railway should persist the credentials Hermes already consumes, explain complete provider combinations, and report whether a usable speech pipeline is configured. Audio capture, transcription, synthesis, interruption handling, and channel delivery should remain upstream responsibilities.

Do not make an unverified release-pin jump solely to expose the new UI. Promote the Herald tag only after a clean image build and Telegram/Discord voice-note smoke tests; retain `HERMES_REF` as the rollback control.

## Voice adoption

### Adopt now

1. **Dedicated voice setup.** Separate speech credentials from the generic tool list. Offer the two practical paths already represented by Hermes environment variables:
   - OpenAI voice credentials for a single-provider STT/TTS path.
   - Groq or Mistral transcription paired with ElevenLabs synthesis.
   The agent's LLM is independent: OpenRouter can power chat/reasoning in either case. OpenRouter does not replace a speech-to-text credential in Hermes' voice-tool configuration. OpenRouter plus ElevenLabs therefore supports the main LLM and spoken output, but voice input still needs OpenAI, Groq, or Mistral.
2. **Readiness rather than false health.** `/api/status` should report individual provider presence and distinguish a complete OpenAI path from a complete split STT/TTS path. A stored key means “configured,” not “provider reachable.”
3. **Keep secrets server-side.** Continue returning masked values from `/api/config`; never expose credential values in voice status or browser logs.
4. **Let upstream own media.** Do not add a second WebSocket/audio proxy in the admin server. That would duplicate codec, streaming, backpressure, and interruption behavior and increase the public attack surface.

### Adopt after staging validation

- Voice-note smoke tests for each enabled messaging adapter, including file-size and duration limits.
- A non-secret diagnostic that records selected STT/TTS path, last voice error category, and latency buckets when upstream exposes stable status hooks.
- Provider/model/voice selection controls only when their upstream config schema is stable and discoverable. Avoid inventing template-only variables.
- Documented behavior for fallback from synthesized speech to text when TTS fails.

### Defer

- Browser microphone capture in this Basic Auth admin panel.
- Public realtime audio ports or direct provider tokens in JavaScript.
- Template-owned wake-word, voice-activity detection, echo cancellation, or barge-in logic.
- Automatic release-pin promotion without container and channel testing.

## Duplex and activation semantics

The template's voice card is credential plumbing, not a realtime voice-mode implementation. Nothing in this change opens a microphone or establishes an audio stream, so it should not be described as half-duplex or full-duplex. Likewise, the template does not implement a wake word or command word. A messaging-channel voice note is activated by sending the note; live duplex, push-to-talk, or wake-word activation must be supplied and documented by the particular upstream Hermes client/channel before this dashboard advertises it. If reliable Telegram voice mode and wake-word activation are non-negotiable product requirements, do not roll this out beyond credential plumbing until those upstream capabilities are confirmed with channel smoke tests.

## Other Herald follow-ups

Herald's non-voice changes should be evaluated using the same rule used in the July review: expose stable upstream lifecycle, diagnostics, profile, skill, and backup primitives rather than maintaining parallel implementations. Gateway drain/busy state remains a higher operational priority than adding convenience controls that stop the subprocess directly.

## Implemented in this pass

- Added a dedicated voice credential section with complete-pipeline guidance.
- Added non-secret voice readiness data to `/api/status`.
- Added registry coverage tests for the four supported voice credential variables.
- Kept the reviewed stable image pin unchanged pending a Herald build and messaging-channel smoke test.
