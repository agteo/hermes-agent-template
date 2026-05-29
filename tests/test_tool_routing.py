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



if __name__ == "__main__":
    unittest.main()
