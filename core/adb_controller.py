import subprocess
import numpy as np
import random
import cv2
import os
import time
from . import config # 匯入設定檔

class AdbController:
    def __init__(self, adb_path, device_id, target_app_package):
        self.adb_path = adb_path
        self.device_id = device_id
        self.target_app_package = target_app_package

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

    def _force_kill_emulator_process(self):
        """
        [核彈級] 強制獵殺模擬器行程
        當 Manager 卡死時，直接用 Windows 系統指令殺掉所有相關行程
        """
        etype = config.EMULATOR_TYPE
        print(f"🔪 [System] 偵測到模擬器/Manager 卡死，執行強制獵殺程序 ({etype})...")

        # 定義要獵殺的目標 (依據不同模擬器)
        # /F = 強制終止
        # /IM = 指定映像名稱
        # /T = 終止子行程 (斬草除根)
        
        targets = []
        if etype == "mumu":
            # MuMu 12 常見的行程名稱
            targets = [
                "MuMuManager.exe",    # 管理器
                "MuMuPlayer.exe",     # 模擬器主體
                "NemuHeadless.exe",   # 背景核心
                "NemuPlayer.exe"      # 舊版或相容行程
            ]
        elif etype == "ldplayer":
            # 雷電常見行程
            targets = [
                "dnplayer.exe",       # 雷電主體
                "ldconsole.exe",      # 控制台
                "LdBoxHeadless.exe"
            ]

        # 執行獵殺
        for process in targets:
            try:
                # 使用 DEVNULL 讓它安靜地殺，不要噴錯誤訊息 (例如行程原本就沒跑的時候)
                subprocess.run(
                    f"taskkill /F /IM {process} /T", 
                    shell=True, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass
        
        print("   ✅ 戰場清理完畢，等待冷卻...")
        time.sleep(3.0) # 殺完之後稍微等一下，讓 Windows 釋放資源

    def restart_emulator(self):
        """ [模擬器] 暴力重啟 (包含防卡死機制) """
        manager = config.MANAGER_PATH
        idx = config.EMULATOR_INDEX
        etype = config.EMULATOR_TYPE

        # ... (中間省略權限檢查與變數定義) ...
        # ... (請保留您原本的 env 設定) ...
        env = os.environ.copy()
        env["__COMPAT_LAYER"] = "RunAsInvoker"

        print(f"💀 [System] 執行模擬器重啟 (Type: {etype} | Index: {idx})...")

        try:
            # === 1. 嘗試「溫柔關閉」 ===
            # 先試著用正規指令關閉，但加上 timeout 防止卡死
            print(f"   💤 嘗試正常關閉模擬器...")
            
            cmd_quit = ""
            if etype == "mumu":
                cmd_quit = f'"{manager}" control -i {idx} -c shutdown'
            elif etype == "ldplayer":
                cmd_quit = f'"{manager}" quit --index {idx}'

            try:
                # 🔥 關鍵：設定 timeout=5秒
                # 如果 Manager 5秒內沒回應，就當作它卡死了
                subprocess.run(
                    cmd_quit, 
                    shell=True, 
                    env=env,
                    timeout=5,  # 👈 超時設定
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
            except subprocess.TimeoutExpired:
                print("   ⚠️ 正常關閉超時 (Manager 可能卡死)")
                # 這裡不需要做什麼，因為下面會檢查 process 並執行強制獵殺

            # === 2. 檢查並執行「強制獵殺」 ===
            # 不管上面有沒有成功，我們直接呼叫獵殺函式來確保乾淨
            # 或者是您可以寫邏輯判斷，但為了穩定，重啟時強制殺一次通常最保險
            self._force_kill_emulator_process()

            # === 3. 重新啟動 ===
            print(f"   🚀 正在啟動模擬器...")
            cmd_open = ""
            if etype == "mumu":
                cmd_open = f'"{manager}" control -i {idx} -c launch'
            elif etype == "ldplayer":
                cmd_open = f'"{manager}" launch --index {idx}'

            subprocess.run(
                cmd_open, 
                shell=True, 
                check=True,
                env=env,
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            
            # 4. 等待 ADB 連線
            self.wait_for_device_boot()

        except Exception as e:
            print(f"❌ 模擬器重啟失敗: {e}")