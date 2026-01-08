# core/debugger.py
import time
import traceback
import cv2
from pathlib import Path
from datetime import datetime

class CrashReporter:
    def __init__(self, adb, save_dir="crash_reports"):
        self.adb = adb
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def save_report(self, exception_obj, context="unknown"):
        """ [整合版] 儲存截圖 + Log + 10秒錄影 """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"{timestamp}_{context}"
        
        print(f"📸 [Debugger] 發生錯誤，正在蒐證... ({filename_base})")

        # 1. 截圖 (瞬間畫面)
        self._save_screenshot(filename_base)
        
        # 2. 寫 Log (錯誤細節)
        self._save_log(filename_base, exception_obj, context)

        # 3. 🔥 錄影 (錄製接下來 10 秒的畫面)
        self._record_video(filename_base, duration=10)

    def _save_screenshot(self, base_name):
        try:
            screen = self.adb.get_screenshot()
            if screen is not None:
                path = self.save_dir / f"{base_name}.png"
                cv2.imwrite(str(path), screen)
                print(f"   └─ [1/3] 截圖已儲存")
        except: pass

    def _save_log(self, base_name, exc, ctx):
        try:
            path = self.save_dir / f"{base_name}.txt"
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"Context: {ctx}\nError: {exc}\n\n{traceback.format_exc()}")
            print(f"   └─ [2/3] Log 已儲存")
        except: pass

    def _record_video(self, base_name, duration=10):
        """ 🔥 新功能: 錄影 10 秒並取出 """
        print(f"   └─ [3/3] 正在錄影 {duration} 秒 (請稍候)...")
        
        # 定義手機端與電腦端的路徑
        # 注意: 檔名不能有特殊字元，這裡用 base_name 很安全
        remote_path = f"/sdcard/crash_{base_name}.mp4"
        local_path = self.save_dir / f"{base_name}.mp4"

        try:
            # A. 開始錄影 (利用 --time-limit 自動停止，這會暫停程式 duration 秒)
            # 指令: screenrecord --time-limit 10 /sdcard/xxx.mp4
            self.adb.run_cmd(f"shell screenrecord --time-limit {duration} {remote_path}")
            
            # B. 將影片拉回電腦
            # 指令: adb pull /sdcard/xxx.mp4 ./crash_reports/xxx.mp4
            # 注意: execute_cmd 的實作通常是 adb -s serial {cmd}，所以這裡不用加 shell
            pull_msg = self.adb.run_cmd(f'pull {remote_path} "{local_path}"')
            
            # C. 清理手機上的暫存檔 (節省空間)
            self.adb.run_cmd(f"shell rm {remote_path}")

            if local_path.exists():
                print(f"      ✅ 影片已存檔: {local_path.name}")
            else:
                print(f"      ❌ 影片下載失敗: {pull_msg}")

        except Exception as e:
            print(f"      ⚠️ 錄影功能異常: {e}")