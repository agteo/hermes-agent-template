#!/usr/bin/env python3
"""Small, dependency-free CLI for the authenticated remote render queue."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_API_URL = "https://egpu-worker-production.up.railway.app"
STATUSES = (
    "queued", "claimed", "running", "uploading", "completed", "failed",
    "cancel_requested", "cancelled",
)


class RenderAPIError(Exception):
    """An actionable, secret-safe render API error."""


def request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    api_url = os.environ.get("RENDER_API_URL", DEFAULT_API_URL).rstrip("/")
    api_key = os.environ.get("AGENT_API_KEY")
    if not api_key:
        raise RenderAPIError("AGENT_API_KEY is not configured")
    if urllib.parse.urlsplit(api_url).scheme not in {"http", "https"}:
        raise RenderAPIError("RENDER_API_URL must be an HTTP(S) URL")

    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(api_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RenderAPIError(f"Render API returned HTTP {exc.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RenderAPIError(f"Render API unavailable: {exc}") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise RenderAPIError("Render API returned an invalid JSON response") from None


def create(args: argparse.Namespace) -> Any:
    parameters: dict[str, Any] = {}
    if args.output_type == "video":
        parameters["frames"] = 121
    if args.seed is not None:
        parameters["seed"] = args.seed
    body = {
        "user_id": args.user_id,
        "workflow_name": "wan22-video" if args.output_type == "video" else "flux-image",
        "prompt": args.prompt,
        "negative_prompt": "",
        "preset": {"quality": args.quality, "aspect_ratio": args.aspect_ratio},
        "parameters": parameters,
        "source_platform": args.source_platform,
        "source_channel_id": args.source_channel_id,
        "source_message_id": args.source_message_id,
    }
    return request("POST", "/v1/jobs", body)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Manage remote render queue jobs")
    commands = root.add_subparsers(dest="command", required=True)
    create_parser = commands.add_parser("create")
    create_parser.add_argument("--prompt", required=True)
    create_parser.add_argument("--output-type", choices=("image", "video"), default="image")
    create_parser.add_argument("--quality", choices=("draft", "balanced", "quality"), default="draft")
    create_parser.add_argument("--aspect-ratio", choices=("1:1", "4:5", "9:16", "16:9"), default="16:9")
    create_parser.add_argument("--seed", type=int)
    create_parser.add_argument("--user-id", required=True)
    create_parser.add_argument("--source-platform", required=True)
    create_parser.add_argument("--source-channel-id", required=True)
    create_parser.add_argument("--source-message-id", default="")

    check_parser = commands.add_parser("check")
    check_parser.add_argument("--job-id", required=True)
    list_parser = commands.add_parser("list")
    list_parser.add_argument("--user-id", required=True)
    list_parser.add_argument("--status", choices=STATUSES)
    cancel_parser = commands.add_parser("cancel")
    cancel_parser.add_argument("--job-id", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "create":
            result = create(args)
        elif args.command == "check":
            result = request("GET", f"/v1/jobs/{urllib.parse.quote(args.job_id, safe='')}")
        elif args.command == "list":
            query = {"user_id": args.user_id}
            if args.status:
                query["status"] = args.status
            result = request("GET", "/v1/jobs?" + urllib.parse.urlencode(query))
        else:
            result = request("POST", f"/v1/jobs/{urllib.parse.quote(args.job_id, safe='')}/cancel", {})
    except RenderAPIError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
