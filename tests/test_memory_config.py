import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

import server


class TestMemoryConfig(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        patcher = patch.object(server, "HERMES_HOME", self.home.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.path = Path(self.home.name) / "config.yaml"

    def read_config(self):
        return yaml.safe_load(self.path.read_text())

    def test_new_config_has_larger_caps_and_round_trips_model(self):
        model = 'model:"quoted"\nname'
        server.write_config_yaml({"LLM_MODEL": model})
        config = self.read_config()
        self.assertEqual(config["model"]["default"], model)
        self.assertEqual(config["memory"], {
            "memory_char_limit": 4000, "user_char_limit": 2000,
        })

    def test_repeated_saves_preserve_memory_and_context_configuration(self):
        existing = {
            "memory": {"provider": "honcho", "write_approval": True,
                       "memory_char_limit": 6000},
            "compression": {"enabled": True, "threshold": 0.8},
            "auxiliary": {"compression": {"model": "custom-model"}},
            "context": {"engine": "custom-engine"},
            "terminal": {"timeout": 120},
        }
        self.path.write_text(yaml.safe_dump(existing))
        for model in ("first-model", "second-model"):
            server.write_config_yaml({"LLM_MODEL": model})
        config = self.read_config()
        for section in ("compression", "auxiliary", "context"):
            self.assertEqual(config[section], existing[section])
        self.assertEqual(config["memory"]["provider"], "honcho")
        self.assertTrue(config["memory"]["write_approval"])
        self.assertEqual(config["memory"]["memory_char_limit"], 6000)
        self.assertEqual(config["memory"]["user_char_limit"], 2000)
        self.assertEqual(config["terminal"]["timeout"], 120)

    def test_invalid_config_is_not_overwritten(self):
        for content in ("memory: [invalid]\n", "- not-a-mapping\n", "memory: ["):
            with self.subTest(content=content):
                self.path.write_text(content)
                with self.assertRaises((ValueError, yaml.YAMLError)):
                    server.write_config_yaml({})
                self.assertEqual(self.path.read_text(), content)

    def test_explicit_reset_restores_defaults(self):
        self.path.write_text("memory:\n  memory_char_limit: 6000\ncompression:\n  enabled: false\n")
        server.write_config_yaml({}, reset=True)
        config = self.read_config()
        self.assertNotIn("compression", config)
        self.assertEqual(config["memory"]["memory_char_limit"], 4000)
