from __future__ import annotations

from dataclasses import dataclass
from typing import Any

IMAGE_LIKE_TOOLS = {
    "capture",
    "capture_screenshot",
    "screenshot",
    "read_image",
    "image_ocr",
    "computer_use.capture",
}


@dataclass(frozen=True)
class ToolRoutingDecision:
    route_via_aux_vision: bool
    reason: str
    target_tool: str


def route_tool_payload(tool_name: str, payload: dict[str, Any] | None) -> ToolRoutingDecision:
    """Centralized policy for routing image-like tool payloads via auxiliary.vision."""
    payload = payload or {}

    normalized = tool_name.strip().lower()
    if normalized not in IMAGE_LIKE_TOOLS:
        return ToolRoutingDecision(False, "tool_not_image_like", tool_name)

    mime_type = str(payload.get("mime_type", "")).lower()
    if mime_type.startswith("image/"):
        return ToolRoutingDecision(True, "image_mime_type", "auxiliary.vision")

    if isinstance(payload.get("image_base64"), str) and payload["image_base64"].strip():
        return ToolRoutingDecision(True, "image_base64_present", "auxiliary.vision")

    if isinstance(payload.get("image_url"), str) and payload["image_url"].strip():
        return ToolRoutingDecision(True, "image_url_present", "auxiliary.vision")

    return ToolRoutingDecision(False, "no_image_artifact", tool_name)
