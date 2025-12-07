"""
Module quản lý checkpoint để lưu trạng thái xử lý pipeline.
Cho phép resume từ điểm đã dừng khi bị interrupt.
"""
import os
import json
from typing import Optional


class CheckpointManager:
    """Quản lý checkpoint để lưu và khôi phục trạng thái xử lý"""
    
    def __init__(self, checkpoint_path: str = "data/processed/pipeline.checkpoint"):
        self.checkpoint_path = checkpoint_path
        # Đảm bảo thư mục tồn tại
        checkpoint_dir = os.path.dirname(checkpoint_path)
        if checkpoint_dir and not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir, exist_ok=True)
    
    def save(self, processed: int, total_written: int, total_errors: int = 0):
        """Lưu checkpoint với số lượng đã xử lý"""
        checkpoint_data = {
            "processed": processed,
            "total_written": total_written,
            "total_errors": total_errors
        }
        try:
            with open(self.checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2)
        except Exception as e:
            print(f"[WARNING] Could not save checkpoint: {e}")
    
    def load(self) -> Optional[dict]:
        """Tải checkpoint nếu có"""
        if not os.path.exists(self.checkpoint_path):
            return None
        
        try:
            with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Could not load checkpoint: {e}")
            return None
    
    def exists(self) -> bool:
        """Kiểm tra checkpoint có tồn tại không"""
        return os.path.exists(self.checkpoint_path)
    
    def clear(self):
        """Xóa checkpoint"""
        if os.path.exists(self.checkpoint_path):
            try:
                os.remove(self.checkpoint_path)
            except Exception:
                pass

