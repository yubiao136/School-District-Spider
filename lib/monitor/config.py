import os
from dataclasses import dataclass
from typing import List

import yaml


_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "monitor.yaml",
)


@dataclass
class SchoolGroup:
    name: str
    schools: List[str]


@dataclass
class MonitorConfig:
    city: dict
    school_groups: List[SchoolGroup]
    target_xiaoqu: List[str]
    budget: dict
    output: dict
    notification: dict


def _env_override(key: str, default: str) -> str:
    return os.environ.get(key, default)


def load_config(path: str = _CONFIG_PATH) -> MonitorConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw: dict = yaml.safe_load(f)

    raw["output"]["dir"] = _env_override("MONITOR_OUTPUT_DIR", raw["output"]["dir"])

    if "notification" in raw:
        for k in list(raw["notification"].keys()):
            env_val = _env_override(f"MONITOR_NOTIFY_{k.upper()}", None)
            if env_val is not None:
                raw["notification"][k] = env_val

    groups = [SchoolGroup(**g) for g in raw.pop("school_groups", [])]

    return MonitorConfig(school_groups=groups, **raw)
