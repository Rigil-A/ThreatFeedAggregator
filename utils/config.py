import yaml
import os

class Config:
    def __init__(self, path=None):
        if path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base_dir, "config", "config.yaml")
        self.path = path
        self._config = self._load_yaml()
        
    def _load_yaml(self):
        if not os.path.exists(self.path):
            self._create_default_config()
        
        with open(self.path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    
    def _create_default_config(self):
        """Create default config file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)

        default_config = {
            "app": {
                "name": "ThreatFeedAggregator",
                "version": "1.0.0"
            },
            "feeds": []
        }

        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                default_config,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )

    def get(self, *keys, default=None):
        """Get nested values from config"""
        data = self._config
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
        return data


# Tạo instance global
config = Config()
