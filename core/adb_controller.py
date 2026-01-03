import subprocess
import numpy as np
import cv2
import os
from . import config # 匯入設定檔

class AdbController:
    def __init__(self):
        self.adb_path = config.ADB_PATH
        self.device_id = config.DEVICE_ID

    def run_cmd(self, command):
        """ 執行 ADB Shell 指令 """
        full_cmd = f'"{self.adb_path}" -s {self.device_id} shell {command}'
        try:
            subprocess.run(full_cmd, shell=True, timeout=5)
        except subprocess.TimeoutExpired:
            print("❌ ADB 指令逾時")

    def get_screenshot(self):
        """ 獲取畫面轉為 OpenCV 格式 """
        full_cmd = f'"{self.adb_path}" -s {self.device_id} shell screencap -p'
        try:
            process = subprocess.Popen(
                full_cmd, shell=True, 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            data, _ = process.communicate(timeout=10)
            
            # Windows 換行符號處理
            if os.name == 'nt':
                data = data.replace(b'\r\n', b'\n')
            
            if len(data) < 100: return None

            image_array = np.frombuffer(data, np.uint8)
            return cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"❌ 截圖失敗: {e}")
            return None

    def tap(self, x, y):
        self.run_cmd(f"input tap {x} {y}")

    def swipe(self, sx, sy, ex, ey, duration=300):
        self.run_cmd(f"input swipe {sx} {sy} {ex} {ey} {duration}")