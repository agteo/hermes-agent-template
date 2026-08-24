---
name: render-tool
description: Create, check, list, and cancel queued image or video renders through the configured remote Render API. Use when a user asks to generate/render an image, picture, video, animation, motion, or clip, or asks about/cancels a previous render job.
---

# Render Queue

Use `python /app/skills/render-tool/scripts/render_tool.py` as the only interface to the render service. Never connect to the worker machine, ComfyUI, storage, Tailscale, SSH, or RDP. Never print or reveal `AGENT_API_KEY`.

## Commands

- Create: `python /app/skills/render-tool/scripts/render_tool.py create --prompt <text> --output-type image|video --user-id <stable-id> --source-platform <platform> --source-channel-id <id> [--source-message-id <id>] [--quality draft|balanced|quality] [--aspect-ratio 1:1|4:5|9:16|16:9] [--seed <integer>]`
- Check: `python /app/skills/render-tool/scripts/render_tool.py check --job-id <id>`
- List: `python /app/skills/render-tool/scripts/render_tool.py list --user-id <stable-id> [--status queued|claimed|running|uploading|completed|failed|cancel_requested|cancelled]`
- Cancel: `python /app/skills/render-tool/scripts/render_tool.py cancel --job-id <id>`

Use the messaging context's stable user/chat identifier and source fields. Prefix a Telegram stable ID with `telegram:`. Omit `--source-message-id` only when the channel does not expose it.

## Creation policy

- Default to `image`, `draft`, and `16:9`.
- Create a video only when the user explicitly requests video, animation, motion, a clip, or duration. Video uses 121 frames and is more expensive.
- Submit the user's visual request as the prompt without inventing a negative prompt.
- After success say: `Queued render job <job_id>. It will start when the local render machine is available.` Do not promise a completion time.

## Status policy

- `queued`: Say it is queued and waiting for the local render machine.
- `claimed`: Say it was assigned but rendering has not started.
- `running`: Say `This job is rendering now: <progress_percent>%.` Do not say it started before this status.
- `uploading`: Say rendering finished locally and the result is uploading.
- `completed`: A check response contains fresh signed `output_urls`. Prefer sending the actual media; otherwise send a signed URL. When a list shows a completed job, run `check` before sending it so the URL is refreshed.
- `failed`: Say `The render failed: <error_message>` plainly.
- `cancel_requested`: Say cancellation was requested for the active job.
- `cancelled`: Say the job was cancelled.

If the command reports that the API is unavailable, say: `The render queue is temporarily unavailable, so I could not submit or check the job. Try again later.`
