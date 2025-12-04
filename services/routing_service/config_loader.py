# services/routing_service/config_loader.py
from pathlib import Path
import yaml

CONFIG_PATH = Path("config/routing_config.yaml")

def load_routing_cfg():
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open() as f:
            return yaml.safe_load(f) or {}
    return {}  # fallback empty dict

ROUTING_CFG = load_routing_cfg()
