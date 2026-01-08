import subprocess
import numpy as np
import random
import cv2
import os
import time
from . import config # 匯入設定檔

class AdbController:
    def __init__(self):
        self.adb_path = config.ADB_PATH
        self.device_id = config.DEVICE_ID
        self.target_app_package = config.target_app_package

    def run_cmd(self, command):
        """ 
        [智慧相容版] 執行 ADB 指令 
        會自動偵測輸入的指令是否已經包含 'shell'，避免重複
        """
        # 0. 先把指令的前後空白清乾淨
        clean_cmd = command.strip()

        # 1. 判斷邏輯：
        # 如果指令開頭已經是 "shell" -> 不要雞婆，直接用
        # 如果指令開頭是 "pull" 或 "push" 或 "connect" (這些不需要 shell) -> 直接用
        if clean_cmd.startswith("shell") or clean_cmd.startswith("pull") or clean_cmd.startswith("connect"):
            full_cmd = f'"{config.ADB_PATH}" -s {config.DEVICE_ID} {clean_cmd}'
        else:
            # 2. 如果沒寫 shell (例如原本的 "input tap...") -> 幫忙補上
            full_cmd = f'"{config.ADB_PATH}" -s {config.DEVICE_ID} shell {clean_cmd}'
        
        try:
            result = subprocess.run(
                full_cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                encoding='utf-8', 
                errors='ignore',
                timeout=15 
            )
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            print(f"❌ ADB 指令逾時: {command}")
            return ""
        except Exception as e:
            print(f"❌ 指令執行失敗: {command} | {e}")
            return ""

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

    def tap(self, x, y, max_offset=5):
        dx = random.randint(-max_offset, max_offset)
        dy = random.randint(-max_offset, max_offset)
        
        final_x = x + dx
        final_y = y + dy
        self.run_cmd(f"input swipe {x} {y} {final_x} {final_y} {10}")

    def swipe(self, sx, sy, ex, ey, duration=300):
        self.run_cmd(f"input swipe {sx} {sy} {ex} {ey} {duration}")

    def stop_app(self, package_name = config.target_app_package):
        cmd = f"am force-stop {package_name}"
        self.run_cmd(cmd)

    def start_app(self, package_name = config.target_app_package):
        # 這裡單純送出啟動指令
        cmd = f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
        self.run_cmd(cmd)

    def restart_app(self, package_name = config.target_app_package):
        """ [系統] 快速重啟 (殺掉 -> 打開) """
        print(f"📱 [ADB] 正在重啟 APP: {package_name}")
        self.stop_app(package_name)
        time.sleep(3.0) # 系統反應時間
        self.start_app(package_name)

    # ==========================================
    # 模擬器控制模組 (Hard Reboot)
    # ==========================================
    def restart_emulator(self):
        """ [模擬器] 暴力重啟 (LDPlayer / MuMu) """
        manager = config.MANAGER_PATH
        idx = config.EMULATOR_INDEX
        etype = config.EMULATOR_TYPE

        if not manager.exists():
            print("❌ 無法重啟：設定檔中的 manager_path 無效")
            return

        print(f"💀 [System] 執行模擬器重啟 (Type: {etype} | Index: {idx})...")

        try:
            cmd_quit = []
            cmd_open = []

            # 根據 config 決定語法
            if etype == "ldplayer":
                cmd_quit = [str(manager), "quit", "--index", idx]
                cmd_open = [str(manager), "launch", "--index", idx]
            elif etype == "mumu":
                cmd_quit = [str(manager), "close_player", "-i", idx]
                cmd_open = [str(manager), "launch_player", "-i", idx]
            else:
                print(f"❌ 未支援的模擬器類型: {etype}")
                return

            # 1. 關閉模擬器
            print(f"   💤 正在關閉模擬器...")
            subprocess.run(cmd_quit, shell=True, check=True)
            time.sleep(5.0) 

            # 2. 啟動模擬器
            print(f"   🚀 正在啟動模擬器...")
            subprocess.run(cmd_open, shell=True, check=True)
            
            # 3. 等待 ADB 連線
            self.wait_for_device_boot()

        except Exception as e:
            print(f"❌ 模擬器重啟失敗: {e}")

    def wait_for_device_boot(self, timeout=600):
        """ 等待 ADB 重新連線成功 """
        print("   ⏳ 等待 Android 系統啟動中...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                connect_cmd = f'"{config.ADB_PATH}" connect {config.DEVICE_ID}'
                subprocess.run(
                    connect_cmd, 
                    shell=True, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL,
                    timeout=3
                )
                res = self.run_cmd("shell echo ok")
                if "ok" in res.strip():
                    print("   ✅ 模擬器已連線！")
                    return True
            except Exception:
                pass
            
            time.sleep(2)

        print("   ⚠️ 等待模擬器啟動超時")
        return False