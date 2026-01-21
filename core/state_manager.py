# core/state_manager.py
import json
from pathlib import Path
from . import config

class StateManager:
    def __init__(self):
        self.file_path = Path(config.STATE_FILE)

    def load_state(self):
        """ 讀取進度，如果沒有存檔就回傳預設值 (從第0個難度, 第1關開始) """
        if not self.file_path.exists():
            return {"diff_index": 0, "package_n": 0}
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            print("⚠️ 存檔損毀，重置進度")
            return {"diff_index": 0, "package_n": 0}

    def save_state(self, diff_index, package_n):
        """ 儲存當前進度 """
        data = {"diff_index": diff_index, "package_n": package_n}
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        print(f"💾 [存檔成功] 檔案位置: {self.file_path.resolve()}")
        # print(f"💾 進度已儲存: 難度[{diff_index+1}] - 關卡[{package_n}]")