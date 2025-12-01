import yaml
import os

class Config:
    def __init__(self, path="config/config.yaml"):
        self.path = path
        self._config = self._load_yaml()
        
    def _load_yaml(self):
        if not os.path.exists(self.path):
            self._create_default_config()
        
        with open(self.path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
    def _create_default_config(self):
        """Create default config file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.path) of ".", exist_ok=True)
        default_config = {
            "app": {
                "name": "ThreatFeedAggregator",
                "version": "1.0.0"
            }
            # Để sẵn, sau này ông sẽ đưa list feed vào đây
            "feeds": []
        
    def get(self, *keys, default=None):
         """Create default config file if it doesn't exist"""
        data = self._config
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return default
            
        return data
#Tạo instance global để import nhanh    
config = Config()