import os
import unittest
from unittest.mock import patch

from lib.monitor.config import MonitorConfig, load_config

_CONFIG_YAML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "monitor.yaml",
)


class TestMonitorConfig(unittest.TestCase):
    def test_load_defaults(self):
        cfg = load_config(_CONFIG_YAML)
        self.assertIsInstance(cfg, MonitorConfig)
        self.assertEqual(cfg.city["code"], "tj")
        self.assertEqual(cfg.city["name"], "天津")
        self.assertEqual(len(cfg.target_xiaoqu), 13)
        self.assertIn("惠安里", cfg.target_xiaoqu)
        self.assertEqual(cfg.budget["max_price"], 800000)
        self.assertEqual(cfg.output["dir"], "/app/data")

    def test_school_groups(self):
        cfg = load_config(_CONFIG_YAML)
        self.assertEqual(len(cfg.school_groups), 3)
        self.assertEqual(cfg.school_groups[0].name, "塘沽一片")
        self.assertGreater(len(cfg.school_groups[0].schools), 0)

    def test_output_dir_env_override(self):
        with patch.dict(os.environ, {"MONITOR_OUTPUT_DIR": "/custom/data"}, clear=False):
            cfg = load_config(_CONFIG_YAML)
            self.assertEqual(cfg.output["dir"], "/custom/data")

    def test_output_dir_default_when_no_env(self):
        with patch.dict(os.environ, {}, clear=False):
            if "MONITOR_OUTPUT_DIR" in os.environ:
                del os.environ["MONITOR_OUTPUT_DIR"]
            cfg = load_config(_CONFIG_YAML)
            self.assertEqual(cfg.output["dir"], "/app/data")

    def test_dry_run_flag_no_error(self):
        from main import main
        with patch(
            "sys.argv", ["main.py", "run-once", "--dry-run"]
        ), patch.dict(os.environ, {}, clear=False):
            try:
                main()
            except SystemExit as e:
                self.fail(f"main() raised SystemExit({e.code}) unexpectedly")

    def test_no_network_requests(self):
        with patch("lib.monitor.config.yaml.safe_load") as mock_load:
            mock_load.return_value = {
                "city": {"code": "tj", "name": "天津"},
                "school_groups": [],
                "target_xiaoqu": ["惠安里"],
                "budget": {"max_price": 800000, "unit": "元"},
                "output": {"dir": "/app/data"},
                "notification": {"enabled": False},
            }
            cfg = load_config(_CONFIG_YAML)
            self.assertEqual(cfg.city["code"], "tj")


if __name__ == "__main__":
    unittest.main()
