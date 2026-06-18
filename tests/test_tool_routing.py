import unittest

from tool_routing import route_tool_payload


class TestToolRouting(unittest.TestCase):
    def test_capture_reroutes_with_base64(self):
        decision = route_tool_payload("capture", {"image_base64": "abcd"})
        self.assertTrue(decision.route_via_aux_vision)
        self.assertEqual(decision.target_tool, "auxiliary.vision")
        self.assertEqual(decision.reason, "image_base64_present")

    def test_image_like_tool_without_artifact_does_not_reroute(self):
        decision = route_tool_payload("screenshot", {"text": "no image"})
        self.assertFalse(decision.route_via_aux_vision)
        self.assertEqual(decision.reason, "no_image_artifact")

    def test_non_image_tool_does_not_reroute(self):
        decision = route_tool_payload("search", {"image_url": "https://x/y.png"})
        self.assertFalse(decision.route_via_aux_vision)
        self.assertEqual(decision.reason, "tool_not_image_like")

    def test_image_mime_type_reroutes_for_other_image_like_paths(self):
        decision = route_tool_payload("read_image", {"mime_type": "image/png"})
        self.assertTrue(decision.route_via_aux_vision)
        self.assertEqual(decision.reason, "image_mime_type")


class TestUpstreamConfigCoverage(unittest.TestCase):
    def test_env_registry_includes_current_provider_tool_and_gateway_vars(self):
        import server

        keys = {k for k, *_ in server.ENV_VARS}
        expected = {
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "NOVITA_API_KEY",
            "NVIDIA_API_KEY",
            "XAI_API_KEY",
            "API_SERVER_ENABLED",
            "API_SERVER_KEY",
            "WEBHOOK_ENABLED",
            "SIGNAL_HTTP_URL",
            "TWILIO_ACCOUNT_SID",
            "EXA_API_KEY",
            "SEARXNG_URL",
            "TOOL_GATEWAY_USER_TOKEN",
        }
        self.assertTrue(expected.issubset(keys))

    def test_channel_map_includes_hosted_api_and_webhook_adapters(self):
        import server

        self.assertEqual(server.CHANNEL_MAP["API Server"], "API_SERVER_ENABLED")
        self.assertEqual(server.CHANNEL_MAP["Webhooks"], "WEBHOOK_ENABLED")

    def test_provider_detection_includes_runtime_environment(self):
        import os
        import server

        old_value = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ["OPENAI_API_KEY"] = "runtime-provider-key"
            self.assertTrue(server.has_configured_provider({}))
            effective = server.effective_config_env({})
            self.assertEqual(effective["OPENAI_API_KEY"], "runtime-provider-key")
        finally:
            if old_value is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = old_value

    def test_dockerfile_copies_server_import_dependencies(self):
        from pathlib import Path

        dockerfile = Path("Dockerfile").read_text()
        self.assertIn("COPY server.py /app/server.py", dockerfile)
        self.assertIn("COPY outer_loop.py /app/outer_loop.py", dockerfile)
        self.assertIn("COPY tool_routing.py /app/tool_routing.py", dockerfile)


if __name__ == "__main__":
    unittest.main()
