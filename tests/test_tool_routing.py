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
    def test_dashboard_probe_reports_available_without_enabling_management(self):
        import server

        capability = server.dashboard_capability_from_probe(
            0, "Usage: hermes dashboard [OPTIONS]\nLaunch the web dashboard"
        )
        self.assertTrue(capability["available"])
        self.assertEqual(capability["state"], "available")
        self.assertFalse(capability["management_enabled"])
        self.assertEqual(capability["docs_url"], server.UPSTREAM_DASHBOARD_DOCS)

    def test_dashboard_probe_degrades_safely_for_older_builds(self):
        import server

        unsupported = server.dashboard_capability_from_probe(
            2, "No such command: dashboard"
        )
        missing = server.dashboard_capability_from_probe(None, "", "not_found")
        self.assertFalse(unsupported["available"])
        self.assertEqual(unsupported["state"], "unsupported")
        self.assertFalse(missing["available"])
        self.assertEqual(missing["state"], "hermes_not_found")

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
            "VOICE_TOOLS_OPENAI_KEY",
            "GROQ_API_KEY",
            "ELEVENLABS_API_KEY",
            "MISTRAL_API_KEY",
        }
        self.assertTrue(expected.issubset(keys))

    def test_channel_map_includes_hosted_api_and_webhook_adapters(self):
        import server

        self.assertEqual(server.CHANNEL_MAP["API Server"], "API_SERVER_ENABLED")
        self.assertEqual(server.CHANNEL_MAP["Webhooks"], "WEBHOOK_ENABLED")

    def test_voice_registry_maps_supported_credential_paths(self):
        import server

        self.assertEqual(server.VOICE_KEYS["openai"], "VOICE_TOOLS_OPENAI_KEY")
        self.assertEqual(server.VOICE_KEYS["groq"], "GROQ_API_KEY")
        self.assertEqual(server.VOICE_KEYS["elevenlabs"], "ELEVENLABS_API_KEY")
        self.assertEqual(server.VOICE_KEYS["mistral"], "MISTRAL_API_KEY")

    def test_openrouter_and_elevenlabs_is_output_only_voice(self):
        import server

        status = server.voice_readiness({
            "OPENROUTER_API_KEY": "llm-key",
            "ELEVENLABS_API_KEY": "speech-key",
        })
        self.assertFalse(status["transcription_ready"])
        self.assertTrue(status["synthesis_ready"])
        self.assertFalse(status["complete_pipeline_ready"])

    def test_voice_does_not_require_every_provider_key(self):
        import server

        openai_status = server.voice_readiness({"VOICE_TOOLS_OPENAI_KEY": "voice-key"})
        split_status = server.voice_readiness({
            "GROQ_API_KEY": "stt-key",
            "ELEVENLABS_API_KEY": "tts-key",
        })
        self.assertTrue(openai_status["complete_pipeline_ready"])
        self.assertTrue(split_status["complete_pipeline_ready"])

    def test_voice_readiness_reports_template_capability_limits(self):
        import server

        status = server.voice_readiness({"VOICE_TOOLS_OPENAI_KEY": "voice-key"})
        self.assertFalse(status["capabilities"]["duplex_audio"])
        self.assertFalse(status["capabilities"]["wake_word"])
        self.assertFalse(status["capabilities"]["command_word"])
        self.assertEqual(
            status["capabilities"]["telegram_voice_notes"],
            "channel_dependent",
        )

    def test_voice_keys_round_trip_into_gateway_environment(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import server

        with tempfile.TemporaryDirectory() as td:
            env_file = Path(td) / ".env"
            server.write_env(env_file, {
                "LLM_MODEL": "openrouter/model",
                "OPENROUTER_API_KEY": "openrouter-key",
                "GROQ_API_KEY": "transcription-key",
                "ELEVENLABS_API_KEY": "speech-key",
            })
            with patch.object(server, "ENV_FILE", env_file), patch.dict(
                os.environ, {"HERMES_HOME": td}, clear=False
            ):
                child_env = server.gateway_environment()

        self.assertEqual(child_env["OPENROUTER_API_KEY"], "openrouter-key")
        self.assertEqual(child_env["GROQ_API_KEY"], "transcription-key")
        self.assertEqual(child_env["ELEVENLABS_API_KEY"], "speech-key")
        self.assertEqual(child_env["HERMES_HOME"], server.HERMES_HOME)

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
